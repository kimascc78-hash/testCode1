"""
Calibration Widget
캘리브레이션 설정 및 테이블 관리
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSpinBox, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt
from rf_protocol import RFProtocol
import struct


class CalibrationWidget(QGroupBox):
    """Calibration 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("⚠️ Calibration (RF OFF Required)", parent)
        self.parent = parent
        self.network_manager = network_manager
        
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self.on_toggle)
        
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        self.main_layout = QVBoxLayout(self)
        
        # 경고 메시지
        warning_label = QLabel("⚠️ WARNING: Calibration requires RF to be OFF")
        warning_label.setStyleSheet("""
            QLabel {
                background-color: #FFEBEE;
                color: #C62828;
                padding: 10px;
                border: 2px solid #EF5350;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        self.main_layout.addWidget(warning_label)
        
        # ========================================
        # Calibration Control
        # ========================================
        control_group = QGroupBox("Calibration Control")
        control_layout = QVBoxLayout(control_group)
        
        # Cal Mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Cal Mode:"))
        
        self.cal_mode_combo = QComboBox()
        self.cal_mode_combo.addItems(["Manual", "Auto"])
        
        mode_layout.addWidget(self.cal_mode_combo)
        mode_layout.addStretch()
        control_layout.addLayout(mode_layout)
        
        # FWD DAC Value
        fwd_dac_layout = QHBoxLayout()
        fwd_dac_layout.addWidget(QLabel("FWD DAC Value:"))
        
        self.fwd_dac_spin = QSpinBox()
        self.fwd_dac_spin.setRange(0, 65535)
        self.fwd_dac_spin.setValue(0)
        
        fwd_dac_layout.addWidget(self.fwd_dac_spin)
        fwd_dac_layout.addStretch()
        control_layout.addLayout(fwd_dac_layout)
        
        # REF DAC Value
        ref_dac_layout = QHBoxLayout()
        ref_dac_layout.addWidget(QLabel("REF DAC Value:"))
        
        self.ref_dac_spin = QSpinBox()
        self.ref_dac_spin.setRange(0, 65535)
        self.ref_dac_spin.setValue(0)
        
        ref_dac_layout.addWidget(self.ref_dac_spin)
        ref_dac_layout.addStretch()
        control_layout.addLayout(ref_dac_layout)
        
        # RF Set DAC Value
        rfset_dac_layout = QHBoxLayout()
        rfset_dac_layout.addWidget(QLabel("RF Set DAC Value:"))
        
        self.rfset_dac_spin = QSpinBox()
        self.rfset_dac_spin.setRange(0, 65535)
        self.rfset_dac_spin.setValue(0)
        
        rfset_dac_layout.addWidget(self.rfset_dac_spin)
        rfset_dac_layout.addStretch()
        control_layout.addLayout(rfset_dac_layout)
        
        # Apply 버튼
        control_button_layout = QHBoxLayout()
        control_button_layout.addStretch()
        
        load_control_button = QPushButton("Load")
        load_control_button.clicked.connect(self.load_control)
        control_button_layout.addWidget(load_control_button)
        
        apply_control_button = QPushButton("Apply")
        apply_control_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        apply_control_button.clicked.connect(self.apply_control)
        control_button_layout.addWidget(apply_control_button)
        
        control_layout.addLayout(control_button_layout)
        
        self.main_layout.addWidget(control_group)
        
        # ========================================
        # Calibration Tables
        # ========================================
        tables_group = QGroupBox("Calibration Tables")
        tables_layout = QVBoxLayout(tables_group)
        
        # RF Set DAC Table
        rfset_table_btn = QPushButton("Edit RF Set DAC Table (26 points)...")
        rfset_table_btn.clicked.connect(lambda: self.open_table_editor("RF Set DAC"))
        tables_layout.addWidget(rfset_table_btn)
        
        # User FWD/LOAD Table
        fwdload_table_btn = QPushButton("Edit User FWD/LOAD Table (26 points)...")
        fwdload_table_btn.clicked.connect(lambda: self.open_table_editor("User FWD/LOAD"))
        tables_layout.addWidget(fwdload_table_btn)
        
        # User REF Table
        ref_table_btn = QPushButton("Edit User REF Table (26 points)...")
        ref_table_btn.clicked.connect(lambda: self.open_table_editor("User REF"))
        tables_layout.addWidget(ref_table_btn)
        
        # User RF Set IN Table
        rfsetin_table_btn = QPushButton("Edit User RF Set IN Table (26 points)...")
        rfsetin_table_btn.clicked.connect(lambda: self.open_table_editor("User RF Set IN"))
        tables_layout.addWidget(rfsetin_table_btn)
        
        # User DC Bias Table
        dcbias_table_btn = QPushButton("Edit User DC Bias Table (26 points)...")
        dcbias_table_btn.clicked.connect(lambda: self.open_table_editor("User DC Bias"))
        tables_layout.addWidget(dcbias_table_btn)
        
        self.main_layout.addWidget(tables_group)
    
    def on_toggle(self, checked):
        """접기/펼치기"""
        for i in range(self.main_layout.count()):
            item = self.main_layout.itemAt(i)
            if item.widget():
                item.widget().setVisible(checked)
    
    def load_control(self):
        """Calibration Control 로드"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_CAL_CTL_GET,
            RFProtocol.SUBCMD_CAL_CTL,
            wait_response=True,
            sync=True
        )
        
        if result.success and result.response_data:
            if len(result.response_data) >= 12:
                cal_mode = struct.unpack('<H', result.response_data[0:2])[0]
                fwd_dac = struct.unpack('<H', result.response_data[2:4])[0]
                ref_dac = struct.unpack('<H', result.response_data[4:6])[0]
                rfset_dac = struct.unpack('<H', result.response_data[6:8])[0]
                
                self.cal_mode_combo.setCurrentIndex(cal_mode)
                self.fwd_dac_spin.setValue(fwd_dac)
                self.ref_dac_spin.setValue(ref_dac)
                self.rfset_dac_spin.setValue(rfset_dac)
                
                QMessageBox.information(self, "완료", "Calibration Control을 로드했습니다.")
        else:
            QMessageBox.warning(self, "오류", "설정 로드 실패")
    
    def apply_control(self):
        """Calibration Control 적용"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        # RF 상태 확인
        status_data = getattr(self.parent.parent.parent, 'latest_status_data', {})
        rf_status = status_data.get("RF On/Off", "Unknown")
        
        if rf_status == "ON":
            QMessageBox.critical(
                self,
                "오류",
                "캘리브레이션은 RF OFF 상태에서만 가능합니다.\n먼저 RF를 끄십시오."
            )
            return
        
        # 데이터 생성
        data = bytearray()
        data.extend(struct.pack('<H', self.cal_mode_combo.currentIndex()))
        data.extend(struct.pack('<H', self.fwd_dac_spin.value()))
        data.extend(struct.pack('<H', self.ref_dac_spin.value()))
        data.extend(struct.pack('<H', self.rfset_dac_spin.value()))
        data.extend(struct.pack('<H', 0))  # Dummy2Value
        data.extend(struct.pack('<H', 0))  # Dummy3Value
        
        result = self.network_manager.client_thread.send_command(
            RFProtocol.CMD_CAL_CTL_SET,
            RFProtocol.SUBCMD_CAL_CTL,
            data=bytes(data),
            wait_response=True,
            sync=True
        )
        
        if result.success:
            QMessageBox.information(self, "완료", "Calibration Control이 적용되었습니다.")
        else:
            QMessageBox.warning(self, "오류", f"설정 적용 실패: {result.message}")
    
    def open_table_editor(self, table_name):
        """테이블 편집기 열기"""
        from developer_widgets.cal_table_dialog import CalTableDialog
        
        dialog = CalTableDialog(self, self.network_manager, table_name)
        dialog.exec_()