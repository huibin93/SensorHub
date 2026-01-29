import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
from tqdm import tqdm
import time



# --------------------------

def download_file(url, filepath):
    """
    从给定的 URL 下载文件,并保存到指定的路径。
    此函数支持大文件,并显示一个下载进度条。
    """
    try:
        # 使用流式请求
        response = requests.get(url, stream=True, timeout=30)
        # 如果服务器返回错误状态码 (如 404), 则抛出异常
        response.raise_for_status()

        # 从响应头获取文件总大小,用于进度条
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 KB

        # 创建并配置 tqdm 进度条
        progress_bar = tqdm(
            total=total_size, 
            unit='iB', 
            unit_scale=True, 
            desc=os.path.basename(filepath)
        )

        # 以二进制写入模式 ('wb') 打开文件
        with open(filepath, 'wb') as f:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                f.write(data)
        
        progress_bar.close()

        # 校验下载的文件大小是否完整
        if total_size != 0 and progress_bar.n != total_size:
            print(f"  [错误] 文件 {os.path.basename(filepath)} 下载不完整,请重试。")
            return False
        
        print(f"  [成功] 文件已保存至: {filepath}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"  [错误] 下载失败 {url}。原因: {e}")
        # 如果下载出错,删除不完整的文件
        if os.path.exists(filepath):
            os.remove(filepath)
        return False

def main():
    """
    主函数,执行整个下载和分类流程。
    """
    # 记录开始时间
    start_time = time.time()
    
    # 确保根下载目录存在
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    print(f"开始从 {BASE_URL} 获取文件列表...")
    
    try:
        # 1. 获取网页内容
        response = requests.get(BASE_URL)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"无法访问网页。请检查 BASE_URL 是否正确以及服务器是否正在运行。错误: {e}")
        return

    # 2. 解析 HTML 并找到所有链接
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=True)  # 找到所有带 href 属性的 <a> 标签
    
    if not links:
        print("在页面上没有找到任何链接。")
        return

    print(f"发现 {len(links)} 个链接。开始处理...")

    # 3. 遍历所有链接
    for link in links:
        relative_url = link['href']
        
        # 只处理包含 "download?file=" 的链接
        if 'download?file=' not in relative_url:
            continue
            
        # 从链接中提取文件名 (并进行 URL 解码以处理中文字符)
        try:
            filename = unquote(relative_url.split('file=')[-1])
        except IndexError:
            continue

        print(f"\n正在处理文件: {filename}")

        # 4. 从文件名中解析日期 (YYYYMMDD)
        # 正则表达式 `_(\d{8})_` 会查找被下划线 `_` 包围的8位数字
        match = re.search(r'_(\d{8})_', filename)
        if not match:
            print(f"  [警告] 在文件名中未找到 YYYYMMDD 格式的日期,跳过此文件。")
            continue
        
        date_str = match.group(1) # 获取匹配到的日期字符串, 如 '20231128'
        
        # 5. 创建日期文件夹
        target_folder = os.path.join(DOWNLOAD_DIR, date_str)
        os.makedirs(target_folder, exist_ok=True)
        
        # 定义最终要保存的文件路径
        local_filepath = os.path.join(target_folder, filename)

        # 如果文件已存在,则跳过下载
        if os.path.exists(local_filepath):
            print(f"  [提示] 文件已存在,跳过下载。")
            continue
            
        # 拼接成完整的下载 URL
        full_download_url = urljoin(BASE_URL, relative_url)
        
        # 6. 下载文件
        download_file(full_download_url, local_filepath)

    # 计算总用时
    end_time = time.time()
    total_time = end_time - start_time
    
    # 格式化总用时显示
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)
    seconds = int(total_time % 60)
    
    if hours > 0:
        time_str = f"{hours}小时{minutes}分钟{seconds}秒"
    elif minutes > 0:
        time_str = f"{minutes}分钟{seconds}秒"
    else:
        time_str = f"{seconds}秒"

    print(f"\n所有任务处理完毕！总用时: {time_str}")
    print(f"详细用时: {total_time:.2f}秒")

# 脚本的入口点
if __name__ == "__main__":
    # --- 您需要配置的参数 ---

    # 1. 服务器的基础 URL (请替换成您服务器的实际 IP 地址和端口)
    BASE_URL = "http://192.168.50.168:8080" 

    # 2. 本地用于存储下载文件的根目录名称
    DOWNLOAD_DIR = r"G:\python\rawdata_downloads251222"

    main()