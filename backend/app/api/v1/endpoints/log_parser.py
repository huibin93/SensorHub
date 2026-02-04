
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.services.log_parsing_service import parse_wear_check_log

router = APIRouter()

class LogParseRequest(BaseModel):
    content: str

class LogParseResponse(BaseModel):
    data: List[Dict[str, Any]]

@router.post("/wear-check", response_model=LogParseResponse)
def parse_wear_check(request: LogParseRequest):
    """
    Parse wear_check_algo log content.
    Returns structured data.
    """
    try:
        parsed_data = parse_wear_check_log(request.content)
        return LogParseResponse(data=parsed_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
