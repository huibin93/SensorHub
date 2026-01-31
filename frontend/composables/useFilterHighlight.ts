/**
 * 过滤高亮 Composable
 * 支持关键字高亮和行过滤功能
 */
import { ref, computed } from 'vue';
import type { DataLine } from './useDataBuffer';

// 高亮规则
export interface HighlightRule {
    id: string;
    pattern: string;
    color: string;
    isRegex: boolean;
}

// 过滤器类型
export type FilterType = 'include' | 'exclude';

// 过滤规则
export interface FilterRule {
    type: FilterType;
    patterns: string[];  // 用 | 分隔的关键字
    isRegex: boolean;
}

// 默认高亮颜色
const HIGHLIGHT_COLORS = [
    '#fbbf24', // yellow
    '#34d399', // green
    '#60a5fa', // blue
    '#f472b6', // pink
    '#a78bfa', // purple
    '#fb923c', // orange
];

export function useFilterHighlight() {
    // 高亮规则
    const highlightRules = ref<HighlightRule[]>([]);

    // 过滤器
    const includeFilter = ref<FilterRule>({
        type: 'include',
        patterns: [],
        isRegex: false,
    });

    const excludeFilter = ref<FilterRule>({
        type: 'exclude',
        patterns: [],
        isRegex: false,
    });

    // 是否启用过滤
    const filterEnabled = ref(false);

    // 添加高亮规则
    function addHighlightRule(pattern: string, isRegex = false): void {
        if (!pattern.trim()) return;

        const colorIndex = highlightRules.value.length % HIGHLIGHT_COLORS.length;
        highlightRules.value.push({
            id: Date.now().toString(),
            pattern: pattern.trim(),
            color: HIGHLIGHT_COLORS[colorIndex],
            isRegex,
        });
    }

    // 移除高亮规则
    function removeHighlightRule(id: string): void {
        highlightRules.value = highlightRules.value.filter(r => r.id !== id);
    }

    // 清空所有高亮规则
    function clearHighlightRules(): void {
        highlightRules.value = [];
    }

    // 设置包含过滤器 (显示匹配的行)
    function setIncludeFilter(text: string, isRegex = false): void {
        includeFilter.value = {
            type: 'include',
            patterns: text.split('|').map(p => p.trim()).filter(Boolean),
            isRegex,
        };
    }

    // 设置排除过滤器 (不显示匹配的行)
    function setExcludeFilter(text: string, isRegex = false): void {
        excludeFilter.value = {
            type: 'exclude',
            patterns: text.split('|').map(p => p.trim()).filter(Boolean),
            isRegex,
        };
    }

    // 清空过滤器
    function clearFilters(): void {
        includeFilter.value.patterns = [];
        excludeFilter.value.patterns = [];
    }

    // 检查文本是否匹配模式
    function matchesPattern(text: string, pattern: string, isRegex: boolean): boolean {
        if (!pattern) return false;

        try {
            if (isRegex) {
                const regex = new RegExp(pattern, 'i');
                return regex.test(text);
            } else {
                return text.toLowerCase().includes(pattern.toLowerCase());
            }
        } catch {
            // 正则表达式语法错误
            return false;
        }
    }

    // 检查行是否应该显示
    // 规则: 同时命中显示和不显示时, 显示优先
    function shouldShowLine(line: DataLine): boolean {
        if (!filterEnabled.value) return true;

        const text = line.content;

        // 检查包含过滤器
        const includePatterns = includeFilter.value.patterns;
        const excludePatterns = excludeFilter.value.patterns;

        // 如果没有任何过滤器, 显示所有行
        if (includePatterns.length === 0 && excludePatterns.length === 0) {
            return true;
        }

        // 检查是否匹配包含过滤器
        const matchesInclude = includePatterns.length === 0 ||
            includePatterns.some(p => matchesPattern(text, p, includeFilter.value.isRegex));

        // 检查是否匹配排除过滤器
        const matchesExclude = excludePatterns.some(p =>
            matchesPattern(text, p, excludeFilter.value.isRegex)
        );

        // 同时命中显示和不显示时, 显示优先
        if (matchesInclude && matchesExclude) {
            return true;
        }

        // 如果匹配排除模式, 不显示
        if (matchesExclude) {
            return false;
        }

        // 如果有包含模式但不匹配, 不显示
        if (includePatterns.length > 0 && !matchesInclude) {
            return false;
        }

        return true;
    }

    // 高亮文本内容
    function highlightText(text: string): string {
        if (highlightRules.value.length === 0) {
            return escapeHtml(text);
        }

        let result = escapeHtml(text);

        for (const rule of highlightRules.value) {
            try {
                const regex = rule.isRegex
                    ? new RegExp(`(${rule.pattern})`, 'gi')
                    : new RegExp(`(${escapeRegex(rule.pattern)})`, 'gi');

                result = result.replace(regex,
                    `<span style="background-color: ${rule.color}; color: #000; padding: 0 2px; border-radius: 2px;">$1</span>`
                );
            } catch {
                // 正则表达式语法错误, 跳过
            }
        }

        return result;
    }

    // 转义HTML特殊字符
    function escapeHtml(text: string): string {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // 转义正则表达式特殊字符
    function escapeRegex(text: string): string {
        return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    return {
        // 高亮
        highlightRules,
        addHighlightRule,
        removeHighlightRule,
        clearHighlightRules,
        highlightText,

        // 过滤
        includeFilter,
        excludeFilter,
        filterEnabled,
        setIncludeFilter,
        setExcludeFilter,
        clearFilters,
        shouldShowLine,
    };
}
