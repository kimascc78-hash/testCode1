"""
Main Application Entry Point
RF 파워 제너레이터 터미널 메인 실행 파일
"""
import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from style_manager import apply_global_styles
import pyqtgraph as pg

# 로컬 모듈 import
from main_window import MainWindow

def main():
    """메인 함수"""
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    pg.setConfigOption('useOpenGL', True)
    pg.setConfigOption('antialias', True)
    # QApplication 생성
    app = QApplication(sys.argv)
    
    # 애플리케이션 속성 설정
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    app.setApplicationName("RF Power Generator Terminal")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("RF Solutions")
    
    # ========================================
    # 전역 스타일 적용 추가
    # ========================================
    #apply_global_styles(app)
    
    # 메인 윈도우 생성 및 표시
    try:
        window = MainWindow()
        window.show()
        
        # 애플리케이션 실행
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"애플리케이션 실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
