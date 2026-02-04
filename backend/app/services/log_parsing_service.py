
import re
import pandas as pd
from typing import List, Dict, Any, Optional

# Field map as provided by user
FIELD_MAP = {
    "wf": "wear_flag",
    "wg": "wear_flag",
    "en": "error_no",
    "rt": "return_type",
    "ir": "wear_ir_result", # Note: 'ir' is mapped to 'wear_ir_result' here
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
    # "ir": "ppg_ir_value", # See comment below
    "eg": "entropy_geometric",
    "zcr": "zero_crossing_rate",
    "lt": "light",
    "gsz": "ppg_g_size",
    "lirsz": "ppg_low_ir_size",
    "baseline": "low_ir_baseline",
}

# Add priority mapping logic if needed or just handle in code.
# The user's code: `mapped_key = field_map.get(k, k)`
# If `ir` appears, it maps to `wear_ir_result`.
# If `irv` appears, it maps to `ppg_ir_value`.
# Since we want to visualize `ppg_ir_value` (IRV) in the 5th plot, we should ensure `irv` or `ir` (large value) maps correctly.
# In the log: `irv=14495`. `ir=0` or `ir=1`.
# So `ir` -> `wear_ir_result` (0/1). `irv` -> `ppg_ir_value` (14495).
# The chart needs `ppg_ir_value`.
# If the log ONLY has `ir` (old format?) and it is the large value, we might have an issue.
# But provided logs have `irv`.

def parse_wear_check_log(log_text: str) -> List[Dict[str, Any]]:
    rows = []
    # Match timestamp and content
    # Support [[2026/2/4-10:11:24]] wear_check_algo: : content...
    # Also support [2026/2/4-10:11:24] if happens.
    line_pattern = re.compile(r'\[{1,2}(.*?)\]{1,2}\s*wear_check_algo:\s*:\s*(.*)')
    kv_pattern = re.compile(r'(\w+)=([\w\d|x.\-]+)') # Enhanced to support floats and negatives just in case

    for line in log_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
            
        match = line_pattern.search(line)
        if match:
            dt_str = match.group(1)
            msg_str = match.group(2)
            row = {'datetime': dt_str}
            
            # Extract all key-value pairs
            kvs = kv_pattern.findall(msg_str)
            for k, v in kvs:
                # Value conversion
                try:
                    if v.startswith('0x'):
                        val = int(v, 16)
                    elif '.' in v:
                        val = float(v)
                    else:
                        val = int(v)
                except ValueError:
                    val = 0 # Fallback
                
                # Map field name
                mapped_key = FIELD_MAP.get(k, k)
                row[mapped_key] = val
            
            # Use 'state' alias logic if 'st' was parsed as 'state' -> done by map
            # Use 'acm' alias logic if 'acc' was parsed as 'wear_acc_momentum' -> done by map
            
            rows.append(row)
            
    # Convert to standard list of dicts for JSON response
    # If we need DataFrame operations (e.g. fillna, rolling), we can use pandas here.
    # User asked for "backend parsing to facilitate writing python script", so using pandas is good.
    if rows:
        df = pd.DataFrame(rows)
        # We can do some cleanup here if needed
        # Handle duplicate indices or sorting?
        # df['datetime'] = pd.to_datetime(df['datetime'], format='%Y/%m/%d-%H:%M:%S', errors='coerce')
        # We return the records
        return df.to_dict(orient='records')
    return []
