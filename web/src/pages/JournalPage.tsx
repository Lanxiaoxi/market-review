import { useState } from "react";
import PageHeader from "@/components/layout/PageHeader";
import CardHeader from "@/components/layout/CardHeader";
import BaseCard from "@/components/common/BaseCard";
import PillButton from "@/components/common/PillButton";
import OrderForm from "@/components/journal/OrderForm";
import OrderCard from "@/components/journal/OrderCard";
import OrderDrawer from "@/components/journal/OrderDrawer";
import { useCountUp } from "@/hooks/useCountUp";
import { useJournalQuery } from "@/hooks/useJournal";
import type { TradeOrder } from "@/types/journal";

/** 汇总指标块（与自选页同构） */
function Metric({
  value,
  label,
  format,
  color,
}: {
  value: number;
  label: string;
  format: (v: number) => string;
  color?: string;
}) {
  const animated = useCountUp(value);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span
        className="num"
        style={{
          fontSize: 30,
          fontWeight: 600,
          letterSpacing: -0.5,
          lineHeight: "38px",
          color: color ?? "var(--ink)",
        }}
      >
        {format(animated)}
      </span>
      <span style={{ fontSize: 12, color: "var(--muted)" }}>{label}</span>
    </div>
  );
}

/** 累计盈亏：后端为元口径，此处换算为万元展示 */
const fmtTotalPnl = (v: number) =>
  `${v >= 0 ? "+" : ""}${(v / 10000).toFixed(2)}万`;

export default function JournalPage() {
  const { data } = useJournalQuery();
  const [showForm, setShowForm] = useState(false);
  const [selected, setSelected] = useState<TradeOrder | null>(null);

  const items = data?.items ?? [];
  const summary = data?.summary;

  return (
    <>
      <PageHeader title="订单复盘" sub="记录每一笔交易 · 复盘开平仓逻辑与执行质量">
        <PillButton
          onClick={() => setShowForm((v) => !v)}
          style={{
            background: showForm ? "var(--active-bg)" : "var(--chip-bg)",
            color: "var(--accent)",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
            <rect x="9" y="4" width="2" height="12" rx="1" fill="currentColor" />
            <rect x="4" y="9" width="12" height="2" rx="1" fill="currentColor" />
          </svg>
          {showForm ? "收起表单" : "新建订单"}
        </PillButton>
      </PageHeader>

      {/* 新建订单（展开式表单，交互与自选页一致） */}
      {showForm && (
        <BaseCard className="mr-enter">
          <CardHeader title="新建订单" hint="标的名 · 截图 · 盈亏金额 · 开平仓逻辑为必填" />
          <div style={{ marginTop: 16 }}>
            <OrderForm
              initial={null}
              onDone={() => setShowForm(false)}
              onCancel={() => setShowForm(false)}
            />
          </div>
        </BaseCard>
      )}

      {/* 复盘统计卡 */}
      <BaseCard
        className="mr-enter"
        style={{
          padding: "20px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          animationDelay: "60ms",
        }}
      >
        <Metric value={summary?.total ?? 0} label="总订单" format={(v) => `${v.toFixed(0)} 笔`} />
        <Metric
          value={summary?.winRate ?? 0}
          label="胜率"
          format={(v) => `${v.toFixed(1)}%`}
        />
        <Metric
          value={summary?.winCount ?? 0}
          label="盈利 / 亏损笔数"
          format={(v) =>
            `${v.toFixed(0)} / ${(summary?.lossCount ?? 0).toFixed(0)}`
          }
        />
        <Metric
          value={summary?.totalPnl ?? 0}
          label="累计盈亏（万元）"
          format={fmtTotalPnl}
          color={(summary?.totalPnl ?? 0) >= 0 ? "var(--up)" : "var(--down)"}
        />
      </BaseCard>

      {/* 订单列表 */}
      <BaseCard
        className="mr-enter"
        style={{ display: "flex", flexDirection: "column", gap: 14, animationDelay: "120ms" }}
      >
        <CardHeader title="订单记录" hint="点击卡片查看详情 · 按订单日期倒序" />
        {items.length === 0 ? (
          <div style={{ padding: "36px 20px", textAlign: "center" }}>
            <span style={{ fontSize: 13, color: "var(--muted-strong)" }}>
              暂无复盘记录，点击右上角「新建订单」记录你的第一笔交易
            </span>
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(400px, 1fr))",
              gap: 12,
            }}
          >
            {items.map((o) => (
              <OrderCard key={o.id} order={o} onOpen={setSelected} />
            ))}
          </div>
        )}
      </BaseCard>

      {/* 详情抽屉（可编辑 / 删除） */}
      <OrderDrawer
        order={selected}
        onClose={() => setSelected(null)}
        onDeleted={() => setSelected(null)}
      />
    </>
  );
}
