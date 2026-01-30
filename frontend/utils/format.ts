
/**
 * Format bytes to human-readable string
 * @param bytes - Size in bytes
 * @param decimals - Number of decimal places
 */
export function formatBytes(bytes: number, decimals: number = 2): string {
    if (bytes === 0) return '0 B';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export function formatBytesSplit(bytes: number, decimals: number = 2): { value: string, unit: string } {
    if (bytes === 0) return { value: '0', unit: 'B' };

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return {
        value: parseFloat((bytes / Math.pow(k, i)).toFixed(dm)).toString(),
        unit: sizes[i]
    };
}
