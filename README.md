# 收盘复盘仪表盘（market-review）

> 个人收盘复盘 Web 应用：收盘后一键查看今日市场全景 —— 指数、涨跌分布、板块轮动、自选跟踪与策略画板。
> 视觉风格：理性克制的轻量仪表盘（发丝边卡片、单一强调色、红涨绿跌、tabular-nums 等宽数字），以 `docs/设计约束.md` 为单一视觉规范源。

---

## ✨ 功能特性

| 页面 | 路由 | 内容 |
|---|---|---|
| 今日总览 | `/overview` | 8 张指数卡 + 指数分时对比 + 市场宽度（涨/平/跌）+ 涨停 TOP + 行业 TOP5 + 「我的图表」钉选区 |
| 自定义图表 | `/charts` | 一行两卡图表网格（涨跌家数分布、成交额分时、指数对比等），支持从图表库添加、钉选到总览页 |
| 板块轮动 | `/sector` | 申万一级 31 行业涨跌排名表（涨跌幅 / 领涨股 / 5 日走势） |
| 自选跟踪 | `/watchlist` | 自选池 + 持仓盈亏汇总（总市值 / 今日盈亏 / 持仓盈亏 / 仓位） |
| 策略画板 | `/canvas` | 策略曲线 + 基准对比（沪深300）+ 成交量柱 |

**设计要点**：A 股红涨绿跌惯例、无阴影 / 无渐变 / 无 spinner、单一强调色 `#0066cc`、发丝边卡片（1px 描边 + 白底）、数字 `tabular-nums` 等宽对齐。

---

## 🛠 技术栈

### 前端 `web/`
- **React 18 + TypeScript + Vite 6**
- **react-router v7**（5 条路由懒加载）
- **Zustand**（客户端状态：行情快照 / 自选持仓 / 图表库钉选）
- **TanStack Query**（服务端状态：缓存 / 重试 / 盘中 60s 轮询）
- **ECharts 5 + echarts-for-react**（图表统一封装 `BaseChart`，配色对齐设计 token）
- **CSS Modules + tokens.css**（设计令牌单一来源，未引入 UI 框架）

### 后端 `api/`
- **FastAPI + pydantic v2 + httpx**（async 并发抓取）
- **SQLModel + SQLite**（自选 / 持仓 / 图表配置 / 每日收盘快照）
- **APScheduler**（收盘 15:35 全量快照入库）
- **uv**（依赖管理，`pyproject.toml` + `uv.lock` 锁版本，内置清华 PyPI 镜像）

### 数据源（Provider 解耦架构）
> 前端只消费后端 REST 契约，**不知道也不关心数据来自哪个源**；后端按「数据域」通过
> `api/app/services/provider.py` 的能力矩阵 + 硬编码映射表自动选择数据源（可逐域指定主源，失败自动降级）。

| 数据域 | 配置主源 | 说明 |
|---|---|---|
| `indices` 指数卡 | Tushare | 指数日线 + sparkline（恒生指数走腾讯兜底） |
| `breadth` 涨跌家数/分布 | Tushare | 全市场日线一次统计 |
| `limit_up` 涨停 TOP | **同花顺** | 涨停池（原因/连板/封单），比 Tushare 更全 |
| `sectors` 板块轮动 | **同花顺** | 同花顺行业指数 + 成分股领涨股（Tushare `sw_daily` 需权限） |
| `intraday` 指数分时 | 腾讯 | Tushare/同花顺均无分钟线，腾讯免费接口唯一能力源 |
| 兜底 | mock | `mock_data.py`，无 token / 数据源故障时自动降级，离线可开发 |

---

## 📁 项目结构

```
market-review/
├── web/                      # 前端（React18 + Vite + TS）
│   ├── src/
│   │   ├── api/              # 接口层（axios 实例 + 各模块 API）
│   │   ├── components/       # layout / common / charts 组件
│   │   ├── hooks/            # TanStack Query hooks（useOverview / useSectors / usePolling）
│   │   ├── pages/            # 5 个页面
│   │   ├── stores/           # Zustand（market / watchlist / chartLib）
│   │   ├── styles/           # tokens.css（设计令牌）+ global.css
│   │   ├── types/            # 行情 / 板块 / 自选 TS 类型
│   │   ├── mocks/            # 前端 mock 数据（M1 阶段）
│   │   ├── router/           # 路由配置（懒加载）
│   │   ├── App.tsx           # 根布局（Sidebar + Outlet）
│   │   └── main.tsx          # 入口
│   ├── vite.config.ts        # @ alias + dev 代理 /api → :8000
│   └── package.json
├── api/                      # 后端（FastAPI）
│   ├── app/
│   │   ├── main.py           # 应用入口 + 路由注册 + CORS + 定时任务
│   │   ├── config.py         # 环境变量配置（TUSHARE_TOKEN 等）
│   │   ├── cache.py          # 内存 TTL 缓存（收盘后 24h / 盘中 60s）
│   │   ├── tasks.py          # APScheduler 收盘快照任务（15:35）
│   │   ├── models/           # SQLModel 表（watchlist / chart_config / snapshot）
│   │   ├── schemas/          # pydantic 响应模型
│   │   ├── services/         # provider 注册表/映射表 + tushare/ths/tencent 数据源 + aggregator
│   │   └── routers/          # overview / sectors / watchlist / charts / history / intraday
│   ├── tests/                # pytest（aggregator 单测 + 接口冒烟）
│   ├── .env.example          # 环境变量模板
│   ├── pyproject.toml        # uv 依赖声明
│   └── uv.lock
├── deploy/                   # 部署配置
│   ├── Caddyfile             # 反代：/ → 前端静态，/api → :8000
│   ├── market-api.service    # systemd unit（uvicorn）
│   ├── Dockerfile            # 可选容器化
│   └── backup.sh             # SQLite 每日备份脚本
├── docs/                     # 设计文档
│   ├── index.html            # 静态 UI 原型（视觉基线，勿删）
│   ├── 设计约束.md            # 视觉与交互规范（单一来源）
│   ├── 技术选型.md            # 技术方案 v2
│   └── 任务拆分规划.md        # 任务拆解与依赖（P0–P8 / M1–M4）
└── README.md
```

---

## 🚀 快速开始

### 环境要求
- Python ≥ 3.11（后端）
- Node.js ≥ 18（前端）
- [uv](https://docs.astral.sh/uv/)（可选，推荐）

### 1. 启动后端（端口 8000）

```bash
cd api
cp .env.example .env        # 填入你的 TUSHARE_TOKEN（未配置时自动使用 mock 数据）
uv sync                     # 安装依赖（默认走清华镜像，锁版本见 uv.lock）
uv run uvicorn app.main:app --reload --port 8000
```

- API 文档（Swagger）：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health

> 不用 uv 也可以：`pip install -e .` 后 `uvicorn app.main:app --reload`。

### 2. 启动前端（端口 5173）

```bash
cd web
npm install
npm run dev                 # Vite dev 已配置 /api 代理到 127.0.0.1:8000
```

浏览器打开 http://127.0.0.1:5173 即可。

### 3. 构建与测试

```bash
# 前端构建（产物输出到 web/dist）
cd web && npm run build

# 后端测试
cd api && uv run pytest
```

---

## 🔑 环境变量（`api/.env`）

| 变量 | 必填 | 说明 |
|---|---|---|
| `TUSHARE_TOKEN` | 条件必填 | Tushare Pro token（2000 积分）；未配置时指数/涨跌家数回退 mock |
| `THS_API_KEY` | 条件必填 | 同花顺金融数据 API Key（fuyao.aicubes.cn 签发）；未配置时板块/涨停回退其他源 |
| `APP_ENV` | 否 | `development` / `production`，默认 development（CORS 全放开） |
| `DATABASE_URL` | 否 | 默认 `sqlite+aiosqlite:///./data/app.db` |
| `API_TOKEN` | 否 | 配置后，写接口（POST/PUT/DELETE）需携带 `X-API-Token` 头 |
| `CORS_ORIGINS` | 否 | 生产环境 CORS 白名单（逗号分隔） |

> 数据源选择策略**不**通过环境变量配置：各域主源在 `api/app/services/provider.py` 的
> `DOMAIN_PROVIDER` 映射表硬编码，`.env` 只存放各类 token。

---

## 🔌 API 一览（前缀 `/api`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/overview` | 今日总览（指数卡 + 市场宽度 + 涨停 TOP + 行业 TOP5） |
| GET | `/sectors` | 申万一级行业排名（支持 `?sort=`） |
| GET | `/watchlist` | 自选池 + 持仓盈亏汇总 |
| POST / PUT / DELETE | `/watchlist[/{code}]` | 自选 / 持仓 CRUD（写接口需 `X-API-Token`） |
| GET | `/charts` | 图表库列表 + 钉选配置 |
| POST / PUT / DELETE | `/charts[/{chart_id}]` | 图表库 CRUD（写接口需 `X-API-Token`） |
| GET | `/intraday` | 指数分时数据（腾讯接口兜底） |
| GET | `/history?date=` | 历史收盘快照（复盘对比） |
| POST | `/history/snapshot` | 手动触发收盘快照入库 |

> 完整请求 / 响应模型见 Swagger：`/docs`。

---

## 🚢 部署

1. **前端构建**：`cd web && npm run build`，产物 `web/dist/`
2. **后端启动**：`uv sync` 后以 `.venv/bin/uvicorn` 经 systemd 常驻（参考 `deploy/market-api.service`）
3. **反向代理**：Caddy 同域反代（`deploy/Caddyfile`），`/` → 静态资源，`/api/*` → 127.0.0.1:8000，避免 CORS
4. **容器化（可选）**：`deploy/Dockerfile`
5. **备份**：`deploy/backup.sh` 每日备份 SQLite 单文件（`api/data/app.db`）

---

## 📚 文档索引

- [设计约束](docs/设计约束.md) —— 视觉与交互规范（单一来源，含 CSS 变量可直接复制）
- [技术选型](docs/技术选型.md) —— 技术方案 v2（选型理由、数据源映射、目录树、里程碑）
- [任务拆分规划](docs/任务拆分规划.md) —— 任务拆解与依赖（P0–P8 / M1–M4，含验收要点）
- [UI 原型](docs/index.html) —— 5 页静态原型，视觉基线（直接用浏览器打开即可预览）

---

## ⚠️ 数据合规说明

数据来源：Tushare Pro（积分制授权，主数据源）+ 腾讯行情（分时补充），**仅供参考，不构成投资建议**。

---

## 📄 状态与路线图

当前仓库包含前后端完整工程骨架与核心实现（对应里程碑 M1–M2 的大部分能力），待定项见 `docs/技术选型.md` §11：

- **G1 鉴权**：默认个人单用户免登，预留 `API_TOKEN` 写接口鉴权开关
- **G2 实时性**：默认仅收盘后数据；盘中 60s 轮询已预留开关（`usePolling` / 后端 TTL 60s）
