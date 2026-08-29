import type { ReactNode } from "react";
import styles from "./DataTable.module.css";

export interface DataColumn {
  label: string;
  className?: string;
}

interface DataTableProps {
  columns: DataColumn[];
  children: ReactNode;
}

export default function DataTable({ columns, children }: DataTableProps) {
  return (
    <div>
      <div className={styles.headerRow}>
        {columns.map((col) => (
          <span key={col.label} className={`${styles.cell} ${col.className ?? ""}`}>
            {col.label}
          </span>
        ))}
      </div>
      {children}
    </div>
  );
}

/* 导出行内辅助组件 */
export function RowSparkline({
  points,
  isUp,
}: {
  points: number[];
  isUp: boolean;
}) {
  if (!points || points.length < 2) return null; // 空数据不渲染（数据源不可用时列留空）
  return (
    <svg className={styles.rowSpark} viewBox="0 0 120 24" fill="none">
      <polyline
        points={points.map((v, i) => `${2 + i * 11.6},${v}`).join(" ")}
        stroke={isUp ? "var(--up)" : "var(--down)"}
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}