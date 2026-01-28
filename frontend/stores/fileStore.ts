import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import { SensorFile, FileStatus, DeviceType } from '../types';
import { fileService, StatsResponse } from '../services/fileService';

export const useFileStore = defineStore('files', () => {
    // ===== STATE =====
    const files = ref<SensorFile[]>([]);
    const isLoading = ref(false);
    const error = ref<string | null>(null);
    const statsData = ref<StatsResponse>({
        totalFiles: 0,
        todayUploads: 0,
        pendingTasks: 0,
        storageUsed: '--',
        lastUpdated: ''
    });

    // ===== GETTERS =====
    // Stats is now from API, but we also compute pending from local files for real-time update
    const stats = computed(() => ({
        ...statsData.value,
        totalFiles: files.value.length > 0 ? files.value.length : statsData.value.totalFiles,
        pendingTasks: files.value.filter(f => f.status === FileStatus.Processing || f.status === FileStatus.Unverified).length,
    }));

    // ===== ACTIONS =====

    /**
     * Fetch stats from backend
     */
    async function fetchStats() {
        try {
            statsData.value = {
                ...await fileService.getStats(),
                lastUpdated: new Date().toLocaleTimeString()
            };
            console.log('[FileStore] Fetched stats:', statsData.value);
        } catch (e) {
            console.error('[FileStore] Failed to fetch stats:', e);
            statsData.value.lastUpdated = '--';
        }
    }

    /**
     * Fetch files from service with pagination
     */
    async function fetchFiles(params: { page?: number; limit?: number; search?: string; device?: string; status?: string } = {}) {
        isLoading.value = true;
        error.value = null;
        try {
            const response = await fileService.getFiles(params);
            files.value = response.items;
            // Update pagination info in stats
            statsData.value = {
                ...statsData.value,
                totalFiles: response.total
            };
            console.log('[FileStore] Fetched files:', response.items.length, 'of', response.total);
        } catch (e) {
            error.value = e instanceof Error ? e.message : 'Failed to fetch files';
            console.error('[FileStore] Error fetching files:', e);
        } finally {
            isLoading.value = false;
        }

        // Auto-poll if any file is unverified
        checkPolling();
    }

    /**
     * Poll keys for unverified files
     */
    let pollTimeout: number | undefined;
    function checkPolling() {
        if (pollTimeout) clearTimeout(pollTimeout);

        const hasUnverified = files.value.some(f => f.status === FileStatus.Unverified);
        if (hasUnverified) {
            console.log('[FileStore] Polling for verification...');
            pollTimeout = window.setTimeout(() => {
                fetchFiles(); // Re-fetch
            }, 3000);
        }
    }

    /**
     * Update a file's notes
     */
    async function updateNote(id: string, note: string) {
        console.log('[FileStore] updateNote called', { id, note });
        const file = files.value.find(f => f.id === id);
        if (file) {
            const oldNote = file.notes;
            file.notes = note;  // Optimistic update
            try {
                await fileService.updateFile(id, { notes: note });
            } catch (e) {
                file.notes = oldNote;  // Rollback on error
                console.error('[FileStore] Failed to update note:', e);
            }
        }
    }

    /**
     * Update a file's device info
     */
    async function updateDevice(id: string, deviceType: DeviceType, deviceModel: string) {
        console.log('[FileStore] updateDevice called', { id, deviceType, deviceModel });
        const file = files.value.find(f => f.id === id);
        if (file) {
            const oldType = file.deviceType;
            const oldModel = file.deviceModel;
            file.deviceType = deviceType;  // Optimistic update
            file.deviceModel = deviceModel;
            try {
                await fileService.updateFile(id, { deviceType, deviceModel });
            } catch (e) {
                file.deviceType = oldType;  // Rollback on error
                file.deviceModel = oldModel;
                console.error('[FileStore] Failed to update device:', e);
            }
        }
    }

    /**
     * Update a file's test type
     */
    async function updateTestType(id: string, l1: string, l2: string) {
        console.log('[FileStore] updateTestType called', { id, l1, l2 });
        const file = files.value.find(f => f.id === id);
        if (file) {
            const oldL1 = file.testTypeL1;
            const oldL2 = file.testTypeL2;
            file.testTypeL1 = l1;  // Optimistic update
            file.testTypeL2 = l2;
            try {
                await fileService.updateFile(id, { testTypeL1: l1, testTypeL2: l2 });
            } catch (e) {
                file.testTypeL1 = oldL1;  // Rollback on error
                file.testTypeL2 = oldL2;
                console.error('[FileStore] Failed to update test type:', e);
            }
        }
    }

    /**
     * Trigger parse for selected files
     * 1. Call backend parse API
     * 2. Show local progress animation (10MB/s estimate)
     * 3. Poll backend for status change to 'Parsed'
     */
    async function triggerParse(ids: string[]) {
        for (const id of ids) {
            const file = files.value.find(f => f.id === id);
            if (!file) continue;

            // 设置本地UI为处理中
            file.status = FileStatus.Processing;
            file.progress = 0;

            // 调用后端解析API
            fileService.triggerParse(id).catch(e => {
                console.error('[FileStore] Failed to trigger parse:', e);
            });

            // 估算进度动画时长 (10MB/s)
            // 从 file.size 解析数字 (支持 "1.5 KB" 或 "10.2 MB")
            const sizeMatch = file.size.match(/(\d+\.?\d*)\s*(KB|MB|GB)/i);
            let sizeInMB = 1; // 默认 1MB
            if (sizeMatch) {
                const value = parseFloat(sizeMatch[1]);
                const unit = sizeMatch[2].toUpperCase();
                if (unit === 'KB') sizeInMB = value / 1024;
                else if (unit === 'MB') sizeInMB = value;
                else if (unit === 'GB') sizeInMB = value * 1024;
            }

            const totalDurationMs = Math.max(sizeInMB / 10 * 1000, 500); // 最少 500ms
            const updateInterval = 100; // 每 100ms 更新一次
            const progressStep = 100 / (totalDurationMs / updateInterval);

            // 本地进度动画
            const animationInterval = setInterval(() => {
                const currentFile = files.value.find(f => f.id === id);
                if (!currentFile || currentFile.status !== FileStatus.Processing) {
                    clearInterval(animationInterval);
                    return;
                }

                const newProgress = Math.min((currentFile.progress || 0) + progressStep, 99);
                currentFile.progress = Math.round(newProgress);

                // 进度到 99% 后停止动画, 等待后端确认
                if (newProgress >= 99) {
                    clearInterval(animationInterval);
                }
            }, updateInterval);

            // 轮询后端状态 (每 500ms 检查一次)
            const pollInterval = setInterval(async () => {
                try {
                    const response = await fileService.getFiles({ page: 1, limit: 1000 });
                    const updatedFile = response.items.find(f => f.id === id);

                    if (updatedFile && updatedFile.status === FileStatus.Processed) {
                        clearInterval(pollInterval);
                        const localFile = files.value.find(f => f.id === id);
                        if (localFile) {
                            localFile.status = FileStatus.Processed;
                            localFile.progress = undefined;
                        }
                        console.log('[FileStore] Parse completed for:', id);
                    }
                } catch (e) {
                    console.error('[FileStore] Poll error:', e);
                }
            }, 500);

            // 超时保护: 30秒后停止轮询
            setTimeout(() => {
                clearInterval(pollInterval);
                const localFile = files.value.find(f => f.id === id);
                if (localFile && localFile.status === FileStatus.Processing) {
                    localFile.status = FileStatus.Processed; // 假设成功
                    localFile.progress = undefined;
                }
            }, 30000);
        }
    }

    /**
     * Delete files by IDs
     */
    async function deleteFiles(ids: string[]) {
        const backup = [...files.value];
        files.value = files.value.filter(f => !ids.includes(f.id));  // Optimistic update
        console.log('[FileStore] Deleted files:', ids);
        try {
            await fileService.deleteFiles(ids);
        } catch (e) {
            files.value = backup;  // Rollback on error
            console.error('[FileStore] Failed to delete files:', e);
        }
    }

    /**
     * Delete single file
     */
    async function deleteFile(id: string) {
        const backup = [...files.value];
        files.value = files.value.filter(f => f.id !== id);  // Optimistic update
        console.log('[FileStore] Deleted file:', id);
        try {
            await fileService.deleteFile(id);
        } catch (e) {
            files.value = backup;  // Rollback on error
            console.error('[FileStore] Failed to delete file:', e);
        }
    }

    /**
     * Download single file
     */
    async function downloadFile(id: string, filename: string) {
        console.log('[FileStore] Downloading file:', id, filename);
        try {
            await fileService.downloadFile(id, filename);
        } catch (e) {
            console.error('[FileStore] Failed to download file:', e);
            error.value = 'File download failed';
        }
    }

    /**
     * Batch download files
     */
    async function batchDownload(ids: string[]) {
        console.log('[FileStore] Batch downloading files:', ids.length);

        const selectedFiles = files.value
            .filter(f => ids.includes(f.id))
            .map(f => ({
                id: f.id,
                filename: f.filename,
                nameSuffix: f.nameSuffix
            }));

        try {
            await fileService.batchDownload(selectedFiles);
        } catch (e) {
            console.error('[FileStore] Failed to batch download:', e);
            error.value = 'Batch download failed';
        }
    }

    return {
        // State
        files,
        isLoading,
        error,
        // Getters
        stats,
        // Actions
        fetchStats,
        fetchFiles,
        updateNote,
        updateDevice,
        updateTestType,
        triggerParse,
        deleteFiles,
        deleteFile,
        downloadFile,
        batchDownload,
    };
});
