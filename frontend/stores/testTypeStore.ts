/**
 * Test Type Store
 * 
 * Manages test types and sub-types, fetching from backend API.
 */

import { ref, computed } from 'vue';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// Internal state
interface TestTypeData {
    id: string;
    name: string;
    subTypes: string[];
}

const testTypesData = ref<TestTypeData[]>([]);
const isLoaded = ref(false);

// Computed: all L1 types (names only)
export const testTypesL1 = computed(() => testTypesData.value.map(t => t.name));
export const allTestTypesL1 = testTypesL1;

// Computed: L2 types mapping
export const testTypesL2 = computed(() => {
    const mapping: Record<string, string[]> = {};
    for (const t of testTypesData.value) {
        mapping[t.name] = t.subTypes;
    }
    return mapping;
});

// Fetch test types from API
export async function fetchTestTypes(): Promise<void> {
    if (isLoaded.value) return;

    try {
        const response = await axios.get(`${API_BASE_URL}/test-types`);
        testTypesData.value = response.data.types || [];
        isLoaded.value = true;
        console.log('[TestTypeStore] Loaded test types from API:', testTypesData.value.length);
    } catch (e) {
        console.error('[TestTypeStore] Failed to fetch test types:', e);
    }
}

// Add new Primary Type (L1)
export async function addTestTypeL1(newType: string): Promise<boolean> {
    const trimmed = newType.trim();
    if (!trimmed) return false;

    // Check if already exists
    if (testTypesData.value.some(t => t.name === trimmed)) {
        return false;
    }

    // Optimistic update
    const tempId = trimmed.toLowerCase().replace(/\s+/g, '_');
    testTypesData.value.push({
        id: tempId,
        name: trimmed,
        subTypes: ['--']
    });

    try {
        const response = await axios.post(`${API_BASE_URL}/test-types`, {
            name: trimmed,
            subTypes: ['--']
        });
        // Update with real ID if different
        const idx = testTypesData.value.findIndex(t => t.id === tempId);
        if (idx > -1 && response.data.testType) {
            testTypesData.value[idx].id = response.data.testType.id;
        }
        console.log('[TestTypeStore] Added new L1 type:', trimmed);
        return true;
    } catch (e) {
        // Rollback
        testTypesData.value = testTypesData.value.filter(t => t.id !== tempId);
        console.error('[TestTypeStore] Failed to add L1 type:', e);
        return false;
    }
}

// Add new Sub Type (L2) to a Primary Type
export async function addTestTypeL2(primaryType: string, newSubType: string): Promise<boolean> {
    const trimmed = newSubType.trim();
    if (!trimmed || trimmed === '--') return false;

    const typeData = testTypesData.value.find(t => t.name === primaryType);
    if (!typeData) return false;

    // Check if already exists
    if (typeData.subTypes.includes(trimmed)) {
        return false;
    }

    // Optimistic update
    typeData.subTypes.push(trimmed);

    try {
        await axios.post(`${API_BASE_URL}/test-types/${typeData.id}/sub-types`, {
            name: trimmed
        });
        console.log('[TestTypeStore] Added new L2 type:', trimmed, 'to', primaryType);
        return true;
    } catch (e) {
        // Rollback
        const idx = typeData.subTypes.indexOf(trimmed);
        if (idx > -1) typeData.subTypes.splice(idx, 1);
        console.error('[TestTypeStore] Failed to add L2 type:', e);
        return false;
    }
}

// Get L2 types for a primary type
export function getTestTypesL2(primaryType: string): string[] {
    const typeData = testTypesData.value.find(t => t.name === primaryType);
    return typeData?.subTypes || ['--'];
}
