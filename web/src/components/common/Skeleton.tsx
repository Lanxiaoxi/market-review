import styles from "./Skeleton.module.css";

/**
 * 页面级骨架屏：路由懒加载 / 首屏数据未就绪时的占位。
 * 设计约束 §6 禁止 spinner，这里用 shimmer 占位块表达「正在取数」。
 */
export default function PageSkeleton() {
  return (
    <div className={styles.wrap} aria-busy="true" aria-label="加载中">
      {/* 标题栏 */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div className={`${styles.shimmer} ${styles.title}`} style={{ width: 180, height: 32 }} />
        <div className={`${styles.shimmer} ${styles.line}`} style={{ width: 320 }} />
      </div>

      {/* 指数卡网格 */}
      <div className={styles.grid}>
        {Array.from({ length: 8 }, (_, i) => (
          <div
            key={i}
            className={`${styles.card} ${styles.shimmer}`}
            style={{ animationDelay: `${i * 60}ms` }}
          />
        ))}
      </div>

      {/* 主图 + 侧卡 */}
      <div style={{ display: "flex", gap: 16 }}>
        <div className={styles.block} style={{ flex: "1 1 968px", minWidth: 0 }}>
          <div className={styles.row}>
            <div className={`${styles.shimmer} ${styles.line}`} style={{ width: 120 }} />
            <div className={`${styles.shimmer} ${styles.line}`} style={{ width: 160 }} />
          </div>
          <div className={`${styles.shimmer} ${styles.body}`} />
        </div>
        <div className={styles.block} style={{ flex: "1 1 400px", minWidth: 0 }}>
          <div className={styles.row}>
            <div className={`${styles.shimmer} ${styles.line}`} style={{ width: 96 }} />
            <div className={`${styles.shimmer} ${styles.line}`} style={{ width: 110 }} />
          </div>
          <div className={`${styles.shimmer} ${styles.line}`} style={{ height: 12 }} />
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className={`${styles.shimmer} ${styles.line}`} style={{ width: `${90 - i * 12}%` }} />
          ))}
        </div>
      </div>
    </div>
  );
}
