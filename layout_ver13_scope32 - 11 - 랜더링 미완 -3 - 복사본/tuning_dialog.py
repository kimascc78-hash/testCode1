"""
Tuning Settings Dialog Module
RF 장비 튜닝 설정을 위한 다이얼로그 - 탭별 적용 기능 수정
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QFormLayout,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox,
    QScrollArea, QLabel, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
import ipaddress

from ui_widgets import SmartSpinBox, SmartDoubleSpinBox 


class ImprovedTuningDialog(QDialog):
    """개선된 튜닝 설정 다이얼로그 - 탭별 적용 기능"""
    
    # 탭별 적용 시그널
    tab_applied = pyqtSignal(str, dict)  # tab_name, settings
    
    def __init__(self, tuning_settings, parent=None):
        super().__init__(parent)
        self.tuning_settings = tuning_settings.copy()
        self.inputs = {}
        self.parent_window = parent
        
        # 탭별 설정 키 매핑 (영문 키 사용)
        self.tab_keys = {
            "control": ["Control Mode", "Regulation Mode"],
            "ramp": ["Ramp Mode", "Ramp Up Time", "Ramp Down Time"],
            "cex": ["CEX Enable", "CEX Mode", "CEX Output Phase", "RF Output Phase"],
            "pulse": [
                "Pulsing Type", "Pulsing Mode", "Pulse On/Off", "Sync Output",
                "Pulse0 Level", "Pulse1 Level", "Pulse2 Level", "Pulse3 Level",
                "Pulse0 Duty", "Pulse1 Duty", "Pulse2 Duty", "Pulse3 Duty",
                "Output Sync Delay", "Input Sync Delay", "Width Control", "Pulse Frequency"
            ],
            "frequency": ["Freq Tuning", "Retuning Mode", "Setting Mode", "Min Frequency", "Max Frequency", 
                         "Start Frequency", "Min Step", "Max Step", "Stop Gamma", "Return Gamma", "Set RF Frequency"],
            "bank": ["Bank1 Enable", "Bank1 Equation Enable", "Bank1 X0", "Bank1 A", "Bank1 B", "Bank1 C", "Bank1 D",
                     "Bank2 Enable", "Bank2 Equation Enable", "Bank2 X0", "Bank2 A", "Bank2 B", "Bank2 C", "Bank2 D"],
            "network": ["IP Address", "Subnet Mask", "Gateway", "DNS"]
        }
        
        # 한글 탭 이름을 영문 키로 매핑
        self.tab_name_mapping = {
            "제어": "control",
            "램프": "ramp", 
            "CEX": "cex",
            "펄스": "pulse",
            "주파수": "frequency",
            "Bank": "bank",  # 추가
            "네트워크": "network"
        }
        
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("튜닝 설정")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.resize(800, 660)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        
        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        
        # 각 탭 생성
        self.create_control_tab(self.tab_widget)
        self.create_ramp_tab(self.tab_widget)
        self.create_cex_tab(self.tab_widget)
        self.create_pulse_tab(self.tab_widget)
        self.create_frequency_tab(self.tab_widget)
        self.create_bank_tab(self.tab_widget) #bank 추가
        self.create_network_tab(self.tab_widget)
        
        main_layout.addWidget(self.tab_widget)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()

        # 현재 값을 기본값으로 저장 버튼
        save_default_btn = QPushButton("현재 값을 기본값으로 저장")
        save_default_btn.setStyleSheet("background-color: #2e7d32; font-weight: bold;")
        save_default_btn.clicked.connect(self.save_as_default)
        button_layout.addWidget(save_default_btn)

        # 기본값 복원 버튼
        reset_btn = QPushButton("기본값 복원")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)

        # 시스템 기본값으로 복원 버튼
        system_reset_btn = QPushButton("시스템 기본값 복원")
        system_reset_btn.setStyleSheet("background-color: #c62828; font-weight: bold;")
        system_reset_btn.clicked.connect(self.reset_to_system_defaults)
        button_layout.addWidget(system_reset_btn)

        button_layout.addStretch()

        # 취소/전체 적용 버튼
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        #apply_all_btn = QPushButton("전체 적용")
        #apply_all_btn.setDefault(True)
        #apply_all_btn.clicked.connect(self.apply_all_settings)
        #button_layout.addWidget(apply_all_btn)
        
        main_layout.addLayout(button_layout)
        
        # 스타일 적용
        self.apply_styles()
    
    def apply_styles(self):
        """다이얼로그 스타일 적용"""
        style_sheet = """
            QDialog {
                background-color: #1e1e2e;
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
                padding: 8px 12px;
                margin-right: 2px;
                border: 1px solid #444;
            }
            QTabBar::tab:selected {
                background: #00f0ff;
                color: #1e1e2e;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background: #3a3a4a;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #00f0ff;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #f0f8ff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #87ceeb;
                font-size: 13px;
            }
            QLabel {
                color: #dcdcdc;
                font-size: 12px;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #2e2e3e;
                border: 1px solid #00f0ff;
                border-radius: 3px;
                padding: 4px;
                color: #e0ffff;
                min-height: 20px;
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
                border: 2px solid #00f0ff;
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
        """
        self.setStyleSheet(style_sheet)
    
    def create_tab_apply_button(self, tab_name):
        """탭별 적용 버튼 생성"""
        apply_btn = QPushButton(f"{tab_name} 적용")
        apply_btn.setProperty("class", "tab-apply")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b00;
                border: 1px solid #ff8c00;
                color: #ffffff;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ff8c00;
                color: #1e1e2e;
            }
        """)
        # 한글 탭 이름을 그대로 전달 (apply_tab_settings에서 변환)
        apply_btn.clicked.connect(lambda: self.apply_tab_settings(tab_name))
        return apply_btn

    def create_tab_load_button(self, tab_name):
        """탭별 로드 버튼 생성"""
        load_btn = QPushButton("Load")
        load_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                border: 1px solid #4caf50;
                color: #ffffff;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4caf50;
                color: #1e1e2e;
            }
        """)
        # 한글 탭 이름을 그대로 전달 (load_tab_settings에서 변환)
        load_btn.clicked.connect(lambda: self.load_tab_settings(tab_name))
        return load_btn
    
    def create_control_tab(self, tab_widget):
        """제어 설정 탭"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 제어 모드 그룹
        control_group = QGroupBox("제어 모드")
        control_layout = QFormLayout(control_group)
        
        # Control Mode
        control_mode = QComboBox()
        control_mode.addItems(["User Port", "Serial", "Ethernet", "EtherCAT", "Serial+User", "Ethernet+User"])
        control_mode.setCurrentText(self.tuning_settings["Control Mode"])
        self.inputs["Control Mode"] = control_mode
        
        control_label = QLabel("제어 모드:")
        control_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        control_layout.addRow(control_label, control_mode)
        
        # Regulation Mode
        regulation_mode = QComboBox()
        regulation_mode.addItems(["Forward Power", "Load Power", "Voltage", "Current"])
        regulation_mode.setCurrentText(self.tuning_settings["Regulation Mode"])
        self.inputs["Regulation Mode"] = regulation_mode
        
        regulation_label = QLabel("조절 모드:")
        regulation_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        control_layout.addRow(regulation_label, regulation_mode)
        
        layout.addWidget(control_group)

        # 로드 및 적용 버튼
        button_layout = QHBoxLayout()
        load_btn = self.create_tab_load_button("제어")
        apply_btn = self.create_tab_apply_button("제어")
        button_layout.addWidget(load_btn)
        button_layout.addWidget(apply_btn)
        layout.addLayout(button_layout)

        layout.addStretch()

        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        tab_widget.addTab(tab, "제어")
    
    def create_ramp_tab(self, tab_widget):
        """램프 설정 탭"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 램프 설정 그룹
        ramp_group = QGroupBox("램프 설정")
        ramp_layout = QFormLayout(ramp_group)
        
        # Ramp Mode
        ramp_mode = QComboBox()
        ramp_mode.addItems(["Disable", "Enable", "Auto"])
        ramp_mode.setCurrentText(self.tuning_settings["Ramp Mode"])
        self.inputs["Ramp Mode"] = ramp_mode
        
        ramp_mode_label = QLabel("램프 모드:")
        ramp_mode_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        ramp_layout.addRow(ramp_mode_label, ramp_mode)
        
        # Ramp Up Time
        ramp_up_time = SmartDoubleSpinBox()
        ramp_up_time.setRange(0.0, 999.9)
        ramp_up_time.setSuffix(" ms")
        ramp_up_time.setValue(float(self.tuning_settings["Ramp Up Time"]))
        self.inputs["Ramp Up Time"] = ramp_up_time
        
        ramp_up_label = QLabel("램프 업 시간:")
        ramp_up_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        ramp_layout.addRow(ramp_up_label, ramp_up_time)
        
        # Ramp Down Time
        ramp_down_time = SmartDoubleSpinBox()
        ramp_down_time.setRange(0.0, 999.9)
        ramp_down_time.setSuffix(" ms")
        ramp_down_time.setValue(float(self.tuning_settings["Ramp Down Time"]))
        self.inputs["Ramp Down Time"] = ramp_down_time
        
        ramp_down_label = QLabel("램프 다운 시간:")
        ramp_down_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        ramp_layout.addRow(ramp_down_label, ramp_down_time)
        
        layout.addWidget(ramp_group)

        # 로드 및 적용 버튼
        button_layout = QHBoxLayout()
        load_btn = self.create_tab_load_button("램프")
        apply_btn = self.create_tab_apply_button("램프")
        button_layout.addWidget(load_btn)
        button_layout.addWidget(apply_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        tab_widget.addTab(tab, "램프")
    
    def create_cex_tab(self, tab_widget):
        """CEX 설정 탭"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # CEX 설정 그룹
        cex_group = QGroupBox("CEX 설정")
        cex_layout = QFormLayout(cex_group)
        
        # CEX Enable
        cex_enable = QComboBox()
        cex_enable.addItems(["Disable", "Enable"])
        cex_enable.setCurrentText(self.tuning_settings["CEX Enable"])
        self.inputs["CEX Enable"] = cex_enable
        
        cex_enable_label = QLabel("CEX 활성화:")
        cex_enable_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        cex_layout.addRow(cex_enable_label, cex_enable)
        
        # CEX Mode
        cex_mode = QComboBox()
        cex_mode.addItems(["Master", "Slave"])
        cex_mode.setCurrentText(self.tuning_settings["CEX Mode"])
        self.inputs["CEX Mode"] = cex_mode
        
        cex_mode_label = QLabel("CEX 모드:")
        cex_mode_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        cex_layout.addRow(cex_mode_label, cex_mode)
        
        # CEX Output Phase
        cex_output_phase = SmartDoubleSpinBox()
        cex_output_phase.setRange(0.0, 360.0)
        cex_output_phase.setSuffix("°")
        cex_output_phase.setValue(float(self.tuning_settings["CEX Output Phase"]))
        self.inputs["CEX Output Phase"] = cex_output_phase
        
        cex_output_label = QLabel("CEX 출력 위상:")
        cex_output_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        cex_layout.addRow(cex_output_label, cex_output_phase)
        
        # RF Output Phase
        rf_output_phase = SmartDoubleSpinBox()
        rf_output_phase.setRange(0.0, 360.0)
        rf_output_phase.setSuffix("°")
        rf_output_phase.setValue(float(self.tuning_settings["RF Output Phase"]))
        self.inputs["RF Output Phase"] = rf_output_phase
        
        rf_output_label = QLabel("RF 출력 위상:")
        rf_output_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        cex_layout.addRow(rf_output_label, rf_output_phase)
        
        layout.addWidget(cex_group)

        # 로드 및 적용 버튼
        button_layout = QHBoxLayout()
        load_btn = self.create_tab_load_button("CEX")
        apply_btn = self.create_tab_apply_button("CEX")
        button_layout.addWidget(load_btn)
        button_layout.addWidget(apply_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        tab_widget.addTab(tab, "CEX")
    
    def create_pulse_tab(self, tab_widget):
        """펄스 설정 탭 - 펌웨어 구조체 기준 전체 필드"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 펄스 설정 그룹
        pulse_group = QGroupBox("펄스 설정")
        pulse_layout = QFormLayout(pulse_group)
        
        # 1. Pulsing Type (SUBCMD 0x01)
        pulsing_type = QComboBox()
        pulsing_type.addItems(["Amplitude", "Phase"])
        pulsing_type.setCurrentText(self.tuning_settings.get("Pulsing Type", "Amplitude"))
        self.inputs["Pulsing Type"] = pulsing_type
        
        pulsing_type_label = QLabel("펄싱 타입:")
        pulsing_type_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(pulsing_type_label, pulsing_type)
        
        # 2. Pulsing Mode (SUBCMD 0x02)
        pulsing_mode = QComboBox()
        pulsing_mode.addItems(["Master", "Slave"])
        pulsing_mode.setCurrentText(self.tuning_settings.get("Pulsing Mode", "Master"))
        self.inputs["Pulsing Mode"] = pulsing_mode
        
        pulsing_mode_label = QLabel("펄싱 모드:")
        pulsing_mode_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(pulsing_mode_label, pulsing_mode)
        
        # 3. Pulse On/Off (SUBCMD 0x03)
        pulse_onoff = QComboBox()
        pulse_onoff.addItems(["Off", "On"])
        pulse_onoff.setCurrentText(self.tuning_settings.get("Pulse On/Off", "Off"))
        self.inputs["Pulse On/Off"] = pulse_onoff
        
        pulse_onoff_label = QLabel("펄스 On/Off:")
        pulse_onoff_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(pulse_onoff_label, pulse_onoff)
        
        # 4. Sync Output (SUBCMD 0x04)
        sync_output = QComboBox()
        sync_output.addItems(["Off", "On"])
        sync_output.setCurrentText(self.tuning_settings.get("Sync Output", "Off"))
        self.inputs["Sync Output"] = sync_output
        
        sync_output_label = QLabel("동기 출력:")
        sync_output_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(sync_output_label, sync_output)
        
        # 5-8. Pulse Level 0~3 (SUBCMD 0x05)
        for i in range(4):
            pulse_level = SmartDoubleSpinBox()
            pulse_level.setRange(0.0, 100.0)
            pulse_level.setSuffix(" %")
            default_val = "100.0" if i == 0 else "0.0"
            pulse_level.setValue(float(self.tuning_settings.get(f"Pulse{i} Level", default_val)))
            self.inputs[f"Pulse{i} Level"] = pulse_level
            
            level_label = QLabel(f"Pulse{i} 레벨:")
            level_label.setStyleSheet("color: #4169e1; font-weight: bold;")
            pulse_layout.addRow(level_label, pulse_level)
        
        # 9-12. Pulse Duty 0~3 (SUBCMD 0x06)
        for i in range(4):
            pulse_duty = SmartDoubleSpinBox()
            pulse_duty.setRange(5.0, 100.0)
            pulse_duty.setSuffix(" %")
            pulse_duty.setValue(float(self.tuning_settings.get(f"Pulse{i} Duty", "20.0")))
            self.inputs[f"Pulse{i} Duty"] = pulse_duty
            
            duty_label = QLabel(f"Pulse{i} 듀티:")
            duty_label.setStyleSheet("color: #4169e1; font-weight: bold;")
            pulse_layout.addRow(duty_label, pulse_duty)
        
        # 13. Output Sync Delay (SUBCMD 0x07)
        output_sync_delay = SmartSpinBox()
        output_sync_delay.setRange(0, 999999)
        output_sync_delay.setSuffix(" µs")
        output_sync_delay.setValue(int(float(self.tuning_settings.get("Output Sync Delay", "0"))))
        self.inputs["Output Sync Delay"] = output_sync_delay
        
        output_sync_label = QLabel("출력 동기 지연:")
        output_sync_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(output_sync_label, output_sync_delay)
        
        # 14. Input Sync Delay (SUBCMD 0x08)
        input_sync_delay = SmartSpinBox()
        input_sync_delay.setRange(0, 999999)
        input_sync_delay.setSuffix(" µs")
        input_sync_delay.setValue(int(float(self.tuning_settings.get("Input Sync Delay", "0"))))
        self.inputs["Input Sync Delay"] = input_sync_delay
        
        input_sync_label = QLabel("입력 동기 지연:")
        input_sync_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(input_sync_label, input_sync_delay)
        
        # 15. Width Control (SUBCMD 0x09)
        width_control = SmartSpinBox()
        width_control.setRange(-999999, 999999)
        width_control.setSuffix(" × 0.5µs")
        width_control.setValue(int(float(self.tuning_settings.get("Width Control", "0"))))
        self.inputs["Width Control"] = width_control
        
        width_label = QLabel("펄스 폭 제어:")
        width_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(width_label, width_control)
        
        # 16. Pulse Frequency (SUBCMD 0x0A)
        pulse_freq = SmartSpinBox()
        pulse_freq.setRange(0, 999999)
        pulse_freq.setSuffix(" × 0.5µs")
        pulse_freq.setValue(int(float(self.tuning_settings.get("Pulse Frequency", "10000"))))
        self.inputs["Pulse Frequency"] = pulse_freq
        
        pulse_freq_label = QLabel("펄스 주파수:")
        pulse_freq_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(pulse_freq_label, pulse_freq)
        
        layout.addWidget(pulse_group)

        # 로드 및 적용 버튼
        button_layout = QHBoxLayout()
        load_btn = self.create_tab_load_button("펄스")
        apply_btn = self.create_tab_apply_button("펄스")
        button_layout.addWidget(load_btn)
        button_layout.addWidget(apply_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        tab_widget.addTab(tab, "펄스")
    
    def create_frequency_tab(self, tab_widget):
        """주파수 설정 탭"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 주파수 튜닝 그룹
        freq_group = QGroupBox("주파수 튜닝")
        freq_layout = QFormLayout(freq_group)
        
        # Freq Tuning
        freq_tuning = QComboBox()
        freq_tuning.addItems(["Disable", "Enable"])
        freq_tuning.setCurrentText(self.tuning_settings["Freq Tuning"])
        self.inputs["Freq Tuning"] = freq_tuning
        
        freq_tuning_label = QLabel("주파수 튜닝:")
        freq_tuning_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        freq_layout.addRow(freq_tuning_label, freq_tuning)
        
        # Retuning Mode
        retuning_mode = QComboBox()
        retuning_mode.addItems(["Disable", "Enable"])  # ✅ 수정
        retuning_mode.setCurrentText(self.tuning_settings["Retuning Mode"])
        self.inputs["Retuning Mode"] = retuning_mode
        
        retuning_mode_label = QLabel("재튜닝 모드:")
        retuning_mode_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        freq_layout.addRow(retuning_mode_label, retuning_mode)
        
        # Setting Mode
        setting_mode = QComboBox()
        setting_mode.addItems(["Disable", "preset", "auto"])  # ✅ 수정
        setting_mode.setCurrentText(self.tuning_settings["Setting Mode"])
        self.inputs["Setting Mode"] = setting_mode
        
        setting_mode_label = QLabel("튜닝 모드:")
        setting_mode_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        freq_layout.addRow(setting_mode_label, setting_mode)
        
        layout.addWidget(freq_group)
        
        # 주파수 범위 그룹
        range_group = QGroupBox("주파수 범위")
        range_layout = QFormLayout(range_group)
        
        # Min Frequency
        min_freq = SmartDoubleSpinBox()
        min_freq.setRange(0.0, 50.0)
        min_freq.setSuffix(" MHz")
        min_freq.setValue(float(self.tuning_settings["Min Frequency"]))
        self.inputs["Min Frequency"] = min_freq
        
        min_freq_label = QLabel("최소 주파수:")
        min_freq_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        range_layout.addRow(min_freq_label, min_freq)
        
        # Max Frequency
        max_freq = SmartDoubleSpinBox()
        max_freq.setRange(0.0, 50.0)
        max_freq.setSuffix(" MHz")
        max_freq.setValue(float(self.tuning_settings["Max Frequency"]))
        self.inputs["Max Frequency"] = max_freq
        
        max_freq_label = QLabel("최대 주파수:")
        max_freq_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        range_layout.addRow(max_freq_label, max_freq)
        
        # Start Frequency
        start_freq = SmartDoubleSpinBox()
        start_freq.setRange(0.0, 50.0)
        start_freq.setSuffix(" MHz")
        start_freq.setValue(float(self.tuning_settings["Start Frequency"]))
        self.inputs["Start Frequency"] = start_freq
        
        start_freq_label = QLabel("시작 주파수:")
        start_freq_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        range_layout.addRow(start_freq_label, start_freq)
        
        # Set RF Frequency
        set_rf_freq = SmartDoubleSpinBox()
        set_rf_freq.setRange(0.0, 50.0)
        set_rf_freq.setSuffix(" MHz")
        set_rf_freq.setValue(float(self.tuning_settings["Set RF Frequency"]))
        self.inputs["Set RF Frequency"] = set_rf_freq
        
        set_rf_freq_label = QLabel("RF 주파수 설정:")
        set_rf_freq_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        range_layout.addRow(set_rf_freq_label, set_rf_freq)
        
        layout.addWidget(range_group)
        
        # 스텝 및 감마 설정 그룹
        step_group = QGroupBox("스텝 및 감마 설정")
        step_layout = QFormLayout(step_group)
        
        # Min Step
        min_step = SmartDoubleSpinBox()
        min_step.setRange(0.0, 10.0)
        min_step.setSuffix(" kHz")
        min_step.setValue(float(self.tuning_settings["Min Step"]))
        self.inputs["Min Step"] = min_step
        
        min_step_label = QLabel("최소 스텝:")
        min_step_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        step_layout.addRow(min_step_label, min_step)
        
        # Max Step
        max_step = SmartDoubleSpinBox()
        max_step.setRange(0.0, 100.0)
        max_step.setSuffix(" kHz")
        max_step.setValue(float(self.tuning_settings["Max Step"]))
        self.inputs["Max Step"] = max_step
        
        max_step_label = QLabel("최대 스텝:")
        max_step_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        step_layout.addRow(max_step_label, max_step)
        
        # Stop Gamma
        stop_gamma = SmartDoubleSpinBox()
        stop_gamma.setRange(0.0, 1.0)
        stop_gamma.setDecimals(3)
        stop_gamma.setValue(float(self.tuning_settings["Stop Gamma"]))
        self.inputs["Stop Gamma"] = stop_gamma
        
        stop_gamma_label = QLabel("정지 감마:")
        stop_gamma_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        step_layout.addRow(stop_gamma_label, stop_gamma)
        
        # Return Gamma
        return_gamma = SmartDoubleSpinBox()
        return_gamma.setRange(0.0, 1.0)
        return_gamma.setDecimals(3)
        return_gamma.setValue(float(self.tuning_settings["Return Gamma"]))
        self.inputs["Return Gamma"] = return_gamma
        
        return_gamma_label = QLabel("복귀 감마:")
        return_gamma_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        step_layout.addRow(return_gamma_label, return_gamma)
        
        layout.addWidget(step_group)

        # 로드 및 적용 버튼
        button_layout = QHBoxLayout()
        load_btn = self.create_tab_load_button("주파수")
        apply_btn = self.create_tab_apply_button("주파수")
        button_layout.addWidget(load_btn)
        button_layout.addWidget(apply_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        tab_widget.addTab(tab, "주파수")
    
    def create_network_tab(self, tab_widget):
        """네트워크 설정 탭 - MAC Address 추가"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # ========================================
        # 네트워크 설정 그룹 (기존 유지)
        # ========================================
        network_group = QGroupBox("네트워크 설정")
        network_layout = QFormLayout(network_group)
        
        # IP Address
        ip_address = QLineEdit()
        ip_address.setText(self.tuning_settings["IP Address"])
        self.inputs["IP Address"] = ip_address
        
        ip_label = QLabel("IP Address:")
        ip_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        network_layout.addRow(ip_label, ip_address)
        
        # Subnet Mask
        subnet_mask = QLineEdit()
        subnet_mask.setText(self.tuning_settings["Subnet Mask"])
        self.inputs["Subnet Mask"] = subnet_mask
        
        subnet_label = QLabel("Subnet Mask:")
        subnet_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        network_layout.addRow(subnet_label, subnet_mask)
        
        # Gateway
        gateway = QLineEdit()
        gateway.setText(self.tuning_settings["Gateway"])
        self.inputs["Gateway"] = gateway
        
        gateway_label = QLabel("Gateway:")
        gateway_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        network_layout.addRow(gateway_label, gateway)
        
        # DNS
        dns = QLineEdit()
        dns.setText(self.tuning_settings["DNS"])
        self.inputs["DNS"] = dns
        
        dns_label = QLabel("DNS:")
        dns_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        network_layout.addRow(dns_label, dns)
        
        layout.addWidget(network_group)
        
        # ========================================
        # 추가: MAC Address 그룹
        # ========================================
        mac_group = QGroupBox("MAC Address (읽기 전용)")
        mac_layout = QHBoxLayout(mac_group)
        
        self.mac_display = QLineEdit()
        self.mac_display.setReadOnly(True)
        self.mac_display.setPlaceholderText("00:00:00:00:00:00")
        self.mac_display.setStyleSheet("""
            QLineEdit {
                background-color: #3e3e4e;
                color: #00ff00;
                border: 1px solid #555555;
                padding: 5px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        mac_layout.addWidget(self.mac_display)
        
        mac_refresh_btn = QPushButton("Refresh")
        mac_refresh_btn.setFixedWidth(100)
        mac_refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d4aa;
                color: #1e1e2e;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #00f0ff;
            }
        """)
        mac_refresh_btn.clicked.connect(self.read_mac_address)
        mac_layout.addWidget(mac_refresh_btn)
        
        layout.addWidget(mac_group)
        
        # ========================================
        # 연결 테스트 버튼 (기존 유지)
        # ========================================
        test_btn = QPushButton("연결 테스트")
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)
        
        # 탭별 적용 버튼
        apply_btn = self.create_tab_apply_button("네트워크")
        layout.addWidget(apply_btn)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        tab_widget.addTab(tab, "네트워크")

    def read_mac_address(self):
        """MAC Address 조회 (CMD=0x12, SUBCMD=0x00)"""
        if not self.parent_window or not hasattr(self.parent_window, 'network_manager'):
            QMessageBox.warning(self, "오류", "네트워크 매니저를 찾을 수 없습니다.")
            return
        
        if not self.parent_window.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.\n먼저 네트워크를 연결하세요.")
            return
        
        try:
            from rf_protocol import RFProtocol
            
            # CMD=0x12, SUBCMD=0x00 (매뉴얼 확인)
            result = self.parent_window.network_manager.client_thread.send_command(
                cmd=RFProtocol.CMD_NETWORK_MAC_GET,
                subcmd=RFProtocol.SUBCMD_NETWORK_MAC_GET,
                data=b'',
                wait_response=True,
                sync=True,
                timeout=2.0
            )
            
            if result.success:
                parsed = RFProtocol.parse_response(result.response_data)
                if parsed and len(parsed['data']) >= 6:
                    mac_bytes = parsed['data'][:6]
                    mac_str = ':'.join(f'{b:02X}' for b in mac_bytes)
                    self.mac_display.setText(mac_str)
                    
                    # 로그 출력
                    if hasattr(self.parent_window, 'log_manager'):
                        self.parent_window.log_manager.write_log(
                            f"[INFO] MAC Address: {mac_str}", "cyan"
                        )
                    
                    QMessageBox.information(self, "성공", f"MAC Address 조회 완료\n\n{mac_str}")
                else:
                    QMessageBox.warning(self, "오류", "MAC Address 데이터가 올바르지 않습니다.")
            else:
                QMessageBox.warning(self, "오류", f"MAC Address 조회 실패\n\n{result.message}")
        
        except Exception as e:
            QMessageBox.critical(self, "오류", f"MAC Address 조회 중 오류 발생:\n\n{str(e)}")
    
    def validate_ip_address(self, ip_str):
        """IP 주소 유효성 검사"""
        try:
            ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False
    
    def test_connection(self):
        """네트워크 연결 테스트"""
        ip = self.inputs["IP Address"].text()
        if not self.validate_ip_address(ip):
            QMessageBox.warning(self, "오류", "유효하지 않은 IP 주소입니다.")
            return
        
        # 실제 연결 테스트 로직은 여기에 구현
        QMessageBox.information(self, "연결 테스트", f"IP {ip}로 연결 테스트를 수행합니다.")
    
    def get_tab_settings(self, tab_name):
        """특정 탭의 설정값만 추출 - 수정된 버전"""
        tab_settings = {}
        if tab_name in self.tab_keys:
            for key in self.tab_keys[tab_name]:
                if key in self.inputs:
                    widget = self.inputs[key]
                    if isinstance(widget, QComboBox):
                        tab_settings[key] = widget.currentText()
                    elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                        tab_settings[key] = str(widget.value())
                    elif isinstance(widget, QLineEdit):
                        tab_settings[key] = widget.text()
        return tab_settings
    
    def apply_tab_settings(self, tab_name):
        """탭별 설정 적용 - 수정된 버전"""
        # 디버깅을 위한 로그 출력
        if hasattr(self.parent_window, 'write_log'):
            self.parent_window.write_log(f"[DEBUG] 탭별 적용 시도: {tab_name}", "yellow")
        
        # 현재 입력값들을 임시로 업데이트
        temp_settings = self.tuning_settings.copy()
        
        # 현재 입력값들을 temp_settings에 반영
        for key, widget in self.inputs.items():
            if isinstance(widget, QComboBox):
                temp_settings[key] = widget.currentText()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                temp_settings[key] = str(widget.value())
            elif isinstance(widget, QLineEdit):
                temp_settings[key] = widget.text()
        
        # 유효성 검사 (네트워크 탭인 경우)
        if tab_name == "네트워크":
            if not self.validate_ip_address(temp_settings["IP Address"]):
                QMessageBox.warning(self, "오류", "유효하지 않은 IP 주소입니다.")
                return
        
        # 영문 탭 이름으로 변환
        english_tab_name = self.tab_name_mapping.get(tab_name, tab_name.lower())
        
        if hasattr(self.parent_window, 'write_log'):
            self.parent_window.write_log(f"[DEBUG] 탭 이름 변환: {tab_name} -> {english_tab_name}", "yellow")
        
        # 탭별 설정값 추출
        tab_settings = self.get_tab_settings(english_tab_name)
        
        if not tab_settings:
            error_msg = f"{tab_name} 탭의 설정을 찾을 수 없습니다. (영문명: {english_tab_name})"
            QMessageBox.warning(self, "오류", error_msg)
            if hasattr(self.parent_window, 'write_log'):
                self.parent_window.write_log(f"[ERROR] {error_msg}", "red")
                self.parent_window.write_log(f"[DEBUG] 사용 가능한 탭 키: {list(self.tab_keys.keys())}", "yellow")
            return
        
        if hasattr(self.parent_window, 'write_log'):
            self.parent_window.write_log(f"[DEBUG] 추출된 설정: {tab_settings}", "yellow")
        
        # 시그널 발생 - 영문 탭 이름으로 전송
        self.tab_applied.emit(english_tab_name, tab_settings)
        
        # 성공 메시지는 부모 윈도우에서 처리 후 표시하도록 변경
        # QMessageBox.information(self, "적용 완료", f"{tab_name} 설정이 장비에 적용되었습니다.")
    
    def save_as_default(self):
        """현재 설정을 사용자 기본값으로 저장"""
        # 현재 UI의 모든 값을 읽어옴
        current_settings = {}
        for key, widget in self.inputs.items():
            if isinstance(widget, QComboBox):
                current_settings[key] = widget.currentText()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                current_settings[key] = str(widget.value())
            elif isinstance(widget, QLineEdit):
                current_settings[key] = widget.text()

        # TuningSettingsManager를 통해 저장
        if hasattr(self.parent_window, 'tuning_manager'):
            success, msg = self.parent_window.tuning_manager.save_user_defaults(current_settings)
            if success:
                QMessageBox.information(self, "저장 완료", "현재 설정이 사용자 기본값으로 저장되었습니다.\n다음부터 '기본값 복원'시 이 값이 사용됩니다.")
            else:
                QMessageBox.warning(self, "저장 실패", msg)
        else:
            QMessageBox.warning(self, "오류", "TuningManager를 찾을 수 없습니다.")

    def reset_to_defaults(self):
        """기본값으로 복원 (사용자 기본값 우선, 없으면 시스템 기본값)"""
        defaults = None

        # 1단계: 사용자 기본값 로드 시도
        if hasattr(self.parent_window, 'tuning_manager'):
            success, user_defaults, msg = self.parent_window.tuning_manager.load_user_defaults()
            if success:
                defaults = user_defaults
                restore_type = "사용자 기본값"
            else:
                # 사용자 기본값 없음 -> 시스템 기본값 사용
                restore_type = "시스템 기본값"

        # 2단계: 기본값이 없으면 시스템 기본값 사용
        if defaults is None:
            defaults = self.get_system_defaults()
            restore_type = "시스템 기본값"

        # 3단계: UI에 기본값 적용
        self.apply_defaults_to_ui(defaults)

        QMessageBox.information(self, "복원 완료", f"모든 설정이 {restore_type}으로 복원되었습니다.")

    def reset_to_system_defaults(self):
        """시스템 기본값으로 강제 복원"""
        reply = QMessageBox.question(
            self, "확인",
            "사용자 기본값을 삭제하고 시스템 기본값으로 복원하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 사용자 기본값 삭제
            if hasattr(self.parent_window, 'tuning_manager'):
                self.parent_window.tuning_manager.delete_user_defaults()

            # 시스템 기본값으로 복원
            defaults = self.get_system_defaults()
            self.apply_defaults_to_ui(defaults)

            QMessageBox.information(self, "복원 완료", "모든 설정이 시스템 기본값으로 복원되었습니다.")

    def get_system_defaults(self):
        """시스템 기본값 반환"""
        return {
            "Control Mode": "User Port",
            "Regulation Mode": "Forward Power",
            "Ramp Mode": "Disable",
            "Ramp Up Time": "0",
            "Ramp Down Time": "0",
            "CEX Enable": "Disable",
            "CEX Mode": "Master",
            "CEX Output Phase": "0",
            "RF Output Phase": "0",

            # ===== Pulse 기본값 =====
            "Pulsing Type": "Amplitude",
            "Pulsing Mode": "Master",
            "Pulse On/Off": "Off",
            "Sync Output": "Off",
            "Pulse Frequency": "10000",
            "Pulse0 Level": "100.0",
            "Pulse1 Level": "75.0",
            "Pulse2 Level": "50.0",
            "Pulse3 Level": "0.0",
            "Pulse0 Duty": "20.0",
            "Pulse1 Duty": "20.0",
            "Pulse2 Duty": "20.0",
            "Pulse3 Duty": "20.0",
            "Input Sync Delay": "0",
            "Output Sync Delay": "0",
            "Width Control": "0",

            "Freq Tuning": "Disable",
            "Retuning Mode": "Disable",
            "Setting Mode": "Disable",
            "Min Frequency": "0",
            "Max Frequency": "0",
            "Start Frequency": "0",
            "Min Step": "0",
            "Max Step": "0",
            "Stop Gamma": "0",
            "Return Gamma": "0",
            "Set RF Frequency": "0",

            # Bank
            "Bank1 Enable": "Disable",
            "Bank1 Equation Enable": "Disable",
            "Bank1 X0": "1.0",
            "Bank1 A": "0.0",
            "Bank1 B": "0.0",
            "Bank1 C": "1.0",
            "Bank1 D": "0.0",
            "Bank2 Enable": "Disable",
            "Bank2 Equation Enable": "Disable",
            "Bank2 X0": "1.0",
            "Bank2 A": "0.0",
            "Bank2 B": "0.0",
            "Bank2 C": "1.0",
            "Bank2 D": "0.0",

            "IP Address": "127.0.0.1",
            "Subnet Mask": "255.255.255.0",
            "Gateway": "192.168.0.1",
            "DNS": "0.0.0.0"
        }

    def apply_defaults_to_ui(self, defaults):
        """기본값을 UI에 적용"""
        for key, default_value in defaults.items():
            if key in self.inputs:
                widget = self.inputs[key]
                try:
                    if isinstance(widget, QComboBox):
                        widget.setCurrentText(str(default_value))
                    elif isinstance(widget, QDoubleSpinBox):
                        widget.setValue(float(default_value))
                    elif isinstance(widget, QSpinBox):
                        widget.setValue(int(float(default_value)))
                    elif isinstance(widget, QLineEdit):
                        widget.setText(str(default_value))
                except Exception as e:
                    print(f"[WARNING] Failed to set {key} = {default_value}: {e}")
    
    def validate_settings(self):
        """설정값 유효성 검사"""
        # IP 주소 검증
        if not self.validate_ip_address(self.inputs["IP Address"].text()):
            QMessageBox.warning(self, "오류", "유효하지 않은 IP 주소입니다.")
            return False
        
        # 주파수 범위 검증
        min_freq = self.inputs["Min Frequency"].value()
        max_freq = self.inputs["Max Frequency"].value()
        if min_freq >= max_freq and max_freq > 0:
            QMessageBox.warning(self, "오류", "최소 주파수는 최대 주파수보다 작아야 합니다.")
            return False
        
        # 스텝 값 검증
        min_step = self.inputs["Min Step"].value()
        max_step = self.inputs["Max Step"].value()
        if min_step >= max_step and max_step > 0:
            QMessageBox.warning(self, "오류", "최소 스텝은 최대 스텝보다 작아야 합니다.")
            return False
        
        return True
    
    def apply_all_settings(self):
        """전체 설정 적용"""
        if not self.validate_settings():
            return
        
        # 모든 입력값을 tuning_settings에 저장
        for key, widget in self.inputs.items():
            if isinstance(widget, QComboBox):
                self.tuning_settings[key] = widget.currentText()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                self.tuning_settings[key] = str(widget.value())
            elif isinstance(widget, QLineEdit):
                self.tuning_settings[key] = widget.text()
        
        self.accept()
    
    def get_settings(self):
        """설정값 반환"""
        return self.tuning_settings
        
    def create_bank_tab(self, tab_widget):
        """Bank Function 설정 탭"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # Bank1 그룹
        bank1_group = QGroupBox("Bank1 설정")
        bank1_layout = QFormLayout(bank1_group)
        
        # Bank1 Enable
        bank1_enable = QComboBox()
        bank1_enable.addItems(["Disable", "Enable"])
        bank1_enable.setCurrentText(self.tuning_settings.get("Bank1 Enable", "Disable"))
        self.inputs["Bank1 Enable"] = bank1_enable
        bank1_layout.addRow(QLabel("Bank1 활성화:"), bank1_enable)
        
        # Bank1 Equation Enable
        bank1_eq = QComboBox()
        bank1_eq.addItems(["Disable", "Enable"])
        bank1_eq.setCurrentText(self.tuning_settings.get("Bank1 Equation Enable", "Disable"))
        self.inputs["Bank1 Equation Enable"] = bank1_eq
        bank1_layout.addRow(QLabel("Bank1 방정식:"), bank1_eq)
        
        # Bank1 Parameters (방정식: Y = A*X³ + B*X² + C*X + D)
        bank1_x0 = SmartDoubleSpinBox()
        bank1_x0.setRange(-1000.0, 1000.0)
        bank1_x0.setValue(float(self.tuning_settings.get("Bank1 X0", 1.0)))
        self.inputs["Bank1 X0"] = bank1_x0
        bank1_layout.addRow(QLabel("X(0) 초기값:"), bank1_x0)
        
        bank1_a = SmartDoubleSpinBox()
        bank1_a.setRange(-1000.0, 1000.0)
        bank1_a.setValue(float(self.tuning_settings.get("Bank1 A", 0.0)))
        self.inputs["Bank1 A"] = bank1_a
        bank1_layout.addRow(QLabel("A (X³ 계수):"), bank1_a)
        
        bank1_b = SmartDoubleSpinBox()
        bank1_b.setRange(-1000.0, 1000.0)
        bank1_b.setValue(float(self.tuning_settings.get("Bank1 B", 0.0)))
        self.inputs["Bank1 B"] = bank1_b
        bank1_layout.addRow(QLabel("B (X² 계수):"), bank1_b)
        
        bank1_c = SmartDoubleSpinBox()
        bank1_c.setRange(-1000.0, 1000.0)
        bank1_c.setValue(float(self.tuning_settings.get("Bank1 C", 1.0)))
        self.inputs["Bank1 C"] = bank1_c
        bank1_layout.addRow(QLabel("C (X 계수):"), bank1_c)
        
        bank1_d = SmartDoubleSpinBox()
        bank1_d.setRange(-1000.0, 1000.0)
        bank1_d.setValue(float(self.tuning_settings.get("Bank1 D", 0.0)))
        self.inputs["Bank1 D"] = bank1_d
        bank1_layout.addRow(QLabel("D (상수):"), bank1_d)
        
        layout.addWidget(bank1_group)
        
        # Bank2 그룹
        bank2_group = QGroupBox("Bank2 설정")
        bank2_layout = QFormLayout(bank2_group)
        
        # Bank2 Enable
        bank2_enable = QComboBox()
        bank2_enable.addItems(["Disable", "Enable"])
        bank2_enable.setCurrentText(self.tuning_settings.get("Bank2 Enable", "Disable"))
        self.inputs["Bank2 Enable"] = bank2_enable
        bank2_layout.addRow(QLabel("Bank2 활성화:"), bank2_enable)
        
        # Bank2 Equation Enable
        bank2_eq = QComboBox()
        bank2_eq.addItems(["Disable", "Enable"])
        bank2_eq.setCurrentText(self.tuning_settings.get("Bank2 Equation Enable", "Disable"))
        self.inputs["Bank2 Equation Enable"] = bank2_eq
        bank2_layout.addRow(QLabel("Bank2 방정식:"), bank2_eq)
        
        # Bank2 Parameters
        bank2_x0 = SmartDoubleSpinBox()
        bank2_x0.setRange(-1000.0, 1000.0)
        bank2_x0.setValue(float(self.tuning_settings.get("Bank2 X0", 1.0)))
        self.inputs["Bank2 X0"] = bank2_x0
        bank2_layout.addRow(QLabel("X(0) 초기값:"), bank2_x0)
        
        bank2_a = SmartDoubleSpinBox()
        bank2_a.setRange(-1000.0, 1000.0)
        bank2_a.setValue(float(self.tuning_settings.get("Bank2 A", 0.0)))
        self.inputs["Bank2 A"] = bank2_a
        bank2_layout.addRow(QLabel("A (X³ 계수):"), bank2_a)
        
        bank2_b = SmartDoubleSpinBox()
        bank2_b.setRange(-1000.0, 1000.0)
        bank2_b.setValue(float(self.tuning_settings.get("Bank2 B", 0.0)))
        self.inputs["Bank2 B"] = bank2_b
        bank2_layout.addRow(QLabel("B (X² 계수):"), bank2_b)
        
        bank2_c = SmartDoubleSpinBox()
        bank2_c.setRange(-1000.0, 1000.0)
        bank2_c.setValue(float(self.tuning_settings.get("Bank2 C", 1.0)))
        self.inputs["Bank2 C"] = bank2_c
        bank2_layout.addRow(QLabel("C (X 계수):"), bank2_c)
        
        bank2_d = SmartDoubleSpinBox()
        bank2_d.setRange(-1000.0, 1000.0)
        bank2_d.setValue(float(self.tuning_settings.get("Bank2 D", 0.0)))
        self.inputs["Bank2 D"] = bank2_d
        bank2_layout.addRow(QLabel("D (상수):"), bank2_d)
        
        layout.addWidget(bank2_group)

        # 로드 및 적용 버튼
        button_layout = QHBoxLayout()
        load_btn = self.create_tab_load_button("Bank")
        apply_btn = self.create_tab_apply_button("Bank")
        button_layout.addWidget(load_btn)
        button_layout.addWidget(apply_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        tab_widget.addTab(tab, "Bank")

    def load_tab_settings(self, tab_name_korean):
        """장비에서 현재 탭의 설정값 읽어오기"""
        # 한글 탭 이름을 영문 키로 변환
        tab_name = self.tab_name_mapping.get(tab_name_korean, tab_name_korean.lower())
        print(f"[DEBUG] Loading settings for tab: {tab_name_korean} -> {tab_name}")

        # parent_window 확인
        if not hasattr(self, 'parent_window') or not self.parent_window:
            QMessageBox.warning(self, "오류", "Parent window를 찾을 수 없습니다.")
            return

        # tuning_manager 확인
        if not hasattr(self.parent_window, 'tuning_manager'):
            QMessageBox.warning(self, "오류", "TuningManager를 찾을 수 없습니다.")
            return

        # network_manager 확인
        if not hasattr(self.parent_window, 'network_manager'):
            QMessageBox.warning(self, "오류", "NetworkManager를 찾을 수 없습니다.")
            return

        try:
            # GET 명령어 목록 가져오기
            success, commands, msg = self.parent_window.tuning_manager.get_tab_read_commands(tab_name)
            print(f"[DEBUG] GET commands generation: success={success}, count={len(commands) if commands else 0}, msg={msg}")

            if not success or not commands:
                QMessageBox.warning(self, "오류", f"{tab_name_korean} 탭 읽기 명령어 생성 실패:\n{msg}")
                return

            # 진행 상황 다이얼로그 표시 (모달로 생성하지 않고 정보만 표시)
            QApplication.processEvents()  # UI 업데이트

            # 응답 수집
            responses = []
            failed_commands = []

            # 각 명령어 순차 전송 (동기 모드)
            for i, cmd_info in enumerate(commands):
                try:
                    print(f"[DEBUG] Sending command {i+1}/{len(commands)}: {cmd_info['description']} (CMD=0x{cmd_info['cmd']:02X}, SUBCMD=0x{cmd_info['subcmd']:02X})")

                    result = self.parent_window.network_manager.send_command(
                        cmd_info['cmd'],
                        cmd_info['subcmd'],
                        cmd_info['data'],
                        wait_response=True,
                        timeout=3.0,
                        sync=True
                    )

                    print(f"[DEBUG] Command result: success={result.success}, has_response={result.response_data is not None}")

                    if result.success and result.response_data:
                        # 응답 파싱
                        from rf_protocol import RFProtocol
                        parsed = RFProtocol.parse_response(result.response_data)
                        print(f"[DEBUG] Parsed response: {parsed is not None}")

                        if parsed and 'data' in parsed:
                            responses.append({
                                'subcmd': parsed['subcmd'],
                                'data': parsed['data']
                            })
                            print(f"[DEBUG] Added response: subcmd=0x{parsed['subcmd']:02X}, data_len={len(parsed['data']) if parsed['data'] else 0}")
                        else:
                            print(f"[DEBUG] Parsed data missing or invalid")
                            failed_commands.append(f"{cmd_info['description']} (파싱 실패)")
                    else:
                        error_msg = f"{cmd_info['description']}"
                        if not result.success:
                            error_msg += f" (실패: {result.message})"
                        else:
                            error_msg += " (응답 없음)"
                        failed_commands.append(error_msg)
                        print(f"[DEBUG] Command failed: {error_msg}")

                    QApplication.processEvents()  # UI 응답성 유지

                except Exception as e:
                    error_msg = f"{cmd_info['description']}: {str(e)}"
                    failed_commands.append(error_msg)
                    print(f"[ERROR] Exception during command: {error_msg}")
                    import traceback
                    traceback.print_exc()
                    continue

            print(f"[DEBUG] Total responses collected: {len(responses)}/{len(commands)}")

            # 응답이 없는 경우
            if not responses:
                error_detail = "\n".join(failed_commands[:10]) if failed_commands else "알 수 없는 오류"
                QMessageBox.warning(
                    self, "오류",
                    f"장비로부터 응답을 받지 못했습니다.\n\n"
                    f"실패: {len(failed_commands)}/{len(commands)}\n\n"
                    f"실패 상세:\n{error_detail}"
                )
                return

            # 응답 파싱 및 설정 딕셔너리 생성
            success, settings, msg = self.parent_window.tuning_manager.parse_tab_responses(tab_name, responses)
            print(f"[DEBUG] Response parsing: success={success}, settings_count={len(settings) if settings else 0}")

            if not success or not settings:
                QMessageBox.warning(self, "오류", f"응답 파싱 실패:\n{msg}")
                return

            print(f"[DEBUG] Applying settings to UI: {list(settings.keys())}")

            # UI에 적용
            self.apply_defaults_to_ui(settings)

            # 결과 메시지
            success_count = len(responses)
            total_count = len(commands)
            if failed_commands:
                QMessageBox.information(
                    self, "로드 완료",
                    f"장비에서 {tab_name_korean} 설정을 불러왔습니다.\n\n"
                    f"성공: {success_count}/{total_count}\n"
                    f"실패: {len(failed_commands)}\n\n"
                    f"실패한 항목:\n" + "\n".join(failed_commands[:5])  # 최대 5개만 표시
                )
            else:
                QMessageBox.information(
                    self, "로드 완료",
                    f"장비에서 {tab_name_korean} 설정을 성공적으로 불러왔습니다.\n({success_count}/{total_count} 항목)"
                )

        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 로드 중 예외 발생:\n{str(e)}")
            import traceback
            traceback.print_exc()