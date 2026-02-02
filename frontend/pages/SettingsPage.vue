<script setup lang="ts">
import { ref, computed } from 'vue';
import { useAuthStore } from '../stores/auth';
import { Settings, Users, Monitor } from 'lucide-vue-next';
import UserManagementTab from '../components/settings/UserManagementTab.vue';

const authStore = useAuthStore();
const activeTab = ref('general');

const tabs = computed(() => {
    const items = [
        { id: 'general', label: 'General', icon: Settings },
        { id: 'display', label: 'Display & Appearance', icon: Monitor },
    ];
    
    // Only show User Management to Admins
    if (authStore.isAdmin) {
        items.push({ id: 'users', label: 'User Management', icon: Users });
    }
    
    return items;
});
</script>

<template>
  <div class="p-8 w-full max-w-[1800px] mx-auto h-[calc(100vh-4rem)] flex flex-col">
    <!-- Header -->
    <div class="mb-6 shrink-0">
        <h1 class="text-2xl font-bold text-slate-800">Settings</h1>
        <p class="text-slate-500 text-sm">Configure system preferences and manage users</p>
    </div>
    
    <!-- Tabbed Layout -->
    <div class="flex flex-1 gap-8 overflow-hidden">
        <!-- Sidebar Tabs -->
        <div class="w-64 shrink-0 flex flex-col gap-1">
            <button 
                v-for="tab in tabs" 
                :key="tab.id"
                @click="activeTab = tab.id"
                class="flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all"
                :class="activeTab === tab.id ? 'bg-white text-blue-600 shadow-sm ring-1 ring-slate-200' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'"
            >
                <component :is="tab.icon" :size="18" />
                {{ tab.label }}
            </button>
        </div>
        
        <!-- Content Area -->
        <div class="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm p-6 overflow-y-auto">
            <!-- General Tab -->
            <div v-if="activeTab === 'general'" class="animate-in fade-in slide-in-from-right-4 duration-300">
                <h3 class="text-lg font-medium text-slate-800 mb-4">General Settings</h3>
                <div class="p-12 border border-dashed border-slate-200 rounded-lg text-center text-slate-400 bg-slate-50">
                    <Settings :size="48" class="mx-auto mb-3 opacity-20" />
                    <p>General Application settings will appear here.</p>
                </div>
            </div>

            <!-- Display Tab -->
            <div v-if="activeTab === 'display'" class="animate-in fade-in slide-in-from-right-4 duration-300">
                <h3 class="text-lg font-medium text-slate-800 mb-4">Display Settings</h3>
                <div class="space-y-4">
                     <div class="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50 transition">
                        <div>
                            <div class="font-medium text-slate-700">Compact Mode</div>
                            <div class="text-xs text-slate-500">Reduce spacing in list views</div>
                        </div>
                        <div class="h-6 w-11 bg-slate-200 rounded-full relative cursor-pointer">
                            <div class="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow-sm"></div>
                        </div>
                     </div>
                </div>
            </div>
            
            <!-- User Management Tab -->
            <div v-if="activeTab === 'users' && authStore.isAdmin" class="animate-in fade-in slide-in-from-right-4 duration-300">
                <UserManagementTab />
            </div>
        </div>
    </div>
  </div>
</template>
