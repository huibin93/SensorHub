import { ref } from 'vue';
import { DeviceType } from '../types';

// Device type options - fixed to Watch and Ring
export const deviceTypeOptions = [
    { type: DeviceType.Watch, label: 'Smart Watch' },
    { type: DeviceType.Ring, label: 'Smart Ring' }
];

// Global reactive device model lists by type
export const deviceModels = ref<Record<DeviceType, string[]>>({
    [DeviceType.Watch]: [
        'Apple Watch Series 9',
        'Samsung Galaxy Watch 6',
        'Fitbit Sense 2',
        'Garmin Forerunner 965'
    ],
    [DeviceType.Ring]: [
        'Oura Ring Gen 3',
        'Samsung Galaxy Ring',
        'Circular Ring Slim',
        'Ultrahuman Ring AIR'
    ]
});

// Add a new device model to a specific type
export function addDeviceModel(deviceType: DeviceType, modelName: string): boolean {
    const trimmed = modelName.trim();
    if (!trimmed) return false;

    if (!deviceModels.value[deviceType].includes(trimmed)) {
        deviceModels.value[deviceType].push(trimmed);
        console.log('[DeviceStore] Added new model:', trimmed, 'to', deviceType);
        return true;
    }
    return false;
}

// Get device models for a specific type
export function getDeviceModels(deviceType: DeviceType): string[] {
    return deviceModels.value[deviceType] || [];
}
