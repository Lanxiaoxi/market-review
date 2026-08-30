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
import BarDistChart from "@/components/charts/BarDistChart";
import TurnoverChart from "@/components/charts/TurnoverChart";
import BreadthTable from "@/components/common/BreadthTable";
import { TOKENS } from "@/components/charts/BaseChart";
import { INDEX_SERIES } from "@/constants/indices";
import { useUserPrefs } from "@/stores/userPrefs";
import { useOverview } from "@/hooks/useOverview";
import { usePolling } from "@/hooks/usePolling";
import { useIntraday } from "@/hooks/useIntraday";

// ─── Gate G2：盘中 60s 轮询开关（默认关闭，改为 true 启用） ───
const MARKET_POLLING_ENABLED = false;
const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

// 历史回放：本地库覆盖起点（首次 250 天回填后）与上海时区「今天」
const HISTORY_START = "2025-08-19";
const shanghaiToday = () => new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);

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
              flex: "0 0 96px",
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
  // 历史日期回放：null = 最新；非空 = 指定日期（后端吸附到最近交易日）
  const [viewDate, setViewDate] = useState<string | null>(null);
  const { data, isError } = useOverview(viewDate);
  usePolling(MARKET_POLLING_ENABLED && !viewDate); // Gate G2：历史回放不轮询

  // T7.2: 分段控件状态（只影响本卡）
  const [period, setPeriod] = useState("today");
  // 分时对比显示的指数（默认取用户偏好；勾选 chips 增删，至少保留一个）
  const selectedIndices = useUserPrefs((s) => s.selectedIndices);
  const setSelectedIndices = useUserPrefs((s) => s.setSelectedIndices);
  const visibleSeries = INDEX_SERIES.filter((s) => selectedIndices.includes(s.code));
  const toggleIndex = (code: string) => {
    setSelectedIndices(
      selectedIndices.includes(code)
        ? selectedIndices.length > 1
          ? selectedIndices.filter((c) => c !== code)
          : selectedIndices
        : [...selectedIndices, code]
    );
  };

  // 日期显示：优先用后端 weekday（历史快照也正确），缺失时本地推算
  const dateStr = data
    ? `${data.date} · ${data.weekday ?? WEEKDAYS[new Date(data.date).getDay()]}`
    : "加载中…";

  // ─── 指数分时对比（今日用真实分时；近5日用最近 5 个交易日分时拼接） ───
  const indices = data?.indices ?? [];
  const idxByCode = (code: string) => indices.find((x) => x.code === code);

  // 拉取全部分时（今日 days=1，近5日 days=5），显示集由 selectedIndices 决定
  const { data: intraday } = useIntraday(
    INDEX_SERIES.map((d) => d.tencent),
    !viewDate, // 历史回放不拉分时（分时是当日数据）
    period === "5d" ? 5 : 1
  );

  // 今日：仅使用真实分时；无数据则为空数组（页面显示「暂无有效数据」）。
  // 历史回放时强制忽略 intraday（react-query 停用不会清缓存，否则会残留最新日分时）
  const todaySeries = visibleSeries.map((def) => {
    const intra = !viewDate ? intraday?.codes[def.tencent] : undefined;
    return {
      name: def.name,
      data: intra && intra.prices.length > 0 ? toPctChange(intra.prices) : [],
      color: def.color,
    };
  });

  // 近5日：最近 5 个交易日分时拼接（times 形如 "MM-DD HH:MM"），
  // 每日以其首点重定基（0% 起）；本地缺失日价格为 0 → 保持 0 线，随 15:35 固化积累自动填满。
  // 历史回放无分时 → 退化为近 5 日收盘价趋势。
  const series5d = visibleSeries.map((def) => {
    const intra = !viewDate ? intraday?.codes[def.tencent] : undefined;
    if (intra && intra.prices.length > 0) {
      const data: number[] = [];
      let base = 0;
      let prevDay = "";
      intra.prices.forEach((p, i) => {
        const day = intra.times[i]?.slice(0, 5) ?? "";
        if (day !== prevDay) {
          prevDay = day;
          base = p > 0 ? p : 0;
        }
        data.push(base > 0 ? ((p - base) / base) * 100 : 0);
      });
      return { name: def.name, data, color: def.color };
    }
    // 历史回放 / 数据缺失 → 收盘价日线（近 5 日）
    return {
      name: def.name,
      data: toPctChange(idxByCode(def.code)?.closes.slice(-5) ?? []),
      color: def.color,
    };
  });

  const intradaySeries = period === "today" ? todaySeries : series5d;
  // 时间轴标签必须与数据点一一对应（ECharts category 轴按索引对齐，长度不等会丢点）
  const todayTimes = intraday?.codes["sh000001"]?.times;
  const todayLen = intraday?.codes["sh000001"]?.prices.length ?? 12;
  const todayLabels = todayTimes && todayTimes.length > 0 ? todayTimes : sessionLabels(todayLen);

  // 近5日：拼接时间轴（"MM-DD HH:MM"），标签只显示每日边界（日期）
  const fiveDayTimes = intraday?.codes["sh000001"]?.times ?? [];
  const fiveDayLabelAt = (idx: number) =>
    idx === 0 || fiveDayTimes[idx]?.slice(0, 5) !== fiveDayTimes[idx - 1]?.slice(0, 5);

  const timeLabels =
    period === "today"
      ? todayLabels
      : viewDate
        ? ["T-4", "T-3", "T-2", "T-1", "今日"]
        : fiveDayTimes;
  const labelAt = period === "5d" && !viewDate && fiveDayTimes.length > 0 ? fiveDayLabelAt : undefined;

  // 无有效数据：整页占位（保留标题栏）
  if (!data || indices.length === 0) {
    return (
      <>
        <PageHeader
          title={viewDate ? "历史总览" : "今日总览"}
          sub="3秒扫盘 · 把握全局 · 关键数字与微缩趋势"
          date="—"
        />
        <PlaceholderCard text="暂无有效数据" />
      </>
    );
  }

  return (
    <>
      {/* 页面标题栏 */}
      <PageHeader
        title={viewDate ? "历史总览" : "今日总览"}
        sub={viewDate ? "历史日期回放 · 数据来自本地库（零回源）" : "3秒扫盘 · 把握全局 · 关键数字与微缩趋势"}
        date={dateStr}
      >
        <input
          type="date"
          value={viewDate ?? ""}
          min={HISTORY_START}
          max={shanghaiToday()}
          onChange={(e) => setViewDate(e.target.value || null)}
          title="选择历史日期查看（非交易日自动吸附到最近交易日）"
          style={{
            padding: "5px 10px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "var(--card)",
            color: "var(--ink)",
            fontSize: 13,
            fontFamily: "inherit",
          }}
        />
        {viewDate && (
          <PillButton
            onClick={() => setViewDate(null)}
            style={{ background: "var(--chip-bg)", color: "var(--muted-strong)" }}
          >
            最新
          </PillButton>
        )}
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
          title={viewDate ? "所选日期无本地数据" : "接口暂不可用，正在展示缓存数据"}
          className="mr-fade"
          style={{ fontSize: 12, color: "var(--muted)", padding: "6px 12px", background: "var(--chip-bg)", borderRadius: "var(--r-pill)", alignSelf: "flex-start" }}
        >
          {viewDate
            ? `⚠ 所选日期 ${viewDate} 暂无数据（本地库覆盖 ${HISTORY_START} 之后）`
            : "⚠ 数据接口暂不可用，已切换为缓存数据"}
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
                options={[{ label: "今日", value: "today" }, { label: "近5日", value: "5d" }]}
                value={period}
                onChange={setPeriod}
              />
            }
          />
          {/* 指数选择 chips：勾选显示哪些指数（色线即图例，点击增删） */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
            {INDEX_SERIES.map((s) => {
              const on = selectedIndices.includes(s.code);
              return (
                <button
                  key={s.code}
                  onClick={() => toggleIndex(s.code)}
                  title={on ? `取消显示 ${s.name}` : `显示 ${s.name}`}
                  aria-pressed={on}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "3px 10px",
                    borderRadius: 9999,
                    border: on ? "1px solid var(--accent)" : "1px solid var(--border)",
                    background: on ? "var(--active-bg)" : "var(--chip-bg)",
                    fontSize: 12,
                    color: on ? "var(--accent)" : "var(--muted)",
                    fontFamily: "inherit",
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  <span style={{ width: 12, height: 3, borderRadius: 2, background: s.color }} />
                  {s.name}
                </button>
              );
            })}
          </div>
          {period === "today" && !todaySeries.some((s) => s.data.length > 0) ? (
            <PlaceholderCard
              text={viewDate ? "历史日期无分时数据，请切换「近5日 / 近20日」" : "暂无有效数据"}
            />
          ) : (
            <IntradayChart series={intradaySeries} timeLabels={timeLabels} height={216} labelAt={labelAt} />
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

      {/* 当日详情：涨跌家数分布 + 成交额分时（当日信息，自自定义图表页移入） */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <BaseCard
          className="mr-enter"
          style={{ display: "flex", flexDirection: "column", gap: 14, animationDelay: "160ms" }}
        >
          <CardHeader title="涨跌家数分布" hint="当日 7 档分布" />
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--up)" }}>上涨区间</span>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>平盘</span>
            <span style={{ fontSize: 12, color: "var(--down)" }}>下跌区间</span>
          </div>
          {(data?.breadth.dist ?? []).length > 0 ? (
            <BarDistChart data={data?.breadth.dist ?? []} height={260} />
          ) : (
            <PlaceholderCard text="暂无有效数据" />
          )}
        </BaseCard>

        <BaseCard
          className="mr-enter"
          style={{ display: "flex", flexDirection: "column", gap: 14, animationDelay: "200ms" }}
        >
          <CardHeader title="成交额分时" hint="上证指数 · 当日" />
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>区间成交额</span>
            <span style={{ fontSize: 12, color: "var(--accent)" }}>累计成交额</span>
          </div>
          {(() => {
            const sh = intraday?.codes["sh000001"];
            return sh && sh.times.length > 0 ? (
              <TurnoverChart times={sh.times} amounts={sh.amounts} height={260} />
            ) : (
              <PlaceholderCard text={viewDate ? "历史日期无分时数据" : "暂无有效数据"} />
            );
          })()}
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

      {/* 页脚：v2 增加发丝分隔线，消除「悬空」感 */}
      <div style={{ paddingTop: 16, borderTop: "1px solid var(--border)" }}>
        <span style={{ fontSize: 12, color: "var(--muted)" }}>
          数据来源：Tushare / 腾讯行情，仅供参考 · 行情按 A 股惯例红涨绿跌
        </span>
      </div>
    </>
  );
}
