import PageHeader from "@/components/layout/PageHeader";
import BaseCard from "@/components/common/BaseCard";
import PlaceholderCard from "@/components/common/PlaceholderCard";
import BarDistChart from "@/components/charts/BarDistChart";
import TurnoverChart from "@/components/charts/TurnoverChart";
import { TOKENS } from "@/components/charts/BaseChart";
import { useOverview } from "@/hooks/useOverview";
import { useIntraday } from "@/hooks/useIntraday";
import { useChartLibQuery, useToggleChartPin } from "@/hooks/useChartLib";
import { useChartLibStore } from "@/stores/chartLib";

/** 钉选按钮（pill 样式，状态切换） */
function PinButton({
  id,
  name,
  type,
  pinned,
}: {
  id: string;
  name: string;
  type: string;
  pinned: boolean;
}) {
  const toggle = useToggleChartPin();

  return (
    <button
      onClick={() => toggle.mutate({ id, name, type, pinned })}
      title={pinned ? "取消钉选" : "钉选到总览页"}
      aria-label={pinned ? `取消钉选 ${name}` : `钉选 ${name} 到总览页`}
      aria-pressed={pinned}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "3px 10px",
        borderRadius: 9999,
        border: pinned ? "1px solid var(--accent)" : "1px solid var(--border)",
        background: pinned ? "var(--active-bg)" : "var(--chip-bg)",
        fontSize: 12,
        color: pinned ? "var(--accent)" : "var(--muted)",
        fontFamily: "inherit",
        cursor: "pointer",
        whiteSpace: "nowrap",
        opacity: toggle.isPending ? 0.6 : 1,
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: 9999, background: pinned ? "var(--accent)" : "var(--series-base)" }} />
      {pinned ? "已钉选" : "钉选"}
    </button>
  );
}

const DIST_COLOR: Record<string, string> = {
  "涨停": TOKENS.up,
  "涨2-10%": TOKENS.up,
  "涨0-2%": TOKENS.up,
  "平盘": TOKENS.seriesBase,
  "跌0-2%": TOKENS.down,
  "跌2-10%": TOKENS.down,
  "跌停": TOKENS.down,
};

export default function CustomChartPage() {
  const { data } = useOverview();
  useChartLibQuery(); // 加载图表库到 store
  const { data: intraday } = useIntraday(["sh000001"]); // 上证指数分时（成交额）

  const charts = useChartLibStore((s) => s.charts);
  const barDist = charts.find((c) => c.id === "bar-dist");
  const turnover = charts.find((c) => c.id === "turnover-intraday");

  // 涨跌家数分布：直接使用后端 7 档真实统计（不再用 up*0.86 近似）
  const distData = (data?.breadth.dist ?? []).map((d) => ({
    label: d.label,
    value: d.value,
    color: DIST_COLOR[d.label] ?? TOKENS.seriesBase,
  }));

  const shIntraday = intraday?.codes["sh000001"];

  return (
    <>
      <PageHeader
        title="自定义图表"
        sub="我的行情统计图表"
      />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* 涨跌家数分布 */}
        <BaseCard style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>涨跌家数分布</span>
            {barDist && <PinButton id={barDist.id} name={barDist.name} type={barDist.type} pinned={barDist.pinned} />}
          </div>
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--up)" }}>上涨区间</span>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>平盘</span>
            <span style={{ fontSize: 12, color: "var(--down)" }}>下跌区间</span>
          </div>
          {distData.length > 0 ? (
            <BarDistChart data={distData} height={300} />
          ) : (
            <PlaceholderCard text="暂无分布数据" />
          )}
        </BaseCard>

        {/* 成交额分时 */}
        <BaseCard style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>成交额分时</span>
            {turnover && <PinButton id={turnover.id} name={turnover.name} type={turnover.type} pinned={turnover.pinned} />}
          </div>
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>区间成交额</span>
            <span style={{ fontSize: 12, color: "var(--accent)" }}>累计成交额</span>
          </div>
          {shIntraday && shIntraday.times.length > 0 ? (
            <TurnoverChart times={shIntraday.times} amounts={shIntraday.amounts} height={300} />
          ) : (
            <PlaceholderCard text="分时数据加载中" />
          )}
        </BaseCard>
      </div>

      {/* 从图表库添加图表 */}
      <PlaceholderCard text="从图表库添加图表" />
    </>
  );
}
