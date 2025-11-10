"""
Gate Bias Config Widget
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDoubleSpinBox, QMessageBox
)
from rf_protocol import RFProtocol
import struct
from developer_widgets.system_widgets.system_data_manager import SystemDataManager
from ui_widgets import SmartSpinBox, SmartDoubleSpinBox

class GateBiasWidget(QGroupBox):
    """Gate Bias Config 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("Gate Bias Config", parent)
        self.parent = parent
        self.network_manager = network_manager
        self.sys_data_manager = SystemDataManager()
        
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
            spin = SmartDoubleSpinBox()
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
            spin = SmartDoubleSpinBox()
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
    
    def apply_settings(self):
        """설정 적용"""
        reply = QMessageBox.question(
            self, "확인",
            "Gate Bias 설정을 적용하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 설정 수집 (8개 float)
        settings = {}
        for i in range(4):
            settings[f'module1_bias_{i}'] = self.module1_spins[i].value()
            settings[f'module2_bias_{i}'] = self.module2_spins[i].value()
        
        # 데이터 생성 (32 bytes)
        success, data, message = self.sys_data_manager.create_gate_bias_data(settings)
        
        if not success:
            QMessageBox.critical(self, "오류", message)
            return
        
        # 명령어 전송 (펌웨어 Line 692)
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_GLOBAL_CONFIG_SET,
            RFProtocol.SUBCMD_GATE_BIAS,
            data=data,
            wait_response=True,
            sync=True
        )
        
        if result.success:
            QMessageBox.information(self, "완료", "Gate Bias가 적용되었습니다.")
        else:
            QMessageBox.warning(self, "오류", f"설정 적용 실패: {result.message}")

    def load_settings(self):
        """설정 로드"""
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_GLOBAL_CONFIG_GET,
            RFProtocol.SUBCMD_GATE_BIAS,
            wait_response=True,
            sync=True
        )
        
        if result.success and result.response_data:
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and len(parsed['data']) >= 32:
                bias_data = self.sys_data_manager.parse_gate_bias_data(parsed['data'])
                
                if bias_data:
                    for i in range(4):
                        self.module1_spins[i].setValue(bias_data[f'module1_bias_{i}'])
                        self.module2_spins[i].setValue(bias_data[f'module2_bias_{i}'])
                    
                    QMessageBox.information(self, "완료", "Gate Bias를 로드했습니다.")