import { DeviceType, FileStatus, SensorFile } from './types';

export const MOCK_STATS = {
  totalFiles: 1251,
  todayUploads: 33,
  pendingTasks: 6,
  storageUsed: '450 GB',
};

export const MOCK_FILES: SensorFile[] = [
  {
    id: '550e8405',
    filename: 'watch_raw_pending.raw',
    deviceType: DeviceType.Watch,
    status: FileStatus.Unverified,
    size: '64 MB',
    duration: '--',
    deviceModel: 'Watch S9',
    testTypeL1: 'Unknown',
    testTypeL2: '--',

    notes: 'Waiting for manual processing',
    uploadTime: '2023-10-27T12:30:00',
    packets: [],
  },
  {
    id: '550e8400',
    filename: 'watch_run_001.raw',
    deviceType: DeviceType.Watch,
    status: FileStatus.Verified,
    size: '256 MB',
    duration: '01:30:00',
    deviceModel: 'Watch S8',
    testTypeL1: 'Run',
    testTypeL2: 'Outdoor',

    notes: 'Test for dropped frames in high motion',
    uploadTime: '2023-10-27T10:30:00',
    packets: [
      { name: 'ACC', freq: '100Hz', count: 54000, present: true },
      { name: 'PPG', freq: '25Hz', count: 13500, present: true },
      { name: 'GYRO', freq: '100Hz', count: 54000, present: true },
      { name: 'GPS', freq: '1Hz', count: 540, present: true },
    ],
  },
  {
    id: '550e8401',
    filename: 'ring_sleep_night.raw',
    deviceType: DeviceType.Ring,
    status: FileStatus.Processing,
    size: '1.2 GB',
    duration: '08:15:20',
    deviceModel: 'Ring Gen2',
    testTypeL1: 'Sleep',
    testTypeL2: 'Night Rest',

    notes: 'Click to add note',
    uploadTime: '2023-10-27T09:15:00',
    packets: [
      { name: 'ACC', freq: '50Hz', count: 120000, present: true },
      { name: 'PPG', freq: '50Hz', count: 120000, present: true },
      { name: 'TEMP', freq: '1Hz', count: 2400, present: true },
    ],
  },
  {
    id: '550e8402',
    filename: 'watch_err_data.raw',
    deviceType: DeviceType.Watch,
    status: FileStatus.Error,
    size: '10 MB',
    duration: '00:05:00',
    deviceModel: 'Watch S7',
    testTypeL1: 'Unknown',
    testTypeL2: '--',

    notes: 'File header corrupted',
    uploadTime: '2023-10-26T18:20:00',
    errorMessage: 'Header checksum mismatch',
    packets: [
      { name: 'ACC', freq: '?', count: 0, present: false },
      { name: 'PPG', freq: '?', count: 0, present: false },
    ],
  },
  {
    id: '550e8403',
    filename: 'watch_walk_office.raw',
    deviceType: DeviceType.Watch,
    status: FileStatus.Verified,
    size: '128 MB',
    duration: '00:45:00',
    deviceModel: 'Watch Ultra',
    testTypeL1: 'Walk',
    testTypeL2: 'Indoor',

    notes: 'Golden dataset candidate',
    uploadTime: '2023-10-26T14:10:00',
    packets: [
      { name: 'ACC', freq: '100Hz', count: 27000, present: true },
      { name: 'PPG', freq: '100Hz', count: 27000, present: true },
      { name: 'GYRO', freq: '100Hz', count: 27000, present: true },
      { name: 'BARO', freq: '1Hz', count: 270, present: true },
    ],
  },
  {
    id: '550e8404',
    filename: 'ring_hr_stress.raw',
    deviceType: DeviceType.Ring,
    status: FileStatus.Verified,
    size: '85 MB',
    duration: '00:20:00',
    deviceModel: 'Oura',
    testTypeL1: 'Stress',
    testTypeL2: 'Cognitive Task',

    notes: 'Subject moved slightly',
    uploadTime: '2023-10-25T11:00:00',
    packets: [
      { name: 'PPG', freq: '100Hz', count: 12000, present: true },
      { name: 'EDA', freq: '4Hz', count: 480, present: true },
    ]
  }
];

export const TEST_TYPES_L1 = ['Run', 'Walk', 'Sleep', 'Stress', 'Static', 'Unknown'];
export const TEST_TYPES_L2: Record<string, string[]> = {
  'Run': ['Outdoor', 'Treadmill', 'Trail'],
  'Walk': ['Indoor', 'Outdoor', 'Commute'],
  'Sleep': ['Night Rest', 'Nap', 'Sedentary'],
  'Stress': ['Cognitive Task', 'Public Speaking', 'Relaxation'],
  'Static': ['Table', 'Wrist'],
  'Unknown': ['--']
};