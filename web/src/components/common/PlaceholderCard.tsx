import type { ReactNode } from "react";
import styles from "./PlaceholderCard.module.css";

interface PlaceholderCardProps {
  text?: string;
  icon?: ReactNode;
  children?: ReactNode;
}

const PlusIcon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="9" y="4" width="2" height="12" rx="1" fill="var(--placeholder-icon)" />
    <rect x="4" y="9" width="12" height="2" rx="1" fill="var(--placeholder-icon)" />
  </svg>
);

export default function PlaceholderCard({ text = "选择图表", icon, children }: PlaceholderCardProps) {
  return (
    <div className={styles.card}>
      {children ? (
        children
      ) : (
        <>
          {icon ?? <PlusIcon />}
          <span className={styles.text}>{text}</span>
        </>
      )}
    </div>
  );
}