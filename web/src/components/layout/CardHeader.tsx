import type { ReactNode } from "react";
import styles from "./CardHeader.module.css";

interface CardHeaderProps {
  title: string;
  /** 右侧说明文字（如「申万一级行业 · 单位 %」） */
  hint?: string;
  /** 右侧操作区（分段控件、按钮等），优先级高于 hint 时只传 actions */
  actions?: ReactNode;
}

/** 卡片标题栏：替代各页面重复手写的「标题 + 右侧说明/操作」组合 */
export default function CardHeader({ title, hint, actions }: CardHeaderProps) {
  return (
    <div className={styles.header}>
      <span className={styles.title}>{title}</span>
      {(hint || actions) && (
        <div className={styles.right}>
          {hint && <span className={styles.hint}>{hint}</span>}
          {actions}
        </div>
      )}
    </div>
  );
}
