from PyQt5.QtWidgets import (QToolBar, QWidget, QHBoxLayout, 
                           QPushButton, QLabel, QComboBox, 
                           QLineEdit, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt

class ToolbarWidget(QToolBar):
    """工具栏控件"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        # 创建主容器
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        
        # 文件夹选择
        layout.addWidget(QLabel("文件夹:"))
        self.path_edit = QLineEdit()
        layout.addWidget(self.path_edit)
        
        self.browse_button = QPushButton("浏览...")
        layout.addWidget(self.browse_button)
        
        # 查重方式选择
        layout.addWidget(QLabel("查重方式:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "按文件名", # FILENAME
            "按大小",   # SIZE 
            "按MD5",    # MD5
            "混合模式"  # MIXED
        ])
        layout.addWidget(self.method_combo)
        
        # 高级选项
        layout.addWidget(QLabel("最小大小(MB):"))
        self.min_size_spin = QDoubleSpinBox()
        self.min_size_spin.setRange(0, 9999)
        layout.addWidget(self.min_size_spin)
        
        layout.addWidget(QLabel("最大深度:"))
        self.max_depth_spin = QSpinBox()
        self.max_depth_spin.setRange(0, 99)
        self.max_depth_spin.setSpecialValueText("无限制")
        layout.addWidget(self.max_depth_spin)
        
        # 搜索按钮
        self.search_button = QPushButton("开始搜索")
        layout.addWidget(self.search_button)
        
        # 添加到工具栏
        self.addWidget(container) 