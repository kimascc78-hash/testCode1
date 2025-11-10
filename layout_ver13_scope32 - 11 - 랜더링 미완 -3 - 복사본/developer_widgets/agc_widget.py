"""
AGC Setup Widget
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QRadioButton, QSpinBox, QDoubleSpinBox, QButtonGroup, QMessageBox, QGridLayout  # ← 추가
)
from rf_protocol import RFProtocol
from developer_data_manager import DeveloperDataManager
from ui_widgets import SmartSpinBox, SmartDoubleSpinBox

class AGCWidget(QGroupBox):
    """AGC Setup 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("AGC Setup", parent)
        self.parent = parent
        self.network_manager = network_manager
        self.dev_data_manager = DeveloperDataManager()
        
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self.on_toggle)
        
        self.init_ui()
        self.on_toggle(False)  # 초기 상태 적용
        
    def init_ui(self):
        """UI 초기화"""
        self.main_layout = QVBoxLayout(self)
        
        # AGC On/Off
        agc_onoff_layout = QHBoxLayout()
        agc_onoff_layout.addWidget(QLabel("AGC On/Off:"))
        
        self.agc_group = QButtonGroup()
        self.agc_on = QRadioButton("On")
        self.agc_off = QRadioButton("Off")
        self.agc_off.setChecked(True)
        
        self.agc_group.addButton(self.agc_on)
        self.agc_group.addButton(self.agc_off)
        
        agc_onoff_layout.addWidget(self.agc_on)
        agc_onoff_layout.addWidget(self.agc_off)
        agc_onoff_layout.addStretch()
        self.main_layout.addLayout(agc_onoff_layout)
        
        # Ref Setup Time
        ref_time_layout = QHBoxLayout()
        ref_time_layout.addWidget(QLabel("Ref Setup Time:"))
        
        self.ref_setup_time_spin = SmartSpinBox()
        self.ref_setup_time_spin.setRange(0, 65535)
        self.ref_setup_time_spin.setValue(100)
        self.ref_setup_time_spin.setSuffix(" ms")
        
        ref_time_layout.addWidget(self.ref_setup_time_spin)
        ref_time_layout.addStretch()
        self.main_layout.addLayout(ref_time_layout)
        
        # AGC Setup Time[4] 그룹 내부
        agc_time_group = QGroupBox("AGC Setup Time")
        agc_time_layout = QGridLayout(agc_time_group)  # ← VBoxLayout → QGridLayout

        self.agc_setup_time_spins = []
        for i in range(4):
            agc_time_layout.addWidget(QLabel(f"Time {i}:"), i, 0)
            
            spin = SmartSpinBox()
            spin.setRange(0, 65535)
            spin.setValue(0)
            spin.setSuffix(" ms")
            self.agc_setup_time_spins.append(spin)
            
            agc_time_layout.addWidget(spin, i, 1)

        agc_time_layout.setColumnStretch(2, 1)
        self.main_layout.addWidget(agc_time_group)

        # Sensor Gain Rates 그룹 내부도 동일하게
        gain_rate_group = QGroupBox("Sensor Gain Rates")
        gain_rate_layout = QGridLayout(gain_rate_group)  # ← VBoxLayout → QGridLayout

        gain_rate_labels = [
            "Reflect Value Rate:",
            "Start Power Gain Rate:",
            "Running AGC Gain Rate:",
            "Reserved:"
        ]

        self.sensor_gain_rate_spins = []
        for i, label in enumerate(gain_rate_labels):
            gain_rate_layout.addWidget(QLabel(label), i, 0)
            
            spin = SmartDoubleSpinBox()
            spin.setRange(0.0, 100.0)
            spin.setValue(0.0)
            spin.setDecimals(3)
            self.sensor_gain_rate_spins.append(spin)
            
            gain_rate_layout.addWidget(spin, i, 1)

        gain_rate_layout.setColumnStretch(2, 1)
        self.main_layout.addWidget(gain_rate_group)
        
        # Init Power Gain
        init_gain_layout = QHBoxLayout()
        init_gain_layout.addWidget(QLabel("Init Power Gain:"))
        
        self.init_power_gain_spin = SmartDoubleSpinBox()
        self.init_power_gain_spin.setRange(0.0, 10.0)
        self.init_power_gain_spin.setValue(1.0)
        self.init_power_gain_spin.setDecimals(3)
        
        init_gain_layout.addWidget(self.init_power_gain_spin)
        init_gain_layout.addStretch()
        self.main_layout.addLayout(init_gain_layout)
        
        # 버튼
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
            item = self.main_layout.itemAt(i)
            if item.widget():
                item.widget().setVisible(checked)
            elif item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if widget:
                        widget.setVisible(checked)
    
    def load_settings(self):
        """설정 로드"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_AGC_SETUP_GET,
            RFProtocol.SUBCMD_AGC_SETUP,
            wait_response=True,
            sync=True
        )
        
        if result.success and result.response_data:
            # ✅ parse_response() 사용
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and parsed['data']:
                settings = self.dev_data_manager.parse_agc_setup_data(parsed['data'])
                
                if settings:
                    # AGC On/Off
                    if settings['agc_onoff']:
                        self.agc_on.setChecked(True)
                    else:
                        self.agc_off.setChecked(True)
                    
                    # Ref Setup Time
                    self.ref_setup_time_spin.setValue(settings['ref_setup_time'])
                    
                    # AGC Setup Time[4]
                    for i in range(4):
                        self.agc_setup_time_spins[i].setValue(settings[f'agc_setup_time_{i}'])
                    
                    # Sensor Gain Rates[4]
                    for i in range(4):
                        self.sensor_gain_rate_spins[i].setValue(settings[f'sensor_gain_rate_{i}'])
                    
                    # Init Power Gain
                    self.init_power_gain_spin.setValue(settings['init_power_gain'])
                    
                    QMessageBox.information(self, "완료", "AGC Setup을 로드했습니다.")
                else:
                    QMessageBox.warning(self, "오류", "AGC 데이터 파싱 실패")
            else:
                QMessageBox.warning(self, "오류", "응답 데이터가 없습니다.")
        else:
            QMessageBox.warning(self, "오류", "설정 로드 실패")
    
    def apply_settings(self):
        """설정 적용"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        settings = {
            'agc_onoff': self.agc_on.isChecked(),
            'ref_setup_time': self.ref_setup_time_spin.value(),
            'init_power_gain': self.init_power_gain_spin.value()
        }
        
        for i in range(4):
            settings[f'agc_setup_time_{i}'] = self.agc_setup_time_spins[i].value()
            settings[f'sensor_gain_rate_{i}'] = self.sensor_gain_rate_spins[i].value()
        
        success, data, message = self.dev_data_manager.create_agc_setup_data(settings)
        
        if not success:
            QMessageBox.critical(self, "오류", message)
            return
        
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_AGC_SETUP_SET,
            RFProtocol.SUBCMD_AGC_SETUP,
            data=data,
            wait_response=True,
            sync=True
        )
        
        if result.success:
            QMessageBox.information(self, "완료", "AGC Setup이 적용되었습니다.")
        else:
            QMessageBox.warning(self, "오류", f"설정 적용 실패: {result.message}")