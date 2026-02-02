import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

export const useAuthStore = defineStore('auth', () => {
    const token = ref<string | null>(localStorage.getItem('token'))
    const user = ref<string | null>(localStorage.getItem('user'))
    const role = ref<string | null>(localStorage.getItem('role')) // 'admin' | 'user'

    const isAuthenticated = computed(() => !!token.value)
    const isAdmin = computed(() => role.value === 'admin')

    const router = useRouter()

    function setAuth(newToken: string, newUser: string, newRole: string) {
        token.value = newToken
        user.value = newUser
        role.value = newRole

        localStorage.setItem('token', newToken)
        localStorage.setItem('user', newUser)
        localStorage.setItem('role', newRole)
    }

    function logout() {
        token.value = null
        user.value = null
        role.value = null

        localStorage.removeItem('token')
        localStorage.removeItem('user')
        localStorage.removeItem('role')

        // 强制刷新或重定向到登录页
        window.location.href = '/login'
    }

    async function login(username: string, password: string): Promise<boolean> {
        try {
            const formData = new URLSearchParams()
            formData.append('username', username)
            formData.append('password', password)

            const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/login/access-token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: formData
            })

            if (!response.ok) {
                return false
            }

            const data = await response.json()
            // data = { access_token: "...", token_type: "bearer" }
            // 这里的 Token 通常是 JWT, 我们需要解析它来获取 Role? 
            // 或者后端在 Login Response 中直接返回 Role 会更方便.
            // 目前后端只返回 access_token.
            // 我们可以简单地解析 JWT payloads (atob) 来获取 Role.

            const payload = JSON.parse(atob(data.access_token.split('.')[1]))
            setAuth(data.access_token, payload.sub, payload.role || 'user')

            return true
        } catch (e) {
            console.error("Login failed", e)
            return false
        }
    }

    return { token, user, role, isAuthenticated, isAdmin, login, logout }
})
