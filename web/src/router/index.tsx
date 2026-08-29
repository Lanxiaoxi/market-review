import { lazy } from "react";
import { createBrowserRouter } from "react-router";
import App from "@/App";

const OverviewPage = lazy(() => import("@/pages/OverviewPage"));
const CustomChartPage = lazy(() => import("@/pages/CustomChartPage"));
const SectorPage = lazy(() => import("@/pages/SectorPage"));
const WatchlistPage = lazy(() => import("@/pages/WatchlistPage"));
const StrategyPage = lazy(() => import("@/pages/StrategyPage"));
const HistoryPage = lazy(() => import("@/pages/HistoryPage"));

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: "overview", element: <OverviewPage /> },
      { path: "charts", element: <CustomChartPage /> },
      { path: "sector", element: <SectorPage /> },
      { path: "watchlist", element: <WatchlistPage /> },
      { path: "canvas", element: <StrategyPage /> },
      { path: "history", element: <HistoryPage /> },
    ],
  },
]);