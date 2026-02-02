/**
 * 日志解析工具
 * 解析固件日志文件，提取时间戳、标签和内容
 */

export interface LogEntry {
    time: string;      // "[2026/1/13-3:0:48]"
    label: string;     // "alg_sleep_model" / "Unknown"
    content: string;   // 日志内容
    lineIndex: number; // 原始行号
}

// 时间戳匹配: [2026/1/13-3:0:48]
const TIMESTAMP_PATTERN = /^\[\d{4}\/\d{1,2}\/\d{1,2}-\d{1,2}:\d{1,2}:\d{1,2}\]/;
// 标签匹配: ][label_name]
const LABEL_PATTERN = /\]\[([a-zA-Z0-9_@~]+)\]/;

/**
 * 解析日志内容
 * 合并多行日志（无时间戳的行合并到上一条）
 */
export function parseLogContent(content: string): LogEntry[] {
    const lines = content.split('\n');
    const mergedData: string[] = [];
    let currentEntry = '';

    for (const rawLine of lines) {
        const line = rawLine.trim();
        if (!line) continue;

        if (TIMESTAMP_PATTERN.test(line)) {
            // 新的日志条目
            if (currentEntry) {
                mergedData.push(currentEntry);
            }
            currentEntry = line;
        } else {
            // 续行，合并到当前条目
            if (currentEntry) {
                currentEntry += ' ' + line;
            } else {
                currentEntry = line;
            }
        }
    }

    // 添加最后一条
    if (currentEntry) {
        mergedData.push(currentEntry);
    }

    // 结构化解析
    const entries: LogEntry[] = [];
    for (let i = 0; i < mergedData.length; i++) {
        const entry = mergedData[i];

        // 提取时间戳
        const timeMatch = entry.match(TIMESTAMP_PATTERN);
        const timeStr = timeMatch ? timeMatch[0] : 'N/A';

        // 提取标签
        const labelMatch = entry.match(LABEL_PATTERN);
        const labelStr = labelMatch ? labelMatch[1] : 'Unknown';

        // 提取内容（去掉时间戳和标签后的部分）
        let contentStr = entry;
        if (timeMatch) {
            contentStr = contentStr.replace(timeMatch[0], '');
        }
        if (labelMatch) {
            contentStr = contentStr.replace(`[${labelStr}]`, '');
        }
        contentStr = contentStr.trim();

        entries.push({
            time: timeStr,
            label: labelStr,
            content: contentStr,
            lineIndex: i
        });
    }

    return entries;
}

/**
 * 从解析后的条目中提取去重的标签列表
 * 返回按出现频率排序的标签
 */
export function extractLabels(entries: LogEntry[]): { label: string; count: number }[] {
    const labelCounts = new Map<string, number>();

    for (const entry of entries) {
        const count = labelCounts.get(entry.label) || 0;
        labelCounts.set(entry.label, count + 1);
    }

    // 转换为数组并按计数降序排序
    return Array.from(labelCounts.entries())
        .map(([label, count]) => ({ label, count }))
        .sort((a, b) => b.count - a.count);
}

/**
 * 查找标签首次出现的行索引
 */
export function findFirstOccurrence(entries: LogEntry[], label: string): number {
    const index = entries.findIndex(e => e.label === label);
    return index >= 0 ? index : 0;
}

/**
 * 检查文件名是否符合日志文件筛选条件
 * 条件：名称包含 "firmware" 且后缀为 ".log"
 */
export function isValidLogFile(filename: string): boolean {
    const lowerName = filename.toLowerCase();
    return lowerName.includes('firmware') && lowerName.endsWith('.log');
}
