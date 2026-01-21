<script setup lang="ts">
import { Watch, Circle, UploadCloud, FileText, Database, CheckCircle, Clock } from 'lucide-vue-next';
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
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Watch Upload -->
          <button class="group relative flex flex-col items-start p-5 rounded-xl border-2 border-blue-50 bg-blue-50/30 hover:bg-blue-50 hover:border-blue-200 transition-all duration-300 text-left">
              <div class="flex items-center justify-between w-full mb-3">
                  <div class="p-3 bg-blue-100 text-blue-600 rounded-lg group-hover:bg-blue-600 group-hover:text-white transition-colors">
                      <Watch :size="24" />
                  </div>
                  <span class="text-xs font-semibold text-blue-600 bg-blue-100 px-2 py-1 rounded">.rawdata</span>
              </div>
              <h3 class="text-lg font-bold text-gray-900">Upload Watch Data</h3>
              <p class="text-sm text-gray-500 mt-1">Supports Watch Series 5-8, Ultra models</p>
          </button>

          <!-- Ring Upload -->
          <button class="group relative flex flex-col items-start p-5 rounded-xl border-2 border-teal-50 bg-teal-50/30 hover:bg-teal-50 hover:border-teal-200 transition-all duration-300 text-left">
              <div class="flex items-center justify-between w-full mb-3">
                  <div class="p-3 bg-teal-100 text-teal-600 rounded-lg group-hover:bg-teal-600 group-hover:text-white transition-colors">
                      <Circle :size="24" />
                  </div>
                  <span class="text-xs font-semibold text-teal-600 bg-teal-100 px-2 py-1 rounded">.rawdata</span>
              </div>
              <h3 class="text-lg font-bold text-gray-900">Upload Ring Data</h3>
              <p class="text-sm text-gray-500 mt-1">Supports Smart Ring Pro, Oura Gen 3</p>
          </button>
      </div>
      <div class="mt-4 text-center border border-dashed border-gray-300 rounded-lg py-3 text-sm text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-colors cursor-pointer bg-gray-50/50">
          Or drag & drop .rawdata files here (auto-detect device type)
      </div>
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
