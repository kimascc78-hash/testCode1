"""
Power Limits Widget
파워 제한 설정 (8개 float)
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDoubleSpinBox, QMessageBox, QGridLayout
)
from rf_protocol import RFProtocol
from developer_widgets.system_widgets.system_data_manager import SystemDataManager
import struct
from ui_widgets import SmartSpinBox, SmartDoubleSpinBox

class PowerLimitsWidget(QGroupBox):
    """Power Limits 설정 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("Power Limits Configuration", parent)
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
        
        # ========================================
        # Forward Power Limits
        # ========================================
        forward_group = QGroupBox("Forward Power Limits")
        forward_layout = QGridLayout(forward_group)
        
        # User Power Limit
        forward_layout.addWidget(QLabel("User Limit:"), 0, 0)
        self.user_power_limit_spin = SmartDoubleSpinBox()
        self.user_power_limit_spin.setRange(0.0, 10000.0)
        self.user_power_limit_spin.setValue(1000.0)
        self.user_power_limit_spin.setSuffix(" W")
        self.user_power_limit_spin.setDecimals(1)
        forward_layout.addWidget(self.user_power_limit_spin, 0, 1)
        
        # Low Power Limit
        forward_layout.addWidget(QLabel("Low Limit:"), 1, 0)
        self.low_power_limit_spin = SmartDoubleSpinBox()
        self.low_power_limit_spin.setRange(0.0, 10000.0)
        self.low_power_limit_spin.setValue(10.0)
        self.low_power_limit_spin.setSuffix(" W")
        self.low_power_limit_spin.setDecimals(1)
        forward_layout.addWidget(self.low_power_limit_spin, 1, 1)
        
        # Max Power Limit
        forward_layout.addWidget(QLabel("Max Limit:"), 2, 0)
        self.max_power_limit_spin = SmartDoubleSpinBox()
        self.max_power_limit_spin.setRange(0.0, 10000.0)
        self.max_power_limit_spin.setValue(5000.0)
        self.max_power_limit_spin.setSuffix(" W")
        self.max_power_limit_spin.setDecimals(1)
        forward_layout.addWidget(self.max_power_limit_spin, 2, 1)
        
        self.main_layout.addWidget(forward_group)
        
        # ========================================
        # Reflected Power Limits
        # ========================================
        reflected_group = QGroupBox("Reflected Power Limits")
        reflected_layout = QGridLayout(reflected_group)
        
        # User Reflected Power Limit
        reflected_layout.addWidget(QLabel("User Limit:"), 0, 0)
        self.user_reflected_limit_spin = SmartDoubleSpinBox()
        self.user_reflected_limit_spin.setRange(0.0, 1000.0)
        self.user_reflected_limit_spin.setValue(100.0)
        self.user_reflected_limit_spin.setSuffix(" W")
        self.user_reflected_limit_spin.setDecimals(1)
        reflected_layout.addWidget(self.user_reflected_limit_spin, 0, 1)
        
        # Max Reflected Power Limit
        reflected_layout.addWidget(QLabel("Max Limit:"), 1, 0)
        self.max_reflected_limit_spin = SmartDoubleSpinBox()
        self.max_reflected_limit_spin.setRange(0.0, 1000.0)
        self.max_reflected_limit_spin.setValue(500.0)
        self.max_reflected_limit_spin.setSuffix(" W")
        self.max_reflected_limit_spin.setDecimals(1)
        reflected_layout.addWidget(self.max_reflected_limit_spin, 1, 1)
        
        self.main_layout.addWidget(reflected_group)
        
        # ========================================
        # External Feedback Limits
        # ========================================
        external_group = QGroupBox("External Feedback Limits")
        external_layout = QGridLayout(external_group)
        
        # User External Feedback Limit
        external_layout.addWidget(QLabel("User Limit:"), 0, 0)
        self.user_ext_limit_spin = SmartDoubleSpinBox()
        self.user_ext_limit_spin.setRange(0.0, 10.0)
        self.user_ext_limit_spin.setValue(10.0)
        self.user_ext_limit_spin.setSuffix(" V")
        self.user_ext_limit_spin.setDecimals(2)
        external_layout.addWidget(self.user_ext_limit_spin, 0, 1)
        
        # Max External Feedback Value
        external_layout.addWidget(QLabel("Max Value:"), 1, 0)
        self.max_ext_value_spin = SmartDoubleSpinBox()
        self.max_ext_value_spin.setRange(0.0, 10.0)
        self.max_ext_value_spin.setValue(10.0)
        self.max_ext_value_spin.setSuffix(" V")
        self.max_ext_value_spin.setDecimals(2)
        external_layout.addWidget(self.max_ext_value_spin, 1, 1)
        
        # Min External Feedback Value
        external_layout.addWidget(QLabel("Min Value:"), 2, 0)
        self.min_ext_value_spin = SmartDoubleSpinBox()
        self.min_ext_value_spin.setRange(0.0, 10.0)
        self.min_ext_value_spin.setValue(0.0)
        self.min_ext_value_spin.setSuffix(" V")
        self.min_ext_value_spin.setDecimals(2)
        external_layout.addWidget(self.min_ext_value_spin, 2, 1)
        
        self.main_layout.addWidget(external_group)
        
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
    
    
    ########
    def apply_settings(self):
        """설정 적용 - 각 필드를 개별 전송 (펌웨어 Line 682-689)"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        # 확인 메시지
        reply = QMessageBox.question(
            self,
            "확인",
            "Power Limits 설정을 적용하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 각 필드와 SUBCMD 매핑
        power_limits = [
            ('User Power Limit', RFProtocol.SUBCMD_USER_POWER_LIMIT, self.user_power_limit_spin.value()),
            ('Low Power Limit', RFProtocol.SUBCMD_LOW_POWER_LIMIT, self.low_power_limit_spin.value()),
            ('Max Power Limit', RFProtocol.SUBCMD_MAX_POWER_LIMIT, self.max_power_limit_spin.value()),
            ('User Reflected Limit', RFProtocol.SUBCMD_USER_REFLECTED_LIMIT, self.user_reflected_limit_spin.value()),
            ('Max Reflected Limit', RFProtocol.SUBCMD_MAX_REFLECTED_LIMIT, self.max_reflected_limit_spin.value()),
            ('User Ext Limit', RFProtocol.SUBCMD_USER_EXT_LIMIT, self.user_ext_limit_spin.value()),
            ('Max Ext Value', RFProtocol.SUBCMD_MAX_EXT_VALUE, self.max_ext_value_spin.value()),
            ('Min Ext Value', RFProtocol.SUBCMD_MIN_EXT_VALUE, self.min_ext_value_spin.value())
        ]
        
        success_count = 0
        failed_items = []
        
        # 각 필드를 개별적으로 전송
        for name, subcmd, value in power_limits:
            # float 데이터 (4 bytes)
            data = struct.pack('<f', float(value))
            
            result = self.network_manager.client_thread.send_command(
                RFProtocol.CMD_GLOBAL_CONFIG_SET,
                subcmd,
                data=data,
                wait_response=True,
                sync=True
            )
            
            if result.success:
                success_count += 1
            else:
                failed_items.append(f"{name}: {result.message}")
        
        # 결과 표시
        if success_count == 8:
            QMessageBox.information(
                self,
                "완료",
                "모든 Power Limits가 성공적으로 적용되었습니다."
            )
        elif success_count > 0:
            QMessageBox.warning(
                self,
                "부분 성공",
                f"적용 완료: {success_count}/8\n\n실패한 항목:\n" + "\n".join(failed_items)
            )
        else:
            QMessageBox.critical(
                self,
                "실패",
                "모든 Power Limits 적용에 실패했습니다.\n\n" + "\n".join(failed_items)
            )

    # ==================================================
    # load_settings 함수 완전 구현
    # ==================================================
    def load_settings(self):
        """설정 로드 - 각 필드를 개별 조회"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        # 각 필드와 SUBCMD, SpinBox 매핑
        power_limits = [
            ('User Power Limit', RFProtocol.SUBCMD_USER_POWER_LIMIT, self.user_power_limit_spin),
            ('Low Power Limit', RFProtocol.SUBCMD_LOW_POWER_LIMIT, self.low_power_limit_spin),
            ('Max Power Limit', RFProtocol.SUBCMD_MAX_POWER_LIMIT, self.max_power_limit_spin),
            ('User Reflected Limit', RFProtocol.SUBCMD_USER_REFLECTED_LIMIT, self.user_reflected_limit_spin),
            ('Max Reflected Limit', RFProtocol.SUBCMD_MAX_REFLECTED_LIMIT, self.max_reflected_limit_spin),
            ('User Ext Limit', RFProtocol.SUBCMD_USER_EXT_LIMIT, self.user_ext_limit_spin),
            ('Max Ext Value', RFProtocol.SUBCMD_MAX_EXT_VALUE, self.max_ext_value_spin),
            ('Min Ext Value', RFProtocol.SUBCMD_MIN_EXT_VALUE, self.min_ext_value_spin)
        ]
        
        success_count = 0
        failed_items = []
        
        # 각 필드를 개별적으로 GET
        for name, subcmd, spin in power_limits:
            result = self.network_manager.client_thread.send_command(
                RFProtocol.CMD_GLOBAL_CONFIG_GET,
                subcmd,
                wait_response=True,
                sync=True
            )
            
            if result.success and result.response_data:
                parsed = RFProtocol.parse_response(result.response_data)
                if parsed and len(parsed['data']) >= 4:
                    value = struct.unpack('<f', parsed['data'][0:4])[0]
                    spin.setValue(value)
                    success_count += 1
                else:
                    failed_items.append(f"{name}: 응답 데이터 형식 오류")
            else:
                failed_items.append(f"{name}: {result.message if result else '응답 없음'}")
        
        # 결과 표시
        if success_count == 8:
            QMessageBox.information(
                self,
                "완료",
                "모든 Power Limits를 성공적으로 로드했습니다."
            )
        elif success_count > 0:
            QMessageBox.warning(
                self,
                "부분 성공",
                f"로드 완료: {success_count}/8\n\n실패한 항목:\n" + "\n".join(failed_items)
            )
        else:
            QMessageBox.critical(
                self,
                "실패",
                "모든 Power Limits 로드에 실패했습니다.\n\n" + "\n".join(failed_items)
            )

    # ==================================================
    # reset_settings 함수 (선택사항)
    # ==================================================
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
        self.user_power_limit_spin.setValue(1000.0)
        self.low_power_limit_spin.setValue(10.0)
        self.max_power_limit_spin.setValue(5000.0)
        self.user_reflected_limit_spin.setValue(100.0)
        self.max_reflected_limit_spin.setValue(500.0)
        self.user_ext_limit_spin.setValue(10.0)
        self.max_ext_value_spin.setValue(10.0)
        self.min_ext_value_spin.setValue(0.0)


















