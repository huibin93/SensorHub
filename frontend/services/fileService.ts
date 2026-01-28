/**
 * File Service Layer
 * 
 * Abstracts data fetching from the backend.
 * Configuration is read from environment variables (.env file)
 */

import axios from 'axios';
import { SensorFile, DeviceType, FileStatus } from '../types';
import { MOCK_FILES } from '../constants';
import { Decompress } from 'fzstd';
import streamSaver from 'streamsaver';
import { ZipWriter } from '@zip.js/zip.js';

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
                status: 'unverified',
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
     * Helper to trigger browser download
     */
    triggerDownload(blob: Blob, filename: string) {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    },

    /**
     * Download a single file (Stream Decompress Zst on client)
     */
    async downloadFile(id: string, filename: string): Promise<void> {
        if (USE_MOCK) {
            console.log('[FileService] Mock download:', id);
            return;
        }

        let writer: WritableStreamDefaultWriter | undefined;
        const startTime = performance.now();

        try {
            console.log(`[Download] Starting stream for file ID: ${id}, Filename: ${filename}`);

            // 1. Setup Stream Saver IMMEDIATELLY (User Request: Pop up save dialog first)
            console.log(`[Download] [${Math.round(performance.now() - startTime)}ms] Initializing StreamSaver...`);
            const fileStream = streamSaver.createWriteStream(filename);
            writer = fileStream.getWriter();

            // 2. Fetch .zst stream
            console.log(`[Download] [${Math.round(performance.now() - startTime)}ms] Fetching stream from backend...`);
            const response = await fetch(`${API_BASE_URL}/files/${id}/download`);
            if (!response.ok || !response.body) {
                if (writer) {
                    writer.abort(); // Abort the streamSaver writer if fetch fails
                }
                throw new Error(`Download failed: ${response.statusText}`);
            }
            console.log(`[Download] [${Math.round(performance.now() - startTime)}ms] Stream received. Content-Length: ${response.headers.get('content-length') || 'unknown'}`);

            // 3. Decompress & Pipe
            // Custom TransformStream for fzstd
            console.log(`[Download] [${Math.round(performance.now() - startTime)}ms] Starting Decompression Pipeline...`);
            let decoder: Decompress;

            const decompressStream = new TransformStream({
                start(controller) {
                    decoder = new Decompress((chunk) => {
                        controller.enqueue(chunk);
                    });
                },
                transform(chunk) {
                    // chunk is Uint8Array
                    decoder.push(chunk as Uint8Array);
                },
                flush() {
                    decoder.push(new Uint8Array(0), true);
                }
            });

            const decompressedStream = new Response(
                response.body.pipeThrough(decompressStream)
            ).body;

            if (!decompressedStream) {
                throw new Error('Decompression stream failed to initialize');
            }

            const reader = decompressedStream.getReader();
            let receivedLength = 0;

            const pump = async () => {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                        writer.close();
                        break;
                    }
                    receivedLength += value.length;
                    await writer.write(value);
                }
            };

            console.log(`[Download] [${Math.round(performance.now() - startTime)}ms] Pipe active. Writing to disk...`);
            await pump();
            const totalTime = performance.now() - startTime;
            console.log(`[Download] Complete: ${filename}. Total bytes written: ${receivedLength}. Duration: ${Math.round(totalTime)}ms. Avg Speed: ${Math.round(receivedLength / 1024 / (totalTime / 1000))} KB/s`);

        } catch (e) {
            console.error(`[Download] Failed for ${filename}:`, e);
            if (writer) {
                writer.abort(e).catch(() => { });
            }
            throw e;
        }
    },

    /**
     * Batch download multiple files as ZIP (Client-side Streaming)
     */
    async batchDownload(files: { id: string; filename: string; nameSuffix?: string }[]): Promise<void> {
        if (USE_MOCK) return;
        const totalStartTime = performance.now();

        try {
            console.log(`[BatchDownload] Starting batch download for ${files.length} files.`);

            // 1. Setup Stream Saver for the ZIP file
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
            const zipFilename = `sensorhub_batch_${timestamp}.zip`;

            console.log(`[BatchDownload] [${Math.round(performance.now() - totalStartTime)}ms] Initializing ZIP stream: ${zipFilename}`);
            const fileStream = streamSaver.createWriteStream(zipFilename);

            // 2. Setup ZipWriter
            // ZipWriter writes to the streamSaver writable stream
            const zipWriter = new ZipWriter(fileStream);

            // 3. Process each file sequentially
            let processedCount = 0;
            for (const file of files) {
                const fileStartTime = performance.now();
                processedCount++;

                // Construct filename logic (mirroring previous backend logic or UI logic)
                let name = file.filename;
                if (file.nameSuffix) {
                    if (name.toLowerCase().endsWith('.rawdata')) {
                        name = name.slice(0, -8) + file.nameSuffix + '.rawdata';
                    } else {
                        name = name + file.nameSuffix;
                    }
                }

                console.log(`[BatchDownload] [${processedCount}/${files.length}] Processing: ${name} (ID: ${file.id})`);

                try {
                    // Fetch .zst stream
                    const response = await fetch(`${API_BASE_URL}/files/${file.id}/download`);
                    if (!response.ok || !response.body) {
                        throw new Error(`Failed to fetch ${name}: ${response.statusText}`);
                    }

                    // Create Decompress Transform Stream
                    let decoder: Decompress;
                    const decompressStream = new TransformStream({
                        start(controller) {
                            decoder = new Decompress((chunk) => {
                                controller.enqueue(chunk);
                            });
                        },
                        transform(chunk) {
                            decoder.push(chunk as Uint8Array);
                        },
                        flush() {
                            decoder.push(new Uint8Array(0), true);
                        }
                    });

                    // Pipe response body through decompressor
                    // We get a ReadableStream of decompressed data
                    const decompressedReadable = new Response(
                        response.body.pipeThrough(decompressStream)
                    ).body;

                    if (!decompressedReadable) {
                        throw new Error('Decompression stream failed');
                    }

                    // Add to ZIP
                    // ZipWriter.add accepts a ReadableStream directly
                    await zipWriter.add(name, decompressedReadable);
                    const fileTime = performance.now() - fileStartTime;
                    console.log(`[BatchDownload] [${processedCount}/${files.length}] Added to ZIP: ${name}. Duration: ${Math.round(fileTime)}ms`);

                } catch (err) {
                    console.error(`[BatchDownload] Error processing file ${name}:`, err);
                    // Decide whether to abort or continue. Continuing allows partial success.
                    // But we might want to add an error log file to the zip?
                    // For now, just log to console.
                }
            }

            // 4. Close ZIP
            console.log(`[BatchDownload] Finalizing ZIP...`);
            const finalizeStart = performance.now();
            await zipWriter.close();
            console.log(`[BatchDownload] Finalized. Duration: ${Math.round(performance.now() - finalizeStart)}ms`);

            const totalDuration = performance.now() - totalStartTime;
            console.log(`[BatchDownload] Complete. Total files: ${files.length}. Total Duration: ${Math.round(totalDuration)}ms`);

        } catch (e) {
            console.error(`[BatchDownload] Failed:`, e);
            throw e;
        }
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
