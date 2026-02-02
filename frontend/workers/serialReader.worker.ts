/**
 * serialReader.worker.ts
 * 
 * 专用于读取串口数据的 Web Worker。
 * 将繁重的 I/O 操作从主线程分离，防止 UI 卡顿导致缓冲区溢出。
 */

// 消息类型定义
type WorkerMessage =
    | { type: 'START'; stream: ReadableStream<Uint8Array> }
    | { type: 'STOP' }
    | { type: 'PING' }; // 用于检测 Worker 活跃状态

let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
let keepReading = false;
let decoder: TextDecoder | null = null;

// 批量处理缓冲区
let pendingLines: string[] = [];
let lastFlushTime = 0;
const BATCH_INTERVAL = 16; // 16ms ~ 60fps
const MAX_BATCH_SIZE = 500; // 最多积累多少行发送一次

// 格式化时间戳 (Worker 中生成时间戳更准确)
function formatTimestamp(): string {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    const ms = now.getMilliseconds().toString().padStart(3, '0');
    return `[${hours}:${minutes}:${seconds}.${ms}]`;
}

// 刷新缓冲区函数
function flushBuffer() {
    if (pendingLines.length > 0) {
        self.postMessage({ type: 'DATA', lines: pendingLines });
        pendingLines = [];
        lastFlushTime = performance.now();
    }
}

// 主读取循环
async function readLoop(stream: ReadableStream<Uint8Array>) {
    // decoder 放在循环内或外都可以，放在内层每次重连重置状态可能更安全
    decoder = new TextDecoder('utf-8');
    let buffer = '';
    let consecutiveErrors = 0; // 连续错误计数，用于抑制日志

    try {
        while (keepReading) {
            try {
                // 每次循环重新获取 reader (支持错误恢复)
                reader = stream.getReader();

                while (keepReading) {
                    const { value, done } = await reader!.read(); // 注意: reader 是全局变量，这里直接用 reader.read() 也可以，但在 TS 中要小心 null

                    if (done) {
                        keepReading = false;
                        break;
                    }

                    if (value) {
                        // 成功读取，重置错误计数
                        consecutiveErrors = 0;

                        const chunk = decoder.decode(value, { stream: true });
                        buffer += chunk;

                        // 修复丢失回车的问题: 如果时间戳前面不是换行符，强制添加换行
                        // 注意：这里是对整个 buffer 做替换，可能会稍微影响性能，但在文本量不大时可以接受
                        // 为了避免切断尚未接收完整的时间戳，我们只处理 buffer 中间的部分，或者依赖正则的健壮性
                        // 正则: 非换行符 + 时间戳 -> 非换行符 + \n + 时间戳
                        buffer = buffer.replace(/([^\n])(\[\d{4}\/\d{1,2}\/\d{1,2}-\d{1,2}:\d{1,2}:\d{1,2}\])/g, '$1\n$2');

                        let newlineIndex;
                        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
                            const line = buffer.slice(0, newlineIndex).trim();
                            buffer = buffer.slice(newlineIndex + 1);

                            if (line) {
                                pendingLines.push(JSON.stringify({
                                    text: line,
                                    timestamp: formatTimestamp()
                                }));
                            }
                        }

                        // 检查刷新
                        const now = performance.now();
                        if (pendingLines.length >= MAX_BATCH_SIZE || (now - lastFlushTime >= BATCH_INTERVAL && pendingLines.length > 0)) {
                            flushBuffer();
                        }
                    }
                }
            } catch (error: any) {
                // 错误处理逻辑
                const isOverrun = error.name === 'BufferOverrunError';
                const isBreak = error.name === 'BreakError';
                const isFraming = error.name === 'FramingError';
                const isParity = error.name === 'ParityError';

                // 增加连续错误计数
                if (isOverrun || isBreak || isFraming || isParity) {
                    consecutiveErrors++;
                }

                const shouldLog = consecutiveErrors === 1 || consecutiveErrors % 20 === 0; // 防止日志刷屏，每20次(约1秒)打印一次

                if (isOverrun) {
                    if (shouldLog) console.warn(`[SerialWorker] Buffer overrun (${consecutiveErrors}), recovering...`);
                    // 继续循环 -> finally 释放锁 -> 下次循环重获 reader
                } else if (isBreak) {
                    if (shouldLog) console.warn(`[SerialWorker] Break signal (${consecutiveErrors}), recovering...`);
                    await new Promise(r => setTimeout(r, 50));
                } else if (isFraming) {
                    if (shouldLog) console.warn(`[SerialWorker] Framing error (${consecutiveErrors}), recovering...`);
                    await new Promise(r => setTimeout(r, 50));
                } else if (isParity) {
                    if (shouldLog) console.warn(`[SerialWorker] Parity error (${consecutiveErrors}), recovering...`);
                    await new Promise(r => setTimeout(r, 50));
                } else if (error.name === 'AbortError') {
                    console.log('[SerialWorker] Read aborted.');
                    // Abort 通常是主动取消，keepReading 应该已经被置为 false
                    break;
                } else if (error.name === 'NetworkError' ||
                    error.message?.includes('device has been lost') ||
                    error.message?.includes('disconnected') ||
                    error.message?.includes('The device has been lost')) {
                    // 设备拔出检测
                    console.error('[SerialWorker] Device disconnected');
                    self.postMessage({ type: 'DEVICE_DISCONNECTED', message: 'Device was unplugged' });
                    keepReading = false;
                    break;
                } else {
                    console.error('[SerialWorker] Read error:', error);
                    self.postMessage({ type: 'ERROR', message: error.message });
                    // 非致命错误尝试恢复，或者决定退出
                    await new Promise(r => setTimeout(r, 1000)); // 避免错误死循环
                }
            } finally {
                // 内层 finally: 确保每次 reader 退出（无论是 done, error, cancel）都释放锁
                if (reader) {
                    try {
                        reader.releaseLock();
                    } catch (e) {
                        // ignore
                    }
                    reader = null;
                }
            }

            // 如果还需要继续读取（错误恢复），加点延迟
            if (keepReading) {
                await new Promise(r => setTimeout(r, 50));
            }
        }
    } finally {
        // 外层 finally: 彻底退出时的清理
        console.log('[SerialWorker] Worker loop ended.');
        decoder = null;
        flushBuffer();
        self.postMessage({ type: 'STOP_ACK' });
    }
}

self.onmessage = async (e: MessageEvent<WorkerMessage>) => {
    const { type } = e.data;

    if (type === 'START') {
        const { stream } = e.data as { stream: ReadableStream<Uint8Array> };
        if (!stream) {
            self.postMessage({ type: 'ERROR', message: 'No stream provided' });
            return;
        }

        console.log('[SerialWorker] Starting read loop');
        keepReading = true;
        readLoop(stream);

    } else if (type === 'STOP') {
        console.log('[SerialWorker] Stopping...');
        keepReading = false;

        // 关键：立即取消读取，打破 await reader.read()
        if (reader) {
            try {
                await reader.cancel();
            } catch (e) {
                // ignore cancel errors
            }
        }
    } else if (type === 'PING') {
        // 响应主线程的活跃检测
        self.postMessage({ type: 'PONG' });
    }
};
