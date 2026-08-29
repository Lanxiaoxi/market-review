import type { MarketBreadth } from "@/types/market";

/**
 * 市场宽度表格（今日总览 / 历史复盘共用）
 *
 * 结构（对应设计稿「市场宽度表格视觉优化」）：
 * 1. 卡头：标题 + 全市场家数
 * 2. 汇总堆叠条（红/灰/绿）+ 50% 多空参考刻度
 * 3. 四列表格：状态（色点+名）｜ 分布（0–100% 统一轨道条）｜ 占比 ｜ 家数
 * 4. 可选：成交额指标（24px）+ 涨停/跌停对等指标块（竖发丝线分隔）
 *
 * 设计令牌全部来自 tokens.css，无阴影、无渐变；数字统一 tabular-nums。
 */

/** 成交额统一显示为「xxx亿」：后端可能返回 "2.12万亿"，这里转成 "21200亿" */
function turnoverToYi(turnover?: string): string {
  if (!turnover) return "—";
  const m = turnover.match(/^([\d.]+)万亿$/);
  if (m) return `${Math.round(parseFloat(m[1]) * 10000).toLocaleString("zh-CN")}亿`;
  return turnover; // 后端已是 "xxxx亿" 格式
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
  const count = (v?: number) => (v == null ? "—" : v.toLocaleString());

  const rows = [
    { key: "up", label: "上涨", color: "var(--up)", pctColor: "var(--up)", value: up, valuePct: breadth?.upPct },
    { key: "flat", label: "平盘", color: "var(--series-base)", pctColor: "var(--muted)", value: flat, valuePct: breadth?.flatPct },
    { key: "down", label: "下跌", color: "var(--down)", pctColor: "var(--down)", value: down, valuePct: breadth?.downPct },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* 卡头：标题 + 全市场家数 */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>市场宽度</span>
        <span className="num" style={{ fontSize: 12, color: "var(--muted)" }}>全市场 {count(total)} 家</span>
      </div>

      {/* 汇总堆叠条 + 50% 多空参考刻度（刻度在条正下方，一眼读出多空力量对比） */}
      <div style={{ position: "relative", paddingBottom: 6 }}>
        <div style={{ display: "flex", height: 12, borderRadius: 4, overflow: "hidden", background: "var(--grid)" }}>
          <span style={{ width: `${(up / total) * 100}%`, background: "var(--up)" }} />
          <span style={{ width: `${(flat / total) * 100}%`, background: "var(--series-base)" }} />
          <span style={{ width: `${(down / total) * 100}%`, background: "var(--down)" }} />
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
      {rows.map((r) => {
        const p = r.valuePct ?? 0;
        return (
          <div key={r.key} style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <div style={{ width: COL_STATE, display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 6, height: 6, borderRadius: 9999, background: r.color, flex: "0 0 auto" }} />
              <span style={{ fontSize: 13, color: "var(--ink)" }}>{r.label}</span>
            </div>
            <div style={{ flex: 1, height: 8, borderRadius: 4, background: "var(--grid)" }}>
              <span
                style={{ display: "block", height: 8, width: `${Math.min(p, 100)}%`, borderRadius: p < 5 ? 2 : 4, background: r.color }}
              />
            </div>
            <span className="num" style={{ width: COL_PCT, fontSize: 13, fontWeight: 500, color: r.pctColor, textAlign: "right" }}>
              {pct(r.valuePct)}
            </span>
            <span className="num" style={{ width: COL_COUNT, fontSize: 13, fontWeight: 500, color: "var(--ink)", textAlign: "right" }}>
              {count(r.value)}
            </span>
          </div>
        );
      })}

      {/* 成交额 + 涨停/跌停（今日总览页；历史页快照头部已展示则省略） */}
      {showTurnover && (
        <>
          <div style={{ height: 1, background: "var(--border)" }} />
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>成交额</span>
            <span className="num" style={{ fontSize: 24, fontWeight: 600, color: "var(--ink)", lineHeight: 1.2 }}>
              {turnoverToYi(breadth?.turnover)}
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "stretch" }}>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>涨停</span>
              <span className="num" style={{ fontSize: 19, fontWeight: 600, color: "var(--up)", lineHeight: "26px" }}>
                {breadth?.limitUpCount ?? "—"}
              </span>
            </div>
            <span style={{ width: 1, background: "var(--border)" }} />
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>跌停</span>
              <span className="num" style={{ fontSize: 19, fontWeight: 600, color: "var(--down)", lineHeight: "26px" }}>
                {breadth?.limitDownCount ?? "—"}
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
