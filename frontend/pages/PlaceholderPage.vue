<script setup lang="ts">
const props = defineProps<{ name?: string }>();
</script>

<template>
  <div class="w-full h-full flex flex-col items-center justify-center text-slate-400 animate-in fade-in">
    <div class="text-xl font-bold">Work in Progress</div>
    <div class="text-sm mt-2">The {{ props.name || 'module' }} is coming soon.</div>
  </div>
</template>
