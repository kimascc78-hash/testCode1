"""
Min/Max Control Widget
최소/최대 제어 제한값 설정 (Ctlminmax_t × 4)
"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDoubleSpinBox, QMessageBox, QGridLayout, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt
from rf_protocol import RFProtocol
from developer_widgets.system_widgets.system_data_manager import SystemDataManager
from ui_widgets import SmartSpinBox, SmartDoubleSpinBox

class MinMaxControlWidget(QGroupBox):
    """Min/Max Control 위젯"""
    
    def __init__(self, parent, network_manager):
        super().__init__("Min/Max Control Limits", parent)
        self.parent = parent
        self.network_manager = network_manager
        self.sys_data_manager = SystemDataManager()
        
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self.on_toggle)
        
        # 4개 섹션의 위젯 저장 (섹션 그룹박스, 스핀박스 딕셔너리, 콘텐츠 위젯 리스트)
        # 튜플 구조 변경: (type, QGroupBox, spinboxes, [scroll_area, button_layout])
        self.sections = []
        
        self.init_ui()
        self.initialize_sections_state()  # 초기 상태 설정 함수 호출
        self.on_toggle(False) # 메인 토글이 해제되면 모든 것을 숨김
        
    def init_ui(self):
        """UI 초기화"""
        self.main_layout = QVBoxLayout(self)
        
        # 설명
        info_label = QLabel(
            "각 섹션은 27개의 float 값을 포함합니다 (DCC, Gate PA1/PA2).\n"
            "Maximum, Minimum, Factor A, Factor B 4개 섹션으로 구성됩니다."
        )
        info_label.setStyleSheet("color: #87ceeb; font-size: 11px;")
        self.main_layout.addWidget(info_label)
        
        # ========================================
        # 4개 섹션 생성 (Accordion)
        # ========================================
        
        # Maximum Values
        max_section, max_widgets, max_contents = self.create_ctlminmax_section("Maximum Values")
        self.main_layout.addWidget(max_section)
        self.sections.append(('max', max_section, max_widgets, max_contents))
        
        # Minimum Values
        min_section, min_widgets, min_contents = self.create_ctlminmax_section("Minimum Values")
        self.main_layout.addWidget(min_section)
        self.sections.append(('min', min_section, min_widgets, min_contents))
        
        # Factor A
        fa_section, fa_widgets, fa_contents = self.create_ctlminmax_section("Factor A")
        self.main_layout.addWidget(fa_section)
        self.sections.append(('fa', fa_section, fa_widgets, fa_contents))
        
        # Factor B
        fb_section, fb_widgets, fb_contents = self.create_ctlminmax_section("Factor B")
        self.main_layout.addWidget(fb_section)
        self.sections.append(('fb', fb_section, fb_widgets, fb_contents))
        
        # ========================================
        # 전체 버튼
        # ========================================
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        load_all_button = QPushButton("Load All")
        load_all_button.clicked.connect(self.load_all_settings)
        button_layout.addWidget(load_all_button)
        
        reset_all_button = QPushButton("Reset All")
        reset_all_button.clicked.connect(self.reset_all_settings)
        button_layout.addWidget(reset_all_button)
        
        apply_all_button = QPushButton("Apply All")
        apply_all_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        apply_all_button.clicked.connect(self.apply_all_settings)
        button_layout.addWidget(apply_all_button)
        
        # 메인 버튼 레이아웃은 위젯으로 감싸서 쉽게 제어
        self.all_buttons_widget = QWidget()
        self.all_buttons_widget.setLayout(button_layout)
        self.main_layout.addWidget(self.all_buttons_widget)
    
    def initialize_sections_state(self):
        """초기 상태 강제 설정: 모든 섹션의 콘텐츠를 숨기고 체크 해제"""
        # 생성자에서 호출되어 위젯이 화면에 보이기 전에 초기 상태 설정
        for _, section, _, contents in self.sections:
            section.setChecked(False)
            # 스크롤 영역과 버튼 레이아웃을 명확하게 숨김
            for widget in contents:
                widget.setVisible(False)
    
    def create_ctlminmax_section(self, title):
        """
        Ctlminmax_t 구조체용 섹션 생성
        
        Returns:
            tuple: (QGroupBox, dict of spinboxes, list of content widgets)
        """
        section = QGroupBox(title)
        section.setCheckable(True)
        section.setChecked(False)
        # on_section_toggled에서 content 위젯을 직접 제어할 수 있도록 람다 함수에 전달
        section.toggled.connect(lambda checked: self.on_section_toggled(section, checked, contents))
        
        layout = QVBoxLayout(section)
        
        # 스크롤 영역 (27개 필드가 많으므로)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(400) # 최대 높이는 유지
        
        scroll_content = QWidget()
        scroll_layout = QGridLayout(scroll_content)
        
        # 27개 float 필드 정의 (기존과 동일)
        fields = [
            # DCC 필드 (5개)
            ('dcc_dcout_voltage', 'DCC DC Voltage', 'V'),
            ('dcc_dcout_current', 'DCC DC Current', 'A'),
            ('dcc_pfcout_current', 'DCC PFC Current', 'A'),
            ('dcc_rfamp_temp', 'DCC RF Amp Temp', '°C'),
            ('dcc_waterplate_temp', 'DCC Water Temp', '°C'),
            
            # Gate PA1 필드 (12개)
            ('gate_pa1_isens', 'Gate PA1 ISens', 'A'),
            ('gate_pa1_vsens', 'Gate PA1 VSens', 'V'),
            ('gate_pa1_temp', 'Gate PA1 Temp', '°C'),
            ('gate_pa1_return_0', 'Gate PA1 Return 0', ''),
            ('gate_pa1_return_1', 'Gate PA1 Return 1', ''),
            ('gate_pa1_return_2', 'Gate PA1 Return 2', ''),
            ('gate_pa1_return_3', 'Gate PA1 Return 3', ''),
            ('gate_pa1_bias_0', 'Gate PA1 Bias 0', 'V'),
            ('gate_pa1_bias_1', 'Gate PA1 Bias 1', 'V'),
            ('gate_pa1_bias_2', 'Gate PA1 Bias 2', 'V'),
            ('gate_pa1_bias_3', 'Gate PA1 Bias 3', 'V'),
            
            # Gate PA2 필드 (11개)
            ('gate_pa2_isens', 'Gate PA2 ISens', 'A'),
            ('gate_pa2_vsens', 'Gate PA2 VSens', 'V'),
            ('gate_pa2_temp', 'Gate PA2 Temp', '°C'),
            ('gate_pa2_return_0', 'Gate PA2 Return 0', ''),
            ('gate_pa2_return_1', 'Gate PA2 Return 1', ''),
            ('gate_pa2_return_2', 'Gate PA2 Return 2', ''),
            ('gate_pa2_return_3', 'Gate PA2 Return 3', ''),
            ('gate_pa2_bias_0', 'Gate PA2 Bias 0', 'V'),
            ('gate_pa2_bias_1', 'Gate PA1 Bias 1', 'V'),
            ('gate_pa2_bias_2', 'Gate PA2 Bias 2', 'V'),
            ('gate_pa2_bias_3', 'Gate PA2 Bias 3', 'V')
        ]
        
        spinboxes = {}
        
        # 3열 구성을 위한 행(row) 및 열(column) 계산: 
        # 한 행에 '레이블+스핀박스' 쌍이 3개 들어감 (총 6개 컬럼)
        for i, (key, label, unit) in enumerate(fields):
            # i // 3: 0, 0, 0, 1, 1, 1, ...
            row = i // 3
            
            # i % 3: 0 (첫째 열), 1 (둘째 열), 2 (셋째 열)
            # 0: Col 0, 1
            # 1: Col 2, 3
            # 2: Col 4, 5
            col_offset = (i % 3) * 2 
            
            # 레이블
            scroll_layout.addWidget(QLabel(f"{label}:"), row, col_offset)
            
            # 스핀 박스
            spin = SmartDoubleSpinBox()
            spin.setRange(-1000.0, 1000.0)
            spin.setValue(0.0)
            spin.setDecimals(3)
            if unit:
                spin.setSuffix(f" {unit}")
            # 스핀 박스의 최소 너비 설정은 그대로 유지
            spin.setMinimumWidth(120)
            
            scroll_layout.addWidget(spin, row, col_offset + 1)
            spinboxes[key] = spin
        
        # 기존에 있던 setColumnStretch(2, 1)는 2열 구성 시 가운데 간격 확보를 위함이었으므로 제거하거나 
        # 마지막 컬럼에 스트레치를 주어 여백을 확보
        scroll_layout.setColumnStretch(6, 1)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # 개별 섹션 버튼 (기존과 동일)
        section_button_layout = QHBoxLayout()
        section_button_layout.addStretch()
        
        load_button = QPushButton("Load")
        load_button.clicked.connect(lambda: self.load_section(title))
        section_button_layout.addWidget(load_button)
        
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(lambda: self.reset_section(spinboxes))
        section_button_layout.addWidget(reset_button)
        
        apply_button = QPushButton("Apply")
        apply_button.setStyleSheet("background-color: #4CAF50; color: white;")
        apply_button.clicked.connect(lambda: self.apply_section(title, spinboxes))
        section_button_layout.addWidget(apply_button)
        
        # 버튼 레이아웃을 위젯으로 감싸서 쉽게 제어
        button_widget = QWidget()
        button_widget.setLayout(section_button_layout)
        layout.addWidget(button_widget)
        
        # 섹션 콘텐츠 위젯 리스트 반환 (scroll 영역과 button 위젯)
        contents = [scroll, button_widget]
        
        return section, spinboxes, contents
    
    def on_toggle(self, checked):
        """접기/펼치기"""
        print(f"MinMaxControlWidget toggled: checked={checked}")
        
        # 상단 정보 라벨과 전체 버튼 위젯의 가시성 제어
        self.main_layout.itemAt(0).widget().setVisible(checked) # Info Label
        self.all_buttons_widget.setVisible(checked) # All Buttons
        
        # 4개 섹션 그룹 박스 위젯의 가시성 제어
        for section_type, section, widgets, contents in self.sections:
            section.setVisible(checked)
            
            if not checked:
                # 메인 토글이 해제되면 섹션도 닫고 콘텐츠도 숨김
                section.setChecked(False)
                for widget in contents:
                    widget.setVisible(False)
            
        # 상위 체크 시 첫 번째 섹션(Maximum Values)만 펼치고 나머지 접기
        if checked and self.sections:
            # 첫 번째 섹션만 열기
            first_section_groupbox = self.sections[0][1]
            first_section_contents = self.sections[0][3]
            
            # 첫 번째 섹션이 이미 열려있지 않은 경우에만 로직 실행 (무한 루프 방지)
            if not first_section_groupbox.isChecked():
                first_section_groupbox.setChecked(True) 
                
            # 첫 번째 섹션 콘텐츠 보이기
            for widget in first_section_contents:
                widget.setVisible(True)
                
            # 나머지 섹션은 닫고 콘텐츠 숨기기
            for section_type, section, widgets, contents in self.sections[1:]:
                if section.isChecked():
                    section.setChecked(False) # on_section_toggled가 호출되어 콘텐츠를 숨길 것임
                else:
                    for widget in contents:
                        widget.setVisible(False)
    
    def on_section_toggled(self, sender_section, checked, sender_contents):
        """섹션 토글 시 다른 섹션들 닫기 및 콘텐츠 가시성 제어 (Accordion)"""
        print(f"Section toggled: {sender_section.title()}, checked={checked}")
        
        # 1. 콘텐츠 가시성 제어
        for widget in sender_contents:
            widget.setVisible(checked)
        
        # 2. 상호 배타적 토글 (아코디언 동작)
        if checked:
            for section_type, section, widgets, contents in self.sections:
                if section != sender_section and section.isChecked():
                    # 다른 섹션을 닫음 (setChecked(False)는 다시 on_section_toggled를 호출하여 콘텐츠를 숨김)
                    section.setChecked(False)
                elif section != sender_section and not section.isChecked():
                    # 체크 해제된 상태에서도 콘텐츠가 혹시 보이는 경우를 대비
                    for widget in contents:
                        widget.setVisible(False)
    
    def load_section(self, section_name):
        """개별 섹션 로드"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        # ========================================
        # 1단계: 섹션별 GET CMD 매핑
        # ========================================
        cmd_map = {
            'Maximum Values': (RFProtocol.CMD_DCC_GATE_MAX_GET, RFProtocol.SUBCMD_DCC_GATE_MAX),
            'Minimum Values': (RFProtocol.CMD_DCC_GATE_MIN_GET, RFProtocol.SUBCMD_DCC_GATE_MIN),
            'Factor A': (RFProtocol.CMD_DCC_FACTOR_A_GET, RFProtocol.SUBCMD_DCC_FACTOR_A),
            'Factor B': (RFProtocol.CMD_DCC_FACTOR_B_GET, RFProtocol.SUBCMD_DCC_FACTOR_B)
        }
        
        if section_name not in cmd_map:
            QMessageBox.critical(self, "오류", f"알 수 없는 섹션: {section_name}")
            return
        
        cmd, subcmd = cmd_map[section_name]
        
        # ========================================
        # 2단계: GET 명령어 전송
        # ========================================
        result = self.network_manager.client_thread.send_command(
            cmd,
            subcmd,
            wait_response=True,
            sync=True
        )
        
        if not result.success:
            QMessageBox.warning(
                self,
                "오류",
                f"{section_name} 로드 실패: {result.message}"
            )
            return
        
        if not result.response_data:
            QMessageBox.warning(self, "오류", "응답 데이터가 없습니다.")
            return
        
        # ========================================
        # 3단계: 응답 데이터 파싱
        # ========================================
        parsed = RFProtocol.parse_response(result.response_data)
        
        if not parsed or len(parsed['data']) < 112:
            QMessageBox.warning(
                self,
                "오류",
                f"응답 데이터 형식 오류\n예상: 112 bytes, 실제: {len(parsed['data']) if parsed else 0} bytes"
            )
            return
        
        try:
            import struct
            data = parsed['data']
            
            # 27개 float 값 + 1개 uint32 enable_flag
            values = []
            for i in range(27):
                offset = i * 4
                value = struct.unpack('<f', data[offset:offset+4])[0]
                values.append(value)
            
            enable_flag = struct.unpack('<I', data[108:112])[0]
            
            # ========================================
            # 4단계: UI 업데이트 - 해당 섹션의 spinbox 찾기
            # ========================================
            target_section = None
            for section_type, section_groupbox, spinboxes, contents in self.sections:
                if section_groupbox.title() == section_name:
                    target_section = (section_type, section_groupbox, spinboxes, contents)
                    break
            
            if not target_section:
                QMessageBox.warning(self, "오류", f"섹션 '{section_name}'을 찾을 수 없습니다.")
                return
            
            _, _, spinboxes, _ = target_section
            
            # spinboxes는 딕셔너리: {'field_name': QDoubleSpinBox}
            # 27개 필드 순서 (system_data_manager.py의 create_ctlminmax_data와 동일)
            field_names = [
                # DCC (5개)
                'dcc_dcout_voltage', 'dcc_dcout_current', 'dcc_pfcout_current',
                'dcc_rfamp_temp', 'dcc_waterplate_temp',
                
                # PA1 (11개: 3 + 4 + 4)
                'gate_pa1_isens', 'gate_pa1_vsens', 'gate_pa1_temp',
                'gate_pa1_return_0', 'gate_pa1_return_1', 'gate_pa1_return_2', 'gate_pa1_return_3',
                'gate_pa1_bias_0', 'gate_pa1_bias_1', 'gate_pa1_bias_2', 'gate_pa1_bias_3',
                
                # PA2 (11개: 3 + 4 + 4)
                'gate_pa2_isens', 'gate_pa2_vsens', 'gate_pa2_temp',
                'gate_pa2_return_0', 'gate_pa2_return_1', 'gate_pa2_return_2', 'gate_pa2_return_3',
                'gate_pa2_bias_0', 'gate_pa2_bias_1', 'gate_pa2_bias_2', 'gate_pa2_bias_3'
            ]
            
            # spinbox에 값 설정
            for i, field_name in enumerate(field_names):
                if field_name in spinboxes:
                    spinboxes[field_name].setValue(values[i])
            
            QMessageBox.information(
                self,
                "완료",
                f"✅ {section_name} 설정을 로드했습니다.\n\n"
                f"• 로드된 값 개수: {len(values)}\n"
                f"• Enable Flag: {enable_flag}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "오류",
                f"데이터 파싱 중 오류 발생:\n{str(e)}"
            )
    
    def reset_section(self, spinboxes):
        """개별 섹션 리셋"""
        reply = QMessageBox.question(
            self,
            "확인",
            "이 섹션을 기본값(0)으로 초기화하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        for spin in spinboxes.values():
            spin.setValue(0.0)
    
    def apply_section(self, section_name, spinboxes):
        """개별 섹션 적용"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        # 확인 메시지
        reply = QMessageBox.question(
            self,
            "확인",
            f"{section_name} 설정을 적용하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 설정 수집
        settings = {}
        for key, spin in spinboxes.items():
            settings[key] = spin.value()
        
        settings['enable_flag'] = 0  # 기본값
        
        # 데이터 생성
        success, data, message = self.sys_data_manager.create_ctlminmax_data(settings)
        
        if not success:
            QMessageBox.critical(self, "오류", message)
            return
        
        # 섹션별 CMD 매핑 (펌웨어 Line 876-885)
        cmd_map = {
            'Maximum Values': (RFProtocol.CMD_DCC_GATE_MAX_SET, RFProtocol.SUBCMD_DCC_GATE_MAX),
            'Minimum Values': (RFProtocol.CMD_DCC_GATE_MIN_SET, RFProtocol.SUBCMD_DCC_GATE_MIN),
            'Factor A': (RFProtocol.CMD_DCC_FACTOR_A_SET, RFProtocol.SUBCMD_DCC_FACTOR_A),
            'Factor B': (RFProtocol.CMD_DCC_FACTOR_B_SET, RFProtocol.SUBCMD_DCC_FACTOR_B)
        }
        
        if section_name not in cmd_map:
            QMessageBox.critical(self, "오류", f"알 수 없는 섹션: {section_name}")
            return
        
        cmd, subcmd = cmd_map[section_name]
        
        # 명령어 전송
        result = self.network_manager.client_thread.send_command(
            cmd,
            subcmd,
            data=data,
            wait_response=True,
            sync=True
        )
        
        if result.success:
            QMessageBox.information(self, "완료", f"{section_name}이(가) 적용되었습니다.")
        else:
            QMessageBox.warning(self, "오류", f"설정 적용 실패: {result.message}")
    
    #############
    def load_all_settings(self):
        """🔧 FIXED: 전체 설정 로드 - 4개 섹션 모두 로드"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        # 🔧 NEW: 4개 섹션 모두 로드
        success_count = 0
        failed_sections = []
        
        section_names = ["Maximum Values", "Minimum Values", "Factor A", "Factor B"]
        cmd_map = {
            'Maximum Values': (RFProtocol.CMD_DCC_GATE_MAX_GET, RFProtocol.SUBCMD_DCC_GATE_MAX),
            'Minimum Values': (RFProtocol.CMD_DCC_GATE_MIN_GET, RFProtocol.SUBCMD_DCC_GATE_MIN),
            'Factor A': (RFProtocol.CMD_DCC_FACTOR_A_GET, RFProtocol.SUBCMD_DCC_FACTOR_A),
            'Factor B': (RFProtocol.CMD_DCC_FACTOR_B_GET, RFProtocol.SUBCMD_DCC_FACTOR_B)
        }
        
        for section_name in section_names:
            cmd, subcmd = cmd_map[section_name]
            
            # GET 명령어 전송
            result = self.network_manager.client_thread.send_command(
                cmd,
                subcmd,
                wait_response=True,
                sync=True
            )
            
            if result.success and result.response_data:
                parsed = RFProtocol.parse_response(result.response_data)
                if parsed and len(parsed['data']) >= 112:
                    # 데이터 파싱
                    data_dict = self.sys_data_manager.parse_ctlminmax_data(parsed['data'])
                    
                    if data_dict:
                        # UI 업데이트 - 해당 섹션 찾기
                        target_spinboxes = None
                        for section_type, section, spinboxes, contents in self.sections:
                            if section.title() == section_name:
                                target_spinboxes = spinboxes
                                break
                        
                        if target_spinboxes:
                            # 스핀박스 값 업데이트
                            for key, spin in target_spinboxes.items():
                                if key in data_dict:
                                    spin.setValue(float(data_dict[key]))
                            
                            success_count += 1
                        else:
                            failed_sections.append(section_name + " (위젯 찾기 실패)")
                    else:
                        failed_sections.append(section_name + " (파싱 실패)")
                else:
                    failed_sections.append(section_name + " (데이터 크기 오류)")
            else:
                failed_sections.append(section_name + " (통신 실패)")
        
        # 🔧 NEW: 결과 메시지
        if success_count == 4:
            QMessageBox.information(
                self, 
                "완료", 
                "✅ 모든 섹션을 성공적으로 로드했습니다.\n\n"
                "- Maximum Values ✓\n"
                "- Minimum Values ✓\n"
                "- Factor A ✓\n"
                "- Factor B ✓"
            )
        elif success_count > 0:
            failed_list = "\n".join(f"- {s}" for s in failed_sections)
            QMessageBox.warning(
                self,
                "부분 완료",
                f"⚠️ {success_count}/4 섹션 로드 성공\n\n"
                f"실패한 섹션:\n{failed_list}"
            )
        else:
            failed_list = "\n".join(f"- {s}" for s in failed_sections)
            QMessageBox.critical(
                self,
                "실패",
                f"❌ 모든 섹션 로드 실패\n\n"
                f"실패한 섹션:\n{failed_list}"
            )
    #############
    
    def reset_all_settings(self):
        """전체 설정 리셋"""
        reply = QMessageBox.question(
            self,
            "확인",
            "모든 섹션을 기본값(0)으로 초기화하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        for section_type, section, spinboxes, contents in self.sections:
            for spin in spinboxes.values():
                spin.setValue(0.0)
    
    ######
    def apply_all_settings(self):
        """전체 설정 적용"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        reply = QMessageBox.question(
            self,
            "확인",
            "모든 섹션의 설정을 적용하시겠습니까?\n"
            "(Maximum, Minimum, Factor A, Factor B)",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 각 섹션별로 데이터 생성 및 전송
        success_count = 0
        failed_sections = []
        
        cmd_map = {
            'Maximum Values': (RFProtocol.CMD_DCC_GATE_MAX_SET, RFProtocol.SUBCMD_DCC_GATE_MAX),
            'Minimum Values': (RFProtocol.CMD_DCC_GATE_MIN_SET, RFProtocol.SUBCMD_DCC_GATE_MIN),
            'Factor A': (RFProtocol.CMD_DCC_FACTOR_A_SET, RFProtocol.SUBCMD_DCC_FACTOR_A),
            'Factor B': (RFProtocol.CMD_DCC_FACTOR_B_SET, RFProtocol.SUBCMD_DCC_FACTOR_B)
        }
        
        for section_type, section, spinboxes, contents in self.sections:
            section_name = section.title()
            
            # 설정 수집
            settings = {}
            for key, spin in spinboxes.items():
                settings[key] = spin.value()
            settings['enable_flag'] = 0
            
            # 데이터 생성
            success, data, message = self.sys_data_manager.create_ctlminmax_data(settings)
            
            if not success:
                failed_sections.append(section_name + " (데이터 생성 실패)")
                continue
            
            # 명령어 전송
            cmd, subcmd = cmd_map.get(section_name, (None, None))
            if not cmd:
                failed_sections.append(section_name + " (명령어 매핑 실패)")
                continue
            
            result = self.network_manager.client_thread.send_command(
                cmd,
                subcmd,
                data=data,
                wait_response=True,
                sync=True
            )
            
            if result.success:
                success_count += 1
            else:
                failed_sections.append(section_name + f" ({result.message})")
        
        # 결과 메시지
        if success_count == 4:
            QMessageBox.information(
                self,
                "완료",
                "✅ 모든 섹션이 성공적으로 적용되었습니다.\n\n"
                "- Maximum Values ✓\n"
                "- Minimum Values ✓\n"
                "- Factor A ✓\n"
                "- Factor B ✓"
            )
        elif success_count > 0:
            failed_list = "\n".join(f"- {s}" for s in failed_sections)
            QMessageBox.warning(
                self,
                "부분 완료",
                f"⚠️ {success_count}/4 섹션 적용 성공\n\n"
                f"실패한 섹션:\n{failed_list}"
            )
        else:
            failed_list = "\n".join(f"- {s}" for s in failed_sections)
            QMessageBox.critical(
                self,
                "실패",
                f"❌ 모든 섹션 적용 실패\n\n"
                f"실패한 섹션:\n{failed_list}"
            )
    ######