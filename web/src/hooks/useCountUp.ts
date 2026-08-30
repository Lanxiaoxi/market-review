import { useEffect, useRef, useState } from "react";

/** 系统「减少动态效果」偏好 */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

const easeOutCubic = (p: number) => 1 - Math.pow(1 - p, 3);

/**
 * 数字滚动：0 → target 的 ease-out 过渡，tabular-nums 下不会抖动宽度。
 * 遵循 prefers-reduced-motion，开启时直接返回目标值。
 */
export function useCountUp(target: number, duration = 800): number {
  const reduced = prefersReducedMotion();
  const [value, setValue] = useState(() => (reduced ? target : 0));
  const fromRef = useRef(reduced ? target : 0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const from = fromRef.current;

    // 目标不可计算 / 未变化 / 用户要求减少动效 → 直接落位
    if (!Number.isFinite(target) || from === target || prefersReducedMotion()) {
      fromRef.current = target;
      setValue(target);
      return;
    }

    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const next = from + (target - from) * easeOutCubic(p);
      setValue(next);
      if (p < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = target;
      }
    };
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [target, duration]);

  return value;
}
