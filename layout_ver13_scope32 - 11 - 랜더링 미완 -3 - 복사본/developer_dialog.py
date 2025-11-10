"""
Developer Dialog
개발자 도구 다이얼로그 (독립 창)
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QDialogButtonBox
)
from PyQt5.QtCore import Qt

from ui_widgets import SmartSpinBox, SmartDoubleSpinBox

class DeveloperDialog(QDialog):
    """Developer Tools 다이얼로그"""
    
    def __init__(self, parent, network_manager):
        super().__init__(parent)
        self.parent = parent
        self.network_manager = network_manager
        
        self.apply_styles()  # 스타일 먼저 적용
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("Developer Tools")
        self.setMinimumSize(1000, 800)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        tab_widget = QTabWidget()
        tab_widget.setTabPosition(QTabWidget.North)
        
        # ========================================
        # Device & Config 탭 
        # ========================================
        from developer_widgets.device_config_widget import DeviceConfigWidget
        self.device_config_widget = DeviceConfigWidget(self, self.network_manager)
        tab_widget.addTab(self.device_config_widget, "Device & Config")
        
        # ========================================
        # ⭐ System Control 탭
        # ========================================
        from developer_widgets.system_control_widget import SystemControlWidget
        self.system_control_widget = SystemControlWidget(self, self.network_manager)
        tab_widget.addTab(self.system_control_widget, "System")
        
        # ========================================
        # Advanced Settings 탭
        # ========================================
        from developer_widgets.advanced_settings_widget import AdvancedSettingsWidget
        self.advanced_widget = AdvancedSettingsWidget(self, self.network_manager)
        tab_widget.addTab(self.advanced_widget, "Advanced")
        
        # ========================================
        # Calibration 탭 
        # ========================================
        from developer_widgets.calibration_widget import CalibrationWidget
        self.calibration_widget = CalibrationWidget(self, self.network_manager)
        self.calibration_widget.setCheckable(False)
        tab_widget.addTab(self.calibration_widget, "Calibration")
        
        # ========================================
        # Arc Management 탭
        # ========================================
        from developer_widgets.arc_management_widget import ArcManagementWidget
        self.arc_widget = ArcManagementWidget(self, self.network_manager)
        self.arc_widget.setCheckable(False)
        tab_widget.addTab(self.arc_widget, "Arc Mgmt")
        
        layout.addWidget(tab_widget)
        
        # 하단 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.close)
        layout.addWidget(button_box)
        
        # 탭 변경 시그널
        tab_widget.currentChanged.connect(self.on_tab_changed)

    def showEvent(self, event):
        """다이얼로그 표시 시 호출"""
        super().showEvent(event)
        # device_info_widget -> device_config_widget로 변경
        self.device_config_widget.load_device_info()

    def on_tab_changed(self, index):
        """탭 변경 시 호출"""
        if index == 0:  # Device & Config 탭
            self.device_config_widget.load_device_info()
    
    def apply_styles(self):
        """다이얼로그 스타일 적용"""
        style_sheet = """
            QDialog {
                color: #e6e6fa;
                font-family: 'Roboto Mono', monospace;
            }
            QTabWidget::pane {
                border: 1px solid #00f0ff;
                background: #252535;
            }
            QTabBar::tab {
                background: #2e2e3e;
                color: #d0d0d0;
                padding: 8px 15px;
                margin-right: 2px;
                border: 1px solid #444;
                border-radius: 4px 4px 0 0;
                min-width: 110px;
                font-weight: bold;
            }

            QTabBar::tab:selected {
                background: #00f0ff;
                color: #1e1e2e;
            }
            
            QTabBar::tab:hover {
                background: #3a3a4a;
                color: #ffffff;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #444444;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #f0f8ff;
            }
            QGroupBox QLabel {
                color: #dcdcdc;
                font-size: 12px;
            }
            QLabel {
                color: #dcdcdc;
                font-size: 12px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #87ceeb;
                font-size: 13px;
            }
            
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #3F3F4F;
                border: 1px solid #00f0ff;
                border-radius: 3px;
                padding: 4px;
                color: #e0ffff;
                min-height: 20px;
                min-width: 80px;
                font-size: 11px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #00d4aa;
                background-color: #363646;
            }
            QComboBox::drop-down {
                border: none;
                background: #404050;
            }
            QComboBox::down-arrow {
                border: 2px solid #00f0ff;
                border-radius: 2px;
                background: #00f0ff;
            }
            QComboBox QAbstractItemView {
                background-color: #2e2e3e;
                color: #e0ffff;
                selection-background-color: #00f0ff;
                selection-color: #1e1e2e;
                border: 1px solid #00f0ff;
            }
            QPushButton {
                background-color: #3e3e4e;
                border: 1px solid #00f0ff;
                border-radius: 5px;
                padding: 6px 12px;
                color: #f5f5f5;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #00f0ff;
                color: #1e1e2e;
                border: 1px solid #00d4aa;
            }
            QPushButton:pressed {
                background-color: #00a0aa;
                color: #ffffff;
            }
            QPushButton:default {
                background-color: #006064;
                border: 1px solid #00f0ff;
                color: #ffffff;
            }
            QPushButton.tab-apply {
                background-color: #ff6b00;
                border: 1px solid #ff8c00;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton.tab-apply:hover {
                background-color: #ff8c00;
                color: #1e1e2e;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #2e2e3e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #00f0ff;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00d4aa;
            }
            
            QCheckBox {
                color: #dcdcdc;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #00f0ff;
                border-radius: 3px;
                background-color: #3F3F4F;
            }
            QCheckBox::indicator:checked {
                background-color: #00f0ff;
                border-color: #00d4aa;
            }
            QCheckBox::indicator:disabled {
                background-color: #2e2e3e;
                border-color: #555555;
            }
            
            QRadioButton {
                color: #dcdcdc;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #00f0ff;
                border-radius: 9px;
                background-color: #3F3F4F;
            }
            QRadioButton::indicator:checked {
                background-color: #00f0ff;
                border-color: #00d4aa;
            }
        """
        
        self.setStyleSheet(style_sheet)