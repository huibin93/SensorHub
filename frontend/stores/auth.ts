import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useToast } from '../composables/useToast'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const REFRESH_LEEWAY_MS = 5 * 60 * 1000
const CLOCK_SKEW_MS = 30 * 1000

type JwtPayload = {
    sub?: string
    role?: string
    exp?: number
}

function decodeJwtPayload(token: string): JwtPayload | null {
    const parts = token.split('.')
    if (parts.length < 2) return null

    const payloadPart = parts[1]
    const normalized = payloadPart.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')

    try {
        return JSON.parse(atob(padded)) as JwtPayload
    } catch {
        return null
    }
}

function isExpired(exp: number | null): boolean {
    if (!exp) return true
    return exp * 1000 <= Date.now() + CLOCK_SKEW_MS
}

export const useAuthStore = defineStore('auth', () => {
    const token = ref<string | null>(localStorage.getItem('token'))
    const user = ref<string | null>(localStorage.getItem('user'))
    const role = ref<string | null>(localStorage.getItem('role')) // 'admin' | 'user'
    const exp = ref<number | null>(null)

    const isAuthenticated = computed(() => !!token.value && !isExpired(exp.value))
    const isAdmin = computed(() => role.value === 'admin')

    const { addToast } = useToast()

    let heartbeatTimer: number | null = null
    let heartbeatEnabled = false
    let visibilityListenerAttached = false
    let storageListenerAttached = false
    let refreshPromise: Promise<string | null> | null = null
    let handledAuthExpired = false

    function persistState() {
        if (token.value) localStorage.setItem('token', token.value)
        else localStorage.removeItem('token')

        if (user.value) localStorage.setItem('user', user.value)
        else localStorage.removeItem('user')

        if (role.value) localStorage.setItem('role', role.value)
        else localStorage.removeItem('role')

        if (exp.value) localStorage.setItem('exp', String(exp.value))
        else localStorage.removeItem('exp')
    }

    function applyTokenFromStorage(newToken: string, payload: JwtPayload) {
        token.value = newToken
        if (payload.sub) user.value = payload.sub
        if (payload.role) role.value = payload.role
        exp.value = payload.exp ?? null

        if (heartbeatEnabled) {
            scheduleHeartbeat()
        }
    }

    function clearAuth(options: { redirect?: boolean } = {}) {
        token.value = null
        user.value = null
        role.value = null
        exp.value = null
        persistState()

        if (options.redirect ?? true) {
            window.location.href = '/login'
        }
    }

    function handleAuthExpired() {
        if (handledAuthExpired) return
        handledAuthExpired = true

        addToast('会话已过期，请重新登录', 'error')
        clearAuth({ redirect: false })
        stopHeartbeat()

        window.setTimeout(() => {
            window.location.href = '/login'
        }, 1200)
    }

    function initializeFromStorage() {
        if (!token.value) {
            exp.value = null
            persistState()
            return
        }

        const payload = decodeJwtPayload(token.value)
        if (!payload?.exp) {
            clearAuth({ redirect: false })
            return
        }

        if (payload.sub) user.value = payload.sub
        if (payload.role) role.value = payload.role
        exp.value = payload.exp
        persistState()

        if (isExpired(exp.value)) {
            clearAuth({ redirect: false })
        }
    }

    function scheduleHeartbeat() {
        if (!heartbeatEnabled) return

        if (heartbeatTimer) {
            window.clearTimeout(heartbeatTimer)
            heartbeatTimer = null
        }

        if (!token.value || !exp.value) return

        const delay = exp.value * 1000 - Date.now() - REFRESH_LEEWAY_MS
        if (delay <= 0) {
            void refreshToken()
            return
        }

        heartbeatTimer = window.setTimeout(() => {
            void refreshToken()
        }, delay)
    }

    function handleVisibilityChange() {
        if (document.visibilityState !== 'visible') return
        if (!token.value || !exp.value) return

        const remaining = exp.value * 1000 - Date.now()
        if (remaining <= REFRESH_LEEWAY_MS) {
            void refreshToken()
        } else {
            scheduleHeartbeat()
        }
    }

    function handleStorageChange(event: StorageEvent) {
        if (!event.key) return

        if (event.key === 'token') {
            if (!event.newValue) {
                token.value = null
                user.value = null
                role.value = null
                exp.value = null
                stopHeartbeat()
                return
            }

            const payload = decodeJwtPayload(event.newValue)
            if (payload?.exp) {
                applyTokenFromStorage(event.newValue, payload)
            } else {
                clearAuth({ redirect: false })
            }
            return
        }

        if (event.key === 'user') user.value = event.newValue
        if (event.key === 'role') role.value = event.newValue
        if (event.key === 'exp') exp.value = event.newValue ? Number(event.newValue) : null
    }

    function startHeartbeat() {
        handledAuthExpired = false

        if (heartbeatEnabled) {
            scheduleHeartbeat()
            return
        }

        heartbeatEnabled = true

        if (!visibilityListenerAttached) {
            document.addEventListener('visibilitychange', handleVisibilityChange)
            visibilityListenerAttached = true
        }

        if (!storageListenerAttached) {
            window.addEventListener('storage', handleStorageChange)
            storageListenerAttached = true
        }

        scheduleHeartbeat()
    }

    function stopHeartbeat() {
        heartbeatEnabled = false

        if (heartbeatTimer) {
            window.clearTimeout(heartbeatTimer)
            heartbeatTimer = null
        }

        if (visibilityListenerAttached) {
            document.removeEventListener('visibilitychange', handleVisibilityChange)
            visibilityListenerAttached = false
        }

        if (storageListenerAttached) {
            window.removeEventListener('storage', handleStorageChange)
            storageListenerAttached = false
        }
    }

    function setAuth(newToken: string, newUser: string, newRole: string, newExp: number | null) {
        token.value = newToken
        user.value = newUser
        role.value = newRole
        exp.value = newExp
        persistState()

        if (heartbeatEnabled) {
            scheduleHeartbeat()
        }
    }

    async function refreshToken(): Promise<string | null> {
        if (refreshPromise) return refreshPromise
        if (!token.value) return null

        refreshPromise = (async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/login/refresh-token`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token.value}`
                    }
                })

                if (!response.ok) {
                    handleAuthExpired()
                    return null
                }

                const data = await response.json()
                const payload = decodeJwtPayload(data.access_token)
                if (!payload?.exp || !payload.sub) {
                    handleAuthExpired()
                    return null
                }

                setAuth(
                    data.access_token,
                    payload.sub,
                    payload.role || role.value || 'user',
                    payload.exp
                )

                return data.access_token
            } catch (e) {
                console.error('Refresh token failed', e)
                handleAuthExpired()
                return null
            }
        })()

        try {
            return await refreshPromise
        } finally {
            refreshPromise = null
        }
    }

    async function ensureFreshToken(): Promise<string | null> {
        if (!token.value) return null

        if (!exp.value) {
            const payload = decodeJwtPayload(token.value)
            if (payload?.exp) {
                exp.value = payload.exp
                if (payload.sub) user.value = payload.sub
                if (payload.role) role.value = payload.role
                persistState()
            } else {
                handleAuthExpired()
                return null
            }
        }

        const remaining = (exp.value ?? 0) * 1000 - Date.now()
        if (remaining <= REFRESH_LEEWAY_MS) {
            return await refreshToken()
        }

        return token.value
    }

    function logout() {
        stopHeartbeat()
        clearAuth({ redirect: true })
    }

    async function login(username: string, password: string): Promise<boolean> {
        try {
            const formData = new URLSearchParams()
            formData.append('username', username)
            formData.append('password', password)

            const response = await fetch(`${API_BASE_URL}/login/access-token`, {
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
            const payload = decodeJwtPayload(data.access_token)

            if (!payload?.exp || !payload.sub) {
                console.error('Failed to parse token payload')
                return false
            }

            setAuth(data.access_token, payload.sub, payload.role || 'user', payload.exp)
            startHeartbeat()
            return true
        } catch (e) {
            console.error('Login failed', e)
            return false
        }
    }

    initializeFromStorage()

    return {
        token,
        user,
        role,
        exp,
        isAuthenticated,
        isAdmin,
        login,
        logout,
        refreshToken,
        startHeartbeat,
        stopHeartbeat,
        ensureFreshToken,
        handleAuthExpired
    }
})
