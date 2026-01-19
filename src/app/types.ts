// Type definitions for the time series annotation platform

export type DeviceType = 'watch' | 'ring';

export type ParseStatus = 'parsing' | 'completed' | 'failed';

export interface DataFile {
  id: string;
  fileName: string;
  deviceType: DeviceType;
  collectionTime: string;
  dataSize: string;
  parseStatus: ParseStatus;
  parseProgress?: number;
  errorMessage?: string;
  metadata?: {
    serialNumber: string;
    sampleRate: number;
  };
}

export interface TimeSeriesDataPoint {
  time: number; // seconds
  accX: number;
  accY: number;
  accZ: number;
  gyroX: number;
  gyroY: number;
  gyroZ: number;
}

export interface AnnotationRegion {
  id: string;
  label: string;
  startTime: number;
  endTime: number;
  color: string;
}

export interface LabelType {
  id: string;
  name: string;
  color: string;
  shortcut: string;
}

export interface FileDetail {
  file: DataFile;
  data: TimeSeriesDataPoint[];
  totalDuration: number;
  annotations: AnnotationRegion[];
}
