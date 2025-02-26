from PyQt5.QtWidgets import QStatusBar, QProgressBar, QLabel
from PyQt5.QtCore import Qt

class StatusBarWidget(QStatusBar):
    """状态栏控件"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        # 状态信息标签
        self.message_label = QLabel()
        self.addWidget(self.message_label, 1)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        self.addPermanentWidget(self.progress_bar)
        
        # 默认隐藏进度条
        self.progress_bar.hide()
        
    def update_progress(self, message: str, progress: float):
        """更新进度信息"""
        self.message_label.setText(message)
        self.progress_bar.show()
        self.progress_bar.setValue(int(progress))
        
    def show_message(self, message: str):
        """显示状态信息"""
        self.message_label.setText(message)
        self.progress_bar.hide()
        
    def show_error(self, error: str):
        """显示错误信息"""
        self.message_label.setText(f"错误: {error}")
        self.progress_bar.hide() 