import type { ReactNode } from "react";
import styles from "./PageHeader.module.css";

interface PageHeaderProps {
  title: string;
  sub: string;
  date?: string;
  children?: ReactNode;
}

export default function PageHeader({ title, sub, date, children }: PageHeaderProps) {
  return (
    <div className={styles.header}>
      <div className={styles.headerLeft}>
        <h1 className={styles.pageTitle}>{title}</h1>
        <p className={styles.pageSub}>{sub}</p>
      </div>
      <div className={styles.headerRight}>
        {date && <span className={styles.date}>{date}</span>}
        {children}
      </div>
    </div>
  );
}