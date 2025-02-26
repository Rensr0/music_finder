#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging
from pathlib import Path
import traceback

# 添加父目录到 Python 路径
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from music_finder.gui.main_window import MainWindow

def print_usage():
    """打印使用说明"""
    print("""
音乐文件查重工具

用法:
    music_finder [目录路径]
    
选项:
    -h, --help     显示此帮助信息
    """)

def setup_logging():
    """配置日志"""
    try:
        # 确保日志和索引目录存在
        log_dir = Path.home() / ".music_finder"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        index_dir = log_dir / "index"
        index_dir.mkdir(exist_ok=True)
        
        # 添加日志文件滚动
        from logging.handlers import RotatingFileHandler
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                RotatingFileHandler(
                    log_dir / 'music_finder.log',
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5,
                    encoding='utf-8'
                )
            ]
        )
    except Exception as e:
        print(f"配置日志时出错: {e}", file=sys.stderr)
        sys.exit(1)

def handle_exception(exc_type, exc_value, exc_traceback):
    """处理未捕获的异常"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logging.error("未捕获的异常:", exc_info=(exc_type, exc_value, exc_traceback))

def main():
    """主程序入口"""
    try:
        # 处理命令行参数
        if len(sys.argv) > 1:
            if sys.argv[1] in ['-h', '--help']:
                print_usage()
                sys.exit(0)
        
        # 设置异常处理器
        sys.excepthook = handle_exception
        
        setup_logging()
        logging.info("程序启动")
        
        app = QApplication(sys.argv)
        
        # 设置应用程序信息
        app.setApplicationName("音乐文件查重工具")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("MusicFinder")
        
        # 创建并显示主窗口
        window = MainWindow()
        window.show()
        
        # 运行应用程序
        ret = app.exec_()
        
        # 清理资源
        logging.info("程序正常退出")
        logging.shutdown()
        
        sys.exit(ret)
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(1)
    except Exception as e:
        logging.error(f"程序运行出错: {e}")
        logging.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 