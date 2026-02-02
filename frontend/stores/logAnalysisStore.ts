/**
 * 日志分析 Store
 * 管理日志文件状态，使用 IndexedDB 持久化存储
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { LogEntry } from '../utils/logParser';

export interface LogFile {
    id: string;
    name: string;
    size: number;
    entries: LogEntry[];
    labels: { label: string; count: number }[];
    addedAt: number;
    source: string;
}

// IndexedDB 配置
const DB_NAME = 'SensorHubLogAnalysis';
const DB_VERSION = 1;
const STORE_NAME = 'logFiles';

// IndexedDB 初始化
function openDB(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
            const db = (event.target as IDBOpenDBRequest).result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: 'id' });
            }
        };
    });
}

// IndexedDB 操作封装
async function dbGetAll(): Promise<LogFile[]> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const request = store.getAll();

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
}

async function dbPut(file: LogFile): Promise<void> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        const request = store.put(file);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();
    });
}

async function dbDelete(id: string): Promise<void> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        const request = store.delete(id);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();
    });
}

async function dbClear(): Promise<void> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        const request = store.clear();

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();
    });
}

export const useLogAnalysisStore = defineStore('logAnalysis', () => {
    // 状态
    const files = ref<LogFile[]>([]);
    const isLoading = ref(false);
    const selectedFileId = ref<string | null>(null);

    // 计算属性
    const selectedFile = computed(() =>
        files.value.find(f => f.id === selectedFileId.value) || null
    );

    const totalFiles = computed(() => files.value.length);

    // 初始化 - 从 IndexedDB 加载
    async function init() {
        isLoading.value = true;
        try {
            files.value = await dbGetAll();
            console.log(`[LogStore] Loaded ${files.value.length} files from IndexedDB`);
        } catch (err) {
            console.error('[LogStore] Failed to load from IndexedDB:', err);
        } finally {
            isLoading.value = false;
        }
    }

    // 添加文件（覆盖同名文件）
    async function addFile(file: LogFile) {
        // 查找同名文件
        const existingIndex = files.value.findIndex(f => f.name === file.name);

        if (existingIndex >= 0) {
            // 覆盖现有文件
            files.value[existingIndex] = file;
            console.log(`[LogStore] Replaced existing file: ${file.name}`);
        } else {
            // 添加新文件
            files.value.push(file);
            console.log(`[LogStore] Added new file: ${file.name}`);
        }

        // 持久化
        await dbPut(file);
    }

    // 批量添加文件
    async function addFiles(newFiles: LogFile[]) {
        for (const file of newFiles) {
            await addFile(file);
        }
    }

    // 删除单个文件
    async function removeFile(id: string) {
        const index = files.value.findIndex(f => f.id === id);
        if (index >= 0) {
            const fileName = files.value[index].name;
            files.value.splice(index, 1);
            await dbDelete(id);
            console.log(`[LogStore] Removed file: ${fileName}`);

            // 如果删除的是当前选中的文件，清除选中状态
            if (selectedFileId.value === id) {
                selectedFileId.value = null;
            }
        }
    }

    // 清空所有文件
    async function clearAll() {
        files.value = [];
        selectedFileId.value = null;
        await dbClear();
        console.log('[LogStore] Cleared all files');
    }

    // 选择文件
    function selectFile(id: string | null) {
        selectedFileId.value = id;
    }

    // 获取文件
    function getFile(id: string): LogFile | undefined {
        return files.value.find(f => f.id === id);
    }

    return {
        // 状态
        files,
        isLoading,
        selectedFileId,

        // 计算属性
        selectedFile,
        totalFiles,

        // 方法
        init,
        addFile,
        addFiles,
        removeFile,
        clearAll,
        selectFile,
        getFile,
    };
});
