
// Mock the fix implementation for testing
function parseLogContent(content: string) {
    // FIX: Insert newline before timestamp if missing
    const fixedContent = content.replace(/([^\n])(\[\d{4}\/\d{1,2}\/\d{1,2}-\d{1,2}:\d{1,2}:\d{1,2}\])/g, '$1\n$2');

    console.log('--- Fixed Content ---');
    console.log(fixedContent);
    console.log('---------------------');

    const lines = fixedContent.split('\n');
    return lines;
}

const testLog = `hx3697_alg_process ppg_count_sum full:ppg_count_sum=49, rx1_data_group_cnt=51[2026/2/2-15:54:54]: mr_res: err=0 initT=3342 motion=1 det=3`;

console.log('Original Length:', testLog.split('\n').length);
const result = parseLogContent(testLog);
console.log('Parsed Length:', result.length);

if (result.length === 2 && result[1].startsWith('[')) {
    console.log('SUCCESS: Timestamp correctly split to new line.');
} else {
    console.error('FAILURE: Timestamp was not split correctly.');
}
