<script setup lang="ts">
import { ref, computed } from 'vue';
import { X, Check, AlertCircle } from 'lucide-vue-next';
import { DeviceType } from '../types';
import { deviceTypeOptions, deviceModels, fetchDevices } from '../stores/deviceStore';
import { testTypesL1, getTestTypesL2, fetchTestTypes } from '../stores/testTypeStore';

const props = defineProps<{
  isOpen: boolean;
  selectedCount: number;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'confirm', updates: { 
      deviceType?: string; 
      deviceModel?: string; 
      testTypeL1?: string; 
      testTypeL2?: string; 
      notes?: string; 
  }): void;
}>();

// Fields state
const updateDevice = ref(false);
const updateTestType = ref(false);
const updateNotes = ref(false);

const selectedDeviceType = ref<DeviceType | 'Unknown'>('Unknown');
const selectedDeviceModel = ref('');
const selectedL1 = ref('');
const selectedL2 = ref('--');
const notes = ref('');

// Load data on mount/open
// We can assume stores are already initialized by parent or layout

// Device Logic
const modelOptions = computed(() => {
    if (selectedDeviceType.value === 'Unknown') return [];
    return deviceModels.value[selectedDeviceType.value] || [];
});

const onDeviceTypeChange = () => {
    selectedDeviceModel.value = ''; // Reset model when type changes
};

// Test Type Logic
const l2Options = computed(() => {
    if (!selectedL1.value) return [];
    return getTestTypesL2(selectedL1.value);
});

const onL1Change = () => {
    selectedL2.value = '--'; // Reset L2 when L1 changes
};

const handleConfirm = () => {
    const updates: any = {};
    
    if (updateDevice.value) {
        updates.deviceType = selectedDeviceType.value;
        updates.deviceModel = selectedDeviceModel.value || 'Unknown';
    }
    
    if (updateTestType.value) {
        updates.testTypeL1 = selectedL1.value || 'Unknown';
        updates.testTypeL2 = selectedL2.value || '--';
    }
    
    if (updateNotes.value) {
        updates.notes = notes.value;
    }
    
    emit('confirm', updates);
};

</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" @click.self="$emit('close')">
    <div class="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
      
      <!-- Header -->
      <div class="bg-slate-50 border-b border-slate-100 p-4 flex items-center justify-between">
        <div>
            <h3 class="font-semibold text-slate-800">Batch Edit</h3>
            <p class="text-xs text-slate-500">Updating {{ selectedCount }} selected items</p>
        </div>
        <button @click="$emit('close')" class="p-1 hover:bg-slate-200 rounded-full transition-colors text-slate-400 hover:text-slate-600">
          <X :size="20" />
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 space-y-6">
        
        <!-- Device Section -->
        <div class="space-y-3">
            <div class="flex items-center gap-2">
                <input type="checkbox" id="check-device" v-model="updateDevice" class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4" />
                <label for="check-device" class="text-sm font-medium text-slate-700 cursor-pointer select-none">Update Device Info</label>
            </div>
            
            <div class="grid grid-cols-2 gap-4 pl-6" :class="{ 'opacity-50 pointer-events-none grayscale': !updateDevice }">
                <!-- Device Type -->
                <div>
                    <label class="block text-xs font-semibold text-slate-500 mb-1.5 uppercase tracking-wider">Type</label>
                    <div class="relative">
                        <select 
                            v-model="selectedDeviceType" 
                            @change="onDeviceTypeChange"
                            class="w-full pl-3 pr-8 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none appearance-none transition-shadow max-h-40"
                        >
                             <option value="Unknown" disabled>Select Type</option>
                             <option v-for="opt in deviceTypeOptions" :key="opt.type" :value="opt.type">
                                {{ opt.label }}
                             </option>
                        </select>
                         <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
                        </div>
                    </div>
                </div>

                <!-- Device Model -->
                <div>
                     <label class="block text-xs font-semibold text-slate-500 mb-1.5 uppercase tracking-wider">Model</label>
                     <div class="relative">
                        <select 
                            v-model="selectedDeviceModel" 
                            class="w-full pl-3 pr-8 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none appearance-none transition-shadow disabled:bg-slate-50"
                            :disabled="selectedDeviceType === 'Unknown'"
                        >
                            <option value="" disabled>Select Model</option>
                            <option v-for="m in modelOptions" :key="m" :value="m">{{ m }}</option>
                            <option value="Unknown">Unknown</option>
                        </select>
                         <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
                        </div>
                     </div>
                </div>
            </div>
        </div>

        <hr class="border-slate-100" />

        <!-- Test Type Section -->
        <div class="space-y-3">
             <div class="flex items-center gap-2">
                <input type="checkbox" id="check-testtype" v-model="updateTestType" class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4" />
                <label for="check-testtype" class="text-sm font-medium text-slate-700 cursor-pointer select-none">Update Test Type</label>
            </div>
            
             <div class="grid grid-cols-2 gap-4 pl-6" :class="{ 'opacity-50 pointer-events-none grayscale': !updateTestType }">
                <!-- Primary Type -->
                <div>
                    <label class="block text-xs font-semibold text-slate-500 mb-1.5 uppercase tracking-wider">Primary Type</label>
                    <div class="relative">
                        <select 
                            v-model="selectedL1" 
                            @change="onL1Change"
                            class="w-full pl-3 pr-8 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none appearance-none transition-shadow"
                        >
                             <option value="" disabled>Select Primary</option>
                             <option v-for="t in testTypesL1" :key="t" :value="t">{{ t }}</option>
                        </select>
                         <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
                        </div>
                    </div>
                </div>

                <!-- Sub Type -->
                <div>
                     <label class="block text-xs font-semibold text-slate-500 mb-1.5 uppercase tracking-wider">Sub Type</label>
                     <div class="relative">
                         <select 
                            v-model="selectedL2" 
                            class="w-full pl-3 pr-8 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none appearance-none transition-shadow disabled:bg-slate-50"
                            :disabled="!selectedL1"
                        >
                             <option value="--" disabled>Select Sub</option>
                             <option v-for="t in l2Options" :key="t" :value="t">{{ t }}</option>
                             <option v-if="l2Options.indexOf('--') === -1" value="--">--</option>
                        </select>
                         <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
                        </div>
                     </div>
                </div>
            </div>
        </div>

        <hr class="border-slate-100" />
        
        <!-- Notes Section -->
        <div class="space-y-3">
             <div class="flex items-center gap-2">
                <input type="checkbox" id="check-notes" v-model="updateNotes" class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4" />
                <label for="check-notes" class="text-sm font-medium text-slate-700 cursor-pointer select-none">Update Notes</label>
            </div>
            
            <div class="pl-6" :class="{ 'opacity-50 pointer-events-none grayscale': !updateNotes }">
                 <textarea 
                    v-model="notes" 
                    placeholder="Enter notes..." 
                    class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none min-h-[80px]"
                 ></textarea>
            </div>
        </div>

      </div>

      <!-- Footer -->
      <div class="bg-slate-50 border-t border-slate-100 p-4 flex justify-end gap-3">
        <button 
            @click="$emit('close')"
            class="px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg transition-colors"
        >
            Cancel
        </button>
        <button 
            @click="handleConfirm"
            :disabled="!updateDevice && !updateTestType && !updateNotes"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
            <Check :size="16" />
            Apply Changes
        </button>
      </div>

    </div>
  </div>
</template>
