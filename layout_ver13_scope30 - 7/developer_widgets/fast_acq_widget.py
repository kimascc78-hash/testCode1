"""
Fast Data Acquisition Widget
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QSpinBox, QMessageBox
)
from rf_protocol import RFProtocol
from developer_data_manager import DeveloperDataManager
import struct


class FastAcqWidget(QGroupBox):
    """Fast Data Acquisition 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("Fast Data Acquisition", parent)
        self.parent = parent
        self.network_manager = network_manager
        self.dev_data_manager = DeveloperDataManager()  # ← 이 줄 추가
        
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self.on_toggle)
        
        self.init_ui()
        self.on_toggle(False)
        
    def init_ui(self):
        """UI 초기화"""
        self.main_layout = QVBoxLayout(self)
        
        # Memory Type
        memory_layout = QHBoxLayout()
        memory_layout.addWidget(QLabel("Memory Type:"))
        
        self.memory_type_combo = QComboBox()
        self.memory_type_combo.addItems(["Ring Buffer", "Single Shot"])
        
        memory_layout.addWidget(self.memory_type_combo)
        memory_layout.addStretch()
        self.main_layout.addLayout(memory_layout)
        
        # Trigger Source
        trigger_layout = QHBoxLayout()
        trigger_layout.addWidget(QLabel("Trigger Source:"))
        
        self.trigger_source_combo = QComboBox()
        self.trigger_source_combo.addItems(["Manual", "External", "Auto"])
        
        trigger_layout.addWidget(self.trigger_source_combo)
        trigger_layout.addStretch()
        self.main_layout.addLayout(trigger_layout)
        
        # Trigger Position
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Trigger Position:"))
        
        self.trigger_position_combo = QComboBox()
        self.trigger_position_combo.addItems(["Start", "Center", "End"])
        
        position_layout.addWidget(self.trigger_position_combo)
        position_layout.addStretch()
        self.main_layout.addLayout(position_layout)
        
        # Control
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("Control:"))
        
        self.control_combo = QComboBox()
        self.control_combo.addItems(["Stop", "Start", "Single"])
        
        control_layout.addWidget(self.control_combo)
        control_layout.addStretch()
        self.main_layout.addLayout(control_layout)
        
        # Sample Rate
        sample_layout = QHBoxLayout()
        sample_layout.addWidget(QLabel("Sample Rate:"))
        
        self.sample_rate_spin = QSpinBox()
        self.sample_rate_spin.setRange(1000, 1000000)
        self.sample_rate_spin.setValue(10000)
        self.sample_rate_spin.setSuffix(" Hz")
        
        sample_layout.addWidget(self.sample_rate_spin)
        sample_layout.addStretch()
        self.main_layout.addLayout(sample_layout)
        
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
            RFProtocol.CMD_FAST_ACQ_GET,
            RFProtocol.SUBCMD_FAST_ACQ,
            wait_response=True,
            sync=True
        )
        
        if result.success and result.response_data:
            # ✅ parse_response() 사용
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and parsed['data']:
                settings = self.dev_data_manager.parse_fast_acq_data(parsed['data'])
                
                if settings:
                    self.memory_type_combo.setCurrentIndex(settings['memory_type'])
                    self.trigger_source_combo.setCurrentIndex(settings['trigger_source'])
                    self.trigger_position_combo.setCurrentIndex(settings['trigger_position'])
                    self.control_combo.setCurrentIndex(settings['control'])
                    self.sample_rate_spin.setValue(settings['sample_rate'])
                    
                    QMessageBox.information(self, "완료", "Fast Acquisition 설정을 로드했습니다.")
                else:
                    QMessageBox.warning(self, "오류", "Fast Acq 데이터 파싱 실패")
            else:
                QMessageBox.warning(self, "오류", "응답 데이터가 없습니다.")
        else:
            QMessageBox.warning(self, "오류", "설정 로드 실패")
    
    def apply_settings(self):
        """설정 적용"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        data = bytearray()
        data.append(self.memory_type_combo.currentIndex())
        data.append(self.trigger_source_combo.currentIndex())
        data.append(self.trigger_position_combo.currentIndex())
        data.append(self.control_combo.currentIndex())
        data.extend(struct.pack('<I', self.sample_rate_spin.value()))
        
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_FAST_ACQ_SET,
            RFProtocol.SUBCMD_FAST_ACQ,
            data=bytes(data),
            wait_response=True,
            sync=True
        )
        
        if result.success:
            QMessageBox.information(self, "완료", "Fast Acquisition 설정이 적용되었습니다.")
        else:
            QMessageBox.warning(self, "오류", f"설정 적용 실패: {result.message}")