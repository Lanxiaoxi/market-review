import { useState } from "react";
import { useNavigate } from "react-router";
import PageHeader from "@/components/layout/PageHeader";
import CardHeader from "@/components/layout/CardHeader";
import IndexCard from "@/components/common/IndexCard";
import BaseCard from "@/components/common/BaseCard";
import Segmented from "@/components/common/Segmented";
import PillButton from "@/components/common/PillButton";
import Chip from "@/components/common/Chip";
import PlaceholderCard from "@/components/common/PlaceholderCard";
import IntradayChart from "@/components/charts/IntradayChart";
import BreadthTable from "@/components/common/BreadthTable";
import { TOKENS } from "@/components/charts/BaseChart";
import { useOverview } from "@/hooks/useOverview";
import { useChartLibQuery } from "@/hooks/useChartLib";
import { usePolling } from "@/hooks/usePolling";
import { useIntraday } from "@/hooks/useIntraday";

// ─── Gate G2：盘中 60s 轮询开关（默认关闭，改为 true 启用） ───
const MARKET_POLLING_ENABLED = false;

const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

/** 分时对比图的三条线：代码显式映射，避免按数组下标取数错位 */
const INDEX_SERIES = [
  { name: "上证指数", code: "000001", tencent: "sh000001", color: TOKENS.ink },
  { name: "沪深300", code: "000300", tencent: "sh000300", color: TOKENS.accent },
  { name: "创业板指", code: "399006", tencent: "sz399006", color: TOKENS.seriesPurple },
];

/**
 * 归一化为「相对首个点的涨跌幅（%）」：三条指数线共享同一比例尺，可真实对比。
 * （替代旧的独立 min-max 归一化——那会把 ±0.05% 的上证拉成和 ±0.85% 的创业板一样高，且 Y 轴显示无意义数值）
 */
function toPctChange(src: number[]): number[] {
  if (!src.length) return [];
  const base = src[0] || 1;
  return src.map((v) => ((v - base) / base) * 100);
}

/** 生成 n 个均匀分布的 A 股交易时段标签（09:30–11:30 + 13:00–15:00，共 242 分钟） */
function sessionLabels(n: number): string[] {
  const all: string[] = [];
  const push = (start: number, count: number) => {
    for (let i = 0; i < count; i++) {
      const m = start + i;
      all.push(`${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`);
    }
  };
  push(9 * 60 + 30, 121);
  push(13 * 60, 121);
  if (all.length <= n) return all;
  const step = (all.length - 1) / (n - 1);
  return Array.from({ length: n }, (_, i) => all[Math.round(i * step)]);
}

/** 钉选图表的迷你渲染（按 type 区分） */
function MiniChart({ type }: { type: string }) {
  if (type === "barDist") {
    return (
      <svg width="150" height="48" viewBox="0 0 150 48" fill="none" style={{ display: "block" }}>
        <rect x="2" y="40" width="14" height="4" rx="1" fill="var(--up)" />
        <rect x="20" y="33" width="14" height="11" rx="1" fill="var(--up)" />
        <rect x="38" y="12" width="14" height="32" rx="1" fill="var(--up)" />
        <rect x="56" y="39" width="14" height="5" rx="1" fill="var(--series-base)" />
        <rect x="74" y="25" width="14" height="19" rx="1" fill="var(--down)" />
        <rect x="92" y="38" width="14" height="6" rx="1" fill="var(--down)" />
        <rect x="110" y="42" width="14" height="2" rx="1" fill="var(--down)" />
      </svg>
    );
  }
  // turnoverIntraday
  if (type === "turnoverIntraday") {
    return (
      <svg width="150" height="48" viewBox="0 0 150 48" fill="none" style={{ display: "block" }}>
        <rect x="4" y="30" width="10" height="14" rx="1" fill="var(--bar-fill)" />
        <rect x="18" y="34" width="10" height="10" rx="1" fill="var(--bar-fill)" />
        <rect x="32" y="38" width="10" height="6" rx="1" fill="var(--bar-fill)" />
        <rect x="46" y="40" width="10" height="4" rx="1" fill="var(--bar-fill)" />
        <rect x="60" y="36" width="10" height="8" rx="1" fill="var(--bar-fill)" />
        <rect x="74" y="32" width="10" height="12" rx="1" fill="var(--bar-fill)" />
        <rect x="88" y="26" width="10" height="18" rx="1" fill="var(--bar-fill)" />
        <rect x="102" y="22" width="10" height="22" rx="1" fill="var(--bar-fill)" />
        <rect x="116" y="14" width="10" height="30" rx="1" fill="var(--bar-fill)" />
        <rect x="130" y="8" width="10" height="36" rx="1" fill="var(--bar-fill)" />
        <polyline points="9,40 23,36 37,34 51,33 65,29 79,27 93,23 107,19 121,13 135,6" stroke="var(--accent)" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  // ifBasis：沪深300现货（ink）vs IF主力（accent）两条线
  if (type === "ifBasis") {
    return (
      <svg width="150" height="48" viewBox="0 0 150 48" fill="none" style={{ display: "block" }}>
        <polyline points="2,40 16,38 30,39 44,34 58,36 72,31 86,33 100,27 114,30 128,24 146,26" stroke="var(--ink)" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <polyline points="2,36 16,34 30,35 44,29 58,31 72,25 86,27 100,20 114,24 128,16 146,18" stroke="var(--accent)" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  // limitCount：涨停红柱 + 跌停绿柱
  if (type === "limitCount") {
    return (
      <svg width="150" height="48" viewBox="0 0 150 48" fill="none" style={{ display: "block" }}>
        {[8, 18, 26, 30, 24, 34, 28, 36, 30, 38].map((h, i) => (
          <rect key={`u${i}`} x={4 + i * 14} y={44 - h} width="6" height={h} rx="1" fill="var(--up)" />
        ))}
        {[6, 10, 8, 14, 9, 12, 15, 8, 11, 6].map((h, i) => (
          <rect key={`d${i}`} x={11 + i * 14} y={44 - h} width="6" height={h} rx="1" fill="var(--down)" />
        ))}
      </svg>
    );
  }
  return (
    <svg width="150" height="48" viewBox="0 0 150 48" fill="none" style={{ display: "block" }}>
      <rect x="4" y="30" width="10" height="14" rx="1" fill="var(--bar-fill)" />
      <rect x="18" y="34" width="10" height="10" rx="1" fill="var(--bar-fill)" />
      <rect x="32" y="38" width="10" height="6" rx="1" fill="var(--bar-fill)" />
      <rect x="46" y="40" width="10" height="4" rx="1" fill="var(--bar-fill)" />
      <rect x="60" y="36" width="10" height="8" rx="1" fill="var(--bar-fill)" />
      <rect x="74" y="32" width="10" height="12" rx="1" fill="var(--bar-fill)" />
      <rect x="88" y="26" width="10" height="18" rx="1" fill="var(--bar-fill)" />
      <rect x="102" y="22" width="10" height="22" rx="1" fill="var(--bar-fill)" />
      <rect x="116" y="14" width="10" height="30" rx="1" fill="var(--bar-fill)" />
      <rect x="130" y="8" width="10" height="36" rx="1" fill="var(--bar-fill)" />
      <polyline points="9,40 23,36 37,34 51,33 65,29 79,27 93,23 107,19 121,13 135,6" stroke="var(--accent)" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** 板块排行榜：轨道 flex 自适应，填充按真实百分比（修复 v1 把百分比当 px 的缺陷） */
function SectorRank({
  title,
  items,
  color,
  sign,
}: {
  title: string;
  items: { name: string; pct: number }[];
  color: string;
  sign: string;
}) {
  const maxAbs = Math.max(...items.map((x) => Math.abs(x.pct)), 1);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}>
      <span style={{ fontSize: 13, fontWeight: 600, color }}>{title}</span>
      {items.map((s, i) => (
        <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            style={{
              flex: "0 0 72px",
              fontSize: 13,
              fontWeight: 500,
              color: "var(--ink)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {s.name}
          </span>
          <span
            style={{
              flex: 1,
              minWidth: 0,
              height: 8,
              borderRadius: 4,
              background: "var(--grid)",
              overflow: "hidden",
            }}
          >
            <span
              className="mr-grow"
              style={{
                display: "block",
                height: 8,
                width: `${Math.max((Math.abs(s.pct) / maxAbs) * 100, 3)}%`,
                borderRadius: 4,
                background: color,
                animationDelay: `${i * 80}ms`,
              }}
            />
          </span>
          <span
            className="num"
            style={{ flex: "0 0 52px", fontSize: 13, fontWeight: 500, color, textAlign: "right" }}
          >
            {sign}
            {Math.abs(s.pct).toFixed(2)}%
          </span>
        </div>
      ))}
    </div>
  );
}

export default function OverviewPage() {
  const navigate = useNavigate();
  const { data, isError } = useOverview();
  const { data: chartLib } = useChartLibQuery();
  usePolling(MARKET_POLLING_ENABLED); // Gate G2

  // T7.2: 分段控件状态（只影响本卡）
  const [period, setPeriod] = useState("today");

  // 日期显示：优先用后端 weekday（历史快照也正确），缺失时本地推算
  const dateStr = data
    ? `${data.date} · ${data.weekday ?? WEEKDAYS[new Date(data.date).getDay()]}`
    : "加载中…";

  // 钉选图表（T7.6）
  const pinnedCharts = (chartLib ?? []).filter((c) => c.pinned);
  const chartNames: Record<string, string> = {
    "bar-dist": "涨跌家数分布",
    "turnover-intraday": "成交额分时",
    "if-basis": "股指期现对比",
    "limit-count": "涨跌停家数",
  };

  // ─── 指数分时对比（T7.2，今日用真实分时，5日/20日用指数 sparkline） ───
  const indices = data?.indices ?? [];
  const idxByCode = (code: string) => indices.find((x) => x.code === code);

  const { data: intraday } = useIntraday(
    INDEX_SERIES.map((d) => d.tencent),
    period === "today"
  );

  // 今日：仅使用真实分时；无数据则为空数组（页面显示「暂无有效数据」）
  const todaySeries = INDEX_SERIES.map((def) => {
    const intra = intraday?.codes[def.tencent];
    return {
      name: def.name,
      data: intra && intra.prices.length > 0 ? toPctChange(intra.prices) : [],
      color: def.color,
    };
  });

  const series5d = INDEX_SERIES.map((def) => ({
    name: def.name,
    data: toPctChange(idxByCode(def.code)?.sparkline.slice(-5) ?? [14, 14, 14, 14, 14]),
    color: def.color,
  }));
  const series20d = INDEX_SERIES.map((def) => ({
    name: def.name,
    data: toPctChange(idxByCode(def.code)?.sparkline ?? [14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14]),
    color: def.color,
  }));

  const intradaySeries = period === "today" ? todaySeries : period === "5d" ? series5d : series20d;
  // 时间轴标签必须与数据点一一对应（ECharts category 轴按索引对齐，长度不等会丢点）
  const todayTimes = intraday?.codes["sh000001"]?.times;
  const todayLen = intraday?.codes["sh000001"]?.prices.length ?? 12;
  const todayLabels = todayTimes && todayTimes.length > 0 ? todayTimes : sessionLabels(todayLen);
  const sparkLen = idxByCode("000001")?.sparkline?.length ?? 12;
  const labels20d = Array.from({ length: sparkLen }, (_, i) =>
    i === sparkLen - 1 ? "今日" : `T-${sparkLen - 1 - i}`
  );
  const timeLabels =
    period === "today"
      ? todayLabels
      : period === "5d"
        ? ["T-4", "T-3", "T-2", "T-1", "今日"]
        : labels20d;

  // 无有效数据：整页占位（保留标题栏）
  if (!data || indices.length === 0) {
    return (
      <>
        <PageHeader title="今日总览" sub="3秒扫盘 · 把握全局 · 关键数字与微缩趋势" date="—" />
        <PlaceholderCard text="暂无有效数据" />
      </>
    );
  }

  return (
    <>
      {/* 页面标题栏 */}
      <PageHeader
        title="今日总览"
        sub="3秒扫盘 · 把握全局 · 关键数字与微缩趋势"
        date={dateStr}
      >
        <Chip
          text={data?.closed ? "已收盘" : "交易中"}
          dotColor={data?.closed ? "var(--series-base)" : "var(--accent)"}
          live={!data?.closed}
        />
        <PillButton
          onClick={() => navigate("/history")}
          style={{ background: "var(--chip-bg)", color: "var(--muted-strong)" }}
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M3 2 L3 13 L13 13 M3 8 L6 5 L9 8 L13 3" stroke="var(--muted-strong)" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          </svg>
          历史复盘
        </PillButton>
        <PillButton title="导出报告（即将上线）">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M8 2.5 L8 9.5 M5 6.5 L8 9.5 L11 6.5 M3 13 L13 13" stroke="#ffffff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          导出报告
        </PillButton>
      </PageHeader>

      {/* T7.4: 错误提示（tooltip 语义，不用 spinner） */}
      {isError && (
        <div
          title="接口暂不可用，正在展示缓存数据"
          className="mr-fade"
          style={{ fontSize: 12, color: "var(--muted)", padding: "6px 12px", background: "var(--chip-bg)", borderRadius: "var(--r-pill)", alignSelf: "flex-start" }}
        >
          ⚠ 数据接口暂不可用，已切换为缓存数据
        </div>
      )}

      {/* 8 张指数卡网格（v2：语义色条 + 面积图 + 入场错峰；窄屏自动换行） */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
        {indices.map((idx, i) => (
          <IndexCard key={idx.code} data={idx} index={i} />
        ))}
      </div>

      {/* 指数分时对比 + 市场宽度（自适应：宽屏并排，窄屏按比例收缩，极窄自动换行） */}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
        {/* 指数分时对比 */}
        <BaseCard
          className="mr-enter"
          style={{ flex: "1 1 968px", minWidth: 0, display: "flex", flexDirection: "column", gap: 14, animationDelay: "80ms" }}
        >
          <CardHeader
            title="指数分时对比"
            actions={
              <Segmented
                options={[{ label: "今日", value: "today" }, { label: "近5日", value: "5d" }, { label: "近20日", value: "20d" }]}
                value={period}
                onChange={setPeriod}
              />
            }
          />
          {/* v2 图例：色线 + 文字，辨识度高于纯文字 */}
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            {INDEX_SERIES.map((s) => (
              <span
                key={s.code}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--muted)" }}
              >
                <span style={{ width: 12, height: 3, borderRadius: 2, background: s.color }} />
                {s.name}
              </span>
            ))}
          </div>
          {period === "today" && !todaySeries.some((s) => s.data.length > 0) ? (
            <PlaceholderCard text="暂无有效数据" />
          ) : (
            <IntradayChart series={intradaySeries} timeLabels={timeLabels} height={216} />
          )}
        </BaseCard>

        {/* 市场宽度：四列表格（状态｜分布｜占比｜家数）+ 50% 参考刻度 + 成交额/涨跌停指标块 */}
        <BaseCard
          className="mr-enter"
          style={{ flex: "1 1 400px", minWidth: 0, animationDelay: "140ms" }}
        >
          <BreadthTable breadth={data?.breadth} showTurnover />
        </BaseCard>
      </div>

      {/* 行业板块表现 */}
      <BaseCard
        className="mr-enter"
        style={{ display: "flex", flexDirection: "column", gap: 16, animationDelay: "200ms" }}
      >
        <CardHeader title="行业板块表现" hint="申万一级行业 · 领涨/领跌 TOP5 · 单位 %" />
        {(data?.sectorsUp?.length ?? 0) === 0 && (data?.sectorsDown?.length ?? 0) === 0 ? (
          <PlaceholderCard text="暂无有效数据" />
        ) : (
          <div style={{ display: "flex", gap: 40 }}>
            <SectorRank title="领涨 TOP5" items={data?.sectorsUp ?? []} color="var(--up)" sign="+" />
            <SectorRank title="领跌 TOP5" items={data?.sectorsDown ?? []} color="var(--down)" sign="-" />
          </div>
        )}
      </BaseCard>

      {/* 我的图表（T7.6 钉选闭环） */}
      <BaseCard
        className="mr-enter"
        style={{ display: "flex", flexDirection: "column", gap: 14, animationDelay: "260ms" }}
      >
        <CardHeader title="我的图表" hint="从自定义图表页选择 · 钉选展示" />
        <div style={{ display: "flex", gap: 12 }}>
          {/* 已钉选槽 */}
          {pinnedCharts.map((c) => (
            <div key={c.id} style={{ position: "relative", flex: 1, height: 150, background: "var(--placeholder)", border: "1px solid var(--border)", borderRadius: "var(--r-card)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}>
              <span style={{ position: "absolute", top: 8, right: 8, display: "flex", alignItems: "center", gap: 5, padding: "3px 8px", borderRadius: "var(--r-pill)", background: "var(--chip-bg)", fontSize: 12, color: "var(--muted-strong)" }}>
                <span style={{ width: 6, height: 6, borderRadius: 9999, background: "var(--accent)" }} />
                已钉选
              </span>
              <MiniChart type={c.type} />
              <span style={{ fontSize: 12, color: "var(--muted)" }}>{chartNames[c.id] ?? c.name}</span>
            </div>
          ))}
          {/* 空槽 */}
          {pinnedCharts.length < 2 && (
            <div style={{ flex: 1 }}>
              <PlaceholderCard actionable />
            </div>
          )}
        </div>
      </BaseCard>

      {/* 页脚：v2 增加发丝分隔线，消除「悬空」感 */}
      <div style={{ paddingTop: 16, borderTop: "1px solid var(--border)" }}>
        <span style={{ fontSize: 12, color: "var(--muted)" }}>
          数据来源：Tushare / 腾讯行情，仅供参考 · 行情按 A 股惯例红涨绿跌
        </span>
      </div>
    </>
  );
}
