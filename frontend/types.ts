export enum DeviceType {
  Watch = 'Watch',
  Ring = 'Ring',
}

export enum FileStatus {
  Unverified = 'unverified',
  Idle = 'idle',
  Error = 'error',
  Processing = 'processing',
  Processed = 'processed',
  Failing = 'failing',
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
  nameSuffix?: string; // Phase 5.6: Suffix for duplicate filenames " (1)"
  deviceType: DeviceType;
  deviceName?: string; // From metadata
  status: FileStatus;
  size: string;
  duration: string;
  deviceModel: string;
  testTypeL1: string; // e.g., "Walking"
  testTypeL2: string; // e.g., "Outdoor"
  progress?: number; // 0-100 for processing progress

  notes: string;
  uploadTime: string; // ISO string
  startTime?: string; // From metadata
  collectionTime?: string; // From metadata
  timezone?: string; // GMT+08:00
  packets: PacketInfo[];
  errorMessage?: string;
}

export interface Stats {
  totalFiles: number;
  todayUploads: number;
  pendingTasks: number;
  storageUsed: string;
}