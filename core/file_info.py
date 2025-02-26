from dataclasses import dataclass
import os
import time
import hashlib
import logging
from typing import Optional, Dict

@dataclass
class FileInfo:
    """文件信息数据类"""
    path: str
    size: str
    mtime: str
    exists: bool = True
    _md5: Optional[str] = None
    _size_bytes: int = 0
    _metadata: Optional[Dict] = None

    # 添加类级缓存
    _metadata_cache = {}
    _md5_cache = {}

    @property
    def md5(self) -> str:
        """懒加载计算MD5"""
        if self._md5 is None and self.exists:
            self._md5 = self._calculate_md5()
        return self._md5

    @property
    def size_bytes(self) -> int:
        """获取文件大小（字节）"""
        return self._size_bytes

    def _calculate_md5(self, chunk_size: int = 8192, max_retries: int = 3) -> str:
        """计算文件MD5值，增加重试机制"""
        retries = 0
        while retries < max_retries:
            try:
                md5_hash = hashlib.md5()
                with open(self.path, "rb", buffering=chunk_size) as f:
                    f.seek(0, os.SEEK_END)
                    file_size = f.tell()
                    f.seek(0)
                    
                    remaining = file_size
                    while remaining > 0:
                        chunk = f.read(min(chunk_size, remaining))
                        if not chunk:
                            break
                        md5_hash.update(chunk)
                        remaining -= len(chunk)
                        
                    return md5_hash.hexdigest()
                    
            except IOError as e:
                retries += 1
                if retries >= max_retries:
                    logging.error(f"计算MD5失败(重试{retries}次): {self.path} - {e}")
                    return ""
                logging.warning(f"计算MD5重试({retries}): {self.path} - {e}")
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"计算MD5意外错误: {self.path} - {e}")
                return ""

    @classmethod
    def from_path(cls, path: str) -> 'FileInfo':
        """从文件路径创建FileInfo对象"""
        try:
            stats = os.stat(path)
            size = f"{stats.st_size / (1024*1024):.2f} MB"
            mtime = time.strftime("%Y-%m-%d %H:%M:%S", 
                                time.localtime(stats.st_mtime))
            return cls(path, size, mtime, True, None, stats.st_size)
        except:
            return cls(path, "N/A", "N/A", False, None, 0)

    @property
    def metadata(self) -> dict:
        """获取音频文件元数据（带缓存）"""
        if self.path in self._metadata_cache:
            return self._metadata_cache[self.path]
            
        if self._metadata is None and self.exists:
            try:
                import mutagen
                self._metadata = mutagen.File(self.path)
                self._metadata_cache[self.path] = self._metadata or {}
            except Exception:
                self._metadata = {}
                
        return self._metadata or {}

    def calculate_md5(self) -> str:
        """计算文件MD5（带缓存）"""
        if self.path in self._md5_cache:
            return self._md5_cache[self.path]
            
        md5_hash = hashlib.md5()
        try:
            with open(self.path, "rb", buffering=8192) as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    md5_hash.update(chunk)
            result = md5_hash.hexdigest()
            self._md5_cache[self.path] = result
            return result
        except Exception as e:
            logging.error(f"计算MD5失败: {self.path} - {e}")
            return "" 