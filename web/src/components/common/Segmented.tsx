import { useState } from "react";
import styles from "./Segmented.module.css";

export interface SegmentedOption {
  label: string;
  value: string;
}

interface SegmentedProps {
  options: SegmentedOption[];
  value?: string;
  onChange?: (value: string) => void;
}

export default function Segmented({ options, value, onChange }: SegmentedProps) {
  // 受控模式（传入 value）时以 value 为准；非受控时内部兜底。
  // 内部 state 只在非受控场景被读取，无需用 effect 同步。
  const [internal, setInternal] = useState(options[0]?.value ?? "");
  const active = value !== undefined ? value : internal;

  return (
    <span className={styles.segmented} role="tablist" aria-label="切换周期">
      {options.map((opt) => (
        <button
          key={opt.value}
          role="tab"
          aria-selected={active === opt.value}
          className={`${styles.seg} ${active === opt.value ? styles.segActive : ""}`}
          onClick={() => {
            setInternal(opt.value);
            onChange?.(opt.value);
          }}
        >
          {opt.label}
        </button>
      ))}
    </span>
  );
}
