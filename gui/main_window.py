from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, 
                           QComboBox, QProgressBar, QFileDialog, QMenu, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os
import logging

from ..core.enums import DuplicateCheckMethod
from ..core.music_finder import MusicFinder
from .widgets.file_tree import FileTreeWidget
from .widgets.status_bar import StatusBarWidget
from .widgets.toolbar import ToolbarWidget
from ..config.settings import Settings
from .search_dialog import SearchDialog

class SearchWorker(QThread):
    """搜索线程"""
    progress = pyqtSignal(str, float)
    finished = pyqtSignal(dict, int)
    error = pyqtSignal(str)

    def __init__(self, directory: str, method: DuplicateCheckMethod):
        super().__init__()
        self.directory = directory
        self.method = method

    def run(self):
        try:
            results, total = MusicFinder.find_duplicates(
                self.directory,
                self.method,
                callback=lambda msg, prog: self.progress.emit(msg, prog)
            )
            self.finished.emit(results, total)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("音乐文件查重工具")
        self.setMinimumSize(1200, 800)
        
        self.settings = Settings()
        
        self.init_ui()
        self.setup_connections()
        
        # 加载配置
        self.load_settings()
        
    def init_ui(self):
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QVBoxLayout(central_widget)
        
        # 添加工具栏
        self.toolbar = ToolbarWidget()
        self.addToolBar(self.toolbar)
        
        # 添加文件树
        self.file_tree = FileTreeWidget()
        layout.addWidget(self.file_tree)
        
        # 添加状态栏
        self.status_bar = StatusBarWidget()
        self.setStatusBar(self.status_bar)
        
    def load_settings(self):
        """加载配置"""
        # 恢复上次的目录
        last_dir = self.settings.get("last_directory")
        if last_dir and os.path.exists(last_dir):
            self.toolbar.path_edit.setText(last_dir)
            
        # 恢复查重方式
        method = self.settings.get("check_method")
        index = self.toolbar.method_combo.findText(method)
        if index >= 0:
            self.toolbar.method_combo.setCurrentIndex(index)
            
        # 恢复其他设置
        self.toolbar.min_size_spin.setValue(self.settings.get("min_size", 0))
        self.toolbar.max_depth_spin.setValue(self.settings.get("max_depth", 0))
        
        # 恢复窗口位置和大小
        geometry = self.settings.get("window_geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
    def closeEvent(self, event):
        """窗口关闭时保存配置"""
        self.settings.set("last_directory", self.toolbar.path_edit.text())
        self.settings.set("check_method", self.toolbar.method_combo.currentText())
        self.settings.set("min_size", self.toolbar.min_size_spin.value())
        self.settings.set("max_depth", self.toolbar.max_depth_spin.value())
        self.settings.set("window_geometry", self.saveGeometry())
        event.accept()
        
    def setup_connections(self):
        # 连接信号和槽
        self.toolbar.browse_button.clicked.connect(self.browse_directory)
        self.toolbar.search_button.clicked.connect(self.start_search)
        
        # 在现有连接后添加:
        self.toolbar.path_edit.textChanged.connect(
            lambda: self.settings.set("last_directory", self.toolbar.path_edit.text())
        )
        
    def browse_directory(self):
        logging.info("打开目录选择对话框")
        directory = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if directory:
            logging.info(f"选择目录: {directory}")
            self.toolbar.path_edit.setText(directory)
            
    def start_search(self):
        directory = self.toolbar.path_edit.text()
        if not directory:
            logging.warning("未选择目录")
            return
            
        # 检查是否是网络路径或映射驱动器
        is_network = directory.startswith(('\\\\', '//'))
        if not is_network and directory[0].isalpha() and directory[1] == ':':
            try:
                import win32wnet
                try:
                    network_path = win32wnet.WNetGetConnection(directory[0] + ':')
                    if network_path:
                        is_network = True
                except Exception:
                    pass
            except ImportError:
                pass
        
        if is_network:
            reply = QMessageBox.question(
                self, 
                "网络路径提示",
                "检测到网络路径，扫描可能较慢。是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        logging.info(f"开始搜索 - 目录: {directory}")
        method_text = self.toolbar.method_combo.currentText()
        logging.info(f"查重方式: {method_text}")
        
        # 添加中文到枚举值的映射
        method_map = {
            "按文件名": "FILENAME",
            "按大小": "SIZE", 
            "按MD5": "MD5",
            "混合模式": "MIXED"
        }
        
        # 获取选中的中文方式并转换为枚举值
        method = DuplicateCheckMethod[method_map[method_text]]
        
        # 创建并启动搜索线程
        self.search_worker = SearchWorker(directory, method)
        self.search_worker.progress.connect(self.update_progress)
        self.search_worker.finished.connect(self.show_results)
        self.search_worker.error.connect(self.show_error)
        self.search_worker.start()
        
    def update_progress(self, message: str, progress: float):
        self.status_bar.update_progress(message, progress)
        
    def show_results(self, results: dict, total: int):
        self.file_tree.display_results(results)
        self.status_bar.show_message(f"找到 {len(results)} 组重复文件，共扫描 {total} 个文件")
        
    def show_error(self, error: str):
        self.status_bar.show_error(error)
        
    def show_search_dialog(self):
        """显示搜索对话框"""
        dialog = SearchDialog(self)
        dialog.search_requested.connect(self.file_tree.filter_items)
        dialog.exec_()
        
    def setup_shortcuts(self):
        """设置快捷键"""
        # 搜索
        search_action = QAction("搜索", self)
        search_action.setShortcut("Ctrl+F")
        search_action.triggered.connect(self.show_search_dialog)
        
        # 刷新
        refresh_action = QAction("刷新", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.start_search)
        
        # 删除
        delete_action = QAction("删除", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.file_tree.delete_selected)
        
        # 全选
        select_all_action = QAction("全选", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.file_tree.selectAll)
        
        # 添加到菜单栏
        menu_bar = self.menuBar()
        
        file_menu = menu_bar.addMenu("文件")
        file_menu.addAction(search_action)
        file_menu.addAction(refresh_action)
        file_menu.addSeparator()
        file_menu.addAction(delete_action)
        
        edit_menu = menu_bar.addMenu("编辑")
        edit_menu.addAction(select_all_action)
        
    def setup_extra_actions(self):
        """设置额外的动作"""
        # 自动选择
        auto_select_action = QAction("自动选择重复文件", self)
        auto_select_action.triggered.connect(self.file_tree.auto_select_duplicates)
        
        # 保留特定格式
        format_menu = QMenu("保留格式", self)
        for ext in [".flac", ".mp3", ".wav"]:
            action = QAction(f"保留 {ext}", self)
            action.triggered.connect(lambda x, e=ext: self.keep_format(e))
            format_menu.addAction(action)
        
        # 添加到菜单
        edit_menu = self.menuBar().findChild(QMenu, "edit_menu")
        if edit_menu:
            edit_menu.addSeparator()
            edit_menu.addAction(auto_select_action)
            edit_menu.addMenu(format_menu)

    def keep_format(self, format: str):
        """保留指定格式，删除其他格式"""
        if not QMessageBox.question(
            self,
            "确认操作",
            f"确定要保留所有 {format} 格式文件，删除其他格式的重复文件吗？",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            return
        
        self.file_tree.keep_format(format)

    def setup_menu(self):
        menu_bar = self.menuBar()
        
        # 编辑菜单
        edit_menu = menu_bar.addMenu("编辑")
        
        # 自动选择动作
        auto_select_action = QAction("自动选择重复文件", self)
        auto_select_action.setShortcut("Ctrl+A")
        auto_select_action.triggered.connect(self.file_tree.auto_select_duplicates)
        edit_menu.addAction(auto_select_action) 