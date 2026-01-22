<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
  initialNote: string;
  fileId: string;
}>();

const emit = defineEmits<{
  (e: 'update', id: string, note: string): void;
}>();

const isEditing = ref(false);
const noteValue = ref(props.initialNote);
const inputRef = ref<HTMLInputElement | null>(null);

// Start editing on double click
const startEdit = async () => {
  noteValue.value = props.initialNote;
  isEditing.value = true;
  
  // Focus input after it's rendered
  await new Promise(resolve => setTimeout(resolve, 0));
  inputRef.value?.focus();
  inputRef.value?.select();
};

// Save changes
const save = () => {
  emit('update', props.fileId, noteValue.value);
  isEditing.value = false;
};

// Cancel editing
const cancel = () => {
  noteValue.value = props.initialNote;
  isEditing.value = false;
};

// Handle keyboard events
const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    save();
  } else if (e.key === 'Escape') {
    e.preventDefault();
    cancel();
  }
};
</script>

<template>
  <div class="w-full h-full">
    <!-- VIEW MODE - Double click to edit -->
    <div
      v-if="!isEditing"
      @dblclick="startEdit"
      class="text-sm text-gray-600 truncate block max-w-[200px] cursor-text hover:bg-slate-50 px-2 py-1 rounded transition-colors"
      :title="initialNote"
    >
      {{ initialNote }}
    </div>

    <!-- EDIT MODE - Input field only -->
    <div v-else @click.stop>
      <input
        ref="inputRef"
        v-model="noteValue"
        type="text"
        class="w-full px-2 py-1 text-sm border border-blue-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
        @keydown="handleKeydown"
        @blur="cancel"
      />
    </div>
  </div>
</template>
