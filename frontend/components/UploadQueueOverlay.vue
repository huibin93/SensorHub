<script setup lang="ts">
import { ref, computed } from 'vue';
import { FileText, CheckCircle, X, Loader2 } from 'lucide-vue-next';

// 上传任务接口
interface UploadTask {
  id: string;
  filename: string;
  size: number;
  progress: number; // 0-100
  status: 'pending' | 'uploading' | 'completed' | 'error';
  message?: string;
  isRemoving?: boolean; // 标记正在移除的动画状态
}

const tasks = ref<UploadTask[]>([]);
const isVisible = computed(() => tasks.value.length > 0);

// 添加任务到队列
const addTask = (filename: string, size: number): string => {
  const id = `task-${Date.now()}-${Math.random()}`;
  tasks.value.push({
    id,
    filename,
    size,
    progress: 0,
    status: 'pending',
  });
  return id;
};

// 更新任务进度
const updateProgress = (id: string, progress: number) => {
  const task = tasks.value.find(t => t.id === id);
  if (task) {
    task.progress = Math.min(100, Math.max(0, progress));
    if (task.status === 'pending') {
      task.status = 'uploading';
    }
  }
};

// 标记任务完成
const markCompleted = (id: string, message?: string) => {
  const task = tasks.value.find(t => t.id === id);
  if (task) {
    task.status = 'completed';
    task.progress = 100;
    task.message = message;
    
    // 延迟后移除
    setTimeout(() => {
      removeTask(id);
    }, 1500);
  }
};

// 标记任务错误
const markError = (id: string, message: string) => {
  const task = tasks.value.find(t => t.id === id);
  if (task) {
    task.status = 'error';
    task.message = message;
    
    // 自动移除错误任务
    setTimeout(() => {
      removeTask(id);
    }, 5000);
  }
};

// 移除任务（带动画）
const removeTask = (id: string) => {
  const task = tasks.value.find(t => t.id === id);
  if (task) {
    task.isRemoving = true;
    // 等待动画完成后移除
    setTimeout(() => {
      const index = tasks.value.findIndex(t => t.id === id);
      if (index !== -1) {
        tasks.value.splice(index, 1);
      }
    }, 500); // 动画持续时间
  }
};

// 格式化文件大小
const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
};

// 暴露方法给父组件
defineExpose({
  addTask,
  updateProgress,
  markCompleted,
  markError,
});
</script>

<template>
  <Transition
    enter-active-class="transition duration-300 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition duration-200 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="isVisible"
      class="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-6"
    >
      <!-- 上传队列面板 -->
      <div class="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[80vh]">
        <!-- 标题栏 -->
        <div class="px-6 py-4 bg-gradient-to-r from-blue-50 to-violet-50 border-b border-slate-200">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-blue-500 text-white rounded-lg">
                <Loader2 :size="20" class="animate-spin" />
              </div>
              <div>
                <h3 class="text-lg font-bold text-slate-800">Uploading Files</h3>
                <p class="text-xs text-slate-500">
                  {{ tasks.filter(t => t.status !== 'completed').length }} remaining
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- 任务列表 -->
        <div class="flex-1 overflow-y-auto p-4 space-y-3">
          <TransitionGroup
            enter-active-class="transition duration-300 ease-out"
            enter-from-class="opacity-0 scale-95 -translate-y-4"
            enter-to-class="opacity-100 scale-100 translate-y-0"
            leave-active-class="transition duration-500 ease-in"
            leave-from-class="opacity-100 translate-x-0"
            leave-to-class="opacity-0 translate-x-full"
            move-class="transition duration-300 ease-in-out"
          >
            <div
              v-for="task in tasks"
              :key="task.id"
              class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm hover:shadow-md transition-shadow"
              :class="{
                'border-green-200 bg-green-50/30': task.status === 'completed',
                'border-red-200 bg-red-50/30': task.status === 'error',
              }"
            >
              <div class="flex items-start gap-3">
                <!-- 图标 -->
                <div
                  class="flex-shrink-0 p-2 rounded-lg transition-colors"
                  :class="{
                    'bg-blue-100 text-blue-600': task.status === 'pending' || task.status === 'uploading',
                    'bg-green-100 text-green-600': task.status === 'completed',
                    'bg-red-100 text-red-600': task.status === 'error',
                  }"
                >
                  <Loader2 v-if="task.status === 'uploading'" :size="20" class="animate-spin" />
                  <CheckCircle v-else-if="task.status === 'completed'" :size="20" />
                  <X v-else-if="task.status === 'error'" :size="20" />
                  <FileText v-else :size="20" />
                </div>

                <!-- 文件信息 -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-start justify-between gap-2 mb-2">
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-semibold text-slate-800 truncate">
                        {{ task.filename }}
                      </p>
                      <p class="text-xs text-slate-500 mt-0.5">
                        {{ formatSize(task.size) }}
                        <span v-if="task.message" class="ml-2">• {{ task.message }}</span>
                      </p>
                    </div>
                    <div class="flex-shrink-0 text-right">
                      <p
                        class="text-sm font-bold"
                        :class="{
                          'text-blue-600': task.status === 'uploading',
                          'text-green-600': task.status === 'completed',
                          'text-red-600': task.status === 'error',
                          'text-slate-400': task.status === 'pending',
                        }"
                      >
                        {{ task.progress }}%
                      </p>
                    </div>
                  </div>

                  <!-- 进度条 -->
                  <div class="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all duration-300 ease-out"
                      :class="{
                        'bg-gradient-to-r from-blue-500 to-blue-600': task.status === 'uploading',
                        'bg-gradient-to-r from-green-500 to-green-600': task.status === 'completed',
                        'bg-gradient-to-r from-red-500 to-red-600': task.status === 'error',
                        'bg-slate-300': task.status === 'pending',
                      }"
                      :style="{ width: task.progress + '%' }"
                    >
                      <div
                        v-if="task.status === 'uploading'"
                        class="h-full w-full bg-gradient-to-r from-transparent via-white/30 to-transparent animate-pulse"
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </TransitionGroup>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* 确保动画流畅 */
.transition {
  transition-property: all;
}
</style>
