import { DataFile, TimeSeriesDataPoint, LabelType } from './types';

// Mock data files
export const mockDataFiles: DataFile[] = [
  {
    id: '1',
    fileName: 'subject_001_morning_run.rawdata',
    deviceType: 'watch',
    collectionTime: '2026-01-19 08:30:45',
    dataSize: '12.5 MB',
    parseStatus: 'completed',
    metadata: {
      serialNumber: 'A1B2C3D4',
      sampleRate: 50,
    },
  },
  {
    id: '2',
    fileName: 'subject_002_sleep_session.rawdata',
    deviceType: 'ring',
    collectionTime: '2026-01-18 22:15:20',
    dataSize: '45.8 MB',
    parseStatus: 'completed',
    metadata: {
      serialNumber: 'R5E6F7G8',
      sampleRate: 50,
    },
  },
  {
    id: '3',
    fileName: 'subject_003_daily_activity.rawdata',
    deviceType: 'watch',
    collectionTime: '2026-01-17 09:00:00',
    dataSize: '28.3 MB',
    parseStatus: 'parsing',
    parseProgress: 67,
  },
  {
    id: '4',
    fileName: 'subject_004_workout.rawdata',
    deviceType: 'watch',
    collectionTime: '2026-01-16 16:45:30',
    dataSize: '15.2 MB',
    parseStatus: 'failed',
    errorMessage: 'Invalid file format: header checksum mismatch',
  },
];

// Generate mock time series data
export function generateMockTimeSeriesData(duration: number = 135): TimeSeriesDataPoint[] {
  const sampleRate = 50; // Hz
  const totalSamples = duration * sampleRate;
  const data: TimeSeriesDataPoint[] = [];

  for (let i = 0; i < totalSamples; i++) {
    const time = i / sampleRate;
    
    // Simulate different activity patterns
    let accAmplitude = 0.5;
    let gyroAmplitude = 0.3;
    
    // Walking pattern (0-45s)
    if (time < 45) {
      accAmplitude = 1.5;
      gyroAmplitude = 0.5;
    }
    // Running pattern (45-90s)
    else if (time < 90) {
      accAmplitude = 3.0;
      gyroAmplitude = 1.2;
    }
    // Resting pattern (90-135s)
    else {
      accAmplitude = 0.3;
      gyroAmplitude = 0.1;
    }

    data.push({
      time,
      accX: accAmplitude * Math.sin(time * 2 + Math.random() * 0.2),
      accY: accAmplitude * Math.cos(time * 1.5 + Math.random() * 0.2),
      accZ: accAmplitude * Math.sin(time * 2.5 + Math.random() * 0.2) + 9.8, // gravity
      gyroX: gyroAmplitude * Math.sin(time * 3 + Math.random() * 0.1),
      gyroY: gyroAmplitude * Math.cos(time * 2 + Math.random() * 0.1),
      gyroZ: gyroAmplitude * Math.sin(time * 1.8 + Math.random() * 0.1),
    });
  }

  return data;
}

// Label types with colors
export const labelTypes: LabelType[] = [
  {
    id: 'running',
    name: '跑步',
    color: '#F5222D',
    shortcut: '1',
  },
  {
    id: 'walking',
    name: '走路',
    color: '#52C41A',
    shortcut: '2',
  },
  {
    id: 'sleeping',
    name: '睡眠',
    color: '#1890FF',
    shortcut: '3',
  },
  {
    id: 'sitting',
    name: '静坐',
    color: '#722ED1',
    shortcut: '4',
  },
  {
    id: 'standing',
    name: '站立',
    color: '#FA8C16',
    shortcut: '5',
  },
];
