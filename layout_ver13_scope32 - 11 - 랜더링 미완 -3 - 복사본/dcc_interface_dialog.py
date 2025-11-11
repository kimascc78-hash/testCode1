"""
DCC Interface Monitor Dialog
DC 전원 제어 및 모니터링 전용 다이얼로그
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QCheckBox, QFrame, QComboBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from rf_protocol import RFProtocol
from developer_widgets.system_widgets.system_data_manager import SystemDataManager
from status_monitor_dialog import StatusIndicator


class DCCInterfaceDialog(QDialog):
    """DCC Interface Monitor 다이얼로그"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.sys_data_manager = SystemDataManager()

        # 상태 인디케이터 저장 (StatusIndicator 사용)
        self.status_indicators = {}

        # 자동 갱신 설정
        self.auto_refresh_enabled = True  # 기본값: 활성화
        self.refresh_interval = 1000  # 기본값: 1000ms (1초)
        self.is_refreshing = False  # 갱신 중 플래그

        # 비트별 상태 타입 정의 (0일 때의 상태)
        # "normal_on_zero": True이면 0일 때 정상, False이면 1일 때 정상
        self.bit_status_config = {
            # Power Status - 1일 때 정상 (ON)
            'dc_status': {'normal_on_zero': False, 'category': 'power'},
            'pfc_status': {'normal_on_zero': False, 'category': 'power'},

            # Safety - 0일 때 정상
            'interlock': {'normal_on_zero': True, 'category': 'safety'},

            # Failures - 0일 때 정상
            'ac_fail': {'normal_on_zero': True, 'category': 'failure'},
            'fan1_fail': {'normal_on_zero': True, 'category': 'cooling'},
            'fan2_fail': {'normal_on_zero': True, 'category': 'cooling'},
            'fan3_fail': {'normal_on_zero': True, 'category': 'cooling'},
            'fan4_fail': {'normal_on_zero': True, 'category': 'cooling'},
            'fan5_fail': {'normal_on_zero': True, 'category': 'cooling'},
            'fan6_fail': {'normal_on_zero': True, 'category': 'cooling'},
            'waterflow_fail': {'normal_on_zero': True, 'category': 'cooling'},

            # Over Conditions - 0일 때 정상
            'over_amp_temper': {'normal_on_zero': True, 'category': 'over'},
            'over_water_temper': {'normal_on_zero': True, 'category': 'cooling'},
            'over_dc_out': {'normal_on_zero': True, 'category': 'over'},
            'over_pfc': {'normal_on_zero': True, 'category': 'over'},
            'over_pfc_vt': {'normal_on_zero': True, 'category': 'over'},

            # Sensors - 1일 때 정상 (센서 활성)
            'dcc_dcout_voltage': {'normal_on_zero': False, 'category': 'sensor'},
            'dcc_dcout_current': {'normal_on_zero': False, 'category': 'sensor'},
            'dcc_pfcout_current': {'normal_on_zero': False, 'category': 'sensor'},
            'dcc_rfamp_temp': {'normal_on_zero': False, 'category': 'sensor'},
            'dcc_waterplate_temp': {'normal_on_zero': False, 'category': 'sensor'},
            'gate_pa1_isens': {'normal_on_zero': False, 'category': 'sensor'},
            'gate_pa1_vsens': {'normal_on_zero': False, 'category': 'sensor'},
            'gate_pa1_temp': {'normal_on_zero': False, 'category': 'sensor'},
            'gate_pa2_isens': {'normal_on_zero': False, 'category': 'sensor'},
            'gate_pa2_vsens': {'normal_on_zero': False, 'category': 'sensor'},
            'gate_pa2_temp': {'normal_on_zero': False, 'category': 'sensor'},
            'gate_bias12': {'normal_on_zero': False, 'category': 'sensor'}
        }

        # 자동 갱신 타이머
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.load_status)

        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("DCC Interface Monitor")
        self.setMinimumSize(1000, 700)

        # 다크 테마 스타일
        self.setStyleSheet("""
            QDialog {
                background-color: #2e3440;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4c566a;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: #3b4252;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #88c0d0;
                font-size: 14px;
                background-color: #2e3440;
            }
            QLabel {
                color: #d8dee9;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # 타이틀
        title_label = QLabel("DCC Interface (DC Power Control & Monitor)")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #88c0d0; margin: 5px; font-size: 18px;")
        main_layout.addWidget(title_label)

        # 상단 컨트롤 & 모니터링 값
        monitor_group = self.create_monitor_section()
        main_layout.addWidget(monitor_group)

        # Status Bits 섹션 (범주별)
        status_bits_layout = QHBoxLayout()
        status_bits_layout.setSpacing(10)

        # 왼쪽 컬럼
        left_column = QVBoxLayout()
        left_column.addWidget(self.create_power_status_group())
        left_column.addWidget(self.create_safety_group())
        left_column.addWidget(self.create_failure_group())
        left_column.addStretch()

        # 중간 컬럼
        middle_column = QVBoxLayout()
        middle_column.addWidget(self.create_cooling_group())
        middle_column.addWidget(self.create_over_conditions_group())
        middle_column.addStretch()

        # 오른쪽 컬럼
        right_column = QVBoxLayout()
        right_column.addWidget(self.create_sensor_group())
        right_column.addStretch()

        status_bits_layout.addLayout(left_column)
        status_bits_layout.addLayout(middle_column)
        status_bits_layout.addLayout(right_column)

        main_layout.addLayout(status_bits_layout)

        # 컬러 가이드
        guide_frame = self.create_color_guide()
        main_layout.addWidget(guide_frame)

        # 하단 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #bf616a;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d08770;
            }
        """)

        button_layout.addWidget(close_btn)
        main_layout.addLayout(button_layout)

        # 자동 갱신 시작 (초기화 완료 후)
        if self.auto_refresh_enabled:
            self.auto_refresh_timer.start(self.refresh_interval)
            self.load_status()  # 즉시 한 번 로드

    def create_monitor_section(self):
        """상단 모니터링 섹션"""
        group = QGroupBox("Status Monitor")
        layout = QVBoxLayout(group)

        # 자동 갱신 컨트롤 (옵션 1: 콤팩트 인라인 배치)
        refresh_control_layout = QHBoxLayout()
        refresh_control_layout.addStretch()

        self.auto_refresh_checkbox = QCheckBox("Auto Refresh")
        self.auto_refresh_checkbox.setChecked(self.auto_refresh_enabled)
        self.auto_refresh_checkbox.setStyleSheet("color: #d8dee9; font-size: 12px;")
        self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
        refresh_control_layout.addWidget(self.auto_refresh_checkbox)

        self.refresh_interval_combo = QComboBox()
        self.refresh_interval_combo.addItems([
            "100ms", "200ms", "500ms", "1000ms", "2000ms", "3000ms", "5000ms"
        ])
        self.refresh_interval_combo.setCurrentText("1000ms")
        self.refresh_interval_combo.setStyleSheet("""
            QComboBox {
                background-color: #3b4252;
                color: #d8dee9;
                border: 1px solid #4c566a;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 80px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #d8dee9;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #3b4252;
                color: #d8dee9;
                selection-background-color: #5e81ac;
            }
        """)
        self.refresh_interval_combo.currentTextChanged.connect(self.change_refresh_interval)
        refresh_control_layout.addWidget(self.refresh_interval_combo)

        self.manual_refresh_btn = QPushButton("⟳ Refresh Now")
        self.manual_refresh_btn.clicked.connect(self.manual_refresh)
        self.manual_refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #5e81ac;
                border: none;
                border-radius: 5px;
                padding: 6px 12px;
                color: white;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #81a1c1;
            }
        """)
        refresh_control_layout.addWidget(self.manual_refresh_btn)

        # LED 표시등 (갱신 중 깜빡임)
        self.status_led = QLabel("●")
        self.status_led.setStyleSheet("color: #4CAF50; font-size: 16px;")
        refresh_control_layout.addWidget(self.status_led)

        layout.addLayout(refresh_control_layout)

        # 구분선
        layout.addWidget(self.create_h_line())

        # 모니터링 값들
        values_layout = QGridLayout()
        values_layout.setSpacing(10)

        # DCC Status (HEX)
        values_layout.addWidget(QLabel("DCC Status:"), 0, 0)
        self.status_value_label = QLabel("0x00000000")
        self.status_value_label.setStyleSheet("color: #00BFFF; font-family: monospace; font-size: 13px; font-weight: bold;")
        values_layout.addWidget(self.status_value_label, 0, 1)

        # DC Voltage
        values_layout.addWidget(QLabel("DC Voltage:"), 1, 0)
        self.voltage_label = QLabel("--- V")
        self.voltage_label.setStyleSheet("color: #00BFFF; font-size: 13px; font-weight: bold;")
        values_layout.addWidget(self.voltage_label, 1, 1)

        # DC Current
        values_layout.addWidget(QLabel("DC Current:"), 2, 0)
        self.current_label = QLabel("--- A")
        self.current_label.setStyleSheet("color: #00BFFF; font-size: 13px; font-weight: bold;")
        values_layout.addWidget(self.current_label, 2, 1)

        # PFC Current
        values_layout.addWidget(QLabel("PFC Current:"), 0, 2)
        self.pfc_current_label = QLabel("--- A")
        self.pfc_current_label.setStyleSheet("color: #00BFFF; font-size: 13px; font-weight: bold;")
        values_layout.addWidget(self.pfc_current_label, 0, 3)

        # RF Amp Temp
        values_layout.addWidget(QLabel("RF Amp Temp:"), 1, 2)
        self.rf_amp_temp_label = QLabel("--- °C")
        self.rf_amp_temp_label.setStyleSheet("color: #00BFFF; font-size: 13px; font-weight: bold;")
        values_layout.addWidget(self.rf_amp_temp_label, 1, 3)

        # Water Temp
        values_layout.addWidget(QLabel("Water Temp:"), 2, 2)
        self.water_temp_label = QLabel("--- °C")
        self.water_temp_label.setStyleSheet("color: #00BFFF; font-size: 13px; font-weight: bold;")
        values_layout.addWidget(self.water_temp_label, 2, 3)

        values_layout.setColumnStretch(4, 1)

        layout.addLayout(values_layout)

        return group

    def create_power_status_group(self):
        """전원 상태 그룹"""
        group = QGroupBox("Power Status")
        layout = QVBoxLayout(group)
        layout.setSpacing(5)

        bits = [
            ('dc_status', 'DC Status'),
            ('pfc_status', 'PFC Status')
        ]

        for key, label in bits:
            indicator = StatusIndicator(label, "disconnected")
            self.status_indicators[key] = indicator
            layout.addWidget(indicator)

        return group

    def create_safety_group(self):
        """안전 상태 그룹"""
        group = QGroupBox("Safety")
        layout = QVBoxLayout(group)
        layout.setSpacing(5)

        bits = [
            ('interlock', 'Interlock')
        ]

        for key, label in bits:
            indicator = StatusIndicator(label, "disconnected")
            self.status_indicators[key] = indicator
            layout.addWidget(indicator)

        return group

    def create_failure_group(self):
        """고장 상태 그룹"""
        group = QGroupBox("AC & Power Failure")
        layout = QVBoxLayout(group)
        layout.setSpacing(5)

        bits = [
            ('ac_fail', 'AC Fail')
        ]

        for key, label in bits:
            indicator = StatusIndicator(label, "disconnected")
            self.status_indicators[key] = indicator
            layout.addWidget(indicator)

        return group

    def create_cooling_group(self):
        """냉각 시스템 그룹"""
        group = QGroupBox("Cooling System")
        layout = QVBoxLayout(group)
        layout.setSpacing(5)

        bits = [
            ('fan1_fail', 'Fan 1 Fail'),
            ('fan2_fail', 'Fan 2 Fail'),
            ('fan3_fail', 'Fan 3 Fail'),
            ('fan4_fail', 'Fan 4 Fail'),
            ('fan5_fail', 'Fan 5 Fail'),
            ('fan6_fail', 'Fan 6 Fail'),
            ('waterflow_fail', 'Water Flow Fail'),
            ('over_water_temper', 'Over Water Temp')
        ]

        for key, label in bits:
            indicator = StatusIndicator(label, "disconnected")
            self.status_indicators[key] = indicator
            layout.addWidget(indicator)

        return group

    def create_over_conditions_group(self):
        """과부하 상태 그룹"""
        group = QGroupBox("Over Conditions")
        layout = QVBoxLayout(group)
        layout.setSpacing(5)

        bits = [
            ('over_amp_temper', 'Over Amp Temp'),
            ('over_dc_out', 'Over DC Out'),
            ('over_pfc', 'Over PFC'),
            ('over_pfc_vt', 'Over PFC VT')
        ]

        for key, label in bits:
            indicator = StatusIndicator(label, "disconnected")
            self.status_indicators[key] = indicator
            layout.addWidget(indicator)

        return group

    def create_sensor_group(self):
        """센서 읽기 그룹"""
        group = QGroupBox("Sensor Readings")
        layout = QVBoxLayout(group)
        layout.setSpacing(5)

        bits = [
            ('dcc_dcout_voltage', 'DCC DC Voltage'),
            ('dcc_dcout_current', 'DCC DC Current'),
            ('dcc_pfcout_current', 'DCC PFC Current'),
            ('dcc_rfamp_temp', 'DCC RF Amp Temp'),
            ('dcc_waterplate_temp', 'DCC Water Temp'),
            ('gate_pa1_isens', 'Gate PA1 I-Sens'),
            ('gate_pa1_vsens', 'Gate PA1 V-Sens'),
            ('gate_pa1_temp', 'Gate PA1 Temp'),
            ('gate_pa2_isens', 'Gate PA2 I-Sens'),
            ('gate_pa2_vsens', 'Gate PA2 V-Sens'),
            ('gate_pa2_temp', 'Gate PA2 Temp'),
            ('gate_bias12', 'Gate Bias 1/2')
        ]

        for key, label in bits:
            indicator = StatusIndicator(label, "disconnected")
            self.status_indicators[key] = indicator
            layout.addWidget(indicator)

        return group

    def create_color_guide(self):
        """컬러 가이드"""
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: #3b4252; border-radius: 8px; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)

        title_label = QLabel("상태 표시 색상 가이드")
        title_label.setStyleSheet("color: #88c0d0; font-weight: bold; font-size: 12px;")
        layout.addWidget(title_label)

        guide_layout = QHBoxLayout()
        guide_layout.setSpacing(20)

        color_guides = [
            ("정상 (Normal/Active)", "#4CAF50", "#ffffff"),
            ("에러/고장 (Error/Fail)", "#F44336", "#ffffff"),
            ("비활성 (Inactive/Off)", "#9E9E9E", "#ffffff"),
            ("연결 없음 (Disconnected)", "#555555", "#aaaaaa")
        ]

        for text, bg_color, text_color in color_guides:
            guide_item = QVBoxLayout()
            guide_item.setSpacing(3)

            sample = QLabel("●")
            sample.setAlignment(Qt.AlignCenter)
            sample.setFixedSize(30, 30)
            sample.setStyleSheet(f"""
                QLabel {{
                    background-color: {bg_color};
                    color: {text_color};
                    border-radius: 15px;
                    font-size: 16px;
                    font-weight: bold;
                }}
            """)
            guide_item.addWidget(sample, 0, Qt.AlignCenter)

            desc_label = QLabel(text)
            desc_label.setStyleSheet("color: #d8dee9; font-size: 11px;")
            desc_label.setAlignment(Qt.AlignCenter)
            desc_label.setWordWrap(True)
            guide_item.addWidget(desc_label)

            guide_layout.addLayout(guide_item)

        layout.addLayout(guide_layout)
        return frame

    def create_h_line(self):
        """수평선 생성"""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #4c566a;")
        return line

    def toggle_auto_refresh(self, state):
        """자동 갱신 on/off 토글"""
        self.auto_refresh_enabled = (state == Qt.Checked)
        if self.auto_refresh_enabled:
            self.auto_refresh_timer.start(self.refresh_interval)
            self.status_led.setStyleSheet("color: #4CAF50; font-size: 16px;")
            self.load_status()  # 즉시 한 번 로드
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log(
                    f"[INFO] DCC 자동 갱신 활성화: {self.refresh_interval}ms",
                    "cyan"
                )
        else:
            self.auto_refresh_timer.stop()
            self.status_led.setStyleSheet("color: #757575; font-size: 16px;")
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log(
                    "[INFO] DCC 자동 갱신 비활성화",
                    "yellow"
                )

    def change_refresh_interval(self, text):
        """갱신 간격 변경"""
        # "1000ms" -> 1000 변환
        interval = int(text.replace("ms", ""))
        self.refresh_interval = interval

        # 타이머가 실행 중이면 재시작
        if self.auto_refresh_enabled and self.auto_refresh_timer.isActive():
            self.auto_refresh_timer.stop()
            self.auto_refresh_timer.start(self.refresh_interval)

            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log(
                    f"[INFO] DCC 갱신 간격 변경: {self.refresh_interval}ms",
                    "cyan"
                )

    def manual_refresh(self):
        """수동 새로 고침"""
        self.load_status()

    def load_status(self):
        """DCC 상태 조회"""
        # LED 깜빡임 (주황색) - 최소 150ms 유지
        self.status_led.setStyleSheet("color: #FF9800; font-size: 16px;")

        if not self.parent_window:
            self.status_led.setStyleSheet("color: #4CAF50; font-size: 16px;")
            return

        # 네트워크 매니저 확인
        if not hasattr(self.parent_window, 'network_manager'):
            self.status_led.setStyleSheet("color: #4CAF50; font-size: 16px;")
            return

        if not self.parent_window.network_manager.client_thread:
            # 연결 없음 상태로 표시
            for key, indicator in self.status_indicators.items():
                indicator.set_status("disconnected", f"{key.replace('_', ' ').title()}: N/A")
            self.status_led.setStyleSheet("color: #4CAF50; font-size: 16px;")
            return

        # CMD_SYSTEM_CONTROL + SUBCMD_GET_DCC_IF
        result = self.parent_window.network_manager.client_thread.send_command(
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
                    # 상태 값 업데이트
                    self.status_value_label.setText(f"0x{dcc_if['dcc_status']:08X}")
                    self.voltage_label.setText(f"{dcc_if['dc_voltage']:.2f} V")
                    self.current_label.setText(f"{dcc_if['dc_current']:.2f} A")
                    self.pfc_current_label.setText(f"{dcc_if['pfc_current']:.2f} A")
                    self.rf_amp_temp_label.setText(f"{dcc_if['rf_amp_temp']:.1f} °C")
                    self.water_temp_label.setText(f"{dcc_if['water_temp']:.1f} °C")

                    # 디버깅: ac_fail 비트 값 로그
                    if 'ac_fail' in dcc_if['status_bits']:
                        ac_fail_value = dcc_if['status_bits']['ac_fail']
                        if hasattr(self.parent_window, 'log_manager'):
                            self.parent_window.log_manager.write_log(
                                f"[DEBUG] DCC ac_fail bit = {ac_fail_value} (status=0x{dcc_if['dcc_status']:08X})",
                                "yellow"
                            )

                    # 상태 비트 업데이트 (StatusIndicator 사용)
                    for key, indicator in self.status_indicators.items():
                        bit_value = dcc_if['status_bits'].get(key, False)
                        status_type = self.determine_status_type(key, bit_value)
                        # 라벨 텍스트 생성
                        label_text = key.replace('_', ' ').title()
                        if bit_value:
                            label_text += ": ON" if not self.bit_status_config[key]['normal_on_zero'] else ": FAIL"
                        else:
                            label_text += ": OFF" if not self.bit_status_config[key]['normal_on_zero'] else ": OK"
                        indicator.set_status(status_type, label_text)
        else:
            # 에러 발생 - 연결 없음으로 표시
            for key, indicator in self.status_indicators.items():
                indicator.set_status("disconnected", f"{key.replace('_', ' ').title()}: N/A")

        # LED 복구 (녹색) - 150ms 지연
        if self.auto_refresh_enabled:
            QTimer.singleShot(150, lambda: self.status_led.setStyleSheet("color: #4CAF50; font-size: 16px;"))

    def determine_status_type(self, bit_key, bit_value):
        """
        비트 값과 설정에 따라 상태 타입 결정
        Returns: "normal", "error", "inactive", "disconnected"
        """
        config = self.bit_status_config.get(bit_key, {'normal_on_zero': False})
        normal_on_zero = config['normal_on_zero']

        # normal_on_zero가 True: 0일 때 정상 (fail 비트들)
        # normal_on_zero가 False: 1일 때 정상 (power/sensor 비트들)

        if normal_on_zero:
            # 0일 때 정상, 1일 때 에러
            if bit_value:
                return "error"
            else:
                return "normal"
        else:
            # 1일 때 정상, 0일 때 비활성
            if bit_value:
                return "normal"
            else:
                return "inactive"

    def closeEvent(self, event):
        """다이얼로그 닫기"""
        if self.auto_refresh_timer.isActive():
            self.auto_refresh_timer.stop()
        super().closeEvent(event)
