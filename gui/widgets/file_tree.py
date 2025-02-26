from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, 
                           QMessageBox, QHeaderView, QDialog,
                           QVBoxLayout, QHBoxLayout, QPushButton,
                           QWidget)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
import os
import time
from collections import defaultdict
from typing import List
from ...core.file_index import FileIndex
from ...config.settings import Settings
from ..dialogs.duplicate_settings_dialog import DuplicateSettingsDialog
import logging

class FileTreeWidget(QTreeWidget):
    """文件树控件"""
    
    # 自定义信号
    file_deleted = pyqtSignal(str)  # 文件被删除时发出信号
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_context_menu()
        
    def setup_ui(self):
        # 创建主布局
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 添加工具栏
        toolbar = QHBoxLayout()
        
        # 自动选择按钮
        self.auto_select_btn = QPushButton("自动选择重复文件")
        self.auto_select_btn.clicked.connect(self.auto_select_duplicates)
        toolbar.addWidget(self.auto_select_btn)
        
        # 删除选中按钮
        self.delete_btn = QPushButton("删除选中文件")
        self.delete_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.delete_btn.clicked.connect(self.delete_selected)
        toolbar.addWidget(self.delete_btn)
        
        # 清除选择按钮
        self.clear_select_btn = QPushButton("清除选择")
        self.clear_select_btn.clicked.connect(self.clearSelection)
        toolbar.addWidget(self.clear_select_btn)
        
        # 添加弹性空间
        toolbar.addStretch()
        
        # 将工具栏添加到主布局
        layout.addLayout(toolbar)
        
        # 设置树形控件
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["路径", "大小", "修改时间"])
        
        # 设置列宽
        header = self.tree.header()
        # 改为用户可调整模式
        header.setSectionResizeMode(0, QHeaderView.Interactive)  # 路径列可调整
        header.setSectionResizeMode(1, QHeaderView.Interactive)  # 大小列可调整
        header.setSectionResizeMode(2, QHeaderView.Interactive)  # 时间列可调整
        
        # 设置默认列宽
        header.resizeSection(0, 400)  # 路径列默认宽度
        header.resizeSection(1, 100)  # 大小列默认宽度
        header.resizeSection(2, 150)  # 时间列默认宽度
        
        # 保存列宽到配置
        header.sectionResized.connect(self._save_column_widths)
        
        # 允许多选
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        
        # 设置排序
        self.tree.setSortingEnabled(True)
        
        # 从配置加载列宽
        self._load_column_widths()
        
        # 将树形控件添加到主布局
        layout.addWidget(self.tree)
        
    def setup_context_menu(self):
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        
        self.context_menu = QMenu(self)
        self.context_menu.addAction("删除", self.delete_selected)
        self.context_menu.addAction("打开所在文件夹", self.open_containing_folder)
        
    def show_context_menu(self, position):
        """显示右键菜单"""
        if self.tree.selectedItems():
            self.context_menu.exec_(self.tree.mapToGlobal(position))
            
    def delete_selected(self):
        """删除选中的文件"""
        selected = self.tree.selectedItems()
        if not selected:
            return
            
        # 计算要删除的文件数量
        file_count = sum(1 for item in selected if not item.childCount())
        
        # 确认删除
        if not QMessageBox.question(self, 
                                  "确认删除",
                                  f"确定要删除选中的 {file_count} 个文件吗？\n此操作不可恢复！",
                                  QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            return
            
        # 执行删除
        for item in selected:
            if item.childCount() == 0:  # 只删除文件，不删除组
                file_path = item.text(0)
                try:
                    os.remove(file_path)
                    self.file_deleted.emit(file_path)
                    
                    # 删除树节点
                    parent = item.parent()
                    parent.removeChild(item)
                    
                    # 如果组内只剩一个文件，删除整个组
                    if parent and parent.childCount() <= 1:
                        index = self.tree.indexOfTopLevelItem(parent)
                        self.tree.takeTopLevelItem(index)
                        
                    # 删除成功后更新索引
                    file_index = FileIndex()
                    file_index.remove_index(os.path.dirname(file_path))
                    
                except Exception as e:
                    QMessageBox.warning(self, "删除失败", f"无法删除文件: {file_path}\n{str(e)}")
                    
    def open_containing_folder(self):
        """打开所选文件所在文件夹"""
        selected = self.tree.selectedItems()
        if not selected:
            return
            
        item = selected[0]
        if item.childCount() > 0:  # 如果是组，使用第一个子项
            item = item.child(0)
            
        path = item.text(0)
        folder = os.path.dirname(path)
        os.startfile(folder)
        
    def display_results(self, results: dict):
        """显示搜索结果"""
        self.tree.clear()
        
        for group_name, files in results.items():
            # 创建组节点
            group_item = QTreeWidgetItem(self.tree)
            group_item.setText(0, group_name)
            group_item.setExpanded(True)  # 默认展开
            
            # 添加文件
            for file_info in files:
                file_item = QTreeWidgetItem(group_item)
                file_item.setText(0, file_info.path)
                file_item.setText(1, file_info.size)
                file_item.setText(2, file_info.mtime)
                
    def filter_items(self, text: str, filter_by: str = "全部"):
        """过滤显示结果"""
        text = text.lower()
        
        # 显示所有项
        if not text:
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                item.setHidden(False)
                for j in range(item.childCount()):
                    item.child(j).setHidden(False)
            return
            
        # 遍历所有项进行过滤
        for i in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(i)
            show_group = False
            
            # 检查每个文件
            for j in range(group_item.childCount()):
                file_item = group_item.child(j)
                show_file = False
                
                if filter_by == "全部":
                    show_file = any(text in file_item.text(k).lower() 
                                  for k in range(file_item.columnCount()))
                elif filter_by == "路径":
                    show_file = text in file_item.text(0).lower()
                elif filter_by == "大小":
                    show_file = text in file_item.text(1).lower()
                elif filter_by == "时间":
                    show_file = text in file_item.text(2).lower()
                    
                file_item.setHidden(not show_file)
                show_group = show_group or show_file
                
            group_item.setHidden(not show_group) 

    def auto_select_duplicates(self):
        """根据设置自动选择要删除的重复文件"""
        # 显示设置对话框
        dialog = DuplicateSettingsDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        
        settings = dialog.get_settings()
        self.clearSelection()
        
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            files = []
            
            # 收集组内所有文件信息
            for j in range(group.childCount()):
                item = group.child(j)
                path = item.text(0)
                ext = os.path.splitext(path)[1].lower()
                size = float(item.text(1).replace(" MB", ""))
                mtime = time.strptime(item.text(2), "%Y-%m-%d %H:%M:%S")
                
                # 检查是否在排除目录中
                if any(excl_dir in path for excl_dir in settings['exclude_dirs']):
                    continue
                    
                files.append({
                    'item': item,
                    'path': path,
                    'ext': ext,
                    'size': size,
                    'mtime': mtime,
                    'priority': settings['format_priority'].get(ext, 999)
                })
            
            if not files:
                continue
            
            # 根据设置选择要保留的文件
            if settings['skip_different_names']:
                # 只处理文件名完全相同的文件
                name_groups = defaultdict(list)
                for f in files:
                    name = os.path.splitext(os.path.basename(f['path']))[0]
                    name_groups[name].append(f)
                
                for name, group_files in name_groups.items():
                    if len(group_files) > 1:
                        self._select_files_to_delete(group_files, settings)
            else:
                self._select_files_to_delete(files, settings)
            
    def _select_files_to_delete(self, files: List[dict], settings: dict):
        """根据设置选择要删除的文件"""
        if not files:
            return
            
        # 首先按优先删除目录排序
        delete_dirs = settings['delete_dirs']
        for file in files:
            file['in_delete_dir'] = any(d.lower() in file['path'].lower() for d in delete_dirs)
            
            # 添加格式优先级日志
            logging.debug(f"文件 {file['path']} 的格式优先级: {file['priority']}")
        
        # 修改排序逻辑
        files.sort(key=lambda x: (
            x['in_delete_dir'],  # True 排在后面（更容易被删除）
            x['priority'],       # 数字越大优先级越低（更容易被删除）
            x['size'] if settings['prefer_larger'] else -x['size'],  # 大小偏好
            -time.mktime(x['mtime']) if settings['keep_oldest'] else time.mktime(x['mtime'])  # 时间偏好
        ))
        
        # 记录排序结果
        logging.info("文件排序结果:")
        for f in files:
            logging.info(f"文件: {f['path']}")
            logging.info(f"  - 在删除目录中: {f['in_delete_dir']}")
            logging.info(f"  - 优先级: {f['priority']}")
            logging.info(f"  - 大小: {f['size']}")
        
        # 选中除了最优先（排在最前面）的文件之外的所有文件
        for file in files[1:]:
            file['item'].setSelected(True)

    def _save_column_widths(self, column, oldSize, newSize):
        """保存列宽到配置"""
        settings = Settings()
        widths = settings.get('column_widths', {})
        widths[str(column)] = newSize
        settings.set('column_widths', widths)

    def _load_column_widths(self):
        """从配置加载列宽"""
        settings = Settings()
        widths = settings.get('column_widths', {})
        header = self.tree.header()
        for col, width in widths.items():
            header.resizeSection(int(col), width)

    def clearSelection(self):
        self.tree.clearSelection()

    def selectedItems(self):
        return self.tree.selectedItems()

    def topLevelItem(self, index):
        return self.tree.topLevelItem(index)

    def topLevelItemCount(self):
        return self.tree.topLevelItemCount() 