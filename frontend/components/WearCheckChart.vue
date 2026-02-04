<template>
  <div class="wear-check-chart h-full flex flex-col">
    <div class="p-4 bg-white border-b border-slate-200 flex justify-between items-center shrink-0">
      <h3 class="font-bold text-slate-700">Wear Check Algo Visualization</h3>
      <div class="text-xs text-slate-500">
        {{ parsedData.length }} data points
      </div>
    </div>
    <div class="flex-1 min-h-0 relative bg-slate-50 p-4">
      <div ref="chartRef" class="w-full h-full"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed, onUnmounted, nextTick } from 'vue';
import * as echarts from 'echarts';
import type { LogEntry } from '../utils/logParser';
import { api } from '../services/api';

const props = defineProps<{
  entries: LogEntry[];
}>();

const chartRef = ref<HTMLElement | null>(null);
let myChart: echarts.ECharts | null = null;
let resizeObserver: ResizeObserver | null = null;

const parsedData = ref<any[]>([]);
const isLoading = ref(false);

const fetchData = async () => {
  if (props.entries.length === 0) {
    parsedData.value = [];
    return;
  }
  
  isLoading.value = true;
  
  // Reconstruct log content for backend parser
  // Backend expects: [[timestamp]] wear_check_algo: : content
  // We strictly format it to match the backend regex expectations
  const content = props.entries.map(e => {
      // Ensure time matches regex
      return `${e.time} wear_check_algo: : ${e.content}`;
  }).join('\n');
  
  try {
    const { data } = await api.post('/log-parser/wear-check', { content });
    parsedData.value = data.data;
    renderChart();
  } catch (err) {
    console.error("Failed to parse log data via backend", err);
    // Fallback? Or just show error
  } finally {
    isLoading.value = false;
  }
};

const initChart = () => {
  if (!chartRef.value) return;
  
  if (myChart) {
    myChart.dispose();
  }
  
  myChart = echarts.init(chartRef.value);
  renderChart();
};

const renderChart = () => {
  if (!myChart) return;
  
  const data = parsedData.value;
  if (data.length === 0) {
    myChart.clear();
    return;
  }
  
  const xData = data.map(item => item.init_timer);
  const xLabels = data.map(item => item.datetime);
  
  const option: echarts.EChartsOption = {
    title: { 
        text: 'Sensor Algorithm Data Analysis', 
        left: 'center',
        top: 10
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!Array.isArray(params) || params.length === 0) return '';
        const idx = params[0].dataIndex;
        const item = data[idx];
        let res = `Timer: ${item.init_timer}<br/>Time: ${item.datetime}<br/>`;
        params.forEach((p: any) => {
          if (p.seriesName) {
             res += `${p.marker} ${p.seriesName}: ${p.value}<br/>`;
          }
        });
        return res;
      }
    },
    grid: [
      { top: '10%', height: '14%', left: '5%', right: '5%' },  // wear_flag
      { top: '28%', height: '14%', left: '5%', right: '5%' }, // state
      { top: '46%', height: '14%', left: '5%', right: '5%' }, // wear_acc_momentum
      { top: '64%', height: '14%', left: '5%', right: '5%' }, // ppg_dc_value
      { top: '82%', height: '14%', left: '5%', right: '5%' }  // ppg_ir_value
    ],
    xAxis: [0, 1, 2, 3, 4].map(i => ({
      gridIndex: i,
      type: 'category',
      data: xData, // shared X data (init_timer)
      show: i === 4, // Only show for the last one
      axisLabel: { show: i === 4 },
      axisTick: { show: i === 4 }
    })),
    yAxis: [
      { gridIndex: 0, name: 'Wear Flag', splitLine: { show: true, lineStyle: { opacity: 0.3 } } },
      { gridIndex: 1, name: 'State', splitLine: { show: true, lineStyle: { opacity: 0.3 } } },
      { gridIndex: 2, name: 'Acc Momentum', splitLine: { show: true, lineStyle: { opacity: 0.3 } } },
      { gridIndex: 3, name: 'PPG DC', splitLine: { show: true, lineStyle: { opacity: 0.3 } } },
      { gridIndex: 4, name: 'PPG IR', splitLine: { show: true, lineStyle: { opacity: 0.3 } }, nameLocation: 'middle', nameGap: 30 }
    ],
    dataZoom: [{ type: 'slider', xAxisIndex: [0, 1, 2, 3, 4], bottom: '0%' }, { type: 'inside', xAxisIndex: [0, 1, 2, 3, 4] }],
    series: [
      {
        name: 'wear_flag',
        type: 'line',
        step: 'start',
        xAxisIndex: 0, yAxisIndex: 0,
        data: data.map(item => item.wear_flag),
        showSymbol: false,
        itemStyle: { color: 'blue' }
      },
      {
        name: 'state',
        type: 'line',
        step: 'start',
        xAxisIndex: 1, yAxisIndex: 1,
        data: data.map(item => item.state),
        showSymbol: false,
        itemStyle: { color: 'orange' }
      },
      {
        name: 'ACM', // Label matches python script 'label'
        type: 'bar', // Using bar as requested generally, though step also used in python comments for others.
        xAxisIndex: 2, yAxisIndex: 2,
        data: data.map(item => item.wear_acc_momentum),
        itemStyle: { color: 'green', opacity: 0.7 },
        large: true
      },
      {
        name: 'DC',
        type: 'bar',
        xAxisIndex: 3, yAxisIndex: 3,
        data: data.map(item => item.ppg_dc_value),
        itemStyle: { color: 'red', opacity: 0.7 },
        large: true
      },
      {
        name: 'IRV',
        type: 'bar',
        xAxisIndex: 4, yAxisIndex: 4,
        data: data.map(item => item.ppg_ir_value),
        itemStyle: { color: 'purple', opacity: 0.7 },
        large: true
      }
    ]
  };

  myChart.setOption(option);
};

// Lifecycle
onMounted(() => {
  if (!chartRef.value) return;

  // Initial fetch
  fetchData();

  // Use ResizeObserver to trigger init when dimensions are ready
  resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
        if (!myChart) {
          initChart();
        } else {
          myChart.resize();
        }
      }
    }
  });
  
  resizeObserver.observe(chartRef.value);
});

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect();
  myChart?.dispose();
});

watch(() => props.entries, () => {
    fetchData();
}, { deep: true });

</script>

<style scoped>
/* Ensure tooltip is on top */
:deep(.echarts-tooltip) {
    z-index: 9999;
}
</style>
