<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js' // Relative path

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
            router.push('/')
        } else {
            errorMsg.value = '用户名或密码错误'
        }
    } catch (e) {
        errorMsg.value = '登录失败，请重试'
    } finally {
        loading.value = false
    }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <div class="logo-area">
        <h1>SensorHub</h1>
        <p>数据管理与分析平台</p>
      </div>
      
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">账号</label>
          <input 
            id="username"
            v-model="username" 
            type="text" 
            placeholder="请输入用户名"
            required 
            autofocus 
          />
        </div>
        
        <div class="form-group">
          <label for="password">密码</label>
          <input 
            id="password"
            v-model="password" 
            type="password" 
            placeholder="请输入密码"
            required 
          />
        </div>
        
        <div v-if="errorMsg" class="error-message">
            <span class="icon">⚠️</span> {{ errorMsg }}
        </div>
        
        <button type="submit" :disabled="loading" class="login-button">
            <span v-if="loading" class="spinner"></span>
            {{ loading ? '登录中...' : '登 录' }}
        </button>
      </form>
      
      <div class="footer">
        <p>仅限内部人员访问</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

.login-card {
  background: white;
  width: 100%;
  max-width: 400px;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1);
  animation: slideUp 0.5s ease-out;
}

@keyframes slideUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.logo-area {
  text-align: center;
  margin-bottom: 30px;
}

h1 {
  margin: 0;
  color: #2c3e50;
  font-size: 28px;
  font-weight: 700;
}

.logo-area p {
    color: #7f8c8d;
    margin-top: 5px;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 8px;
  color: #34495e;
  font-weight: 500;
}

input {
  width: 100%;
  padding: 12px;
  border: 1px solid #dfe6e9;
  border-radius: 6px;
  font-size: 16px;
  transition: border-color 0.3s;
  box-sizing: border-box;
}

input:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
}

.login-button {
  width: 100%;
  padding: 12px;
  background-color: #3498db;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.3s, transform 0.1s;
  margin-top: 10px;
}

.login-button:hover {
  background-color: #2980b9;
}

.login-button:active {
  transform: scale(0.98);
}

.login-button:disabled {
  background-color: #95a5a6;
  cursor: not-allowed;
}

.error-message {
  background-color: #fee;
  color: #e74c3c;
  padding: 10px;
  border-radius: 6px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.footer {
    text-align: center;
    margin-top: 20px;
    font-size: 12px;
    color: #bdc3c7;
}
</style>
