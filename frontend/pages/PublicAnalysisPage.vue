<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const token = ref(route.query.token as string)
const fileId = ref(route.query.fid as string)
const loading = ref(true)
const error = ref('')
const fileData = ref<any>(null)

// API Base
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const loadData = async () => {
    if (!token.value) {
        error.value = "Invalid Link: Token Missing"
        loading.value = false
        return
    }
    
    try {
        const res = await fetch(`${API_BASE}/public/file?token=${token.value}`)
        if (!res.ok) {
            throw new Error(await res.text())
        }
        fileData.value = await res.json()
    } catch (e: any) {
        error.value = `Access Denied: ${e.message}`
    } finally {
        loading.value = false
    }
}

onMounted(() => {
    loadData()
})
</script>

<template>
  <div class="public-container">
    <div v-if="loading" class="loading">
       Loading Shared Data...
    </div>
    
    <div v-else-if="error" class="error-box">
       <h1>⚠️ Access Denied</h1>
       <p>{{ error }}</p>
    </div>
    
    <div v-else class="content-box">
       <header>
          <h1>{{ fileData.filename }}</h1>
          <div class="meta">
             <span>Size: {{ fileData.size }}</span>
             <span>Uploaded: {{ new Date(fileData.uploadTime).toLocaleString() }}</span>
          </div>
       </header>
       
       <div class="viewer-placeholder">
          <!-- TODO: Reuse Log Viewer Components here if possible -->
          <!-- For now, just show metadata to prove access -->
          <div class="json-dump">
             <pre>{{ JSON.stringify(fileData.contentMeta, null, 2) }}</pre>
          </div>
          
          <div class="warning">
            Note: Full interactive chart visualization requires login. 
            This is a preview of the metadata.
          </div>
       </div>
    </div>
  </div>
</template>

<style scoped>
.public-container {
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
    font-family: sans-serif;
}
.error-box {
    text-align: center;
    color: #e74c3c;
    margin-top: 5rem;
}
.content-box header {
    border-bottom: 1px solid #eee;
    padding-bottom: 1rem;
    margin-bottom: 2rem;
}
.meta {
    color: #7f8c8d;
    font-size: 0.9rem;
    margin-top: 0.5rem;
    display: flex;
    gap: 1rem;
}
.json-dump {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
    overflow-x: auto;
}
.warning {
    margin-top: 1rem;
    background: #fff3cd;
    color: #856404;
    padding: 1rem;
    border-radius: 4px;
}
</style>
