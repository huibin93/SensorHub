<script setup lang="ts">
/**
 * 串口工具页面 - 简化版
 * 使用 Web Serial API 进行串口通信调试
 */
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { Usb, Trash2, Download, Send, AlertCircle, X, Settings, Plus, Hash, Clock, ArrowUp, ArrowDown, Filter } from 'lucide-vue-next';

// 串口状态
// 串口状态
const port = ref<any>(null);
const writer = ref<WritableStreamDefaultWriter<Uint8Array> | null>(null);
// Reader 移交给 Worker，主线程不再持有
const serialWorker = ref<Worker | null>(null);
const status = ref<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
const errorMessage = ref('');
const isSecureContext = ref(window.isSecureContext);
const locationOrigin = window.location ? window.location.origin : '';
const isSupported = ref(checkSupport());

// 初始化 Worker
import SerialWorker from '../workers/serialReader.worker?worker';

function initWorker() {
  if (serialWorker.value) return;
  
  // 创建 Worker
  serialWorker.value = new SerialWorker();
  
  serialWorker.value.onmessage = (e) => {
    const { type, lines: newLines, message } = e.data;
    
    if (type === 'DATA' && newLines && newLines.length > 0) {
       // Worker 传回的是 JSON 字符串数组，需要解析
       const parsedLines = newLines.map((l: string) => JSON.parse(l));
       
       // 批量添加到 UI
       lines.value.push(...parsedLines);
       
       // 内存保护
       if (lines.value.length > 20000) {
         lines.value = lines.value.slice(-10000);
       }
       
       // 自动滚动 (使用 setTimeout 0 避免阻塞)
       if (autoScroll.value) {
          setTimeout(() => {
            if (terminalRef.value) {
               terminalRef.value.scrollTop = terminalRef.value.scrollHeight;
            }
          }, 0);
       }
    } else if (type === 'ERROR') {
       console.error('[Worker] Error:', message);
       if (status.value === 'connected') {
          errorMessage.value = message;
          status.value = 'error';
       }
    } else if (type === 'STOP_ACK') {
       console.log('[Worker] Stopped acknowledged');
    } else if (type === 'DEVICE_DISCONNECTED') {
       // Worker 检测到设备断开
       console.warn('[Main] Device disconnected detected by Worker:', message);
       forceCleanup();
       showToastMessage('Device disconnected: ' + message);
    }
  };
}

// 在组件挂载时初始化 Workder
initWorker();

// 设备拔出事件监听
function setupDisconnectListener() {
  if ('serial' in navigator) {
    (navigator as any).serial.addEventListener('disconnect', handlePortDisconnect);
  }
}

function handlePortDisconnect(event: any) {
  const disconnectedPort = event.target;
  if (disconnectedPort === port.value) {
    console.warn('[Serial] Device disconnected unexpectedly');
    forceCleanup();
    showToastMessage('Device unplugged unexpectedly');
  }
}

function removeDisconnectListener() {
  if ('serial' in navigator) {
    (navigator as any).serial.removeEventListener('disconnect', handlePortDisconnect);
  }
}

// 强制清理函数 (用于意外断开)
async function forceCleanup() {
  // 通知 Worker 停止
  if (serialWorker.value) {
    serialWorker.value.postMessage({ type: 'STOP' });
    serialWorker.value.terminate();
    serialWorker.value = null;
    initWorker();
  }
  
  // 清理写入器
  if (writer.value) {
    try { writer.value.releaseLock(); } catch (e) {}
    writer.value = null;
  }
  
  // 清理端口引用
  port.value = null;
  status.value = 'disconnected';
  errorMessage.value = '';
  isDisconnecting.value = false;
}

// 生命周期钩子
onMounted(() => {
  setupDisconnectListener();
});

onUnmounted(() => {
  removeDisconnectListener();
  if (serialWorker.value) {
    serialWorker.value.terminate();
    serialWorker.value = null;
  }
});

// 配置
const baudRate = ref(115200);

// 添加断开连接标志，用于协调 startReading 退出
const isDisconnecting = ref(false);
const baudRateOptions = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600];

// 数据 - 每行包含文本和时间戳
interface LineData {
  text: string;
  timestamp: string;
}
const lines = ref<LineData[]>([]);
const sendInput = ref('');
const toastMessage = ref('');
const showToast = ref(false);

// UI 状态
const showSettings = ref(false);
const showBaudRateDialog = ref(false);
const customBaudRateInput = ref('');
const showLineNumber = ref(true);
const showTimestamp = ref(true);
const autoScroll = ref(true);

// 过滤和高亮
const highlightInput = ref('');
const showFilterInput = ref('');
const hideFilterInput = ref('');
const useRegex = ref(false);
const highlightKeywords = ref<string[]>([]);
const showFilter = ref('');
const hideFilter = ref('');

// 串口配置参数
const dataBits = ref<7 | 8>(8);
const stopBits = ref<1 | 2>(1);
const parity = ref<'none' | 'even' | 'odd'>('none');
const dtrEnabled = ref(false); // DTR 流控，默认关闭
const rtsEnabled = ref(false); // RTS 流控，默认关闭
const encoding = ref<'utf-8' | 'ascii' | 'hex'>('utf-8');

// 终端容器
const terminalRef = ref<HTMLElement | null>(null);

// 格式化时间戳
function formatTimestamp(): string {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  const seconds = now.getSeconds().toString().padStart(2, '0');
  const ms = now.getMilliseconds().toString().padStart(3, '0');
  return `[${hours}:${minutes}:${seconds}.${ms}]`;
}

// 滚动控制
function scrollToTop() {
  if (terminalRef.value) {
    terminalRef.value.scrollTop = 0;
    autoScroll.value = false;
  }
}

function scrollToBottom() {
  if (terminalRef.value) {
    terminalRef.value.scrollTop = terminalRef.value.scrollHeight;
    autoScroll.value = true;
  }
}

// 监听悬停模式
function handleWheel(event: WheelEvent) {
  if (event.deltaY < 0 && autoScroll.value) {
    autoScroll.value = false;
  }
}

// 添加自定义波特率
function addCustomBaudRate() {
  const rate = parseInt(customBaudRateInput.value);
  if (rate > 0 && !baudRateOptions.includes(rate)) {
    baudRateOptions.push(rate);
    baudRateOptions.sort((a, b) => a - b);
    baudRate.value = rate;
    customBaudRateInput.value = '';
    showBaudRateDialog.value = false;
  }
}

// 添加高亮关键字
function addHighlight() {
  if (highlightInput.value.trim() && !highlightKeywords.value.includes(highlightInput.value.trim())) {
    highlightKeywords.value.push(highlightInput.value.trim());
    highlightInput.value = '';
  }
}

// 移除高亮关键字
function removeHighlight(keyword: string) {
  const index = highlightKeywords.value.indexOf(keyword);
  if (index > -1) {
    highlightKeywords.value.splice(index, 1);
  }
}

// 应用过滤器
function applyFilters() {
  showFilter.value = showFilterInput.value;
  hideFilter.value = hideFilterInput.value;
}

// 清除过滤器
function clearFilters() {
  showFilter.value = '';
  hideFilter.value = '';
  showFilterInput.value = '';
  hideFilterInput.value = '';
}

// 检查行是否应该显示
function shouldShowLine(text: string): boolean {
  if (!showFilter.value && !hideFilter.value) return true;
  
  const matchText = (pattern: string, text: string): boolean => {
    if (useRegex.value) {
      try {
        return new RegExp(pattern).test(text);
      } catch {
        return text.includes(pattern);
      }
    }
    return text.includes(pattern);
  };

  // Show filter
  if (showFilter.value) {
    const patterns = showFilter.value.split('|').map(p => p.trim()).filter(Boolean);
    if (!patterns.some(p => matchText(p, text))) {
      return false;
    }
  }

  // Hide filter
  if (hideFilter.value) {
    const patterns = hideFilter.value.split('|').map(p => p.trim()).filter(Boolean);
    if (patterns.some(p => matchText(p, text))) {
      return false;
    }
  }

  return true;
}

// 高亮文本
function highlightText(text: string): string {
  if (highlightKeywords.value.length === 0) return text;
  
  let result = text;
  const colors = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899'];
  
  highlightKeywords.value.forEach((keyword, index) => {
    const color = colors[index % colors.length];
    const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    result = result.replace(
      new RegExp(escaped, 'gi'),
      match => `<span style="background-color: ${color}30; color: ${color}; font-weight: 600;">${match}</span>`
    );
  });
  
  return result;
}

// 检查浏览器支持
function checkSupport(): boolean {
  return 'serial' in navigator;
}

// 连接串口
async function connect() {
  if (!isSupported.value) {
    showToastMessage('Web Serial API not supported. Use Chrome or Edge.');
    return;
  }

  try {
    status.value = 'connecting';
    errorMessage.value = '';

    // 请求串口
    const selectedPort = await (navigator as any).serial.requestPort();
    port.value = selectedPort;

    // 打开串口
    await selectedPort.open({
      baudRate: baudRate.value,
      dataBits: dataBits.value,
      stopBits: stopBits.value,
      parity: parity.value,
      flowControl: (dtrEnabled.value || rtsEnabled.value) ? 'hardware' : 'none',
      bufferSize: 1024 * 1024, // 1MB buffer
    });

    // 设置读取器和写入器
    if (selectedPort.readable) {
       // 关键步骤：将 readableStream 转移给 Worker
       // 主线程从此失去对 readable 的控制权
       if (!serialWorker.value) initWorker();
       
       serialWorker.value?.postMessage({
         type: 'START',
         stream: selectedPort.readable
       }, [selectedPort.readable]);
    }

    if (selectedPort.writable) {
      writer.value = selectedPort.writable.getWriter();
    }

    status.value = 'connected';
    showToastMessage('Serial port connected');
  } catch (error: any) {
    console.error('Connection error:', error);
    errorMessage.value = error.message || 'Failed to connect';
    status.value = 'error';
    showToastMessage('Connection failed: ' + errorMessage.value);
  }
}

// 断开连接 (Worker 模式)
async function disconnect() {
  if (status.value === 'disconnected' || isDisconnecting.value) return;
  
  isDisconnecting.value = true;
  console.log('Disconnecting (Worker mode)...');

  try {
    // 1. 先停止 Worker 读取 (释放 readable 流的锁)
    if (serialWorker.value) {
       // 发送 STOP 信号
       serialWorker.value.postMessage({ type: 'STOP' });
       
       // 等待 ACK 或超时 (3秒)
       await new Promise<void>((resolve) => {
         const timeout = setTimeout(() => {
            console.warn('Worker stop timeout, forcing close');
            resolve();
         }, 3000);
         
         const ackHandler = (e: MessageEvent) => {
           if (e.data.type === 'STOP_ACK') {
             clearTimeout(timeout);
             serialWorker.value?.removeEventListener('message', ackHandler);
             console.log('Worker ACK received, stream lock released');
             resolve();
           }
         };
         serialWorker.value?.addEventListener('message', ackHandler);
       });
       
       // 等待一小段时间确保流完全释放
       await new Promise(r => setTimeout(r, 100));
       
       // 终止并重建 Worker
       serialWorker.value.terminate();
       serialWorker.value = null;
    }

    // 2. Writer 清理 (先释放锁，再 close)
    if (writer.value) {
      try {
        writer.value.releaseLock();
      } catch (e) {
        console.warn('Writer releaseLock failed:', e);
      }
      writer.value = null;
    }

    // 3. 关闭端口 (流已解锁后才能关闭)
    if (port.value) {
      try {
        await port.value.close();
        console.log('Port closed successfully');
      } catch (e: any) {
        // 即使关闭失败也要清理引用
        console.warn('Port close failed:', e.message);
      }
      port.value = null;
    }

    // 4. 重建 Worker 以备下次连接
    initWorker();

    status.value = 'disconnected';
    errorMessage.value = '';
    showToastMessage('Disconnected');
  } catch (error: any) {
    console.error('Disconnect error:', error);
    errorMessage.value = error.message || 'Error during disconnect';
    // 即使出错也要重置状态
    status.value = 'disconnected';
    port.value = null;
    writer.value = null;
  } finally {
    isDisconnecting.value = false;
  }
}



// 发送数据
async function sendData() {
  if (!sendInput.value.trim() || !writer.value) return;

  try {
    const encoder = new TextEncoder();
    const data = encoder.encode(sendInput.value + '\r\n');
    await writer.value.write(data);
    sendInput.value = '';
  } catch (error: any) {
    console.error('Send error:', error);
    showToastMessage('Failed to send data');
  }
}

// 清空数据
function clearData() {
  lines.value = [];
  showToastMessage('Data cleared');
}

// 导出数据
function exportData() {
  const text = lines.value.map(line => `${line.timestamp} ${line.text}`).join('\n');
  const blob = new Blob([text], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `serial_log_${new Date().toISOString().replace(/[:.]/g, '-')}.txt`;
  a.click();
  URL.revokeObjectURL(url);
  showToastMessage('Data exported');
}

// Toast消息
function showToastMessage(message: string) {
  toastMessage.value = message;
  showToast.value = true;
  setTimeout(() => {
    showToast.value = false;
  }, 3000);
}

// 切换连接
async function toggleConnection() {
  if (status.value === 'connected') {
    await disconnect();
  } else {
    await connect();
  }
}

// 清理
onUnmounted(() => {
  disconnect();
});

// 过滤后的行
const filteredLines = computed(() => {
  return lines.value.filter(line => shouldShowLine(line.text));
});

// 计算统计
const stats = computed(() => {
  const totalChars = lines.value.map(l => l.text).join('').length;
  const sizeMB = (totalChars / 1024 / 1024).toFixed(2);
  return {
    lines: lines.value.length,
    size: sizeMB
  };
});
</script>

<template>
  <div class="flex flex-col h-full bg-slate-50">
    <!-- 不支持浏览器提示 -->
    <div v-if="!isSupported" class="flex-1 flex items-center justify-center p-6">
      <div class="text-center p-8 bg-white rounded-xl shadow-sm border border-slate-200 max-w-lg">
        <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-red-50 flex items-center justify-center">
          <AlertCircle :size="32" class="text-red-500" />
        </div>
        <h2 class="text-xl font-bold text-slate-800 mb-2">Web Serial Not Available</h2>
        
        <div v-if="!isSecureContext" class="text-left mt-4 text-sm text-slate-600 bg-slate-50 p-4 rounded-lg border border-slate-100">
           <p class="font-bold text-red-600 mb-2">⚠️ Insecure Context Detected</p>
           <p class="mb-2">Web Serial API requires a Secure Context (HTTPS or localhost). You are connecting via HTTP.</p>
           <p class="mb-2 font-medium">To enable this for development:</p>
           <ol class="list-decimal list-inside space-y-1 text-xs font-mono bg-white p-3 rounded border border-slate-200">
             <li>Go to <span class="bg-yellow-100 px-1 text-slate-800 rounded select-all">chrome://flags/#unsafely-treat-insecure-origin-as-secure</span></li>
             <li>Enable the flag</li>
             <li>Add this URL to the text box: <br><span class="text-blue-600 select-all">{{ locationOrigin }}</span></li>
             <li>Relaunch Chrome</li>
           </ol>
        </div>

        <p v-else class="text-slate-500 text-sm mt-4">
          Please use <span class="font-semibold text-blue-600">Chrome</span> or 
          <span class="font-semibold text-blue-600">Edge</span> (Version 89+).
        </p>
      </div>
    </div>

    <!-- 主界面 -->
    <template v-else>
      <!-- Header -->
      <div class="px-6 py-4 border-b border-slate-200 bg-white">
        <div class="flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-violet-50 flex items-center justify-center text-violet-600">
            <Usb :size="20" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-800">Serial Tool</h1>
            <p class="text-xs text-slate-500">Serial port debugging</p>
          </div>

          <div class="ml-auto flex items-center gap-3">
            <!-- 状态 -->
            <div class="flex items-center gap-2">
              <div 
                class="w-2 h-2 rounded-full"
                :class="{
                  'bg-green-500': status === 'connected',
                  'bg-yellow-500 animate-pulse': status === 'connecting',
                  'bg-slate-300': status === 'disconnected',
                  'bg-red-500': status === 'error',
                }"
              ></div>
              <span class="text-xs font-semibold text-slate-600 capitalize">{{ status }}</span>
            </div>

            <!-- 统计 -->
            <div class="text-xs text-slate-600">
              RX: {{ stats.lines }} lines | {{ stats.size }} MB
            </div>
          </div>
        </div>

        <!-- 工具栏 -->
        <div class="mt-3 flex gap-2 items-center">
          <!-- 波特率 -->
          <select 
            v-model="baudRate"
            :disabled="status === 'connected'"
            class="px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:opacity-50"
          >
            <option v-for="rate in baudRateOptions" :key="rate" :value="rate">{{ rate }}</option>
          </select>

          <!-- 添加波特率 -->
          <button 
            @click="showBaudRateDialog = true"
            :disabled="status === 'connected'"
            class="px-2 py-2 bg-slate-50 border border-slate-200 rounded-lg hover:bg-slate-100 disabled:opacity-50 transition-colors"
            title="Add custom baud rate"
          >
            <Plus :size="16" class="text-slate-600" />
          </button>

          <!-- 设置按钮 -->
          <button 
            @click="showSettings = !showSettings"
            class="px-2 py-2 bg-slate-50 border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors"
            :class="{ 'bg-violet-50 border-violet-200': showSettings }"
            title="Settings"
          >
            <Settings :size="16" class="text-slate-600" />
          </button>

          <div class="w-px h-6 bg-slate-200"></div>

          <!-- 连接按钮 -->
          <button 
            @click="toggleConnection"
            class="px-4 py-2 text-sm font-bold rounded-lg transition-all"
            :class="status === 'connected' 
              ? 'bg-red-500 hover:bg-red-600 text-white' 
              : 'bg-violet-600 hover:bg-violet-700 text-white'"
          >
            {{ status === 'connected' ? 'Disconnect' : 'Connect' }}
          </button>

          <div class="w-px h-6 bg-slate-200"></div>

          <!-- 清空 -->
          <button 
            @click="clearData"
            class="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-slate-600 bg-slate-50 border border-slate-200 rounded-lg hover:bg-slate-100"
          >
            <Trash2 :size="14" />
            Clear
          </button>

          <!-- 导出 -->
          <button 
            @click="exportData"
            :disabled="lines.length === 0"
            class="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-slate-600 bg-slate-50 border border-slate-200 rounded-lg hover:bg-slate-100 disabled:opacity-50"
          >
            <Download :size="14" />
            Export
          </button>

          <div class="flex-1"></div>

          <!-- 显示选项 -->
          <label class="flex items-center gap-2 text-xs font-medium text-slate-600 cursor-pointer">
            <input type="checkbox" v-model="showLineNumber" class="rounded border-slate-300 text-violet-600" />
            <Hash :size="12" />
            Line#
          </label>
          <label class="flex items-center gap-2 text-xs font-medium text-slate-600 cursor-pointer">
            <input type="checkbox" v-model="showTimestamp" class="rounded border-slate-300 text-violet-600" />
            <Clock :size="12" />
            Timestamp
          </label>

          <div class="w-px h-6 bg-slate-200"></div>

          <!-- 滚动控制 -->
          <button 
            @click="scrollToTop"
            class="px-2 py-2 bg-slate-50 border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors"
            title="Scroll to top"
          >
            <ArrowUp :size="16" class="text-slate-600" />
          </button>
          <button 
            @click="scrollToBottom"
            class="px-2 py-2 bg-slate-50 border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors"
            :class="{ 'bg-violet-50 border-violet-300': autoScroll }"
            title="Scroll to bottom (auto-scroll)"
          >
            <ArrowDown :size="16" class="text-slate-600" />
          </button>

          <!-- 滚动模式指示 -->
          <div 
            class="px-2 py-1 text-[10px] font-bold uppercase tracking-wide rounded"
            :class="autoScroll 
              ? 'bg-green-50 text-green-700' 
              : 'bg-yellow-50 text-yellow-700'"
          >
            {{ autoScroll ? 'Auto' : 'Paused' }}
          </div>
        </div>

        <!-- 设置面板 -->
        <div v-if="showSettings" class="mt-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
          <div class="grid grid-cols-6 gap-4">
            <!-- 数据位 -->
            <div>
              <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Data Bits</label>
              <select 
                v-model="dataBits"
                :disabled="status === 'connected'"
                class="mt-1 w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-violet-500 disabled:opacity-50"
              >
                <option :value="7">7</option>
                <option :value="8">8</option>
              </select>
            </div>

            <!-- 校验位 -->
            <div>
              <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Parity</label>
              <select 
                v-model="parity"
                :disabled="status === 'connected'"
                class="mt-1 w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-violet-500 disabled:opacity-50"
              >
                <option value="none">None</option>
                <option value="even">Even</option>
                <option value="odd">Odd</option>
              </select>
            </div>

            <!-- 停止位 -->
            <div>
              <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Stop Bits</label>
              <select 
                v-model="stopBits"
                :disabled="status === 'connected'"
                class="mt-1 w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-violet-500 disabled:opacity-50"
              >
                <option :value="1">1</option>
                <option :value="2">2</option>
              </select>
            </div>

            <!-- DTR 流控 -->
            <div>
              <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">DTR</label>
              <button
                @click="dtrEnabled = !dtrEnabled"
                :disabled="status === 'connected'"
                class="mt-1 w-full px-3 py-2 text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
                :class="dtrEnabled 
                  ? 'bg-green-100 text-green-700 border-2 border-green-300' 
                  : 'bg-slate-100 text-slate-500 border-2 border-slate-200'"
              >
                {{ dtrEnabled ? 'ON' : 'OFF' }}
              </button>
            </div>

            <!-- RTS 流控 -->
            <div>
              <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">RTS</label>
              <button
                @click="rtsEnabled = !rtsEnabled"
                :disabled="status === 'connected'"
                class="mt-1 w-full px-3 py-2 text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
                :class="rtsEnabled 
                  ? 'bg-green-100 text-green-700 border-2 border-green-300' 
                  : 'bg-slate-100 text-slate-500 border-2 border-slate-200'"
              >
                {{ rtsEnabled ? 'ON' : 'OFF' }}
              </button>
            </div>

            <!-- 编码 -->
            <div>
              <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Encoding</label>
              <select 
                v-model="encoding"
                class="mt-1 w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-violet-500"
              >
                <option value="utf-8">UTF-8</option>
                <option value="ascii">ASCII</option>
                <option value="hex">HEX</option>
              </select>
            </div>
          </div>
        </div>

        <!-- 过滤和高亮面板 -->
        <div class="mt-3 flex gap-3 items-center flex-wrap">
          <!-- 高亮输入 -->
          <div class="flex items-center gap-2">
            <input 
              v-model="highlightInput"
              @keyup.enter="addHighlight"
              type="text"
              placeholder="Highlight keyword..."
              class="w-40 px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-violet-500"
            />
            <button 
              @click="addHighlight"
              class="px-3 py-2 text-xs font-semibold text-violet-600 bg-violet-50 border border-violet-200 rounded-lg hover:bg-violet-100 transition-colors"
            >
              Add
            </button>
          </div>

          <!-- 高亮标签 -->
          <div v-if="highlightKeywords.length > 0" class="flex items-center gap-1 flex-wrap">
            <div 
              v-for="(keyword, index) in highlightKeywords"
              :key="index"
              class="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-lg bg-violet-50 text-violet-700 border border-violet-200"
            >
              {{ keyword }}
              <button @click="removeHighlight(keyword)" class="hover:opacity-70">
                <X :size="12" />
              </button>
            </div>
          </div>

          <div class="w-px h-6 bg-slate-200"></div>

          <!-- 过滤器 -->
          <div class="flex items-center gap-2">
            <input 
              v-model="showFilterInput"
              @keyup.enter="applyFilters"
              type="text"
              placeholder="Show: key1|key2"
              class="w-32 px-2 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-green-500"
            />
            <input 
              v-model="hideFilterInput"
              @keyup.enter="applyFilters"
              type="text"
              placeholder="Hide: key1|key2"
              class="w-32 px-2 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-red-500"
            />
            <label class="flex items-center gap-1 text-xs text-slate-500 cursor-pointer">
              <input type="checkbox" v-model="useRegex" class="rounded border-slate-300 text-violet-600" />
              Regex
            </label>
            <button 
              @click="applyFilters"
              class="px-3 py-2 text-xs font-semibold text-slate-600 bg-slate-100 border border-slate-200 rounded-lg hover:bg-slate-200 transition-colors"
            >
              Apply
            </button>
            <button 
              v-if="showFilter || hideFilter"
              @click="clearFilters"
              class="px-3 py-2 text-xs font-semibold text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
            >
              Clear
            </button>
          </div>

          <!-- 过滤状态 -->
          <div 
            v-if="showFilter || hideFilter"
            class="px-2 py-1 text-[10px] font-bold uppercase tracking-wide rounded bg-blue-50 text-blue-700"
          >
            Filter Active
          </div>
        </div>
      </div>

      <!-- 数据显示区域 -->
      <div class="flex-1 overflow-hidden px-6 my-4">
        <div class="h-full flex flex-col bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <!-- 内容区域 -->
          <div 
            ref="terminalRef"
            @wheel="handleWheel"
            class="flex-1 overflow-auto font-mono text-sm text-slate-800 leading-5 p-4"
          >
            <div v-if="lines.length === 0" class="flex items-center justify-center h-full text-slate-400">
              <div class="text-center">
                <Usb :size="48" class="mx-auto mb-4 opacity-30" />
                <p class="text-sm">No data received</p>
                <p class="text-xs mt-1 opacity-70">Connect to a serial port to start</p>
              </div>
            </div>
            <div v-else>
              <div 
                v-for="(line, index) in filteredLines"
                :key="index"
                class="whitespace-pre hover:bg-slate-50 px-2 py-0.5 rounded"
              >
                <span v-if="showLineNumber" class="text-slate-400 select-none mr-2">{{ (lines.indexOf(line) + 1).toString().padStart(5, ' ') }} │</span><span v-if="showTimestamp" class="text-slate-500">{{ line.timestamp }}</span> <span v-html="highlightText(line.text)"></span>
              </div>
            </div>
          </div>

          <!-- 发送区域 -->
          <div class="border-t border-slate-200 p-4 bg-slate-50">
            <div class="flex gap-2">
              <input 
                v-model="sendInput"
                @keyup.enter="sendData"
                type="text"
                placeholder="Enter command to send..."
                :disabled="status !== 'connected'"
                class="flex-1 px-4 py-2 text-sm font-mono bg-white text-slate-800 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-violet-500 disabled:opacity-50 disabled:bg-slate-100 placeholder:text-slate-400"
              />
              <button 
                @click="sendData"
                :disabled="status !== 'connected' || !sendInput.trim()"
                class="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white text-sm font-semibold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
              >
                <Send :size="16" />
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 自定义波特率对话框 -->
    <div v-if="showBaudRateDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click="showBaudRateDialog = false">
      <div class="bg-white rounded-xl p-6 w-80 shadow-2xl border border-slate-200" @click.stop>
        <h3 class="text-lg font-bold text-slate-800 mb-4">Add Custom Baud Rate</h3>
        <input 
          v-model="customBaudRateInput"
          @keyup.enter="addCustomBaudRate"
          type="number"
          placeholder="Enter baud rate..."
          class="w-full px-4 py-2 text-sm bg-white text-slate-800 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500"
        />
        <div class="flex justify-end gap-2 mt-4">
          <button 
            @click="showBaudRateDialog = false"
            class="px-4 py-2 text-sm font-semibold text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
          >
            Cancel
          </button>
          <button 
            @click="addCustomBaudRate"
            class="px-4 py-2 text-sm font-bold text-white bg-violet-600 rounded-lg hover:bg-violet-700 transition-colors"
          >
            Add
          </button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <transition name="toast">
      <div 
        v-if="showToast"
        class="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg bg-blue-600 text-white"
      >
        <span class="text-sm font-medium">{{ toastMessage }}</span>
        <button @click="showToast = false" class="hover:opacity-70">
          <X :size="16" />
        </button>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
