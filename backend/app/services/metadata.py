from typing import Dict, Optional, Any
from sqlmodel import Session, select
from app.core.logger import logger
from app.models.dictionary import TestType, TestSubType

def parse_filename(filename: str) -> Dict[str, Any]:
    """
    从文件名中解析元数据。
    格式: CollectionMode_Label_Tester_Date_Time_MAC.rawdata
    示例: Wear_Wearing_yuyue_20251227_162142_0983.rawdata
    
    鲁棒性:
    - 要求至少有 5 个部分。
    - 处理缺失的 MAC 地址 (返回空字符串)。
    """
    try:
        # Strip extension
        name_part = filename.rsplit('.', 1)[0]
        parts = name_part.split('_')
        
        if len(parts) < 5:
            return {}

        l1 = parts[0]
        l2 = parts[1]
        tester = parts[2]
        date_str = parts[3]
        time_str = parts[4]
        
        # MAC 地址可选/位于最后
        mac = parts[5] if len(parts) > 5 else ""
        
        # Formatting collection_time
        # date: 20251227 -> 2025-12-27 (Stored as string in DB for now based on current model)
        # time: 162142 -> 16:21:42
        # Combined: 20251227_162142 (As per requirement from previous session)
        collection_time = f"{date_str}_{time_str}"
        
        return {
            "test_type_l1": l1,
            "test_type_l2": l2,
            "tester": tester,
            "mac": mac,
            "collection_time": collection_time,
            "deviceType": "Watch" # Default
        }
    except Exception as e:
        logger.error(f"Filename parse error for {filename}: {e}")
        return {}

def ensure_test_types_exist(session: Session, l1: str, l2: str):
    """
    确保字典中存在测试类型 (L1) 和测试子类型 (L2)。
    如果不存在, 则创建它们。
    """
    if not l1: return
    
    # 1. 检查/创建 L1
    tt = session.exec(select(TestType).where(TestType.id == l1)).first()
    if not tt:
        tt = TestType(id=l1, name=l1, description="Auto-created during import")
        session.add(tt)
        try:
            session.commit()
            session.refresh(tt)
            logger.info(f"Auto-created TestType: {l1}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create TestType {l1}: {e}")
            return # Stop if L1 fails

    # 2. 检查/创建 L2
    if not l2: return
    
    existing_l2 = session.exec(select(TestSubType).where(
        TestSubType.test_type_id == l1,
        TestSubType.name == l2
    )).first()
    
    if not existing_l2:
        new_l2 = TestSubType(test_type_id=l1, name=l2)
        session.add(new_l2)
        try:
             session.commit()
             logger.info(f"Auto-created TestSubType: {l2} for {l1}")
        except Exception:
            session.rollback()
