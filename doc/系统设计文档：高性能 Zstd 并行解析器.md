这是一个针对 **Zstd 大文件并行解压与解析系统** 的技术设计文档。

该设计充分利用了你提供的 Frame 元数据（特别是 `nl` 标记），采用了 **"Clean Batching"（纯净分批）** 策略，实现了 Worker 进程间的完全解耦，最大化并行吞吐量并最小化 IPC（进程间通信）开销。

---

# 系统设计文档：高性能 Zstd 并行解析器

## 1. 设计概述

本系统旨在高效处理 GB/TB 级别的 Zstd 压缩文本文件。通过预生成的 Frame 索引信息，将大文件逻辑切分为独立的“任务包（Batch）”，分发至多核 CPU 并行处理。

### 核心优势

* **零跨进程拼接**：利用 `nl` (Ends With Newline) 标记，确保每个 Batch 的边界在物理上和逻辑上都是完整的行，主进程无需处理任何字符拼接。
* **内存感知**：利用 OS Page Cache 共享文件内存，仅在 Worker 内部申请解压所需的瞬时内存。
* **线性扩展**：吞吐量随 CPU 核心数线性增加，仅受限于内存带宽或磁盘 IO。

---

## 2. 核心架构原理

### 2.1 数据模型：Smart Batching (智能分批)

系统不再按照固定数量分批，而是基于数据完整性分批。

* **定义**：一个 Batch 包含多个连续 Frame。
* **终止条件**：
1. 累积 Frame 数量达到 `MIN_BATCH_SIZE=10`。
2. **且** 当前 Frame 的 `nl` 字段为 `True`。


* **结果**：
* **Batch Start**：必定是新的一行的开始（因为上一个 Batch 必定以换行符结束）。
* **Batch End**：必定是一行的结束。
* **独立性**：Worker 进程只需返回解析后的结构化数据 (`Dict`)。



### 2.2 处理流程 (Pipeline)

1. **Generator (主进程)**:
* 读取 Frame 索引列表。
* 应用 "Smart Batching" 策略，动态生成任务包。
* 将任务包元数据（Metadata Only）推送到任务队列。


2. **Workers (子进程池)**:
* **Seek & Read**: 根据 `cs` (Compressed Start) 和 `cl` (Compressed Length) 直接定位并读取压缩块。
* **Decompress**: 在内存中解压为文本块。
* **Internal Stitching**: 处理 Batch **内部** Frame 之间的断行拼接（Worker 内部闭环）。
* **Parse**: 调用解析逻辑，将文本转换为 `DataFrame` 或 `List`。
* **Return**: 返回结构化数据字典。


3. **Aggregator (主进程)**:
* 收集 Worker 返回的字典,与序号。
* 执行轻量级合并（List Append）。
* 最终统一执行 `Concat` 操作。



---

## 3. 详细模块设计

### 3.1 输入数据规范

系统依赖以下元数据字段进行调度：

* `cs`: 文件指针定位 (Seek)。
* `cl`: 读取字节数 (Read)。
* `dl`: 解压缓冲区预分配 (Memory optimization)。
* `nl`: **批次切分依据 (Batch Boundary)**。

### 3.2 内存与 IO 策略

| 资源 | 策略 | 说明 |
| --- | --- | --- |
| **磁盘 IO** | Random Access + OS Page Cache | 多进程只读打开同一文件路径。操作系统负责缓存热点数据页，避免应用层重复加载。 |
| **压缩内存** | 瞬时 (Transient) | 读取 `cl` 长度的 bytes，解压后立即释放。 |
| **解压内存** | 预分配 (Pre-allocated) | 使用 `dl` 参数初始化解压 buffer，避免动态扩容带来的 `realloc` 开销。 |
| **结果内存** | 紧凑传输 (Compact Transfer) | Worker 仅回传处理好的高密度数据（如 DataFrame），避免回传原始字符串。 |




---

## 4. 进程间通信 (IPC) 设计

为了最小化序列化（Pickle）开销，设计如下：

* **入参 (Main -> Worker)**:
* `file_path` (str)
* `batch_metadata` (List[Dict]): 仅包含数十个 Frame 的元数据信息，极小。
* 分包序号


* **出参 (Worker -> Main)**:
* `result_dict` (Dict): 包含解析后的业务数据。
* 分包序号



---

## 5. 异常处理与容错

1. **数据损坏 (Corrupt Frame)**:
* Zstd 解压失败会抛出异常。
* Worker 捕获异常并抛出 `(Batch_ID, Error)`。
* 主进程记录错误日志并立即终止整个解析任务（Fail-Fast，无降级回退）。


2. **逻辑错误 (Invalid Split)**:
* 如果 Batch 结束时 `nl=True` 但解压出的文本最后字符不是 `\n`，说明索引数据有误。
* 设计校验机制：Worker 结束时检查 `internal_buffer` 是否为空。如果不为空，标记为“截断错误”。



---

## 6. 性能预估

假设环境：16核 CPU，NVMe SSD。

* **CPU 利用率**: 接近 100%（解压与解析完全并行）。
* **IO 瓶颈**: 极低。顺序读取被随机读取取代，但由于每个 Batch 读取数据量大（MB级别），磁盘吞吐依然高效。
* **主要瓶颈**: 解析逻辑 (`parse_lines`) 的复杂度。
* **加速比**: 理想情况下接近  (K为核心数)。

---

## 7. 总结

该设计通过引入 **基于 `nl` 标记的智能分批策略**，成功将一个复杂的流式解压问题转化为**易于并行的“独立任务包”问题**。这不仅降低了代码实现的复杂度，更消除了并行计算中昂贵的同步与数据拼接成本，是处理此类数据的最优架构。