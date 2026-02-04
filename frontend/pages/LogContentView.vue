<script setup lang="ts">
/**
 * 独立日志查看页面
 * 提供完整的日志分析功能，包含筛选、标签、虚拟滚动
 */
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Search, ChevronDown, ChevronUp, ChevronLeft, Filter, Tag, Copy, Check } from 'lucide-vue-next';
import { useLogAnalysisStore, type LogFile } from '../stores/logAnalysisStore';
import { findFirstOccurrence } from '../utils/logParser';
import type { LogEntry } from '../utils/logParser';
import WearCheckChart from '../components/WearCheckChart.vue';
import { BarChart2, X } from 'lucide-vue-next';

const props = defineProps<{
  id: string;
}>();

const route = useRoute();
const router = useRouter();
const logStore = useLogAnalysisStore();

// 虚拟滚动配置
const LINE_HEIGHT = 24;
const BUFFER = 10;

// 状态
const containerRef = ref<HTMLElement | null>(null);
const scrollTop = ref(0);
const containerHeight = ref(800);
const isLoading = ref(true);

// 搜索
const searchQuery = ref('');
const searchMatches = ref<number[]>([]);
const currentMatch = ref(0);

// 过滤
const showFilterInput = ref('');
const hideFilterInput = ref('');
const showFilter = ref('');
const hideFilter = ref('');
const useRegex = ref(false);
const isCopying = ref(false);
const showChart = ref(false);

// 标签选择
const selectedLabels = ref<Set<string>>(new Set());

// 获取当前文件
const currentFile = computed<LogFile | null>(() => {
  return logStore.getFile(props.id) || null;
});

// 初始化
// 状态
let resizeObserver: ResizeObserver | null = null;

onMounted(async () => {
  // 如果 Store 为空，尝试重新初始化
  if (logStore.files.length === 0) {
    await logStore.init();
  }
  
  if (!currentFile.value) {
    // 文件不存在，返回列表页
    router.replace({ name: 'LogAnalysis' });
    return;
  }
  
  isLoading.value = false;
  
  nextTick(() => {
    if (containerRef.value) {
      containerHeight.value = containerRef.value.clientHeight;
      
      // 监听容器大小变化
      resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          containerHeight.value = entry.contentRect.height;
        }
      });
      resizeObserver.observe(containerRef.value);
    }
  });
});

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
});

// 过滤后的条目
const filteredEntries = computed<LogEntry[]>(() => {
  if (!currentFile.value) return [];
  
  let entries = currentFile.value.entries;
  
  // 标签过滤
  if (selectedLabels.value.size > 0) {
    entries = entries.filter(e => selectedLabels.value.has(e.label));
  }
  
  // 正向过滤
  if (showFilter.value) {
    const patterns = showFilter.value.split('|').map(p => p.trim()).filter(Boolean);
    entries = entries.filter(e => {
      const text = `${e.time} ${e.label} ${e.content}`;
      return patterns.some(p => matchText(p, text));
    });
  }
  
  // 反向过滤
  if (hideFilter.value) {
    const patterns = hideFilter.value.split('|').map(p => p.trim()).filter(Boolean);
    entries = entries.filter(e => {
      const text = `${e.time} ${e.label} ${e.content}`;
      return !patterns.some(p => matchText(p, text));
    });
  }
  
  return entries;
});

// 匹配文本
const matchText = (pattern: string, text: string): boolean => {
  if (useRegex.value) {
    try {
      return new RegExp(pattern, 'i').test(text);
    } catch {
      return text.toLowerCase().includes(pattern.toLowerCase());
    }
  }
  return text.toLowerCase().includes(pattern.toLowerCase());
};

// 虚拟滚动计算
const totalLines = computed(() => filteredEntries.value.length);
const contentHeight = computed(() => totalLines.value * LINE_HEIGHT);

const visibleStart = computed(() => 
  Math.max(0, Math.floor(scrollTop.value / LINE_HEIGHT) - BUFFER)
);

const visibleEnd = computed(() => 
  Math.min(totalLines.value, Math.ceil((scrollTop.value + containerHeight.value) / LINE_HEIGHT) + BUFFER)
);

const visibleEntries = computed(() => 
  filteredEntries.value.slice(visibleStart.value, visibleEnd.value).map((entry, index) => ({
    ...entry,
    visibleIndex: visibleStart.value + index,
    top: (visibleStart.value + index) * LINE_HEIGHT
  }))
);

// 滚动处理
const handleScroll = (e: Event) => {
  const target = e.target as HTMLElement;
  scrollTop.value = target.scrollTop;
};

// 复制所有过滤后的日志
const handleCopy = async () => {
  if (filteredEntries.value.length === 0) return;
  
  const text = filteredEntries.value
    .map(e => `[${e.time}] ${e.label}: ${e.content}`)
    .join('\n');
    
  try {
    await navigator.clipboard.writeText(text);
    isCopying.value = true;
    setTimeout(() => {
      isCopying.value = false;
    }, 2000);
  } catch (err) {
    console.error('Failed to copy', err);
  }
};

// 搜索逻辑
const performSearch = () => {
  if (!searchQuery.value || filteredEntries.value.length === 0) {
    searchMatches.value = [];
    currentMatch.value = 0;
    return;
  }
  
  const query = searchQuery.value.toLowerCase();
  const matches: number[] = [];
  
  filteredEntries.value.forEach((entry, index) => {
    const text = `${entry.time} ${entry.label} ${entry.content}`.toLowerCase();
    if (text.includes(query)) {
      matches.push(index);
    }
  });
  
  searchMatches.value = matches;
  currentMatch.value = matches.length > 0 ? 0 : -1;
  
  if (matches.length > 0) {
    scrollToLine(matches[0]);
  }
};

const nextMatch = () => {
  if (searchMatches.value.length === 0) return;
  currentMatch.value = (currentMatch.value + 1) % searchMatches.value.length;
  scrollToLine(searchMatches.value[currentMatch.value]);
};

const prevMatch = () => {
  if (searchMatches.value.length === 0) return;
  currentMatch.value = (currentMatch.value - 1 + searchMatches.value.length) % searchMatches.value.length;
  scrollToLine(searchMatches.value[currentMatch.value]);
};

const scrollToLine = (lineIndex: number) => {
  if (containerRef.value) {
    containerRef.value.scrollTop = lineIndex * LINE_HEIGHT - containerHeight.value / 2;
  }
};

// 高亮文本
const highlightText = (text: string, lineIndex: number): string => {
  let result = escapeHtml(text);
  
  // 搜索高亮
  if (searchQuery.value && searchMatches.value.includes(lineIndex)) {
    const query = escapeHtml(searchQuery.value);
    const regex = new RegExp(`(${query})`, 'gi');
    result = result.replace(regex, '<span class="bg-yellow-300 text-yellow-900 font-semibold">$1</span>');
  }
  
  return result;
};

const escapeHtml = (text: string): string => {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
};

// 应用过滤器
const applyFilters = () => {
  showFilter.value = showFilterInput.value;
  hideFilter.value = hideFilterInput.value;
};

// 清除过滤器
const clearFilters = () => {
  showFilter.value = '';
  hideFilter.value = '';
  showFilterInput.value = '';
  hideFilterInput.value = '';
};

// 标签点击
const handleLabelClick = (label: string) => {
  if (selectedLabels.value.has(label)) {
    selectedLabels.value.delete(label);
  } else {
    selectedLabels.value.add(label);
  }
  selectedLabels.value = new Set(selectedLabels.value);
};

// 清空标签选择
const clearLabels = () => {
  selectedLabels.value = new Set();
};

// 跳转到标签
const jumpToLabel = (label: string) => {
  if (!currentFile.value) return;
  const index = findFirstOccurrence(filteredEntries.value, label);
  scrollToLine(index);
};

// 返回
const goBack = () => {
  router.push({ name: 'LogAnalysis' });
};

// 监听搜索输入
watch(searchQuery, () => {
  performSearch();
});
</script>

<template>
  <div class="flex flex-col h-screen bg-slate-50">
    <!-- Header -->
    <header class="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between gap-4 shrink-0">
      <div class="flex items-center gap-4 flex-1 min-w-0">
        <button 
          @click="goBack"
          class="p-2 -ml-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <ChevronLeft :size="20" />
        </button>
        
        <div class="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center text-amber-600 shrink-0">
          <Tag :size="20" />
        </div>
        
        <div class="min-w-0">
          <h1 class="text-lg font-bold text-slate-800 truncate">
            {{ currentFile?.name || 'Loading...' }}
          </h1>
          <p class="text-xs text-slate-500" v-if="currentFile">
            {{ currentFile.entries.length }} entries | {{ currentFile.labels.length }} labels | {{ currentFile.source }}
          </p>
        </div>
      </div>

      <div class="text-xs text-slate-400 font-mono">
        Log Viewer
      </div>
    </header>

    <template v-if="!isLoading && currentFile">
      <!-- Labels Bar -->
      <div v-if="currentFile.labels.length > 0" class="px-6 py-3 border-b border-slate-100 bg-slate-50/50">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider mr-2">Labels:</span>
          
          <button
            v-for="labelInfo in currentFile.labels"
            :key="labelInfo.label"
            @click="handleLabelClick(labelInfo.label)"
            @dblclick="jumpToLabel(labelInfo.label)"
            class="px-2 py-1 text-xs font-medium rounded-full transition-all cursor-pointer"
            :class="selectedLabels.has(labelInfo.label) 
              ? 'bg-amber-500 text-white' 
              : 'bg-white border border-slate-200 text-slate-600 hover:border-amber-300'"
            :title="`Click to filter, double-click to jump`"
          >
            {{ labelInfo.label }} ({{ labelInfo.count }})
          </button>

          <button
            v-if="selectedLabels.size > 0"
            @click="clearLabels"
            class="px-2 py-1 text-xs font-semibold text-red-600 bg-red-50 rounded-full hover:bg-red-100 transition-colors ml-2"
          >
            Clear All
          </button>
        </div>
      </div>

      <!-- Filter Bar -->
      <div class="px-6 py-2 border-b border-slate-100 bg-white flex items-center gap-3 flex-wrap shadow-sm z-10">
        <!-- Show Filter -->
        <div class="flex items-center gap-2">
          <span class="text-xs font-semibold text-green-600">Show:</span>
          <input
            v-model="showFilterInput"
            @keyup.enter="applyFilters"
            type="text"
            placeholder="key1|key2"
            class="w-32 px-2 py-1 text-xs bg-green-50 border border-green-200 rounded focus:outline-none focus:border-green-400"
          />
        </div>

        <!-- Hide Filter -->
        <div class="flex items-center gap-2">
          <span class="text-xs font-semibold text-red-600">Hide:</span>
          <input
            v-model="hideFilterInput"
            @keyup.enter="applyFilters"
            type="text"
            placeholder="key1|key2"
            class="w-32 px-2 py-1 text-xs bg-red-50 border border-red-200 rounded focus:outline-none focus:border-red-400"
          />
        </div>

        <!-- Regex Toggle -->
        <label class="flex items-center gap-1 text-xs font-medium text-slate-600 cursor-pointer">
          <input type="checkbox" v-model="useRegex" class="rounded border-slate-300 text-amber-600" />
          Regex
        </label>

        <!-- Apply/Clear -->
        <button
          @click="applyFilters"
          class="px-2 py-1 text-xs font-semibold text-amber-600 bg-amber-50 border border-amber-200 rounded hover:bg-amber-100 transition-colors"
        >
          Apply
        </button>
        <button
          v-if="showFilter || hideFilter"
          @click="clearFilters"
          class="px-2 py-1 text-xs font-semibold text-slate-500 bg-slate-100 rounded hover:bg-slate-200 transition-colors"
        >
          Clear
        </button>


        <div class="w-px h-4 bg-slate-200 mx-2"></div>
        
        <button
          v-if="filteredEntries.length > 0"
          @click="handleCopy"
          class="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold bg-white border border-slate-200 rounded hover:bg-slate-50 hover:text-slate-900 transition-colors"
          :class="isCopying ? 'text-green-600 border-green-200 bg-green-50' : 'text-slate-600'"
          title="Copy all currently filtered logs"
        >
          <component :is="isCopying ? Check : Copy" :size="14" :class="isCopying ? 'text-green-600' : 'text-slate-400'" />
          <span>{{ isCopying ? 'Copied!' : 'Copy All' }}</span>
        </button>

        <div class="w-px h-4 bg-slate-200 mx-2"></div>

        <button
          v-if="selectedLabels.has('wear_check_algo')"
          @click="showChart = true"
          class="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold bg-indigo-50 text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-100 transition-colors"
          title="Visualize Wear Check Algo Data"
        >
          <BarChart2 :size="14" />
          <span>Visualize</span>
        </button>

        <div class="flex-1"></div>

        <!-- Search -->
        <div class="flex items-center gap-2">
          <div class="relative">
            <Search class="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" :size="14" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search..."
              class="w-64 pl-8 pr-3 py-1 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-amber-400"
            />
          </div>
          <div v-if="searchMatches.length > 0" class="flex items-center gap-1 text-xs text-slate-600">
            <span>{{ currentMatch + 1 }}/{{ searchMatches.length }}</span>
            <button @click="prevMatch" class="p-1 hover:bg-slate-100 rounded"><ChevronUp :size="14" /></button>
            <button @click="nextMatch" class="p-1 hover:bg-slate-100 rounded"><ChevronDown :size="14" /></button>
          </div>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-hidden relative bg-slate-50">
        <div
          ref="containerRef"
          @scroll="handleScroll"
          class="h-full overflow-y-auto font-mono text-sm"
        >
          <div class="relative" :style="{ height: contentHeight + 'px' }">
            <div
              v-for="entry in visibleEntries"
              :key="entry.visibleIndex"
              :style="{
                position: 'absolute',
                top: entry.top + 'px',
                left: 0,
                right: 0,
                height: LINE_HEIGHT + 'px'
              }"
              class="px-6 whitespace-nowrap"
              :class="{
                'hover:bg-white/50': !(searchMatches.length > 0 && entry.visibleIndex === searchMatches[currentMatch]),
                'bg-yellow-100 hover:bg-yellow-100': searchMatches.length > 0 && entry.visibleIndex === searchMatches[currentMatch],
                'bg-yellow-50': searchMatches.includes(entry.visibleIndex) && (searchMatches.length === 0 || entry.visibleIndex !== searchMatches[currentMatch])
              }"
            >
              <!-- Line Number -->
              <span class="inline-block w-12 text-right text-slate-400 text-xs select-none mr-2 align-middle">
                {{ entry.lineIndex + 1 }}
              </span>
              
              <!-- Time -->
              <span class="inline-block text-blue-600 text-xs w-36 select-all mr-2 align-middle">
                {{ entry.time }}
              </span>
              
              <!-- Label -->
              <span 
                class="inline-block px-1.5 py-0.5 text-[10px] font-semibold rounded min-w-[80px] text-center mr-2 align-middle"
                :class="entry.label === 'Unknown' 
                  ? 'bg-slate-200 text-slate-600' 
                  : 'bg-amber-100 text-amber-700'"
              >
                {{ entry.label }}
              </span>
              
              <!-- Content -->
              <span 
                class="inline-block text-slate-800 whitespace-pre align-middle"
                v-html="highlightText(entry.content, entry.visibleIndex)"
              ></span>
              
              <!-- Hidden Newline for Copy -->
              <span class="inline-block w-[1px] h-[1px] overflow-hidden whitespace-pre opacity-0 select-text">{{ '\n' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-6 py-2 border-t border-slate-200 bg-white text-xs text-slate-500 flex items-center gap-4">
        <span>Showing {{ filteredEntries.length }} of {{ currentFile.entries.length }} entries</span>
        <span v-if="selectedLabels.size > 0" class="text-amber-600">
          {{ selectedLabels.size }} label(s) selected
        </span>
        <span v-if="showFilter" class="text-green-600">
          Show: {{ showFilter }}
        </span>
        <span v-if="hideFilter" class="text-red-600">
          Hide: {{ hideFilter }}
        </span>
      </div>
    </template>
    
    <div v-else class="flex-1 flex items-center justify-center text-slate-400">
      Loading...
    </div>

    <!-- Chart Drawer/Modal -->
    <div v-if="showChart" class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-8">
      <div class="bg-white rounded-xl shadow-2xl w-full h-full max-w-7xl max-h-[90vh] flex flex-col overflow-hidden relative">
        <button 
          @click="showChart = false"
          class="absolute top-4 right-4 z-10 p-2 bg-white/80 rounded-full hover:bg-slate-100 transition-colors"
        >
          <X :size="20" class="text-slate-600" />
        </button>
        <WearCheckChart :entries="filteredEntries" />
      </div>
    </div>
  </div>
</template>
