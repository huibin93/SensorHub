
目标是把当前“全部解压后再解析”的路径替换为“按 nl+10帧分批，在子进程内读→解压→解析，主进程仅按源顺序合并结果”，并保持失败即终止、最终结果顺序严格等于源文件顺序。重构范围严格限定你指定的 5 个模块，并移除为历史调用保留的兼容路径，按新架构统一入口。

**Steps**
1. 在 [backend/app/services/parser_types.py](backend/app/services/parser_types.py) 新增并统一并行解析类型定义：FrameMeta、BatchMeta、WorkerInput、WorkerOutput、PartialParsedResult、AggregateResult，明确 worker 入参/出参可序列化（Windows spawn 友好）。
2. 在 [backend/app/services/parser_dispatcher.py](backend/app/services/parser_dispatcher.py#L100) 重写并行主流程：保留 [validate_frame_index](backend/app/services/parser_dispatcher.py#L25)；新增按 nl + 最小10帧切批函数；删除当前 decompressed_frames/grouped_texts 全量缓存路径。
3. 在 [backend/app/services/parser_dispatcher.py](backend/app/services/parser_dispatcher.py) 增加顶层 worker 函数（非嵌套函数）：单批次内执行 seek/read + zstd 解压 + parse_lines，立即返回结构化结果；禁止返回大文本，降低 IPC 开销。
4. 在 [backend/app/services/parser_dispatcher.py](backend/app/services/parser_dispatcher.py) 使用 ProcessPoolExecutor 调度批次，as_completed 收集后按 batch_id 重排合并；任何 batch 异常立即 cancel 未完成任务并抛错（不降级、不跳过）。
5. 在 [backend/app/services/parser_worker.py](backend/app/services/parser_worker.py#L82) 调整解析聚合契约：保证 parse_lines 适配“批次独立解析”；补充/重构批次结果合并函数（替代 dispatcher 内手写大段字段拼接），保留最终 merge_acc_items/merge_ppg_items + build_dataframes 链路。
6. 在 [backend/app/services/parser.py](backend/app/services/parser.py#L174) 切换到新 dispatcher 接口与参数（固定批次策略 nl+10）；移除旧兼容包装入口 [backend/app/services/parser.py](backend/app/services/parser.py#L280-L305)，让 parse_file 只走新流程。
7. 在 [backend/app/services/parse_progress.py](backend/app/services/parse_progress.py#L30) 增加并行批次进度映射规范（例如 completed_batches/total_batches → 0-90），确保仍然单调递增并与现有 SSE 订阅行为兼容。
8. 文档同步：更新 [doc/系统设计文档：高性能 Zstd 并行解析器.md](doc/%E7%B3%BB%E7%BB%9F%E8%AE%BE%E8%AE%A1%E6%96%87%E6%A1%A3%EF%BC%9A%E9%AB%98%E6%80%A7%E8%83%BD%20Zstd%20%E5%B9%B6%E8%A1%8C%E8%A7%A3%E6%9E%90%E5%99%A8.md) 中与实现不一致处（当前实现从线程全量缓存改为进程批次流式）。

**Verification**
- 静态验证：运行 backend 单测入口并至少覆盖 parser 模块；重点断言“结果顺序 == 源 batch 顺序”“任一批次异常即整体失败”。
- 功能验证：用真实 数据库中的压缩 文件触发一次解析，检查 SSE 进度单调、最终 processed/error 状态正确。
- 性能验证：对同一输入对比重构前后峰值内存与总耗时，确认不再出现“全量解压字符串驻留”。

**Decisions**
- 并行模型：ProcessPool 主方案。
- 顺序约束：允许子进程完成先后无序，但主进程最终合并必须严格按源顺序。
- 异常策略：失败即终止，不做降级回退。
- 批次策略：nl + 最小10帧，且不考虑向前兼容旧测试/旧接口。
