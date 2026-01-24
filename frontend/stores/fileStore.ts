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
        pendingTasks: files.value.filter(f => f.status === FileStatus.Processing || f.status === FileStatus.Idle).length,
    }));

    // ===== ACTIONS =====

    /**
     * Fetch stats from backend
     */
    async function fetchStats() {
        try {
            statsData.value = await fileService.getStats();
            console.log('[FileStore] Fetched stats:', statsData.value);
        } catch (e) {
            console.error('[FileStore] Failed to fetch stats:', e);
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
     */
    function triggerParse(ids: string[]) {
        // 1. Set status to Processing
        ids.forEach(id => {
            const file = files.value.find(f => f.id === id);
            if (file) {
                file.status = FileStatus.Processing;
                file.progress = 0;
            }
        });

        // 2. Start mock progress
        const interval = setInterval(() => {
            let stillProcessing = false;

            files.value.forEach(file => {
                if (ids.includes(file.id) && file.status === FileStatus.Processing) {
                    const newProgress = (file.progress || 0) + 10;

                    if (newProgress >= 100) {
                        file.status = FileStatus.Ready;
                        file.progress = undefined;
                        if (file.packets.length === 0) {
                            file.packets = [
                                { name: 'ACC', freq: '100Hz', count: 10000, present: true },
                                { name: 'PPG', freq: '25Hz', count: 2500, present: true }
                            ];
                        }
                        if (file.duration === '--') {
                            file.duration = '00:10:00';
                        }
                    } else {
                        file.progress = newProgress;
                        stillProcessing = true;
                    }
                }
            });

            if (!stillProcessing) {
                clearInterval(interval);
            }
        }, 200);
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
    };
});
