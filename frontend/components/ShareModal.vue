<script setup lang="ts">
import { ref, watch } from 'vue';
import { Copy, Check, X, Globe } from 'lucide-vue-next';

const props = defineProps<{
  isOpen: boolean;
  fileId: string | null;
  filename: string | null;
}>();

const emit = defineEmits(['close']);

const days = ref(7);
const loading = ref(false);
const generatedLink = ref('');
const copied = ref(false);
const error = ref('');

// Reset state when opening
watch(() => props.isOpen, (newVal) => {
    if (newVal) {
        generatedLink.value = '';
        error.value = '';
        copied.value = false;
        days.value = 7;
    }
});

const generateLink = async () => {
    if (!props.fileId) return;
    
    loading.value = true;
    error.value = '';
    
    try {
        const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
        const token = localStorage.getItem('token');
        
        const res = await fetch(`${apiBase}/files/${props.fileId}/share?days=${days.value}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!res.ok) throw new Error(await res.text());
        
        const data = await res.json();
        // Construct full URL
        const origin = window.location.origin;
        generatedLink.value = `${origin}${data.url}`;
        
    } catch (e: any) {
        error.value = e.message || "Failed to generate link";
    } finally {
        loading.value = false;
    }
};

const copyLink = () => {
    if (!generatedLink.value) return;
    navigator.clipboard.writeText(generatedLink.value);
    copied.value = true;
    setTimeout(() => { copied.value = false; }, 2000);
};

const close = () => {
    emit('close');
};
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 overflow-hidden border border-slate-200" @click.stop>
      
      <!-- Header -->
      <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
        <div class="flex items-center gap-2">
            <div class="p-1.5 bg-blue-100 text-blue-600 rounded">
                <Globe :size="18" />
            </div>
            <h3 class="font-semibold text-slate-800">Share Analysis</h3>
        </div>
        <button @click="close" class="text-slate-400 hover:text-slate-600 transition-colors">
          <X :size="20" />
        </button>
      </div>
      
      <!-- Body -->
      <div class="p-6">
        <p class="text-sm text-slate-600 mb-4">
            Generate a secure link for <strong>{{ filename }}</strong>. External visitors can view the data without logging in.
        </p>
        
        <div class="flex flex-col gap-4">
            <div class="flex flex-col gap-1">
                <label class="text-xs font-medium text-slate-500">Expiration</label>
                <div class="flex gap-2">
                    <button 
                        v-for="d in [7, 30]" 
                        :key="d"
                        @click="days = d"
                        class="px-3 py-1.5 rounded border text-sm transition-colors"
                        :class="days === d ? 'border-blue-500 bg-blue-50 text-blue-600 font-medium' : 'border-slate-200 text-slate-600 hover:border-slate-300'"
                    >
                        {{ d }} Days
                    </button>
                </div>
            </div>
            
            <div v-if="!generatedLink" class="mt-2">
                <button 
                    @click="generateLink" 
                    :disabled="loading"
                    class="w-full py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                >
                    <span v-if="loading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                    {{ loading ? 'Generating...' : 'Create Public Link' }}
                </button>
            </div>
            
            <div v-else class="animate-in fade-in slide-in-from-top-2 duration-300">
                <div class="flex flex-col gap-1">
                    <label class="text-xs font-medium text-green-600">Link Ready!</label>
                    <div class="flex items-center gap-2">
                        <input 
                            readonly 
                            :value="generatedLink"
                            class="flex-1 text-sm p-2 border border-slate-200 rounded bg-slate-50 text-slate-600 outline-none focus:ring-1 focus:ring-blue-500"
                            @click="$event.target.select()"
                        />
                        <button 
                            @click="copyLink"
                            class="p-2 border border-slate-200 rounded hover:bg-slate-50 text-slate-600 transition-colors"
                            :class="copied ? 'text-green-600 border-green-200 bg-green-50' : ''"
                            :title="copied ? 'Copied' : 'Copy'"
                        >
                            <Check v-if="copied" :size="18" />
                            <Copy v-else :size="18" />
                        </button>
                    </div>
                </div>
                <p class="text-xs text-slate-400 mt-2 text-center">
                    This link will expire in {{ days }} days.
                </p>
            </div>
            
            <div v-if="error" class="bg-red-50 text-red-600 text-sm p-3 rounded-lg border border-red-100 flex gap-2">
                <span>⚠️</span> {{ error }}
            </div>
        </div>
      </div>
    </div>
  </div>
</template>
