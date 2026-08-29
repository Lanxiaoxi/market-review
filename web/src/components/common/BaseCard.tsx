import type { ReactNode, HTMLAttributes } from "react";
import styles from "./BaseCard.module.css";

interface BaseCardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export default function BaseCard({ children, className, ...rest }: BaseCardProps) {
  const cls = className ? `${styles.card} ${className}` : styles.card;
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}