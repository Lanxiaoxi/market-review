import type { TradeOrder } from "@/types/journal";
import styles from "./OrderReview.module.css";

interface OrderCardProps {
  order: TradeOrder;
  onOpen: (order: TradeOrder) => void;
}

const fmtWan = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}万`;

export default function OrderCard({ order, onOpen }: OrderCardProps) {
  const isUp = order.pnl >= 0;
  const pnlColor = isUp ? "var(--up)" : "var(--down)";

  return (
    <div
      className={styles.orderCard}
      role="button"
      tabIndex={0}
      onClick={() => onOpen(order)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onOpen(order);
      }}
      title={`${order.symbol} · ${order.tradeDate} · 查看详情`}
    >
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <img src={order.imageUrl} alt="" className={styles.cardThumb} loading="lazy" />

        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 7 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {order.symbol}
            </span>
            <span style={{ fontSize: 11, color: "var(--muted)", whiteSpace: "nowrap" }}>
              {order.tradeDate}
            </span>
          </div>
          <div className={styles.tagRow}>
            <span className={styles.tag}>开 · {order.openLogic}</span>
            <span className={styles.tag}>平 · {order.closeLogic}</span>
          </div>
          {order.note && (
            <span
              style={{
                fontSize: 12,
                color: "var(--muted)",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {order.note}
            </span>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 2, flexShrink: 0 }}>
          <span className={`num ${styles.pnlNum}`} style={{ color: pnlColor }}>
            {fmtWan(order.pnl)}
          </span>
          <span style={{ fontSize: 11, color: "var(--muted)" }}>{isUp ? "盈利" : "亏损"}</span>
        </div>
      </div>
    </div>
  );
}
