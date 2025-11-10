"""
Arc Management Widget
아크 관리 설정
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QRadioButton, QSpinBox, QDoubleSpinBox, QButtonGroup, QMessageBox, QGridLayout  # ← 추가
)
from PyQt5.QtCore import Qt
from rf_protocol import RFProtocol
from developer_data_manager import DeveloperDataManager
from ui_widgets import SmartSpinBox, SmartDoubleSpinBox

class ArcManagementWidget(QGroupBox):
    """Arc Management 설정 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("Arc Management", parent)
        self.parent = parent
        self.network_manager = network_manager
        self.dev_data_manager = DeveloperDataManager()
        
        self.setCheckable(True)
        self.setChecked(True)  # 기본 펼침
        self.toggled.connect(self.on_toggle)
        
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        self.main_layout = QVBoxLayout(self)
        
        # ========================================
        # Reflected Arc Detection
        # ========================================
        reflected_group = QGroupBox("Reflected Arc Detection")
        reflected_layout = QVBoxLayout(reflected_group)

        # Enable/Disable (라디오 버튼은 그대로)
        reflected_enable_layout = QHBoxLayout()
        reflected_enable_layout.addWidget(QLabel("Enable:"))
        self.reflected_arc_group = QButtonGroup()
        self.reflected_arc_enable = QRadioButton("Enabled")
        self.reflected_arc_disable = QRadioButton("Disabled")
        self.reflected_arc_disable.setChecked(True)
        self.reflected_arc_group.addButton(self.reflected_arc_enable)
        self.reflected_arc_group.addButton(self.reflected_arc_disable)
        reflected_enable_layout.addWidget(self.reflected_arc_enable)
        reflected_enable_layout.addWidget(self.reflected_arc_disable)
        reflected_enable_layout.addStretch()
        reflected_layout.addLayout(reflected_enable_layout)

        # Threshold만 GridLayout으로
        threshold_grid = QGridLayout()
        threshold_grid.addWidget(QLabel("Threshold:"), 0, 0)
        self.reflected_threshold_spin = SmartDoubleSpinBox()
        self.reflected_threshold_spin.setRange(0.0, 1000.0)
        self.reflected_threshold_spin.setValue(10.0)
        self.reflected_threshold_spin.setSuffix(" W")
        self.reflected_threshold_spin.setDecimals(1)
        threshold_grid.addWidget(self.reflected_threshold_spin, 0, 1)
        threshold_grid.setColumnStretch(2, 1)
        reflected_layout.addLayout(threshold_grid)

        self.main_layout.addWidget(reflected_group)
        
        # ========================================
        # External Arc Input
        # ========================================
        external_group = QGroupBox("External Arc Input")
        external_layout = QVBoxLayout(external_group)
        
        # Enable/Disable
        external_enable_layout = QHBoxLayout()
        external_enable_layout.addWidget(QLabel("Enable:"))
        
        self.external_arc_group = QButtonGroup()
        self.external_arc_enable = QRadioButton("Enabled")
        self.external_arc_disable = QRadioButton("Disabled")
        self.external_arc_disable.setChecked(True)
        
        self.external_arc_group.addButton(self.external_arc_enable)
        self.external_arc_group.addButton(self.external_arc_disable)
        
        external_enable_layout.addWidget(self.external_arc_enable)
        external_enable_layout.addWidget(self.external_arc_disable)
        external_enable_layout.addStretch()
        external_layout.addLayout(external_enable_layout)
        
        # RF Power Latch State
        latch_layout = QHBoxLayout()
        latch_layout.addWidget(QLabel("RF Power Latch:"))
        
        self.latch_group = QButtonGroup()
        self.latch_turn_off = QRadioButton("Turn Off")
        self.latch_turn_on = QRadioButton("Turn On")
        self.latch_turn_off.setChecked(True)
        
        self.latch_group.addButton(self.latch_turn_off)
        self.latch_group.addButton(self.latch_turn_on)
        
        latch_layout.addWidget(self.latch_turn_off)
        latch_layout.addWidget(self.latch_turn_on)
        latch_layout.addStretch()
        external_layout.addLayout(latch_layout)
        
        self.main_layout.addWidget(external_group)
        
        # ========================================
        # Timing Parameters
        # ========================================
        timing_group = QGroupBox("Timing Parameters")
        timing_layout = QGridLayout(timing_group)  # ← VBoxLayout → QGridLayout
        row = 0

        # Suppression Time
        timing_layout.addWidget(QLabel("Suppression Time:"), row, 0)
        self.suppression_time_spin = SmartSpinBox()
        self.suppression_time_spin.setRange(0, 511)
        self.suppression_time_spin.setValue(0)
        self.suppression_time_spin.setSuffix(" μs")
        self.suppression_time_spin.setToolTip("0=Disabled, 5~511 μs")
        timing_layout.addWidget(self.suppression_time_spin, row, 1)
        timing_layout.addWidget(QLabel("(0=Disabled, 5~511)"), row, 2)
        row += 1

        # Initial Delay
        timing_layout.addWidget(QLabel("Initial Delay:"), row, 0)
        self.initial_delay_spin = SmartSpinBox()
        self.initial_delay_spin.setRange(0, 10000)
        self.initial_delay_spin.setValue(0)
        self.initial_delay_spin.setSuffix(" ms")
        timing_layout.addWidget(self.initial_delay_spin, row, 1)
        timing_layout.addWidget(QLabel("(0~10,000)"), row, 2)
        row += 1

        # Setpoint Delay
        timing_layout.addWidget(QLabel("Setpoint Delay:"), row, 0)
        self.setpoint_delay_spin = SmartSpinBox()
        self.setpoint_delay_spin.setRange(0, 245)
        self.setpoint_delay_spin.setValue(0)
        self.setpoint_delay_spin.setSuffix(" ms")
        timing_layout.addWidget(self.setpoint_delay_spin, row, 1)
        timing_layout.addWidget(QLabel("(0~245)"), row, 2)

        timing_layout.setColumnStretch(3, 1)  # 4열 stretch
        self.main_layout.addWidget(timing_group)
        
        # ========================================
        # Arc Output Signal
        # ========================================
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Arc Output Signal:"))
        
        self.output_signal_group = QButtonGroup()
        self.output_signal_enable = QRadioButton("Enabled")
        self.output_signal_disable = QRadioButton("Disabled")
        self.output_signal_disable.setChecked(True)
        
        self.output_signal_group.addButton(self.output_signal_enable)
        self.output_signal_group.addButton(self.output_signal_disable)
        
        output_layout.addWidget(self.output_signal_enable)
        output_layout.addWidget(self.output_signal_disable)
        output_layout.addStretch()
        self.main_layout.addLayout(output_layout)
        
        # ========================================
        # Number of Attempts
        # ========================================
        attempts_grid = QGridLayout()
        attempts_grid.addWidget(QLabel("Number of Attempts:"), 0, 0)
        self.attempts_spin = SmartSpinBox()
        self.attempts_spin.setRange(0, 250)
        self.attempts_spin.setValue(10)
        self.attempts_spin.setToolTip("0=Unlimited, 1~250")
        attempts_grid.addWidget(self.attempts_spin, 0, 1)
        attempts_grid.addWidget(QLabel("(0=Unlimited, 1~250)"), 0, 2)
        attempts_grid.setColumnStretch(3, 1)
        self.main_layout.addLayout(attempts_grid)
        
        # ========================================
        # 버튼
        # ========================================
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        load_button = QPushButton("Load")
        load_button.clicked.connect(self.load_settings)
        button_layout.addWidget(load_button)
        
        apply_button = QPushButton("Apply")
        apply_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        apply_button.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_button)
        
        self.main_layout.addLayout(button_layout)
    
    def on_toggle(self, checked):
        """접기/펼치기"""
        for i in range(self.main_layout.count()):
            widget = self.main_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(checked)
    
    def load_settings(self):
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_ARC_MANAGEMENT_GET,
            RFProtocol.SUBCMD_ARC_MANAGEMENT,
            wait_response=True,
            sync=True
        )
        
        if result.success and result.response_data:
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and len(parsed['data']) >= 16:
                settings = self.dev_data_manager.parse_arc_management_data(parsed['data'])
                
                if settings:
                    # UI 업데이트
                    if settings['en_reflected_arc_det']:
                        self.reflected_arc_enable.setChecked(True)
                    else:
                        self.reflected_arc_disable.setChecked(True)
                    
                    if settings['en_external_arc_input']:
                        self.external_arc_enable.setChecked(True)
                    else:
                        self.external_arc_disable.setChecked(True)
                    
                    if settings['rfpower_latch_state']:
                        self.latch_turn_on.setChecked(True)
                    else:
                        self.latch_turn_off.setChecked(True)
                    
                    if settings['en_arc_output_signal']:
                        self.output_signal_enable.setChecked(True)
                    else:
                        self.output_signal_disable.setChecked(True)
                    ##########
                    all_zero = all(v == 0 or v == False for k, v in settings.items() 
                    if k != 'reflected_arc_threshold')
        
                    if all_zero:
                        QMessageBox.warning(
                            self, 
                            "경고", 
                            "펌웨어에서 모든 값이 0으로 설정되어 있습니다.\n"
                            "이 설정은 유효하지 않을 수 있으니 값을 변경 후 Apply 하세요."
                        )
                    ##########
                    self.suppression_time_spin.setValue(settings['suppression_time'])
                    self.initial_delay_spin.setValue(settings['initial_delay_time'])
                    self.setpoint_delay_spin.setValue(settings['setpoint_delay_time'])
                    self.attempts_spin.setValue(settings['no_of_attempts'])
                    self.reflected_threshold_spin.setValue(settings['reflected_arc_threshold'])
                    
                    QMessageBox.information(self, "완료", "Arc Management 설정을 로드했습니다.")
                else:
                    QMessageBox.warning(self, "오류", "데이터 파싱 실패")
            else:
                QMessageBox.warning(self, "오류", "응답 데이터 형식 오류")
        else:
            QMessageBox.warning(self, "오류", "설정 로드 실패")
    
    def apply_settings(self):
        """설정 적용 (유효성 검사 추가)"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        # 설정 수집
        settings = {
            'en_reflected_arc_det': self.reflected_arc_enable.isChecked(),
            'en_external_arc_input': self.external_arc_enable.isChecked(),
            'rfpower_latch_state': self.latch_turn_on.isChecked(),
            'en_arc_output_signal': self.output_signal_enable.isChecked(),
            'suppression_time': self.suppression_time_spin.value(),
            'initial_delay_time': self.initial_delay_spin.value(),
            'setpoint_delay_time': self.setpoint_delay_spin.value(),
            'no_of_attempts': self.attempts_spin.value(),
            'reflected_arc_threshold': self.reflected_threshold_spin.value()
        }
        
        # ✅ 유효성 검사
        all_disabled = (
            not settings['en_reflected_arc_det'] and
            not settings['en_external_arc_input'] and
            not settings['en_arc_output_signal']
        )
        
        if all_disabled and settings['reflected_arc_threshold'] == 0.0:
            reply = QMessageBox.question(
                self, 
                "경고", 
                "모든 Arc 기능이 비활성화되고 임계값이 0입니다.\n"
                "이 설정은 펌웨어에서 거부될 수 있습니다.\n\n"
                "계속하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # 데이터 생성 및 전송
        success, data, message = self.dev_data_manager.create_arc_management_data(settings)
        
        if not success:
            QMessageBox.critical(self, "오류", message)
            return
        
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_ARC_MANAGEMENT_SET,
            RFProtocol.SUBCMD_ARC_MANAGEMENT,
            data=data,
            wait_response=True,
            sync=True
        )
        
        if result.success:
            QMessageBox.information(self, "완료", "Arc Management 설정이 적용되었습니다.")
        else:
            QMessageBox.warning(self, "오류", f"설정 적용 실패: {result.message}")