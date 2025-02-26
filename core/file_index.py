import os
import json
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

class FileIndex:
    """文件索引管理"""
    
    def __init__(self):
        self.index_dir = Path.home() / ".music_finder" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {}  # 添加内存缓存
        
    def get_index_path(self, root_dir: str) -> Path:
        """获取索引文件路径"""
        # 使用目录路径的哈希作为索引文件名
        import hashlib
        dir_hash = hashlib.md5(root_dir.encode()).hexdigest()
        return self.index_dir / f"{dir_hash}.json"
    
    def save_index(self, root_dir: str, files: List[Dict]) -> None:
        """保存文件索引"""
        try:
            current_time = time.time()
            
            # 过滤掉不存在的文件
            valid_files = []
            for file in files:
                try:
                    if os.path.exists(file['path']):
                        # 不再设置index_time，而是使用文件的实际mtime
                        valid_files.append({
                            'path': file['path'],
                            'size': file['size'],
                            'mtime': os.path.getmtime(file['path']),
                            'exists': True
                        })
                except Exception:
                    continue
            
            if not valid_files:
                logging.warning("没有有效的文件信息可以保存到索引")
                return
                
            index_path = self.get_index_path(root_dir)
            index_data = {
                'root_dir': root_dir,
                'timestamp': current_time,  # 记录索引创建时间
                'files': valid_files
            }
            
            # 先写入临时文件
            temp_path = index_path.with_suffix('.json.tmp')
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
                    
                # 成功写入后替换原文件
                temp_path.replace(index_path)
                logging.info(f"索引文件已保存到: {index_path}")
                logging.info(f"索引包含 {len(valid_files)} 个文件信息")
                
            finally:
                # 清理临时文件
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except:
                        pass
                        
        except Exception as e:
            logging.error(f"保存索引文件失败: {e}")
            # 不要中断程序，继续处理其他任务
    
    def load_index(self, root_dir: str) -> Optional[Tuple[List[Dict], float]]:
        """加载文件索引"""
        index_path = self.get_index_path(root_dir)
        
        if not index_path.exists():
            logging.info("未找到索引文件，将创建新索引")
            return None
            
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 检查索引是否过期
            age_hours = (time.time() - data['timestamp']) / 3600
            if age_hours > 24:
                logging.info(f"索引文件已过期 ({age_hours:.1f}小时)")
                return None
                
            # 验证索引
            valid_files = []
            invalid_files = []
            
            for file in data['files']:
                try:
                    path = file['path']
                    if os.path.exists(path):
                        stat = os.stat(path)
                        if (stat.st_size == file.get('size') and 
                            abs(stat.st_mtime - file.get('mtime', 0)) < 1):
                            valid_files.append(file)
                        else:
                            invalid_files.append(path)
                    else:
                        invalid_files.append(path)
                except Exception as e:
                    logging.debug(f"验证文件失败: {file.get('path', '未知')} - {e}")
                    
            if invalid_files:
                # 只显示前几个无效文件
                sample = invalid_files[:3]
                remaining = len(invalid_files) - 3
                files_str = ", ".join(os.path.basename(f) for f in sample)
                if remaining > 0:
                    files_str += f" 等{remaining}个文件"
                logging.info(f"发现无效文件: {files_str}")
                
                # 更新索引文件，移除无效文件
                self.save_index(root_dir, valid_files)
                
            if not valid_files:
                logging.info("索引中没有有效文件")
                return None
                
            logging.info(f"索引验证完成: {len(valid_files)} 个有效, {len(invalid_files)} 个无效")
            
            return valid_files, data['timestamp']
            
        except Exception as e:
            logging.error(f"加载索引失败: {e}")
            return None
    
    def _quick_verify_index(self, root_dir: str, files: List[Dict]) -> bool:
        """快速验证索引 - 只检查几个关键文件"""
        try:
            # 只验证前几个文件
            sample_size = min(5, len(files))
            valid_count = 0
            
            for file in files[:sample_size]:
                try:
                    path = file['path']
                    if os.path.exists(path):
                        stat = os.stat(path)
                        if (stat.st_size == file.get('size') and 
                            abs(stat.st_mtime - file.get('mtime', 0)) < 1):
                            valid_count += 1
                except:
                    continue
            
            # 如果至少有60%的样本文件有效，就认为索引可用
            return valid_count >= sample_size * 0.6
            
        except Exception:
            return False
    
    def _verify_index(self, root_dir: str, files: List[Dict]) -> bool:
        """验证索引是否有效"""
        # 随机检查几个文件
        import random
        sample_size = min(10, len(files))
        sample_files = random.sample(files, sample_size)
        
        for file in sample_files:
            path = file['path']
            if not os.path.exists(path):
                return False
            
            try:
                stat = os.stat(path)
                if stat.st_mtime != file.get('mtime'):
                    return False
                if stat.st_size != file.get('size'):
                    return False
            except:
                return False
        
        return True
    
    def remove_index(self, root_dir: str) -> None:
        """删除索引"""
        index_path = self.get_index_path(root_dir)
        if index_path.exists():
            index_path.unlink() 