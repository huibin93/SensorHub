import { ref } from 'vue';
import apiClient from '../services/apiClient';

export interface DeviceMapping {
    deviceName: string;
    deviceType: string;
    deviceModel: string;
}

const deviceMappings = ref<DeviceMapping[]>([]);

export const fetchDeviceMappings = async () => {
    try {
        const res = await apiClient.get('/device-mappings/');
        deviceMappings.value = res.data;
    } catch (error) {
        console.error('Failed to fetch device mappings:', error);
    }
};

export const createDeviceMapping = async (mapping: DeviceMapping) => {
    try {
        const res = await apiClient.post('/device-mappings/', {
            device_name: mapping.deviceName,
            device_type: mapping.deviceType,
            device_model: mapping.deviceModel,
        });
        if (res.status === 200) {
            await fetchDeviceMappings();
        }
    } catch (error) {
        console.error('Failed to create device mapping:', error);
    }
};

export const updateDeviceMapping = async (deviceName: string, updates: { deviceType?: string; deviceModel?: string }) => {
    try {
        const res = await apiClient.put(`/device-mappings/${encodeURIComponent(deviceName)}`, {
            device_type: updates.deviceType,
            device_model: updates.deviceModel,
        });
        if (res.status === 200) {
            await fetchDeviceMappings();
        }
    } catch (error) {
        console.error('Failed to update device mapping:', error);
    }
};

export const getDeviceMappingByName = (name: string): DeviceMapping | undefined => {
    return deviceMappings.value.find(m =>
        m.deviceName.toLowerCase() === name.toLowerCase()
    );
};

export { deviceMappings };
