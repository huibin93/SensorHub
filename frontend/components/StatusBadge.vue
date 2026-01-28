<script setup lang="ts">
import { Clock, CheckCircle2, Loader2, AlertCircle } from 'lucide-vue-next';
import { FileStatus } from '../types';

defineProps<{
  status: FileStatus;
  error?: string;
}>();
</script>

<template>
  <span v-if="status === FileStatus.Unverified" class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
    <Clock :size="12" /> Unverified
  </span>
  
  <span v-else-if="status === FileStatus.Processed" class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800">
    <CheckCircle2 :size="12" /> Processed
  </span>

  <span v-else-if="status === FileStatus.Processing" class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
    <Loader2 :size="12" class="animate-spin" /> Processing
  </span>

  <span v-else-if="status === FileStatus.Error" 
      class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800" 
      :title="error">
    <AlertCircle :size="12" /> Error
  </span>
</template>
