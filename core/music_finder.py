import os
import threading
from typing import Dict, List, Tuple, Optional, Callable
from functools import lru_cache
import mimetypes
import re
from collections import defaultdict
import logging
from pathlib import Path
import time
from datetime import datetime

from .file_info import FileInfo
from .enums import DuplicateCheckMethod
from .file_index import FileIndex

class MusicFinder:
    """音乐文件查找器核心"""
    MUSIC_EXTENSIONS = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.ape', '.wma'}

    _file_cache = {}
    _cache_lock = threading.Lock()
    
    @classmethod
    def get_file_info(cls, path: str) -> FileInfo:
        """使用缓存获取文件信息"""
        with cls._cache_lock:
            if path in cls._file_cache:
                return cls._file_cache[path]
            file_info = FileInfo.from_path(path)
            cls._file_cache[path] = file_info
            return file_info

    @classmethod
    def clear_cache(cls):
        """清理缓存"""
        with cls._cache_lock:
            cls._file_cache.clear()

    @staticmethod
    @lru_cache(maxsize=1000)
    def normalize_path(path: str) -> str:
        """标准化网络路径"""
        # 处理网络路径
        if path.startswith(('\\\\', '//')):
            # 确保使用正确的网络路径格式
            path = path.replace('/', '\\')
            if not path.startswith(r'\\'):
                path = r'\\' + path.lstrip('\\/')
        else:
            # 处理本地路径
            path = os.path.normpath(path)
            # 如果是映射的网络驱动器，尝试获取实际的网络路径
            try:
                import win32wnet
                if path[0].isalpha() and path[1] == ':':
                    try:
                        network_path = win32wnet.WNetGetConnection(path[0] + ':')
                        if network_path:
                            path = os.path.join(network_path, path[3:])
                            path = path.replace('/', '\\')
                            logging.info(f"映射驱动器转换为网络路径: {path}")
                    except Exception:
                        pass
            except ImportError:
                pass
        
        return path

    @staticmethod
    def is_music_file(filepath: str) -> bool:
        """改进的音乐文件检测"""
        try:
            # 检查文件是否存在且可访问
            if not os.path.exists(filepath):
                logging.debug(f"文件不存在: {filepath}")
                return False
            
            # 检查是否是文件而不是目录
            if not os.path.isfile(filepath):
                logging.debug(f"不是文件: {filepath}")
                return False
            
            # 获取扩展名
            ext = os.path.splitext(filepath)[1].lower()
            
            # 记录检查过程
            logging.debug(f"检查文件: {filepath} (扩展名: {ext})")
            
            # 首先检查扩展名
            if ext in MusicFinder.MUSIC_EXTENSIONS:
                logging.debug(f"通过扩展名识别为音乐文件: {filepath}")
                return True
            
            # 使用 mimetypes 进行额外检查
            mime_type = mimetypes.guess_type(filepath)[0]
            is_music = mime_type and mime_type.startswith('audio/')
            
            if is_music:
                logging.debug(f"通过MIME类型识别为音乐文件: {filepath} ({mime_type})")
            else:
                logging.debug(f"不是音乐文件: {filepath} ({mime_type})")
            
            return is_music
        except Exception as e:
            logging.warning(f"检查文件类型时出错: {filepath} - {e}")
            return False

    @staticmethod
    def normalize_artist_name(artist: str) -> str:
        """标准化艺术家名称"""
        # 移除特殊字符和多余空格
        artist = re.sub(r'[%\.\s\-_]+', ' ', artist)
        
        # 移除常见的艺术家名称变体和后缀
        remove_patterns = [
            r'邓紫棋$', r'G\.E\.M$',
            r'阿妹$', r'A-Mei$',
            r'feat\..+$', r'ft\..+$',
            r'[\(\（].+[\)\）]$',
            r'翻自.+$', r'cover.+$',
        ]
        
        for pattern in remove_patterns:
            artist = re.sub(pattern, '', artist, flags=re.IGNORECASE)
        
        return artist.strip().lower()

    @staticmethod
    def parse_music_filename(filename: str) -> Tuple[str, str]:
        """解析音乐文件名，返回(标题, 艺术家)"""
        name = os.path.splitext(filename)[0].strip()
        name = re.sub(r'_\d{14}$', '', name)  # 移除时间戳后缀
        
        parts = name.split(' - ', 1)
        if len(parts) == 2:
            title, artist = parts
            # 处理标题中的特殊标记
            title_patterns = [
                r'\(Live\)$', r'\(Remix\)$',
                r'\(Cover\)$', r'\(DJ版\)$',
                r'\(纯音乐\)$', r'\(伴奏\)$',
                r'\(片段\)$', r'\(Demo\)$',
            ]
            
            for pattern in title_patterns:
                title = re.sub(pattern, '', title, flags=re.IGNORECASE)
            
            return title.strip(), MusicFinder.normalize_artist_name(artist)
        
        return name, ""

    @classmethod
    def find_duplicates(cls, root_dir: str, method: DuplicateCheckMethod, 
                       callback: Optional[Callable] = None,
                       max_depth: int = 0,
                       min_size_mb: float = 0) -> Tuple[Dict[str, List[FileInfo]], int]:
        """查找重复文件"""
        root_dir = cls.normalize_path(root_dir)
        logging.info(f"开始查找重复文件 - 目录: {root_dir}")
        
        file_index = FileIndex()
        index_result = file_index.load_index(root_dir)
        known_files = set()
        all_files = []
        
        # 创建目录修改时间缓存
        dir_mtime_cache = {}
        
        def get_dir_mtime(dir_path: str) -> float:
            """获取目录的最后修改时间"""
            if dir_path in dir_mtime_cache:
                return dir_mtime_cache[dir_path]
            try:
                mtime = os.path.getmtime(dir_path)
                dir_mtime_cache[dir_path] = mtime
                return mtime
            except:
                return 0
        
        if index_result:
            indexed_files, index_time = index_result
            logging.info("使用缓存的文件索引")
            if callback:
                callback("使用缓存索引加速搜索...", 10)
            
            # 使用更友好的时间格式
            index_time_str = datetime.fromtimestamp(index_time).strftime('%Y-%m-%d %H:%M:%S')
            logging.info(f"索引创建时间: {index_time_str}")
            
            # 添加进度信息
            total_files = len(indexed_files)
            processed = 0
            
            for f in indexed_files:
                try:
                    path = f['path']
                    dir_path = os.path.dirname(path)
                    
                    # 使用相对路径显示
                    rel_path = os.path.relpath(dir_path, root_dir)
                    
                    file_mtime = f.get('mtime', 0)
                    dir_mtime = get_dir_mtime(dir_path)
                    
                    if dir_mtime > file_mtime:
                        # 使用更简洁的日志格式
                        logging.debug(f"目录已更新: {rel_path}")
                        continue
                        
                    processed += 1
                    if processed % 100 == 0:  # 每处理100个文件显示一次进度
                        progress = (processed / total_files) * 100
                        logging.info(f"处理进度: {progress:.1f}% ({processed}/{total_files})")
                        
                    file_info = FileInfo.from_path(path)
                    if file_info.exists:
                        all_files.append(file_info)
                        known_files.add(path)
                except Exception as e:
                    logging.warning(f"处理文件失败: {os.path.basename(path)} - {e}")
                    
            logging.info(f"从索引加载完成: {len(all_files)}/{total_files} 个文件有效")
        
        # 扫描目录查找新文件
        logging.info("开始扫描目录查找新文件...")
        if callback:
            callback("扫描目录查找新文件...", 20)
        
        min_size_bytes = min_size_mb * 1024 * 1024
        new_files_count = 0
        
        def should_scan_dir(dir_path: str, has_index: bool) -> bool:
            """判断是否需要扫描该目录"""
            if not has_index:
                return True
                
            try:
                # 检查当前目录
                current_mtime = get_dir_mtime(dir_path)
                if current_mtime > index_time:
                    return True
                    
                # 检查父目录
                parent = os.path.dirname(dir_path)
                if parent and parent.startswith(root_dir):
                    parent_mtime = get_dir_mtime(parent)
                    if parent_mtime > index_time:
                        return True
                        
                return False
            except:
                return True
        
        for root, dirs, files in os.walk(root_dir):
            # 检查是否需要扫描此目录
            if not should_scan_dir(root, index_result is not None):  # 传入是否有索引的标志
                logging.debug(f"跳过未修改的目录: {root}")
                # 如果父目录未修改，可以跳过所有子目录
                dirs.clear()  # 这会阻止os.walk继续遍历子目录
                continue
            
            if max_depth > 0:
                rel_path = os.path.relpath(root, root_dir)
                current_depth = len(Path(rel_path).parts)
                if rel_path != '.' and current_depth > max_depth:
                    dirs.clear()  # 超过最大深度，不再遍历子目录
                    continue
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # 跳过已知文件
                if file_path in known_files:
                    continue
                
                try:
                    # 快速检查扩展名
                    if not os.path.splitext(file_path)[1].lower() in cls.MUSIC_EXTENSIONS:
                        continue
                    
                    # 检查文件大小
                    try:
                        size = os.path.getsize(file_path)
                        if size < min_size_bytes:
                            continue
                    except:
                        continue
                    
                    file_info = FileInfo.from_path(file_path)
                    if file_info.exists:
                        all_files.append(file_info)
                        new_files_count += 1
                        
                        if callback and new_files_count % 10 == 0:
                            callback(f"找到 {new_files_count} 个新文件...", 30)
                        
                except Exception as e:
                    logging.warning(f"处理文件失败: {file_path} - {e}")
        
        total_files = len(all_files)
        logging.info(f"总共找到 {total_files} 个文件 (新增: {new_files_count})")
        
        # 扫描完成后，保存新的索引
        if new_files_count > 0 or (index_result and len(all_files) != len(indexed_files)):
            logging.info("更新文件索引...")
            index_data = []
            for file_info in all_files:
                try:
                    if os.path.exists(file_info.path):
                        index_data.append({
                            'path': file_info.path,
                            'size': file_info.size_bytes,
                            'mtime': os.path.getmtime(file_info.path),
                            'exists': True
                        })
                except Exception as e:
                    logging.debug(f"准备索引数据时出错: {file_info.path} - {e}")
                    continue
                
            if index_data:
                file_index.save_index(root_dir, index_data)
        
        # 继续处理重复文件检查
        logging.info(f"开始处理 {len(all_files)} 个文件...")
        if callback:
            callback(f"开始查找重复文件...", 40)
        
        # 根据不同方法处理重复文件
        duplicates: Dict[str, List[FileInfo]] = {}
        
        try:
            if method == DuplicateCheckMethod.SIZE:
                logging.info("开始按大小分组...")
                # 按大小分组
                size_groups = defaultdict(list)
                for file_info in all_files:
                    if callback:
                        callback(f"正在按大小分组: {file_info.path}", 50)
                    size_groups[file_info.size_bytes].append(file_info)
                
                # 找出重复的大小组
                for size, files in size_groups.items():
                    if len(files) > 1:
                        duplicates[f"大小: {files[0].size}"] = files
                        
            elif method == DuplicateCheckMethod.MD5:
                logging.info("开始计算MD5...")
                # 计算MD5
                total = len(all_files)
                for i, file_info in enumerate(all_files, 1):
                    if callback:
                        progress = (i / total) * 100
                        callback(f"正在计算MD5 ({i}/{total}): {file_info.path}", progress)
                        
                # 按MD5分组
                md5_groups = defaultdict(list)
                for file_info in all_files:
                    md5 = file_info.md5
                    if md5:  # 只添加成功计算MD5的文件
                        md5_groups[md5].append(file_info)
                
                # 找出重复的MD5组
                for md5, files in md5_groups.items():
                    if len(files) > 1:
                        duplicates[f"MD5: {md5[:8]}..."] = files
                        
            elif method == DuplicateCheckMethod.MIXED:
                logging.info("开始混合模式查重...")
                # 先按大小分组
                size_groups = defaultdict(list)
                for file_info in all_files:
                    size_groups[file_info.size_bytes].append(file_info)
                
                # 对相同大小的文件计算MD5
                for size, files in size_groups.items():
                    if len(files) > 1:
                        md5_groups = defaultdict(list)
                        for file_info in files:
                            md5 = file_info.md5
                            if md5:
                                md5_groups[md5].append(file_info)
                        
                        for md5, md5_files in md5_groups.items():
                            if len(md5_files) > 1:
                                duplicates[f"大小: {md5_files[0].size}, MD5: {md5[:8]}..."] = md5_files
                                
            elif method == DuplicateCheckMethod.FILENAME:
                logging.info("开始按文件名分组...")
                # 按文件名分组
                name_groups = defaultdict(list)
                for file_info in all_files:
                    title, artist = cls.parse_music_filename(os.path.basename(file_info.path))
                    key = f"{title}|{artist}" if artist else title
                    name_groups[key].append(file_info)
                
                # 找出重复的文件名组
                for name_key, files in name_groups.items():
                    if len(files) > 1:
                        title = name_key.split('|')[0]
                        duplicates[f"歌曲: {title} ({len(files)}个版本)"] = files
                        
            logging.info(f"查重完成 - 找到 {len(duplicates)} 组重复文件")
            if callback:
                callback(f"扫描完成，找到 {len(duplicates)} 组重复文件", 100)
            
        except Exception as e:
            logging.error(f"处理重复文件时出错: {e}", exc_info=True)
            if callback:
                callback(f"处理出错: {e}", 0)
            return {}, len(all_files)

        return duplicates, len(all_files)

    # ... [其他方法保持不变，从原代码复制] ... 