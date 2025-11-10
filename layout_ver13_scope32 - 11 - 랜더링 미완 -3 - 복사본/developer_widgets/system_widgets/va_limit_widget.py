"""
VA Limit Widget
전압/전류 제한 설정 (2개 float)
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDoubleSpinBox, QMessageBox, QGridLayout
)
from rf_protocol import RFProtocol
from developer_widgets.system_widgets.system_data_manager import SystemDataManager
from ui_widgets import SmartSpinBox, SmartDoubleSpinBox

class VALimitWidget(QGroupBox):
    """VA Limit 설정 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("VA Limit Configuration", parent)
        self.parent = parent
        self.network_manager = network_manager
        self.sys_data_manager = SystemDataManager()
        
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self.on_toggle)
        
        self.init_ui()
        self.on_toggle(False)
        
    def init_ui(self):
        """UI 초기화"""
        self.main_layout = QVBoxLayout(self)
        
        # 설명
        info_label = QLabel(
            "VA (Voltage × Ampere) Limit:\n"
            "전압과 전류의 곱에 대한 제한값을 설정합니다."
        )
        info_label.setStyleSheet("color: #87ceeb; font-size: 11px;")
        self.main_layout.addWidget(info_label)
        
        # ========================================
        # VA Limit Values
        # ========================================
        limits_group = QGroupBox("VA Limit Values")
        limits_layout = QGridLayout(limits_group)
        
        # VA Limit 1
        limits_layout.addWidget(QLabel("VA Limit 1:"), 0, 0)
        self.va_limit_1_spin = SmartDoubleSpinBox()
        self.va_limit_1_spin.setRange(0.0, 1000.0)
        self.va_limit_1_spin.setValue(50.0)
        self.va_limit_1_spin.setSuffix(" V·A")
        self.va_limit_1_spin.setDecimals(2)
        self.va_limit_1_spin.setMinimumWidth(150)
        limits_layout.addWidget(self.va_limit_1_spin, 0, 1)
        
        # VA Limit 2
        limits_layout.addWidget(QLabel("VA Limit 2:"), 1, 0)
        self.va_limit_2_spin = SmartDoubleSpinBox()
        self.va_limit_2_spin.setRange(0.0, 1000.0)
        self.va_limit_2_spin.setValue(50.0)
        self.va_limit_2_spin.setSuffix(" V·A")
        self.va_limit_2_spin.setDecimals(2)
        self.va_limit_2_spin.setMinimumWidth(150)
        limits_layout.addWidget(self.va_limit_2_spin, 1, 1)
        
        limits_layout.setColumnStretch(2, 1)  # 오른쪽 여백
        
        self.main_layout.addWidget(limits_group)
        
        # ========================================
        # 버튼
        # ========================================
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        load_button = QPushButton("Load")
        load_button.clicked.connect(self.load_settings)
        button_layout.addWidget(load_button)
        
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset_settings)
        button_layout.addWidget(reset_button)
        
        apply_button = QPushButton("Apply")
        apply_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        apply_button.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_button)
        
        self.main_layout.addLayout(button_layout)
        
        # 스트레치 추가
        self.main_layout.addStretch()
    
    def on_toggle(self, checked):
        """접기/펼치기"""
        for i in range(self.main_layout.count()):
            item = self.main_layout.itemAt(i)
            if item.widget():
                item.widget().setVisible(checked)
            elif item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if widget:
                        widget.setVisible(checked)
    
    def reset_settings(self):
        """기본값으로 리셋"""
        reply = QMessageBox.question(
            self,
            "확인",
            "기본값으로 초기화하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 기본값 설정
        self.va_limit_1_spin.setValue(50.0)
        self.va_limit_2_spin.setValue(50.0)
    
    def apply_settings(self):
        """설정 적용"""
        reply = QMessageBox.question(
            self, "확인",
            "VA Limit 설정을 적용하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        settings = {
            'va_limit_1': self.va_limit_1_spin.value(),
            'va_limit_2': self.va_limit_2_spin.value()
        }
        
        # 데이터 생성 (2 floats = 8 bytes)
        success, data, message = self.sys_data_manager.create_va_limit_data(settings)
        
        if not success:
            QMessageBox.critical(self, "오류", message)
            return
        
        # 명령어 전송 (펌웨어 Line 693)
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_GLOBAL_CONFIG_SET,
            RFProtocol.SUBCMD_VA_LIMIT,
            data=data,
            wait_response=True,
            sync=True
        )
        
        if result.success:
            QMessageBox.information(self, "완료", "VA Limit이 적용되었습니다.")
        else:
            QMessageBox.warning(self, "오류", f"설정 적용 실패: {result.message}")

    def load_settings(self):
        """설정 로드"""
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_GLOBAL_CONFIG_GET,
            RFProtocol.SUBCMD_VA_LIMIT,
            wait_response=True,
            sync=True
        )
        
        if result.success and result.response_data:
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and len(parsed['data']) >= 8:
                va_limits = self.sys_data_manager.parse_va_limit_data(parsed['data'])
                
                if va_limits:
                    self.va_limit_1_spin.setValue(va_limits['va_limit_1'])
                    self.va_limit_2_spin.setValue(va_limits['va_limit_2'])
                    QMessageBox.information(self, "완료", "VA Limit을 로드했습니다.")