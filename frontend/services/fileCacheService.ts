/**
 * File cache service using IndexedDB
 * Stores compressed .zst files for quick access
 */

const DB_NAME = 'SensorHub';
const STORE_NAME = 'compressedFiles';
const DB_VERSION = 1;

interface CachedFile {
    fileId: string;
    filename: string;
    data: Blob;
    originalSize: number;
    compressedSize: number;
    cachedAt: number;
}

class FileCacheService {
    private db: IDBDatabase | null = null;

    async init(): Promise<void> {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve();
            };

            request.onupgradeneeded = (event) => {
                const db = (event.target as IDBOpenDBRequest).result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    const store = db.createObjectStore(STORE_NAME, { keyPath: 'fileId' });
                    store.createIndex('filename', 'filename', { unique: false });
                    store.createIndex('cachedAt', 'cachedAt', { unique: false });
                }
            };
        });
    }

    async get(fileId: string): Promise<CachedFile | null> {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.get(fileId);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result || null);
        });
    }

    async set(cachedFile: CachedFile): Promise<void> {
        if (!this.db) await this.init();

        // Ensure space before adding (clean up old files)
        await this.prune();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.put(cachedFile);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve();
        });
    }

    async delete(fileId: string): Promise<void> {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.delete(fileId);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve();
        });
    }

    async clear(): Promise<void> {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.clear();

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve();
        });
    }

    async getAll(): Promise<CachedFile[]> {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.getAll();

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result || []);
        });
    }

    async getCacheSize(): Promise<number> {
        const files = await this.getAll();
        return files.reduce((total, file) => total + file.compressedSize, 0);
    }

    /**
     * Prune cache to stay within limits
     * Policy:
     * 1. Remove files older than 7 days
     * 2. If total size > 1GB, remove oldest files until under limit
     */
    async prune(): Promise<void> {
        const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000; // 7 days
        const MAX_SIZE_BYTES = 1024 * 1024 * 1024; // 1 GB

        const files = await this.getAll();
        const now = Date.now();
        let currentSize = 0;
        const filesKeep: CachedFile[] = [];

        // 1. Filter by Age
        for (const file of files) {
            if (now - file.cachedAt > MAX_AGE_MS) {
                console.log(`[FileCache] Creating space: Removing expired file ${file.filename}`);
                await this.delete(file.fileId);
            } else {
                filesKeep.push(file);
                currentSize += file.compressedSize;
            }
        }

        // 2. Filter by Size (LRU - strictly relies on cachedAt)
        // Sort by cachedAt ascending (oldest first)
        filesKeep.sort((a, b) => a.cachedAt - b.cachedAt);

        while (currentSize > MAX_SIZE_BYTES && filesKeep.length > 0) {
            const fileToRemove = filesKeep.shift();
            if (fileToRemove) {
                console.log(`[FileCache] Creating space: Removing old file ${fileToRemove.filename} (Size: ${(fileToRemove.compressedSize / 1024 / 1024).toFixed(2)} MB)`);
                await this.delete(fileToRemove.fileId);
                currentSize -= fileToRemove.compressedSize;
            }
        }
    }
}

export const fileCacheService = new FileCacheService();
export type { CachedFile };
