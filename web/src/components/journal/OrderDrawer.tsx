import { useEffect, useRef, useState } from "react";
import PillButton from "@/components/common/PillButton";
import OrderForm from "./OrderForm";
import { useDeleteOrder } from "@/hooks/useJournal";
import type { TradeOrder } from "@/types/journal";
import styles from "./OrderReview.module.css";

interface OrderDrawerProps {
  order: TradeOrder | null;
  onClose: () => void;
  /** 订单删除成功后回调（父级负责关抽屉） */
  onDeleted?: (id: number) => void;
}

const fmtWan = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}万`;

function DetailStat({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: 12, color: "var(--muted)" }}>{label}</span>
      <span className="num" style={{ fontSize: 15, fontWeight: 600, color: "var(--ink)" }}>
        {value}
      </span>
    </div>
  );
}

export default function OrderDrawer({ order, onClose, onDeleted }: OrderDrawerProps) {
  const [current, setCurrent] = useState<TradeOrder | null>(order);
  const [editing, setEditing] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const timerRef = useRef<number | null>(null);
  const deleteMut = useDeleteOrder();

  // 订单切换 / 关闭时重置内部态
  useEffect(() => {
    setCurrent(order);
    setEditing(false);
    setConfirmDel(false);
  }, [order]);

  // Esc：编辑中先退出编辑，否则关闭抽屉
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (editing) setEditing(false);
      else onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editing, onClose]);

  useEffect(
    () => () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    },
    []
  );

  if (!current) return null;

  const isUp = current.pnl >= 0;
  const pnlColor = isUp ? "var(--up)" : "var(--down)";

  const handleDelete = () => {
    if (!confirmDel) {
      setConfirmDel(true);
      timerRef.current = window.setTimeout(() => setConfirmDel(false), 3000);
      return;
    }
    if (timerRef.current) window.clearTimeout(timerRef.current);
    deleteMut.mutate(current.id, {
      onSuccess: () => onDeleted?.(current.id),
    });
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.panel}
        role="dialog"
        aria-label="订单详情"
        onClick={(e) => e.stopPropagation()}
      >
        <header className={styles.panelHeader}>
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <span style={{ fontSize: 15, fontWeight: 600, color: "var(--ink)" }}>
              {editing ? "编辑订单" : current.symbol}
            </span>
            {!editing && (
              <span style={{ fontSize: 11, color: "var(--muted)" }}>
                {current.tradeDate} · {current.openLogic} → {current.closeLogic}
              </span>
            )}
          </div>
          <button
            className={styles.iconBtn}
            onClick={onClose}
            title="关闭（Esc）"
            aria-label="关闭"
          >
            ✕
          </button>
        </header>

        <div className={styles.panelBody}>
          {editing ? (
            <OrderForm
              initial={current}
              onDone={(updated) => {
                if (updated) setCurrent(updated);
                setEditing(false);
              }}
              onCancel={() => setEditing(false)}
            />
          ) : (
            <>
              {/* 大图预览 */}
              <div>
                <a
                  href={current.imageUrl}
                  target="_blank"
                  rel="noreferrer"
                  title="新标签页查看原图"
                  style={{ display: "block" }}
                >
                  <img
                    src={current.imageUrl}
                    alt={`${current.symbol} 订单截图`}
                    style={{
                      width: "100%",
                      maxHeight: 340,
                      objectFit: "contain",
                      borderRadius: 10,
                      border: "1px solid var(--border)",
                      background: "var(--chip-bg)",
                    }}
                  />
                </a>
                <span className={styles.hintText}>点击图片可在新标签页查看原图</span>
              </div>

              {/* 金额概览 */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 16px",
                  borderRadius: 10,
                  background: "var(--chip-bg)",
                }}
              >
                <DetailStat label="订单日期" value={current.tradeDate} />
                <DetailStat label="盈亏类型" value={isUp ? "盈利" : "亏损"} />
                <div style={{ display: "flex", flexDirection: "column", gap: 2, alignItems: "flex-end" }}>
                  <span className="num" style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.5, color: pnlColor, lineHeight: 1.1 }}>
                    {fmtWan(current.pnl)}
                  </span>
                  <span style={{ fontSize: 11, color: "var(--muted)" }}>盈亏（万元）</span>
                </div>
              </div>

              {/* 开平仓逻辑 */}
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 12, color: "var(--muted)", width: 60 }}>开仓逻辑</span>
                  <span className={styles.tag}>{current.openLogic}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 12, color: "var(--muted)", width: 60 }}>平仓逻辑</span>
                  <span className={styles.tag}>{current.closeLogic}</span>
                </div>
              </div>

              {/* 订单笔记 */}
              {current.note && (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>订单笔记</span>
                  <p
                    style={{
                      fontSize: 13,
                      color: "var(--ink)",
                      lineHeight: 1.8,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      background: "var(--bg-content)",
                      border: "1px solid var(--border)",
                      borderRadius: 10,
                      padding: "12px 14px",
                    }}
                  >
                    {current.note}
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* 底部操作（查看态） */}
        {!editing && (
          <footer
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "14px 22px 18px",
              borderTop: "1px solid var(--border)",
              flexShrink: 0,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              {confirmDel ? (
                <PillButton
                  onClick={handleDelete}
                  disabled={deleteMut.isPending}
                  style={{ background: "var(--up)", opacity: deleteMut.isPending ? 0.7 : 1 }}
                >
                  {deleteMut.isPending ? "删除中…" : "确认删除？"}
                </PillButton>
              ) : (
                <button
                  type="button"
                  onClick={handleDelete}
                  style={{
                    border: "1px solid var(--border)",
                    background: "transparent",
                    color: "var(--muted-strong)",
                    fontSize: 12,
                    borderRadius: 9999,
                    padding: "7px 14px",
                    cursor: "pointer",
                    fontFamily: "inherit",
                  }}
                >
                  删除订单
                </button>
              )}
              {deleteMut.isError && (
                <span className={styles.formError}>删除失败，请重试</span>
              )}
              <span className={styles.hintText}>删除将同时移除该截图</span>
            </div>

            <PillButton onClick={() => setEditing(true)}>编辑</PillButton>
          </footer>
        )}
      </div>
    </div>
  );
}
