from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QComboBox, QCheckBox, QLineEdit, QPushButton,
                           QGroupBox, QRadioButton, QSpinBox, QTextEdit)
from PyQt5.QtCore import Qt

class DuplicateSettingsDialog(QDialog):
    """重复文件处理设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("重复文件处理设置")
        self.setMinimumWidth(400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 文件格式优先级
        format_group = QGroupBox("文件格式优先级")
        format_layout = QVBoxLayout()
        self.format_priority = []
        formats = ['.flac', '.wav', '.ape', '.mp3', '.m4a', '.ogg', '.wma']
        for fmt in formats:
            combo = QComboBox()
            combo.addItems([str(i) for i in range(1, len(formats) + 1)])
            hlayout = QHBoxLayout()
            hlayout.addWidget(QLabel(fmt))
            hlayout.addWidget(combo)
            format_layout.addLayout(hlayout)
            self.format_priority.append((fmt, combo))
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # 文件大小选择
        size_group = QGroupBox("文件大小选择")
        size_layout = QVBoxLayout()
        self.size_prefer = QComboBox()
        self.size_prefer.addItems(["保留大文件", "保留小文件"])
        size_layout.addWidget(self.size_prefer)
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # 优先删除目录
        delete_dir_group = QGroupBox("优先删除目录")
        delete_dir_layout = QVBoxLayout()
        self.delete_dirs = QTextEdit()
        self.delete_dirs.setPlaceholderText("输入要优先删除的目录，每行一个\n例如：\nDownloads\n临时文件夹")
        self.delete_dirs.setMaximumHeight(100)
        delete_dir_layout.addWidget(self.delete_dirs)
        delete_dir_group.setLayout(delete_dir_layout)
        layout.addWidget(delete_dir_group)
        
        # 排除目录
        exclude_group = QGroupBox("排除目录")
        exclude_layout = QVBoxLayout()
        self.exclude_dirs = QLineEdit()
        self.exclude_dirs.setPlaceholderText("输入要排除的目录，用分号分隔")
        exclude_layout.addWidget(self.exclude_dirs)
        exclude_group.setLayout(exclude_layout)
        layout.addWidget(exclude_group)
        
        # 其他选项
        options_group = QGroupBox("其他选项")
        options_layout = QVBoxLayout()
        
        self.keep_oldest = QCheckBox("优先保留最早的文件")
        options_layout.addWidget(self.keep_oldest)
        
        self.skip_different_names = QCheckBox("跳过文件名不完全相同的文件")
        options_layout.addWidget(self.skip_different_names)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
    def get_settings(self) -> dict:
        """获取设置"""
        return {
            'format_priority': {fmt: int(combo.currentText()) 
                              for fmt, combo in self.format_priority},
            'prefer_larger': self.size_prefer.currentText() == "保留大文件",
            'exclude_dirs': [d.strip() for d in self.exclude_dirs.text().split(';') if d.strip()],
            'delete_dirs': [d.strip() for d in self.delete_dirs.toPlainText().splitlines() if d.strip()],
            'keep_oldest': self.keep_oldest.isChecked(),
            'skip_different_names': self.skip_different_names.isChecked()
        } 