"""
设备相关 API 端点模块;

本模块提供连接设备、获取文件列表以及下载设备文件的功能;
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import re
from sqlmodel import Session

# 修复: 导入特定异常
from requests.exceptions import RequestException

from app.api import deps
from app.schemas import api_models
from app.crud import file as crud
from app.core.logger import logger
from app.services.device_import import download_manager

router = APIRouter()

@router.get("/devices/list", response_model=api_models.DeviceFilesResponse)
def list_device_files(
    url: str = Query(..., description="Device base URL"),
    session: Session = Depends(deps.get_db)
) -> api_models.DeviceFilesResponse:
    """
    连接设备并获取文件列表;
    
    Args:
        url: 设备的基础 URL (e.g. http://192.168.1.100:8080);
        
    Returns:
        DeviceFilesResponse: 包含文件列表和状态;
    """
    logger.info(f"Connecting to device at {url}...")
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except RequestException as e:
        logger.error(f"Failed to connect to device: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to connect: {str(e)}")
        
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=True)
    
    device_files: List[api_models.DeviceFile] = []
    
    for link in links:
        relative_url = link['href']
        
        # 过滤逻辑 (与脚本相同)
        if 'download?file=' not in relative_url:
            continue
            
        try:
            filename = unquote(relative_url.split('file=')[-1])
        except IndexError:
            continue
            
        # 解析逻辑
        full_url = urljoin(url, relative_url)
        
        # 检查数据库状态
        # 注意: 我们仅通过文件名检查, 因为我们还没有哈希值
        # 如果用户重新上传同名文件, 后端会处理重命名后缀, 但这里我们只想知道 "具有此名称的文件" 是否已上传.
        # 理想情况下, 我们应该检查精确匹配, 但在没有哈希的情况下, 名称匹配是最好的提示.
        
        # 检查文件名是否大致符合 "已上传" 模式
        # crud 方法 `get_file_by_name_and_size` 进行严格检查.
        # 如果我们有大小/哈希, 我们可以在 CRUD 中实现更简单的检查或重用精确匹配逻辑.
        # 目前, 我们只检查是否存在具有此名称的任何文件. 
        # 但等等, 现有的 crud 不具有 "get_any_file_by_filename".
        # 让我们添加一个快速助手或直接迭代. 
        # 实际上 `crud.get_files(search=filename)` 处理部分匹配.
        
        # 让我们为了效率使用直接查询, 或稍后添加到 CRUD.
        # 目前, 我们假设如果找到具有精确名称的文件, 则它已上传.
        
        # 由于目前无法在不进行上下文切换的情况下修改 crud, 因此让我们使用带有搜索功能的 get_files.
        # 但严格检查更好. 让我们做一个简单的检查.
        # 我们可以假设如果不存在文件, `crud.get_next_naming_suffix(session, filename)` 返回 ""?
        # 不, 那会返回下一个后缀.
        
        # 让我们查询 crud.listing
        # 优化: 如果出现性能问题, 稍后进行批量检查.
        matches, _ = crud.get_files(session, limit=1, search=filename)
        is_uploaded = False
        
        # 如果搜索找到了内容, 验证精确的文件名匹配 (因为搜索是部分匹配)
        db_size = "Unknown"
        for m in matches:
            if m.filename == filename:
                is_uploaded = True
                db_size = m.size
                break
                
        # 解析日期
        date_str = None
        match = re.search(r'_(\d{8})_', filename)
        if match:
            date_str = match.group(1)
            
        device_files.append(api_models.DeviceFile(
            filename=filename,
            url=full_url,
            size=db_size if is_uploaded else "Unknown", # 如果已上传则使用数据库存储的大小
            date=date_str,
            is_uploaded=is_uploaded
        ))
        
    return api_models.DeviceFilesResponse(items=device_files, total=len(device_files))


from app.services.device_import import download_manager


@router.post("/devices/import")
def import_device_files(
    request: api_models.DeviceDownloadRequest,
    # background_tasks: BackgroundTasks, # 已弃用, 改用线程池
    session: Session = Depends(deps.get_db)
) -> dict:
    download_manager.reset_cancel()
    
    count = 0
    for file in request.files:
        if not file.url.startswith("http"):
             file.url = urljoin(request.device_ip, "download?file=" + file.filename)
        
        download_manager.start_download(file.url, file.filename)
        count += 1
        
    return {"message": f"Queued {count} files for download.", "count": count}

@router.post("/devices/stop")
def stop_import() -> dict:
    """停止所有下载任务"""
    download_manager.stop_all()
    return {"message": "Stop signal sent."}

@router.get("/devices/tasks")
def get_device_tasks() -> dict:
    """获取当前任务状态"""
    return download_manager.get_tasks()

