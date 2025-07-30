"""
优化版Python请求库
基于urllib.request的改进版本，提供更好的性能和错误处理
"""

import base64
import bisect
import email
import hashlib
import http.client
import io
import os
import posixpath
import re
import socket
import string
import sys
import time
import tempfile
import contextlib
import warnings
import logging
from typing import Optional, Dict, Any, Union, Tuple
from urllib.parse import urlparse, urlunparse, urljoin, quote
from urllib.error import URLError, HTTPError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局配置
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
DEFAULT_USER_AGENT = "Python-urllib/3.9"

class OptimizedRequest:
    """
    优化的请求类，提供更好的性能和错误处理
    """
    
    def __init__(self, url: str, data: Optional[bytes] = None, 
                 headers: Optional[Dict[str, str]] = None,
                 method: Optional[str] = None,
                 timeout: Optional[int] = None,
                 retries: int = DEFAULT_RETRIES):
        self.url = url
        self.data = data
        self.headers = headers or {}
        self.method = method or ('POST' if data else 'GET')
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.retries = retries
        self._parsed_url = None
        
        # 设置默认User-Agent
        if 'User-Agent' not in self.headers:
            self.headers['User-Agent'] = DEFAULT_USER_AGENT
    
    @property
    def parsed_url(self):
        """缓存解析的URL"""
        if self._parsed_url is None:
            self._parsed_url = urlparse(self.url)
        return self._parsed_url
    
    def get_method(self) -> str:
        """获取HTTP方法"""
        return self.method
    
    def get_full_url(self) -> str:
        """获取完整URL"""
        return self.url
    
    def add_header(self, key: str, value: str):
        """添加请求头"""
        self.headers[key] = value
    
    def has_header(self, header_name: str) -> bool:
        """检查是否有指定请求头"""
        return header_name.lower() in {k.lower(): v for k, v in self.headers.items()}
    
    def get_header(self, header_name: str, default: Optional[str] = None) -> Optional[str]:
        """获取请求头值"""
        return self.headers.get(header_name, default)

class OptimizedHTTPHandler:
    """
    优化的HTTP处理器，提供连接池和重试机制
    """
    
    def __init__(self, debuglevel: int = 0, 
                 connection_pool_size: int = 10,
                 max_retries: int = DEFAULT_RETRIES):
        self.debuglevel = debuglevel
        self.connection_pool_size = connection_pool_size
        self.max_retries = max_retries
        self._connection_pool = {}
        self._pool_lock = contextlib.nullcontext()  # 简化版本，实际应使用threading.Lock
    
    def _get_connection(self, host: str, port: int, is_https: bool = False) -> http.client.HTTPConnection:
        """获取连接（从连接池或创建新连接）"""
        key = f"{host}:{port}:{is_https}"
        
        with self._pool_lock:
            if key in self._connection_pool:
                conn = self._connection_pool[key]
                try:
                    # 测试连接是否仍然有效
                    conn.request('HEAD', '/', headers={'Connection': 'keep-alive'})
                    return conn
                except (socket.error, http.client.HTTPException):
                    # 连接已断开，从池中移除
                    del self._connection_pool[key]
            
            # 创建新连接
            if is_https:
                import ssl
                context = ssl.create_default_context()
                conn = http.client.HTTPSConnection(host, port, timeout=self.timeout, context=context)
            else:
                conn = http.client.HTTPConnection(host, port, timeout=self.timeout)
            
            # 添加到连接池
            if len(self._connection_pool) < self.connection_pool_size:
                self._connection_pool[key] = conn
            
            return conn
    
    def _make_request(self, req: OptimizedRequest) -> http.client.HTTPResponse:
        """执行HTTP请求"""
        parsed_url = req.parsed_url
        host = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
        path = parsed_url.path or '/'
        
        if parsed_url.query:
            path += '?' + parsed_url.query
        
        # 准备请求头
        headers = req.headers.copy()
        if req.data:
            headers['Content-Length'] = str(len(req.data))
        
        # 重试机制
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                conn = self._get_connection(host, port, parsed_url.scheme == 'https')
                conn.request(req.method, path, body=req.data, headers=headers)
                response = conn.getresponse()
                
                # 检查响应状态
                if response.status >= 400:
                    raise HTTPError(req.url, response.status, response.reason, response.headers, response)
                
                return response
                
            except (socket.error, http.client.HTTPException, HTTPError) as e:
                last_exception = e
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                else:
                    break
        
        # 所有重试都失败了
        if isinstance(last_exception, HTTPError):
            raise last_exception
        else:
            raise URLError(f"无法连接到 {req.url}: {last_exception}")

class OptimizedOpenerDirector:
    """
    优化的URL打开器，提供更好的错误处理和性能
    """
    
    def __init__(self):
        self.handlers = []
        self._default_handlers = []
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """设置默认处理器"""
        self.add_handler(OptimizedHTTPHandler())
        # 可以添加更多默认处理器，如HTTPS、FTP等
    
    def add_handler(self, handler):
        """添加处理器"""
        self.handlers.append(handler)
    
    def open(self, url: Union[str, OptimizedRequest], 
             data: Optional[bytes] = None,
             timeout: Optional[int] = None) -> http.client.HTTPResponse:
        """打开URL"""
        if isinstance(url, str):
            req = OptimizedRequest(url, data, timeout=timeout)
        else:
            req = url
            if data is not None:
                req.data = data
            if timeout is not None:
                req.timeout = timeout
        
        # 查找合适的处理器
        for handler in self.handlers:
            if hasattr(handler, 'http_open'):
                try:
                    return handler.http_open(req)
                except Exception as e:
                    logger.error(f"处理器 {handler.__class__.__name__} 失败: {e}")
                    continue
        
        raise URLError(f"没有找到合适的处理器来处理 {req.url}")

def urlopen(url: str, data: Optional[bytes] = None, 
            timeout: Optional[int] = None,
            retries: int = DEFAULT_RETRIES) -> http.client.HTTPResponse:
    """
    优化的urlopen函数
    
    Args:
        url: 要打开的URL
        data: POST数据
        timeout: 超时时间（秒）
        retries: 重试次数
    
    Returns:
        HTTPResponse对象
    
    Raises:
        URLError: 网络错误
        HTTPError: HTTP错误
    """
    opener = OptimizedOpenerDirector()
    req = OptimizedRequest(url, data, timeout=timeout, retries=retries)
    return opener.open(req)

def urlretrieve(url: str, filename: Optional[str] = None,
                reporthook: Optional[callable] = None,
                data: Optional[bytes] = None) -> Tuple[str, http.client.HTTPMessage]:
    """
    下载文件到本地
    
    Args:
        url: 要下载的URL
        filename: 本地文件名，如果为None则自动生成
        reporthook: 进度回调函数
        data: POST数据
    
    Returns:
        (filename, headers) 元组
    """
    if filename is None:
        filename = tempfile.mktemp()
    
    response = urlopen(url, data)
    
    with open(filename, 'wb') as f:
        total_size = int(response.headers.get('Content-Length', 0))
        downloaded = 0
        
        while True:
            chunk = response.read(8192)
            if not chunk:
                break
            
            f.write(chunk)
            downloaded += len(chunk)
            
            if reporthook and total_size > 0:
                reporthook(downloaded, total_size, downloaded / total_size)
    
    return filename, response.headers

class OptimizedHTTPBasicAuthHandler:
    """
    优化的HTTP基本认证处理器
    """
    
    def __init__(self, password_mgr=None):
        self.password_mgr = password_mgr or HTTPPasswordMgr()
    
    def http_error_401(self, req, fp, code, msg, headers):
        """处理401认证错误"""
        realm = self._get_realm(headers)
        if realm:
            user, password = self.password_mgr.find_user_password(realm, req.url)
            if user and password:
                auth = base64.b64encode(f"{user}:{password}".encode()).decode()
                req.add_header('Authorization', f'Basic {auth}')
                return self.parent.open(req)
        return None
    
    def _get_realm(self, headers):
        """从响应头中提取realm"""
        auth_header = headers.get('WWW-Authenticate', '')
        match = re.search(r'realm="([^"]*)"', auth_header)
        return match.group(1) if match else None

class HTTPPasswordMgr:
    """密码管理器"""
    
    def __init__(self):
        self.passwords = {}
    
    def add_password(self, realm, uri, user, passwd):
        """添加密码"""
        self.passwords[(realm, uri)] = (user, passwd)
    
    def find_user_password(self, realm, authuri):
        """查找用户名和密码"""
        return self.passwords.get((realm, authuri), (None, None))

# 便捷函数
def build_opener(*handlers):
    """构建URL打开器"""
    opener = OptimizedOpenerDirector()
    for handler in handlers:
        opener.add_handler(handler)
    return opener

def install_opener(opener):
    """安装全局打开器"""
    global _opener
    _opener = opener

# 全局默认打开器
_opener = None

def get_default_opener():
    """获取默认打开器"""
    global _opener
    if _opener is None:
        _opener = OptimizedOpenerDirector()
    return _opener

# 向后兼容的函数
def request_host(request):
    """获取请求主机"""
    return request.parsed_url.hostname

# 导出主要类和函数
__all__ = [
    'OptimizedRequest',
    'OptimizedHTTPHandler', 
    'OptimizedOpenerDirector',
    'OptimizedHTTPBasicAuthHandler',
    'HTTPPasswordMgr',
    'urlopen',
    'urlretrieve',
    'build_opener',
    'install_opener',
    'URLError',
    'HTTPError'
]