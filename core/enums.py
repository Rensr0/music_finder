from enum import Enum, auto

class DuplicateCheckMethod(Enum):
    """查重方式枚举"""
    FILENAME = auto()  # 基于文件名
    SIZE = auto()      # 基于文件大小
    MD5 = auto()       # 基于MD5
    MIXED = auto()     # 混合模式(先大小后MD5) 