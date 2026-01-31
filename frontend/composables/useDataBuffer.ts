/**
 * 数据缓冲管理 Composable
 * 分块存储串口数据, 支持内存限制和阈值告警
 */
import { ref, computed, shallowRef } from 'vue';

// 配置常量
const CHUNK_SIZE = 32 * 1024 * 1024; // 32MB per chunk
const MAX_MEMORY = 512 * 1024 * 1024; // 512MB total
const MAX_CHUNKS = Math.floor(MAX_MEMORY / CHUNK_SIZE); // 16 chunks
const WARNING_THRESHOLD = 0.8; // 80%
const STOP_THRESHOLD = 1.0; // 100%

// 数据行接口
export interface DataLine {
    index: number;       // 全局行号
    timestamp: number;   // 时间戳 (ms)
    content: string;     // 文本内容
    raw: Uint8Array;     // 原始字节
    chunkIndex: number;  // 所属块索引
}

// 数据块接口
export interface DataChunk {
    index: number;
    lines: DataLine[];
    size: number;        // 当前块大小 (bytes)
    startLineIndex: number;
    endLineIndex: number;
}

// 存储状态
export type StorageStatus = 'normal' | 'warning' | 'full';

export function useDataBuffer() {
    // 数据块存储
    const chunks = shallowRef<DataChunk[]>([]);

    // 统计信息
    const totalLines = ref(0);
    const totalSize = ref(0);
    const storageStatus = ref<StorageStatus>('normal');

    // 是否暂停接收 (达到100%时)
    const isPaused = ref(false);

    // 当前未完成行的缓冲 (用于处理不完整的行)
    let pendingBuffer = '';

    // 是否显示时间戳
    const showTimestamp = ref(true);
    // 是否显示行号
    const showLineNumber = ref(true);

    // 回调
    let onWarningCallback: (() => void) | null = null;
    let onFullCallback: (() => void) | null = null;

    // 使用率
    const usagePercent = computed(() => {
        return totalSize.value / MAX_MEMORY;
    });

    // 格式化的内存使用
    const memoryUsage = computed(() => {
        const usedMB = (totalSize.value / (1024 * 1024)).toFixed(1);
        const totalMB = (MAX_MEMORY / (1024 * 1024)).toFixed(0);
        return `${usedMB} / ${totalMB} MB`;
    });

    // 获取当前块或创建新块
    function getCurrentChunk(): DataChunk {
        const allChunks = chunks.value;
        if (allChunks.length === 0 || allChunks[allChunks.length - 1].size >= CHUNK_SIZE) {
            // 创建新块
            const newChunk: DataChunk = {
                index: allChunks.length,
                lines: [],
                size: 0,
                startLineIndex: totalLines.value,
                endLineIndex: totalLines.value,
            };
            chunks.value = [...allChunks, newChunk];
            return newChunk;
        }
        return allChunks[allChunks.length - 1];
    }

    // 添加数据
    function appendData(data: Uint8Array): DataLine[] {
        // 检查是否已满
        if (isPaused.value) {
            return [];
        }

        // 将字节转换为字符串
        const decoder = new TextDecoder('utf-8');
        const text = pendingBuffer + decoder.decode(data);

        // 按换行符分割
        const parts = text.split(/\r?\n/);

        // 最后一部分可能是不完整的行
        pendingBuffer = parts.pop() || '';

        const newLines: DataLine[] = [];
        const timestamp = Date.now();

        for (const content of parts) {
            const line: DataLine = {
                index: totalLines.value,
                timestamp,
                content,
                raw: new TextEncoder().encode(content),
                chunkIndex: chunks.value.length > 0 ? chunks.value.length - 1 : 0,
            };

            const chunk = getCurrentChunk();
            chunk.lines.push(line);
            chunk.size += line.raw.length;
            chunk.endLineIndex = line.index;
            line.chunkIndex = chunk.index;

            totalLines.value++;
            totalSize.value += line.raw.length;

            newLines.push(line);
        }

        // 触发任何强制更新
        chunks.value = [...chunks.value];

        // 检查阈值
        checkThresholds();

        return newLines;
    }

    // 检查内存阈值
    function checkThresholds(): void {
        const usage = usagePercent.value;

        if (usage >= STOP_THRESHOLD) {
            if (storageStatus.value !== 'full') {
                storageStatus.value = 'full';
                isPaused.value = true;
                if (onFullCallback) {
                    onFullCallback();
                }
            }
        } else if (usage >= WARNING_THRESHOLD) {
            if (storageStatus.value === 'normal') {
                storageStatus.value = 'warning';
                if (onWarningCallback) {
                    onWarningCallback();
                }
            }
        }
    }

    // 清空所有数据
    function clear(): void {
        chunks.value = [];
        totalLines.value = 0;
        totalSize.value = 0;
        pendingBuffer = '';
        storageStatus.value = 'normal';
        isPaused.value = false;
    }

    // 恢复接收 (清空后)
    function resume(): void {
        if (usagePercent.value < STOP_THRESHOLD) {
            isPaused.value = false;
            if (usagePercent.value < WARNING_THRESHOLD) {
                storageStatus.value = 'normal';
            } else {
                storageStatus.value = 'warning';
            }
        }
    }

    // 获取指定范围的行
    function getLines(startIndex: number, endIndex: number): DataLine[] {
        const result: DataLine[] = [];
        for (const chunk of chunks.value) {
            if (chunk.endLineIndex < startIndex) continue;
            if (chunk.startLineIndex > endIndex) break;

            for (const line of chunk.lines) {
                if (line.index >= startIndex && line.index <= endIndex) {
                    result.push(line);
                }
            }
        }
        return result;
    }

    // 格式化行显示
    function formatLine(line: DataLine): string {
        const parts: string[] = [];

        if (showLineNumber.value) {
            parts.push(String(line.index + 1).padStart(6, ' '));
        }

        if (showTimestamp.value) {
            const date = new Date(line.timestamp);
            const ts = `[${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}.${String(date.getMilliseconds()).padStart(3, '0')}]`;
            parts.push(ts);
        }

        parts.push(line.content);

        return parts.join(' ');
    }

    // 设置回调
    function onWarning(callback: () => void): void {
        onWarningCallback = callback;
    }

    function onFull(callback: () => void): void {
        onFullCallback = callback;
    }

    // 导出数据为文本
    function exportAsText(): string {
        const lines: string[] = [];
        for (const chunk of chunks.value) {
            for (const line of chunk.lines) {
                lines.push(formatLine(line));
            }
        }
        return lines.join('\n');
    }

    return {
        // 状态
        chunks,
        totalLines,
        totalSize,
        storageStatus,
        isPaused,
        usagePercent,
        memoryUsage,

        // 配置
        showTimestamp,
        showLineNumber,

        // 方法
        appendData,
        clear,
        resume,
        getLines,
        formatLine,
        exportAsText,

        // 回调
        onWarning,
        onFull,
    };
}
