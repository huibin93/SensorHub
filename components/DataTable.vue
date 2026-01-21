<script setup lang="ts">
import { ref, computed } from 'vue';
import { 
  Search, Filter, ChevronDown, Eye, Download, MoreHorizontal, 
  RotateCw, Play, Zap, Edit2, Watch, Circle 
} from 'lucide-vue-next';
import { SensorFile, FileStatus, DeviceType } from '../types';
import { MOCK_FILES, MOCK_STATS } from '../constants';
import StatusBadge from './StatusBadge.vue';
import StarRating from './StarRating.vue';
import PacketPopover from './PacketPopover.vue';
import TestTypeEditor from './TestTypeEditor.vue';

const data = ref<SensorFile[]>(MOCK_FILES);
const selectedIds = ref<Set<string>>(new Set());
const editingId = ref<string | null>(null);
const editingField = ref<'notes' | 'testType' | null>(null);

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
  if (field !== 'notes' && field !== 'rating') {
      // Notes and rating might allow staying in edit mode or not? 
      // Original logic: setEditingId(null) for all updates in updateField helper
      editingId.value = null;
      editingField.value = null;
  }
};

const updateTestType = (id: string, l1: string, l2: string) => {
     data.value = data.value.map(item => item.id === id ? { ...item, testTypeL1: l1, testTypeL2: l2 } : item);
     editingId.value = null;
     editingField.value = null;
};

const triggerParse = (ids: string[]) => {
    // Optimistically update status
    data.value = data.value.map(item => ids.includes(item.id) ? { ...item, status: FileStatus.Processing } : item);
    
    setTimeout(() => {
        data.value = data.value.map(item => {
            if (ids.includes(item.id)) {
                return {
                    ...item,
                    status: FileStatus.Ready,
                    packets: item.packets.length > 0 ? item.packets : [
                        { name: 'ACC', freq: '100Hz', count: 10000, present: true },
                        { name: 'PPG', freq: '25Hz', count: 2500, present: true }
                    ],
                    duration: item.duration === '--' ? '00:10:00' : item.duration
                };
            }
            return item;
        });
    }, 2000);

    if (ids.length > 1) selectedIds.value = new Set();
};

const startEditing = (id: string, field: 'notes' | 'testType') => {
    editingId.value = id;
    editingField.value = field;
};

const updateNote = (id: string, event: Event) => {
    const val = (event.target as HTMLInputElement).value;
    // We don't close edit mode for notes as user might be typing? 
    // Original: onChange updated state. 
    // Since we are using local state for `data`, we can just update it.
    // But `updateField` closes edit mode. 
    // Wait, original: `onChange={(e) => updateField(row.id, 'notes', e.target.value)}`
    // And `updateField` calls `setEditingId(null)`. 
    // This means typing one character would close the input if it was conditional?
    // Actually the input for notes is ALWAYS visible in the original: 
    // `<input ... value={row.notes} onChange=... />`
    // It wasn't conditional on `editingId`. 
    // The `Edit2` icon was conditional or just visual.
    // So for notes, I will just update directly without closing "edit mode" because there isn't one for notes.
    data.value = data.value.map(item => item.id === id ? { ...item, notes: val } : item);
};

</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col">
    
    <!-- 3.1 Search & Filter Bar -->
    <div class="p-4 border-b border-gray-200 flex flex-col lg:flex-row gap-4 justify-between items-center bg-gray-50/50 rounded-t-xl">
      <div class="relative w-full lg:w-96">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="16" />
        <input 
          type="text" 
          placeholder="Search filename, notes, or ID..." 
          class="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
        />
      </div>
      
      <div class="flex items-center gap-2 w-full lg:w-auto overflow-x-auto pb-2 lg:pb-0 no-scrollbar">
        
        <div v-if="selectedIds.size > 0" class="flex items-center gap-2 animate-in fade-in duration-200">
            <span class="text-sm font-medium text-gray-600 bg-gray-100 px-3 py-2 rounded-lg">
                {{ selectedIds.size }} Selected
            </span>
            <button 
                @click="triggerParse(Array.from(selectedIds))"
                class="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
            >
                <Zap :size="16" /> Parse Selected
            </button>
            <div class="h-6 w-px bg-gray-300 mx-1"></div>
        </div>

        <div class="relative">
            <select 
            class="appearance-none pl-3 pr-8 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer hover:border-gray-400 transition-colors"
            v-model="filterDevice"
            >
            <option value="All">Device: All</option>
            <option value="Watch">Watch</option>
            <option value="Ring">Ring</option>
            </select>
            <ChevronDown class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" :size="14" />
        </div>

        <div class="relative">
            <select 
                class="appearance-none pl-3 pr-8 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer hover:border-gray-400 transition-colors"
                v-model="filterStatus"
            >
            <option value="All">Status: All</option>
            <option value="Idle">Idle</option>
            <option value="Ready">Ready</option>
            <option value="Processing">Processing</option>
            <option value="Failed">Failed</option>
            </select>
            <ChevronDown class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" :size="14" />
        </div>
        
        <button class="flex items-center gap-1.5 px-4 py-2 bg-gray-100 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors ml-auto lg:ml-0">
        <Filter :size="16" /> Filters
        </button>
      </div>
    </div>

    <!-- 3.2 The Data Table -->
    <div class="overflow-x-auto custom-scrollbar">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th scope="col" class="px-4 py-3 text-left w-12">
              <input 
                  type="checkbox" 
                  class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  @change="handleSelectAll"
                  :checked="data.length > 0 && selectedIds.size === data.length"
              />
            </th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">File Info</th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Device</th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Data Content</th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Test Type</th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Rating</th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider min-w-[200px]">Notes</th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider text-right">Actions</th>
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
                <div class="flex flex-col">
                <span class="text-sm font-medium text-gray-900">{{ row.filename }}</span>
                <span class="text-xs text-gray-400 font-mono">ID: {{ row.id }}</span>
                <span class="text-xs text-gray-400">{{ new Date(row.uploadTime).toLocaleDateString() }}</span>
                </div>
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
                <div class="flex flex-col">
                <div class="flex items-center gap-1.5">
                    <Watch v-if="row.deviceType === DeviceType.Watch" :size="14" class="text-blue-500" />
                    <Circle v-else :size="14" class="text-teal-500" />
                    <span class="text-sm text-gray-700">{{ row.deviceModel }}</span>
                </div>
                <span class="text-xs text-gray-400">{{ row.duration }} • {{ row.size }}</span>
                </div>
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
                <PacketPopover :packets="row.packets" />
            </td>
            <td class="px-4 py-3 whitespace-nowrap relative">
                <!-- Test Type Editable -->
                <div 
                    class="cursor-pointer group flex items-center gap-1"
                    @click="startEditing(row.id, 'testType')"
                >
                        <div class="flex flex-col">
                        <span class="text-sm font-medium text-gray-800">{{ row.testTypeL1 }}</span>
                        <span class="text-xs text-gray-500">{{ row.testTypeL2 }}</span>
                        </div>
                        <Edit2 :size="10" class="text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <!-- Inline Editor -->
                <TestTypeEditor 
                    v-if="editingId === row.id && editingField === 'testType'"
                    :file="row"
                    @update="updateTestType"
                    @close="editingId = null; editingField = null;" 
                />
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
                <StarRating :modelValue="row.rating" @update:modelValue="(v: number) => updateField(row.id, 'rating', v)" />
            </td>
            <td class="px-4 py-3">
                <!-- Inline Note Editing -->
                <div class="relative group">
                <input
                    type="text"
                    class="w-full bg-transparent border-b border-transparent focus:border-blue-500 focus:bg-white text-sm text-gray-600 focus:text-gray-900 outline-none transition-all placeholder-gray-300 truncate"
                    :value="row.notes"
                    @input="(e) => updateNote(row.id, e)"
                    placeholder="Add a note..."
                />
                <Edit2 :size="12" class="absolute right-0 top-1/2 -translate-y-1/2 text-gray-300 opacity-0 group-hover:opacity-100 pointer-events-none" />
                </div>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                <div class="flex items-center justify-end gap-2">
                
                <!-- Action Buttons based on status -->
                <button 
                    v-if="row.status === FileStatus.Idle"
                    @click="triggerParse([row.id])"
                    class="p-1.5 rounded hover:bg-green-50 text-green-600 transition-colors" 
                    title="Start Parsing"
                >
                    <Play :size="18" />
                </button>

                <button 
                    class="p-1.5 rounded hover:bg-gray-100 transition-colors"
                    :class="row.status === FileStatus.Ready ? 'text-blue-600' : 'text-gray-300 cursor-not-allowed'"
                    :disabled="row.status !== FileStatus.Ready"
                    title="Analyze"
                >
                    <Eye :size="18" />
                </button>
                <button 
                    class="p-1.5 rounded hover:bg-gray-100 text-gray-600 transition-colors"
                    title="Download Raw Data"
                >
                    <Download :size="18" />
                </button>
                <button 
                    v-if="row.status === FileStatus.Failed"
                    @click="triggerParse([row.id])"
                    class="p-1.5 rounded hover:bg-gray-100 text-orange-600 transition-colors" 
                    title="Retry"
                >
                        <RotateCw :size="18" />
                </button>
                <button class="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
                    <MoreHorizontal :size="18" />
                </button>
                </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 3.3 Footer -->
    <div class="p-4 border-t border-gray-200 flex items-center justify-between bg-gray-50 rounded-b-xl text-sm text-gray-600">
        <div class="flex items-center gap-2">
        <span>Showing 1 to {{ data.length }} of {{ MOCK_STATS.totalFiles }} items</span>
        </div>
        <div class="flex items-center gap-2">
            <button class="px-3 py-1 border border-gray-300 rounded hover:bg-white disabled:opacity-50" disabled>Previous</button>
            <button class="px-3 py-1 bg-blue-600 text-white rounded shadow-sm">1</button>
            <button class="px-3 py-1 border border-gray-300 rounded hover:bg-white">2</button>
            <button class="px-3 py-1 border border-gray-300 rounded hover:bg-white">3</button>
            <span class="text-gray-400">...</span>
            <button class="px-3 py-1 border border-gray-300 rounded hover:bg-white">50</button>
            <button class="px-3 py-1 border border-gray-300 rounded hover:bg-white">Next</button>
        </div>
    </div>
  </div>
</template>
