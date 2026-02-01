<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { Search, ChevronDown, ChevronUp, AlertTriangle, Loader2, HardDrive, X, ExternalLink } from 'lucide-vue-next';
import { Decompress } from 'fzstd';
import { fileCacheService } from '../services/fileCacheService';
import appConfig from '../config.json';

const props = defineProps<{
  id: string | null;
  isOpen: boolean;
}>();

const emit = defineEmits(['close']);

const router = useRouter();

// State
const allLines = ref<string[]>([]);
const isLoading = ref(false);
const error = ref('');
const filename = ref('');
const originalSize = ref(0);
const compressedSize = ref(0);
const loadedLines = ref(0);
const loadedFromCache = ref(false);
const isPartialLoad = ref(false);

// Performance metrics
const transferTime = ref(0);
const decompressTime = ref(0);

// Search
const searchQuery = ref('');
const searchMatches = ref<number[]>([]);
const currentMatchIndex = ref(-1);

// Virtual scroll
const LINE_HEIGHT = 20;
const containerRef = ref<HTMLElement>();
const scrollTop = ref(0);
const containerHeight = ref(800);

// Computed
const originalSizeMB = computed(() => (originalSize.value / (1024 * 1024)).toFixed(2));
const compressedSizeMB = computed(() => (compressedSize.value / (1024 * 1024)).toFixed(2));
const compressionRatio = computed(() => {
  if (originalSize.value === 0) return '0';
  return ((1 - compressedSize.value / originalSize.value) * 100).toFixed(1);
});

const totalLines = computed(() => allLines.value.length);

const visibleStart = computed(() => Math.max(0, Math.floor(scrollTop.value / LINE_HEIGHT) - 50));
const visibleEnd = computed(() => Math.min(totalLines.value, visibleStart.value + Math.ceil(containerHeight.value / LINE_HEIGHT) + 100));

const visibleLines = computed(() => {
  return allLines.value.slice(visibleStart.value, visibleEnd.value).map((line, index) => ({
    index: visibleStart.value + index,
    content: line,
    top: (visibleStart.value + index) * LINE_HEIGHT
  }));
});

const contentHeight = computed(() => totalLines.value * LINE_HEIGHT);

// Methods
const openInNewTab = () => {
  console.log(`[ClickLog] FilePreviewDrawer | Action: OpenInNewTab | FileID: ${props.id}`);
  if (props.id) {
    const routeData = router.resolve({ name: 'FileContent', params: { id: props.id } });
    window.open(routeData.href, '_blank');
  }
};

const handleScroll = (e: Event) => {
  scrollTop.value = (e.target as HTMLElement).scrollTop;
  containerHeight.value = (e.target as HTMLElement).clientHeight;
};

// Search Logic (Same as FileContentView)
const performSearch = () => {
    console.log(`[ClickLog] FilePreviewDrawer | Action: Search | Query: ${searchQuery.value}`);
    searchMatches.value = [];
    currentMatchIndex.value = -1;
    if (!searchQuery.value) return;
    const query = searchQuery.value.toLowerCase();
    allLines.value.forEach((line, index) => {
        if (line.toLowerCase().includes(query)) searchMatches.value.push(index);
    });
    if (searchMatches.value.length > 0) {
        currentMatchIndex.value = 0;
        scrollToLine(searchMatches.value[0]);
    }
};

const nextMatch = () => {
    console.log(`[ClickLog] FilePreviewDrawer | Action: NextMatch | Index: ${currentMatchIndex.value + 1}`);
    if (searchMatches.value.length === 0) return;
    currentMatchIndex.value = (currentMatchIndex.value + 1) % searchMatches.value.length;
    scrollToLine(searchMatches.value[currentMatchIndex.value]);
};

const prevMatch = () => {
    console.log(`[ClickLog] FilePreviewDrawer | Action: PrevMatch | Index: ${currentMatchIndex.value - 1}`);
    if (searchMatches.value.length === 0) return;
    currentMatchIndex.value = (currentMatchIndex.value - 1 + searchMatches.value.length) % searchMatches.value.length;
    scrollToLine(searchMatches.value[currentMatchIndex.value]);
};

const scrollToLine = (lineIndex: number) => {
    if (containerRef.value) containerRef.value.scrollTop = lineIndex * LINE_HEIGHT - containerHeight.value / 2;
};

const highlightLine = (lineContent: string, lineIndex: number) => {
    if (!searchQuery.value || !searchMatches.value.includes(lineIndex)) return escapeHtml(lineContent);
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

const escapeHtml = (text: string) => {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
};

// Load Logic - 流式解压 + 渐进式渲染
let abortController: AbortController | null = null;
const currentFileId = ref<string | null>(null);

const loadPreview = async () => {
  if (!props.id) return;
  
  // Prevent duplicate load
  if (props.id === currentFileId.value && !error.value && allLines.value.length > 0) {
      console.log(`[ClickLog] FilePreviewDrawer | Action: LoadSkip | FileID: ${props.id} | Reason: Already loaded`);
      return;
  }

  // Cancel previous request
  if (abortController) {
      abortController.abort();
      abortController = null;
  }
  abortController = new AbortController();
  const signal = abortController.signal;
  
  console.log(`[ClickLog] FilePreviewDrawer | Action: LoadPreview | FileID: ${props.id}`);
  
  currentFileId.value = props.id;
  isLoading.value = true;
  error.value = '';
  allLines.value = [];
  loadedLines.value = 0;
  isPartialLoad.value = false;
  
  const startTime = performance.now();

  try {
    // Try cache first
    let cached = null;
    try {
      cached = await fileCacheService.get(props.id);
    } catch (e) { /* ignore */ }

    if (signal.aborted) return;

    let accumulatedText = '';
    const RENDER_BATCH_SIZE = 5000; // 每 5000 行渲染一批
    
    // 解压回调：只累积文本，不做渲染
    const decompressor = new Decompress((chunk) => {
      const text = new TextDecoder('utf-8', { fatal: false }).decode(chunk);
      accumulatedText += text;
    });
    
    // 辅助函数：刷新累积的行到 UI
    const flushLines = () => {
      if (signal.aborted) return;
      const newlineCount = (accumulatedText.match(/\n/g) || []).length;
      if (newlineCount >= RENDER_BATCH_SIZE) {
        const lines = accumulatedText.split('\n');
        const completedLines = lines.slice(0, -1);
        accumulatedText = lines[lines.length - 1] || '';
        
        allLines.value.push(...completedLines);
        loadedLines.value = allLines.value.length;
        console.log(`[Drawer] Rendered ${allLines.value.length} lines...`);
      }
    };

    if (cached) {
      console.log('[Drawer] Loading from cache...');
      loadedFromCache.value = true;
      filename.value = cached.filename;
      originalSize.value = cached.originalSize;
      compressedSize.value = cached.compressedSize;
      
      // 流式解压缓存数据
      const arrayBuffer = await cached.data.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      const CHUNK_SIZE = 256 * 1024; // 256KB 分块
      
      for (let i = 0; i < uint8Array.length; i += CHUNK_SIZE) {
        if (signal.aborted) return;
        const chunk = uint8Array.slice(i, Math.min(i + CHUNK_SIZE, uint8Array.length));
        const isLast = i + CHUNK_SIZE >= uint8Array.length;
        decompressor.push(chunk, isLast);
        
        flushLines();
        await new Promise(resolve => setTimeout(resolve, 0));
      }
      
    } else {
      console.log('[Drawer] Fetching from network with streaming decompression...');
      loadedFromCache.value = false;
      
      const transferStart = performance.now();
      const response = await fetch(`/api/v1/files/${props.id}/content`, { signal });
      if (!response.ok) throw new Error(`Failed to load: ${response.statusText}`);

      filename.value = response.headers.get('X-File-Name') || 'Unknown';
      originalSize.value = parseInt(response.headers.get('X-Original-Size') || '0');
      compressedSize.value = parseInt(response.headers.get('X-Compressed-Size') || '0');

      if (!response.body) throw new Error('Response body is null');

      const reader = response.body.getReader();
      const chunks: Uint8Array[] = []; 
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          if (!signal.aborted) decompressor.push(new Uint8Array(0), true);
          break;
        }
        if (signal.aborted) break;
        
        chunks.push(value);
        
        try {
          decompressor.push(value);
        } catch (e) {
          console.warn('[Drawer] Decompression warning:', e);
        }
        
        flushLines();
        await new Promise(resolve => setTimeout(resolve, 0));
      }

      const transferEnd = performance.now();
      transferTime.value = transferEnd - transferStart;
      
      // Only cache if fully loaded and not aborted
      if (!signal.aborted) {
          const compressedData = new Blob(chunks as BlobPart[], { type: 'application/zstd' });
          try {
            await fileCacheService.set({
              fileId: props.id,
              filename: filename.value,
              data: compressedData,
              originalSize: originalSize.value,
              compressedSize: compressedSize.value,
              cachedAt: Date.now()
            });
            console.log('[Drawer] Saved to cache');
          } catch (e) {
            console.warn('[Drawer] Failed to save to cache:', e);
          }
      }
    }

    if (signal.aborted) return;

    // 处理剩余未渲染的行
    if (accumulatedText) {
      const remainingLines = accumulatedText.split('\n');
      allLines.value.push(...remainingLines);
      loadedLines.value = allLines.value.length;
    }
    
    decompressTime.value = performance.now() - startTime - transferTime.value;
    
    const totalTime = performance.now() - startTime;
    console.log(`[Drawer] Loaded ${allLines.value.length} lines in ${Math.round(totalTime)}ms`);

  } catch (err: any) {
    if (err.name === 'AbortError') {
        console.log('[Drawer] Load aborted');
        return;
    }
    error.value = err.message || 'Failed to load preview';
    console.error('[Drawer] Error:', err);
  } finally {
    if (!signal.aborted) {
         isLoading.value = false;
         abortController = null;
    }
  }
};

// Initial Load & Watch
watch([() => props.isOpen, () => props.id], ([newOpen, newId]) => {
  if (newOpen && newId) {
    loadPreview();
  }
  // No else/reset here to keep state for fast re-open (cache behavior)
});
</script>

<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <Transition name="fade">
      <div 
        v-if="isOpen" 
        @click="emit('close')" 
        class="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 transition-opacity"
      ></div>
    </Transition>
    
    <!-- Drawer -->
    <Transition name="slide-right">
      <div v-if="isOpen" class="fixed right-0 top-0 h-full w-[800px] max-w-[90vw] bg-white shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ease-out">
        
        <!-- Header -->
        <header class="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between gap-4 shrink-0">
          <div class="flex items-center gap-4 flex-1 min-w-0">
            <button @click="emit('close')" class="p-2 hover:bg-slate-100 rounded-lg transition-colors text-slate-500">
               <X :size="20" />
            </button>
            
            <div class="flex-1 min-w-0">
              <h2 class="text-lg font-bold text-slate-800 truncate">{{ filename }}</h2>
              <div class="flex items-center gap-2 text-xs text-slate-500">
                <span>{{ originalSizeMB }} MB</span>
                <span v-if="isPartialLoad" class="text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">Preview Mode</span>
                <span v-if="loadedFromCache" class="text-green-600 bg-green-50 px-1.5 py-0.5 rounded">Cached</span>
              </div>
            </div>

            <button 
                @click="openInNewTab"
                class="flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors font-medium text-sm"
            >
                <ExternalLink :size="16" />
                Open in New Tab
            </button>
          </div>
        </header>

        <!-- Search Bar -->
        <div class="px-6 py-2 border-b border-slate-100 bg-slate-50/50 flex items-center gap-2">
             <div class="relative flex-1">
                <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" :size="14" />
                <input 
                    v-model="searchQuery"
                    @input="performSearch"
                    type="text"
                    placeholder="Search in preview..."
                    class="w-full pl-9 pr-4 py-1.5 border border-slate-200 rounded-md text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
            </div>
             <div v-if="searchMatches.length > 0" class="flex items-center gap-1 text-sm text-slate-600">
                <span>{{ currentMatchIndex + 1 }}/{{ searchMatches.length }}</span>
                <button @click="prevMatch" class="p-1 hover:bg-slate-200 rounded"><ChevronUp :size="14"/></button>
                <button @click="nextMatch" class="p-1 hover:bg-slate-200 rounded"><ChevronDown :size="14"/></button>
            </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-hidden relative bg-slate-50 flex flex-col">
            <!-- Loading Overlay (Initial only) -->
            <div v-if="isLoading && loadedLines === 0" class="absolute inset-0 flex flex-col items-center justify-center bg-white/80 z-20">
                <Loader2 :size="32" class="animate-spin text-blue-600 mb-2" />
                <p class="text-slate-500">Loading preview...</p>
            </div>
            
            <!-- Loading Indicator (Progressive) -->
            <div v-if="isLoading && loadedLines > 0" class="absolute top-2 right-4 bg-white/90 backdrop-blur px-3 py-1.5 rounded-full shadow-sm border border-slate-200 z-20 flex items-center gap-2 text-xs text-blue-600">
                <Loader2 :size="12" class="animate-spin" />
                <span>Loading... ({{ loadedLines.toLocaleString() }} lines)</span>
            </div>

            <!-- Error -->
            <div v-if="error" class="flex-1 flex items-center justify-center p-8 text-center">
                <div class="text-red-500">
                    <AlertTriangle :size="32" class="mx-auto mb-2" />
                    <p>{{ error }}</p>
                </div>
            </div>

            <!-- Virtual Scroll -->
            <div 
                v-else
                ref="containerRef"
                @scroll="handleScroll"
                class="flex-1 overflow-y-auto relative font-mono text-sm"
            >
                <div class="relative" :style="{ height: contentHeight + 'px' }">
                    <div
                        v-for="line in visibleLines"
                        :key="line.index"
                        :style="{ 
                            position: 'absolute',
                            top: line.top + 'px',
                            left: 0,
                            right: 0,
                            height: LINE_HEIGHT + 'px'
                        }"
                        class="px-4 text-sm font-mono text-slate-800 whitespace-pre hover:bg-slate-50"
                        v-html="highlightLine(line.content, line.index)"
                    />
                </div>
            </div>

            <!-- Footer Hint -->
            <div class="px-6 py-2 bg-slate-100 border-t border-slate-200 text-xs text-slate-500 flex justify-between">
                <span>Loaded {{ loadedLines.toLocaleString() }} lines</span>
                <span v-if="isPartialLoad" class="flex items-center gap-1 text-amber-600">
                    <AlertTriangle :size="12" />
                    Partial preview. Open in new tab for full content.
                </span>
            </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
}
</style>
