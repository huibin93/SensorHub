import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import { SensorFile, FileStatus, DeviceType } from '../types';
import { fileService, StatsResponse, type FilesQueryParams } from '../services/fileService';

export const useFileStore = defineStore('files', () => {
    // ===== STATE =====
    const files = ref<SensorFile[]>([]);
    const isLoading = ref(false);
    const error = ref<string | null>(null);
    const statsData = ref<StatsResponse>({
        totalFiles: 0,
        todayUploads: 0,
        pendingTasks: 0,
        storageUsed: 0
    });

    // ===== GETTERS =====
    // Stats is now from API, but we also compute pending from local files for real-time update
    const stats = computed(() => ({
        ...statsData.value,
        totalFiles: files.value.length > 0 ? statsData.value.totalFiles : statsData.value.totalFiles, // Trust backend for total count unless searching? actually existing logic seemed weird. Let's rely on statsData mainly. But current file list might be filtered. Stick to statsData for global stats.
        // Actually, let's keep it simple: prefer statsData for everything global.
        // But for pendingTasks, we might want real-time feedback from local state?
        // "today's pending" is strict. Local files might not be from today.
        // So relying on backend statsData is safer.
        pendingTasks: files.value.some(f =>
            f.status === FileStatus.Processing ||
            f.status === FileStatus.Unverified ||
            f.status === FileStatus.Idle
        )
            ? statsData.value.pendingTasks // Backend handles the "today" scoping logic
            : statsData.value.pendingTasks
    }));

    // ===== ACTIONS =====
    /**
     * 向列表增量添加文件 (通常用于上传后)
     */
    function addFiles(newFiles: SensorFile | SensorFile[]) {
        const toAdd = Array.isArray(newFiles) ? newFiles : [newFiles];
        // 过滤掉已存在的 (防止重复同步)
        const existingIds = new Set(files.value.map(f => f.id));
        const filtered = toAdd.filter(f => !existingIds.has(f.id));

        if (filtered.length > 0) {
            files.value = [...filtered, ...files.value];
            console.log('[FileStore] Incremental add:', filtered.length, 'files');
            // 上传后启动轮询以检查验证状态
            checkPolling();
        }
    }

    /**
     * 从后端获取统计信息
     */
    async function fetchStats() {
        try {
            statsData.value = await fileService.getStats();
            console.log('[FileStore] Fetched stats:', statsData.value);
        } catch (e) {
            console.error('[FileStore] Failed to fetch stats:', e);
            // statsData.value.lastUpdated = '--'; // Removed
        }
    }

    /**
     * 从服务中获取分页文件
     */
    // Last fetch params for polling
    const lastFetchParams = ref<FilesQueryParams>({});

    /**
     * 从服务中获取分页文件
     */
    async function fetchFiles(params: { page?: number; limit?: number; search?: string; device?: string; status?: string } = {}) {
        isLoading.value = true;
        error.value = null;

        // 智能参数合并:
        // 1. 如果提供了明确的参数 -> 使用它们并更新缓存
        // 2. 如果参数为空 (轮询/刷新) -> 使用缓存
        // 3. 默认限制为 2000 以进行客户端分页
        if (Object.keys(params).length > 0) {
            lastFetchParams.value = { ...params };
        }

        const finalParams = {
            limit: 2000, // Default to high limit for client-side pagination
            ...lastFetchParams.value,
            ...params
        };

        try {
            const response = await fileService.getFiles(finalParams);
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

    let pollTimeout: number | undefined;
    function checkPolling() {
        if (pollTimeout) clearTimeout(pollTimeout);

        const hasUnverified = files.value.some(f => f.status === FileStatus.Unverified);
        const hasProcessing = files.value.some(f => f.status === FileStatus.Processing);

        if (hasUnverified || hasProcessing) {
            console.log(`[FileStore] Polling for state updates (unverified: ${hasUnverified}, processing: ${hasProcessing})...`);
            pollTimeout = window.setTimeout(() => {
                fetchFiles(); // Re-fetch
            }, 3000);
        }
    }

    /**
     * 更新文件备注
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
     * 更新文件设备信息
     */
    async function updateDevice(id: string, deviceType: DeviceType, deviceModel: string, deviceName?: string) {
        console.log('[FileStore] updateDevice called', { id, deviceType, deviceModel, deviceName });
        const file = files.value.find(f => f.id === id);
        if (file) {
            const oldType = file.deviceType;
            const oldModel = file.deviceModel;
            file.deviceType = deviceType;  // Optimistic update
            file.deviceModel = deviceModel;
            try {
                await fileService.updateFile(id, { deviceType, deviceModel, deviceName });
                // Refetch all files to pick up cascaded device mapping changes
                await fetchFiles();
            } catch (e) {
                file.deviceType = oldType;  // Rollback on error
                file.deviceModel = oldModel;
                console.error('[FileStore] Failed to update device:', e);
            }
        }
    }

    /**
     * 更新文件测试类型
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
     * 触发选中文件的解析
     * 1. 调用后端解析 API
     * 2. 通过 SSE (Server-Sent Events) 实时接收进度推送
     */
    async function triggerParse(ids: string[]) {
        for (const id of ids) {
            const file = files.value.find(f => f.id === id);
            if (!file) continue;

            // 设置本地UI为处理中
            file.status = FileStatus.Processing;
            file.progress = 0;
            console.log(`[FileStore] triggerParse start: id=${id}, size=${file.size}`);

            // 调用后端解析API
            fileService.triggerParse(id).catch(e => {
                console.error('[FileStore] Failed to trigger parse:', e);
            });

            // SSE 订阅解析进度
            const sseUrl = fileService.getParseEventsUrl(id);
            console.log(`[FileStore] SSE connecting: ${sseUrl}`);
            const eventSource = new EventSource(sseUrl);

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    const localFile = files.value.find(f => f.id === id);
                    if (!localFile) { eventSource.close(); return; }

                    const prevProgress = localFile.progress ?? 0;
                    localFile.progress = data.progress ?? 0;

                    if (data.progress !== prevProgress) {
                        console.log(`[FileStore] SSE progress: id=${id}, ${prevProgress}% → ${data.progress}%`);
                    }

                    if (data.status === 'processed') {
                        console.log(`[FileStore] SSE: parse completed for ${id}`);
                        eventSource.close();
                        // 获取完整的解析结果
                        fileService.getFiles({ page: 1, limit: 1, search: id }).then(resp => {
                            const updated = resp.items.find(f => f.id === id);
                            if (updated && localFile) {
                                Object.assign(localFile, updated);
                                localFile.progress = undefined;
                            }
                        });
                    } else if (data.status === 'error') {
                        console.error(`[FileStore] SSE: parse failed for ${id}`);
                        eventSource.close();
                        fileService.getFiles({ page: 1, limit: 1, search: id }).then(resp => {
                            const updated = resp.items.find(f => f.id === id);
                            if (updated && localFile) {
                                Object.assign(localFile, updated);
                                localFile.progress = undefined;
                            }
                        });
                    }
                } catch (e) {
                    console.error('[FileStore] SSE parse error:', e);
                }
            };

            eventSource.addEventListener('done', () => {
                console.log(`[FileStore] SSE stream done for ${id}`);
                eventSource.close();
            });

            eventSource.onerror = (e) => {
                console.warn(`[FileStore] SSE error for ${id}, falling back to poll`, e);
                eventSource.close();
                // 降级: 如果 SSE 断开, 单次轮询获取最终状态
                setTimeout(() => {
                    const localFile = files.value.find(f => f.id === id);
                    if (localFile && localFile.status === FileStatus.Processing) {
                        fileService.getFiles({ page: 1, limit: 1, search: id }).then(resp => {
                            const updated = resp.items.find(f => f.id === id);
                            if (updated && localFile) {
                                Object.assign(localFile, updated);
                                localFile.progress = undefined;
                            }
                        }).catch(() => {});
                    }
                }, 3000);
            };

            // 超时保护: 5分钟后关闭 SSE
            setTimeout(() => {
                if (eventSource.readyState !== EventSource.CLOSED) {
                    console.warn(`[FileStore] SSE timeout for ${id}, closing`);
                    eventSource.close();
                    const localFile = files.value.find(f => f.id === id);
                    if (localFile && localFile.status === FileStatus.Processing) {
                        fileService.getFiles({ page: 1, limit: 1, search: id }).then(resp => {
                            const updated = resp.items.find(f => f.id === id);
                            if (updated && localFile) {
                                Object.assign(localFile, updated);
                                localFile.progress = undefined;
                            }
                        }).catch(() => {
                            if (localFile) {
                                localFile.status = FileStatus.Error;
                                localFile.progress = undefined;
                            }
                        });
                    }
                }
            }, 300000);
        }
    }

    /**
     * 按 ID 列表删除文件
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
     * 删除单个文件
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
     * 下载单个文件
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
     * 批量下载文件
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

    /**
     * 批量更新文件
     * 遍历 ID 并为每个 ID 调用 updateFile。
     */
    async function batchUpdate(ids: string[], updates: {
        deviceType?: string;
        deviceModel?: string;
        testTypeL1?: string;
        testTypeL2?: string;
        notes?: string;
    }) {
        console.log('[FileStore] Batch updating files:', ids.length, updates);

        let successCount = 0;
        let failCount = 0;

        // Create a copy of updates to avoid reference issues
        const payload: any = { ...updates };

        for (const id of ids) {
            const file = files.value.find(f => f.id === id);
            if (!file) continue;

            // Optimistic update
            const backup = { ...file };

            if (payload.deviceType) file.deviceType = payload.deviceType;
            if (payload.deviceModel) file.deviceModel = payload.deviceModel;
            if (payload.testTypeL1) file.testTypeL1 = payload.testTypeL1;
            if (payload.testTypeL2) file.testTypeL2 = payload.testTypeL2;
            if (payload.notes !== undefined) file.notes = payload.notes;

            try {
                await fileService.updateFile(id, payload);
                successCount++;
            } catch (e) {
                console.error(`[FileStore] Failed to update file ${id}:`, e);
                // Rollback
                Object.assign(file, backup);
                failCount++;
            }
        }

        console.log(`[FileStore] Batch update complete. Success: ${successCount}, Failed: ${failCount}`);

        // 只有当有失败时, 才可能需要刷新以确保一致性 (通常不需要, 因为我们已经做了乐观更新)
        if (failCount > 0) {
            console.warn('[FileStore] Some updates failed, optional refresh suggested but skipping for performance.');
        }

        return { success: successCount, failed: failCount };
    }

    /**
     * Fetch file content (分段读取)
     */
    async function fetchFileContent(id: string, offset: number = 0, limit: number = 1024 * 1024) {
        try {
            const response = await fileService.getFileContent(id, offset, limit);
            return response;
        } catch (e) {
            console.error('[FileStore] Failed to fetch file content:', e);
            throw e;
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
        addFiles,
        updateNote,
        updateDevice,
        updateTestType,
        triggerParse,
        deleteFiles,
        deleteFile,
        downloadFile,
        batchDownload,
        batchUpdate,
        fetchFileContent,
    };
});
