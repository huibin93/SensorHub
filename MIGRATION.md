# 迁移总结：从 Recharts 到 uPlot

## 迁移完成日期
2026年1月20日

## 迁移概述
成功将 SensorHub 项目的图表库从 Recharts 迁移到 uPlot，以提升性能并实现更精确的时间序列数据可视化和标注功能。

## 主要变更

### 1. 依赖变更
- **移除**: `recharts@2.15.2`
- **添加**: `uplot@1.6.31`

### 2. 新增文件

#### Hooks
- **`src/app/hooks/useUplot.ts`**: uPlot 实例管理 Hook
  - 初始化和销毁 uPlot 实例
  - 数据更新
  - 尺寸调整
  - 缩放控制

- **`src/app/hooks/useRegions.ts`**: 标注区域管理 Hook
  - 时间与像素坐标转换
  - 区域命中测试
  - 区域边缘检测

#### 组件
- **`src/app/components/OverlayCanvas.tsx`**: Canvas 覆盖层组件
  - 渲染标注区域
  - 渲染拖拽选区
  - 处理鼠标交互
  - 显示区域标签

### 3. 更新文件

#### TimeSeriesChart 组件 (`src/app/components/TimeSeriesChart.tsx`)
**主要改动**:
- 使用 uPlot 替代 Recharts 的 LineChart
- 实现 Canvas 覆盖层用于标注渲染
- 保留所有原有功能：
  - 标注创建（拖拽）
  - 缩放（zoom）
  - 平移（pan）
  - 自定义工具模式
  - Y 轴自适应
  - 时间提示

**技术优势**:
- 更高的渲染性能（Canvas vs SVG）
- 更精确的时间-像素转换
- 更流畅的大数据量显示
- 更好的标注交互体验

#### MiniMap 组件 (`src/app/components/MiniMap.tsx`)
**主要改动**:
- 使用 uPlot 替代 Recharts
- 保留所有交互功能：
  - 视口拖拽
  - 边缘调整
  - 视觉反馈

## 架构对齐

本次迁移完全符合 `frontend-architecture.md` 中的设计：
- ✅ 使用 uPlot 作为图表层
- ✅ Canvas 覆盖层用于标注
- ✅ React Hooks 架构
- ✅ 时间序列数据优化
- ✅ 高性能渲染

## 功能保留

所有原有功能均已保留：
- ✅ 双通道数据显示（ACC/GYRO）
- ✅ 三轴数据（X/Y/Z）
- ✅ 标注创建和编辑
- ✅ 缩放和平移工具
- ✅ 视口管理
- ✅ MiniMap 导航
- ✅ 区域高亮
- ✅ 标签管理
- ✅ Y 轴自适应

## 性能提升

uPlot 相比 Recharts 的优势：
1. **渲染速度**: Canvas 渲染比 SVG 快 5-10 倍
2. **内存占用**: 更少的 DOM 节点
3. **大数据支持**: 可流畅显示数万个数据点
4. **交互响应**: 更流畅的缩放和平移
5. **精确控制**: 像素级别的坐标转换

## 开发服务器
```bash
npm run dev
```
访问: http://localhost:5174/

## 待优化项

虽然迁移已完成，以下是未来可以考虑的优化：

1. **性能优化**
   - 实现虚拟滚动
   - 数据分块加载
   - WebWorker 数据处理

2. **交互增强**
   - 多选标注区域
   - 键盘快捷键
   - 撤销/重做功能
   - 标注区域拖拽调整

3. **视觉改进**
   - 动画过渡
   - 自定义主题
   - 更多图表样式选项

## 注意事项

1. **CSS 导入**: 确保在使用 uPlot 的组件中导入 `'uplot/dist/uPlot.min.css'`
2. **TypeScript 类型**: uPlot 的类型定义完整，但某些高级 API 可能需要类型断言
3. **响应式**: 使用 ResizeObserver 确保图表正确调整尺寸
4. **内存管理**: uPlot 实例需要手动销毁，已在 useUplot Hook 中处理

## 总结

迁移成功完成！项目现在使用 uPlot 作为核心图表库，提供更好的性能和用户体验。所有原有功能均已保留，代码结构更加清晰，符合架构设计文档。
