import { Suspense } from "react";
import { Outlet } from "react-router";
import Sidebar from "@/components/layout/Sidebar";

export default function App() {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main
        style={{
          flex: 1,
          minWidth: 0,
          background: "var(--bg-content)",
          padding: 28,
          display: "flex",
          flexDirection: "column",
          gap: 24,
        }}
      >
        <Suspense fallback={<div style={{ color: "var(--muted)", fontSize: 13 }}>加载中…</div>}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  );
}