import { useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import CardHeader from "@/components/layout/CardHeader";
import BaseCard from "@/components/common/BaseCard";
import DataTable, { RowSparkline } from "@/components/common/DataTable";
import PillButton from "@/components/common/PillButton";
import { useCountUp } from "@/hooks/useCountUp";
import {
  useWatchlistQuery,
  useAddWatchlistItem,
  useDeleteWatchlistItem,
  useUpdateWatchlistItem,
} from "@/hooks/useWatchlist";
import type { WatchlistItem } from "@/types/market";

/** 汇总指标块：30px 数值 + 数字滚动 */
function Metric({
  value,
  label,
  format,
  color,
}: {
  value: number;
  label: string;
  format: (v: number) => string;
  color?: string;
}) {
  const animated = useCountUp(value);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span
        className="num"
        style={{
          fontSize: 30,
          fontWeight: 600,
          letterSpacing: -0.5,
          lineHeight: "38px",
          color: color ?? "var(--ink)",
        }}
      >
        {format(animated)}
      </span>
      <span style={{ fontSize: 12, color: "var(--muted)" }}>{label}</span>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "6px 10px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "#fff",
  fontSize: 13,
  fontFamily: "inherit",
  color: "var(--ink)",
  outline: "none",
  width: 110,
};

const numInputStyle: React.CSSProperties = { ...inputStyle, width: 84, textAlign: "right" };

/** 可编辑行：展开内联表单，保存走 PUT /api/watchlist/{code} */
function EditableRow({
  item,
  onCancel,
}: {
  item: WatchlistItem;
  onCancel: () => void;
}) {
  const update = useUpdateWatchlistItem();
  const [draft, setDraft] = useState({
    price: String(item.price),
    cost: String(item.cost),
    holdingValue: String(item.holdingValue),
    positionPct: String(item.positionPct),
    pnl: String(item.pnl),
  });

  const set = (k: keyof typeof draft) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setDraft((d) => ({ ...d, [k]: e.target.value }));

  const save = () => {
    update.mutate({
      code: item.code,
      patch: {
        price: parseFloat(draft.price) || 0,
        cost: parseFloat(draft.cost) || 0,
        holdingValue: parseFloat(draft.holdingValue) || 0,
        positionPct: parseFloat(draft.positionPct) || 0,
        pnl: parseFloat(draft.pnl) || 0,
      },
    });
    onCancel();
  };

  const busy = update.isPending;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 0", flexWrap: "wrap" }}>
      <span style={{ fontSize: 13, fontWeight: 500, color: "var(--ink)", width: 120 }}>{item.name}</span>
      <input style={numInputStyle} aria-label="现价（元）" value={draft.price} onChange={set("price")} />
      <input style={numInputStyle} aria-label="成本价（元）" value={draft.cost} onChange={set("cost")} />
      <input style={numInputStyle} aria-label="持仓市值（万）" value={draft.holdingValue} onChange={set("holdingValue")} />
      <input style={numInputStyle} aria-label="仓位（%）" value={draft.positionPct} onChange={set("positionPct")} />
      <input style={numInputStyle} aria-label="今日盈亏（万）" value={draft.pnl} onChange={set("pnl")} />
      <PillButton onClick={save} disabled={busy} style={{ opacity: busy ? 0.6 : 1 }}>
        保存
      </PillButton>
      <span
        style={{ fontSize: 12, color: "var(--muted)", cursor: "pointer" }}
        onClick={onCancel}
      >
        取消
      </span>
    </div>
  );
}

export default function WatchlistPage() {
  const { data } = useWatchlistQuery();
  const addMutation = useAddWatchlistItem();
  const deleteMutation = useDeleteWatchlistItem();

  const [showForm, setShowForm] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [cost, setCost] = useState("");
  const [holdingValue, setHoldingValue] = useState("");
  const [positionPct, setPositionPct] = useState("");
  const [editingCode, setEditingCode] = useState<string | null>(null);

  const items = data?.items ?? [];
  const summary = data?.summary;

  const fmtWan = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}万`;

  const handleAdd = () => {
    if (!code.trim() || !name.trim()) return;
    addMutation.mutate({
      code: code.trim().toUpperCase(),
      name: name.trim(),
      price: parseFloat(price) || 0,
      cost: parseFloat(cost) || 0,
      changePct: 0,
      pnl: 0,
      holdingValue: parseFloat(holdingValue) || 0,
      positionPct: parseFloat(positionPct) || 0,
    });
    setCode("");
    setName("");
    setPrice("");
    setCost("");
    setHoldingValue("");
    setPositionPct("");
    setShowForm(false);
  };

  const handleDelete = (c: string) => {
    if (editingCode === c) setEditingCode(null);
    deleteMutation.mutate(c);
  };

  const busy = addMutation.isPending || deleteMutation.isPending;

  return (
    <>
      <PageHeader title="自选跟踪" sub="聚焦自选与盈亏贡献 · 我的自选池">
        <PillButton
          onClick={() => setShowForm((v) => !v)}
          style={{ background: "var(--chip-bg)", color: "var(--muted-strong)" }}
        >
          <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
            <rect x="9" y="4" width="2" height="12" rx="1" fill="var(--muted-strong)" />
            <rect x="4" y="9" width="12" height="2" rx="1" fill="var(--muted-strong)" />
          </svg>
          添加自选
        </PillButton>
      </PageHeader>

      {/* 添加自选表单 */}
      {showForm && (
        <BaseCard style={{ padding: "14px 20px", display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <input style={inputStyle} placeholder="代码 (如 600519.SH)" value={code} onChange={(e) => setCode(e.target.value)} aria-label="股票代码" />
          <input style={inputStyle} placeholder="名称" value={name} onChange={(e) => setName(e.target.value)} aria-label="股票名称" />
          <input style={numInputStyle} placeholder="现价(元)" value={price} onChange={(e) => setPrice(e.target.value)} aria-label="现价（元）" />
          <input style={numInputStyle} placeholder="成本(元)" value={cost} onChange={(e) => setCost(e.target.value)} aria-label="成本价（元）" />
          <input style={numInputStyle} placeholder="市值(万)" value={holdingValue} onChange={(e) => setHoldingValue(e.target.value)} aria-label="持仓市值（万）" />
          <input style={numInputStyle} placeholder="仓位%" value={positionPct} onChange={(e) => setPositionPct(e.target.value)} aria-label="仓位（%）" />
          <PillButton onClick={handleAdd} disabled={busy} style={{ opacity: busy ? 0.6 : 1 }}>
            确认添加
          </PillButton>
          <span
            style={{ fontSize: 12, color: "var(--muted)", cursor: "pointer" }}
            onClick={() => setShowForm(false)}
          >
            取消
          </span>
        </BaseCard>
      )}

      {/* 汇总卡（v2：指标值 30px + 数字滚动 + 入场动效） */}
      <BaseCard
        className="mr-enter"
        style={{ padding: "20px 24px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}
      >
        <Metric value={summary?.totalValue ?? 0} label="总市值" format={(v) => `${v.toFixed(1)}万`} />
        <Metric
          value={summary?.todayPnl ?? 0}
          label="今日盈亏"
          format={fmtWan}
          color={(summary?.todayPnl ?? 0) >= 0 ? "var(--up)" : "var(--down)"}
        />
        <Metric
          value={summary?.holdingPnl ?? 0}
          label="持仓盈亏"
          format={fmtWan}
          color={(summary?.holdingPnl ?? 0) >= 0 ? "var(--up)" : "var(--down)"}
        />
        <Metric value={summary?.position ?? 0} label="仓位" format={(v) => `${v.toFixed(0)}%`} />
      </BaseCard>

      {/* 自选池 */}
      <BaseCard
        className="mr-enter"
        style={{ display: "flex", flexDirection: "column", gap: 14, animationDelay: "120ms" }}
      >
        <CardHeader title="自选池" hint="当日分时 · 盈亏贡献" />
        {items.length === 0 ? (
          <div style={{ padding: "32px 20px", textAlign: "center" }}>
            <span style={{ fontSize: 13, color: "var(--muted-strong)" }}>暂无自选，点击右上角「添加自选」开始跟踪</span>
          </div>
        ) : (
          <DataTable
            columns={[
              { label: "股票", className: "colName" },
              { label: "现价（元）" },
              { label: "涨跌幅" },
              { label: "今日盈亏（万）" },
              { label: "分时走势", className: "colSpark" },
            ]}
          >
            {items.map((w) => {
              if (editingCode === w.code) {
                return <EditableRow key={w.code} item={w} onCancel={() => setEditingCode(null)} />;
              }
              const isUp = w.changePct >= 0;
              return (
                <div key={w.code} style={{ display: "flex", alignItems: "center", padding: "10px 0" }}>
                  <span style={{ fontSize: 13, fontWeight: 500, color: "var(--ink)", width: 120 }}>{w.name}</span>
                  <span className="num" style={{ fontSize: 13, fontWeight: 500, color: "var(--ink)", width: 100, textAlign: "right" }}>
                    {w.price.toFixed(2)}
                  </span>
                  <span className="num" style={{
                    fontSize: 13, fontWeight: 500, width: 80, textAlign: "right",
                    color: isUp ? "var(--up)" : "var(--down)",
                  }}>
                    {isUp ? "+" : ""}{w.changePct.toFixed(2)}%
                  </span>
                  <span className="num" style={{
                    fontSize: 13, fontWeight: 500, width: 100, textAlign: "right",
                    color: w.pnl >= 0 ? "var(--up)" : "var(--down)",
                  }}>
                    {fmtWan(w.pnl)}
                  </span>
                  <RowSparkline points={w.sparkline} isUp={isUp} />
                  {/* 编辑按钮 */}
                  <button
                    onClick={() => setEditingCode(w.code)}
                    title="编辑持仓信息"
                    aria-label={`编辑 ${w.name}`}
                    style={{
                      marginLeft: 8,
                      padding: "3px 10px",
                      borderRadius: 9999,
                      border: "1px solid var(--border)",
                      background: "var(--chip-bg)",
                      color: "var(--muted-strong)",
                      fontSize: 12,
                      cursor: "pointer",
                      fontFamily: "inherit",
                    }}
                  >
                    编辑
                  </button>
                  {/* 删除按钮 */}
                  <button
                    onClick={() => handleDelete(w.code)}
                    disabled={busy}
                    title="移除自选"
                    aria-label={`移除 ${w.name}`}
                    style={{
                      marginLeft: 8,
                      width: 24, height: 24,
                      borderRadius: 9999,
                      border: "none",
                      background: "transparent",
                      color: "var(--muted)",
                      fontSize: 14,
                      cursor: "pointer",
                      fontFamily: "inherit",
                      opacity: busy ? 0.5 : 1,
                    }}
                  >
                    ×
                  </button>
                </div>
              );
            })}
          </DataTable>
        )}
      </BaseCard>
    </>
  );
}
