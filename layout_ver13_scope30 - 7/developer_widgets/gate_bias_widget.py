"""
Gate Bias Config Widget
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDoubleSpinBox, QMessageBox
)
from rf_protocol import RFProtocol
import struct


class GateBiasWidget(QGroupBox):
    """Gate Bias Config 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("Gate Bias Config", parent)
        self.parent = parent
        self.network_manager = network_manager
        
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self.on_toggle)
        
        self.init_ui()
        self.on_toggle(False)
        
    def init_ui(self):
        """UI 초기화"""
        self.main_layout = QVBoxLayout(self)
        
        # Module 1 (4 values)
        module1_group = QGroupBox("Module 1")
        module1_layout = QHBoxLayout(module1_group)
        
        self.module1_spins = []
        for i in range(4):
            module1_layout.addWidget(QLabel(f"B{i}:"))
            spin = QDoubleSpinBox()
            spin.setRange(-100.0, 100.0)
            spin.setValue(0.0)
            spin.setDecimals(3)
            self.module1_spins.append(spin)
            module1_layout.addWidget(spin)
        
        self.main_layout.addWidget(module1_group)
        
        # Module 2 (4 values)
        module2_group = QGroupBox("Module 2")
        module2_layout = QHBoxLayout(module2_group)
        
        self.module2_spins = []
        for i in range(4):
            module2_layout.addWidget(QLabel(f"B{i}:"))
            spin = QDoubleSpinBox()
            spin.setRange(-100.0, 100.0)
            spin.setValue(0.0)
            spin.setDecimals(3)
            self.module2_spins.append(spin)
            module2_layout.addWidget(spin)
        
        self.main_layout.addWidget(module2_group)
        
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
        
        # CMD_SYSTEM_CONTROL + SUBCMD_GET_GATE_BIAS
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_SYSTEM_CONTROL,
            RFProtocol.SUBCMD_GET_GATE_BIAS,
            wait_response=True,
            sync=True
        )
        
        if result.success and result.response_data:
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and len(parsed['data']) >= 32:  # 8개 float = 32바이트
                # 8개 float 파싱
                values = []
                for i in range(8):
                    offset = i * 4
                    value = struct.unpack('<f', parsed['data'][offset:offset+4])[0]
                    values.append(value)
                
                # Module 1 (B0~B3)
                for i in range(4):
                    self.module1_spins[i].setValue(values[i])
                
                # Module 2 (B0~B3)
                for i in range(4):
                    self.module2_spins[i].setValue(values[4 + i])
                
                QMessageBox.information(self, "완료", "Gate Bias 설정을 로드했습니다.")
            else:
                QMessageBox.warning(self, "오류", "응답 데이터 형식 오류")
        else:
            QMessageBox.warning(self, "오류", "설정 로드 실패")
    
    def apply_settings(self):
        """설정 적용"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        # TODO: Gate Bias SET 명령어는 VHF 매뉴얼 확인 필요
        QMessageBox.information(self, "정보", "Gate Bias 설정 기능은 준비 중입니다.")