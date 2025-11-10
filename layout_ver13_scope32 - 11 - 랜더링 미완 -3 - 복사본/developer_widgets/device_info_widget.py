"""
Device Info Widget
상단 고정 영역 - 디바이스 정보 표시 (간소화)
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt5.QtCore import Qt
from rf_protocol import RFProtocol
from developer_data_manager import DeveloperDataManager


class DeviceInfoWidget(QGroupBox):
    """Device 정보 표시 (간소화)"""
    
    def __init__(self, parent, network_manager):
        super().__init__("Device Information", parent)
        self.parent = parent
        self.network_manager = network_manager
        self.dev_data_manager = DeveloperDataManager()
        
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화 - 간소화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Device Info (1줄)
        device_layout = QHBoxLayout()
        
        self.model_label = QLabel("Model: ---")
        self.sn_label = QLabel("S/N: ---")
        self.fw_label = QLabel("FW: ---")
        
        device_layout.addWidget(self.model_label)
        device_layout.addWidget(self.create_separator())
        device_layout.addWidget(self.sn_label)
        device_layout.addWidget(self.create_separator())
        device_layout.addWidget(self.fw_label)
        device_layout.addStretch()
        
        layout.addLayout(device_layout)
        
        # Network Info (1줄)
        network_layout = QHBoxLayout()
        
        self.ip_label = QLabel("IP: ---")
        self.mac_label = QLabel("MAC: ---")
        
        network_layout.addWidget(self.ip_label)
        network_layout.addWidget(self.create_separator())
        network_layout.addWidget(self.mac_label)
        network_layout.addStretch()
        
        layout.addLayout(network_layout)
        
        # Diagnostics 버튼들 (1줄)
        button_layout = QHBoxLayout()
        
        status_monitor_btn = QPushButton("Status Monitor")
        status_monitor_btn.setFixedWidth(140)
        status_monitor_btn.clicked.connect(self.open_status_monitor)
        
        adc_dac_btn = QPushButton("ADC/DAC Viewer")
        adc_dac_btn.setFixedWidth(140)
        adc_dac_btn.clicked.connect(self.open_adc_dac_viewer)
        
        button_layout.addWidget(status_monitor_btn)
        button_layout.addWidget(adc_dac_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def create_separator(self):
        """구분자 레이블 생성"""
        sep = QLabel("|")
        sep.setStyleSheet("color: #555555;")
        return sep
    
    def load_device_info(self):
        """Device Manager 정보 로드"""
        if not self.network_manager.client_thread:
            return
        
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_DEVICE_MANAGER_GET,
            RFProtocol.SUBCMD_DEVICE_MANAGER,
            wait_response=True,
            sync=True
        )
        
        if result.success and result.response_data:
            device_info = self.dev_data_manager.parse_device_manager_data(result.response_data)
            if device_info:
                self.model_label.setText(f"Model: {device_info.get('model_name', '---')}")
                self.sn_label.setText(f"S/N: {device_info.get('serial_no', '---')}")
                self.fw_label.setText(f"FW: {device_info.get('fw_version', '---')}")
        
        self.load_network_info()
    
    def load_network_info(self):
        """Network 정보 로드"""
        if not self.network_manager.client_thread:
            return
        
        try:
            if hasattr(self.network_manager.client_thread, 'host'):
                ip = self.network_manager.client_thread.host
            elif hasattr(self.network_manager.client_thread, 'server_ip'):
                ip = self.network_manager.client_thread.server_ip
            else:
                ip = "---"
            self.ip_label.setText(f"IP: {ip}")
        except:
            self.ip_label.setText("IP: Not Connected")
        
        self.mac_label.setText("MAC: ---")
    
    def open_status_monitor(self):
        """Status Monitor Dialog 열기"""
        if hasattr(self.parent.parent, 'show_status_monitor'):
            self.parent.parent.show_status_monitor()
    
    def open_adc_dac_viewer(self):
        """ADC/DAC Viewer 열기"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "준비 중", "ADC/DAC Viewer는 Phase 2에서 구현됩니다.")