import { useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import CardHeader from "@/components/layout/CardHeader";
import BaseCard from "@/components/common/BaseCard";
import Segmented from "@/components/common/Segmented";
import DataTable, { RowSparkline } from "@/components/common/DataTable";
import SectorHistoryChart from "@/components/charts/SectorHistoryChart";
import { useSectors, useSectorHistory } from "@/hooks/useSectors";

/** 异动标记：连涨天数 / 10 日新高 */
function MoveBadge({ item }: { item: { upDays?: number; newHigh10d?: boolean } }) {
  const badges: { text: string; color: string; bg: string }[] = [];
  if ((item.upDays ?? 0) >= 3) {
    badges.push({ text: `连涨${item.upDays}天`, color: "var(--up)", bg: "var(--active-bg)" });
  }
  if (item.newHigh10d) {
    badges.push({ text: "10日新高", color: "var(--accent)", bg: "var(--active-bg)" });
  }
  if (badges.length === 0) return null;
  return (
    <span style={{ display: "inline-flex", gap: 4, flex: "0 0 auto" }}>
      {badges.map((b) => (
        <span
          key={b.text}
          style={{
            fontSize: 11,
            padding: "1px 6px",
            borderRadius: 9999,
            color: b.color,
            background: b.bg,
            whiteSpace: "nowrap",
          }}
        >
          {b.text}
        </span>
      ))}
    </span>
  );
}

export default function SectorPage() {
  // 动量区间：1=当日 / 5=近5日 / 10=近10日 / 20=近20日
  const [range, setRange] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const { data } = useSectors("pct", range);
  const { data: history } = useSectorHistory(selected);

  const rangeLabel = range === 1 ? "当日" : `近${range}日`;

  return (
    <>
      <PageHeader title="板块轮动" sub="捕捉当日热点与异动 · 申万一级行业涨跌排名" />

      <BaseCard
        className="mr-enter"
        style={{ display: "flex", flexDirection: "column", gap: 14 }}
      >
        <CardHeader
          title={`行业板块 · ${rangeLabel}涨跌排名`}
          hint="按涨跌幅排序 · 单位 % · 点击板块查看历史走势"
          actions={
            <Segmented
              options={[
                { label: "当日", value: "1" },
                { label: "近5日", value: "5" },
                { label: "近10日", value: "10" },
                { label: "近20日", value: "20" },
              ]}
              value={String(range)}
              onChange={(v) => {
                setRange(Number(v));
                setSelected(null);
              }}
              ariaLabel="切换动量区间"
            />
          }
        />
        <DataTable
          columns={[
            { label: "板块", className: "colName" },
            { label: "涨跌幅", className: "colPct" },
            { label: "异动", className: "colMove" },
            { label: "领涨股", className: "colLeader" },
            { label: `${rangeLabel}走势`, className: "colSpark" },
          ]}
        >
          {(data ?? []).length === 0 ? (
            <div style={{ padding: "32px 20px", textAlign: "center" }}>
              <span style={{ fontSize: 13, color: "var(--muted-strong)" }}>暂无有效数据</span>
            </div>
          ) : (
            (data ?? []).map((s) => {
              const isUp = s.pct >= 0;
              const active = selected === s.code;
              return (
                <div
                  key={s.code ?? s.name}
                  onClick={() => setSelected(s.code ?? null)}
                  title="查看历史走势"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "10px 6px",
                    cursor: "pointer",
                    background: active ? "var(--active-bg)" : "transparent",
                    borderRadius: 8,
                    marginLeft: -6,
                  }}
                >
                  <span style={{ fontSize: 13, fontWeight: 500, color: "var(--ink)", width: 120, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.name}</span>
                  <span className="num" style={{
                    fontSize: 13, fontWeight: 500, textAlign: "right", width: 80,
                    color: isUp ? "var(--up)" : "var(--down)",
                  }}>
                    {isUp ? "+" : ""}{s.pct.toFixed(2)}%
                  </span>
                  <span style={{ width: 96, display: "flex", alignItems: "center" }}>
                    <MoveBadge item={s} />
                  </span>
                  <span style={{ fontSize: 13, color: "var(--muted-strong)", flex: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.leading}</span>
                  <RowSparkline points={s.sparkline} isUp={isUp} />
                </div>
              );
            })
          )}
        </DataTable>
      </BaseCard>

      {/* 板块详情：历史收盘走势 */}
      {selected && history && (
        <BaseCard
          className="mr-enter"
          style={{ display: "flex", flexDirection: "column", gap: 14, animationDelay: "60ms" }}
        >
          <CardHeader
            title={history.name}
            hint={`近 ${history.dates.length} 个交易日收盘`}
            actions={
              <span
                style={{ fontSize: 12, color: "var(--muted)", cursor: "pointer", padding: "3px 8px" }}
                onClick={() => setSelected(null)}
              >
                收起 ×
              </span>
            }
          />
          <SectorHistoryChart data={history} />
        </BaseCard>
      )}
    </>
  );
}
