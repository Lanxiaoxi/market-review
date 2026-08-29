import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import PageHeader from "@/components/layout/PageHeader";
import IndexCard from "@/components/common/IndexCard";
import BaseCard from "@/components/common/BaseCard";
import Chip from "@/components/common/Chip";
import PillButton from "@/components/common/PillButton";
import BreadthBar from "@/components/charts/BreadthBar";
import { fetchHistory } from "@/api/history";
import type { OverviewData } from "@/types/market";

const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

export default function HistoryPage() {
  // 默认今天（仅作输入框初值；queryDate 为 null 表示尚未查询）
  const [selectedDate, setSelectedDate] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  });
  const [queryDate, setQueryDate] = useState<string | null>(null);

  const { data, isError, isFetching, refetch } = useQuery<OverviewData>({
    queryKey: ["history", queryDate ?? "none"],
    queryFn: () => fetchHistory(queryDate!),
    // 由 handleQuery 控制：首次设置 queryDate 时自动拉取；同日重复点击走 refetch
    enabled: queryDate !== null,
    retry: false,
  });

  const handleQuery = () => {
    if (queryDate === selectedDate) {
      // 同一日期再次查询 → 重新拉取（observer 闭包已是最新，无竞态）
      refetch();
    } else {
      // 切换日期 → 更新 key，自动触发新查询
      setQueryDate(selectedDate);
    }
  };

  const dateStr = data
    ? `${data.date} · ${data.weekday ?? WEEKDAYS[new Date(data.date).getDay()]}`
    : "";

  return (
    <>
      <PageHeader title="历史复盘" sub="按日期调取收盘快照 · 对比当日市场全貌">
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          aria-label="选择快照日期"
          style={{
            padding: "6px 10px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "#fff",
            fontSize: 13,
            fontFamily: "inherit",
            color: "var(--ink)",
            outline: "none",
          }}
        />
        <PillButton onClick={handleQuery} disabled={isFetching} style={{ opacity: isFetching ? 0.6 : 1 }}>
          查询快照
        </PillButton>
      </PageHeader>

      {/* 无数据提示 */}
      {!data && !isError && (
        <BaseCard style={{ padding: "40px 20px", display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 13, color: "var(--muted-strong)" }}>选择日期并点击「查询快照」</span>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>收盘快照由定时任务 15:35 自动生成，也可通过接口手动触发</span>
        </BaseCard>
      )}

      {isError && (
        <BaseCard style={{ padding: "40px 20px", display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 13, color: "var(--down)" }}>未找到 {queryDate} 的快照</span>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>该日可能未生成收盘快照（节假日或尚未收盘）</span>
        </BaseCard>
      )}

      {data && (
        <>
          {/* 快照头部信息 */}
          <BaseCard style={{ padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>{dateStr} 收盘快照</span>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>成交额 {data.breadth.turnover} · 涨停 {data.breadth.limitUpCount} · 跌停 {data.breadth.limitDownCount}</span>
            </div>
            <Chip
              text={data.closed ? "已收盘" : "盘中"}
              dotColor={data.closed ? "var(--series-base)" : "var(--accent)"}
            />
          </BaseCard>

          {/* 指数卡网格 */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {data.indices.map((idx) => (
              <IndexCard key={idx.code} data={idx} />
            ))}
          </div>

          {/* 市场宽度 + 涨停 TOP */}
          <div style={{ display: "flex", gap: 16, alignItems: "stretch" }}>
            <BaseCard style={{ flex: "0 0 400px", padding: "18px 20px", display: "flex", flexDirection: "column", gap: 16 }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>市场宽度</span>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <span className="num" style={{ fontSize: 22, fontWeight: 600, color: "var(--up)" }}>{data.breadth.up.toLocaleString()}</span>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>上涨</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <span className="num" style={{ fontSize: 22, fontWeight: 600, color: "var(--down)" }}>{data.breadth.down.toLocaleString()}</span>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>下跌</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <span className="num" style={{ fontSize: 22, fontWeight: 600, color: "var(--muted-strong)" }}>{data.breadth.flat.toLocaleString()}</span>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>平盘</span>
                </div>
              </div>
              <BreadthBar up={data.breadth.up} flat={data.breadth.flat} down={data.breadth.down} height={18} />
              <div style={{ display: "flex", gap: 12 }}>
                <span style={{ fontSize: 12, color: "var(--up)" }}>上涨 {data.breadth.upPct}%</span>
                <span style={{ fontSize: 12, color: "var(--muted)" }}>平盘 {data.breadth.flatPct}%</span>
                <span style={{ fontSize: 12, color: "var(--down)" }}>下跌 {data.breadth.downPct}%</span>
              </div>
            </BaseCard>

            <BaseCard style={{ flex: "1 1 auto", padding: "18px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>涨停 TOP</span>
              {(data.breadth.limitUpTop ?? []).map((s) => (
                <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 12, color: "var(--ink)", width: 64 }}>{s.name}</span>
                  <span className="num" style={{ fontSize: 12, fontWeight: 500, color: "var(--up)" }}>+{s.pct.toFixed(2)}%</span>
                </div>
              ))}
            </BaseCard>
          </div>

          {/* 行业 TOP5 */}
          <BaseCard style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>行业板块表现</span>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>申万一级行业 · 领涨/领跌 TOP5 · 单位 %</span>
            </div>
            <div style={{ display: "flex", gap: 32 }}>
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: "var(--up)" }}>领涨 TOP5</span>
                {(data.sectorsUp ?? []).map((s) => (
                  <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ width: 68, fontSize: 12, color: "var(--ink)", flex: "0 0 auto" }}>{s.name}</span>
                    <span className="num" style={{ fontSize: 12, fontWeight: 500, color: "var(--up)" }}>+{s.pct.toFixed(2)}%</span>
                  </div>
                ))}
              </div>
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: "var(--down)" }}>领跌 TOP5</span>
                {(data.sectorsDown ?? []).map((s) => (
                  <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ width: 68, fontSize: 12, color: "var(--ink)", flex: "0 0 auto" }}>{s.name}</span>
                    <span className="num" style={{ fontSize: 12, fontWeight: 500, color: "var(--down)" }}>{s.pct.toFixed(2)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </BaseCard>
        </>
      )}
    </>
  );
}
