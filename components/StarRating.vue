<script setup lang="ts">
defineProps<{
  modelValue: number;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
}>();

const updateValue = (star: number) => {
  emit('update:modelValue', star);
};
</script>

<template>
  <div class="flex">
    <button
      v-for="star in 5"
      :key="star"
      @click.stop="updateValue(star)"
      class="text-sm focus:outline-none hover:scale-110 transition-transform"
      :class="star <= modelValue ? 'text-yellow-400' : 'text-gray-200'"
      type="button"
    >
      ★
    </button>
  </div>
</template>
