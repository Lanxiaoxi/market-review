import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import styles from "./Segmented.module.css";

export interface SegmentedOption {
  label: string;
  value: string;
}

interface SegmentedProps {
  options: SegmentedOption[];
  value?: string;
  onChange?: (value: string) => void;
  /** 无障碍标签（同一页面多个分段控件需要区分） */
  ariaLabel?: string;
}

export default function Segmented({
  options,
  value,
  onChange,
  ariaLabel = "切换周期",
}: SegmentedProps) {
  // 受控模式（传入 value）时以 value 为准；非受控时内部兜底。
  // 内部 state 只在非受控场景被读取，无需用 effect 同步。
  const [internal, setInternal] = useState(options[0]?.value ?? "");
  const active = value !== undefined ? value : internal;

  const btnRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const [indicator, setIndicator] = useState({ left: 0, width: 0, ready: false });

  // 测量选中段位置，驱动指示块位移（250ms spring 过渡）
  const measure = useCallback(() => {
    const idx = options.findIndex((o) => o.value === active);
    const el = btnRefs.current[idx < 0 ? 0 : idx];
    if (!el) return;
    setIndicator({ left: el.offsetLeft, width: el.offsetWidth, ready: true });
  }, [active, options]);

  useLayoutEffect(measure, [measure]);

  // 字体加载 / 容器尺寸变化后重新测量，避免指示块错位
  useEffect(() => {
    window.addEventListener("resize", measure);
    const fonts = (document as Document & { fonts?: FontFaceSet }).fonts;
    fonts?.ready.then(measure).catch(() => undefined);
    return () => window.removeEventListener("resize", measure);
  }, [measure]);

  return (
    <span className={styles.segmented} role="tablist" aria-label={ariaLabel}>
      <span
        className={`${styles.indicator} ${indicator.ready ? styles.indicatorReady : ""}`}
        style={{ transform: `translateX(${indicator.left}px)`, width: indicator.width }}
      />
      {options.map((opt, i) => (
        <button
          key={opt.value}
          ref={(el) => {
            btnRefs.current[i] = el;
          }}
          role="tab"
          type="button"
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
