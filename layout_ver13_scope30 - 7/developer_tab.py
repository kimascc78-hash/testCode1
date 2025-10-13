"""
Developer Tab
개발자 전용 기능 탭
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import Qt


class DeveloperTab(QWidget):
    """Developer 탭 메인 컨테이너"""
    
    def __init__(self, parent, network_manager):
        super().__init__(parent)
        self.parent = parent
        self.network_manager = network_manager
        
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 스크롤 컨텐츠 위젯
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        
        # ========================================
        # 상단: Device Info Widget (고정)
        # ========================================
        from developer_widgets.device_info_widget import DeviceInfoWidget
        self.device_info_widget = DeviceInfoWidget(self, self.network_manager)
        scroll_layout.addWidget(self.device_info_widget)
        
        # ========================================
        # 중단: Accordion Sections
        # ========================================
        
        # Arc Management (기본 펼침)
        from developer_widgets.arc_management_widget import ArcManagementWidget
        self.arc_widget = ArcManagementWidget(self, self.network_manager)
        scroll_layout.addWidget(self.arc_widget)
        
        # Advanced Settings (기본 접힘)
        from developer_widgets.advanced_settings_widget import AdvancedSettingsWidget
        self.advanced_widget = AdvancedSettingsWidget(self, self.network_manager)
        scroll_layout.addWidget(self.advanced_widget)
        
        # Calibration (기본 접힘)
        from developer_widgets.calibration_widget import CalibrationWidget
        self.calibration_widget = CalibrationWidget(self, self.network_manager)
        scroll_layout.addWidget(self.calibration_widget)
        
        # 스트레치 추가
        scroll_layout.addStretch()
        
        # 스크롤 영역에 컨텐츠 설정
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # ========================================
        # 하단: Config Management (고정)
        # ========================================
        from developer_widgets.config_management_widget import ConfigManagementWidget
        self.config_widget = ConfigManagementWidget(self, self.network_manager)
        main_layout.addWidget(self.config_widget)
    
    def on_tab_selected(self):
        """탭 선택 시 호출"""
        # Device 정보 자동 로드
        self.device_info_widget.load_device_info()