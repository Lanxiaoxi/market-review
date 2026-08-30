import { useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import CardHeader from "@/components/layout/CardHeader";
import BaseCard from "@/components/common/BaseCard";
import PlaceholderCard from "@/components/common/PlaceholderCard";
import Segmented from "@/components/common/Segmented";
import BarDistChart from "@/components/charts/BarDistChart";
import TurnoverChart from "@/components/charts/TurnoverChart";
import BasisChart from "@/components/charts/BasisChart";
import LimitCountChart from "@/components/charts/LimitCountChart";
import { TOKENS } from "@/components/charts/BaseChart";
import { useOverview } from "@/hooks/useOverview";
import { useIntraday } from "@/hooks/useIntraday";
import { useIfBasis } from "@/hooks/useIfBasis";
import { useLimitCounts } from "@/hooks/useLimitCounts";
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
  const [contract, setContract] = useState("IF"); // 期现对比合约（IF/IH/IM）
  // 时间范围：近7天 / 近30天 / 默认（60 个交易日，即当前维度），作用于下方两个日线序列图
  const [range, setRange] = useState("default");
  const days = range === "7d" ? 7 : range === "30d" ? 30 : 60;
  const { data: basis } = useIfBasis(contract, days);
  const { data: limitCounts } = useLimitCounts(days); // 日线涨跌停家数

  const charts = useChartLibStore((s) => s.charts);
  const barDist = charts.find((c) => c.id === "bar-dist");
  const turnover = charts.find((c) => c.id === "turnover-intraday");
  const ifBasis = charts.find((c) => c.id === "if-basis");
  const limitCount = charts.find((c) => c.id === "limit-count");

  // 涨跌家数分布：直接使用后端 7 档真实统计（不再用 up*0.86 近似）
  const distData = (data?.breadth.dist ?? []).map((d) => ({
    label: d.label,
    value: d.value,
    color: DIST_COLOR[d.label] ?? TOKENS.seriesBase,
  }));

  const shIntraday = intraday?.codes["sh000001"];

  return (
    <>
      <PageHeader title="自定义图表" sub="我的行情统计图表">
        <span style={{ fontSize: 12, color: "var(--muted)" }}>时间范围</span>
        <Segmented
          options={[
            { label: "近7天", value: "7d" },
            { label: "近30天", value: "30d" },
            { label: "默认", value: "default" },
          ]}
          value={range}
          onChange={setRange}
          ariaLabel="图表时间范围"
        />
      </PageHeader>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* 涨跌家数分布 */}
        <BaseCard
          className="mr-enter"
          style={{ display: "flex", flexDirection: "column", gap: 14, animationDelay: "0ms" }}
        >
          <CardHeader
            title="涨跌家数分布"
            actions={barDist && <PinButton id={barDist.id} name={barDist.name} type={barDist.type} pinned={barDist.pinned} />}
          />
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--up)" }}>上涨区间</span>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>平盘</span>
            <span style={{ fontSize: 12, color: "var(--down)" }}>下跌区间</span>
          </div>
          {distData.length > 0 ? (
            <BarDistChart data={distData} height={300} />
          ) : (
            <PlaceholderCard text="暂无有效数据" />
          )}
        </BaseCard>

        {/* 成交额分时 */}
        <BaseCard
          className="mr-enter"
          style={{ display: "flex", flexDirection: "column", gap: 14, animationDelay: "60ms" }}
        >
          <CardHeader
            title="成交额分时"
            actions={turnover && <PinButton id={turnover.id} name={turnover.name} type={turnover.type} pinned={turnover.pinned} />}
          />
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>区间成交额</span>
            <span style={{ fontSize: 12, color: "var(--accent)" }}>累计成交额</span>
          </div>
          {shIntraday && shIntraday.times.length > 0 ? (
            <TurnoverChart times={shIntraday.times} amounts={shIntraday.amounts} height={300} />
          ) : (
            <PlaceholderCard text="暂无有效数据" />
          )}
        </BaseCard>

        {/* 股指期货期现对比（通栏，分段切换合约） */}
        <BaseCard
          className="mr-enter"
          style={{ gridColumn: "1 / -1", display: "flex", flexDirection: "column", gap: 14, animationDelay: "120ms" }}
        >
          <CardHeader
            title="股指期货期现对比"
            actions={
              <>
                <span style={{ fontSize: 12, color: "var(--muted)", whiteSpace: "nowrap" }}>现货 vs 中金所主力合约 · 近 {days} 个交易日</span>
                <Segmented
                  options={[
                    { label: "沪深300", value: "IF" },
                    { label: "上证50", value: "IH" },
                    { label: "中证1000", value: "IM" },
                  ]}
                  value={contract}
                  onChange={setContract}
                  ariaLabel="切换期货合约"
                />
                {ifBasis && <PinButton id={ifBasis.id} name={ifBasis.name} type={ifBasis.type} pinned={ifBasis.pinned} />}
              </>
            }
          />
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--ink)" }}>{basis?.name ?? "现货指数"}</span>
            <span style={{ fontSize: 12, color: "var(--accent)" }}>{basis?.contract ?? ""}主力合约</span>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>基差（点，现货-期货）</span>
            {basis && basis.dates.length > 0 && (
              <span style={{ fontSize: 12, color: "var(--muted-strong)" }}>
                最新基差 {basis.basis[basis.basis.length - 1] >= 0 ? "+" : ""}
                {basis.basis[basis.basis.length - 1].toFixed(2)} 点 · 基差率{" "}
                {(basis.premium[basis.premium.length - 1] ?? 0) >= 0 ? "+" : ""}
                {(basis.premium[basis.premium.length - 1] ?? 0).toFixed(3)}%
              </span>
            )}
          </div>
          {basis && basis.dates.length > 0 ? (
            <BasisChart data={basis} height={320} />
          ) : (
            <PlaceholderCard text="暂无有效数据" />
          )}
        </BaseCard>

        {/* 日线涨停/跌停家数（通栏） */}
        <BaseCard
          className="mr-enter"
          style={{ gridColumn: "1 / -1", display: "flex", flexDirection: "column", gap: 14, animationDelay: "180ms" }}
        >
          <CardHeader
            title="涨跌停家数"
            actions={
              <>
                <span style={{ fontSize: 12, color: "var(--muted)", whiteSpace: "nowrap" }}>每日涨停/跌停 · 近 {days} 个交易日</span>
                {limitCount && <PinButton id={limitCount.id} name={limitCount.name} type={limitCount.type} pinned={limitCount.pinned} />}
              </>
            }
          />
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--up)" }}>涨停</span>
            <span style={{ fontSize: 12, color: "var(--down)" }}>跌停</span>
            {limitCounts && limitCounts.dates.length > 0 && (
              <span style={{ fontSize: 12, color: "var(--muted)" }}>
                最新一日（{limitCounts.dates[limitCounts.dates.length - 1]}）：涨停 {limitCounts.limitUp[limitCounts.limitUp.length - 1]} · 跌停 {limitCounts.limitDown[limitCounts.limitDown.length - 1]}
              </span>
            )}
          </div>
          {limitCounts && limitCounts.dates.length > 0 ? (
            <LimitCountChart data={limitCounts} height={300} />
          ) : (
            <PlaceholderCard text="暂无有效数据" />
          )}
        </BaseCard>
      </div>

      {/* 从图表库添加图表 */}
      <PlaceholderCard text="从图表库添加图表" actionable />
    </>
  );
}
