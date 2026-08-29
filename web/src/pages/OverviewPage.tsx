import { useState } from "react";
import { useNavigate } from "react-router";
import PageHeader from "@/components/layout/PageHeader";
import IndexCard from "@/components/common/IndexCard";
import BaseCard from "@/components/common/BaseCard";
import Segmented from "@/components/common/Segmented";
import PillButton from "@/components/common/PillButton";
import Chip from "@/components/common/Chip";
import PlaceholderCard from "@/components/common/PlaceholderCard";
import IntradayChart from "@/components/charts/IntradayChart";
import BreadthBar from "@/components/charts/BreadthBar";
import { TOKENS } from "@/components/charts/BaseChart";
import { useOverview } from "@/hooks/useOverview";
import { useChartLibQuery } from "@/hooks/useChartLib";
import { useChartLibStore } from "@/stores/chartLib";
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

/** 后端/腾讯分时不可用时：用该指数 sparkline 推导示意曲线（按序加确定性偏移，避免三条线重合） */
function mockTodayPoints(spark: number[], seed: number): number[] {
  return spark.map((v, i) => v + Math.sin(i * 1.37 + seed * 2.1) * 2.5);
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
        <rect x="2" y="40" width="14" height="4" fill="var(--up)" />
        <rect x="20" y="33" width="14" height="11" fill="var(--up)" />
        <rect x="38" y="12" width="14" height="32" fill="var(--up)" />
        <rect x="56" y="39" width="14" height="5" fill="var(--series-base)" />
        <rect x="74" y="25" width="14" height="19" fill="var(--down)" />
        <rect x="92" y="38" width="14" height="6" fill="var(--down)" />
        <rect x="110" y="42" width="14" height="2" fill="var(--down)" />
      </svg>
    );
  }
  // turnoverIntraday
  return (
    <svg width="150" height="48" viewBox="0 0 150 48" fill="none" style={{ display: "block" }}>
      <rect x="4" y="30" width="10" height="14" fill="var(--bar-fill)" />
      <rect x="18" y="34" width="10" height="10" fill="var(--bar-fill)" />
      <rect x="32" y="38" width="10" height="6" fill="var(--bar-fill)" />
      <rect x="46" y="40" width="10" height="4" fill="var(--bar-fill)" />
      <rect x="60" y="36" width="10" height="8" fill="var(--bar-fill)" />
      <rect x="74" y="32" width="10" height="12" fill="var(--bar-fill)" />
      <rect x="88" y="26" width="10" height="18" fill="var(--bar-fill)" />
      <rect x="102" y="22" width="10" height="22" fill="var(--bar-fill)" />
      <rect x="116" y="14" width="10" height="30" fill="var(--bar-fill)" />
      <rect x="130" y="8" width="10" height="36" fill="var(--bar-fill)" />
      <polyline points="9,40 23,36 37,34 51,33 65,29 79,27 93,23 107,19 121,13 135,6" stroke="var(--accent)" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
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
  };

  // ─── 指数分时对比（T7.2，今日用真实分时，5日/20日用指数 sparkline） ───
  const indices = data?.indices ?? [];
  const idxByCode = (code: string) => indices.find((x) => x.code === code);

  const { data: intraday } = useIntraday(
    INDEX_SERIES.map((d) => d.tencent),
    period === "today"
  );

  // 今日：优先真实分时；不可用时用各指数 sparkline 推导（三条线各自不同）
  const todaySeries = INDEX_SERIES.map((def, i) => {
    const intra = intraday?.codes[def.tencent];
    if (intra && intra.prices.length > 0) {
      return { name: def.name, data: toPctChange(intra.prices), color: def.color };
    }
    const spark = idxByCode(def.code)?.sparkline ?? [24, 20, 16, 18, 12, 14, 9, 11, 7, 8, 5, 6];
    return { name: def.name, data: toPctChange(mockTodayPoints(spark, i)), color: def.color };
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
  const todayLabels =
    todayTimes && todayTimes.length > 0 ? todayTimes : sessionLabels(todayLen);
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
          style={{ fontSize: 12, color: "var(--muted)", padding: "6px 12px", background: "var(--chip-bg)", borderRadius: "var(--r-pill)", alignSelf: "flex-start" }}
        >
          ⚠ 数据接口暂不可用，已切换为缓存数据
        </div>
      )}

      {/* 8 张指数卡网格 */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
        {indices.map((idx) => (
          <IndexCard key={idx.code} data={idx} />
        ))}
      </div>

      {/* 指数分时对比 + 市场宽度 */}
      <div style={{ display: "flex", gap: 16, alignItems: "stretch" }}>
        {/* 指数分时对比 */}
        <BaseCard style={{ flex: "0 0 968px", padding: "18px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>指数分时对比</span>
            <Segmented
              options={[{ label: "今日", value: "today" }, { label: "近5日", value: "5d" }, { label: "近20日", value: "20d" }]}
              value={period}
              onChange={setPeriod}
            />
          </div>
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--ink)" }}>上证指数</span>
            <span style={{ fontSize: 12, color: "var(--accent)" }}>沪深300</span>
            <span style={{ fontSize: 12, color: "var(--series-purple)" }}>创业板指</span>
          </div>
          <IntradayChart series={intradaySeries} timeLabels={timeLabels} height={216} />
        </BaseCard>

        {/* 市场宽度 */}
        <BaseCard style={{ flex: "1 1 auto", padding: "18px 20px", display: "flex", flexDirection: "column", gap: 16 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>市场宽度</span>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span className="num" style={{ fontSize: 22, fontWeight: 600, color: "var(--up)" }}>{data?.breadth.up.toLocaleString() ?? "—"}</span>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>上涨</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span className="num" style={{ fontSize: 22, fontWeight: 600, color: "var(--down)" }}>{data?.breadth.down.toLocaleString() ?? "—"}</span>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>下跌</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span className="num" style={{ fontSize: 22, fontWeight: 600, color: "var(--muted-strong)" }}>{data?.breadth.flat.toLocaleString() ?? "—"}</span>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>平盘</span>
            </div>
          </div>
          {data && (
            <BreadthBar
              up={data.breadth.up}
              flat={data.breadth.flat}
              down={data.breadth.down}
              height={18}
            />
          )}
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--up)" }}>上涨 {data?.breadth.upPct}%</span>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>平盘 {data?.breadth.flatPct}%</span>
            <span style={{ fontSize: 12, color: "var(--down)" }}>下跌 {data?.breadth.downPct}%</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 13, color: "var(--ink)" }}>成交额 {data?.breadth.turnover}</span>
            <span style={{ fontSize: 13, color: "var(--muted)" }}>涨停 {data?.breadth.limitUpCount} · 跌停 {data?.breadth.limitDownCount}</span>
          </div>
          <div style={{ height: 1, background: "var(--border)" }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--ink)" }}>涨停 TOP</span>
          {(data?.breadth.limitUpTop ?? []).map((s) => (
            <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 12, color: "var(--ink)", width: 64 }}>{s.name}</span>
              <span className="num" style={{ fontSize: 12, fontWeight: 500, color: "var(--up)" }}>+{s.pct.toFixed(2)}%</span>
            </div>
          ))}
        </BaseCard>
      </div>

      {/* 行业板块表现 */}
      <BaseCard style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>行业板块表现</span>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>申万一级行业 · 领涨/领跌 TOP5 · 单位 %</span>
        </div>
        <div style={{ display: "flex", gap: 32 }}>
          {/* 领涨 */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: "var(--up)" }}>领涨 TOP5</span>
            {(data?.sectorsUp ?? []).map((s) => {
              const maxW = Math.max(...(data?.sectorsUp ?? []).map((x) => Math.abs(x.pct)), 1);
              return (
                <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ width: 68, fontSize: 12, color: "var(--ink)", flex: "0 0 auto" }}>{s.name}</span>
                  <span style={{ height: 8, borderRadius: 4, background: "var(--up)", width: Math.max(8, s.pct / maxW * 100) }} />
                  <span className="num" style={{ fontSize: 12, fontWeight: 500, color: "var(--up)" }}>+{s.pct.toFixed(2)}%</span>
                </div>
              );
            })}
          </div>
          {/* 领跌 */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: "var(--down)" }}>领跌 TOP5</span>
            {(data?.sectorsDown ?? []).map((s) => {
              const maxW = Math.max(...(data?.sectorsDown ?? []).map((x) => Math.abs(x.pct)), 1);
              return (
                <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ width: 68, fontSize: 12, color: "var(--ink)", flex: "0 0 auto" }}>{s.name}</span>
                  <span style={{ height: 8, borderRadius: 4, background: "var(--down)", width: Math.max(8, Math.abs(s.pct) / maxW * 100) }} />
                  <span className="num" style={{ fontSize: 12, fontWeight: 500, color: "var(--down)" }}>{s.pct.toFixed(2)}%</span>
                </div>
              );
            })}
          </div>
        </div>
      </BaseCard>

      {/* 我的图表（T7.6 钉选闭环） */}
      <BaseCard style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>我的图表</span>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>从自定义图表页选择 · 钉选展示</span>
        </div>
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
              <PlaceholderCard />
            </div>
          )}
        </div>
      </BaseCard>

      {/* 页脚 */}
      <div style={{ paddingTop: 4 }}>
        <span style={{ fontSize: 12, color: "var(--muted)" }}>数据来源：Tushare / 腾讯行情，仅供参考 · 行情按 A 股惯例红涨绿跌</span>
      </div>
    </>
  );
}
