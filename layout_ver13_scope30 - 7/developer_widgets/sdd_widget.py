"""
SDD Config Widget
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QMessageBox
)
from rf_protocol import RFProtocol
import struct


class SDDWidget(QGroupBox):
    """SDD Config 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("SDD Config", parent)
        self.parent = parent
        self.network_manager = network_manager
        
        self.setCheckable(True)
        self.setChecked(False)  # 기본 접힘
        self.toggled.connect(self.on_toggle)
        
        self.init_ui()
        self.on_toggle(False)  # 초기 상태 적용
        
    def init_ui(self):
        """UI 초기화"""
        self.main_layout = QVBoxLayout(self)
        
        # GUI Model
        gui_layout = QHBoxLayout()
        gui_layout.addWidget(QLabel("GUI Model:"))
        
        self.gui_model_spin = QSpinBox()
        self.gui_model_spin.setRange(0, 65535)
        self.gui_model_spin.setValue(1)
        
        gui_layout.addWidget(self.gui_model_spin)
        gui_layout.addStretch()
        self.main_layout.addLayout(gui_layout)
        
        # Pulsing Freq/Duty Count
        pulsing_layout = QHBoxLayout()
        pulsing_layout.addWidget(QLabel("Pulsing Freq/Duty Count:"))
        
        self.pulsing_count_spin = QSpinBox()
        self.pulsing_count_spin.setRange(0, 65535)
        self.pulsing_count_spin.setValue(100)
        
        pulsing_layout.addWidget(self.pulsing_count_spin)
        pulsing_layout.addStretch()
        self.main_layout.addLayout(pulsing_layout)
        
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
            RFProtocol.CMD_SDD_CONFIG_GET,
            RFProtocol.SUBCMD_SDD_CONFIG,
            wait_response=True,
            sync=True
        )
        
        if result.success and result.response_data:
            # ✅ 수정: parse_response() 사용
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and len(parsed['data']) >= 4:
                gui_model = struct.unpack('<H', parsed['data'][0:2])[0]
                pulsing_count = struct.unpack('<H', parsed['data'][2:4])[0]
                
                self.gui_model_spin.setValue(gui_model)
                self.pulsing_count_spin.setValue(pulsing_count)
                
                QMessageBox.information(self, "완료", "SDD Config를 로드했습니다.")
            else:
                QMessageBox.warning(self, "오류", "응답 데이터 형식 오류")
        else:
            QMessageBox.warning(self, "오류", "설정 로드 실패")
    
    def apply_settings(self):
        """설정 적용"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        # 데이터 생성
        data = bytearray()
        data.extend(struct.pack('<H', self.gui_model_spin.value()))
        data.extend(struct.pack('<H', self.pulsing_count_spin.value()))
        
        # 명령 전송
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_SDD_CONFIG_SET,
            RFProtocol.SUBCMD_SDD_CONFIG,
            data=bytes(data),
            wait_response=True,
            sync=True
        )
        
        if result.success:
            QMessageBox.information(self, "완료", "SDD Config가 적용되었습니다.")
        else:
            QMessageBox.warning(self, "오류", f"설정 적용 실패: {result.message}")