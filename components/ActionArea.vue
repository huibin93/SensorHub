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
    <!-- Upload Section (Left - Larger) -->
    <div class="lg:col-span-8 bg-white rounded-xl p-6 shadow-sm border border-gray-200">
      <h2 class="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <UploadCloud :size="20" class="text-gray-400" />
          Quick Upload
      </h2>
      
      <!-- Unified Upload Zone -->
      <button class="w-full group relative flex flex-col items-center justify-center p-8 rounded-xl border-2 border-dashed border-blue-200 bg-blue-50/30 hover:bg-blue-50 hover:border-blue-400 transition-all duration-300">
          <div class="p-4 bg-blue-100 text-blue-600 rounded-full mb-3 group-hover:bg-blue-600 group-hover:text-white group-hover:scale-110 transition-all duration-300">
              <UploadCloud :size="32" />
          </div>
          <h3 class="text-lg font-bold text-gray-900 mb-1">Upload Data Files</h3>
          <p class="text-sm text-gray-500 mb-4">Support .rawdata or .zip files</p>
          <div class="flex gap-2">
            <span class="text-xs font-semibold text-blue-600 bg-blue-100 px-3 py-1 rounded-full">.rawdata</span>
            <span class="text-xs font-semibold text-blue-600 bg-blue-100 px-3 py-1 rounded-full">.zip</span>
          </div>
      </button>
    </div>

    <!-- Stats Section (Right) -->
    <div class="lg:col-span-4 grid grid-cols-2 gap-4">
        <!-- Stat Cards -->
        <div class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-center h-full">
            <div class="flex items-center gap-2 mb-2 text-gray-400">
                <FileText :size="18" />
                <span class="text-xs font-medium uppercase tracking-wider">Total Files</span>
            </div>
            <div class="text-2xl font-bold text-gray-800">{{ MOCK_STATS.totalFiles.toLocaleString() }}</div>
        </div>

        <div class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-center h-full">
            <div class="flex items-center gap-2 mb-2 text-gray-400">
                <CheckCircle :size="18" />
                <span class="text-xs font-medium uppercase tracking-wider">Today's Uploads</span>
            </div>
            <div class="text-2xl font-bold text-gray-800">{{ MOCK_STATS.todayUploads }}</div>
        </div>

        <div class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-center h-full">
            <div class="flex items-center gap-2 mb-2 text-orange-500">
                <Clock :size="18" />
                <span class="text-xs font-medium uppercase tracking-wider">Pending Tasks</span>
            </div>
            <div class="text-2xl font-bold text-gray-800">{{ MOCK_STATS.pendingTasks }}</div>
        </div>

        <div class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-center h-full">
            <div class="flex items-center gap-2 mb-2 text-gray-400">
                <Database :size="18" />
                <span class="text-xs font-medium uppercase tracking-wider">Storage Used</span>
            </div>
            <div class="text-2xl font-bold text-gray-800">{{ MOCK_STATS.storageUsed }}</div>
        </div>
    </div>
  </div>
</template>
