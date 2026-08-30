# 收盘复盘仪表盘 · UI 优化建议与视觉升级方案

> 基于 `docs/设计约束.md`、`web/src` 前端实现以及现有 Ardot 设计稿的审计结论。
> 已在 Ardot 画布交付「今日总览 v2」高保真设计稿 + 「视觉升级规范 v2」动效/Token 规范板。

---

## 一、现状总评

当前前端骨架和配色体系已经比较扎实：单一强调色 `#0066cc`、红涨绿跌、发丝边、无阴影、`tabular-nums` 等核心约束都已落地。`市场宽度卡` 刚完成表格化重构，信息层级清晰，建议直接沿用。

但整体界面仍停留在「功能正确」阶段，距离「精致、可扫读、有品牌感」还有明显距离。主要问题集中在：**组件化不足**、**视觉层级弱**、**动效缺失**、**若干实现 bug**。

---

## 二、体系层问题（工程债 + 规范不一致）

| # | 问题 | 位置 | 影响 | 改造建议 |
|---|---|---|---|---|
| 1 | `BaseCard` 没有内边距，所有调用处手写 `style={{ padding: "18px 20px" }}` | `web/src/components/common/BaseCard.tsx` | 5 个页面重复 10+ 处；改规范需全局替换 | 给 `BaseCard` 默认 `padding: 18px 20px`，调用处删除重复样式 |
| 2 | 卡片标题栏（标题 + 右侧说明/操作）未组件化 | `pages/*` 多处 | 同一段式重复 8+ 次，字号/对齐不一致风险 | 新增 `CardHeader` 组件：标题 `15px/600`，副标题 `12px/400` |
| 3 | 内容区无最大宽度约束 | `web/src/App.tsx` `main` 直接 `flex: 1` | 宽屏下卡片无限拉宽，扫读效率下降 | 增加 `max-width: 1440px` + `margin: 0 auto`；侧栏固定 240px |
| 4 | `Segmented` 选中段字重为 500 | `components/common/Segmented.module.css` line 19 | 设计约束 §4.4 要求选中段 600 | 改为 `font-weight: 600` |
| 5 | `Chip` 状态点默认绿色 | `components/common/Chip.module.css` line 10 | 默认态用跌色 `#2f9e6e`，语义错误 | 默认改为中性灰或组件强制传入 `dotColor` |
| 6 | 空态/加载态/错误态不统一 | `OverviewPage` / `SectorPage` / `BreadthTable` 等 | 同一产品有 3 种空态写法 | 统一 `EmptyState` / `Skeleton` 组件 |
| 7 | `Suspense fallback` 只有一行灰字 | `App.tsx` line 20 | 与设计约束「不用 spinner」但也没给骨架方案冲突 | 替换为卡片级骨架屏（ shimmer 渐变块） |

---

## 三、视觉层问题

| # | 问题 | 位置 | 改造建议 |
|---|---|---|---|
| 1 | 8 张指数卡整圈红绿描边，视觉噪音大 | `IndexCard.module.css` `.cardUp/.cardDown` | 改为「白底 + 左侧 3px 语义色竖条」，并给 sparkline 加同色面积填充 |
| 2 | 页面标题 22px 在 1440px 宽内容区中过弱 | `PageHeader.module.css` | 提升到 32px/600，负字距 -0.5px；副标题 15px |
| 3 | 指数卡数字 19px 偏小，字距默认 | `IndexCard.module.css` | 提升到 22px/600，字距 -0.3px；涨跌幅 14px/500 |
| 4 | 行业板块比例条把百分比当 px 用 | `OverviewPage.tsx` line 303 | `width: s.pct / maxW * 100` 是数字 → 被 React 视为 px，最长只有 100px；应改为 flex 轨道 + 百分比填充 |
| 5 | 页脚悬空，无分隔 | `OverviewPage.tsx` line 355 | 增加 1px 发丝顶边线 + padding-top 16px |
| 6 | 主图卡图例为纯文字，辨识度低 | `OverviewPage.tsx` line 267 | 改为「3px 色线 + 文字」mini legend |
| 7 | 全站几乎无字距调整，数字/标题显松散 | 多处 | 标题/大数字统一加轻微负字距 |

---

## 四、动效层问题

当前全站仅有 3 处 `transition`（导航 hover、按钮按压、指数卡边框），**0 个 `@keyframes`**。数据刷新时数字/图表/条形全部硬切，体验偏生硬。

建议补齐以下 8 组舒适微动效（详细参数见画布「视觉升级规范 v2」）：

| 动效 | 触发时机 | 参数 |
|---|---|---|
| 页面入场 | 路由切换 / 数据就绪 | opacity 0→1, translateY(12px→0), 400ms ease-out, 卡片 stagger 60ms |
| 数字滚动 | 行情数字更新 | value 0→target, 800ms ease-out, `tabular-nums` |
| 条形生长 | 分布条/比例条渲染 | scaleX(0→1), transform-origin left, 500ms ease-out, stagger 80ms |
| 折线描绘 | 分时图/Sparkline 渲染 | stroke-dashoffset 100%→0, 900ms ease-in-out, 系列 stagger 150ms |
| 卡片悬浮 | 鼠标 hover 卡片 | translateY(0→-2px), border-color #ececef→#d8d8dd, 200ms ease |
| 按钮按压 | 鼠标按下 | scale(1→0.96), 100ms ease（已存在，保留） |
| 分段滑块 | 切换 Segmented | 背景胶囊 translateX, 250ms cubic-bezier(0.25,0.1,0.25,1) |
| 骨架屏 shimmer | 数据加载中 | linear-gradient translateX 循环, 1200ms linear infinite, 数据到达后消失 |

> 设计约束 §6 禁止 spinner，但骨架屏不属于 spinner，可用于初始加载；持续上传/传输类动作也可保留动效。

---

## 五、关于「阴影」与「渐变」的边界

设计约束 §9 明确禁止阴影和装饰性渐变。本次升级方案**不引入卡片/按钮阴影**，以保持体系一致。

- **走势面积填充**：属于数据可视化语义（面积图），不是装饰性渐变，可使用 10% 透明度的同色填充。
- **骨架屏 shimmer**：属于加载状态，使用渐变动画，不是装饰性背景。
- **卡片 hover**：用 `translateY(-2px)` + 边框色加深表达，不引入阴影。

如果后续希望进一步「提亮」，可在规范板中把「卡片 hover 阴影 `0 2px 8px rgba(0,0,0,.05)`」作为可选开关单独评估，但默认关闭。

---

## 六、实施优先级建议

### P0（立即做，低风险高收益）
1. `BaseCard` 默认 padding + 删除调用处重复样式
2. 新增 `CardHeader` 组件统一卡片标题栏
3. 修复行业板块比例条 bug（flex 轨道）
4. `Segmented` 选中字重 500 → 600
5. `Chip` 默认状态点颜色修正
6. 页脚加顶部分隔线

### P1（视觉升级）
7. 指数卡改造：左侧 3px 语义条 + 面积图 + hover 态
8. 页面标题/指数数字字号与字距提升
9. 主图卡图例改为色线+文字
10. 内容区最大宽度约束

### P2（动效补齐）
11. 页面入场 stagger + 骨架屏 shimmer
12. 数字滚动 + 条形生长 + 折线描绘
13. 分段滑块动画 + 卡片 hover 位移

---

## 七、设计稿说明

- **画布文件**：`收盘复盘仪表盘 · 视觉升级方案 v2`（fileId `720361563300601`）
- **Frame 1**：「今日总览 v2」高保真 —— 1680×1280，包含侧栏、标题栏、8 张指数卡、指数分时对比、市场宽度、行业 TOP5、我的图表、页脚。
- **Frame 2**：「视觉升级规范 v2」—— 包含排版/间距/卡片升级对比、Bug 修复说明、8 组动效规范卡片。

所有颜色、字号、间距均沿用现有设计约束 token，未引入第二强调色，未给卡片加阴影。
