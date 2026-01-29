<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { 
  Search, Filter, ChevronDown, Eye, Download, MoreHorizontal, 
  RotateCw, Play, Zap, Edit2, Watch, Circle, Trash2, ChevronLeft, ChevronRight 
} from 'lucide-vue-next';
import { SensorFile, FileStatus, DeviceType } from '../types';
import StatusBadge from './StatusBadge.vue';
import EditableTestTypeCell from './EditableTestTypeCell.vue';
import EditableNoteCell from './EditableNoteCell.vue';
import EditableDeviceCell from './EditableDeviceCell.vue';
import { useFileStore } from '../stores/fileStore';

// ===== STORE =====
const fileStore = useFileStore();
const { files, isLoading } = storeToRefs(fileStore);

// ===== LOCAL UI STATE =====
const selectedIds = ref<Set<string>>(new Set());
const activeRowMenu = ref<string | null>(null);
const filterDevice = ref<string>('All');
const filterStatus = ref<string>('All');
const searchQuery = ref('');

// ===== PAGINATION STATE =====
const currentPage = ref(1);
const pageSize = ref(20);

// ===== COMPUTED: FILTERING & PAGINATION =====
const filteredFiles = computed(() => {
    let result = files.value;

    // 1. Search
    if (searchQuery.value) {
        const q = searchQuery.value.toLowerCase();
        result = result.filter(f => 
            f.filename.toLowerCase().includes(q) || 
            (f.notes && f.notes.toLowerCase().includes(q)) ||
            f.id.toLowerCase().includes(q)
        );
    }

    // 2. Filter Device
    if (filterDevice.value !== 'All') {
        result = result.filter(f => f.deviceType === filterDevice.value);
    }

    // 3. Filter Status
    if (filterStatus.value !== 'All') {
        result = result.filter(f => f.status === filterStatus.value);
    }

    return result;
});

const totalPages = computed(() => {
    if (pageSize.value >= filteredFiles.value.length) return 1;
    return Math.ceil(filteredFiles.value.length / pageSize.value);
});

const paginatedFiles = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value;
    const end = start + pageSize.value;
    return filteredFiles.value.slice(start, end);
});

// ===== WATCHERS =====
// Reset to page 1 if filters change
watch([searchQuery, filterDevice, filterStatus, pageSize], () => {
    currentPage.value = 1;
});

const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages.value) {
        currentPage.value = page;
    }
};

// ===== LIFECYCLE =====
onMounted(() => {
    // Fetch all files for client-side pagination
    fileStore.fetchFiles({ limit: 2000 });
    
    // Refresh stats
    fileStore.fetchStats();
    document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside);
});

// ===== SELECTION HANDLERS =====
const handleSelectAll = (e: Event) => {
  const checked = (e.target as HTMLInputElement).checked;
  const newSelected = new Set(selectedIds.value);
  
  if (checked) {
    // Add all current page items
    paginatedFiles.value.forEach(f => newSelected.add(f.id));
  } else {
    // Remove all current page items
    paginatedFiles.value.forEach(f => newSelected.delete(f.id));
  }
  selectedIds.value = newSelected;
};

const handleSelectRow = (id: string) => {
  const newSelected = new Set(selectedIds.value);
  if (newSelected.has(id)) {
    newSelected.delete(id);
  } else {
    newSelected.add(id);
  }
  selectedIds.value = newSelected;
};

// ===== UPDATE HANDLERS (delegate to Store) =====
const updateTestType = (id: string, l1: string, l2: string) => {
    fileStore.updateTestType(id, l1, l2);
};

const updateNote = (id: string, note: string) => {
    fileStore.updateNote(id, note);
};

const updateDevice = (id: string, deviceType: DeviceType, deviceModel: string) => {
    fileStore.updateDevice(id, deviceType, deviceModel);
};

const triggerParse = (ids: string[]) => {
    fileStore.triggerParse(ids);
    if (ids.length > 1) selectedIds.value = new Set();
};

// ===== BATCH ACTIONS =====
const handleBatchDownload = () => {
    if (selectedIds.value.size === 0) return;
    fileStore.batchDownload(Array.from(selectedIds.value));
    selectedIds.value = new Set();
};

const handleBatchDelete = () => {
    const count = selectedIds.value.size;
    if (count === 0) return;
    
    if (!window.confirm(`Are you sure you want to delete ${count} selected file(s)?`)) return;

    const idsToDelete = Array.from(selectedIds.value);
    fileStore.deleteFiles(idsToDelete);
    selectedIds.value = new Set();
};

const deleteRow = (id: string) => {
    if (!window.confirm('Are you sure you want to delete this file?')) {
        activeRowMenu.value = null;
        return;
    }
    fileStore.deleteFile(id);
    activeRowMenu.value = null;
};

const downloadRow = (id: string) => {
    const file = files.value.find(f => f.id === id);
    if (file) {
        let name = file.filename;
        if (file.nameSuffix) {
            if (name.toLowerCase().endsWith('.rawdata')) {
                name = name.slice(0, -8) + file.nameSuffix + '.rawdata';
            } else {
                name = name + file.nameSuffix;
            }
        }
        fileStore.downloadFile(id, name);
    }
    activeRowMenu.value = null;
};

// ===== UI HELPERS =====
const handleClickOutside = (event: MouseEvent) => {
    if (activeRowMenu.value && !(event.target as Element).closest('.row-menu-container')) {
        activeRowMenu.value = null;
    }
};

</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-full overflow-hidden">
    
    <!-- 3.1 Search & Filter Bar -->
    <!-- 3.1 Search & Filter Bar -->
    <div class="p-4 border-b border-slate-100 flex flex-col lg:flex-row gap-4 justify-between items-start lg:items-center bg-white rounded-t-xl">
      
      <!-- Left Group: Search & Filters -->
      <div class="flex flex-col md:flex-row items-stretch md:items-center gap-2 w-full lg:w-auto">
        <!-- Search -->
        <div class="relative w-full md:w-80 lg:w-96">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" :size="16" />
            <input 
            type="text" 
            v-model="searchQuery"
            placeholder="Search filename, notes, or ID..." 
            class="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none placeholder-slate-400 bg-white shadow-sm transition-all"
            />
        </div>

        <!-- Filters -->
        <div class="flex items-center gap-2 overflow-x-auto no-scrollbar">
            <div class="relative">
                <select 
                class="appearance-none pl-3 pr-8 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer hover:border-slate-300 transition-colors shadow-sm text-slate-600 font-medium"
                v-model="filterDevice"
                >
                <option value="All">Device: All</option>
                <option value="Watch">Watch</option>
                <option value="Ring">Ring</option>
                </select>
                <ChevronDown class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" :size="14" />
            </div>

            <div class="relative">
                <select 
                    class="appearance-none pl-3 pr-8 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer hover:border-slate-300 transition-colors shadow-sm text-slate-600 font-medium"
                    v-model="filterStatus"
                >
                <option value="All">Status: All</option>
                <option value="unverified">Unverified</option>
                <option value="idle">Ready (Idle)</option>
                <option value="processed">Processed</option>
                <option value="failing">Failing</option>
                <option value="error">Error</option>
                </select>
                <ChevronDown class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" :size="14" />
            </div>
            
            <button class="flex items-center gap-1.5 px-3 py-2 bg-transparent text-slate-500 rounded-lg text-sm font-medium hover:bg-slate-100 transition-colors whitespace-nowrap">
                <Filter :size="16" /> Filters
            </button>
        </div>
      </div>
      
      <!-- Right Group: Batch Actions -->
      <div class="flex items-center gap-2 w-full lg:w-auto justify-end overflow-x-auto no-scrollbar">
        <div v-if="selectedIds.size > 0" class="flex items-center gap-2 animate-in fade-in duration-200">
            <span class="text-sm font-medium text-gray-600 bg-gray-100 px-3 py-2 rounded-lg whitespace-nowrap">
                {{ selectedIds.size }} Selected
            </span>
            <button 
                @click="triggerParse(Array.from(selectedIds))"
                class="flex items-center gap-1.5 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm whitespace-nowrap"
            >
                <Zap :size="16" /> Parse
            </button>
            <button 
                @click="handleBatchDownload"
                class="flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors shadow-sm whitespace-nowrap"
            >
                <Download :size="16" /> Download
            </button>
            <button 
                @click="handleBatchDelete"
                class="flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-300 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 hover:border-red-200 transition-colors shadow-sm whitespace-nowrap"
            >
                <Trash2 :size="16" /> Delete
            </button>
        </div>
      </div>
    </div>

    <!-- 3.2 The Data Table -->
    <div class="flex-1 overflow-auto custom-scrollbar min-h-0 relative">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50 sticky top-0 z-10 shadow-sm">
          <tr>
            <th scope="col" class="px-4 py-3 text-left w-12 bg-slate-50/50">
              <input 
                  type="checkbox" 
                  class="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  @change="handleSelectAll"
                  :checked="paginatedFiles.length > 0 && paginatedFiles.every(f => selectedIds.has(f.id))"
              />
            </th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider bg-slate-50/50">Status</th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider bg-slate-50/50">File Name</th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider bg-slate-50/50">File Info</th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider bg-slate-50/50">Device</th>

            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider bg-slate-50/50">Test Type</th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider min-w-[200px] bg-slate-50/50">Notes</th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider text-right bg-slate-50/50">Actions</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="row in paginatedFiles" :key="row.id" 
              class="hover:bg-blue-50/30 transition-colors" 
              :class="{ 'bg-blue-50/50': selectedIds.has(row.id) }">
            <td class="px-4 py-3 whitespace-nowrap">
                <input 
                    type="checkbox" 
                    class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    :checked="selectedIds.has(row.id)"
                    @change="handleSelectRow(row.id)"
                />
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
                <StatusBadge :status="row.status" :error="row.errorMessage" />
            </td>
            <td class="px-4 py-3">
                <span class="text-sm font-bold text-slate-800">
                    {{ row.filename.replace(/\.rawdata$/i, '') }}{{ row.nameSuffix || '' }}
                </span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
                <div class="flex flex-col">
                    <span class="text-sm text-slate-700 font-medium">{{ new Date(row.uploadTime).toLocaleString() }}</span>
                    <span class="text-xs text-slate-500">{{ row.duration }} • {{ row.size }}</span>
                </div>
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
                <EditableDeviceCell 
                    :initialDeviceType="row.deviceType"
                    :initialDeviceModel="row.deviceModel"
                    :fileId="row.id"
                    @update="updateDevice"
                />
            </td>

            <td class="px-4 py-3 whitespace-nowrap relative">
                <EditableTestTypeCell 
                    :initialL1="row.testTypeL1"
                    :initialL2="row.testTypeL2"
                    :fileId="row.id"
                    @update="updateTestType"
                />
            </td>
            <td class="px-4 py-3">
                <EditableNoteCell 
                    :initialNote="row.notes"
                    :fileId="row.id"
                    @update="updateNote"
                />
            </td>


            <td class="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                <div class="flex items-center justify-end gap-2 relative row-menu-container">
                
                <!-- 1. Start / Retry / Progress -->
                <div v-if="row.status === FileStatus.Processing" class="px-1.5 py-1 text-xs font-semibold text-blue-500 min-w-[32px] text-center bg-blue-50 rounded">
                    {{ row.progress || 0 }}%
                </div>
                <template v-else>
                    <button 
                        v-if="row.status === FileStatus.Idle"
                        @click="triggerParse([row.id])"
                        class="p-1.5 rounded hover:bg-green-50 text-slate-400 hover:text-green-700 transition-colors" 
                        title="Start Parsing"
                    >
                        <Play :size="18" />
                    </button>
                    <button 
                        v-if="row.status === FileStatus.Error || row.status === FileStatus.Processed || row.status === FileStatus.Failing"
                        @click="triggerParse([row.id])"
                        class="p-1.5 rounded transition-colors"
                        :class="row.status === FileStatus.Processed ? 'hover:bg-blue-50 text-blue-400 hover:text-blue-600' : 'hover:bg-orange-50 text-orange-400 hover:text-orange-600'" 
                        :title="row.status === FileStatus.Processed ? 'Re-parse' : 'Retry'"
                    >
                            <RotateCw :size="18" />
                    </button>
                    <!-- Unverified: Show nothing or spinner? -->
                    <span v-if="row.status === FileStatus.Unverified" class="text-xs text-slate-400 italic">Verifying...</span>
                </template>

                <!-- 2. Analyze Button -->
                <button 
                    class="p-1.5 rounded transition-colors"
                    :class="row.status === FileStatus.Processed ? 'text-blue-600 hover:text-blue-800 hover:bg-blue-100' : 'text-slate-200 cursor-not-allowed'"
                    :disabled="row.status !== FileStatus.Processed"
                    title="Analyze"
                >
                    <Eye :size="18" />
                </button>

                <!-- 3. More Actions Menu -->
                <div class="relative">
                    <button 
                        class="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                        @click.stop="activeRowMenu = activeRowMenu === row.id ? null : row.id"
                    >
                        <MoreHorizontal :size="18" />
                    </button>
                    <!-- Dropdown Menu -->
                    <div 
                        v-if="activeRowMenu === row.id" 
                        class="absolute right-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-xl z-50 flex flex-col py-1"
                    >
                        <button 
                            @click="downloadRow(row.id)"
                            class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                        >
                            <Download :size="16" /> Download
                        </button>
                        <button 
                            @click="deleteRow(row.id)"
                            class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                        >
                            <Trash2 :size="16" /> Delete
                        </button>
                    </div>
                </div>

                </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 3.3 Footer -->
    <div class="px-6 py-4 border-t border-gray-200 flex flex-col md:flex-row items-center justify-between gap-4 bg-white rounded-b-xl text-sm text-gray-600">
        
        <!-- Left: Items per page & Total count -->
        <div class="flex items-center gap-4">
            <div class="flex items-center gap-2">
                <span class="text-gray-600">Show</span>
                <div class="relative">
                    <select 
                        v-model.number="pageSize"
                        class="appearance-none bg-white border border-gray-300 text-gray-700 py-1 pl-3 pr-8 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
                    >
                        <option :value="20">20 items</option>
                        <option :value="50">50 items</option>
                        <option :value="100">100 items</option>
                    </select>
                    <ChevronDown class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" :size="14" />
                </div>
            </div>
            
            <span class="text-gray-500">
                Showing {{ filteredFiles.length > 0 ? (currentPage - 1) * pageSize + 1 : 0 }} - {{ Math.min(currentPage * pageSize, filteredFiles.length) }} of {{ filteredFiles.length }} items
            </span>
        </div>

        <!-- Right: Pagination -->
        <div class="flex items-center gap-1" v-if="totalPages > 1">
            <button 
                @click="handlePageChange(currentPage - 1)"
                :disabled="currentPage === 1"
                class="p-1 rounded hover:bg-gray-100 text-gray-600 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                title="Previous"
            >
                <ChevronLeft :size="18" />
            </button>
            
            <div class="flex items-center gap-1 px-2">
                 <button 
                    v-if="currentPage > 2"
                    @click="handlePageChange(1)"
                    class="min-w-[32px] h-8 flex items-center justify-center rounded hover:bg-gray-50 text-gray-600 transition-colors"
                >1</button>
                <span v-if="currentPage > 3" class="text-gray-400">...</span>

                <button 
                    v-if="currentPage > 1"
                    @click="handlePageChange(currentPage - 1)"
                    class="min-w-[32px] h-8 flex items-center justify-center rounded hover:bg-gray-50 text-gray-600 transition-colors"
                >{{ currentPage - 1 }}</button>

                <button class="min-w-[32px] h-8 flex items-center justify-center rounded bg-blue-50 text-blue-600 font-medium border border-blue-100">{{ currentPage }}</button>

                <button 
                    v-if="currentPage < totalPages"
                    @click="handlePageChange(currentPage + 1)"
                    class="min-w-[32px] h-8 flex items-center justify-center rounded hover:bg-gray-50 text-gray-600 transition-colors"
                >{{ currentPage + 1 }}</button>

                <span v-if="currentPage < totalPages - 2" class="text-gray-400">...</span>
                <button 
                    v-if="currentPage < totalPages - 1"
                    @click="handlePageChange(totalPages)"
                    class="min-w-[32px] h-8 flex items-center justify-center rounded hover:bg-gray-50 text-gray-600 transition-colors"
                >{{ totalPages }}</button>
            </div>

            <button 
                @click="handlePageChange(currentPage + 1)"
                :disabled="currentPage === totalPages"
                class="p-1 rounded hover:bg-gray-100 text-gray-600 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                title="Next"
            >
                <ChevronRight :size="18" />
            </button>
        </div>
    </div>
  </div>
</template>
