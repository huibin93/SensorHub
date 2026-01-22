export enum DeviceType {
  Watch = 'Watch',
  Ring = 'Ring',
}

export enum FileStatus {
  Idle = 'Idle',
  Ready = 'Ready',
  Processing = 'Processing',
  Failed = 'Failed',
}

export interface PacketInfo {
  name: string;
  freq: string; // e.g., "100Hz"
  count: number;
  present: boolean;
}

export interface SensorFile {
  id: string;
  filename: string;
  deviceType: DeviceType;
  status: FileStatus;
  size: string;
  duration: string;
  deviceModel: string;
  testTypeL1: string; // e.g., "Walking"
  testTypeL2: string; // e.g., "Outdoor"
  progress?: number; // 0-100 for processing progress

  notes: string;
  uploadTime: string; // ISO string
  packets: PacketInfo[];
  errorMessage?: string;
}

export interface Stats {
  totalFiles: number;
  todayUploads: number;
  pendingTasks: number;
  storageUsed: string;
}