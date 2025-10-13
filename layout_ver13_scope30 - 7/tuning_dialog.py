"""
Tuning Settings Dialog Module
RF 장비 튜닝 설정을 위한 다이얼로그 - 탭별 적용 기능 수정
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QFormLayout,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox,
    QScrollArea, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
import ipaddress


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
            "pulse": ["Pulse Mode", "Pulse On/Off", "Pulse Duty", "Output Sync", "Input Sync", "Pulse Frequency"],
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
        self.resize(800, 600)
        
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
        
        # 기본값 복원 버튼
        reset_btn = QPushButton("기본값 복원")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
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
        
        # 탭별 적용 버튼
        apply_btn = self.create_tab_apply_button("제어")
        layout.addWidget(apply_btn)
        
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
        ramp_up_time = QDoubleSpinBox()
        ramp_up_time.setRange(0.0, 999.9)
        ramp_up_time.setSuffix(" ms")
        ramp_up_time.setValue(float(self.tuning_settings["Ramp Up Time"]))
        self.inputs["Ramp Up Time"] = ramp_up_time
        
        ramp_up_label = QLabel("램프 업 시간:")
        ramp_up_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        ramp_layout.addRow(ramp_up_label, ramp_up_time)
        
        # Ramp Down Time
        ramp_down_time = QDoubleSpinBox()
        ramp_down_time.setRange(0.0, 999.9)
        ramp_down_time.setSuffix(" ms")
        ramp_down_time.setValue(float(self.tuning_settings["Ramp Down Time"]))
        self.inputs["Ramp Down Time"] = ramp_down_time
        
        ramp_down_label = QLabel("램프 다운 시간:")
        ramp_down_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        ramp_layout.addRow(ramp_down_label, ramp_down_time)
        
        layout.addWidget(ramp_group)
        
        # 탭별 적용 버튼
        apply_btn = self.create_tab_apply_button("램프")
        layout.addWidget(apply_btn)
        
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
        cex_output_phase = QDoubleSpinBox()
        cex_output_phase.setRange(0.0, 360.0)
        cex_output_phase.setSuffix("°")
        cex_output_phase.setValue(float(self.tuning_settings["CEX Output Phase"]))
        self.inputs["CEX Output Phase"] = cex_output_phase
        
        cex_output_label = QLabel("CEX 출력 위상:")
        cex_output_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        cex_layout.addRow(cex_output_label, cex_output_phase)
        
        # RF Output Phase
        rf_output_phase = QDoubleSpinBox()
        rf_output_phase.setRange(0.0, 360.0)
        rf_output_phase.setSuffix("°")
        rf_output_phase.setValue(float(self.tuning_settings["RF Output Phase"]))
        self.inputs["RF Output Phase"] = rf_output_phase
        
        rf_output_label = QLabel("RF 출력 위상:")
        rf_output_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        cex_layout.addRow(rf_output_label, rf_output_phase)
        
        layout.addWidget(cex_group)
        
        # 탭별 적용 버튼
        apply_btn = self.create_tab_apply_button("CEX")
        layout.addWidget(apply_btn)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        tab_widget.addTab(tab, "CEX")
    
    def create_pulse_tab(self, tab_widget):
        """펄스 설정 탭"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 펄스 설정 그룹
        pulse_group = QGroupBox("펄스 설정")
        pulse_layout = QFormLayout(pulse_group)
        
        # Pulse Mode
        pulse_mode = QComboBox()
        pulse_mode.addItems(["Master", "Slave", "External"])
        pulse_mode.setCurrentText(self.tuning_settings["Pulse Mode"])
        self.inputs["Pulse Mode"] = pulse_mode
        
        pulse_mode_label = QLabel("펄스 모드:")
        pulse_mode_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(pulse_mode_label, pulse_mode)
        
        # Pulse On/Off
        pulse_onoff = QComboBox()
        pulse_onoff.addItems(["Off (CW)", "On (Pulse)"])
        pulse_onoff.setCurrentText(self.tuning_settings["Pulse On/Off"])
        self.inputs["Pulse On/Off"] = pulse_onoff
        
        pulse_onoff_label = QLabel("펄스 On/Off:")
        pulse_onoff_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(pulse_onoff_label, pulse_onoff)
        
        # Pulse Duty
        pulse_duty = QDoubleSpinBox()
        pulse_duty.setRange(0.0, 100.0)
        pulse_duty.setSuffix(" %")
        pulse_duty.setValue(float(self.tuning_settings["Pulse Duty"]))
        self.inputs["Pulse Duty"] = pulse_duty
        
        pulse_duty_label = QLabel("펄스 듀티:")
        pulse_duty_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(pulse_duty_label, pulse_duty)
        
        # Output Sync
        output_sync = QSpinBox()
        output_sync.setRange(0, 999)
        output_sync.setValue(int(float(self.tuning_settings["Output Sync"])))
        self.inputs["Output Sync"] = output_sync
        
        output_sync_label = QLabel("출력 동기:")
        output_sync_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(output_sync_label, output_sync)
        
        # Input Sync
        input_sync = QSpinBox()
        input_sync.setRange(0, 999)
        input_sync.setValue(int(float(self.tuning_settings["Input Sync"])))
        self.inputs["Input Sync"] = input_sync
        
        input_sync_label = QLabel("입력 동기:")
        input_sync_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(input_sync_label, input_sync)
        
        # Pulse Frequency
        pulse_freq = QDoubleSpinBox()
        pulse_freq.setRange(0.0, 10000.0)
        pulse_freq.setSuffix(" Hz")
        pulse_freq.setValue(float(self.tuning_settings["Pulse Frequency"]))
        self.inputs["Pulse Frequency"] = pulse_freq
        
        pulse_freq_label = QLabel("펄스 주파수:")
        pulse_freq_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        pulse_layout.addRow(pulse_freq_label, pulse_freq)
        
        layout.addWidget(pulse_group)
        
        # 탭별 적용 버튼
        apply_btn = self.create_tab_apply_button("펄스")
        layout.addWidget(apply_btn)
        
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
        retuning_mode.addItems(["One-Time", "Continuous", "Auto"])
        retuning_mode.setCurrentText(self.tuning_settings["Retuning Mode"])
        self.inputs["Retuning Mode"] = retuning_mode
        
        retuning_mode_label = QLabel("재튜닝 모드:")
        retuning_mode_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        freq_layout.addRow(retuning_mode_label, retuning_mode)
        
        # Setting Mode
        setting_mode = QComboBox()
        setting_mode.addItems(["Fixed", "Variable", "Sweep"])
        setting_mode.setCurrentText(self.tuning_settings["Setting Mode"])
        self.inputs["Setting Mode"] = setting_mode
        
        setting_mode_label = QLabel("설정 모드:")
        setting_mode_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        freq_layout.addRow(setting_mode_label, setting_mode)
        
        layout.addWidget(freq_group)
        
        # 주파수 범위 그룹
        range_group = QGroupBox("주파수 범위")
        range_layout = QFormLayout(range_group)
        
        # Min Frequency
        min_freq = QDoubleSpinBox()
        min_freq.setRange(0.0, 50.0)
        min_freq.setSuffix(" MHz")
        min_freq.setValue(float(self.tuning_settings["Min Frequency"]))
        self.inputs["Min Frequency"] = min_freq
        
        min_freq_label = QLabel("최소 주파수:")
        min_freq_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        range_layout.addRow(min_freq_label, min_freq)
        
        # Max Frequency
        max_freq = QDoubleSpinBox()
        max_freq.setRange(0.0, 50.0)
        max_freq.setSuffix(" MHz")
        max_freq.setValue(float(self.tuning_settings["Max Frequency"]))
        self.inputs["Max Frequency"] = max_freq
        
        max_freq_label = QLabel("최대 주파수:")
        max_freq_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        range_layout.addRow(max_freq_label, max_freq)
        
        # Start Frequency
        start_freq = QDoubleSpinBox()
        start_freq.setRange(0.0, 50.0)
        start_freq.setSuffix(" MHz")
        start_freq.setValue(float(self.tuning_settings["Start Frequency"]))
        self.inputs["Start Frequency"] = start_freq
        
        start_freq_label = QLabel("시작 주파수:")
        start_freq_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        range_layout.addRow(start_freq_label, start_freq)
        
        # Set RF Frequency
        set_rf_freq = QDoubleSpinBox()
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
        min_step = QDoubleSpinBox()
        min_step.setRange(0.0, 10.0)
        min_step.setSuffix(" kHz")
        min_step.setValue(float(self.tuning_settings["Min Step"]))
        self.inputs["Min Step"] = min_step
        
        min_step_label = QLabel("최소 스텝:")
        min_step_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        step_layout.addRow(min_step_label, min_step)
        
        # Max Step
        max_step = QDoubleSpinBox()
        max_step.setRange(0.0, 100.0)
        max_step.setSuffix(" kHz")
        max_step.setValue(float(self.tuning_settings["Max Step"]))
        self.inputs["Max Step"] = max_step
        
        max_step_label = QLabel("최대 스텝:")
        max_step_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        step_layout.addRow(max_step_label, max_step)
        
        # Stop Gamma
        stop_gamma = QDoubleSpinBox()
        stop_gamma.setRange(0.0, 1.0)
        stop_gamma.setDecimals(3)
        stop_gamma.setValue(float(self.tuning_settings["Stop Gamma"]))
        self.inputs["Stop Gamma"] = stop_gamma
        
        stop_gamma_label = QLabel("정지 감마:")
        stop_gamma_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        step_layout.addRow(stop_gamma_label, stop_gamma)
        
        # Return Gamma
        return_gamma = QDoubleSpinBox()
        return_gamma.setRange(0.0, 1.0)
        return_gamma.setDecimals(3)
        return_gamma.setValue(float(self.tuning_settings["Return Gamma"]))
        self.inputs["Return Gamma"] = return_gamma
        
        return_gamma_label = QLabel("복귀 감마:")
        return_gamma_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        step_layout.addRow(return_gamma_label, return_gamma)
        
        layout.addWidget(step_group)
        
        # 탭별 적용 버튼
        apply_btn = self.create_tab_apply_button("주파수")
        layout.addWidget(apply_btn)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        tab_widget.addTab(tab, "주파수")
    
    def create_network_tab(self, tab_widget):
        """네트워크 설정 탭"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 네트워크 설정 그룹
        network_group = QGroupBox("네트워크 설정")
        network_layout = QFormLayout(network_group)
        
        # IP Address
        ip_address = QLineEdit(self.tuning_settings["IP Address"])
        ip_address.setPlaceholderText("예: 192.168.1.100")
        self.inputs["IP Address"] = ip_address
        
        ip_label = QLabel("IP 주소:")
        ip_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        network_layout.addRow(ip_label, ip_address)
        
        # Subnet Mask
        subnet_mask = QLineEdit(self.tuning_settings["Subnet Mask"])
        subnet_mask.setPlaceholderText("예: 255.255.255.0")
        self.inputs["Subnet Mask"] = subnet_mask
        
        subnet_label = QLabel("서브넷 마스크:")
        subnet_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        network_layout.addRow(subnet_label, subnet_mask)
        
        # Gateway
        gateway = QLineEdit(self.tuning_settings["Gateway"])
        gateway.setPlaceholderText("예: 192.168.1.1")
        self.inputs["Gateway"] = gateway
        
        gateway_label = QLabel("게이트웨이:")
        gateway_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        network_layout.addRow(gateway_label, gateway)
        
        # DNS
        dns = QLineEdit(self.tuning_settings["DNS"])
        dns.setPlaceholderText("예: 8.8.8.8")
        self.inputs["DNS"] = dns
        
        dns_label = QLabel("DNS:")
        dns_label.setStyleSheet("color: #4169e1; font-weight: bold;")
        network_layout.addRow(dns_label, dns)
        
        layout.addWidget(network_group)
        
        # 연결 테스트 버튼
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
    
    def reset_to_defaults(self):
        """기본값으로 복원"""
        defaults = {
            "Control Mode": "User Port",
            "Regulation Mode": "Forward Power", 
            "Ramp Mode": "Disable",
            "Ramp Up Time": "0",
            "Ramp Down Time": "0",
            "CEX Enable": "Disable",
            "CEX Mode": "Master",
            "CEX Output Phase": "0",
            "RF Output Phase": "0",
            "Pulse Mode": "Master",
            "Pulse On/Off": "Off (CW)",
            "Pulse Duty": "0",
            "Output Sync": "0",
            "Input Sync": "0",
            "Pulse Frequency": "0",
            "Freq Tuning": "Disable",
            "Retuning Mode": "One-Time",
            "Setting Mode": "Fixed",
            "Min Frequency": "0",
            "Max Frequency": "0",
            "Start Frequency": "0",
            "Min Step": "0",
            "Max Step": "0",
            "Stop Gamma": "0",
            "Return Gamma": "0",
            "Set RF Frequency": "0",
            "IP Address": "127.0.0.1",
            "Subnet Mask": "255.255.255.0",
            "Gateway": "192.168.0.1",
            "DNS": "0.0.0.0"
        }
        
        for key, default_value in defaults.items():
            if key in self.inputs:
                widget = self.inputs[key]
                if isinstance(widget, QComboBox):
                    widget.setCurrentText(default_value)
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    widget.setValue(float(default_value))
                elif isinstance(widget, QLineEdit):
                    widget.setText(default_value)
        
        QMessageBox.information(self, "복원 완료", "모든 설정이 기본값으로 복원되었습니다.")
    
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
        bank1_x0 = QDoubleSpinBox()
        bank1_x0.setRange(-1000.0, 1000.0)
        bank1_x0.setValue(float(self.tuning_settings.get("Bank1 X0", 1.0)))
        self.inputs["Bank1 X0"] = bank1_x0
        bank1_layout.addRow(QLabel("X(0) 초기값:"), bank1_x0)
        
        bank1_a = QDoubleSpinBox()
        bank1_a.setRange(-1000.0, 1000.0)
        bank1_a.setValue(float(self.tuning_settings.get("Bank1 A", 0.0)))
        self.inputs["Bank1 A"] = bank1_a
        bank1_layout.addRow(QLabel("A (X³ 계수):"), bank1_a)
        
        bank1_b = QDoubleSpinBox()
        bank1_b.setRange(-1000.0, 1000.0)
        bank1_b.setValue(float(self.tuning_settings.get("Bank1 B", 0.0)))
        self.inputs["Bank1 B"] = bank1_b
        bank1_layout.addRow(QLabel("B (X² 계수):"), bank1_b)
        
        bank1_c = QDoubleSpinBox()
        bank1_c.setRange(-1000.0, 1000.0)
        bank1_c.setValue(float(self.tuning_settings.get("Bank1 C", 1.0)))
        self.inputs["Bank1 C"] = bank1_c
        bank1_layout.addRow(QLabel("C (X 계수):"), bank1_c)
        
        bank1_d = QDoubleSpinBox()
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
        bank2_x0 = QDoubleSpinBox()
        bank2_x0.setRange(-1000.0, 1000.0)
        bank2_x0.setValue(float(self.tuning_settings.get("Bank2 X0", 1.0)))
        self.inputs["Bank2 X0"] = bank2_x0
        bank2_layout.addRow(QLabel("X(0) 초기값:"), bank2_x0)
        
        bank2_a = QDoubleSpinBox()
        bank2_a.setRange(-1000.0, 1000.0)
        bank2_a.setValue(float(self.tuning_settings.get("Bank2 A", 0.0)))
        self.inputs["Bank2 A"] = bank2_a
        bank2_layout.addRow(QLabel("A (X³ 계수):"), bank2_a)
        
        bank2_b = QDoubleSpinBox()
        bank2_b.setRange(-1000.0, 1000.0)
        bank2_b.setValue(float(self.tuning_settings.get("Bank2 B", 0.0)))
        self.inputs["Bank2 B"] = bank2_b
        bank2_layout.addRow(QLabel("B (X² 계수):"), bank2_b)
        
        bank2_c = QDoubleSpinBox()
        bank2_c.setRange(-1000.0, 1000.0)
        bank2_c.setValue(float(self.tuning_settings.get("Bank2 C", 1.0)))
        self.inputs["Bank2 C"] = bank2_c
        bank2_layout.addRow(QLabel("C (X 계수):"), bank2_c)
        
        bank2_d = QDoubleSpinBox()
        bank2_d.setRange(-1000.0, 1000.0)
        bank2_d.setValue(float(self.tuning_settings.get("Bank2 D", 0.0)))
        self.inputs["Bank2 D"] = bank2_d
        bank2_layout.addRow(QLabel("D (상수):"), bank2_d)
        
        layout.addWidget(bank2_group)
        
        # 탭별 적용 버튼
        apply_btn = self.create_tab_apply_button("Bank")
        layout.addWidget(apply_btn)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        tab_widget.addTab(tab, "Bank")