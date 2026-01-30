<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue';
import { ChevronDown, X, Check } from 'lucide-vue-next';
import { 
  testTypesL1, 
  testTypesL2, 
  addTestTypeL1, 
  getTestTypesL2,
  fetchTestTypes,
  addTestTypeL2
} from '../stores/testTypeStore';

// Load test types on mount
onMounted(() => {
    fetchTestTypes();
});

const props = defineProps<{
  initialL1: string;
  initialL2: string;
  fileId: string;
}>();

const emit = defineEmits<{
  (e: 'update', id: string, l1: string, l2: string): void;
}>();

const isEditing = ref(false);
const selectedL1 = ref(props.initialL1);
const selectedL2 = ref(props.initialL2);
const showL1Dropdown = ref(false);
const showL2Dropdown = ref(false);
const searchQuery = ref('');
const searchQueryL2 = ref('');
const containerRef = ref<HTMLDivElement | null>(null);

// Filter L1 options based on search - show all types, with matches first
const filteredL1Options = computed(() => {
  const allTypes = testTypesL1.value;
  const query = searchQuery.value?.trim() || '';
  
  if (!query) {
    return allTypes;
  }
  
  const lowerQuery = query.toLowerCase();
  // Split into matching and non-matching
  const matches: string[] = [];
  const others: string[] = [];
  
  allTypes.forEach(opt => {
    if (opt.toLowerCase().includes(lowerQuery)) {
      matches.push(opt);
    } else {
      others.push(opt);
    }
  });
  
  // Check if we have an exact match
  const hasExactMatch = allTypes.some(opt => opt.toLowerCase() === lowerQuery);
  
  // If no exact match, prepend a "Create" option
  if (!hasExactMatch && query.length > 0) {
    return [`__CREATE__${query}`, ...matches, ...others];
  }
  
  // Return matches first, then all others
  return [...matches, ...others];
});

// Check if option is a "Create new" option for L1
const isCreateOption = (option: string): boolean => {
  return option.startsWith('__CREATE__');
};

// Check if option is a "Create new" option for L2
const isCreateOptionL2 = (option: string): boolean => {
  return option.startsWith('__CREATE_L2__');
};

// Get display text for option
const getOptionDisplay = (option: string): string => {
  if (isCreateOption(option)) {
    return `Create "${option.replace('__CREATE__', '')}"`;
  }
  return option;
};

// Get display text for L2 option
const getOptionDisplayL2 = (option: string): string => {
  if (isCreateOptionL2(option)) {
    return `Create "${option.replace('__CREATE_L2__', '')}"`;
  }
  return option;
};

// Get L2 options for selected L1
const l2Options = computed(() => {
  return getTestTypesL2(selectedL1.value);
});

// Filter L2 options based on search - show all types, with matches first
const filteredL2Options = computed(() => {
  const allTypes = l2Options.value;
  const query = searchQueryL2.value?.trim() || '';
  
  if (!query) {
    return allTypes;
  }
  
  const lowerQuery = query.toLowerCase();
  const matches: string[] = [];
  const others: string[] = [];
  
  allTypes.forEach(opt => {
    if (opt.toLowerCase().includes(lowerQuery)) {
      matches.push(opt);
    } else {
      others.push(opt);
    }
  });
  
  // Check if we have an exact match
  const hasExactMatch = allTypes.some(opt => opt.toLowerCase() === lowerQuery);
  
  // If no exact match, prepend a "Create" option
  if (!hasExactMatch && query.length > 0 && query !== '--') {
    return [`__CREATE_L2__${query}`, ...matches, ...others];
  }
  
  return [...matches, ...others];
});

// Check if an option matches the current search
const isMatchingSearch = (option: string): boolean => {
  if (!searchQuery.value || searchQuery.value.trim() === '') return false;
  return option.toLowerCase().includes(searchQuery.value.toLowerCase());
};

// Check if an L2 option matches the current search
const isMatchingSearchL2 = (option: string): boolean => {
  if (!searchQueryL2.value || searchQueryL2.value.trim() === '') return false;
  return option.toLowerCase().includes(searchQueryL2.value.toLowerCase());
};

// Start editing
const startEdit = async () => {
  console.log('[EditableTestTypeCell] startEdit called', {
    fileId: props.fileId,
    initialL1: props.initialL1,
    initialL2: props.initialL2
  });
  
  selectedL1.value = props.initialL1;
  selectedL2.value = props.initialL2;
  searchQuery.value = props.initialL1;
  searchQueryL2.value = props.initialL2;
  isEditing.value = true;
  
  console.log('[EditableTestTypeCell] Set isEditing to true', { isEditing: isEditing.value });
  
  await nextTick();
  // Don't auto-show dropdown - let user trigger it by focusing input
  showL1Dropdown.value = false;
  showL2Dropdown.value = false;
  
  console.log('[EditableTestTypeCell] Edit mode activated', {
    selectedL1: selectedL1.value,
    selectedL2: selectedL2.value,
    showL1Dropdown: showL1Dropdown.value,
    showL2Dropdown: showL2Dropdown.value
  });
};

// Select L1 option
const selectL1 = (option: string) => {
  console.log('[EditableTestTypeCell] selectL1 called', { option });
  
  let actualType = option;
  
  // Handle "Create new" option
  if (isCreateOption(option)) {
    actualType = option.replace('__CREATE__', '');
    console.log('[EditableTestTypeCell] Creating new type:', actualType);
    addTestTypeL1(actualType);
  }
  
  selectedL1.value = actualType;
  searchQuery.value = actualType;
  showL1Dropdown.value = false;
  
  // If Unknown is selected, set L2 to '--' and don't show sub types
  if (actualType === 'Unknown') {
    selectedL2.value = '--';
    searchQueryL2.value = '--';
    console.log('[EditableTestTypeCell] Unknown selected, set L2 to --');
  } else {
    // Auto-select first L2 option if available
    const options = getTestTypesL2(actualType);
    if (options && options.length > 0) {
      selectedL2.value = options[0];
      searchQueryL2.value = options[0];
      console.log('[EditableTestTypeCell] Auto-selected L2', { selectedL2: selectedL2.value });
    }
  }
  
  console.log('[EditableTestTypeCell] L1 selection complete', {
    selectedL1: selectedL1.value,
    searchQuery: searchQuery.value
  });
};

// Select L2 option
const selectL2 = async (option: string) => {
  console.log('[EditableTestTypeCell] selectL2 called', { option });
  
  let actualType = option;
  
  // Handle "Create new" option
  if (isCreateOptionL2(option)) {
    actualType = option.replace('__CREATE_L2__', '');
    console.log('[EditableTestTypeCell] Creating new L2 type:', actualType);
    // Add to the store
    addTestTypeL2(selectedL1.value, actualType);
  }
  
  selectedL2.value = actualType;
  searchQueryL2.value = actualType;
  showL2Dropdown.value = false;
  
  console.log('[EditableTestTypeCell] L2 selection complete', {
    selectedL2: selectedL2.value,
    searchQueryL2: searchQueryL2.value
  });
};

// Save changes
const save = async () => {
  console.log('[EditableTestTypeCell] save called', {
    selectedL1: selectedL1.value,
    selectedL2: selectedL2.value,
    searchQuery: searchQuery.value,
    searchQueryL2: searchQueryL2.value
  });
  
  // Use searchQuery if user typed a custom value, otherwise use selectedL1
  const finalL1 = searchQuery.value.trim() || selectedL1.value || props.initialL1;
  const finalL2 = searchQueryL2.value.trim() || selectedL2.value || '--';
  
  // 如果用户输入了新的Primary Type,添加到全局列表
  if (finalL1 && !testTypesL1.value.includes(finalL1)) {
    const added = addTestTypeL1(finalL1);
    if (added) {
      console.log('[EditableTestTypeCell] Added new Primary Type to global list:', finalL1);
      // 更新选中的值
      selectedL1.value = finalL1;
      // 为新类型设置默认的Sub Type
      if (getTestTypesL2(finalL1).length === 0 || getTestTypesL2(finalL1)[0] === '--') {
        selectedL2.value = '--';
      }
    }
  }
  
  // 如果用户输入了新的Sub Type,添加到全局列表
  if (finalL2 && finalL2 !== '--' && !getTestTypesL2(finalL1).includes(finalL2)) {
    const added = addTestTypeL2(finalL1, finalL2);
    if (added) {
      console.log('[EditableTestTypeCell] Added new Sub Type to global list:', finalL2);
      selectedL2.value = finalL2;
    }
  }
  
  console.log('[EditableTestTypeCell] Emitting update', {
    fileId: props.fileId,
    finalL1,
    finalL2
  });
  
  emit('update', props.fileId, finalL1, finalL2);
  isEditing.value = false;
  showL1Dropdown.value = false;
  showL2Dropdown.value = false;
  
  console.log('[EditableTestTypeCell] Save complete, edit mode closed');
};

// Cancel editing
const cancel = () => {
  console.log('[EditableTestTypeCell] cancel called');
  isEditing.value = false;
  showL1Dropdown.value = false;
  showL2Dropdown.value = false;
  searchQuery.value = '';
  searchQueryL2.value = '';
  console.log('[EditableTestTypeCell] Edit mode canceled');
};

// Handle click outside - now cancels instead of saving
const handleClickOutside = (event: MouseEvent) => {
  console.log('[EditableTestTypeCell] handleClickOutside called', {
    isEditing: isEditing.value,
    target: event.target
  });
  
  if (containerRef.value && !containerRef.value.contains(event.target as Node)) {
    if (isEditing.value) {
      console.log('[EditableTestTypeCell] Click outside detected, canceling');
      cancel(); // Cancel on click outside
    }
  }
};

// Keyboard handlers
const handleKeydown = (e: KeyboardEvent) => {
  console.log('[EditableTestTypeCell] handleKeydown', { key: e.key });
  
  if (e.key === 'Escape') {
    e.preventDefault();
    console.log('[EditableTestTypeCell] Escape pressed, canceling');
    cancel();
  } else if (e.key === 'Enter') {
    e.preventDefault();
    console.log('[EditableTestTypeCell] Enter pressed, saving');
    save();
  }
};

// Keyboard handler for Primary Type input
const handleL1InputKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && showL1Dropdown.value && filteredL1Options.value.length > 0) {
    e.preventDefault();
    // Select first option (which could be Create option)
    selectL1(filteredL1Options.value[0]);
  } else if (e.key === 'Escape') {
    e.preventDefault();
    showL1Dropdown.value = false;
  }
};

// Keyboard handler for Sub Type input
const handleL2InputKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && showL2Dropdown.value && filteredL2Options.value.length > 0) {
    e.preventDefault();
    // Select first option (which could be Create option)
    selectL2(filteredL2Options.value[0]);
  } else if (e.key === 'Escape') {
    e.preventDefault();
    showL2Dropdown.value = false;
  }
};

// Wrapper functions with logging for template
const onViewClick = (event: MouseEvent) => {
  console.log('[EditableTestTypeCell] View mode clicked', {
    target: event.target,
    currentTarget: event.currentTarget,
    isEditing: isEditing.value
  });
  startEdit();
};

const onModalBackdropClick = (event: MouseEvent) => {
  console.log('[EditableTestTypeCell] Modal backdrop clicked');
  cancel(); // Cancel instead of save
};

const onInputFocus = () => {
  console.log('[EditableTestTypeCell] L1 Input focused');
  showL1Dropdown.value = true;
  showL2Dropdown.value = false; // Close L2 dropdown when L1 opens
};

const onInputInput = () => {
  console.log('[EditableTestTypeCell] L1 Input changed', { searchQuery: searchQuery.value });
  showL1Dropdown.value = true;
};

const onL2InputFocus = () => {
  console.log('[EditableTestTypeCell] L2 Input focused');
  showL2Dropdown.value = true;
  showL1Dropdown.value = false; // Close L1 dropdown when L2 opens
};

const onL2InputInput = () => {
  console.log('[EditableTestTypeCell] L2 Input changed', { searchQueryL2: searchQueryL2.value });
  showL2Dropdown.value = true;
};

</script>

<template>
  <div ref="containerRef" class="w-full h-full" @click.stop>
    <!-- VIEW MODE - Always visible -->
    <div
      @click="onViewClick"
      class="flex items-center gap-1.5 px-2 py-2 cursor-pointer hover:bg-slate-50 rounded transition-colors min-h-[44px]"
    >
      <template v-if="initialL1">
        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
          {{ initialL1 }}
        </span>
        <span v-if="initialL2 && initialL2 !== '--'" class="text-xs text-slate-500">
          {{ initialL2 }}
        </span>
      </template>
      <span v-else class="text-xs text-slate-400 italic">Click to set...</span>
    </div>

    <!-- EDIT MODE - Modal Overlay -->
    <div
      v-if="isEditing"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/20 backdrop-blur-[1px]"
      @click.self="onModalBackdropClick"
    >
      <div
        class="bg-white rounded-xl shadow-2xl border border-slate-100 p-5 w-full max-w-sm mx-auto animate-in fade-in zoom-in-95 duration-200"
        @click.stop
        @keydown="handleKeydown"
      >
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold text-slate-700">Edit Test Type</h3>
          <button
            @click="cancel"
            class="p-1 hover:bg-slate-100 rounded transition-colors"
          >
            <X :size="16" class="text-slate-400" />
          </button>
        </div>

        <!-- L1 Selection -->
        <div class="mb-3">
          <label class="block text-xs font-medium text-slate-600 mb-1">Primary Type</label>
          <div class="relative">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search or type..."
              class="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              @focus="onInputFocus"
              @input="onInputInput"
              @keydown="handleL1InputKeydown"
            />
            
            <!-- L1 Dropdown -->
            <div
              v-if="showL1Dropdown && filteredL1Options.length > 0"
              class="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-md shadow-lg max-h-48 overflow-y-auto z-10 flex flex-col"
            >
              <button
                v-for="option in filteredL1Options"
                :key="option"
                @click="selectL1(option)"
                class="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm transition-colors flex-shrink-0"
                :class="{ 
                  'bg-green-50 text-green-700 font-semibold border-b border-green-200': isCreateOption(option),
                  'bg-blue-100 font-semibold text-blue-700': !isCreateOption(option) && isMatchingSearch(option),
                  'bg-blue-50 font-medium': option === selectedL1 && !isMatchingSearch(option) && !isCreateOption(option)
                }"
              >
                <span v-if="isCreateOption(option)" class="flex items-center gap-1">
                  <span class="text-green-600">+</span>
                  {{ getOptionDisplay(option) }}
                </span>
                <span v-else>{{ option }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- L2 Selection -->
        <div class="mb-4" v-if="l2Options.length > 0 && selectedL1 !== 'Unknown'">
          <label class="block text-xs font-medium text-slate-600 mb-1">Sub Type</label>
          <div class="relative">
            <input
              v-model="searchQueryL2"
              type="text"
              placeholder="Search or type..."
              class="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              @focus="onL2InputFocus"
              @input="onL2InputInput"
              @keydown="handleL2InputKeydown"
            />
            
            <!-- L2 Dropdown -->
            <div
              v-if="showL2Dropdown && filteredL2Options.length > 0"
              class="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-md shadow-lg max-h-48 overflow-y-auto z-10 flex flex-col"
            >
              <button
                v-for="option in filteredL2Options"
                :key="option"
                @click="selectL2(option)"
                class="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm transition-colors flex-shrink-0"
                :class="{ 
                  'bg-green-50 text-green-700 font-semibold border-b border-green-200': isCreateOptionL2(option),
                  'bg-blue-100 font-semibold text-blue-700': !isCreateOptionL2(option) && isMatchingSearchL2(option),
                  'bg-blue-50 font-medium': option === selectedL2 && !isMatchingSearchL2(option) && !isCreateOptionL2(option)
                }"
              >
                <span v-if="isCreateOptionL2(option)" class="flex items-center gap-1">
                  <span class="text-green-600">+</span>
                  {{ getOptionDisplayL2(option) }}
                </span>
                <span v-else>{{ option }}</span>
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
