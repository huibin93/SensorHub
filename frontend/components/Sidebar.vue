<script setup lang="ts">
import { ref } from 'vue';
import { LayoutDashboard, Activity, FileText, Settings, Database, ChevronLeft, ChevronRight, Network } from 'lucide-vue-next';

const isCollapsed = ref(true);

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value;
};

const props = defineProps<{
  activeId: string;
}>();

const emit = defineEmits<{
  (e: 'navigate', id: string): void;
}>();

const menuItems = [
  { label: 'Data Management', icon: Database, id: 'data' },
  { label: 'Device Import', icon: Network, id: 'device' },
  { label: 'Algorithm Analysis', icon: Activity, id: 'algo' },
  { label: 'Report Center', icon: FileText, id: 'report' },
  { label: 'Settings', icon: Settings, id: 'settings' },
];
</script>

<template>
  <aside 
    class="bg-[#E9EEF6] flex flex-col h-full text-slate-500 border-r border-slate-200 flex-shrink-0 transition-all duration-300 relative"
    :class="isCollapsed ? 'w-20' : 'w-64'"
  >
    <!-- Logo Area -->
    <div class="h-20 flex items-center px-5 border-b border-slate-200/60 shrink-0" :class="isCollapsed ? 'justify-center' : 'gap-4'">
        <div class="w-9 h-9 rounded-xl flex items-center justify-center bg-white p-1.5 shrink-0 shadow-sm transition-all duration-300">
             <img src="/logo.svg" alt="Logo" class="w-full h-full object-contain" />
        </div>
        <div class="flex flex-col whitespace-nowrap opacity-100 transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isCollapsed }">
            <span class="text-lg font-bold text-slate-800 tracking-tight leading-none">SensorHub</span>
            <span class="text-[11px] text-slate-500 font-medium uppercase tracking-widest mt-1">Analytics</span>
        </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 py-8 px-4 flex flex-col gap-3 overflow-visible">
        <div 
            class="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-2 whitespace-nowrap transition-all duration-300 select-none"
            :class="isCollapsed ? 'opacity-0 text-center h-4' : 'px-2 opacity-100'"
        >
            {{ isCollapsed ? '...' : 'Main Menu' }}
        </div>
        
        <a v-for="item in menuItems" :key="item.label" href="#" 
           @click.prevent="emit('navigate', item.id)"
           class="flex items-center rounded-xl transition-all duration-300 group relative"
           :class="[
             item.id === activeId 
                ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200/50' 
                : 'hover:bg-white/60 hover:text-slate-700',
             isCollapsed ? 'justify-center px-0 py-3.5' : 'px-3 py-3.5 gap-3'
           ]"
           :title="isCollapsed ? '' : ''"
        >
            <component :is="item.icon" :size="20" class="shrink-0 transition-colors duration-300" 
                :class="item.id === activeId ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-600'" 
            />
            <span class="text-sm font-semibold whitespace-nowrap transition-all duration-300 overflow-hidden" 
                  :class="isCollapsed ? 'w-0 h-0 opacity-0 m-0 p-0' : 'w-auto opacity-100'">
                {{ item.label }}
            </span>
            
            <!-- Tooltip for collapsed state -->
            <div v-if="isCollapsed" class="absolute left-full top-1/2 -translate-y-1/2 ml-3 px-3 py-2 bg-white text-slate-700 text-xs font-bold rounded-md opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap shadow-xl border border-slate-100 z-50 transition-opacity">
                {{ item.label }}
                <!-- Little arrow for tooltip -->
                <div class="absolute left-0 top-1/2 -translate-x-1/2 -translate-y-1/2 border-[6px] border-transparent border-r-white"></div>
            </div>
        </a>
    </nav>
    
    <!-- Collapse Toggle Button -->
    <button 
        @click="toggleSidebar"
        class="absolute -right-3 top-24 w-6 h-6 bg-[#E9EEF6] border border-slate-300 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-600 hover:border-slate-400 transition-all shadow-sm z-50 group"
    >
        <ChevronLeft v-if="!isCollapsed" :size="14" class="group-hover:-translate-x-0.5 transition-transform" />
        <ChevronRight v-else :size="14" class="group-hover:translate-x-0.5 transition-transform" />
    </button>

    <!-- Bottom User/Profile Area -->
    <div class="p-5 border-t border-slate-200/60 shrink-0">
        <div class="flex items-center gap-3.5" :class="isCollapsed ? 'justify-center' : ''">
             <div class="w-9 h-9 rounded-full bg-white flex items-center justify-center text-xs font-bold text-slate-700 ring-2 ring-slate-100 shrink-0 shadow-sm">
                JD
             </div>
             <div class="flex flex-col whitespace-nowrap overflow-hidden transition-all duration-300" :class="{ 'w-0 opacity-0': isCollapsed }">
                 <span class="text-sm font-semibold text-slate-700 truncate">John Doe</span>
                 <span class="text-xs text-slate-500 truncate">Admin Workspace</span>
             </div>
        </div>
    </div>
  </aside>
</template>
