import PageHeader from "@/components/layout/PageHeader";
import BaseCard from "@/components/common/BaseCard";
import StrategyChart from "@/components/charts/StrategyChart";

export default function StrategyPage() {
  // 策略收益 vs 沪深300（mock 数据，P7 可接入真实策略）
  const strategyData = [150, 138, 145, 128, 132, 118, 124, 105, 112, 95, 88, 92, 78, 70, 74, 60, 66, 52, 58, 55];
  const benchmarkData = [150, 146, 148, 140, 142, 135, 138, 128, 131, 122, 126, 118, 120, 112, 115, 108, 110, 104, 107, 105];
  const volumeData = [30, 45, 25, 60, 50, 70, 40, 65, 55, 80, 45, 35, 50, 60, 40, 70, 55, 45, 60, 50];

  return (
    <>
      <PageHeader
        title="策略画板"
        sub="承载自制图表与深度分析 · 全屏宽幅画布"
      />

      <BaseCard style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>自定义策略曲线</span>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>策略收益 vs 沪深300 · 含成交量</span>
        </div>
        <StrategyChart
          strategyData={strategyData}
          benchmarkData={benchmarkData}
          volumeData={volumeData}
          height={300}
        />
      </BaseCard>
    </>
  );
}