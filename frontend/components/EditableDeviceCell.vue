<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue';
import { Watch, Circle, X, Check } from 'lucide-vue-next';
import { DeviceType } from '../types';
import { 
  deviceTypeOptions, 
  deviceModels, 
  addDeviceModel,
  fetchDevices
} from '../stores/deviceStore';

// Load devices on mount
onMounted(() => {
    fetchDevices();
});

const props = defineProps<{
  initialDeviceType: DeviceType;
  initialDeviceModel: string;
  fileId: string;
}>();

const emit = defineEmits<{
  (e: 'update', id: string, deviceType: DeviceType, deviceModel: string): void;
}>();

const isEditing = ref(false);
const selectedDeviceType = ref(props.initialDeviceType);
const selectedDeviceModel = ref(props.initialDeviceModel);
const showModelDropdown = ref(false);
const searchQueryModel = ref('');
const containerRef = ref<HTMLDivElement | null>(null);

// Get device icon component
const getDeviceIcon = (deviceType: DeviceType) => {
  return deviceType === DeviceType.Watch ? Watch : Circle;
};

// Get device type label
const getDeviceTypeLabel = (deviceType: DeviceType) => {
  const option = deviceTypeOptions.find(opt => opt.type === deviceType);
  return option?.label || deviceType;
};

// Get models for current device type
const modelOptions = computed(() => {
  return deviceModels.value[selectedDeviceType.value] || [];
});

// Filter model options based on search
const filteredModelOptions = computed(() => {
  const allModels = modelOptions.value;
  const query = searchQueryModel.value?.trim() || '';
  
  if (!query) {
    return allModels;
  }
  
  const lowerQuery = query.toLowerCase();
  const matches: string[] = [];
  const others: string[] = [];
  
  allModels.forEach(model => {
    if (model.toLowerCase().includes(lowerQuery)) {
      matches.push(model);
    } else {
      others.push(model);
    }
  });
  
  // Check if we have an exact match
  const hasExactMatch = allModels.some(model => model.toLowerCase() === lowerQuery);
  
  // If no exact match, prepend a "Create" option
  if (!hasExactMatch && query.length > 0) {
    return [`__CREATE__${query}`, ...matches, ...others];
  }
  
  return [...matches, ...others];
});

// Check if option is a "Create new" option
const isCreateOption = (option: string): boolean => {
  return option.startsWith('__CREATE__');
};

// Get display text for option
const getOptionDisplay = (option: string): string => {
  if (isCreateOption(option)) {
    return `Create "${option.replace('__CREATE__', '')}"`;
  }
  return option;
};

// Check if model matches search
const isMatchingSearch = (model: string): boolean => {
  if (!searchQueryModel.value || searchQueryModel.value.trim() === '') return false;
  return model.toLowerCase().includes(searchQueryModel.value.toLowerCase());
};

// Start editing
const startEdit = async () => {
  selectedDeviceType.value = props.initialDeviceType;
  selectedDeviceModel.value = props.initialDeviceModel;
  searchQueryModel.value = props.initialDeviceModel;
  isEditing.value = true;
  
  await nextTick();
  showModelDropdown.value = false;
};

// Select device type
const selectDeviceType = (deviceType: DeviceType) => {
  selectedDeviceType.value = deviceType;
  
  // Auto-select first model for new type
  const models = deviceModels.value[deviceType];
  if (models && models.length > 0) {
    selectedDeviceModel.value = models[0];
    searchQueryModel.value = models[0];
  }
};

// Select model
const selectModel = async (model: string) => {
  let actualModel = model;
  
  // Handle "Create new" option
  if (isCreateOption(model)) {
    actualModel = model.replace('__CREATE__', '');
    addDeviceModel(selectedDeviceType.value, actualModel);
  }
  
  selectedDeviceModel.value = actualModel;
  searchQueryModel.value = actualModel;
  showModelDropdown.value = false;
};

// Save changes
const save = async () => {
  const finalModel = searchQueryModel.value.trim() || selectedDeviceModel.value;
  
  // If user typed a new model, add it to the store
  if (finalModel && !modelOptions.value.includes(finalModel)) {
    addDeviceModel(selectedDeviceType.value, finalModel);
  }
  
  emit('update', props.fileId, selectedDeviceType.value, finalModel);
  isEditing.value = false;
  showModelDropdown.value = false;
};

// Cancel editing
const cancel = () => {
  isEditing.value = false;
  showModelDropdown.value = false;
  searchQueryModel.value = '';
};

// Keyboard handlers
const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    e.preventDefault();
    cancel();
  } else if (e.key === 'Enter') {
    e.preventDefault();
    save();
  }
};

const handleModelInputKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && showModelDropdown.value && filteredModelOptions.value.length > 0) {
    e.preventDefault();
    selectModel(filteredModelOptions.value[0]);
  } else if (e.key === 'Escape') {
    e.preventDefault();
    showModelDropdown.value = false;
  }
};

// Event handlers
const onViewClick = () => {
  startEdit();
};

const onModalBackdropClick = () => {
  cancel();
};

const onModelInputFocus = () => {
  showModelDropdown.value = true;
};

const onModelInputInput = () => {
  showModelDropdown.value = true;
};
</script>

<template>
  <div ref="containerRef" class="w-full h-full" @click.stop>
    <!-- VIEW MODE -->
    <div
      @click="onViewClick"
      class="flex flex-col px-2 py-2 cursor-pointer hover:bg-slate-50 rounded transition-colors min-h-[44px]"
    >
      <div class="flex items-center gap-1.5">
        <div class="w-5 flex justify-center">
          <component 
            :is="getDeviceIcon(initialDeviceType)" 
            :size="initialDeviceType === DeviceType.Watch ? 16 : 14" 
            class="text-slate-400" 
          />
        </div>
        <span class="text-sm font-medium text-slate-700">{{ initialDeviceModel }}</span>
      </div>
      <span class="text-xs text-slate-400 pl-[26px]">{{ getDeviceTypeLabel(initialDeviceType) }}</span>
    </div>

    <!-- EDIT MODE - Modal Overlay -->
    <div
      v-if="isEditing"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/10"
      @click.self="onModalBackdropClick"
    >
      <div
        class="bg-white rounded-lg shadow-2xl p-4 w-full max-w-md mx-4"
        @click.stop
        @keydown="handleKeydown"
      >
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold text-slate-700">Edit Device</h3>
          <button
            @click="cancel"
            class="p-1 hover:bg-slate-100 rounded transition-colors"
          >
            <X :size="16" class="text-slate-400" />
          </button>
        </div>

        <!-- Device Type Selection -->
        <div class="mb-3">
          <label class="block text-xs font-medium text-slate-600 mb-2">Device Type</label>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="option in deviceTypeOptions"
              :key="option.type"
              @click="selectDeviceType(option.type)"
              class="flex items-center gap-2 px-3 py-2 border rounded-md transition-all text-sm"
              :class="selectedDeviceType === option.type 
                ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium' 
                : 'border-slate-300 hover:border-slate-400 text-slate-700'"
            >
              <component 
                :is="getDeviceIcon(option.type)" 
                :size="option.type === DeviceType.Watch ? 16 : 14" 
              />
              {{ option.label }}
            </button>
          </div>
        </div>

        <!-- Device Model Selection -->
        <div class="mb-4">
          <label class="block text-xs font-medium text-slate-600 mb-1">Device Model</label>
          <div class="relative">
            <input
              v-model="searchQueryModel"
              type="text"
              placeholder="Search or type..."
              class="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              @focus="onModelInputFocus"
              @input="onModelInputInput"
              @keydown="handleModelInputKeydown"
            />
            
            <!-- Model Dropdown -->
            <div
              v-if="showModelDropdown && filteredModelOptions.length > 0"
              class="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-md shadow-lg max-h-48 overflow-y-auto z-10 flex flex-col"
            >
              <button
                v-for="model in filteredModelOptions"
                :key="model"
                @click="selectModel(model)"
                class="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm transition-colors flex-shrink-0"
                :class="{ 
                  'bg-green-50 text-green-700 font-semibold border-b border-green-200': isCreateOption(model),
                  'bg-blue-100 font-semibold text-blue-700': !isCreateOption(model) && isMatchingSearch(model),
                  'bg-blue-50 font-medium': model === selectedDeviceModel && !isMatchingSearch(model) && !isCreateOption(model)
                }"
              >
                <span v-if="isCreateOption(model)" class="flex items-center gap-1">
                  <span class="text-green-600">+</span>
                  {{ getOptionDisplay(model) }}
                </span>
                <span v-else>{{ model }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end gap-2">
          <button
            @click="cancel"
            class="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-md transition-colors"
          >
            Cancel
          </button>
          <button
            @click="save"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors flex items-center gap-1.5"
          >
            <Check :size="16" />
            Save
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
