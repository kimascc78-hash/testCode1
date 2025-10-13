"""
Oscilloscope Dialog Module
오실로스코프 다이얼로그 전담 모듈
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtCore import Qt
from oscilloscope_view import OscilloscopeView


class OscilloscopeDialog(QDialog):
    """오실로스코프 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()
        self.setup_connections()
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("RF Power Generator - Oscilloscope View")
        self.setMinimumSize(1200, 930)
        #self.resize(1400, 950)
        
        # 다이얼로그 스타일 적용
        self.setStyleSheet("""
            QDialog {
                background-color: #2e3440;
                color: #ffffff;
                font-family: 'Roboto Mono', monospace;
            }
        """)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 오실로스코프 뷰 추가
        self.oscilloscope_view = OscilloscopeView(self)
        main_layout.addWidget(self.oscilloscope_view)
    
    def setup_connections(self):
        """부모 윈도우와의 연결 설정"""
        if self.parent_window:
            # 부모 윈도우의 데이터 업데이트 신호가 있다면 연결
            pass
    
    def update_data(self, status_data):
        """데이터 업데이트"""
        if hasattr(self, 'oscilloscope_view'):
            self.oscilloscope_view.update_data(status_data)
    
    def closeEvent(self, event):
        """다이얼로그 닫기 이벤트"""
        # 오실로스코프 데이터 수집 중지
        if hasattr(self, 'oscilloscope_view'):
            self.oscilloscope_view.stop_acquisition()
        
        super().closeEvent(event)
