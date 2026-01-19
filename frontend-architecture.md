# React + uPlot 叠加 Canvas 标注工具（时间序列/波形）需求设计文档

## 1. 背景与目标
当前项目需要在时间序列/波形图上完成“拖拽框选 + 标签 + 选中/调整”等交互标注能力。现有前端技术栈为 React，图表层使用 uPlot。目标是以最小复杂度实现高性能的标注体验，并可逐步扩展到多标签、多选、快捷键、撤销/重做等能力。

### 1.1 目标
- 覆盖 uPlot 上的 Canvas 标注层，支持区域创建、选中、调整与删除。 需要绘制半透明色块、拖拽边缘、垂直参考线 
  - 使用 React Hooks，组件化、可复用、可扩展。
- 兼顾性能（大数据/长时间轴）、交互可用性、可维护性。

### 1.2 非目标
- 不在本阶段实现协作标注与多人实时同步。
- 不在本阶段完成后端持久化与权限系统的细节设计（可留接口）。
- 不实现复杂的自动标注或模型推断流程。

## 2. 术语
- **Region**：一个时间范围区域，包含 `start/end/color/labels` 等字段。
- **Overlay Canvas**：覆盖在 uPlot 上的绘制层。
- **Hit Layer**：事件捕获层（可与 Overlay 合并）。
- **Viewport**：uPlot 当前可视时间窗口。

## 3. 需求范围
### 3.1 MVP 功能
1. 区域创建：按下-拖拽-松开生成区域。
2. 可视渲染：仅渲染当前视窗内区域。
3. 选中高亮：点击区域可选中。
4. 调整大小：拖拽左右边缘调整 `start/end`。
5. 删除区域：键盘 `Delete/Backspace` 删除选中区域。

### 3.2 增强功能
1. 多选：`Shift` 叠加选择。
2. 快捷键：撤销/重做、锁定区域、复制区域。
3. 标签显示策略：仅选中时显示或悬停显示。
4. 多层渲染：底色层/标签层分离。
5. 大批量渲染优化：批量绘制、延迟文本测量。

## 4. 用户故事
1. 作为标注人员，我希望拖拽即可创建一段时间区域，便于快速标注。
2. 作为标注人员，我希望调整区域边缘以精准定位。
3. 作为标注人员，我希望一键删除错误的标注。
4. 作为项目成员，我希望标注层在缩放/滚动时与图表保持对齐。

## 5. 交互设计
### 5.1 鼠标交互
- **新建区域**：在空白区域 `mousedown` 创建零宽度 Region，`mousemove` 更新 `end`，`mouseup` 固定。
- **选择区域**：点击区域内部选中；`Shift+点击` 进行多选。
- **调整边缘**：鼠标接近左右边缘（例如 $\pm 4px$ 命中区）进入 resize 模式。
- **拖拽移动**（增强）：在区域中部拖拽整体平移。

### 5.2 键盘交互
- `Delete/Backspace`：删除选中区域。
- `Esc`：取消绘制/取消当前操作。
- `Ctrl/Cmd+Z`、`Ctrl/Cmd+Shift+Z`：撤销/重做（增强）。

### 5.3 边界与异常
- 最小长度阈值：长度小于阈值的区域视为无效或转为“点事件”。
- 越界拖拽：区域 `start/end` clamp 到当前数据时间范围。

## 6. 数据模型
### 6.1 Region
```ts
type Region = {
  id: string;
  start: number; // 时间，使用 uPlot x 轴单位
  end: number;
  color: string; // rgba()
  labels?: string[];
  selected?: boolean;
  visible?: boolean;
  locked?: boolean;
};
```

### 6.2 交互状态
```ts
type DrawingState = {
  mode: "idle" | "drawing" | "resizing" | "moving";
  activeRegionId?: string;
  resizeHandle?: "left" | "right";
  startTime?: number;
};
```

## 7. 前端架构
### 7.1 组件分层
```
App
└─ TimeSeriesAnnotator
   ├─ uPlotChart
   ├─ OverlayCanvas
   └─ HitLayer
```

### 7.2 代码结构建议
- [frontend/src/components/TimeSeriesAnnotator.tsx](frontend/src/components/TimeSeriesAnnotator.tsx)：容器组件，组合 uPlot 与 Overlay。
- [frontend/src/components/OverlayCanvas.tsx](frontend/src/components/OverlayCanvas.tsx)：Canvas 渲染层（可选）。
- [frontend/src/hooks/useUplot.ts](frontend/src/hooks/useUplot.ts)：uPlot 初始化与钩子管理（可选）。
- [frontend/src/hooks/useRegions.ts](frontend/src/hooks/useRegions.ts)：Region 增删改查与命中测试（可选）。

### 7.3 事件流
1. `mousedown` → 创建 Region（零宽度）
2. `mousemove` → 更新 Region 终点
3. `mouseup` → 归一化并提交到 `regions`
4. uPlot `draw/setScale` → `renderOverlay()` 重绘

## 8. 渲染策略
- **仅渲染可见区域**：`end >= tMin && start <= tMax`
- **DPR 适配**：`canvas.width = clientWidth * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0)`
- **分层渲染**：底色层与标签层可拆分
- **标签策略**：仅选中/悬停时绘制，减少文本测量成本

## 9. 与 uPlot 的集成
- 时间↔像素映射：`valToPos/posToVal`
- 钩子触发重绘：`draw`、`setScale`
- 视窗范围：`u.scales.x.minmax`

## 10. 性能与指标
- 目标交互帧率：$\ge 60fps$（普通数据量）。
- 渲染策略：mousemove 使用 `requestAnimationFrame` 节流。
- 大量 Regions：先过滤可见窗口，再绘制。

## 11. 可观测性与调试
- 标注事件埋点：创建/删除/修改/选择次数。
- 关键性能指标：渲染耗时、重绘频次、平均交互延迟。

## 12. 参考实现与资料
- 参考 Label Studio 的区域管理与渲染模型：
  - [Reference/Regions.ts.txt](Reference/Regions.ts.txt)
  - [Reference/Segment.ts.txt](Reference/Segment.ts.txt)
  - [Reference/Region.ts.txt](Reference/Region.ts.txt)
  - [Reference/Timeline.ts.txt](Reference/Timeline.ts.txt)
  - [Reference/TimeSeries.jsx](Reference/TimeSeries.jsx)
  - [Reference/view.tsx](Reference/view.tsx)
  - [Reference/model.js](Reference/model.js)

## 13. 风险与对策
- **滚动/缩放不同步**：在 `draw/setScale` 时强制重绘。
- **高频重绘卡顿**：采用 `requestAnimationFrame`，减少文本绘制。
- **大量区域内存增长**：提供批量导入/清理机制，限制同时渲染数量。

## 14. 里程碑
1. MVP：创建 + 渲染 + 选中 + 删除
2. 调整/拖拽 + 多选 + 快捷键
3. 性能优化 + 分层渲染 + 标签策略
4. 接入后端保存/加载（如需）

## 15. 验收标准
- 能在 uPlot 上完成区域创建与渲染。
- 缩放/拖拽视图后区域与波形保持对齐。
- 支持区域选中、调整边缘与删除。
- 在 $\le 5000$ 个区域情况下保持可用交互性能。

## 16. Label Studio 音频序列化与参考实现迁移建议

- **Label Studio 的音频序列化（summary）**：Label Studio 在任务数据中使用 `audio` 类型来表示可注释的音频资源（通常包含音频 URL、采样率、时长等元信息）。具体的注释实体（比如区间/segment/region）在序列化时以 `start`/`end`（时间，秒或毫秒）和关联的标签 id/名称形式存储，便于后端与前端在时间轴上精确定位并还原 UI 状态。

- **与我们架构的映射建议**：将 Label Studio 的 `audio` 任务字段映射到本项目的 `Region` 数据结构（保留 `start`, `end`, `labels`, `color`, `id`, `locked` 等），并在任务加载时把音频元数据注入到音频解码/可视化层（如 `AudioDecoder` / `WaveformAudio`）以确保时间单位一致。

- **采纳参考工程的关键点**：参考仓库里的实现（例如 [Reference/model.js](Reference/model.js)、[Reference/Region.ts](Reference/Region.ts)、[Reference/Regions.ts](Reference/Regions.ts)、[Reference/TimeSeries.jsx](Reference/TimeSeries.jsx)、[Reference/view.tsx](Reference/view.tsx)）可以直接迁移以下模式：
  - 区间创建：按下即创建零宽度 Region，mousemove 更新 end，mouseup 归一化并提交（与 Label Studio 相同交互流）。
  - 选择与多选：点击选中，`Shift+Click` 叠加选择；选中状态保存在 `Region.selected` 字段，便于样式和操作逻辑统一。参考实现中 `Regions` 管理集合、命中测试与选中逻辑值得重用。
  - 缩放与坐标变换：用 uPlot 的 `valToPos/posToVal` 或等价函数替代像素到时间的映射；所有绘制与命中测试均基于可视窗口的映射，避免像素与时间单位错配。
  - 边缘调整与阈值：在边缘 ±4px 命中进入 resize 模式；对小于最小长度阈值的区域视为无效或转换为点事件（同参考实现的最小长度策略）。
  - 删除与快捷键：`Delete/Backspace` 删除选中项，`Esc` 取消当前操作；建议引入撤销/重做栈（增强功能）。
  - 标签（Tagging）策略：把标签作为 `Region.labels`（数组或 id 列表）绑定到区间；显示策略采用“仅选中或悬停时绘制标签”以降低渲染成本。标签集合（choices/labels）可复用 Label Studio 的枚举式结构并在 UI 提供快速选择组件（参考 `tags/control/*`）。

- **性能与渲染建议（来自参考工程）**：
  - 仅渲染可见区域（`end >= tMin && start <= tMax`）并在 `requestAnimationFrame` 内做节流。
  - DPR 适配：`canvas.width = clientWidth * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0)`。
  - 分层 Canvas：底色/形状层与标签/文本层分离，减少频繁文本测量。

- **集成步骤建议（简短行动项）**：
  1. 在任务加载时把 Label Studio 风格的 `audio` 字段映射到本地 `Region` 数据模型。  
  2. 复用 `Reference/Regions.ts` 的管理与命中测试逻辑，确保选中/多选/删除行为一致。  
  3. 使用 uPlot 的坐标转换（或等价实现）统一时间↔像素映射，保证缩放/滚动同步。  
  4. 按需复用 `tags/control/*` 中的标签选择控件与 `Audio` 标签视图，保证标注体验一致性。

- 将以上摘要加入到 `frontend-architecture.md`，便于团队在迁移 Label Studio 概念到 Vue3+uPlot 时保留一致的数据契约与交互范式。
迁移自 Label Studio 的要点
保留 start/end/selected/labels/color 的数据结构。
保留“按下即创建零宽度、拖动更新、松开确定”的交互。
用 uPlot 的 valToPos/posToVal 替代 LS 的 pixelsToTime/mapToPx。
用 overlay Canvas 替 LS 的 Visualizer 层；若需要 timeline，单独再加一条 Canvas/DOM。
用以上骨架，你可以把 Label Studio 的 Region/Segment 概念和交互流快速搬到 React + uPlot 上，最少量代码即可跑通“划框标注”。