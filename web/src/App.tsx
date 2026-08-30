import { Suspense } from "react";
import { Outlet } from "react-router";
import Sidebar from "@/components/layout/Sidebar";
import PageSkeleton from "@/components/common/Skeleton";

export default function App() {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main
        style={{
          flex: 1,
          minWidth: 0,
          background: "var(--bg-content)",
          display: "flex",
          justifyContent: "center",
        }}
      >
        {/* v2：内容区限制最大宽度，宽屏下不无限拉伸 */}
        <div
          style={{
            width: "100%",
            maxWidth: "var(--content-max)",
            padding: "var(--pad-content)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--gap-section)",
          }}
        >
          <Suspense fallback={<PageSkeleton />}>
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  );
}
