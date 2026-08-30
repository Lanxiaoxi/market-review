import { useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import CardHeader from "@/components/layout/CardHeader";
import BaseCard from "@/components/common/BaseCard";
import PlaceholderCard from "@/components/common/PlaceholderCard";
import Segmented from "@/components/common/Segmented";
import BasisChart from "@/components/charts/BasisChart";
import LimitCountChart from "@/components/charts/LimitCountChart";
import BreadthSeriesChart from "@/components/charts/BreadthSeriesChart";
import { useIfBasis } from "@/hooks/useIfBasis";
import { useLimitCounts } from "@/hooks/useLimitCounts";
import { useBreadthSeries } from "@/hooks/useBreadthSeries";

/** 时间范围选项：默认（60 个交易日）在左，近7天 / 近30天 依次 */
const RANGE_OPTIONS = [
  { label: "默认", value: "default" },
  { label: "近7天", value: "7d" },
  { label: "近30天", value: "30d" },
];

export default function CustomChartPage() {
  const [contract, setContract] = useState("IF"); // 期现对比合约（IF/IH/IM）
  // 各表独立的时间范围：近7天 / 近30天 / 默认（60 个交易日，即当前维度）
  const [basisRange, setBasisRange] = useState("default");
  const [limitRange, setLimitRange] = useState("default");
  const [breadthRange, setBreadthRange] = useState("default");
  const basisDays = basisRange === "7d" ? 7 : basisRange === "30d" ? 30 : 60;
  const limitDays = limitRange === "7d" ? 7 : limitRange === "30d" ? 30 : 60;
  const breadthDays = breadthRange === "7d" ? 7 : breadthRange === "30d" ? 30 : 60;
  const { data: basis } = useIfBasis(contract, basisDays);
  const { data: limitCounts } = useLimitCounts(limitDays); // 日线涨跌停家数
  const { data: breadthSeries } = useBreadthSeries(breadthDays); // 日线市场宽度

  return (
    <>
      <PageHeader title="自定义图表" sub="我的行情统计图表" />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* 股指期货期现对比（通栏，分段切换合约） */}
        <BaseCard
          className="mr-enter"
          style={{ gridColumn: "1 / -1", display: "flex", flexDirection: "column", gap: 14, animationDelay: "0ms" }}
        >
          <CardHeader
            title="股指期货期现对比"
            actions={
              <>
                <span style={{ fontSize: 12, color: "var(--muted)", whiteSpace: "nowrap" }}>现货 vs 中金所主力合约 · 近 {basisDays} 个交易日</span>
                <Segmented
                  options={RANGE_OPTIONS}
                  value={basisRange}
                  onChange={setBasisRange}
                  ariaLabel="期现对比时间范围"
                />
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

        {/* 市场宽度（通栏，日线序列） */}
        <BaseCard
          className="mr-enter"
          style={{ gridColumn: "1 / -1", display: "flex", flexDirection: "column", gap: 14, animationDelay: "60ms" }}
        >
          <CardHeader
            title="市场宽度"
            actions={
              <>
                <span style={{ fontSize: 12, color: "var(--muted)", whiteSpace: "nowrap" }}>每日上涨/平盘/下跌家数 · 近 {breadthDays} 个交易日</span>
                <Segmented
                  options={RANGE_OPTIONS}
                  value={breadthRange}
                  onChange={setBreadthRange}
                  ariaLabel="市场宽度时间范围"
                />
              </>
            }
          />
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--up)" }}>上涨</span>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>平盘</span>
            <span style={{ fontSize: 12, color: "var(--down)" }}>下跌</span>
            {breadthSeries && breadthSeries.dates.length > 0 && (
              <span style={{ fontSize: 12, color: "var(--muted)" }}>
                最新一日（{breadthSeries.dates[breadthSeries.dates.length - 1]}）：上涨 {breadthSeries.up[breadthSeries.up.length - 1]} · 平盘 {breadthSeries.flat[breadthSeries.flat.length - 1]} · 下跌 {breadthSeries.down[breadthSeries.down.length - 1]}
              </span>
            )}
          </div>
          {breadthSeries && breadthSeries.dates.length > 0 ? (
            <BreadthSeriesChart data={breadthSeries} height={300} />
          ) : (
            <PlaceholderCard text="暂无有效数据" />
          )}
        </BaseCard>

        {/* 日线涨停/跌停家数（通栏） */}
        <BaseCard
          className="mr-enter"
          style={{ gridColumn: "1 / -1", display: "flex", flexDirection: "column", gap: 14, animationDelay: "120ms" }}
        >
          <CardHeader
            title="涨跌停家数"
            actions={
              <>
                <span style={{ fontSize: 12, color: "var(--muted)", whiteSpace: "nowrap" }}>每日涨停/跌停 · 近 {limitDays} 个交易日</span>
                <Segmented
                  options={RANGE_OPTIONS}
                  value={limitRange}
                  onChange={setLimitRange}
                  ariaLabel="涨跌停时间范围"
                />
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
