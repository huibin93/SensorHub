<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue';
import { Network, Search, Hash, DownloadCloud, AlertCircle, CheckCircle2, Server, Wifi, Loader2, XCircle, Filter } from 'lucide-vue-next';
import { api } from '../services/api';

const deviceUrl = ref('http://192.168.50.168:8080'); // Default User URL
const isConnecting = ref(false);
const errorMsg = ref('');
const fileList = ref<any[]>([]);
const search = ref('');
const selectedFiles = ref<Set<string>>(new Set());
const pendingImports = ref<Set<string>>(new Set());
const taskStates = ref<Record<string, string>>({}); // Store task states from backend
let pollInterval: any = null;

// Filters
const filters = ref({
    mode: '',
    label: '',
    tester: ''
});

// Parsed Metadata
const parseFilename = (filename: string) => {
    // CollectionMode_Label_Tester_Date_Time_MAC.rawdata
    const name = filename.split('.')[0];
    const parts = name.split('_');
    // Forgiving parsing (at least 5 parts)
    if (parts.length < 5) return null;
    
    return {
        mode: parts[0],
        label: parts[1],
        tester: parts[2],
        date: parts[3],
        time: parts[4],
        mac: parts.length > 5 ? parts[5] : ''
    };
};

// Filtered List
const filteredFiles = computed(() => {
    let list = fileList.value;
    
    // 1. Text Search
    if (search.value) {
        const s = search.value.toLowerCase();
        list = list.filter(f => f.filename.toLowerCase().includes(s));
    }
    
    // 2. Metadata Filters
    if (filters.value.mode) {
        const m = filters.value.mode.toLowerCase();
        list = list.filter(f => f.meta?.mode.toLowerCase().includes(m));
    }
    if (filters.value.label) {
        const l = filters.value.label.toLowerCase();
        list = list.filter(f => f.meta?.label.toLowerCase().includes(l));
    }
    if (filters.value.tester) {
        const t = filters.value.tester.toLowerCase();
        list = list.filter(f => f.meta?.tester.toLowerCase().includes(t));
    }
    
    return list;
});

// Progress Counts
const completedCount = computed(() => {
    return fileList.value.filter(f => f.is_uploaded).length;
});
const totalSelectedCount = ref(0); // Tracked when import starts

// Unique Options for Filters (Optional improvement, using text input for now as per simple req)
// ...

// Selection Logic
const toggleSelection = (filename: string) => {
  if (pendingImports.value.has(filename)) return; 
  
  if (selectedFiles.value.has(filename)) {
    selectedFiles.value.delete(filename);
  } else {
    selectedFiles.value.add(filename);
  }
};

const toggleAll = () => {
  const availableToSelect = filteredFiles.value.filter(f => !f.is_uploaded && !pendingImports.value.has(f.filename));
  if (selectedFiles.value.size >= availableToSelect.length && availableToSelect.length > 0) {
    selectedFiles.value.clear();
  } else {
    availableToSelect.forEach(f => selectedFiles.value.add(f.filename));
  }
};

const isAllSelected = computed(() => {
   const available = filteredFiles.value.filter(f => !f.is_uploaded && !pendingImports.value.has(f.filename));
   return available.length > 0 && selectedFiles.value.size === available.length;
});

// Actions
const connectDevice = async (isPolling = false) => {
    if (!isPolling) {
        isConnecting.value = true;
        fileList.value = [];
        selectedFiles.value.clear();
        taskStates.value = {}; // Reset states on new connection/refresh? Maybe not if we want persistent history.
    }
    errorMsg.value = '';
    
    try {
        const res = await api.get('/devices/list', { params: { url: deviceUrl.value } });
        const newItems = res.data.items.map((item: any) => ({
            ...item,
            meta: parseFilename(item.filename)
        }));

        // Sort by Date/Time Descending (Newest -> Oldest)
        // User requested "Reverse" (Original was Ascending/Newest Bottom)
        newItems.sort((a: any, b: any) => {
             const timeA = a.meta ? (a.meta.date + a.meta.time) : '';
             const timeB = b.meta ? (b.meta.date + b.meta.time) : '';
             // If parsing failed, fallback to filename descending
             if (!timeA && !timeB) return b.filename.localeCompare(a.filename);
             if (!timeA) return 1; 
             if (!timeB) return -1;
             return timeB.localeCompare(timeA);
        });
        
        // Merge check
        fileList.value = newItems; // Simpler to just replace for now, as meta is added.
        
        // Update states based on backend task status if polling
        if (isPolling) {
             await checkTaskStatus();
        }
        
    } catch (e: any) {
        console.error(e);
        if (!isPolling) {
             errorMsg.value = e.response?.data?.detail || 'Failed to connect. Check URL/Network.';
        }
    } finally {
        if (!isPolling) isConnecting.value = false;
    }
}

const isStopping = ref(false);

// ...

const checkTaskStatus = async () => {
    try {
        const res = await api.get('/devices/tasks');
        const states = res.data;
        taskStates.value = states;
        
        // Process states
        let hasPending = false;
        let activeCount = 0;

        console.log(`[DeviceImport] Checking Status. Pending: ${pendingImports.value.size}, States received: ${Object.keys(states).length}`);

        for (const [filename, status] of Object.entries(states)) {
            if (status === 'success') {
                const f = fileList.value.find(f => f.filename === filename);
                if (f) {
                    if (!f.is_uploaded) {
                        f.is_uploaded = true; 
                        console.log(`[DeviceImport] Marked as uploaded: ${filename}`);
                    }
                }
                // ALWAYS remove from pending if success, regardless of UI state
                if (pendingImports.value.has(filename)) {
                    pendingImports.value.delete(filename);
                    console.log(`[DeviceImport] Removed from pending (Success): ${filename}`);
                }
            } else if (status === 'failed' || status === 'cancelled') {
                 if (pendingImports.value.has(filename)) {
                     pendingImports.value.delete(filename); 
                     console.log(`[DeviceImport] Removed from pending (${status}): ${filename}`);
                 }
            } else if (status === 'processing' || status === 'queued') {
                // Keep or ADD to pending if missing (e.g. page refresh)
                // BUT do not add if we are explicitly stopping
                if (!pendingImports.value.has(filename) && !isStopping.value) {
                    pendingImports.value.add(filename);
                    // If we discovered a new task on refresh, bump total logic?
                    // Use a simple heuristic: if total < pending, bump total.
                    if (totalSelectedCount.value < pendingImports.value.size) {
                        totalSelectedCount.value = pendingImports.value.size;
                    }
                }
                hasPending = true;
            }
        }
        
        if (!hasPending && pendingImports.value.size === 0) {
            stopPolling();
        }
        
    } catch (e) { 
        console.error("Failed to check task status", e);
    }
}

// ...

// (Removed duplicates)

// ... Template ...
// <div v-if="pendingImports.size > 0" ...>
//    Importing {{ totalSelectedCount - pendingImports.size }}/{{ totalSelectedCount }} files...
// </div>

const startPolling = () => {
    if (pollInterval) return;
    pollInterval = setInterval(() => {
        // connectDevice(true); // Re-fetching list is good for `is_uploaded`, but `checkTaskStatus` is better for failure.
        // Let's do both or just checkTaskStatus?
        // `connectDevice(true)` calls `checkTaskStatus`.
        connectDevice(true);
    }, 2000); 
};

const stopPolling = () => {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
};

// ...

const importSelected = async () => {
    if (selectedFiles.value.size === 0) return;
    
    const filesToImport = fileList.value.filter(f => selectedFiles.value.has(f.filename));
    totalSelectedCount.value = filesToImport.length;
    isStopping.value = false;
    
    // Mark as pending
    filesToImport.forEach(f => pendingImports.value.add(f.filename));
    selectedFiles.value.clear(); 
    
    try {
        await api.post('/devices/import', {
            device_ip: deviceUrl.value,
            files: filesToImport
        });
        startPolling();
    } catch (e: any) {
        alert("Failed to start: " + (e.response?.data?.detail || e.message));
        filesToImport.forEach(f => pendingImports.value.delete(f.filename));
    }
}

const stopImport = async () => {
    try {
        isStopping.value = true;
        await api.post('/devices/stop');
        pendingImports.value.clear();
        stopPolling();
    } catch (e) {
        console.error("Failed to stop", e);
    }
};

onUnmounted(() => {
    stopPolling();
});
</script>

<template>
  <div class="flex flex-col h-full bg-slate-50/50">
    <!-- Header -->
    <div class="px-6 py-5 border-b border-slate-200/60 bg-white sticky top-0 z-10">
        <div class="flex items-center gap-4">
             <div class="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center text-blue-600 shadow-sm ring-1 ring-blue-100">
                <Network :size="20" />
            </div>
            <div>
                <h1 class="text-xl font-bold text-slate-800 tracking-tight">Device Import</h1>
                <p class="text-xs text-slate-500 font-medium">Connect to capture devices and import raw data directly</p>
            </div>
            
            <!-- Progress Stats -->
             <div v-if="pendingImports.size > 0 || completedCount > 0" class="ml-auto flex items-center gap-4 animate-in fade-in">
                <div class="flex flex-col items-end">
                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Progress</span>
                    <span class="text-sm font-bold text-slate-700">
                        <span class="text-blue-600">{{ completedCount }}</span> 
                        <span class="text-slate-300 mx-1">/</span> 
                        <span>{{ fileList.length }} (Total)</span>
                    </span>
                 </div>
            </div>
        </div>

        <!-- Connection Bar -->
        <div class="mt-6 flex gap-3 max-w-2xl">
            <!-- ... URL Input ... -->
            <div class="flex-1 relative group">
                <div class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors">
                    <Server :size="16" />
                </div>
                <input 
                    v-model="deviceUrl"
                    type="text" 
                    placeholder="http://192.168.x.x:8080"
                    @keyup.enter="() => connectDevice(false)"
                    class="w-full pl-9 pr-4 py-2.5 text-sm font-medium text-slate-700 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-sm placeholder:text-slate-400"
                />
            </div>
            <button 
                @click="() => connectDevice(false)"
                :disabled="isConnecting"
                class="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold rounded-lg shadow-sm shadow-blue-200 transition-all flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed active:scale-95"
            >
                <Wifi v-if="!isConnecting" :size="16" />
                <div v-else class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                {{ isConnecting ? 'Connecting...' : 'Connect' }}
            </button>
        </div>
        
        <!-- Error Message -->
         <div v-if="errorMsg" class="mt-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg flex items-center gap-2 border border-red-100 animate-in fade-in slide-in-from-top-1">
            <AlertCircle :size="16" />
            {{ errorMsg }}
        </div>
        
        <!-- Filters Toolbar -->
        <div class="mt-4 pt-4 border-t border-slate-100 flex gap-3 items-center" v-if="fileList.length > 0">
             <div class="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5 mr-1">
                 <Filter :size="12" /> Filters
             </div>
             <input v-model="filters.mode" type="text" placeholder="Mode (e.g. HeartRate)" class="w-24 px-2 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:border-blue-500" />
             <input v-model="filters.label" type="text" placeholder="Label (e.g. Static)" class="w-24 px-2 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:border-blue-500" />
             <input v-model="filters.tester" type="text" placeholder="Tester" class="w-24 px-2 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:border-blue-500" />
             
             <div class="ml-auto relative w-48">
                 <Search :size="14" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                 <input v-model="search" type="text" placeholder="Search filename..." class="w-full pl-8 pr-3 py-1.5 text-xs font-semibold bg-white border border-slate-200 rounded-md focus:outline-none focus:border-blue-400" />
             </div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 overflow-hidden p-6 relative">
        <div v-if="fileList.length === 0 && !isConnecting" class="h-full flex flex-col items-center justify-center text-slate-400">
             <!-- Empty State -->
             <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                <Server :size="32" class="opacity-50" />
            </div>
            <p class="text-sm font-medium">No device connected</p>
        </div>

        <div v-else class="h-full flex flex-col bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden animate-in fade-in zoom-in-95 duration-300">
            <!-- Action Toolbar (Select/Stop/Import) -->
            <div class="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                 <div class="flex items-center gap-3">
                    <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">{{ filteredFiles.length }} Files</span>
                    
                     <!-- Pending Indicator -->
                    <div v-if="pendingImports.size > 0" class="flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 text-xs font-bold rounded-lg animate-pulse">
                        <Loader2 :size="14" class="animate-spin" />
                        Processing {{ totalSelectedCount - pendingImports.size }} / {{ totalSelectedCount }}...
                    </div>
                </div>

                <div class="flex items-center gap-3">
                     <!-- Stop Button -->
                     <button 
                        v-if="pendingImports.size > 0"
                        @click="stopImport"
                        class="flex items-center gap-2 px-3 py-1.5 bg-red-100 text-red-700 text-xs font-bold rounded-lg hover:bg-red-200 transition-all shadow-sm animate-in fade-in"
                    >
                        <XCircle :size="14" />
                        Stop
                    </button>
                    
                     <div v-if="selectedFiles.size > 0" class="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-md animate-in fade-in">
                        {{ selectedFiles.size }} Selected
                    </div>
                    <button 
                        @click="importSelected"
                        :disabled="selectedFiles.size === 0"
                        class="flex items-center gap-2 px-4 py-1.5 bg-slate-800 text-white text-xs font-bold rounded-lg hover:bg-slate-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                        <DownloadCloud :size="14" />
                        Import
                    </button>
                </div>
            </div>

            <!-- Table Header -->
            <div class="grid grid-cols-12 gap-4 px-4 py-2.5 bg-slate-50/80 text-xs font-bold text-slate-500 border-b border-slate-200 select-none">
                <div class="col-span-1 flex items-center justify-center">
                    <input type="checkbox" :checked="isAllSelected" @change="toggleAll" class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer" />
                </div>
                <div class="col-span-5">Filename / Info</div>
                <div class="col-span-2">Tester/MAC</div>
                <div class="col-span-2">Date/Time</div>
                <div class="col-span-2 text-right">Status</div>
            </div>

            <!-- List -->
            <div class="flex-1 overflow-y-auto min-h-0">
                <div 
                    v-for="file in filteredFiles" 
                    :key="file.filename"
                    class="grid grid-cols-12 gap-4 px-4 py-3 border-b border-slate-100 hover:bg-blue-50/50 transition-colors group items-center text-sm"
                    :class="{ 'bg-blue-50/30': selectedFiles.has(file.filename) }"
                >
                    <div class="col-span-1 flex items-center justify-center">
                        <input 
                            type="checkbox" 
                            :checked="selectedFiles.has(file.filename)" 
                            @change="toggleSelection(file.filename)"
                            :disabled="file.is_uploaded || pendingImports.has(file.filename)"
                            class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer disabled:opacity-50" 
                        />
                    </div>
                    <div class="col-span-5 min-w-0">
                        <div class="font-medium text-slate-700 font-mono text-xs truncate" :title="file.filename">
                            {{ file.filename }}
                        </div>
                        <div v-if="file.meta" class="flex gap-2 mt-1 text-[10px] text-slate-400">
                             <span class="bg-slate-100 px-1 rounded border border-slate-200">{{ file.meta.mode }}</span>
                             <span class="bg-slate-100 px-1 rounded border border-slate-200">{{ file.meta.label }}</span>
                        </div>
                    </div>
                    <div class="col-span-2 min-w-0 flex flex-col gap-1">
                        <span v-if="file.meta?.tester" class="text-xs text-slate-600 flex items-center gap-1">
                            <span class="opacity-50 text-[10px]">User:</span>{{ file.meta.tester }}
                        </span>
                        <span v-if="file.meta?.mac" class="text-xs text-slate-500 font-mono flex items-center gap-1">
                            <span class="opacity-50 text-[10px]">MAC:</span>{{ file.meta.mac }}
                        </span>
                    </div>
                     <div class="col-span-2 text-slate-500 text-xs flex flex-col">
                        <span>{{ file.date || '-' }}</span>
                        <span v-if="file.meta?.time" class="text-[10px] text-slate-400 font-mono">{{ file.meta.time }}</span>
                    </div>
                    <div class="col-span-2 flex justify-end">
                         <!-- Backend Status Logic -->
                         <span v-if="file.is_uploaded" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-50 text-green-700 text-[10px] font-bold border border-green-100">
                            <CheckCircle2 :size="10" />
                            Imported
                        </span>
                        <!-- Status from TaskStates -->
                        <span v-else-if="taskStates[file.filename] === 'failed'" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-50 text-red-600 text-[10px] font-bold border border-red-100" title="Upload Failed. Try again.">
                            <AlertCircle :size="10" />
                            Failed
                        </span>
                         <span v-else-if="taskStates[file.filename] === 'cancelled'" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-orange-50 text-orange-600 text-[10px] font-bold border border-orange-100">
                            Cancelled
                        </span>
                        
                        <span v-else-if="pendingImports.has(file.filename) || taskStates[file.filename] === 'processing' || taskStates[file.filename] === 'queued'" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-bold border border-blue-100">
                            <Loader2 :size="10" class="animate-spin" />
                            Importing...
                        </span>
                        <span v-else class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 text-[10px] font-bold border border-slate-200">
                            New
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </div>
  </div>
</template>
