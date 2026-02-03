"""
元数据解析服务模块;

提供从原始数据内容或 ZSTD 压缩文件中提取元数据的功能;
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import zstandard as zstd

def clean_control_characters(text: str) -> str:
    """Remove problematic ASCII control characters while keeping \t, \n, \r."""
    return re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)


def repair_json_via_comma_split(json_content: str) -> str:
    """Try to repair a corrupted JSON-like string by cleaning control chars
    and fixing simple missing-quote/key issues.
    This is a best-effort fixer for metadata lines in rawdata files.
    """
    json_content = clean_control_characters(json_content)
    content = json_content.strip().strip('{}')
    fixed_parts = []

    for part in content.split(','):
        part = part.strip()
        if not part:
            continue

        quote_count = part.count('"')

        if quote_count == 3:
            part += '"'
        elif quote_count == 1 and ':' in part:
            try:
                key, value = part.split(':', 1)
                key = key.strip().strip('"\'')
                value = value.strip().strip('"\'')
                part = f'"{key}":"{value}"'
            except ValueError:
                pass
        elif quote_count == 0 and ':' in part:
            try:
                key, value = part.split(':', 1)
                key = key.strip().strip('"\'')
                value = value.strip().strip('"\'')
                part = f'"{key}":"{value}"'
            except ValueError:
                pass

        fixed_parts.append(part)

    return '{' + ','.join(fixed_parts) + '}'


def merge_metadata_objects(metadata_list: List[Dict]) -> Dict[str, Any]:
    """Merge a list of small metadata dicts into one dict.
    Resolve `Mac address` conflicts by renaming them to clear keys:
      - device_mac   : the device being collected
      - reference_mac: the reference device
      - phone_version: the phone / collector field (often a build string)
    Other keys are stripped of surrounding spaces and merged.
    """
    merged = {}
    device_info_keys = {'device', 'device version'}
    reference_info_keys = {'reference'}
    phone_info_keys = {'phone'}

    for obj in metadata_list:
        if not isinstance(obj, dict):
            continue

        keys = set(obj.keys())

        if keys & device_info_keys:  # collected device info
            for k, v in obj.items():
                if k == 'Mac address':
                    merged['device_mac'] = v
                else:
                    merged[k.strip()] = v

        elif keys & reference_info_keys:  # reference device
            for k, v in obj.items():
                if k == 'Mac address':
                    merged['reference_mac'] = v
                else:
                    merged[k.strip()] = v

        elif keys & phone_info_keys:  # collector / phone info
            for k, v in obj.items():
                if k == 'Mac address':
                    merged['phone_version'] = v
                else:
                    merged[k.strip()] = v

        else:
            for k, v in obj.items():
                merged[k.strip()] = v

    return merged


def extract_metadata_from_content(content: str, return_merged: bool = True) -> Any:
    """
    从字符串内容中提取元数据;
    
    Args:
        content: 包含元数据的字符串 (通常是文件头部);
        return_merged: 是否返回合并后的字典;
        
    Returns:
        dict | list: 元数据字典或列表;
    """
    metadata_objects = []
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}')
    buffer, brace_count = '', 0
    
    lines = content.splitlines()

    for line in lines:
        stripped = line.strip()

        # 停止条件: 遇到 "start collecting" 或 日期开头的长行 (表示数据区开始)
        if 'start collecting' in stripped or (len(stripped) > 10 and date_pattern.match(stripped)):
            break

        if not buffer and not stripped.startswith('{'):
            continue

        buffer += line
        brace_count += line.count('{') - line.count('}')

        if brace_count == 0 and buffer.strip():
            clean_str = buffer.replace('\n', ' ').strip()
            repaired_str = repair_json_via_comma_split(clean_str)

            try:
                obj = json.loads(repaired_str)
                metadata_objects.append(obj)
            except json.JSONDecodeError:
                # 忽略解析错误
                pass

            buffer = ''

    return merge_metadata_objects(metadata_objects) if return_merged else metadata_objects


def extract_metadata_from_zstd(file_path: Path, max_bytes: int = 64 * 1024) -> Dict[str, Any]:
    """
    从 ZSTD 文件头部流式解压并提取元数据;
    
    Args:
        file_path: ZSTD 文件路径;
        max_bytes: 读取的最大字节数 (默认 64KB);
        
    Returns:
        dict: 合并后的元数据;
    """
    try:
        dctx = zstd.ZstdDecompressor()
        with open(file_path, 'rb') as f:
            # 仅读取第一块解压流
            with dctx.stream_reader(f) as reader:
                # 读取一部分解压后的数据 (足够覆盖头部元数据)
                # 假设元数据不会超过 64KB
                chunk = reader.read(max_bytes)
                content = chunk.decode('utf-8', errors='ignore')
                return extract_metadata_from_content(content)
                
    except Exception as e:
        print(f"Error extracting metadata from zstd {file_path}: {e}")
        return {}
