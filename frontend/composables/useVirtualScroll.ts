/**
 * 虚拟滚动 Composable
 * 实现高性能的滚动懒加载, 支持悬停模式和自动滚动
 */
import { ref, computed, watch, onMounted, onUnmounted, type Ref } from 'vue';

// 滚动模式
export type ScrollMode = 'auto' | 'hover';

// 配置
const LINE_HEIGHT = 20; // 每行高度 (px)
const BUFFER_LINES = 50; // 上下缓冲行数
const SCROLL_THRESHOLD = 50; // 判断是否在底部的阈值 (px)

export interface VirtualScrollOptions {
    totalLines: Ref<number>;
    containerRef: Ref<HTMLElement | null>;
}

export function useVirtualScroll(options: VirtualScrollOptions) {
    const { totalLines, containerRef } = options;

    // 滚动模式
    const scrollMode = ref<ScrollMode>('auto');

    // 可见区域
    const scrollTop = ref(0);
    const containerHeight = ref(0);

    // 计算可见行范围
    const visibleStartLine = computed(() => {
        return Math.max(0, Math.floor(scrollTop.value / LINE_HEIGHT) - BUFFER_LINES);
    });

    const visibleEndLine = computed(() => {
        const visibleLines = Math.ceil(containerHeight.value / LINE_HEIGHT);
        return Math.min(totalLines.value - 1, Math.floor(scrollTop.value / LINE_HEIGHT) + visibleLines + BUFFER_LINES);
    });

    // 虚拟高度 (用于滚动条)
    const virtualHeight = computed(() => {
        return totalLines.value * LINE_HEIGHT;
    });

    // 可见区域偏移
    const visibleOffset = computed(() => {
        return visibleStartLine.value * LINE_HEIGHT;
    });

    // 是否在底部
    const isAtBottom = computed(() => {
        if (!containerRef.value) return true;
        const maxScroll = virtualHeight.value - containerHeight.value;
        return scrollTop.value >= maxScroll - SCROLL_THRESHOLD;
    });

    // 处理滚动事件
    function handleScroll(event: Event): void {
        const target = event.target as HTMLElement;
        scrollTop.value = target.scrollTop;

        // 如果滚动到底部, 切换到自动模式
        if (isAtBottom.value) {
            scrollMode.value = 'auto';
        }
    }

    // 处理鼠标滚轮事件 (触发悬停模式)
    function handleWheel(event: WheelEvent): void {
        // 向上滚动时进入悬停模式
        if (event.deltaY < 0 && scrollMode.value === 'auto') {
            scrollMode.value = 'hover';
        }
    }

    // 滚动到顶部
    function scrollToTop(): void {
        if (containerRef.value) {
            containerRef.value.scrollTop = 0;
            scrollTop.value = 0;
            scrollMode.value = 'hover';
        }
    }

    // 滚动到底部
    function scrollToBottom(): void {
        if (containerRef.value) {
            const maxScroll = virtualHeight.value - containerHeight.value;
            containerRef.value.scrollTop = maxScroll;
            scrollTop.value = maxScroll;
            scrollMode.value = 'auto';
        }
    }

    // 自动滚动 (当新数据到达且处于自动模式时)
    function autoScroll(): void {
        if (scrollMode.value === 'auto' && containerRef.value) {
            const maxScroll = virtualHeight.value - containerHeight.value;
            containerRef.value.scrollTop = maxScroll;
            scrollTop.value = maxScroll;
        }
    }

    // 更新容器尺寸
    function updateContainerSize(): void {
        if (containerRef.value) {
            containerHeight.value = containerRef.value.clientHeight;
        }
    }

    // ResizeObserver
    let resizeObserver: ResizeObserver | null = null;

    onMounted(() => {
        updateContainerSize();

        if (containerRef.value) {
            resizeObserver = new ResizeObserver(() => {
                updateContainerSize();
            });
            resizeObserver.observe(containerRef.value);
        }
    });

    onUnmounted(() => {
        if (resizeObserver) {
            resizeObserver.disconnect();
        }
    });

    // 当总行数变化时自动滚动
    watch(totalLines, () => {
        autoScroll();
    });

    return {
        // 状态
        scrollMode,
        scrollTop,
        containerHeight,
        isAtBottom,

        // 计算值
        visibleStartLine,
        visibleEndLine,
        virtualHeight,
        visibleOffset,
        lineHeight: LINE_HEIGHT,

        // 方法
        handleScroll,
        handleWheel,
        scrollToTop,
        scrollToBottom,
        autoScroll,
        updateContainerSize,
    };
}
