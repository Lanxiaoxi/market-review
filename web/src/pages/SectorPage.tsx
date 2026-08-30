import PageHeader from "@/components/layout/PageHeader";
import CardHeader from "@/components/layout/CardHeader";
import BaseCard from "@/components/common/BaseCard";
import DataTable, { RowSparkline } from "@/components/common/DataTable";
import { useSectors } from "@/hooks/useSectors";

export default function SectorPage() {
  const { data } = useSectors("pct");

  return (
    <>
      <PageHeader
        title="板块轮动"
        sub="捕捉当日热点与异动 · 申万一级行业涨跌排名"
        date={undefined}
      />

      <BaseCard className="mr-enter" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <CardHeader title="申万一级行业 · 涨跌排名" hint="按涨跌幅排序 · 单位 %" />
        <DataTable
          columns={[
            { label: "板块", className: "colName" },
            { label: "涨跌幅", className: "colPct" },
            { label: "领涨股", className: "colLeader" },
            { label: "5日走势", className: "colSpark" },
          ]}
        >
          {(data ?? []).length === 0 ? (
            <div style={{ padding: "32px 20px", textAlign: "center" }}>
              <span style={{ fontSize: 13, color: "var(--muted-strong)" }}>暂无有效数据</span>
            </div>
          ) : (
            (data ?? []).map((s) => {
              const isUp = s.pct >= 0;
              return (
                <div key={s.name} style={{ display: "flex", alignItems: "center", padding: "10px 0" }}>
                  <span style={{ fontSize: 13, fontWeight: 500, color: "var(--ink)", width: 120 }}>{s.name}</span>
                  <span className="num" style={{
                    fontSize: 13, fontWeight: 500, textAlign: "right", width: 80,
                    color: isUp ? "var(--up)" : "var(--down)",
                  }}>
                    {isUp ? "+" : ""}{s.pct.toFixed(2)}%
                  </span>
                  <span style={{ fontSize: 13, color: "var(--muted-strong)", flex: 1 }}>{s.leading}</span>
                  <RowSparkline points={s.sparkline} isUp={isUp} />
                </div>
              );
            })
          )}
        </DataTable>
      </BaseCard>
    </>
  );
}