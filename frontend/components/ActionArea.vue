<script setup lang="ts">
import { UploadCloud, FileText, Database, CheckCircle, Clock } from 'lucide-vue-next';
import { MOCK_STATS } from '../constants';

const StatCard = {
  props: {
    label: String,
    value: String,
    highlight: Boolean,
  },
  components: {
    FileText, CheckCircle, Clock, Database
  }
};
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
    <!-- Upload Section (Left - 2/3 width) -->
    <div class="lg:col-span-7 flex flex-col">
      <h2 class="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2 px-1">
          <UploadCloud :size="18" class="text-slate-400" />
          Quick Upload
      </h2>
      
      <!-- Unified Upload Zone -->
      <button class="w-full flex-1 group relative flex flex-col items-center justify-center py-6 px-4 rounded-2xl border border-dashed border-slate-300 bg-white hover:border-blue-500 hover:bg-blue-50/10 hover:shadow-md transition-all duration-300 shadow-sm min-h-[140px]">
          <div class="p-3 bg-blue-50 text-blue-600 rounded-full mb-3 group-hover:bg-blue-600 group-hover:text-white group-hover:scale-110 transition-all duration-300 shadow-sm shadow-blue-100">
              <UploadCloud :size="24" />
          </div>
          <h3 class="text-lg font-bold text-slate-800 mb-1 text-center">Upload Data</h3>
          <p class="text-xs text-slate-400 mb-3 text-center font-medium">Support .rawdata or .zip files</p>
          <div class="flex gap-2 flex-wrap justify-center">
            <span class="text-[10px] font-semibold text-slate-500 bg-slate-100/80 px-2.5 py-1 rounded-full border border-slate-200">.rawdata</span>
            <span class="text-[10px] font-semibold text-slate-500 bg-slate-100/80 px-2.5 py-1 rounded-full border border-slate-200">.zip</span>
          </div>
      </button>
    </div>

    <!-- Stats Section (Right - 1/3 width) -->
    <div class="lg:col-span-5 flex flex-col">
         <!-- Spacer to match Left Title Alignment -->
        <div class="mb-3 h-[28px] flex items-end pb-1 px-1 justify-between">
           <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">System Overview</span>
           <span class="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">Updated: Just now</span>
        </div>

        <!-- Merged Stats Container -->
        <div class="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0 divide-slate-100 items-center min-h-[140px]">
            
            <div class="p-5 flex flex-col justify-center items-center h-full hover:bg-slate-50 transition-all duration-300 first:rounded-l-2xl group cursor-default">
                <div class="flex flex-col items-center gap-2 mb-1">
                    <FileText :size="18" class="text-slate-400 group-hover:text-blue-500 transition-colors" />
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 text-center">Total Files</span>
                </div>
                <div class="text-2xl font-bold text-slate-800 group-hover:scale-105 transition-transform">{{ MOCK_STATS.totalFiles.toLocaleString() }}</div>
            </div>

            <div class="p-5 flex flex-col justify-center items-center h-full hover:bg-slate-50 transition-all duration-300 group cursor-default">
                <div class="flex flex-col items-center gap-2 mb-1">
                    <CheckCircle :size="18" class="text-slate-400 group-hover:text-green-500 transition-colors" />
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 text-center">Today</span>
                </div>
                <div class="text-2xl font-bold text-slate-800 group-hover:scale-105 transition-transform">{{ MOCK_STATS.todayUploads }}</div>
            </div>

            <div class="p-5 flex flex-col justify-center items-center h-full hover:bg-slate-50 transition-all duration-300 group cursor-default">
                <div class="flex flex-col items-center gap-2 mb-1">
                    <Clock :size="18" class="text-slate-400 group-hover:text-amber-500 transition-colors" />
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 text-center">Pending</span>
                </div>
                <div class="text-2xl font-bold text-slate-800 group-hover:scale-105 transition-transform">{{ MOCK_STATS.pendingTasks }}</div>
            </div>

            <div class="p-5 flex flex-col justify-center items-center h-full hover:bg-slate-50 transition-all duration-300 last:rounded-r-2xl group cursor-default">
                <div class="flex flex-col items-center gap-2 mb-1">
                    <Database :size="18" class="text-slate-400 group-hover:text-purple-500 transition-colors" />
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 text-center">Storage</span>
                </div>
                <div class="text-2xl font-bold text-slate-800 group-hover:scale-105 transition-transform">{{ MOCK_STATS.storageUsed }}</div>
            </div>
        </div>
    </div>
  </div>
</template>
