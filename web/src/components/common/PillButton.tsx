import type { ReactNode, ButtonHTMLAttributes } from "react";
import styles from "./PillButton.module.css";

interface PillButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
}

export default function PillButton({ children, className, ...rest }: PillButtonProps) {
  const cls = className ? `${styles.btn} ${className}` : styles.btn;
  return (
    <button className={cls} {...rest}>
      {children}
    </button>
  );
}