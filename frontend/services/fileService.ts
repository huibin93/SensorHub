/**
 * File Service Layer
 * 
 * Abstracts data fetching from the backend.
 * Configuration is read from environment variables (.env file)
 */

import axios from 'axios';
import { SensorFile, DeviceType, FileStatus } from '../types';
import { MOCK_FILES } from '../constants';

// ===== CONFIGURATION (from .env) =====
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// ===== TYPE DEFINITIONS =====
export interface FileUpdatePayload {
    notes?: string;
    deviceType?: DeviceType;
    deviceModel?: string;
    testTypeL1?: string;
    testTypeL2?: string;
    status?: FileStatus;
}

export interface StatsResponse {
    totalFiles: number;
    todayUploads: number;
    pendingTasks: number;
    storageUsed: string;
    lastUpdated: string;
}

export interface FilesQueryParams {
    page?: number;
    limit?: number;
    search?: string;
    device?: string;
    status?: string;
    sort?: string;
}

export interface PaginatedFilesResponse {
    items: SensorFile[];
    total: number;
    page: number;
    limit: number;
    totalPages: number;
}

// ===== SERVICE IMPLEMENTATION =====
export const fileService = {
    /**
     * Fetch system statistics
     */
    async getStats(): Promise<StatsResponse> {
        if (USE_MOCK) {
            await new Promise(resolve => setTimeout(resolve, 50));
            return {
                totalFiles: 1251,
                todayUploads: 33,
                pendingTasks: 6,
                storageUsed: '450 GB',
                lastUpdated: new Date().toISOString()
            };
        }

        const response = await axios.get<StatsResponse>(`${API_BASE_URL}/stats`);
        return response.data;
    },

    /**
     * Fetch paginated sensor files
     */
    async getFiles(params: FilesQueryParams = {}): Promise<PaginatedFilesResponse> {
        if (USE_MOCK) {
            // Simulate network delay for realistic feel
            await new Promise(resolve => setTimeout(resolve, 100));
            return {
                items: [...MOCK_FILES],
                total: MOCK_FILES.length,
                page: params.page || 1,
                limit: params.limit || 20,
                totalPages: 1
            };
        }

        const response = await axios.get<PaginatedFilesResponse>(`${API_BASE_URL}/files`, {
            params: {
                page: params.page || 1,
                limit: params.limit || 20,
                search: params.search || undefined,
                device: params.device || undefined,
                status: params.status || undefined,
                sort: params.sort || '-uploadTime'
            }
        });
        return response.data;
    },

    /**
     * Update a file by ID
     */
    async updateFile(id: string, data: FileUpdatePayload): Promise<SensorFile> {
        if (USE_MOCK) {
            await new Promise(resolve => setTimeout(resolve, 50));
            console.log('[FileService] Mock update:', id, data);
            // In mock mode, we don't actually persist - Store handles local state
            return {} as SensorFile;
        }

        const response = await axios.patch<SensorFile>(`${API_BASE_URL}/files/${id}`, data);
        return response.data;
    },

    /**
     * Delete a file by ID
     */
    async deleteFile(id: string): Promise<void> {
        if (USE_MOCK) {
            await new Promise(resolve => setTimeout(resolve, 50));
            console.log('[FileService] Mock delete:', id);
            return;
        }

        await axios.delete(`${API_BASE_URL}/files/${id}`);
    },

    /**
     * Delete multiple files
     */
    async deleteFiles(ids: string[]): Promise<void> {
        if (USE_MOCK) {
            await new Promise(resolve => setTimeout(resolve, 50));
            console.log('[FileService] Mock batch delete:', ids);
            return;
        }

        await axios.post(`${API_BASE_URL}/files/batch-delete`, { ids });
    },

    /**
     * Upload a file with progress callback
     */
    async uploadFile(
        file: File,
        onProgress?: (percent: number) => void
    ): Promise<{ success: boolean; fileId: string; filename: string; message: string }> {
        if (USE_MOCK) {
            // Simulate upload progress
            for (let i = 0; i <= 100; i += 10) {
                await new Promise(resolve => setTimeout(resolve, 100));
                if (onProgress) onProgress(i);
            }
            return {
                success: true,
                fileId: 'mock_' + Date.now(),
                filename: file.name,
                message: 'Mock upload complete'
            };
        }

        const formData = new FormData();
        formData.append('file', file);

        const response = await axios.post(`${API_BASE_URL}/files/upload`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            },
            onUploadProgress: (progressEvent) => {
                if (onProgress && progressEvent.total) {
                    const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    onProgress(percent);
                }
            }
        });

        return response.data;
    },

    /**
     * Get file structure (content_meta after parsing)
     */
    async getFileStructure(id: string): Promise<{
        fileId: string;
        status: string;
        processedDir: string | null;
        contentMeta: {
            summary?: { total_rows: number; file_size_kb: number };
            keys?: Record<string, { rows: number; columns: string[]; preview: string }>;
        };
    }> {
        if (USE_MOCK) {
            return {
                fileId: id,
                status: 'Idle',
                processedDir: null,
                contentMeta: {}
            };
        }

        const response = await axios.get(`${API_BASE_URL}/files/${id}/structure`);
        return response.data;
    },

    /**
     * Get parsed data for a specific key
     */
    async getFileData(
        id: string,
        key: string,
        options?: { limit?: number; columns?: string[] }
    ): Promise<{
        key: string;
        columns: string[];
        rows: number;
        data: Record<string, unknown>[];
    }> {
        if (USE_MOCK) {
            return { key, columns: [], rows: 0, data: [] };
        }

        const params = new URLSearchParams();
        if (options?.limit) params.append('limit', String(options.limit));
        if (options?.columns) params.append('columns', options.columns.join(','));

        const response = await axios.get(
            `${API_BASE_URL}/files/${id}/data/${key}?${params.toString()}`
        );
        return response.data;
    },

    /**
     * Download a single file as ZIP
     */
    downloadFile(id: string): void {
        window.open(`${API_BASE_URL}/files/${id}/download`, '_blank');
    },

    /**
     * Batch download multiple files as ZIP
     */
    async batchDownload(ids: string[]): Promise<void> {
        const response = await axios.post(
            `${API_BASE_URL}/files/batch-download`,
            { ids },
            { responseType: 'blob' }
        );

        // Create download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'batch_download.zip');
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    },

    /**
     * Trigger parsing for a file
     */
    async triggerParse(id: string, options?: Record<string, unknown>): Promise<{
        success: boolean;
        message: string;
        status: string;
    }> {
        if (USE_MOCK) {
            return { success: true, message: 'Mock parse triggered', status: 'Processing' };
        }

        const response = await axios.post(`${API_BASE_URL}/files/${id}/parse`, { options });
        return response.data;
    }
};
