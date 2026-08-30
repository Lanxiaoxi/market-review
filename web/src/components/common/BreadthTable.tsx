import type { MarketBreadth } from "@/types/market";
import { useCountUp } from "@/hooks/useCountUp";

/**
 * 市场宽度表格（今日总览 / 历史复盘共用）
 *
 * 结构（对应设计稿「市场宽度表格视觉优化」）：
 * 1. 卡头：标题 + 全市场家数
 * 2. 汇总堆叠条（红/灰/绿）+ 50% 多空参考刻度
 * 3. 四列表格：状态（色点+名）｜ 分布（0–100% 统一轨道条）｜ 占比 ｜ 家数
 * 4. 可选：成交额指标（30px）+ 涨停/跌停对等指标块（竖发丝线分隔）
 *
 * 设计令牌全部来自 tokens.css，无阴影、无渐变；数字统一 tabular-nums。
 * v2：条形入场生长（mr-grow）+ 数字滚动（useCountUp）。
 */

/** 成交额统一显示为「xxx亿」：后端可能返回 "2.12万亿"，这里转成 "21200亿" */
function turnoverToYi(turnover?: string): string {
  if (!turnover) return "—";
  const m = turnover.match(/^([\d.]+)万亿$/);
  if (m) return `${Math.round(parseFloat(m[1]) * 10000).toLocaleString("zh-CN")}亿`;
  return turnover; // 后端已是 "xxxx亿" 格式
}

/** 数字滚动：整数场景（家数、涨停数） */
function AnimatedInt({ value }: { value: number }) {
  const v = useCountUp(value);
  return <>{Math.round(v).toLocaleString("zh-CN")}</>;
}

/** 数字滚动：保留单位（如 "11,246亿"） */
function AnimatedWithUnit({ text }: { text: string }) {
  // 非字符串（undefined/null）时直接原样输出，避免 .replace 抛错
  const num = typeof text === "string" ? parseFloat(text.replace(/[^\d.]/g, "")) : NaN;
  const v = useCountUp(Number.isFinite(num) ? num : 0);
  if (typeof text !== "string" || !Number.isFinite(num)) return <>{text}</>;
  const unit = text.replace(/[\d,.]/g, "");
  return (
    <>
      {v.toLocaleString("zh-CN", { maximumFractionDigits: 0 })}
      {unit}
    </>
  );
}

interface BreadthTableProps {
  breadth?: MarketBreadth | null;
  /** 是否渲染底部成交额 + 涨跌停指标块（历史页快照头部已展示，可省略） */
  showTurnover?: boolean;
}

/** 列宽：状态 72px ｜ 分布条 flex ｜ 占比 52px ｜ 家数 64px（后两列右对齐） */
const COL_STATE = 72;
const COL_PCT = 52;
const COL_COUNT = 64;

export default function BreadthTable({ breadth, showTurnover = false }: BreadthTableProps) {
  const up = breadth?.up ?? 0;
  const flat = breadth?.flat ?? 0;
  const down = breadth?.down ?? 0;
  const total = up + flat + down || 1;

  const pct = (v?: number) => (v == null ? "—" : `${v.toFixed(1)}%`);

  const rows = [
    { key: "up", label: "上涨", color: "var(--up)", pctColor: "var(--up)", value: up, valuePct: breadth?.upPct },
    { key: "flat", label: "平盘", color: "var(--series-base)", pctColor: "var(--muted)", value: flat, valuePct: breadth?.flatPct },
    { key: "down", label: "下跌", color: "var(--down)", pctColor: "var(--down)", value: down, valuePct: breadth?.downPct },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* 卡头：标题 + 全市场家数 */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: "var(--ink)", letterSpacing: -0.2 }}>
          市场宽度
        </span>
        <span className="num" style={{ fontSize: 12, color: "var(--muted)" }}>
          全市场 <AnimatedInt value={total} /> 家
        </span>
      </div>

      {/* 无有效数据占位 */}
      {!breadth && (
        <div style={{ padding: "28px 0", textAlign: "center" }}>
          <span style={{ fontSize: 13, color: "var(--muted-strong)" }}>暂无有效数据</span>
        </div>
      )}

      {breadth && (
        <>
          {/* 汇总堆叠条 + 50% 多空参考刻度 */}
          <div style={{ position: "relative", paddingBottom: 6 }}>
            <div
              style={{
                display: "flex",
                height: 12,
                borderRadius: 4,
                overflow: "hidden",
                background: "var(--grid)",
              }}
            >
              {[
                { w: (up / total) * 100, c: "var(--up)" },
                { w: (flat / total) * 100, c: "var(--series-base)" },
                { w: (down / total) * 100, c: "var(--down)" },
              ].map((seg, i) => (
                <span
                  key={i}
                  className="mr-grow"
                  style={{
                    width: `${seg.w}%`,
                    background: seg.c,
                    display: "block",
                    height: 12,
                    animationDelay: `${i * 80}ms`,
                  }}
                />
              ))}
            </div>
            <span
              title="50% 多空分界"
              style={{ position: "absolute", left: "50%", bottom: 0, width: 1, height: 6, background: "var(--placeholder-icon)" }}
            />
          </div>

          {/* 表头 */}
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span style={{ width: COL_STATE, fontSize: 12, color: "var(--muted)" }}>状态</span>
            <span style={{ flex: 1, fontSize: 12, color: "var(--muted)" }}>分布</span>
            <span style={{ width: COL_PCT, fontSize: 12, color: "var(--muted)", textAlign: "right" }}>占比</span>
            <span style={{ width: COL_COUNT, fontSize: 12, color: "var(--muted)", textAlign: "right" }}>家数</span>
          </div>
          <div style={{ height: 1, background: "var(--border)" }} />

          {/* 数据行：分布条以 0–100% 为统一轨道，填充长度 = 该状态占比 */}
          {rows.map((r, i) => {
            const p = r.valuePct ?? 0;
            return (
              <div key={r.key} style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <div style={{ width: COL_STATE, display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ width: 6, height: 6, borderRadius: 9999, background: r.color, flex: "0 0 auto" }} />
                  <span style={{ fontSize: 13, color: "var(--ink)" }}>{r.label}</span>
                </div>
                <div
                  style={{
                    flex: 1,
                    minWidth: 0,
                    height: 8,
                    borderRadius: 4,
                    background: "var(--grid)",
                    overflow: "hidden",
                  }}
                >
                  <span
                    className="mr-grow"
                    style={{
                      display: "block",
                      height: 8,
                      width: `${Math.min(p, 100)}%`,
                      borderRadius: 4,
                      background: r.color,
                      animationDelay: `${200 + i * 80}ms`,
                    }}
                  />
                </div>
                <span
                  className="num"
                  style={{ width: COL_PCT, fontSize: 13, fontWeight: 500, color: r.pctColor, textAlign: "right" }}
                >
                  {pct(r.valuePct)}
                </span>
                <span
                  className="num"
                  style={{ width: COL_COUNT, fontSize: 13, fontWeight: 500, color: "var(--ink)", textAlign: "right" }}
                >
                  <AnimatedInt value={r.value} />
                </span>
              </div>
            );
          })}

          {/* 成交额 + 涨停/跌停（今日总览页） */}
          {showTurnover && (
            <>
              <div style={{ height: 1, background: "var(--border)" }} />
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                <span style={{ fontSize: 12, color: "var(--muted)" }}>成交额</span>
                <span
                  className="num"
                  style={{ fontSize: 30, fontWeight: 600, color: "var(--ink)", letterSpacing: -0.6, lineHeight: "38px" }}
                >
                  <AnimatedWithUnit text={turnoverToYi(breadth?.turnover)} />
                </span>
                {breadth?.turnoverChangeYi != null && breadth?.turnoverChangePct != null && (
                  <span
                    className="num"
                    style={{
                      fontSize: 12,
                      fontWeight: 500,
                      color:
                        breadth.turnoverChangeYi > 0
                          ? "var(--up)"
                          : breadth.turnoverChangeYi < 0
                            ? "var(--down)"
                            : "var(--muted)",
                    }}
                  >
                    较上一交易日{" "}
                    {breadth.turnoverChangeYi > 0
                      ? "+"
                      : breadth.turnoverChangeYi < 0
                        ? "-"
                        : ""}
                    {Math.abs(breadth.turnoverChangeYi).toLocaleString("zh-CN", { maximumFractionDigits: 0 })}亿
                    （{breadth.turnoverChangeYi > 0 ? "+" : ""}
                    {breadth.turnoverChangePct.toFixed(2)}%）
                  </span>
                )}
              </div>
              <div style={{ display: "flex", alignItems: "stretch" }}>
                <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>涨停</span>
                  <span className="num" style={{ fontSize: 19, fontWeight: 600, color: "var(--up)", lineHeight: "26px" }}>
                    <AnimatedInt value={breadth?.limitUpCount ?? 0} />
                  </span>
                </div>
                <span style={{ width: 1, background: "var(--border)" }} />
                <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>跌停</span>
                  <span className="num" style={{ fontSize: 19, fontWeight: 600, color: "var(--down)", lineHeight: "26px" }}>
                    <AnimatedInt value={breadth?.limitDownCount ?? 0} />
                  </span>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
