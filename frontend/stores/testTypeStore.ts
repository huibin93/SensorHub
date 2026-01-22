import { ref, computed } from 'vue';

// 全局响应式测试类型列表
export const testTypesL1 = ref<string[]>([
    'Unknown',
    'Run',
    'Walk',
    'Sleep',
    'Stress',
    'Yoga',
    'Cycle'
]);

// 全局响应式子类型映射
export const testTypesL2 = ref<Record<string, string[]>>({
    'Unknown': ['--'],
    'Run': ['Outdoor', 'Indoor', 'Treadmill'],
    'Walk': ['Outdoor', 'Indoor'],
    'Sleep': ['Night Rest', 'Nap'],
    'Stress': ['Work', 'Exercise', 'Daily'],
    'Yoga': ['Meditation', 'Flow', 'Power'],
    'Cycle': ['Outdoor', 'Indoor', 'Stationary']
});

// 添加新的Primary Type
export function addTestTypeL1(newType: string) {
    const trimmed = newType.trim();
    if (!trimmed) return false;

    if (!testTypesL1.value.includes(trimmed)) {
        testTypesL1.value.push(trimmed);
        // 为新类型初始化一个空的子类型数组
        if (!testTypesL2.value[trimmed]) {
            testTypesL2.value[trimmed] = ['--'];
        }
        console.log('[TestTypeStore] Added new L1 type:', trimmed);
        return true;
    }
    return false;
}

// 添加新的Sub Type到指定的Primary Type
export function addTestTypeL2(primaryType: string, newSubType: string) {
    const trimmed = newSubType.trim();
    if (!trimmed || trimmed === '--') return false;

    if (!testTypesL2.value[primaryType]) {
        testTypesL2.value[primaryType] = ['--'];
    }

    if (!testTypesL2.value[primaryType].includes(trimmed)) {
        testTypesL2.value[primaryType].push(trimmed);
        console.log('[TestTypeStore] Added new L2 type:', trimmed, 'to', primaryType);
        return true;
    }
    return false;
}

// 获取所有L1类型（只读计算属性）
export const allTestTypesL1 = computed(() => testTypesL1.value);

// 获取指定L1的所有L2类型
export function getTestTypesL2(primaryType: string): string[] {
    return testTypesL2.value[primaryType] || ['--'];
}
