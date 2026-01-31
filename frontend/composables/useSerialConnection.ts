/**
 * 串口连接 Composable
 * 使用 Web Serial API 管理串口连接和数据通信
 */
import { ref, computed, shallowRef } from 'vue';

// 默认波特率选项列表
const DEFAULT_BAUD_RATES = [
    9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600, 1500000, 2000000
];

// 串口配置接口
export interface SerialConfig {
    baudRate: number;
    dataBits: 7 | 8;
    stopBits: 1 | 2;
    parity: 'none' | 'even' | 'odd';
    flowControl: 'none' | 'hardware';
    encoding: 'utf-8' | 'ascii' | 'hex';
}

// 连接状态
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export function useSerialConnection() {
    // 状态
    // 使用 any 类型以兼容 Web Serial API (需要在 tsconfig 中添加 dom 类型)
    const port = shallowRef<any>(null);
    const reader = shallowRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
    const writer = shallowRef<WritableStreamDefaultWriter<Uint8Array> | null>(null);
    const status = ref<ConnectionStatus>('disconnected');
    const errorMessage = ref('');
    const isSupported = ref(checkSupport());

    // 配置
    const config = ref<SerialConfig>({
        baudRate: 115200,
        dataBits: 8,
        stopBits: 1,
        parity: 'none',
        flowControl: 'none',
        encoding: 'utf-8',
    });

    // 自定义波特率列表
    const customBaudRates = ref<number[]>([]);
    const allBaudRates = computed(() => {
        const all = [...DEFAULT_BAUD_RATES, ...customBaudRates.value];
        return [...new Set(all)].sort((a, b) => a - b);
    });

    // 数据回调
    let onDataCallback: ((data: Uint8Array) => void) | null = null;

    // 检查浏览器支持
    function checkSupport(): boolean {
        return 'serial' in navigator;
    }

    // 添加自定义波特率
    function addCustomBaudRate(rate: number) {
        if (rate > 0 && !allBaudRates.value.includes(rate)) {
            customBaudRates.value.push(rate);
        }
    }

    // 请求串口权限并连接
    async function connect(): Promise<boolean> {
        if (!isSupported.value) {
            errorMessage.value = 'Web Serial API is not supported in this browser. Please use Chrome or Edge.';
            status.value = 'error';
            return false;
        }

        try {
            status.value = 'connecting';
            errorMessage.value = '';

            // 请求用户选择串口
            const selectedPort = await (navigator as any).serial.requestPort();
            port.value = selectedPort;

            // 打开串口 - 设置较大的缓冲区以避免高速传输时溢出
            await selectedPort.open({
                baudRate: config.value.baudRate,
                dataBits: config.value.dataBits,
                stopBits: config.value.stopBits,
                parity: config.value.parity,
                flowControl: config.value.flowControl,
                bufferSize: 1024 * 1024, // 1MB buffer to handle high-speed data
            });

            // 设置读取器
            if (selectedPort.readable) {
                startReading(selectedPort);
            }

            // 设置写入器
            if (selectedPort.writable) {
                writer.value = selectedPort.writable.getWriter();
            }

            status.value = 'connected';
            return true;
        } catch (error: any) {
            console.error('Serial connection error:', error);
            if (error.name === 'NotFoundError') {
                errorMessage.value = 'No serial port selected.';
            } else {
                errorMessage.value = error.message || 'Failed to connect to serial port.';
            }
            status.value = 'error';
            return false;
        }
    }

    // 断开连接
    async function disconnect(): Promise<void> {
        try {
            if (reader.value) {
                try {
                    await reader.value.cancel();
                } catch (e) {
                    // 忽略 cancel 错误
                }
                try {
                    reader.value.releaseLock();
                } catch (e) {
                    // 忽略 releaseLock 错误
                }
                reader.value = null;
            }

            if (writer.value) {
                try {
                    await writer.value.close();
                } catch (e) {
                    // 忽略 close 错误
                }
                try {
                    writer.value.releaseLock();
                } catch (e) {
                    // 忽略 releaseLock 错误
                }
                writer.value = null;
            }

            if (port.value) {
                await port.value.close();
                port.value = null;
            }

            status.value = 'disconnected';
            errorMessage.value = '';
        } catch (error: any) {
            console.error('Disconnect error:', error);
            errorMessage.value = error.message || 'Error during disconnect.';
        }
    }

    // 开始读取数据 - 带有错误恢复机制
    async function startReading(serialPort: any): Promise<void> {
        let keepReading = true;

        while (keepReading && serialPort.readable) {
            try {
                reader.value = serialPort.readable.getReader();

                while (true) {
                    const { value, done } = await reader.value.read();
                    if (done) {
                        console.log('Serial reader done');
                        keepReading = false;
                        break;
                    }
                    if (value && onDataCallback) {
                        onDataCallback(value);
                    }
                }
            } catch (error: any) {
                // 处理 BufferOverrunError - 释放读取器并重新获取
                if (error.name === 'BufferOverrunError') {
                    console.warn('Buffer overrun detected, recovering...');
                    try {
                        if (reader.value) {
                            reader.value.releaseLock();
                            reader.value = null;
                        }
                    } catch (e) {
                        // 忽略释放错误
                    }
                    // 短暂延迟后继续读取
                    await new Promise(resolve => setTimeout(resolve, 10));
                    continue;
                }

                // 其他错误
                if (error.name !== 'AbortError') {
                    console.error('Read error:', error);
                    errorMessage.value = error.message || 'Error reading from serial port.';
                    status.value = 'error';
                }
                keepReading = false;
            } finally {
                // 确保释放读取器锁
                if (reader.value) {
                    try {
                        reader.value.releaseLock();
                    } catch (e) {
                        // 忽略
                    }
                    reader.value = null;
                }
            }
        }
    }

    // 发送数据
    async function send(data: string): Promise<boolean> {
        if (!writer.value || status.value !== 'connected') {
            return false;
        }

        try {
            let bytes: Uint8Array;
            if (config.value.encoding === 'hex') {
                // 将十六进制字符串转换为字节
                const hex = data.replace(/\s/g, '');
                bytes = new Uint8Array(hex.match(/.{1,2}/g)?.map(byte => parseInt(byte, 16)) || []);
            } else {
                // UTF-8 或 ASCII 编码
                const encoder = new TextEncoder();
                bytes = encoder.encode(data);
            }

            await writer.value.write(bytes);
            return true;
        } catch (error: any) {
            console.error('Send error:', error);
            errorMessage.value = error.message || 'Error sending data.';
            return false;
        }
    }

    // 设置数据回调
    function onData(callback: (data: Uint8Array) => void): void {
        onDataCallback = callback;
    }

    return {
        // 状态
        status,
        errorMessage,
        isSupported,
        config,

        // 波特率
        allBaudRates,
        addCustomBaudRate,

        // 方法
        connect,
        disconnect,
        send,
        onData,
    };
}
