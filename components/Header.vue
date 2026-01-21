<script setup lang="ts">
import { Search, Bell } from 'lucide-vue-next';
</script>

<template>
  <header class="bg-white border-b border-gray-200 sticky top-0 z-40 h-16 flex items-center justify-between px-6 shadow-sm">
    <!-- Left: Logo -->
    <div class="flex items-center gap-3">
      <!-- Custom SVG Logo -->
      <div class="w-8 h-8 flex items-center justify-center">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
          <!-- Center Bar - Teal -->
          <rect x="10" y="3" width="4" height="18" rx="2" class="fill-teal-500" />
          
          <!-- Left Bar - Dark Blue -->
          <rect x="4" y="9" width="3" height="6" rx="1.5" class="fill-blue-700" />
          <circle cx="5.5" cy="5" r="1.5" class="fill-blue-700" />
          <circle cx="5.5" cy="19" r="1.5" class="fill-blue-700" />

          <!-- Right Bar - Dark Blue -->
          <rect x="17" y="9" width="3" height="6" rx="1.5" class="fill-blue-700" />
          <circle cx="18.5" cy="5" r="1.5" class="fill-blue-700" />
          <circle cx="18.5" cy="19" r="1.5" class="fill-blue-700" />
        </svg>
      </div>
      <span class="text-xl text-gray-800 tracking-tight flex gap-1.5 items-baseline">
        <span class="font-semibold">SensorHub</span>
        <span class="font-normal text-gray-600">Analytics</span>
      </span>
    </div>

    <!-- Middle: Navigation -->
    <nav class="hidden md:flex items-center gap-8 h-full">
      <a href="#" class="h-full flex items-center text-blue-600 font-semibold border-b-2 border-blue-600 px-1">
        Data Management
      </a>
      <a href="#" class="h-full flex items-center text-gray-500 hover:text-gray-800 hover:border-b-2 hover:border-gray-300 transition-colors px-1">
        Algorithm Analysis
      </a>
      <a href="#" class="h-full flex items-center text-gray-500 hover:text-gray-800 hover:border-b-2 hover:border-gray-300 transition-colors px-1">
        Report Center
      </a>
      <a href="#" class="h-full flex items-center text-gray-500 hover:text-gray-800 hover:border-b-2 hover:border-gray-300 transition-colors px-1">
        Settings
      </a>
    </nav>

    <!-- Right: Actions -->
    <div class="flex items-center gap-4">
      <div class="relative hidden lg:block">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="16" />
        <input 
          type="text" 
          placeholder="Search platform..." 
          class="pl-9 pr-4 py-1.5 bg-gray-100 border-none rounded-full text-sm focus:ring-2 focus:ring-blue-100 focus:bg-white transition-all w-64"
        />
      </div>
      <button class="relative p-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors">
        <Bell :size="20" />
        <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-white"></span>
      </button>
      <div class="flex items-center gap-2 cursor-pointer hover:bg-gray-100 p-1.5 rounded-lg transition-colors">
        <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 text-white flex items-center justify-center font-medium text-sm">
          JD
        </div>
        <span class="text-sm font-medium text-gray-700 hidden xl:block">John Doe</span>
      </div>
    </div>
  </header>
</template>
