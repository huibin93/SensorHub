import { ref, computed, Ref } from 'vue';

/**
 * 文本搜索 Composable
 * 提供搜索、高亮、导航功能
 */
export function useTextSearch(lines: Ref<string[]>) {
    const searchQuery = ref('');
    const searchMatches = ref<number[]>([]);
    const currentMatchIndex = ref(-1);

    /**
     * 执行搜索
     */
    const performSearch = () => {
        searchMatches.value = [];
        currentMatchIndex.value = -1;

        if (!searchQuery.value) return;

        const query = searchQuery.value.toLowerCase();
        lines.value.forEach((line, index) => {
            if (line.toLowerCase().includes(query)) {
                searchMatches.value.push(index);
            }
        });

        if (searchMatches.value.length > 0) {
            currentMatchIndex.value = 0;
        }
    };

    /**
     * 跳转到下一个匹配
     */
    const nextMatch = () => {
        if (searchMatches.value.length === 0) return -1;
        currentMatchIndex.value = (currentMatchIndex.value + 1) % searchMatches.value.length;
        return searchMatches.value[currentMatchIndex.value];
    };

    /**
     * 跳转到上一个匹配
     */
    const prevMatch = () => {
        if (searchMatches.value.length === 0) return -1;
        currentMatchIndex.value = (currentMatchIndex.value - 1 + searchMatches.value.length) % searchMatches.value.length;
        return searchMatches.value[currentMatchIndex.value];
    };

    /**
     * HTML 转义
     */
    const escapeHtml = (text: string): string => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };

    /**
     * 高亮行内容
     * @param lineContent 行文本
     * @param lineIndex 行索引
     * @returns 带高亮标记的 HTML
     */
    const highlightLine = (lineContent: string, lineIndex: number): string => {
        if (!searchQuery.value || !searchMatches.value.includes(lineIndex)) {
            return escapeHtml(lineContent);
        }

        const isCurrent = searchMatches.value[currentMatchIndex.value] === lineIndex;
        const className = isCurrent ? 'bg-yellow-400' : 'bg-yellow-200';
        const query = searchQuery.value;

        let result = '';
        let lastIndex = 0;
        const lowerLine = lineContent.toLowerCase();
        const lowerQuery = query.toLowerCase();

        let index = lowerLine.indexOf(lowerQuery);
        while (index !== -1) {
            result += escapeHtml(lineContent.slice(lastIndex, index));
            result += `<mark class="${className}">${escapeHtml(lineContent.slice(index, index + query.length))}</mark>`;
            lastIndex = index + query.length;
            index = lowerLine.indexOf(lowerQuery, lastIndex);
        }

        result += escapeHtml(lineContent.slice(lastIndex));
        return result;
    };

    return {
        searchQuery,
        searchMatches,
        currentMatchIndex,
        performSearch,
        nextMatch,
        prevMatch,
        highlightLine,
        escapeHtml
    };
}
