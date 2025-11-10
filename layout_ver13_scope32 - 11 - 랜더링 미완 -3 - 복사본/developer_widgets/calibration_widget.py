"""
Calibration Widget
캘리브레이션 설정 및 테이블 관리
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSpinBox, QComboBox, QMessageBox, QGridLayout
)
from PyQt5.QtCore import Qt
from rf_protocol import RFProtocol
import struct
from ui_widgets import SmartSpinBox, SmartDoubleSpinBox

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
        
        # ========================================
        # 경고 메시지
        # ========================================
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
        # Calibration Control (QGridLayout으로 정렬)
        # ========================================
        control_group = QGroupBox("Calibration Control")
        control_layout = QGridLayout(control_group)
        row = 0
        
        # Cal Mode
        control_layout.addWidget(QLabel("Cal Mode:"), row, 0)
        self.cal_mode_combo = QComboBox()
        self.cal_mode_combo.addItems(["Manual", "Auto"])
        control_layout.addWidget(self.cal_mode_combo, row, 1)
        row += 1
        
        # FWD DAC Value
        control_layout.addWidget(QLabel("FWD DAC Value:"), row, 0)
        self.fwd_dac_spin = SmartSpinBox()
        self.fwd_dac_spin.setRange(0, 65535)
        self.fwd_dac_spin.setValue(0)
        control_layout.addWidget(self.fwd_dac_spin, row, 1)
        row += 1
        
        # REF DAC Value
        control_layout.addWidget(QLabel("REF DAC Value:"), row, 0)
        self.ref_dac_spin = SmartSpinBox()
        self.ref_dac_spin.setRange(0, 65535)
        self.ref_dac_spin.setValue(0)
        control_layout.addWidget(self.ref_dac_spin, row, 1)
        row += 1
        
        # RF Set DAC Value
        control_layout.addWidget(QLabel("RF Set DAC Value:"), row, 0)
        self.rfset_dac_spin = SmartSpinBox()
        self.rfset_dac_spin.setRange(0, 65535)
        self.rfset_dac_spin.setValue(0)
        control_layout.addWidget(self.rfset_dac_spin, row, 1)
        
        control_layout.setColumnStretch(2, 1)  # 3열에 stretch 추가
        
        self.main_layout.addWidget(control_group)
        
        # ========================================
        # 버튼 (그룹 밖에 별도 추가)
        # ========================================
        control_button_layout = QHBoxLayout()
        control_button_layout.addStretch()
        
        load_control_button = QPushButton("Load")
        load_control_button.clicked.connect(self.load_control)
        control_button_layout.addWidget(load_control_button)
        
        apply_control_button = QPushButton("Apply")
        apply_control_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        apply_control_button.clicked.connect(self.apply_control)
        control_button_layout.addWidget(apply_control_button)
        
        self.main_layout.addLayout(control_button_layout)
        
        # ========================================
        # Calibration Tables
        # ========================================
        tables_group = QGroupBox("Calibration Tables")
        tables_layout = QVBoxLayout(tables_group)
        
        rfset_table_btn = QPushButton("Edit RF Set DAC Table (26 points)...")
        rfset_table_btn.clicked.connect(lambda: self.open_table_editor("RF Set DAC"))
        tables_layout.addWidget(rfset_table_btn)
        
        fwdload_table_btn = QPushButton("Edit User FWD/LOAD Table (26 points)...")
        fwdload_table_btn.clicked.connect(lambda: self.open_table_editor("User FWD/LOAD"))
        tables_layout.addWidget(fwdload_table_btn)
        
        ref_table_btn = QPushButton("Edit User REF Table (26 points)...")
        ref_table_btn.clicked.connect(lambda: self.open_table_editor("User REF"))
        tables_layout.addWidget(ref_table_btn)
        
        rfsetin_table_btn = QPushButton("Edit User RF Set IN Table (26 points)...")
        rfsetin_table_btn.clicked.connect(lambda: self.open_table_editor("User RF Set IN"))
        tables_layout.addWidget(rfsetin_table_btn)
        
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
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and len(parsed['data']) >= 12:
                cal_mode = struct.unpack('<H', parsed['data'][0:2])[0]
                fwd_dac = struct.unpack('<H', parsed['data'][2:4])[0]
                ref_dac = struct.unpack('<H', parsed['data'][4:6])[0]
                rfset_dac = struct.unpack('<H', parsed['data'][6:8])[0]
                
                self.cal_mode_combo.setCurrentIndex(cal_mode)
                self.fwd_dac_spin.setValue(fwd_dac)
                self.ref_dac_spin.setValue(ref_dac)
                self.rfset_dac_spin.setValue(rfset_dac)
                
                QMessageBox.information(self, "완료", "Calibration Control을 로드했습니다.")
            else:
                QMessageBox.warning(self, "오류", "응답 데이터 형식 오류")
        else:
            QMessageBox.warning(self, "오류", "설정 로드 실패")
    
    def apply_control(self):
        """Calibration Control 적용"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        status_data = getattr(self.parent.parent.parent, 'latest_status_data', {})
        rf_status = status_data.get("RF On/Off", "Unknown")
        
        if rf_status == "ON":
            QMessageBox.critical(
                self,
                "오류",
                "캘리브레이션은 RF OFF 상태에서만 가능합니다.\n먼저 RF를 끄십시오."
            )
            return
        
        data = bytearray()
        data.extend(struct.pack('<H', self.cal_mode_combo.currentIndex()))
        data.extend(struct.pack('<H', self.fwd_dac_spin.value()))
        data.extend(struct.pack('<H', self.ref_dac_spin.value()))
        data.extend(struct.pack('<H', self.rfset_dac_spin.value()))
        data.extend(struct.pack('<H', 0))
        data.extend(struct.pack('<H', 0))
        
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
        dialog.show()  # 비동기적으로 표시