import { useEffect, useRef, useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import CardHeader from "@/components/layout/CardHeader";
import BaseCard from "@/components/common/BaseCard";
import Segmented from "@/components/common/Segmented";
import { RowSparkline } from "@/components/common/DataTable";
import SectorHistoryChart from "@/components/charts/SectorHistoryChart";
import { useSectors, useSectorHistory } from "@/hooks/useSectors";
import type { SectorItem } from "@/types/market";

/** 异动标记：连涨/连跌天数、10 日新高/新低 */
function MoveBadge({ item }: { item: { upDays?: number; downDays?: number; newHigh10d?: boolean; newLow10d?: boolean } }) {
  const badges: { text: string; color: string; bg: string }[] = [];
  if ((item.upDays ?? 0) >= 3) {
    badges.push({ text: `连涨${item.upDays}天`, color: "var(--up)", bg: "var(--active-bg)" });
  }
  if ((item.downDays ?? 0) >= 3) {
    badges.push({ text: `连跌${item.downDays}天`, color: "var(--down)", bg: "var(--active-bg)" });
  }
  if (item.newHigh10d) {
    badges.push({ text: "10日新高", color: "var(--accent)", bg: "var(--active-bg)" });
  }
  if (item.newLow10d) {
    badges.push({ text: "10日新低", color: "var(--accent)", bg: "var(--active-bg)" });
  }
  if (badges.length === 0) return null;
  return (
    <span style={{ display: "inline-flex", gap: 4, flexWrap: "wrap" }}>
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

/** 板块行（涨幅榜/跌幅榜共用），点击查看历史走势 */
function SectorRow({
  s,
  selected,
  onSelect,
  topBadge,
}: {
  s: SectorItem;
  selected: string | null;
  onSelect: (code: string | null) => void;
  /** 区间领涨/领跌 TOP 徽标（前 5 名） */
  topBadge?: string;
}) {
  const isUp = s.pct >= 0;
  const active = selected === s.code;
  return (
    <div
      onClick={() => onSelect(s.code ?? null)}
      title="查看历史走势"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 6px",
        cursor: "pointer",
        background: active ? "var(--active-bg)" : "transparent",
        borderRadius: 8,
        marginLeft: -6,
      }}
    >
      <span style={{ flex: "0 0 88px", fontSize: 13, fontWeight: 500, color: "var(--ink)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.name}</span>
      {topBadge && (
        <span
          style={{
            flex: "0 0 auto",
            fontSize: 11,
            padding: "1px 5px",
            borderRadius: 4,
            border: "1px solid var(--border-hover)",
            color: "var(--muted-strong)",
            whiteSpace: "nowrap",
          }}
        >
          {topBadge}
        </span>
      )}
      <span className="num" style={{
        flex: "0 0 72px", fontSize: 13, fontWeight: 500, textAlign: "right",
        color: isUp ? "var(--up)" : "var(--down)",
      }}>
        {isUp ? "+" : ""}{s.pct.toFixed(2)}%
      </span>
      <span style={{ flex: "0 0 auto", display: "flex", alignItems: "center" }}>
        <MoveBadge item={s} />
      </span>
      <span style={{ flex: 1, fontSize: 12, color: "var(--muted-strong)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.leading}</span>
      <RowSparkline points={s.sparkline} isUp={isUp} />
    </div>
  );
}

export default function SectorPage() {
  // 动量区间：1=当日 / 5=近5日 / 10=近10日 / 20=近20日
  const [range, setRange] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  // 详情时间范围：30 / 90 / 250 日
  const [detailDays, setDetailDays] = useState(90);
  const { data } = useSectors("pct", range);
  const { data: history } = useSectorHistory(selected, detailDays);
  const detailRef = useRef<HTMLDivElement>(null);

  // 点击板块后自动滚动到详情卡（卡片在页面上方）
  useEffect(() => {
    if (selected && detailRef.current) {
      detailRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [selected]);

  const rangeLabel = range === 1 ? "当日" : `近${range}日`;
  // 左涨幅榜（>=0 降序）/ 右跌幅榜（<0 升序）
  const items = data ?? [];
  const gainers = items.filter((s) => s.pct >= 0);
  const losers = items.filter((s) => s.pct < 0).reverse();

  return (
    <>
      <PageHeader title="板块轮动" sub="捕捉当日热点与异动 · 申万一级行业涨跌排名" />

      {/* 板块详情（点击行后出现在上方） */}
      {selected && history && (
        <div ref={detailRef} style={{ scrollMarginTop: 16 }}>
          <BaseCard
            className="mr-enter"
            style={{ display: "flex", flexDirection: "column", gap: 14, animationDelay: "0ms" }}
          >
            <CardHeader
              title={history.name}
              hint={`近 ${history.dates.length} 个交易日收盘`}
              actions={
                <>
                  <Segmented
                    options={[
                      { label: "近30日", value: "30" },
                      { label: "近90日", value: "90" },
                      { label: "近250日", value: "250" },
                    ]}
                    value={String(detailDays)}
                    onChange={(v) => setDetailDays(Number(v))}
                    ariaLabel="详情时间范围"
                  />
                  <span
                    style={{ fontSize: 12, color: "var(--muted)", cursor: "pointer", padding: "3px 8px" }}
                    onClick={() => setSelected(null)}
                  >
                    收起 ×
                  </span>
                </>
              }
            />
            <SectorHistoryChart data={history} />
          </BaseCard>
        </div>
      )}

      <BaseCard
        className="mr-enter"
        style={{ display: "flex", flexDirection: "column", gap: 14 }}
      >
        <CardHeader
          title={`行业板块 · ${rangeLabel}涨跌`}
          hint="左涨幅榜 / 右跌幅榜 · 单位 % · 点击板块查看历史走势"
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

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          {/* 左：涨幅榜 */}
          <div style={{ minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--up)" }}>涨幅榜</span>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>{gainers.length} 个板块</span>
            </div>
            {gainers.length === 0 ? (
              <div style={{ padding: "24px 12px", textAlign: "center" }}>
                <span style={{ fontSize: 13, color: "var(--muted-strong)" }}>暂无上涨板块</span>
              </div>
            ) : (
              gainers.map((s, i) => (
                <SectorRow key={s.code ?? s.name} s={s} selected={selected} onSelect={setSelected} topBadge={i < 5 ? "领涨TOP" : undefined} />
              ))
            )}
          </div>

          {/* 右：跌幅榜 */}
          <div style={{ minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--down)" }}>跌幅榜</span>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>{losers.length} 个板块</span>
            </div>
            {losers.length === 0 ? (
              <div style={{ padding: "24px 12px", textAlign: "center" }}>
                <span style={{ fontSize: 13, color: "var(--muted-strong)" }}>暂无下跌板块</span>
              </div>
            ) : (
              losers.map((s, i) => (
                <SectorRow key={s.code ?? s.name} s={s} selected={selected} onSelect={setSelected} topBadge={i < 5 ? "领跌TOP" : undefined} />
              ))
            )}
          </div>
        </div>
      </BaseCard>
    </>
  );
}
