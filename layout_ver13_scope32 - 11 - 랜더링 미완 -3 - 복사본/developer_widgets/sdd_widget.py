"""
SDD Config Widget
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QComboBox
)
from rf_protocol import RFProtocol
import struct
from developer_data_manager import DeveloperDataManager
from ui_widgets import SmartSpinBox


# ========================================
# GUI Model 매핑 테이블
# TODO: 각 모델에 해당하는 정확한 값을 VHF 매뉴얼에서 확인 후 수정 필요
# ========================================
GUI_MODEL_MAP = {
    "Gen. 13.56MHz": 0,   # TODO: 정확한 값 확인 필요
    "Gen. 27.125MHz": 1,  # TODO: 정확한 값 확인 필요
    "Gen. 40MHz": 2,      # TODO: 정확한 값 확인 필요
    "Gen. 60MHz": 3,      # TODO: 정확한 값 확인 필요
}


class SDDWidget(QGroupBox):
    """SDD Config 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("SDD Config", parent)
        self.parent = parent
        self.network_manager = network_manager
        self.dev_data_manager = DeveloperDataManager()
        
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self.on_toggle)
        
        self.init_ui()
        self.on_toggle(False)
        
    def init_ui(self):
        """UI 초기화"""
        self.main_layout = QVBoxLayout(self)
        
        # ========================================
        # 한 줄 레이아웃: Gen. Model + Pulsing Count
        # ========================================
        control_layout = QHBoxLayout()
        
        # Gen. Model
        control_layout.addWidget(QLabel("Gen. Model:"))
        
        self.gui_model_combo = QComboBox()
        self.gui_model_combo.setMinimumWidth(150)
        
        # 모델 리스트 추가
        for model_name, model_value in GUI_MODEL_MAP.items():
            self.gui_model_combo.addItem(model_name, model_value)
        
        control_layout.addWidget(self.gui_model_combo)
        
        # Pulsing Freq/Duty Count
        control_layout.addWidget(QLabel("Pulsing Freq/Duty Count:"))
        
        self.pulsing_count_spin = SmartSpinBox()
        self.pulsing_count_spin.setRange(0, 65535)
        self.pulsing_count_spin.setValue(100)
        
        control_layout.addWidget(self.pulsing_count_spin)
        control_layout.addStretch()
        
        self.main_layout.addLayout(control_layout)
        
        # ========================================
        # 버튼
        # ========================================
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
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and parsed['data']:
                settings = self.dev_data_manager.parse_sdd_config_data(parsed['data'])
                
                if settings:
                    # GUI Model 값으로 ComboBox 인덱스 찾기
                    gui_model_value = settings['gui_model']
                    index = self.gui_model_combo.findData(gui_model_value)
                    if index >= 0:
                        self.gui_model_combo.setCurrentIndex(index)
                    else:
                        # 매칭되는 값이 없으면 경고
                        QMessageBox.warning(
                            self, 
                            "경고", 
                            f"알 수 없는 GUI Model 값: {gui_model_value}\n"
                            f"GUI_MODEL_MAP에 추가가 필요합니다."
                        )
                    
                    self.pulsing_count_spin.setValue(settings['pulsing_count'])
                    
                    QMessageBox.information(self, "완료", "SDD Config를 로드했습니다.")
                else:
                    QMessageBox.warning(self, "오류", "SDD 데이터 파싱 실패")
            else:
                QMessageBox.warning(self, "오류", "응답 데이터 형식 오류")
        else:
            QMessageBox.warning(self, "오류", "설정 로드 실패")
    
    def apply_settings(self):
        """설정 적용"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        # ComboBox에서 선택된 모델의 값 가져오기
        gui_model_value = self.gui_model_combo.currentData()
        
        if gui_model_value is None:
            QMessageBox.warning(self, "오류", "GUI Model을 선택해주세요.")
            return
        
        # 데이터 생성
        data = bytearray()
        data.extend(struct.pack('<H', gui_model_value))
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






