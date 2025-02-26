from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                           QLabel, QLineEdit, QComboBox, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal

class SearchDialog(QDialog):
    """搜索对话框"""
    
    search_requested = pyqtSignal(str, str)  # 发出搜索信号(关键词, 过滤类型)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("搜索文件")
        self.setMinimumWidth(300)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 搜索输入框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入搜索关键词")
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # 过滤类型选择
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("过滤方式:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "路径", "大小", "时间"])
        filter_layout.addWidget(self.filter_combo)
        layout.addLayout(filter_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.do_search)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(search_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 绑定回车键
        self.search_edit.returnPressed.connect(self.do_search)
        
    def do_search(self):
        keyword = self.search_edit.text()
        filter_type = self.filter_combo.currentText()
        self.search_requested.emit(keyword, filter_type)
        self.accept() 