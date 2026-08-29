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
- **SQLModel + SQLite**（业务表 + 行情持久层 L2）
- **APScheduler**（收盘 15:35：回填 L2 → 落收盘快照）
- **uv**（依赖管理，`pyproject.toml` + `uv.lock` 锁版本，内置清华 PyPI 镜像）

**L2 行情持久层**是后端的取数底座：把历史行情落到本地 SQLite，
让「永不变的历史数据」只读本地、不再回源。详见 [数据存储策略](docs/L2-数据存储策略.md)。

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
| 兜底 | mock | 无 token / 数据源故障时自动降级，离线可开发 |

除了上表的**实时域**，后端另有 5 个**回填专用域**（`stock_daily_raw` / `index_range` /
`sector_range` / `stock_names` / `calendar`），只供 L2 落库使用，前端不直接消费。
其中历史区间只有 Tushare 能补 —— 同花顺的快照类接口只能取当日。

---

## 💾 数据存储与缓存策略

> 完整设计见 [docs/L2-数据存储策略.md](docs/L2-数据存储策略.md)

### 核心原则：按「数据可变性」分层，而不是按 TTL 分层

```
不可变历史 (trade_date < 最新交易日)  →  永久存储，命中即返回
当日已收盘 (已过 15:05 且已入库)      →  永久存储，只读
当日盘中                              →  内存短 TTL（60s）
```

读取路径 **L1 内存 TTL → L2 SQLite（按 `trade_date` 命中）→ L3 数据源 API**：

- 已定格的数据先读本地，命中即返回，**零回源**
- 盘中数据先取实时源，本地库仅作兜底
- 回填完成后主动清空 L1，避免继续吐回填前的旧数据

### 表结构（`api/app/models/market_data.py`）

| 表 | 主键 | 内容 |
|---|---|---|
| `trade_calendar` | `trade_date` | 交易日历（按年同步，同步过就跳过） |
| `stock_daily` | `ts_code + trade_date` | 全市场个股日线（数据底座） |
| `market_daily_agg` | `trade_date` | 预聚合：7 档分布 / 涨跌停数 / 成交额 / 涨停 TOP5 |
| `index_daily` | `ts_code + trade_date` | 指数日线 |
| `sector_daily` | `sector_code + trade_date` | 行业日线 + 领涨股 |
| `futures_daily` | `contract + trade_date` | IF / IH / IM 主力连续 |
| `intraday_bar` | `code + trade_date + time` | 分时分钟线（收盘后固化） |
| `stock_name` | `ts_code` | 代码 → 名称 |
| `fetch_log` | `domain + ref_key` | **回源去重闸门** |
| `series_cache` | `cache_key` | 难建模数据的通用兜底 |

`stock_daily` 存明细（可回溯重算任意指标，`market_daily_agg` 存预聚合（查询 O(1)）——
双写兼顾灵活性与性能。全市场日线约 70MB/年。

### 不重复获取：`fetch_log`

`(domain, ref_key)` 唯一。任何回源动作落库后必须登记，回填前先查差集，
**已拉过的数据永不再拉**。重复调用回填是安全的幂等操作。

### 回填触发

| 方式 | 说明 |
|---|---|
| 定时任务 | 每工作日 15:35（上海时区），回填近 5 个交易日后落收盘快照 |
| 手动接口 | `POST /api/history/backfill?days=250`（需 `X-API-Token`） |
| 启动自动 | `BACKFILL_ON_STARTUP_DAYS=250`，后台跑不阻塞启动；首次部署后改回 `0` |

首次上线一次性约 **293 次请求**补齐一年（250 日线 + 8 指数 + 32 板块 + 3 期货），
之后每个交易日仅 1~4 次。

### 收益

| 接口 | 改造前（冷启动回源） | 改造后 |
|---|---|---|
| `/api/charts/limit-counts?days=60` | **≈120 次** | **0 次** |
| `/api/overview` | ≈76 次 | 0~3 次 |
| `/api/sectors` | ≈35 次 | **0 次** |
| `/api/watchlist` sparkline × N | N 次 | **0 次** |
| 进程重启 | 全量重拉 | **0 次** |

`api/tests/test_l2_read.py` 是这条策略的回归保障：回填后把各模块的 `fetch_domain`
换成「一调用就抛错」的探针，再打所有读接口 —— 只要还能返回 200 且数据正确，
就证明请求没碰数据源。

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
│   │   ├── cache.py          # L1 内存 TTL 缓存（收盘后 24h / 盘中 60s）+ clear_all
│   │   ├── tasks.py          # APScheduler 收盘任务（15:35 回填 + 快照）
│   │   ├── models/           # SQLModel 表
│   │   │   ├── market_data.py    # L2 行情表（10 张，见上文）
│   │   │   └── watchlist / chart_config / snapshot
│   │   ├── schemas/          # pydantic 响应模型
│   │   ├── services/
│   │   │   ├── provider.py       # 数据域注册表 + 能力矩阵 + 降级链
│   │   │   ├── store.py          # L2 仓储：交易日解析 / 读写闸门 / 本地聚合
│   │   │   ├── backfill.py       # L2 回填编排：缺口识别 + 限流 + 幂等
│   │   │   ├── buckets.py        # 涨跌分档与 sparkline 归一化（provider 共用）
│   │   │   ├── aggregator.py     # 聚合层（按定格状态在 L2 / 实时源间选路）
│   │   │   └── tushare / ths / tencent_provider.py
│   │   └── routers/          # overview / sectors / watchlist / charts / history / intraday
│   ├── tests/                # pytest（aggregator 单测 + 接口冒烟 + L2 零回源验证）
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
│   ├── L2-数据存储策略.md      # 后端数据存储 / 缓存 / 回填策略
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
>
> 想看到历史行情（涨跌停家数序列、期现对比等），需要先回填一年数据 ——
> 见 [首次部署：补齐历史数据](#首次部署补齐历史数据)，本地开发同样适用。

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
| `BACKFILL_ON_STARTUP_DAYS` | 否 | 启动时自动回填的历史交易日数，`0` = 关闭（默认）。首次部署建议设 `250`，跑完改回 `0` |

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
| GET | `/charts/futures-basis?contract=&days=` | 股指期货期现对比（IF/IH/IM 现货 vs 中金所主力，日线 + 基差率） |
| GET | `/history?date=` | 历史收盘快照（复盘对比） |
| POST | `/history/snapshot` | 手动触发收盘快照入库 |
| POST | `/history/backfill?days=` | 手动触发 L2 回填（需 `X-API-Token`；已回填日期自动跳过，幂等） |

> 完整请求 / 响应模型见 Swagger：`/docs`。

---

## 🚢 部署

1. **前端构建**：`cd web && npm run build`，产物 `web/dist/`
2. **后端启动**：`uv sync` 后以 `.venv/bin/uvicorn` 经 systemd 常驻（参考 `deploy/market-api.service`）
3. **首次回填历史**（见下方「首次部署：补齐历史数据」）
4. **反向代理**：Caddy 同域反代（`deploy/Caddyfile`），`/` → 静态资源，`/api/*` → 127.0.0.1:8000，避免 CORS
5. **容器化（可选）**：`deploy/Dockerfile`
6. **备份**：`deploy/backup.sh` 每日备份 SQLite 单文件（`api/data/app.db`）

> 每日 15:35 的定时任务会自动回填近 5 个交易日并落收盘快照，日常无需人工干预。

### 首次部署：补齐历史数据

L2 持久层的价值在于「历史数据落本地、不再回源」，所以**首次拉起服务时要先补一年历史**。
不补也能正常跑（读接口会实时降级到数据源），但享受不到零回源的收益。

两种方式二选一：

**方式一：启动自动回填**（推荐，后台跑不阻塞启动）

```bash
# api/.env 里设置，启动一次即可
BACKFILL_ON_STARTUP_DAYS=250

# 启动服务
uv run uvicorn app.main:app --port 8000
# 日志出现 [Startup] 自动回填完成：{...} 后，把该变量改回 0
```

**方式二：启动后手动触发**

```bash
curl -X POST "http://127.0.0.1:8000/api/history/backfill?days=250" \
     -H "X-API-Token: $API_TOKEN"
```

返回各域实际写入量，全为 `0` 表示无缺口：

```json
{"calendar": 778, "stock_names": 5403, "stock_daily": 250,
 "index_daily": 250, "sector_daily": 250, "futures": 750, "intraday": 0}
```

> **回填是幂等的**：已拉取的日期记录在 `fetch_log`，重复调用不会重复拉取，
> 可以放心重试或多次执行。补历史约 **293 次请求**（250 日线 + 8 指数 + 32 板块 + 3 期货），
> 之后每个交易日自动 1~4 次。
>
> 历史回填依赖 Tushare（同花顺的快照接口只能取当日）。若 `TUSHARE_TOKEN` 未配置，
> 回填会静默跳过并记日志，线上读取仍会实时降级到同花顺，不影响可用性。

---

## 📚 文档索引

- [设计约束](docs/设计约束.md) —— 视觉与交互规范（单一来源，含 CSS 变量可直接复制）
- [技术选型](docs/技术选型.md) —— 技术方案 v2（选型理由、数据源映射、目录树、里程碑）
- [L2 数据存储策略](docs/L2-数据存储策略.md) —— 数据分层、表结构、`fetch_log` 去重、回填编排与收益
- [任务拆分规划](docs/任务拆分规划.md) —— 任务拆解与依赖（P0–P8 / M1–M4，含验收要点）
- [UI 原型](docs/index.html) —— 5 页静态原型，视觉基线（直接用浏览器打开即可预览）

---

## ⚠️ 数据合规说明

数据来源：Tushare Pro（积分制授权，行情主数据源）+ 同花顺金融数据（板块 / 涨停池）+
腾讯行情（指数分时、港股指数兜底），**仅供参考，不构成投资建议**。

行情数据落本地库（`api/data/app.db`）仅作缓存用途，受各数据源授权条款约束，
请勿二次分发。

---

## 📄 状态与路线图

当前仓库包含前后端完整工程骨架与核心实现（对应里程碑 M1–M2 的大部分能力），待定项见 `docs/技术选型.md` §11：

- **G1 鉴权**：默认个人单用户免登，预留 `API_TOKEN` 写接口鉴权开关
- **G2 实时性**：默认仅收盘后数据；盘中 60s 轮询已预留开关（`usePolling` / 后端 TTL 60s）

### 已完成

- **L2 行情持久层**：10 张行情表 + 本地聚合 + `fetch_log` 去重 + 回填编排，
  读接口冷启动回源次数从 76~120 次降到 0~3 次（详见 [数据存储策略](docs/L2-数据存储策略.md)）

### 已知限制

- 历史板块的领涨股显示为 `—`：需「行业成分股 × 逐日全市场涨跌幅」比对，
  历史区间还原成本过高，目前只对当日补齐。后续加 `sector_member` 表即可本地计算。
- `daily_snapshot` 仍是每日全量 JSON blob，未改为从 L2 按日期重建。
- 历史回填依赖 Tushare（同花顺无法补历史区间）；token 失效时回填静默跳过，
  线上读取仍会实时降级到同花顺，不影响可用性。
