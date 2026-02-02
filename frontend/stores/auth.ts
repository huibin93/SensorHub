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

        // Save to LocalStorage
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

        // Redirect via window because router might not be ready or we want full reload
        window.location.href = '/login'
    }

    async function login(username: string, password: string): Promise<boolean> {
        try {
            const formData = new URLSearchParams()
            formData.append('username', username)
            formData.append('password', password)

            // Dynamic API Base
            const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

            const response = await fetch(`${apiBase}/login/access-token`, {
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
            // Parse JWT payload
            // data.access_token is "header.payload.signature"
            try {
                const payloadPart = data.access_token.split('.')[1]
                const payload = JSON.parse(atob(payloadPart))
                setAuth(data.access_token, payload.sub, payload.role || 'user')
                return true
            } catch (parseError) {
                console.error("Failed to parse token", parseError)
                return false
            }
        } catch (e) {
            console.error("Login failed", e)
            return false
        }
    }

    return { token, user, role, isAuthenticated, isAdmin, login, logout }
})
