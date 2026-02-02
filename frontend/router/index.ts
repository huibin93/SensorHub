import { createRouter, createWebHistory } from 'vue-router';

// Lazy load pages
const HomePage = () => import('../pages/HomePage.vue');
const DataManagementPage = () => import('../pages/DataManagementPage.vue');
const DeviceImportPage = () => import('../pages/DeviceImportPage.vue');
const FileContentView = () => import('../pages/FileContentView.vue');
const SerialToolPage = () => import('../pages/SerialToolPage.vue');

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            component: HomePage,
            children: [
                {
                    path: '',
                    name: 'DataManagement',
                    component: DataManagementPage,
                },
                {
                    path: 'device-import',
                    name: 'DeviceImport',
                    component: DeviceImportPage,
                },
                {
                    path: 'algorithm',
                    name: 'Algorithm',
                    component: () => import('../pages/PlaceholderPage.vue'),
                },
                // Removed Reports Route
                {
                    path: 'settings',
                    name: 'Settings',
                    component: () => import('../pages/SettingsPage.vue'),
                },
                {
                    path: 'serial-tool',
                    name: 'SerialTool',
                    component: SerialToolPage,
                },
                {
                    path: 'log-analysis',
                    name: 'LogAnalysis',
                    component: () => import('../pages/LogAnalysisPage.vue'),
                },
            ],
        },
        {
            path: '/files/:id/view',
            name: 'FileContent',
            component: FileContentView,
            props: true,
        },
        {
            path: '/logs/:id/view',
            name: 'LogContent',
            component: () => import('../pages/LogContentView.vue'),
            props: true,
        },
        {
            path: '/login',
            name: 'Login',
            component: () => import('../pages/LoginView.vue'),
            meta: { public: true }
        },
        {
            path: '/public/analysis',
            name: 'PublicAnalysis',
            component: () => import('../pages/PublicAnalysisPage.vue'),
            meta: { public: true }
        },
        // Removed AdminUser standalone route
    ],
});

import { useAuthStore } from '../stores/auth';

router.beforeEach((to, from, next) => {
    const authStore = useAuthStore();
    const isPublic = to.matched.some(record => record.meta.public);

    // 如果已登录且访问登录页 -> 跳转首页
    if (to.name === 'Login' && authStore.isAuthenticated) {
        next({ name: 'DataManagement' });
        return;
    }

    // 如果未登录且访问非公开页 -> 跳转登录页
    if (!isPublic && !authStore.isAuthenticated) {
        next({ name: 'Login', query: { redirect: to.fullPath } });
        return;
    }

    next();
});

export default router;
