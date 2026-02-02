/**
 * Device Store
 * 
 * Manages device types and models, fetching from backend API.
 */

import { ref, computed } from 'vue';
import axios from 'axios';
import { DeviceType } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// State
const deviceModelsData = ref<Record<DeviceType, string[]>>({
    [DeviceType.Watch]: [],
    [DeviceType.Ring]: []
});

const isLoaded = ref(false);

// Device type options - fixed
export const deviceTypeOptions = [
    { type: DeviceType.Watch, label: 'Smart Watch' },
    { type: DeviceType.Ring, label: 'Smart Ring' }
];

// Reactive device models export
export const deviceModels = computed(() => deviceModelsData.value);

// Fetch device data from API
export async function fetchDevices(): Promise<void> {
    if (isLoaded.value) return;

    try {
        const response = await axios.get(`${API_BASE_URL}/devices`);
        const data = response.data;

        deviceModelsData.value = {
            [DeviceType.Watch]: data.deviceModels?.Watch || [],
            [DeviceType.Ring]: data.deviceModels?.Ring || []
        };

        isLoaded.value = true;
        console.log('[DeviceStore] Loaded devices from API');
    } catch (e) {
        console.error('[DeviceStore] Failed to fetch devices:', e);
        // Keep default empty arrays
    }
}

// Add a new device model to a specific type
export async function addDeviceModel(deviceType: DeviceType, modelName: string): Promise<boolean> {
    const trimmed = modelName.trim();
    if (!trimmed) return false;

    // Optimistic update
    if (!deviceModelsData.value[deviceType].includes(trimmed)) {
        deviceModelsData.value[deviceType].push(trimmed);

        try {
            await axios.post(`${API_BASE_URL}/devices/models`, {
                deviceType: deviceType,
                modelName: trimmed
            });
            console.log('[DeviceStore] Added new model:', trimmed, 'to', deviceType);
            return true;
        } catch (e) {
            // Rollback
            const idx = deviceModelsData.value[deviceType].indexOf(trimmed);
            if (idx > -1) deviceModelsData.value[deviceType].splice(idx, 1);
            console.error('[DeviceStore] Failed to add model:', e);
            return false;
        }
    }
    return false;
}

// Get device models for a specific type
export function getDeviceModels(deviceType: DeviceType): string[] {
    return deviceModelsData.value[deviceType] || [];
}
