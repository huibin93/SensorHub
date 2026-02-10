/**
 * API 客户端配置
 * 
 * 配置 axios 实例并添加请求/响应拦截器
 */

import axios from 'axios';
import { useAuthStore } from '../stores/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// 创建 axios 实例
export const apiClient = axios.create({
    baseURL: API_BASE_URL,
});

let refreshPromise: Promise<string | null> | null = null;
let pendingRequests: Array<(token: string | null) => void> = [];

const processQueue = (newToken: string | null) => {
    pendingRequests.forEach(callback => callback(newToken));
    pendingRequests = [];
};

// 请求拦截器 - 添加 token
apiClient.interceptors.request.use(
    (config) => {
        const authStore = useAuthStore();
        if (authStore.token) {
            config.headers.Authorization = `Bearer ${authStore.token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// 响应拦截器 - 处理 401 错误
apiClient.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        if (error.response?.status !== 401) {
            return Promise.reject(error);
        }

        const authStore = useAuthStore();
        const originalRequest = error.config;

        if (!originalRequest || (originalRequest as any)._retry) {
            authStore.handleAuthExpired();
            return Promise.reject(error);
        }

        if (!authStore.token) {
            authStore.handleAuthExpired();
            return Promise.reject(error);
        }

        if (!refreshPromise) {
            refreshPromise = authStore.refreshToken()
                .then((newToken) => {
                    processQueue(newToken);
                    return newToken;
                })
                .catch((refreshError) => {
                    processQueue(null);
                    throw refreshError;
                })
                .finally(() => {
                    refreshPromise = null;
                });
        }

        return new Promise((resolve, reject) => {
            pendingRequests.push((newToken) => {
                if (!newToken) {
                    reject(error);
                    return;
                }

                (originalRequest as any)._retry = true;
                originalRequest.headers = originalRequest.headers || {};
                originalRequest.headers.Authorization = `Bearer ${newToken}`;
                resolve(apiClient(originalRequest));
            });
        });
    }
);

export default apiClient;
