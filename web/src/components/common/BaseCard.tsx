import type { ReactNode, HTMLAttributes } from "react";
import styles from "./BaseCard.module.css";

interface BaseCardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  /** 关闭组件内置内边距（默认开启） */
  plain?: boolean;
  /** 开启 hover 微动效（默认关闭） */
  interactive?: boolean;
}

export default function BaseCard({
  children,
  className,
  plain = false,
  interactive = false,
  ...rest
}: BaseCardProps) {
  const cls = [styles.card, plain && styles.plain, interactive && styles.interactive, className]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}