<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const username = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)

const router = useRouter()
const authStore = useAuthStore()

const handleLogin = async () => {
    loading.value = true
    errorMsg.value = ''
    
    try {
        const success = await authStore.login(username.value, password.value)
        if (success) {
            router.push('/dashboard')
        } else {
            errorMsg.value = 'Invalid username or password'
        }
    } catch (e) {
        errorMsg.value = 'Login error'
    } finally {
        loading.value = false
    }
}
</script>

<template>
  <div class="login-container">
    <div class="login-box">
      <h1>SensorHub Login</h1>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>Username</label>
          <input v-model="username" type="text" required autofocus />
        </div>
        <div class="form-group">
          <label>Password</label>
          <!-- Show asterisks, standard password input -->
          <input v-model="password" type="password" required />
        </div>
        <div v-if="errorMsg" class="error">{{ errorMsg }}</div>
        <button type="submit" :disabled="loading">
            {{ loading ? 'Logging in...' : 'Login' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}

.login-box {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  width: 100%;
  max-width: 400px;
}

h1 {
  text-align: center;
  margin-bottom: 2rem;
  color: #333;
}

.form-group {
  margin-bottom: 1.5rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  color: #666;
}

input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

button {
  width: 100%;
  padding: 0.75rem;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.3s;
}

button:hover {
  background-color: #40a9ff;
}

button:disabled {
  background-color: #bae7ff;
  cursor: not-allowed;
}

.error {
  color: #ff4d4f;
  margin-bottom: 1rem;
  text-align: center;
}
</style>
