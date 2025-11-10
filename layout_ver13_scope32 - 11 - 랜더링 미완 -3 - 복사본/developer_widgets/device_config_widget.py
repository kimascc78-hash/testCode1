"""
Device & Config Widget
디바이스 정보 + 설정 관리 통합
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
)
from PyQt5.QtCore import QDateTime
from rf_protocol import RFProtocol
from developer_data_manager import DeveloperDataManager


class DeviceConfigWidget(QWidget):
    """디바이스 정보 + 설정 관리 통합 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__(parent)
        self.parent = parent
        self.network_manager = network_manager
        self.dev_data_manager = DeveloperDataManager()
        
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ========================================
        # Device Information
        # ========================================
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
        
        # Network Info
        network_layout = QHBoxLayout()
        
        self.ip_label = QLabel("IP: ---")
        self.mac_label = QLabel("MAC: ---")
        
        network_layout.addWidget(self.ip_label)
        network_layout.addWidget(self.create_separator())
        network_layout.addWidget(self.mac_label)
        network_layout.addStretch()
        
        layout.addLayout(network_layout)
        
        # 구분선
        layout.addWidget(self.create_h_line())
        
        # ========================================
        # Configuration Management
        # ========================================
        config_label = QLabel("Configuration Management")
        config_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #87ceeb;")
        layout.addWidget(config_label)
        
        config_layout = QHBoxLayout()
        
        # Save Kgen Config
        save_kgen_btn = QPushButton("Save Kgen Config")
        save_kgen_btn.setFixedWidth(150)
        save_kgen_btn.setStyleSheet("background-color: #4CAF50;")
        save_kgen_btn.clicked.connect(lambda: self.save_config(0))
        config_layout.addWidget(save_kgen_btn)
        
        # Save VIZ Config
        save_viz_btn = QPushButton("Save VIZ Config")
        save_viz_btn.setFixedWidth(150)
        save_viz_btn.setStyleSheet("background-color: #4CAF50;")
        save_viz_btn.clicked.connect(lambda: self.save_config(1))
        config_layout.addWidget(save_viz_btn)
        
        # Load Config
        load_btn = QPushButton("Load All Device Data")
        load_btn.setFixedWidth(170)
        load_btn.clicked.connect(self.load_config)
        config_layout.addWidget(load_btn)
        
        config_layout.addStretch()
        
        # Timestamp
        self.timestamp_label = QLabel("Last saved: ---")
        self.timestamp_label.setStyleSheet("color: #888888;")
        config_layout.addWidget(self.timestamp_label)
        
        layout.addLayout(config_layout)
        
        # 구분선
        layout.addWidget(self.create_h_line())
        
        # ========================================
        # Diagnostics Tools
        # ========================================
        diag_label = QLabel("Diagnostics")
        diag_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #87ceeb;")
        layout.addWidget(diag_label)
        
        diag_layout = QHBoxLayout()
        
        status_monitor_btn = QPushButton("Status Monitor")
        status_monitor_btn.setFixedWidth(140)
        status_monitor_btn.clicked.connect(self.open_status_monitor)
        
        adc_dac_btn = QPushButton("ADC/DAC Viewer")
        adc_dac_btn.setFixedWidth(140)
        adc_dac_btn.clicked.connect(self.open_adc_dac_viewer)
        
        diag_layout.addWidget(status_monitor_btn)
        diag_layout.addWidget(adc_dac_btn)
        diag_layout.addStretch()
        
        layout.addLayout(diag_layout)
        
        layout.addStretch()  # 하단 여백
    
    def create_separator(self):
        """구분자"""
        sep = QLabel("|")
        sep.setStyleSheet("color: #555555;")
        return sep
    
    def create_h_line(self):
        """수평선"""
        from PyQt5.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #444444;")
        return line
    
    # ========================================
    # Device Info 메서드
    # ========================================
    
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
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and parsed['data']:
                device_info = self.dev_data_manager.parse_device_manager_data(parsed['data'])
                if device_info:
                    # 수신한 값만 색상 변경 (예: 밝은 파란색)
                    model = device_info.get('model_name', '---')
                    sn = device_info.get('serial_no', '---')
                    fw = device_info.get('fw_version', '---')
                    
                    self.model_label.setText(f'Model: <span style="color: #00BFFF;">{model}</span>')
                    self.sn_label.setText(f'S/N: <span style="color: #00BFFF;">{sn}</span>')
                    self.fw_label.setText(f'FW: <span style="color: #00BFFF;">{fw}</span>')
        
        self.load_network_info()

    def load_network_info(self):
        """Network 정보 로드"""
        if not self.network_manager.client_thread:
            return
        
        try:
            if hasattr(self.network_manager.client_thread, 'host'):
                ip = self.network_manager.client_thread.host
            else:
                ip = "---"
            # IP 값도 색상 변경
            self.ip_label.setText(f'IP: <span style="color: #00BFFF;">{ip}</span>')
        except:
            self.ip_label.setText("IP: Not Connected")
        
        self.mac_label.setText("MAC: ---")
    
    # ========================================
    # Config 메서드
    # ========================================
    
    def save_config(self, config_type):
        """설정 저장 (0=Kgen, 1=VIZ)"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        config_name = "Kgen Config" if config_type == 0 else "VIZ Config"
        
        reply = QMessageBox.question(
            self, "확인",
            f"{config_name}를 장치에 저장하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        success, data, message = self.dev_data_manager.create_save_config_data(config_type)
        
        if not success:
            QMessageBox.critical(self, "오류", message)
            return
        
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_SYSTEM_CONTROL,
            RFProtocol.SUBCMD_SAVE_CONFIG,  # ← 이 줄 추가!
            data=data,
            wait_response=True,
            sync=True
        )
        
        if result.success:
            current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
            self.timestamp_label.setText(f"Last saved: {current_time}")
            QMessageBox.information(self, "완료", f"{config_name}가 저장되었습니다.")
        else:
            QMessageBox.warning(self, "오류", f"저장 실패: {result.message}")
    
    def load_config(self):
        """모든 설정 재로드"""
        reply = QMessageBox.question(
            self, "확인",
            "장치에서 모든 설정을 다시 로드하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Device Info 로드
        self.load_device_info()
        
        # Arc Management 로드
        if hasattr(self.parent, 'arc_widget'):
            self.parent.arc_widget.load_settings()
        
        # ========================================
        # Advanced Settings 위젯들 로드 추가
        # ========================================
        if hasattr(self.parent, 'advanced_widget'):
            # SDD Config
            if hasattr(self.parent.advanced_widget, 'sdd_widget'):
                self.parent.advanced_widget.sdd_widget.load_settings()
            
            # DDS Control
            if hasattr(self.parent.advanced_widget, 'dds_widget'):
                self.parent.advanced_widget.dds_widget.load_settings()
            
            # AGC Setup
            if hasattr(self.parent.advanced_widget, 'agc_widget'):
                self.parent.advanced_widget.agc_widget.load_settings()
            
            # Fast Data Acquisition
            if hasattr(self.parent.advanced_widget, 'fast_acq_widget'):
                self.parent.advanced_widget.fast_acq_widget.load_settings()
            
            # Gate Bias Config
            if hasattr(self.parent.advanced_widget, 'gate_bias_widget'):
                self.parent.advanced_widget.gate_bias_widget.load_settings()
        
        # Calibration 로드
        if hasattr(self.parent, 'calibration_widget'):
            self.parent.calibration_widget.load_control()
        
        QMessageBox.information(self, "완료", "모든 설정을 로드했습니다.")
    
    # ========================================
    # Diagnostics 메서드
    # ========================================
    
    def open_status_monitor(self):
        """Status Monitor 열기"""
        if hasattr(self.parent.parent, 'show_status_monitor'):
            self.parent.parent.show_status_monitor()
    
    def open_adc_dac_viewer(self):
        """ADC/DAC Viewer 열기"""
        QMessageBox.information(self, "준비 중", "ADC/DAC Viewer는 Phase 2에서 구현됩니다.")