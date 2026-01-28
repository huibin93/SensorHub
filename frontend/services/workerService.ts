import { v4 as uuidv4 } from 'uuid';
import ZstdWorker from '../workers/zstd.worker.js?worker';

class WorkerService {
    private worker: Worker | null = null;
    private resolvers = new Map<string, { resolve: (value: any) => void, reject: (reason?: any) => void }>();

    constructor() {
        this.initWorker();
    }

    private initWorker() {
        if (this.worker) return;

        this.worker = new ZstdWorker();
        this.worker.onmessage = (e) => {
            const { id, status, message, ...data } = e.data;

            const resolver = this.resolvers.get(id);
            if (!resolver) return;

            if (status === 'error') {
                resolver.reject(new Error(message));
            } else {
                resolver.resolve(data);
            }
            this.resolvers.delete(id);
        };

        console.log('[WorkerService] Shared ZstdWorker initialized.');
    }

    public async call(action: string, payload: any): Promise<any> {
        if (!this.worker) this.initWorker();

        return new Promise((resolve, reject) => {
            const id = uuidv4();
            this.resolvers.set(id, { resolve, reject });
            this.worker!.postMessage({ id, action, ...payload });
        });
    }

    public terminate() {
        if (this.worker) {
            this.worker.terminate();
            this.worker = null;
            this.resolvers.clear();
            console.log('[WorkerService] Shared ZstdWorker terminated.');
        }
    }
}

export const workerService = new WorkerService();
