"""
DDS Control Widget
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSpinBox, QDoubleSpinBox, QMessageBox
)
from rf_protocol import RFProtocol
from developer_data_manager import DeveloperDataManager


class DDSWidget(QGroupBox):
    """DDS Control 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("DDS Control", parent)
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
        
        # Ch0 Amp Gain
        ch0_gain_layout = QHBoxLayout()
        ch0_gain_layout.addWidget(QLabel("Ch0 Amp Gain:"))
        
        self.ch0_gain_spin = QSpinBox()
        self.ch0_gain_spin.setRange(0, 4095)
        self.ch0_gain_spin.setValue(1024)
        
        ch0_gain_layout.addWidget(self.ch0_gain_spin)
        ch0_gain_layout.addStretch()
        self.main_layout.addLayout(ch0_gain_layout)
        
        # Ch1 Amp Gain
        ch1_gain_layout = QHBoxLayout()
        ch1_gain_layout.addWidget(QLabel("Ch1 Amp Gain:"))
        
        self.ch1_gain_spin = QSpinBox()
        self.ch1_gain_spin.setRange(0, 4095)
        self.ch1_gain_spin.setValue(1024)
        
        ch1_gain_layout.addWidget(self.ch1_gain_spin)
        ch1_gain_layout.addStretch()
        self.main_layout.addLayout(ch1_gain_layout)
        
        # Ch0 Phase Offset (CEX)
        ch0_phase_layout = QHBoxLayout()
        ch0_phase_layout.addWidget(QLabel("Ch0 Phase Offset (CEX):"))
        
        self.ch0_phase_spin = QDoubleSpinBox()
        self.ch0_phase_spin.setRange(-180.0, 180.0)
        self.ch0_phase_spin.setValue(0.0)
        self.ch0_phase_spin.setSuffix("°")
        self.ch0_phase_spin.setDecimals(2)
        
        ch0_phase_layout.addWidget(self.ch0_phase_spin)
        ch0_phase_layout.addStretch()
        self.main_layout.addLayout(ch0_phase_layout)
        
        # Ch1 Phase Offset (RF)
        ch1_phase_layout = QHBoxLayout()
        ch1_phase_layout.addWidget(QLabel("Ch1 Phase Offset (RF):"))
        
        self.ch1_phase_spin = QDoubleSpinBox()
        self.ch1_phase_spin.setRange(-180.0, 180.0)
        self.ch1_phase_spin.setValue(0.0)
        self.ch1_phase_spin.setSuffix("°")
        self.ch1_phase_spin.setDecimals(2)
        
        ch1_phase_layout.addWidget(self.ch1_phase_spin)
        ch1_phase_layout.addStretch()
        self.main_layout.addLayout(ch1_phase_layout)
        
        # Set Auto RF Offset
        auto_offset_layout = QHBoxLayout()
        auto_offset_layout.addWidget(QLabel("Set Auto RF Offset:"))
        
        self.auto_offset_spin = QSpinBox()
        self.auto_offset_spin.setRange(0, 65535)
        self.auto_offset_spin.setValue(0)
        
        auto_offset_layout.addWidget(self.auto_offset_spin)
        auto_offset_layout.addStretch()
        self.main_layout.addLayout(auto_offset_layout)
        
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
            RFProtocol.CMD_DDS_CTL_GET,
            RFProtocol.SUBCMD_DDS_CTL,
            wait_response=True,
            sync=True
        )
        
        if result.success and result.response_data:
            # parse_response() 사용
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and parsed['data']:
                settings = self.dev_data_manager.parse_dds_control_data(parsed['data'])
                
                if settings:
                    # UI 업데이트
                    self.ch0_gain_spin.setValue(settings['dds_ch0_amp_gain'])
                    self.ch1_gain_spin.setValue(settings['dds_ch1_amp_gain'])
                    self.ch0_phase_spin.setValue(settings['dds_ch0_phase_offset'])
                    self.ch1_phase_spin.setValue(settings['dds_ch1_phase_offset'])
                    self.auto_offset_spin.setValue(settings['set_auto_rf_offset'])
                    
                    QMessageBox.information(self, "완료", "DDS Control을 로드했습니다.")
                else:
                    QMessageBox.warning(self, "오류", "DDS 데이터 파싱 실패")
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
            'dds_ch0_amp_gain': self.ch0_gain_spin.value(),
            'dds_ch1_amp_gain': self.ch1_gain_spin.value(),
            'dds_ch0_phase_offset': self.ch0_phase_spin.value(),
            'dds_ch1_phase_offset': self.ch1_phase_spin.value(),
            'dds_rf_freqoffset': 0,
            'set_auto_rf_offset': self.auto_offset_spin.value()
        }
        
        success, data, message = self.dev_data_manager.create_dds_control_data(settings)
        
        if not success:
            QMessageBox.critical(self, "오류", message)
            return
        
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_DDS_CTL_SET,
            RFProtocol.SUBCMD_DDS_CTL,
            data=data,
            wait_response=True,
            sync=True
        )
        
        if result.success:
            QMessageBox.information(self, "완료", "DDS Control이 적용되었습니다.")
        else:
            QMessageBox.warning(self, "오류", f"설정 적용 실패: {result.message}")