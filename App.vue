<script setup lang="ts">
import Header from './components/Header.vue';
import ActionArea from './components/ActionArea.vue';
import DataTable from './components/DataTable.vue';
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-gray-900 font-sans">
    <Header />
    
    <main class="max-w-[1600px] mx-auto p-4 md:p-6 lg:p-8">
      <!-- Section 2: Action & Stats Area -->
      <ActionArea />

      <!-- Section 3: Data Table Area -->
      <section>
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-bold text-gray-800">Recent Data Files</h2>
          <div class="flex gap-2">
              <!-- Optional Top Actions -->
          </div>
        </div>
        <DataTable />
      </section>
    </main>
  </div>
</template>
