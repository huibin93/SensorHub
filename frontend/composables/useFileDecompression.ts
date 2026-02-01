import { ref, nextTick } from 'vue';
import { Decompress } from 'fzstd';
import { fileCacheService } from '../services/fileCacheService';

export interface DecompressionOptions {
    /** 每批次渲染的行数 */
    batchSize?: number;
    /** 分块大小 (bytes) */
    chunkSize?: number;
    /** 启用流式渲染 */
    streamingRender?: boolean;
}

export interface DecompressionResult {
    filename: string;
    originalSize: number;
    compressedSize: number;
    loadedFromCache: boolean;
    transferTime: number;
    decompressTime: number;
}

/**
 * 文件解压 Composable
 * 提供流式解压和渐进式渲染功能
 */
export function useFileDecompression(options: DecompressionOptions = {}) {
    const {
        batchSize = 5000,
        chunkSize = 256 * 1024,
        streamingRender = true
    } = options;

    const isLoading = ref(false);
    const loadedLines = ref(0);
    const allLines = ref<string[]>([]);
    const error = ref('');

    // 元数据
    const filename = ref('');
    const originalSize = ref(0);
    const compressedSize = ref(0);
    const loadedFromCache = ref(false);
    const transferTime = ref(0);
    const decompressTime = ref(0);

    /**
     * 解压文件
     * @param fileId 文件 ID
     * @param apiPath API 路径模板，{id} 会被替换
     */
    async function decompressFile(
        fileId: string,
        apiPath: string = '/api/v1/files/{id}/content'
    ): Promise<DecompressionResult> {
        isLoading.value = true;
        error.value = '';
        allLines.value = [];
        loadedLines.value = 0;

        const startTime = performance.now();
        let accumulatedText = '';

        try {
            // 尝试从缓存读取
            let cached = null;
            try {
                cached = await fileCacheService.get(fileId);
            } catch (e) { /* ignore */ }

            // 解压回调
            const decompressor = new Decompress((chunk) => {
                const text = new TextDecoder('utf-8', { fatal: false }).decode(chunk);
                accumulatedText += text;

                // 流式渲染：每累积足够行数就立即更新
                if (streamingRender) {
                    const newlineCount = (accumulatedText.match(/\n/g) || []).length;
                    if (newlineCount >= batchSize) {
                        const lines = accumulatedText.split('\n');
                        const completedLines = lines.slice(0, -1);
                        accumulatedText = lines[lines.length - 1] || '';

                        allLines.value.push(...completedLines);
                        loadedLines.value = allLines.value.length;

                        nextTick();
                    }
                }
            });

            if (cached) {
                console.log('[Decompress] Loading from cache...');
                loadedFromCache.value = true;
                filename.value = cached.filename;
                originalSize.value = cached.originalSize;
                compressedSize.value = cached.compressedSize;

                // 分块解压缓存数据
                const arrayBuffer = await cached.data.arrayBuffer();
                const uint8Array = new Uint8Array(arrayBuffer);

                for (let i = 0; i < uint8Array.length; i += chunkSize) {
                    const chunk = uint8Array.slice(i, Math.min(i + chunkSize, uint8Array.length));
                    const isLast = i + chunkSize >= uint8Array.length;
                    decompressor.push(chunk, isLast);
                    // 线程让步
                    await new Promise(resolve => setTimeout(resolve, 0));
                }

            } else {
                console.log('[Decompress] Fetching from network...');
                loadedFromCache.value = false;

                const transferStart = performance.now();
                const url = apiPath.replace('{id}', fileId);
                const response = await fetch(url);

                if (!response.ok) {
                    throw new Error(`Failed to load: ${response.statusText}`);
                }

                filename.value = response.headers.get('X-File-Name') || 'Unknown';
                originalSize.value = parseInt(response.headers.get('X-Original-Size') || '0');
                compressedSize.value = parseInt(response.headers.get('X-Compressed-Size') || '0');

                if (!response.body) {
                    throw new Error('Response body is null');
                }

                const reader = response.body.getReader();
                const chunks: Uint8Array[] = [];

                // 流式读取并实时解压
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                        decompressor.push(new Uint8Array(0), true);
                        break;
                    }

                    chunks.push(value);

                    try {
                        decompressor.push(value);
                    } catch (e) {
                        console.warn('[Decompress] Decompression warning:', e);
                    }

                    // 线程让步
                    await new Promise(resolve => setTimeout(resolve, 0));
                }

                transferTime.value = performance.now() - transferStart;

                // 写入缓存
                const compressedData = new Blob(chunks as BlobPart[], { type: 'application/zstd' });
                try {
                    await fileCacheService.set({
                        fileId,
                        filename: filename.value,
                        data: compressedData,
                        originalSize: originalSize.value,
                        compressedSize: compressedSize.value,
                        cachedAt: Date.now()
                    });
                    console.log('[Decompress] Saved to cache');
                } catch (e) {
                    console.warn('[Decompress] Failed to save to cache:', e);
                }
            }

            // 处理剩余未渲染的行
            if (accumulatedText) {
                const remainingLines = accumulatedText.split('\n');
                allLines.value.push(...remainingLines);
                loadedLines.value = allLines.value.length;
            }

            decompressTime.value = performance.now() - startTime - transferTime.value;

            const totalTime = performance.now() - startTime;
            console.log(`[Decompress] Loaded ${allLines.value.length} lines in ${Math.round(totalTime)}ms`);

            return {
                filename: filename.value,
                originalSize: originalSize.value,
                compressedSize: compressedSize.value,
                loadedFromCache: loadedFromCache.value,
                transferTime: transferTime.value,
                decompressTime: decompressTime.value
            };

        } catch (err: any) {
            error.value = err.message || 'Failed to decompress file';
            console.error('[Decompress] Error:', err);
            throw err;
        } finally {
            isLoading.value = false;
        }
    }

    /**
     * 重置状态
     */
    function reset() {
        allLines.value = [];
        loadedLines.value = 0;
        filename.value = '';
        originalSize.value = 0;
        compressedSize.value = 0;
        error.value = '';
    }

    return {
        // 状态
        isLoading,
        loadedLines,
        allLines,
        error,

        // 元数据
        filename,
        originalSize,
        compressedSize,
        loadedFromCache,
        transferTime,
        decompressTime,

        // 方法
        decompressFile,
        reset
    };
}
