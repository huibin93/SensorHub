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
                {
                    path: 'reports',
                    name: 'Reports',
                    component: () => import('../pages/PlaceholderPage.vue'),
                },
                {
                    path: 'settings',
                    name: 'Settings',
                    component: () => import('../pages/PlaceholderPage.vue'),
                },
                {
                    path: 'serial-tool',
                    name: 'SerialTool',
                    component: SerialToolPage,
                },
            ],
        },
        {
            path: '/files/:id/view',
            name: 'FileContent',
            component: FileContentView,
            props: true,
        },
    ],
});

export default router;
