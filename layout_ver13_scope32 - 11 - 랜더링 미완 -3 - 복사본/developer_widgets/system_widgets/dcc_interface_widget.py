"""
DCC Interface Widget
DC 전원 제어 및 모니터링
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QRadioButton, QButtonGroup, QMessageBox, QGridLayout, QCheckBox,
    QFrame
)
from PyQt5.QtCore import Qt, QTimer
from rf_protocol import RFProtocol
from developer_widgets.system_widgets.system_data_manager import SystemDataManager


class DCCInterfaceWidget(QGroupBox):
    """DCC Interface 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("DCC Interface (DC Power Control & Monitor)", parent)
        self.parent = parent
        self.network_manager = network_manager
        self.sys_data_manager = SystemDataManager()
        
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self.on_toggle)
        
        # 자동 갱신 타이머
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.load_status)
        
        self.init_ui()
        self.on_toggle(False)
        
    def init_ui(self):
        """UI 초기화"""
        self.main_layout = QVBoxLayout(self)
        
        # ========================================
        # DC Power Control
        # ========================================
        # control_group = QGroupBox("DC Power Control")
        # control_layout = QHBoxLayout(control_group)
        
        # control_layout.addWidget(QLabel("DC Power:"))
        
        # self.dc_power_group = QButtonGroup()
        # self.dc_power_off = QRadioButton("Off")
        # self.dc_power_on = QRadioButton("On")
        # self.dc_power_off.setChecked(True)
        
        # self.dc_power_group.addButton(self.dc_power_off)
        # self.dc_power_group.addButton(self.dc_power_on)
        
        # control_layout.addWidget(self.dc_power_off)
        # control_layout.addWidget(self.dc_power_on)
        # control_layout.addStretch()
        
        # apply_control_button = QPushButton("Apply Control")
        # apply_control_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        # apply_control_button.clicked.connect(self.apply_control)
        # control_layout.addWidget(apply_control_button)
        
        # self.main_layout.addWidget(control_group)
        
        # ========================================
        # Status Monitor
        # ========================================
        monitor_group = QGroupBox("Status Monitor")
        monitor_layout = QVBoxLayout(monitor_group)
        
        # 상단: 새로고침 버튼
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        
        self.auto_refresh_checkbox = QCheckBox("Auto Refresh (1s)")
        self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
        refresh_layout.addWidget(self.auto_refresh_checkbox)
        
        refresh_button = QPushButton("Refresh Now")
        refresh_button.clicked.connect(self.load_status)
        refresh_layout.addWidget(refresh_button)
        
        monitor_layout.addLayout(refresh_layout)
        
        # 구분선
        monitor_layout.addWidget(self.create_h_line())
        
        # 모니터링 값들
        values_layout = QGridLayout()
        
        values_layout.addWidget(QLabel("DCC Status:"), 0, 0)
        self.status_value_label = QLabel("0x00000000")
        self.status_value_label.setStyleSheet("color: #00BFFF; font-family: monospace;")
        values_layout.addWidget(self.status_value_label, 0, 1)
        
        values_layout.addWidget(QLabel("DC Voltage:"), 1, 0)
        self.voltage_label = QLabel("--- V")
        self.voltage_label.setStyleSheet("color: #00BFFF;")
        values_layout.addWidget(self.voltage_label, 1, 1)
        
        values_layout.addWidget(QLabel("DC Current:"), 2, 0)
        self.current_label = QLabel("--- A")
        self.current_label.setStyleSheet("color: #00BFFF;")
        values_layout.addWidget(self.current_label, 2, 1)
        
        values_layout.addWidget(QLabel("PFC Current:"), 3, 0)
        self.pfc_current_label = QLabel("--- A")
        self.pfc_current_label.setStyleSheet("color: #00BFFF;")
        values_layout.addWidget(self.pfc_current_label, 3, 1)
        
        values_layout.addWidget(QLabel("RF Amp Temp:"), 4, 0)
        self.rf_amp_temp_label = QLabel("--- °C")
        self.rf_amp_temp_label.setStyleSheet("color: #00BFFF;")
        values_layout.addWidget(self.rf_amp_temp_label, 4, 1)
        
        values_layout.addWidget(QLabel("Water Temp:"), 5, 0)
        self.water_temp_label = QLabel("--- °C")
        self.water_temp_label.setStyleSheet("color: #00BFFF;")
        values_layout.addWidget(self.water_temp_label, 5, 1)
        
        values_layout.setColumnStretch(2, 1)
        
        monitor_layout.addLayout(values_layout)
        
        self.main_layout.addWidget(monitor_group)
        
        # ========================================
        # Status Bits (28 bits)
        # ========================================
        status_bits_group = QGroupBox("Status Bits (Read-only)")
        status_bits_layout = QVBoxLayout(status_bits_group)
        
        # 3개 컬럼으로 나누기
        bits_grid = QGridLayout()
        
        self.status_checkboxes = {}
        
        # kgen_config.h Line 232-260 참조
        status_bit_labels = [
            ('dc_status', 'DC Status'),
            ('pfc_status', 'PFC Status'),
            ('interlock', 'Interlock'),
            ('ac_fail', 'AC Fail'),
            ('fan1_fail', 'Fan 1 Fail'),
            ('fan2_fail', 'Fan 2 Fail'),
            ('over_amp_temper', 'Over Amp Temp'),
            ('over_water_temper', 'Over Water Temp'),
            ('waterflow_fail', 'Water Flow Fail'),
            ('over_dc_out', 'Over DC Out'),
            ('over_pfc', 'Over PFC'),
            ('over_pfc_vt', 'Over PFC VT'),
            ('fan3_fail', 'Fan 3 Fail'),
            ('fan4_fail', 'Fan 4 Fail'),
            ('fan5_fail', 'Fan 5 Fail'),
            ('fan6_fail', 'Fan 6 Fail'),
            ('dcc_dcout_voltage', 'DCC DC Voltage'),
            ('dcc_dcout_current', 'DCC DC Current'),
            ('dcc_pfcout_current', 'DCC PFC Current'),
            ('dcc_rfamp_temp', 'DCC RF Amp Temp'),
            ('dcc_waterplate_temp', 'DCC Water Temp'),
            ('gate_pa1_isens', 'Gate PA1 ISens'),
            ('gate_pa1_vsens', 'Gate PA1 VSens'),
            ('gate_pa1_temp', 'Gate PA1 Temp'),
            ('gate_pa2_isens', 'Gate PA2 ISens'),
            ('gate_pa2_vsens', 'Gate PA2 VSens'),
            ('gate_pa2_temp', 'Gate PA2 Temp'),
            ('gate_bias12', 'Gate Bias 1/2')
        ]
        
        # 3개 컬럼으로 배치 (각 컬럼에 9-10개씩)
        col = 0
        row = 0
        for key, label in status_bit_labels:
            cb = QCheckBox(label)
            cb.setEnabled(False)  # Read-only
            self.status_checkboxes[key] = cb
            bits_grid.addWidget(cb, row, col)
            
            row += 1
            if row >= 10:  # 한 컬럼에 10개씩
                row = 0
                col += 1
        
        status_bits_layout.addLayout(bits_grid)
        
        self.main_layout.addWidget(status_bits_group)
    
    def create_h_line(self):
        """수평선 생성"""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #444444;")
        return line
    
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
        
        # 펼쳐질 때 자동 갱신 중이면 계속, 접히면 중지
        if not checked and self.auto_refresh_timer.isActive():
            self.auto_refresh_timer.stop()
        elif checked and self.auto_refresh_checkbox.isChecked():
            self.auto_refresh_timer.start(1000)
    
    def toggle_auto_refresh(self, state):
        """자동 갱신 토글"""
        if state == Qt.Checked:
            self.auto_refresh_timer.start(1000)  # 1초마다
            self.load_status()  # 즉시 한 번 로드
        else:
            self.auto_refresh_timer.stop()
    
    def load_status(self):
        """DCC 상태 조회"""
        if not self.network_manager.client_thread:
            return
        
        # CMD_SYSTEM_CONTROL + SUBCMD_GET_DCC_IF
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_SYSTEM_CONTROL,
            RFProtocol.SUBCMD_GET_DCC_IF,
            wait_response=True,
            sync=True
        )
        
        if result.success and result.response_data:
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and len(parsed['data']) >= 28:
                dcc_if = self.sys_data_manager.parse_dcc_interface_data(parsed['data'])
                
                if dcc_if:
                    # DC On/Off 상태 업데이트
                    # if dcc_if['dc_onoff']:
                        # self.dc_power_on.setChecked(True)
                    # else:
                        # self.dc_power_off.setChecked(True)
                    
                    # 상태 값 업데이트
                    self.status_value_label.setText(f"0x{dcc_if['dcc_status']:08X}")
                    self.voltage_label.setText(f"{dcc_if['dc_voltage']:.2f} V")
                    self.current_label.setText(f"{dcc_if['dc_current']:.2f} A")
                    self.pfc_current_label.setText(f"{dcc_if['pfc_current']:.2f} A")
                    self.rf_amp_temp_label.setText(f"{dcc_if['rf_amp_temp']:.1f} °C")
                    self.water_temp_label.setText(f"{dcc_if['water_temp']:.1f} °C")
                    
                    # 상태 비트 업데이트
                    for key, checkbox in self.status_checkboxes.items():
                        checkbox.setChecked(dcc_if['status_bits'].get(key, False))
                else:
                    QMessageBox.warning(self, "오류", "DCC Interface 데이터 파싱 실패")
            else:
                QMessageBox.warning(self, "오류", "응답 데이터 형식 오류")
        else:
            if not self.auto_refresh_timer.isActive():  # 자동 갱신 중이 아닐 때만 메시지
                QMessageBox.warning(self, "오류", "상태 조회 실패")
    
    # def apply_control(self):
        # """DC Power 제어 적용"""
        # if not self.network_manager.client_thread:
            # QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            # return
        
        # # 확인 메시지
        # action = "켜기" if self.dc_power_on.isChecked() else "끄기"
        # reply = QMessageBox.question(
            # self,
            # "확인",
            # f"DC 전원을 {action}하시겠습니까?",
            # QMessageBox.Yes | QMessageBox.No
        # )
        
        # if reply != QMessageBox.Yes:
            # return
        
        # # 데이터 생성
        # dc_onoff = self.dc_power_on.isChecked()
        # success, data, message = self.sys_data_manager.create_dcc_control_data(dc_onoff)
        
        # if not success:
            # QMessageBox.critical(self, "오류", message)
            # return
        
        # # TODO: 실제 SET 명령어는 VHF 매뉴얼 확인 필요
        # # 임시로 메시지만 표시
        # QMessageBox.information(
            # self,
            # "준비 중",
            # f"DCC Control SET 명령어는 VHF 매뉴얼 확인이 필요합니다.\n"
            # f"데이터 생성은 완료되었습니다 ({len(data)} bytes).\n\n"
            # f"설정값: DC Power = {'On' if dc_onoff else 'Off'}"
        # )