<script setup lang="ts">
import { computed } from 'vue';
import { CheckCircle2, Ban } from 'lucide-vue-next';
import { PacketInfo } from '../types';

const props = defineProps<{
  packets: PacketInfo[];
}>();

const summary = computed(() => {
  if (!props.packets || props.packets.length === 0) return '';
  return props.packets.slice(0, 3).map(p => p.name).join(', ') + (props.packets.length > 3 ? ` [+${props.packets.length - 3}]` : '');
});
</script>

<template>
  <span v-if="!packets || packets.length === 0" class="text-xs font-medium text-gray-400 bg-gray-50 px-2 py-1 rounded border border-gray-100">
    --
  </span>

  <div v-else class="group relative inline-block cursor-help">
    <span class="text-xs font-medium text-gray-600 bg-gray-100 px-2 py-1 rounded border border-gray-200 hover:bg-gray-200 transition-colors">
      {{ summary }}
    </span>
    <!-- Popover -->
    <div class="absolute left-0 bottom-full mb-2 w-48 bg-white rounded-lg shadow-xl border border-gray-200 p-3 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 pointer-events-none">
      <div class="text-xs font-semibold text-gray-700 mb-2 border-b pb-1">Packet Structure</div>
      <div class="space-y-1.5">
        <div v-for="(p, idx) in packets" :key="idx" class="flex items-center justify-between text-xs">
          <span class="font-mono" :class="p.present ? 'text-gray-600' : 'text-red-400 line-through'">
            {{ p.name }}
          </span>
          <div class="flex items-center gap-2">
            <span class="text-gray-400 text-[10px]">{{ p.freq }}</span>
            <CheckCircle2 v-if="p.present" :size="10" class="text-green-500" />
            <Ban v-else :size="10" class="text-red-500" />
          </div>
        </div>
      </div>
      <!-- Triangle arrow -->
      <div class="absolute left-4 bottom-[-4px] w-2 h-2 bg-white border-r border-b border-gray-200 transform rotate-45"></div>
    </div>
  </div>
</template>
