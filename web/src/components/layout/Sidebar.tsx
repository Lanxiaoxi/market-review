import { useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { INDEX_SERIES } from "@/constants/indices";
import { useUserPrefs } from "@/stores/userPrefs";
import styles from "./Sidebar.module.css";

interface NavItem {
  id: string;
  title: string;
  sub: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  {
    id: "overview",
    title: "今日总览",
    sub: "3秒扫盘 · 把握全局",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <rect x="2" y="2" width="6" height="6" rx="1.5" fill="var(--icon)" />
        <rect x="10" y="2" width="6" height="6" rx="1.5" fill="var(--icon)" />
        <rect x="2" y="10" width="6" height="6" rx="1.5" fill="var(--icon)" />
        <rect x="10" y="10" width="6" height="6" rx="1.5" fill="var(--icon)" />
      </svg>
    ),
  },
  {
    id: "charts",
    title: "自定义图表",
    sub: "我的行情统计图表",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <path d="M2.5 13.5 A6.5 6.5 0 0 1 15.5 13.5" stroke="var(--icon)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        <circle cx="9" cy="13" r="1.2" fill="var(--icon)" />
        <line x1="9" y1="13" x2="12.5" y2="7" stroke="var(--icon)" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    id: "sector",
    title: "板块轮动",
    sub: "捕捉当日热点与异动",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <rect x="2" y="9" width="3.2" height="6" rx="0.8" fill="var(--icon)" />
        <rect x="6.4" y="6" width="3.2" height="9" rx="0.8" fill="var(--icon)" />
        <rect x="10.8" y="3" width="3.2" height="12" rx="0.8" fill="var(--icon)" />
      </svg>
    ),
  },
  {
    id: "watchlist",
    title: "自选跟踪",
    sub: "聚焦自选与盈亏贡献",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <polygon points="9,2 10.6,6.3 15.2,6.5 11.6,9.3 12.8,13.8 9,11.2 5.2,13.8 6.4,9.3 2.8,6.5 7.4,6.3" fill="var(--icon)" />
      </svg>
    ),
  },
  {
    id: "canvas",
    title: "策略画板",
    sub: "承载自制图表与深度分析",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <rect x="2" y="3" width="14" height="12" rx="2" stroke="var(--icon)" strokeWidth="1.3" fill="none" />
        <polyline points="4.5,11 7.5,8 10,10 13.5,5" stroke="var(--icon)" strokeWidth="1.3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const nickname = useUserPrefs((s) => s.nickname);
  const selectedIndices = useUserPrefs((s) => s.selectedIndices);
  const setNickname = useUserPrefs((s) => s.setNickname);
  const setSelectedIndices = useUserPrefs((s) => s.setSelectedIndices);

  const [open, setOpen] = useState(false);
  const [draftName, setDraftName] = useState(nickname);

  // 确定当前活跃的页面 id
  const activeId = navItems.find((item) => location.pathname === `/${item.id}` || (item.id === "overview" && location.pathname === "/"))?.id ?? "overview";

  const toggleIndex = (code: string) => {
    setSelectedIndices(
      selectedIndices.includes(code)
        ? selectedIndices.length > 1
          ? selectedIndices.filter((c) => c !== code)
          : selectedIndices
        : [...selectedIndices, code]
    );
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M2.5 15.5 L6.5 9.5 L10 12.5 L13.5 6 L17.5 8" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className={styles.brandTitle}>收盘复盘</span>
      </div>

      <nav className={styles.nav}>
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`${styles.navItem} ${activeId === item.id ? styles.navItemActive : ""}`}
            onClick={() => navigate(`/${item.id === "overview" ? "" : item.id}`)}
          >
            <span className={styles.navIcon}>{item.icon}</span>
            <span className={styles.navText}>
              <span className={styles.navTitle}>{item.title}</span>
              <span className={styles.navSub}>{item.sub}</span>
            </span>
          </button>
        ))}
      </nav>

      <div className={styles.spacer} />

      {/* 偏好设置面板（点击用户区展开） */}
      {open && (
        <div className={styles.settings}>
          <div className={styles.settingsTitle}>偏好设置</div>

          <div className={styles.settingsLabel}>昵称</div>
          <div style={{ display: "flex", gap: 6 }}>
            <input
              className={styles.input}
              value={draftName}
              onChange={(e) => setDraftName(e.target.value)}
              aria-label="昵称"
            />
            <button
              className={styles.saveBtn}
              onClick={() => setNickname(draftName)}
            >
              保存
            </button>
          </div>

          <div className={styles.settingsLabel}>默认分时指数</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {INDEX_SERIES.map((s) => {
              const on = selectedIndices.includes(s.code);
              return (
                <button
                  key={s.code}
                  onClick={() => toggleIndex(s.code)}
                  title={on ? `取消 ${s.name}` : `勾选 ${s.name}`}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    padding: "3px 8px",
                    borderRadius: 9999,
                    border: on ? "1px solid var(--accent)" : "1px solid var(--border)",
                    background: on ? "var(--active-bg)" : "var(--chip-bg)",
                    fontSize: 11,
                    color: on ? "var(--accent)" : "var(--muted)",
                    fontFamily: "inherit",
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  <span style={{ width: 10, height: 3, borderRadius: 2, background: s.color }} />
                  {s.name}
                </button>
              );
            })}
          </div>
        </div>
      )}

      <div
        className={styles.user}
        onClick={() => {
          setOpen((v) => !v);
          setDraftName(nickname);
        }}
        title="偏好设置"
      >
        <span className={styles.avatar}>
          <span className={styles.avatarText}>{nickname.slice(0, 1)}</span>
        </span>
        <span className={styles.userStack}>
          <span className={styles.userName}>{nickname}</span>
          <span className={styles.userSub}>个人复盘空间</span>
        </span>
      </div>
    </aside>
  );
}