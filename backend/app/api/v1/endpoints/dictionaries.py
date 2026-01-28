"""
字典相关 API 端点模块;

本模块提供设备型号和测试类型字典的查询和管理 API;
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.api import deps
from app.schemas import api_models
from app.models.dictionary import DeviceModel, TestType, TestSubType

router = APIRouter()


@router.get("/devices", response_model=api_models.DevicesResponse)
def get_devices(session: Session = Depends(deps.get_db)) -> api_models.DevicesResponse:
    """
    获取所有设备型号列表;

    Returns:
        DevicesResponse: 按设备类型分组的型号列表;
    """
    models = session.exec(select(DeviceModel)).all()

    devices_map = {}
    # 确保默认类型存在
    default_types = ["Watch", "Ring"]
    for t in default_types:
        devices_map[t] = []

    for m in models:
        if m.device_type not in devices_map:
            devices_map[m.device_type] = []
        if m.model_name not in devices_map[m.device_type]:
            devices_map[m.device_type].append(m.model_name)

    result = [{"type": k, "models": v} for k, v in devices_map.items()]
    return {"devices": result}


@router.post("/devices/models")
def add_device_model(
    req: api_models.AddDeviceModelRequest,
    session: Session = Depends(deps.get_db)
) -> dict:
    """
    添加新设备型号;

    Args:
        req: 包含设备类型和型号名称;

    Returns:
        dict: 添加结果;

    Raises:
        HTTPException: 型号已存在时抛出 400 错误;
    """
    # 检查是否已存在
    existing = session.exec(select(DeviceModel).where(
        DeviceModel.device_type == req.deviceType,
        DeviceModel.model_name == req.modelName
    )).first()

    if existing:
        raise HTTPException(status_code=400, detail="Model already exists")

    model = DeviceModel(device_type=req.deviceType, model_name=req.modelName)
    session.add(model)
    session.commit()
    return {"success": True, "message": f"Added {req.modelName}"}


@router.get("/test-types", response_model=api_models.TestTypesResponse)
def get_test_types(session: Session = Depends(deps.get_db)) -> api_models.TestTypesResponse:
    """
    获取所有测试类型列表;

    Returns:
        TestTypesResponse: 包含主类型和子类型的列表;
    """
    types = session.exec(select(TestType)).all()
    result = []

    for t in types:
        sub_types = session.exec(
            select(TestSubType).where(TestSubType.test_type_id == t.id)
        ).all()
        sub_names = [s.name for s in sub_types]
        if not sub_names:
            sub_names = ["--"]

        result.append({
            "id": t.id,
            "name": t.name,
            "subTypes": sub_names
        })

    return {"types": result}


@router.post("/test-types")
def add_test_type(
    req: api_models.AddTestTypeRequest,
    session: Session = Depends(deps.get_db)
) -> dict:
    """
    添加新测试类型;

    Args:
        req: 包含测试类型名称;

    Returns:
        dict: 添加结果,包含新创建的测试类型信息;

    Raises:
        HTTPException: 类型已存在时抛出 400 错误;
    """
    type_id = req.name  # 简单的 ID 生成
    if session.get(TestType, type_id):
        raise HTTPException(status_code=400, detail="Type exists")

    new_type = TestType(id=type_id, name=req.name)
    session.add(new_type)

    # 添加默认子类型
    session.add(TestSubType(test_type_id=type_id, name="--"))

    session.commit()
    return {"success": True, "testType": {"id": type_id, "name": req.name, "subTypes": ["--"]}}


@router.post("/test-types/{type_id}/sub-types")
def add_sub_type(
    type_id: str,
    req: api_models.AddSubTypeRequest,
    session: Session = Depends(deps.get_db)
) -> dict:
    """
    添加测试子类型;

    Args:
        type_id: 父测试类型 ID;
        req: 包含子类型名称;

    Returns:
        dict: 添加结果;

    Raises:
        HTTPException: 父类型不存在时抛出 404 错误,子类型已存在时抛出 400 错误;
    """
    if not session.get(TestType, type_id):
        raise HTTPException(status_code=404, detail="Type not found")

    existing = session.exec(select(TestSubType).where(
        TestSubType.test_type_id == type_id,
        TestSubType.name == req.name
    )).first()

    if existing:
        raise HTTPException(status_code=400, detail="Sub-type exists")

    session.add(TestSubType(test_type_id=type_id, name=req.name))
    session.commit()
    return {"success": True, "message": "Added"}
