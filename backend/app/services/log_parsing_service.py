
import re
import pandas as pd
from typing import List, Dict, Any, Optional

# 字段映射表，由用户提供
FIELD_MAP = {
    "wf": "wear_flag",
    "wg": "wear_flag",
    "en": "error_no",
    "rt": "return_type",
    "ir": "wear_ir_result", # 注意: 'ir' 在这里映射到 'wear_ir_result'
    "gr": "wear_green_result",
    "amb": "wear_ambient_result",
    "cf": "confusion",
    "pk": "peak_cnt",
    "hr": "wear_rr_hr",
    "dc": "ppg_dc_value",
    "gtf": "green_temp_flag_encode",
    "acm": "wear_acc_momentum",
    "acc": "wear_acc_momentum",
    "as": "amb_std",
    "it": "init_timer",
    "st": "state",
    "state": "state",
    "6d": "imu_6d_state",
    "gc": "ppg_g_current",
    "gi": "ppg_g_idac",
    "irv": "ppg_ir_value",
    # "ir": "ppg_ir_value", # 参见下方注释
    "eg": "entropy_geometric",
    "zcr": "zero_crossing_rate",
    "lt": "light",
    "gsz": "ppg_g_size",
    "lirsz": "ppg_low_ir_size",
    "baseline": "low_ir_baseline",
}

# 如果需要优先级映射逻辑，可以添加或直接在代码中处理。
# 用户原始代码: `mapped_key = field_map.get(k, k)`
# 如果出现 `ir`, 它映射到 `wear_ir_result`。
# 如果出现 `irv`, 它映射到 `ppg_ir_value`。
# 由于我们需要在第5个图表中可视化 `ppg_ir_value` (IRV)，我们应确保 `irv` 或 `ir` (大值) 映射正确。
# 在日志中: `irv=14495`。`ir=0` 或 `ir=1`。
# 因此 `ir` -> `wear_ir_result` (0/1)。`irv` -> `ppg_ir_value` (14495)。
# 图表需要 `ppg_ir_value`。
# 如果日志只有 `ir` (旧格式?) 且它是大值，可能会有问题。
# 但当前提供的日志包含 `irv`。

def parse_wear_check_log(log_text: str) -> List[Dict[str, Any]]:
    """
    解析佩戴检测算法日志
    """
    rows = []
    # 匹配时间戳和内容
    # 支持 [[2026/2/4-10:11:24]] wear_check_algo: : content...
    # 同时也支持 [2026/2/4-10:11:24] 这种格式
    line_pattern = re.compile(r'\[{1,2}(.*?)\]{1,2}\s*wear_check_algo:\s*:\s*(.*)')
    kv_pattern = re.compile(r'(\w+)=([\w\d|x.\-]+)') # 增强版以支持浮点数和负数

    for line in log_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
            
        match = line_pattern.search(line)
        if match:
            dt_str = match.group(1)
            msg_str = match.group(2)
            row = {'datetime': dt_str}
            
            # 提取所有键值对
            kvs = kv_pattern.findall(msg_str)
            for k, v in kvs:
                # 数值转换
                try:
                    if v.startswith('0x'):
                        val = int(v, 16)
                    elif '.' in v:
                        val = float(v)
                    else:
                        val = int(v)
                except ValueError:
                    val = 0 # 回退值
                
                # 映射字段名
                mapped_key = FIELD_MAP.get(k, k)
                row[mapped_key] = val
            
            # 使用 'state' 别名逻辑，如果 'st' 被映射为 'state' -> 已通过映射处理
            # 使用 'acm' 别名逻辑，如果 'acc' 被映射为 'wear_acc_momentum' -> 已通过映射处理
            
            rows.append(row)
            
    # 转换为标准的列表字典格式用于 JSON 响应
    # 如果我们需要 DataFrame 操作 (例如 fillna, rolling)，可以在这里使用 pandas。
    # 用户要求 "后端解析以方便编写 python 脚本"，所以使用 pandas 是合适的。
    if rows:
        df = pd.DataFrame(rows)
        # 如果需要，可以在这里进行一些清理工作
        # 处理重复索引或排序？
        # df['datetime'] = pd.to_datetime(df['datetime'], format='%Y/%m/%d-%H:%M:%S', errors='coerce')
        # 返回记录
        return df.to_dict(orient='records')
    return []
