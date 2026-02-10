import { ref } from 'vue'

export type ToastType = 'error' | 'success' | 'info'

export interface ToastItem {
    id: number
    msg: string
    type: ToastType
}

const toasts = ref<ToastItem[]>([])
let nextId = 1

function removeToast(id: number) {
    toasts.value = toasts.value.filter(toast => toast.id !== id)
}

function addToast(msg: string, type: ToastType = 'info', duration = 2500) {
    const id = nextId++
    toasts.value.push({ id, msg, type })

    if (duration > 0) {
        window.setTimeout(() => removeToast(id), duration)
    }

    return id
}

export function useToast() {
    return { toasts, addToast, removeToast }
}
