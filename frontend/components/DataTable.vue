<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { 
  Search, Filter, ChevronDown, Eye, Download, MoreHorizontal, 
  RotateCw, Play, Zap, Edit2, Watch, Circle, Trash2, ChevronLeft, ChevronRight 
} from 'lucide-vue-next';
import { SensorFile, FileStatus, DeviceType } from '../types';
import { MOCK_FILES, MOCK_STATS } from '../constants';
import StatusBadge from './StatusBadge.vue';





import EditableTestTypeCell from './EditableTestTypeCell.vue';
import EditableNoteCell from './EditableNoteCell.vue';
import EditableDeviceCell from './EditableDeviceCell.vue';

const data = ref<SensorFile[]>(MOCK_FILES);
const selectedIds = ref<Set<string>>(new Set());
const editingId = ref<string | null>(null);
const editingField = ref<'notes' | 'testType' | null>(null);
const activeRowMenu = ref<string | null>(null);

const filterDevice = ref<string>('All');
const filterStatus = ref<string>('All');

// Computed filters could be added here to actually filter `data`
// For now matching React implementation which uses visual-only filters in some parts, 
// but let's implement actual filtering if the original did? 
// Original: const [filterDevice, setFilterDevice] = useState<string>('All');
// But didn't actually filter the map(row => ...). It just updated state. 
// I will keep it consistent with original (UI only) or implement it if easy. 
// The original map iterates `data` directly. So filters were just UI controls.

const handleSelectAll = (e: Event) => {
  const checked = (e.target as HTMLInputElement).checked;
  if (checked) {
    selectedIds.value = new Set(data.value.map(f => f.id));
  } else {
    selectedIds.value = new Set();
  }
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

const updateField = (id: string, field: keyof SensorFile, value: any) => {
  data.value = data.value.map(item => item.id === id ? { ...item, [field]: value } : item);
  if (field !== 'notes') {
      editingId.value = null;
      editingField.value = null;
  }
};

const updateTestType = (id: string, l1: string, l2: string) => {
     console.log('[DataTable] updateTestType called', { id, l1, l2 });
     data.value = data.value.map(item => item.id === id ? { ...item, testTypeL1: l1, testTypeL2: l2 } : item);
     editingId.value = null;
     editingField.value = null;
     console.log('[DataTable] Test type updated successfully');
};

const updateNote = (id: string, note: string) => {
     console.log('[DataTable] updateNote called', { id, note });
     data.value = data.value.map(item => item.id === id ? { ...item, notes: note } : item);
     console.log('[DataTable] Note updated successfully');
};

const updateDevice = (id: string, deviceType: DeviceType, deviceModel: string) => {
     console.log('[DataTable] updateDevice called', { id, deviceType, deviceModel });
     data.value = data.value.map(item => item.id === id ? { ...item, deviceType, deviceModel } : item);
     console.log('[DataTable] Device updated successfully');
};

const triggerParse = (ids: string[]) => {
    // 1. Optimistically update status to Processing and init progress
    data.value = data.value.map(item => ids.includes(item.id) ? { ...item, status: FileStatus.Processing, progress: 0 } : item);

    if (ids.length > 1) selectedIds.value = new Set();

    // 2. Start Mock Progress Interval
    const interval = setInterval(() => {
        let anyProcessing = false;

        data.value = data.value.map(item => {
             if (ids.includes(item.id) && item.status === FileStatus.Processing) {
                 const newP = (item.progress || 0) + 10; // Increment
                 
                 // If complete
                 if (newP >= 100) {
                     return {
                        ...item,
                        status: FileStatus.Ready,
                        progress: undefined,
                         packets: item.packets.length > 0 ? item.packets : [
                            { name: 'ACC', freq: '100Hz', count: 10000, present: true },
                            { name: 'PPG', freq: '25Hz', count: 2500, present: true }
                        ],
                        duration: item.duration === '--' ? '00:10:00' : item.duration
                     };
                 }
                 
                 anyProcessing = true;
                 return { ...item, progress: newP };
             }
             return item;
        });
        
        // Stop if no relevant items are still processing
        // (This simple check might stop too early if something else sets it to processing, strict check is ids.includes)
        // But for this mock it's fine.
        const stillRunning = data.value.some(i => ids.includes(i.id) && i.status === FileStatus.Processing);
        if (!stillRunning) {
            clearInterval(interval);
        }
    }, 200); // Fast updates for demo
};

const startEditing = (id: string, field: 'testType') => {
    editingId.value = id;
    editingField.value = field;
};



// Batch Actions
const handleBatchDownload = () => {
    console.log('Downloading files:', Array.from(selectedIds.value));
    selectedIds.value = new Set();
};

const handleBatchDelete = () => {
    const idsToDelete = selectedIds.value;
    data.value = data.value.filter(item => !idsToDelete.has(item.id));
    selectedIds.value = new Set();
};

const deleteRow = (id: string) => {
    data.value = data.value.filter(item => item.id !== id);
    activeRowMenu.value = null;
};

const downloadRow = (id: string) => {
    console.log('Downloading file:', id);
    activeRowMenu.value = null;
};

// Close menu when clicking outside
const handleClickOutside = (event: MouseEvent) => {
    if (activeRowMenu.value && !(event.target as Element).closest('.row-menu-container')) {
        activeRowMenu.value = null;
    }
};

onMounted(() => {
    document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside);
});

</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col">
    
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
                <option value="Idle">Idle</option>
                <option value="Ready">Ready</option>
                <option value="Processing">Processing</option>
                <option value="Failed">Failed</option>
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
    <div class="overflow-x-auto custom-scrollbar">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th scope="col" class="px-4 py-3 text-left w-12 bg-slate-50/50">
              <input 
                  type="checkbox" 
                  class="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  @change="handleSelectAll"
                  :checked="data.length > 0 && selectedIds.size === data.length"
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
          <tr v-for="row in data" :key="row.id" 
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
                <span class="text-sm font-bold text-slate-800">{{ row.filename }}</span>
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
                        v-if="row.status === FileStatus.Failed || row.status === FileStatus.Ready"
                        @click="triggerParse([row.id])"
                        class="p-1.5 rounded transition-colors"
                        :class="row.status === FileStatus.Ready ? 'hover:bg-blue-50 text-blue-400 hover:text-blue-600' : 'hover:bg-orange-50 text-orange-400 hover:text-orange-600'" 
                        :title="row.status === FileStatus.Ready ? 'Re-parse' : 'Retry'"
                    >
                            <RotateCw :size="18" />
                    </button>
                </template>

                <!-- 2. Analyze Button -->
                <button 
                    class="p-1.5 rounded transition-colors"
                    :class="row.status === FileStatus.Ready ? 'text-blue-600 hover:text-blue-800 hover:bg-blue-100' : 'text-slate-200 cursor-not-allowed'"
                    :disabled="row.status !== FileStatus.Ready"
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
                    <select class="appearance-none bg-white border border-gray-300 text-gray-700 py-1 pl-3 pr-8 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer">
                        <option>20 items</option>
                        <option>50 items</option>
                        <option>100 items</option>
                    </select>
                    <ChevronDown class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" :size="14" />
                </div>
            </div>
            
            <span class="text-gray-500">Total {{ MOCK_STATS.totalFiles }} items</span>
        </div>

        <!-- Right: Pagination -->
        <div class="flex items-center gap-1">
            <button class="p-1 rounded hover:bg-gray-100 text-gray-400 disabled:opacity-30 transition-colors" disabled>
                <ChevronLeft :size="18" />
            </button>
            
            <button class="min-w-[32px] h-8 flex items-center justify-center rounded bg-blue-50 text-blue-600 font-medium border border-blue-100">1</button>
            <button class="min-w-[32px] h-8 flex items-center justify-center rounded hover:bg-gray-50 text-gray-600 transition-colors">2</button>
            <button class="min-w-[32px] h-8 flex items-center justify-center rounded hover:bg-gray-50 text-gray-600 transition-colors">3</button>
            <span class="px-2 text-gray-400">...</span>
            <button class="min-w-[32px] h-8 flex items-center justify-center rounded hover:bg-gray-50 text-gray-600 transition-colors">50</button>

            <button class="p-1 rounded hover:bg-gray-100 text-gray-600 transition-colors">
                <ChevronRight :size="18" />
            </button>
        </div>
    </div>
  </div>
</template>
