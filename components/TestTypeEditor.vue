<script setup lang="ts">
import { ref, computed } from 'vue';
import { SensorFile } from '../types';
import { TEST_TYPES_L1, TEST_TYPES_L2 } from '../constants';

const props = defineProps<{
  file: SensorFile;
}>();

const emit = defineEmits<{
  (e: 'update', id: string, l1: string, l2: string): void;
  (e: 'close'): void;
}>();

const l1 = ref(props.file.testTypeL1);
const l2 = ref(props.file.testTypeL2);

const l2Options = computed(() => TEST_TYPES_L2[l1.value] || []);

const updateTestType = () => {
    emit('update', props.file.id, l1.value, l2.value);
    emit('close');
};

const handleL1Change = (event: Event) => {
    const val = (event.target as HTMLSelectElement).value;
    l1.value = val;
    l2.value = TEST_TYPES_L2[val]?.[0] || '--';
};
</script>

<template>
  <div class="absolute z-10 bg-white shadow-lg border border-blue-200 rounded p-2 flex gap-2 min-w-[200px] animate-in fade-in zoom-in-95 duration-100">
    <select 
      class="text-xs border border-gray-300 rounded px-1 py-1"
      :value="l1"
      @change="handleL1Change"
    >
      <option v-for="t in TEST_TYPES_L1" :key="t" :value="t">{{ t }}</option>
    </select>
    <select 
       class="text-xs border border-gray-300 rounded px-1 py-1"
       v-model="l2"
    >
       <option v-for="t in l2Options" :key="t" :value="t">{{ t }}</option>
    </select>
    <button 
      class="bg-blue-600 text-white text-xs px-2 rounded hover:bg-blue-700"
      @click="updateTestType"
    >
      ✓
    </button>
  </div>
</template>
