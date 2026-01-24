from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.api import deps
from app.schemas import api_models
from app.models.dictionary import DeviceModel, TestType, TestSubType

router = APIRouter()

@router.get("/devices", response_model=api_models.DevicesResponse)
def get_devices(session: Session = Depends(deps.get_db)):
    models = session.exec(select(DeviceModel)).all()
    
    devices_map = {}
    # Ensure defaults exist in map if desired, or rely on DB seeding
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
def add_device_model(req: api_models.AddDeviceModelRequest, session: Session = Depends(deps.get_db)):
    # Check if exists
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
def get_test_types(session: Session = Depends(deps.get_db)):
    types = session.exec(select(TestType)).all()
    result = []
    
    for t in types:
        sub_types = session.exec(select(TestSubType).where(TestSubType.test_type_id == t.id)).all()
        sub_names = [s.name for s in sub_types]
        if not sub_names: sub_names = ["--"]
        
        result.append({
            "id": t.id,
            "name": t.name,
            "subTypes": sub_names
        })
        
    return {"types": result}

@router.post("/test-types")
def add_test_type(req: api_models.AddTestTypeRequest, session: Session = Depends(deps.get_db)):
    type_id = req.name # Simple ID generation
    if session.get(TestType, type_id):
        raise HTTPException(status_code=400, detail="Type exists")
        
    new_type = TestType(id=type_id, name=req.name)
    session.add(new_type)
    
    # Add default sub-type
    session.add(TestSubType(test_type_id=type_id, name="--"))
    
    session.commit()
    return {"success": True, "testType": {"id": type_id, "name": req.name, "subTypes": ["--"]}}

@router.post("/test-types/{type_id}/sub-types")
def add_sub_type(type_id: str, req: api_models.AddSubTypeRequest, session: Session = Depends(deps.get_db)):
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
