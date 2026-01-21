<script setup lang="ts">
import { Clock, CheckCircle2, Loader2, AlertCircle } from 'lucide-vue-next';
import { FileStatus } from '../types';

defineProps<{
  status: FileStatus;
  error?: string;
}>();
</script>

<template>
  <span v-if="status === FileStatus.Idle" class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200">
    <Clock :size="12" /> Idle
  </span>
  
  <span v-else-if="status === FileStatus.Ready" class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-100">
    <CheckCircle2 :size="12" /> Ready
  </span>

  <span v-else-if="status === FileStatus.Processing" class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-100">
    <Loader2 :size="12" class="animate-spin" /> Processing
  </span>

  <span v-else-if="status === FileStatus.Failed" 
      class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-100" 
      :title="error">
    <AlertCircle :size="12" /> Failed
  </span>
</template>
