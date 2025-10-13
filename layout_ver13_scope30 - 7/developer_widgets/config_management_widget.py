"""
Config Management Widget
하단 고정 영역 - 설정 저장/로드
"""

from PyQt5.QtWidgets import (
    QGroupBox, QHBoxLayout, QPushButton, QLabel, QMessageBox
)
from PyQt5.QtCore import QDateTime
from rf_protocol import RFProtocol
from developer_data_manager import DeveloperDataManager


class ConfigManagementWidget(QGroupBox):
    """설정 관리 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("Configuration Management", parent)
        self.parent = parent
        self.network_manager = network_manager
        self.dev_data_manager = DeveloperDataManager()
        
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        
        layout.addWidget(QLabel("💾"))
        
        # Save Kgen Config
        save_kgen_button = QPushButton("Save Kgen Config")
        save_kgen_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        save_kgen_button.clicked.connect(lambda: self.save_config(0))
        layout.addWidget(save_kgen_button)
        
        # Save VIZ Config
        save_viz_button = QPushButton("Save VIZ Config")
        save_viz_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        save_viz_button.clicked.connect(lambda: self.save_config(1))
        layout.addWidget(save_viz_button)
        
        # Load Config
        load_button = QPushButton("Load Config")
        load_button.clicked.connect(self.load_config)
        layout.addWidget(load_button)
        
        layout.addStretch()
        
        # Last saved timestamp
        self.timestamp_label = QLabel("Last saved: ---")
        self.timestamp_label.setStyleSheet("color: gray;")
        layout.addWidget(self.timestamp_label)
    
    def save_config(self, config_type):
        """
        설정 저장
        Args:
            config_type: 0=Kgen Config, 1=VIZ Config
        """
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        config_name = "Kgen Config" if config_type == 0 else "VIZ Config"
        
        reply = QMessageBox.question(
            self,
            "확인",
            f"{config_name}를 장치에 저장하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 데이터 생성
        success, data, message = self.dev_data_manager.create_save_config_data(config_type)
        
        if not success:
            QMessageBox.critical(self, "오류", message)
            return
        
        # 명령 전송
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_SYSTEM_CONTROL,
            RFProtocol.SUBCMD_SAVE_CONFIG,  # ← 추가
            data=data,
            wait_response=True,
            sync=True
        )
        
        if result.success:
            current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
            self.timestamp_label.setText(f"Last saved: {current_time}")
            QMessageBox.information(self, "완료", f"{config_name}가 저장되었습니다.")
        else:
            QMessageBox.warning(self, "오류", f"설정 저장 실패: {result.message}")
    
    def load_config(self):
        """설정 로드 (모든 위젯에서 로드)"""
        reply = QMessageBox.question(
            self,
            "확인",
            "장치에서 모든 설정을 다시 로드하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Device Info 로드
        if hasattr(self.parent, 'device_info_widget'):
            self.parent.device_info_widget.load_device_info()
        
        # Arc Management 로드
        if hasattr(self.parent, 'arc_widget'):
            self.parent.arc_widget.load_settings()
        
        # TODO: 다른 위젯들도 로드
        
        QMessageBox.information(self, "완료", "모든 설정을 로드했습니다.")