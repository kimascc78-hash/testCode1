"""
UI Controller Module
UI 구성 요소 관리 전담 모듈 - 상태창 색상 변화 + Status Monitor 버튼 추가
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMenuBar, QMenu,
    QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
    QCheckBox, QSizePolicy, QAction
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont
from settings_dialog import SettingsManager  # SettingsManager 임포트

class UIController:
    """UI 컨트롤러 - 기본 UI 요소들 관리"""
    
    def __init__(self, parent):
        self.parent = parent
        
        self.settings_manager = SettingsManager()  # SettingsManager 초기화
        
        # UI 요소들 초기화
        self.status_table = None
        self.rf_toggle_btn = None
        self.power_input = None
        self.clear_log_btn = None
        self.status_monitor_btn = None  # 새로 추가
        self.plot_checkboxes = []
        
        # ✅ RF 버튼 깜빡임용 타이머
        self.rf_blink_timer = QTimer()
        self.rf_blink_timer.timeout.connect(self._toggle_rf_button_color)
        self.rf_blink_state = False  # 깜빡임 상태
    
    def create_menubar(self):
        """Create Menu Bar"""
        menubar = QMenuBar(self.parent)
        self.parent.setMenuBar(menubar)
        
        # Tuning Menu
        tuning_menu = QMenu("Tuning", self.parent)
        tuning_menu.addAction("Tuning Settings").triggered.connect(self.parent.show_tuning_dialog)
        
        # Settings Menu (GUI -> Settings로 변경)
        settings_menu = QMenu("Settings", self.parent)
        settings_menu.addAction("GUI Settings").triggered.connect(self.parent.show_settings_dialog)
        
        # Log Menu
        log_menu = QMenu("Log", self.parent)
        log_menu.addAction("Save to Excel").triggered.connect(self.parent.save_excel)
        log_menu.addAction("Toggle Auto-Save to Excel").triggered.connect(self.parent.toggle_auto_save)
        log_menu.addSeparator()
        log_menu.addAction("Save Log").triggered.connect(self.parent.save_log)
        log_menu.addAction("Clear Log").triggered.connect(self.parent.log_manager.clear_log)
        
        # Status Log Toggle
        # self.status_log_action = log_menu.addAction("Show Status Logs")
        # self.status_log_action.setCheckable(True)
        # self.status_log_action.setChecked(self.parent.log_manager.show_status_logs)
        # self.status_log_action.triggered.connect(self.toggle_status_logs)
        
        # View Menu (Tool -> View로 변경, 주석과 맞춤)
        view_menu = QMenu("View", self.parent)
        view_menu.addAction("Oscilloscope").triggered.connect(self.parent.show_oscilloscope)
        view_menu.addAction("Status Monitor (Ctrl+M)").triggered.connect(self.parent.show_status_monitor)
        
        # Developer Menu
        developer_menu = QMenu("Developer", self.parent)
        developer_action = QAction("Developer Settings", self.parent)
        #developer_action.setShortcut("Ctrl+Shift+D")
        developer_action.setStatusTip("Open Developer Tools")
        developer_action.triggered.connect(self.parent.show_developer_dialog)
        developer_menu.addAction(developer_action)
        
        # Help Menu
        help_menu = QMenu("Help", self.parent)
        help_menu.addAction("Web Manual").triggered.connect(self.parent.show_web_manual)
        help_menu.addAction("License").triggered.connect(self.parent.show_license)
        help_menu.addAction("About").triggered.connect(self.parent.show_about)
        
        menubar.addMenu(tuning_menu)
        menubar.addMenu(developer_menu)
        menubar.addMenu(settings_menu)                      
        menubar.addMenu(log_menu)
        menubar.addMenu(view_menu)
        menubar.addMenu(help_menu)
        
        self.parent.log_manager.write_log("[INFO] 메뉴바 초기화 완료", "cyan")
    
    def create_settings_panel(self, main_layout):        
        # 경계선 추가
        separator = QWidget()
        separator.setFixedHeight(3)
        separator.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent, 
                    stop:0.1 #00f0ff, 
                    stop:0.5 #666633, 
                    stop:0.9 #00f0ff, 
                    stop:1 transparent);
                margin: 8px 15px;
                border-radius: 1px;
            }
        """)
        main_layout.addWidget(separator)
        
        """설정 패널 생성"""
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)  # QHBoxLayout -> QVBoxLayout으로 변경
        
        # 상단 행: 버튼 및 입력 요소들
        upper_layout = QHBoxLayout()
        
        # 네트워크 연결
        upper_layout.addWidget(QLabel("네트워크:"))
        connect_btn = QPushButton("연결")
        connect_btn.clicked.connect(self.parent.network_manager.connect_server)
        upper_layout.addWidget(connect_btn)
        
        disconnect_btn = QPushButton("해제")
        disconnect_btn.clicked.connect(self.parent.network_manager.disconnect_server)
        upper_layout.addWidget(disconnect_btn)
        
        #고정 공간
        upper_layout.addSpacing(20)  # 20px 고정 공간
        upper_layout.addWidget(QLabel("/"))
        upper_layout.addSpacing(20)  # 20px 고정 공간
        
        # RF 제어
        self.rf_toggle_btn = QPushButton("RF On")
        self.rf_toggle_btn.clicked.connect(self.parent.network_manager.toggle_rf)
        upper_layout.addWidget(self.rf_toggle_btn)
        
        # 파워 설정
        upper_layout.addWidget(QLabel("Set Point Power:"))
        self.power_input = QLineEdit("0")
        self.power_input.setMinimumWidth(100)
        self.power_input.setMaximumWidth(100)
        self.power_input.setMinimumHeight(30)
        self.power_input.setMaximumHeight(30)
        upper_layout.addWidget(self.power_input)
        
        apply_btn = QPushButton("적용")
        apply_btn.clicked.connect(self._apply_power)
        upper_layout.addWidget(apply_btn)
        
        #고정 공간
        upper_layout.addSpacing(20)  # 20px 고정 공간
        upper_layout.addWidget(QLabel("/"))
        upper_layout.addSpacing(20)  # 20px 고정 공간
        
        # 상태 모니터 버튼 추가 (새로 추가)
        self.status_monitor_btn = QPushButton("상태 모니터")
        self.status_monitor_btn.setStyleSheet("""
            QPushButton {
                background-color: #4c566a;
                border: 1px solid #88c0d0;
                color: #eceff4;
                max-width: 120px;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #88c0d0;
                color: #2e3440;
            }
        """)
        self.status_monitor_btn.clicked.connect(self.parent.show_status_monitor)
        upper_layout.addWidget(self.status_monitor_btn)
        
        # 그래프 초기화 버튼 추가
        clear_plots_btn = QPushButton("그래프 초기화")
        clear_plots_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff8800;
                border: 1px solid #ffaa00;
                color: #ffffff;
                max-width: 120px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ffaa00;
                color: #ffffff;
            }
        """)
        clear_plots_btn.clicked.connect(self.clear_all_graphs)
        upper_layout.addWidget(clear_plots_btn)
        
        # 로그 클리어 버튼
        self.clear_log_btn = QPushButton("로그 클리어")
        self.clear_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                border: 1px solid #ff6666;
                color: #ffffff;
                max-width: 100px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6666;
                color: #ffffff;
            }
        """)
        self.clear_log_btn.clicked.connect(self.parent.log_manager.clear_log)
        upper_layout.addWidget(self.clear_log_btn)
        
        upper_layout.addStretch()
        settings_layout.addLayout(upper_layout)  # 상단 행 추가
        
        # 하단 행: 그래프 표시 체크박스
        lower_layout = QHBoxLayout()
        
        # 그래프 표시 체크박스
        lower_layout.addWidget(QLabel("그래프 표시:"))
        for i, label in enumerate(self.parent.plot_labels):
            checkbox = QCheckBox(label)
            checkbox.setChecked(self.parent.selected_plots[i])
            checkbox.stateChanged.connect(
                lambda state, idx=i: self.toggle_plot_visibility(idx, state)
            )
            self.plot_checkboxes.append(checkbox)
            lower_layout.addWidget(checkbox)
        
        lower_layout.addStretch()
        settings_layout.addLayout(lower_layout)  # 하단 행 추가
        
        settings_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(settings_widget)
        
    def clear_all_graphs(self):
        """모든 그래프 데이터 초기화"""
        # 플롯 데이터 클리어
        self.parent.plot_manager.clear_all_plots()
        
        # 메인 데이터 초기화
        for key in self.parent.plot_data:
            self.parent.plot_data[key].clear()
        
        # 샘플 카운터 리셋
        self.parent.sample_count = 0
        
        self.parent.log_manager.write_log("[INFO] 모든 그래프가 초기화되었습니다", "cyan")
    
    def create_middle_section(self, main_layout):
        """중간 섹션 생성 (상태 테이블 + 로그)"""
        middle_widget = QWidget()
        middle_layout = QHBoxLayout(middle_widget)
        middle_layout.setSpacing(5)
        middle_layout.setContentsMargins(0, 0, 0, 5)
        
        # 상태 정보 테이블
        self.create_status_table()
        
        # 로그 위젯 가져오기
        log_widget = self.parent.log_manager.get_log_widget()
        log_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # 상태 테이블과 로그 창의 높이를 제한
        self.status_table.setMaximumHeight(250)
        self.status_table.setMinimumHeight(200)
        log_widget.setMaximumHeight(250)
        log_widget.setMinimumHeight(200)
        
        # 5:5 비율로 배치
        middle_layout.addWidget(self.status_table, 7)
        middle_layout.addWidget(log_widget, 3)
        
        # middle_widget의 크기 정책 설정
        middle_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        middle_widget.setMaximumHeight(270)
        
        main_layout.addWidget(middle_widget)
    
    
    def create_status_table(self):
        """상태 테이블 생성 - 6행 6열로 수정 및 카테고리 헤더 색상 구분"""
        self.status_table = QTableWidget()
        # 18개 항목을 6행 6열로 배치: (항목명-값, 항목명-값, 항목명-값)
        self.status_table.setRowCount(6)
        self.status_table.setColumnCount(6)
        self.status_table.setHorizontalHeaderLabels(["Item", "Value", "Item", "Value", "Item", "Value"])

        # 헤더 숨기기
        self.status_table.horizontalHeader().hide()
        self.status_table.verticalHeader().hide()

        # 전체 항목 리스트 (18개)
        all_labels = [
            "Device Status", "RF On/Off", "Control Mode", "System State", "LED State", "Alarm State",
            "Set Power", "Firmware Version", "Power Readings", "Forward Power", "Reflect Power",
            "Delivery Power", "Frequency", "Gamma", "Real Gamma", "Image Gamma", "RF Phase", "Temperature"
        ]

        # 3개의 그룹으로 나누기 (각 6개 항목)
        group1_labels = all_labels[0:6]   # 첫 번째 열 쌍 (0~5)
        group2_labels = all_labels[6:12]  # 두 번째 열 쌍 (6~11)
        group3_labels = all_labels[12:18] # 세 번째 열 쌍 (12~17)

        # 첫 번째 열 쌍 (0, 1번 열)
        for i, label in enumerate(group1_labels):
            # 항목명
            item = QTableWidgetItem(label)
            item.setFlags(Qt.ItemIsEnabled)
            item.setBackground(QColor("#3e3e4e"))
            item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(i, 0, item)

            # 값 칸 초기화
            value_item = QTableWidgetItem("")
            value_item.setBackground(QColor("#2e2e3e"))
            value_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(i, 1, value_item)

        # 두 번째 열 쌍 (2, 3번 열)
        for i, label in enumerate(group2_labels):
            # 항목명
            item = QTableWidgetItem(label)
            item.setFlags(Qt.ItemIsEnabled)
            item.setBackground(QColor("#3e3e4e"))
            item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(i, 2, item)

            # 값 칸 초기화
            value_item = QTableWidgetItem("")
            value_item.setBackground(QColor("#2e2e3e"))
            value_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(i, 3, value_item)

        # 세 번째 열 쌍 (4, 5번 열)
        for i, label in enumerate(group3_labels):
            # 항목명
            item = QTableWidgetItem(label)
            item.setFlags(Qt.ItemIsEnabled)
            item.setBackground(QColor("#3e3e4e"))
            item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(i, 4, item)

            # 값 칸 초기화
            value_item = QTableWidgetItem("")
            value_item.setBackground(QColor("#2e2e3e"))
            value_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(i, 5, value_item)

        # 열 너비 설정
        self.status_table.setColumnWidth(0, 150)  # 첫 번째 항목명
        self.status_table.setColumnWidth(1, 145)  # 첫 번째 값
        self.status_table.setColumnWidth(2, 150)  # 두 번째 항목명
        self.status_table.setColumnWidth(3, 145)  # 두 번째 값
        self.status_table.setColumnWidth(4, 150)  # 세 번째 항목명
        self.status_table.setColumnWidth(5, 145)  # 세 번째 값

        # 모든 행의 높이를 10픽셀로 설정
        for row in range(self.status_table.rowCount()):
            self.status_table.setRowHeight(row, 10)

        self.status_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    #########
    def update_status_table(self, status):
        """상태 테이블 업데이트 - 6행 6열 구조에 맞게 수정 및 동적 색상 변화"""
        try:
            # 첫 번째 열 쌍 (0, 1번 열) 업데이트
            # Device Status (항상 "Active"로 가정, status에 따라 변경 가능)
            device_item = QTableWidgetItem("Active")
            device_item.setBackground(QColor("#2e2e3e"))
            device_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(0, 1, device_item)

            # RF On/Off
            rf_item = QTableWidgetItem("On" if status["rf_on_off"] else "Off")
            if status["rf_on_off"]:
                rf_item.setBackground(QColor("#00ff00"))  # RF On: 녹색
                rf_item.setForeground(QColor("#000000"))
            else:
                rf_item.setBackground(QColor("#666666"))  # RF Off: 회색
                rf_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(1, 1, rf_item)

            # Control Mode
            control_modes = {
                0: "User Port", 1: "Serial", 2: "Ethernet",
                3: "EtherCAT", 4: "Serial+User", 5: "Ethernet+User"
            }
            control_item = QTableWidgetItem(control_modes.get(status["control_mode"], "Unknown"))
            control_item.setBackground(QColor("#2e2e3e"))
            control_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(2, 1, control_item)

            # System State
            system_item = QTableWidgetItem(f"0x{status['system_state']:04x}")
            system_item.setBackground(QColor("#2e2e3e"))
            system_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(3, 1, system_item)

            # LED State
            led_item = QTableWidgetItem(f"0x{status['led_state']:04x}")
            led_item.setBackground(QColor("#2e2e3e"))
            led_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(4, 1, led_item)

            # Alarm State
            alarm_text = "None" if status["alarm_state"] == 0 else f"Alarm 0x{status['alarm_state']:04x}"
            alarm_item = QTableWidgetItem(alarm_text)
            if status["alarm_state"] != 0:
                alarm_item.setBackground(QColor("#ff4444"))
                alarm_item.setForeground(QColor("#ffffff"))
                alarm_item.setFont(QFont("Roboto Mono", 10, QFont.Bold))
                # Alarm State는 row=5, column=1에 위치
                self.set_item_color_animated(5, 1, "#ff0000", 2000)
            else:
                alarm_item.setBackground(QColor("#44ff44"))
                alarm_item.setForeground(QColor("#000000"))
            self.status_table.setItem(5, 1, alarm_item)

            # 두 번째 열 쌍 (2, 3번 열) 업데이트
            # Set Power
            set_power_item = QTableWidgetItem(f"{status['set_power']} W")
            set_power_item.setBackground(QColor("#2e2e3e"))
            set_power_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(0, 3, set_power_item)

            # Firmware Version
            fw_item = QTableWidgetItem(f"{status['firmware_version']:.2f}")
            fw_item.setBackground(QColor("#2e2e3e"))
            fw_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(1, 3, fw_item)

            # Power Readings (항상 "N/A"로 가정, status에 따라 변경 가능)
            power_readings_item = QTableWidgetItem("N/A")
            power_readings_item.setBackground(QColor("#2e2e3e"))
            power_readings_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(2, 3, power_readings_item)

            # Forward Power - 설정된 임계값 적용 (새로 추가된 부분)
            fwd_power = status['forward_power']
            if hasattr(self.parent, 'get_threshold_status'):
                fwd_status = self.parent.get_threshold_status(fwd_power, "forward_power")
                fwd_text = self.parent.format_value_with_precision(fwd_power, "forward_power") + " W"
            else:
                # 기본 임계값 사용
                if fwd_power > 699:
                    fwd_status = "error"
                elif fwd_power > 400:
                    fwd_status = "warning"
                elif fwd_power > 100:
                    fwd_status = "caution"
                else:
                    fwd_status = "normal"
                fwd_text = f"{fwd_power:.2f} W"
            
            fwd_power_item = QTableWidgetItem(fwd_text)
            if fwd_status == "error":
                fwd_power_item.setBackground(QColor("#ff4444"))
                fwd_power_item.setForeground(QColor("#ffffff"))
            elif fwd_status == "warning":
                fwd_power_item.setBackground(QColor("#ff8800"))
                fwd_power_item.setForeground(QColor("#ffffff"))
            elif fwd_status == "caution":
                fwd_power_item.setBackground(QColor("#ffff00"))
                fwd_power_item.setForeground(QColor("#000000"))
            else:
                fwd_power_item.setBackground(QColor("#2e2e3e"))
                fwd_power_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(3, 3, fwd_power_item)

            # Reflect Power - 설정된 임계값 적용 (새로 추가된 부분)
            ref_power = status['reflect_power']
            if hasattr(self.parent, 'get_threshold_status'):
                ref_status = self.parent.get_threshold_status(ref_power, "reflect_power")
                ref_text = self.parent.format_value_with_precision(ref_power, "reflect_power") + " W"
            else:
                # 기본 임계값 사용
                if ref_power > 50:
                    ref_status = "error"
                elif ref_power > 20:
                    ref_status = "warning"
                else:
                    ref_status = "normal"
                ref_text = f"{ref_power:.2f} W"
            
            ref_power_item = QTableWidgetItem(ref_text)
            if ref_status == "error":
                ref_power_item.setBackground(QColor("#ff4444"))
                ref_power_item.setForeground(QColor("#ffffff"))
            elif ref_status == "warning":
                ref_power_item.setBackground(QColor("#ff8800"))
                ref_power_item.setForeground(QColor("#ffffff"))
            else:
                ref_power_item.setBackground(QColor("#2e2e3e"))
                ref_power_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(4, 3, ref_power_item)

            # Delivery Power
            del_power = status['delivery_power']
            if hasattr(self.parent, 'format_value_with_precision'):
                del_text = self.parent.format_value_with_precision(del_power, "delivery_power") + " W"
            else:
                del_text = f"{del_power:.2f} W"
            
            del_power_item = QTableWidgetItem(del_text)
            del_power_item.setBackground(QColor("#2e2e3e"))
            del_power_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(5, 3, del_power_item)

            # 세 번째 열 쌍 (4, 5번 열) 업데이트
            # Frequency
            frequency = status['frequency']
            if hasattr(self.parent, 'format_value_with_precision'):
                freq_text = self.parent.format_value_with_precision(frequency, "frequency") + " MHz"
            else:
                freq_text = f"{frequency:.2f} MHz"
            
            freq_item = QTableWidgetItem(freq_text)
            freq_item.setBackground(QColor("#2e2e3e"))
            freq_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(0, 5, freq_item)

            # Gamma
            gamma_item = QTableWidgetItem(f"{status['gamma']:.3f}")
            gamma_item.setBackground(QColor("#2e2e3e"))
            gamma_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(1, 5, gamma_item)

            # Real Gamma
            real_gamma_item = QTableWidgetItem(f"{status['real_gamma']:.3f}")
            real_gamma_item.setBackground(QColor("#2e2e3e"))
            real_gamma_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(2, 5, real_gamma_item)

            # Image Gamma
            img_gamma_item = QTableWidgetItem(f"{status['image_gamma']:.3f}")
            img_gamma_item.setBackground(QColor("#2e2e3e"))
            img_gamma_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(3, 5, img_gamma_item)

            # RF Phase
            phase_item = QTableWidgetItem(f"{status['rf_phase']:.2f}°")
            phase_item.setBackground(QColor("#2e2e3e"))
            phase_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(4, 5, phase_item)

            # Temperature - 설정된 임계값 적용 (새로 추가된 부분)
            temp = status['temperature']
            if hasattr(self.parent, 'get_threshold_status'):
                temp_status = self.parent.get_threshold_status(temp, "temperature")
                temp_text = self.parent.format_value_with_precision(temp, "temperature") + "°C"
            else:
                # 기본 임계값 사용
                if temp > 70:
                    temp_status = "error"
                elif temp > 50:
                    temp_status = "warning"
                elif temp < 20:
                    temp_status = "special"  # 저온
                else:
                    temp_status = "normal"
                temp_text = f"{temp:.1f}°C"
            
            temp_item = QTableWidgetItem(temp_text)
            if temp_status == "error":
                temp_item.setBackground(QColor("#ff4444"))
                temp_item.setForeground(QColor("#ffffff"))
                temp_item.setFont(QFont("Roboto Mono", 10, QFont.Bold))
            elif temp_status == "warning":
                temp_item.setBackground(QColor("#ff8800"))
                temp_item.setForeground(QColor("#ffffff"))
            elif temp_status == "special":
                temp_item.setBackground(QColor("#4444ff"))
                temp_item.setForeground(QColor("#ffffff"))
            else:
                temp_item.setBackground(QColor("#2e2e3e"))
                temp_item.setForeground(QColor("#ffffff"))
            self.status_table.setItem(5, 5, temp_item)

        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 상태 테이블 업데이트 실패: {e}", "red")
    ##################
    def set_item_color_animated(self, row, column, color, duration=1000):
        """항목 색상을 애니메이션으로 변경 (깜박임 효과)"""
        try:
            # 현재 아이템 가져오기
            item = self.status_table.item(row, column)
            if not item:
                return  # 아이템이 없으면 종료

            # 원래 색상 저장
            original_color = item.background().color()
            
            # 새 색상 적용
            item.setBackground(QColor(color))
            
            # 일정 시간 후 원래 색상으로 복원
            QTimer.singleShot(duration, lambda: self._restore_item_color(row, column, original_color))
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 애니메이션 색상 변경 실패: {e}", "red")

    def _restore_item_color(self, row, column, color):
        """아이템 색상 복원 헬퍼 메서드"""
        try:
            item = self.status_table.item(row, column)
            if item:
                item.setBackground(color)
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 색상 복원 실패: {e}", "red")
    
    def update_gauges(self, status):
        """게이지 업데이트"""
        gauge_values = [
            status["forward_power"], status["reflect_power"], status["delivery_power"],
            status["frequency"], status["gamma"], status["real_gamma"],
            status["image_gamma"], status["rf_phase"], status["temperature"]
        ]
        
        for i, value in enumerate(gauge_values):
            if (self.parent.selected_plots[i] and 
                i < len(self.parent.dock_manager.gauges)):
                self.parent.dock_manager.gauges[i].set_value(value)
    
    # def update_rf_button_text(self, rf_enabled):
        # """RF 버튼 텍스트 업데이트"""
        # if self.rf_toggle_btn:
            # self.rf_toggle_btn.setText("RF Off" if rf_enabled else "RF On")
    
    # ✅ RF 버튼 깜빡임 메서드들
    def _toggle_rf_button_color(self):
        """RF 버튼 색상 깜빡임"""
        if not self.rf_toggle_btn:
            return
        
        self.rf_blink_state = not self.rf_blink_state
        
        if self.rf_blink_state:
            # 밝은 초록색
            self.rf_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #00ff00;
                    color: #000000;
                    font-weight: bold;
                    border: 2px solid #00cc00;
                }
            """)
        else:
            # 어두운 초록색
            self.rf_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #008800;
                    color: #000000;
                    font-weight: bold;
                    border: 2px solid #006600;
                }
            """)
    
    def start_rf_button_blink(self):
        """RF 버튼 깜빡임 시작 (1초 간격)"""
        if not self.rf_blink_timer.isActive():
            self.rf_blink_state = True  # 초기 상태는 밝음
            self.rf_blink_timer.start(1000)  # 1000ms = 1초
    
    def stop_rf_button_blink(self):
        """RF 버튼 깜빡임 중지"""
        if self.rf_blink_timer.isActive():
            self.rf_blink_timer.stop()
    
    #251103 수정
    def update_rf_button_text(self, rf_enabled):
        """RF 버튼 텍스트 및 색상 업데이트"""
        if self.rf_toggle_btn:
            if rf_enabled:
                self.rf_toggle_btn.setText("RF On")
                # ✅ RF On일 때 깜빡임 시작
                self.start_rf_button_blink()
            else:
                self.rf_toggle_btn.setText("RF Off")
                # ✅ RF Off일 때 깜빡임 중지 및 회색으로 고정
                self.stop_rf_button_blink()
                self.rf_toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #666666;
                        color: #ffffff;
                        font-weight: bold;
                        border: 2px solid #555555;
                    }
                    
                    QPushButton:hover {
                        background-color: #88c0d0;
                        color: #2e3440;
                    }
                """)
    
    def toggle_plot_visibility(self, index, state):
        """플롯 가시성 토글"""
        self.parent.selected_plots[index] = bool(state)
        if index < len(self.parent.dock_manager.dock_widgets):
            self.parent.dock_manager.dock_widgets[index].setVisible(self.parent.selected_plots[index])
        self.parent.log_manager.write_log(
            f"[INFO] {self.parent.plot_labels[index]} 그래프 "
            f"{'표시' if self.parent.selected_plots[index] else '숨김'}", "cyan"
        )
    
    def toggle_status_logs(self):
        """상태 조회 로그 표시 토글"""
        show_status = self.parent.log_manager.toggle_status_logs()
        self.status_log_action.setChecked(show_status)
    
    # def _apply_power(self):
        # """파워 설정 적용 - NetworkManager에 위임"""
        # try:
            # # 게이지 범위 가져오기
            # range_info = self.settings_manager.get_gauge_range('forward_power')
            # min_val, max_val = range_info['min'], range_info['max']
            
            # # 입력값 처리
            # power_text = self.power_input.text().strip()  # 입력값 가져오고 공백 제거
            # if not power_text:
                # raise ValueError("파워 값을 입력하세요.")
            
            # #power = int(power_text)  # 문자열을 정수로 변환
            # power = float(power_text)  # float로 변환 #251103
            # if min_val <= power <= max_val:
                # self.parent.network_manager.apply_power(power_text)  # NetworkManager에 전달
            # else:
                # raise ValueError(f"파워는 {min_val}에서 {max_val} 사이의 값이어야 합니다.")    
        # except ValueError as e:
            # self.parent.log_manager.write_log(f"[ERROR] 잘못된 파워 입력: {e}", "red")
            # from PyQt5.QtWidgets import QMessageBox
            # QMessageBox.warning(self.parent, "입력 오류", str(e))
    
    #251103 교체
    def _apply_power(self):
        """파워 설정 적용"""
        try:
            # ✅ 범위 정보 가져오기 (이 부분 추가)
            range_info = self.settings_manager.get_gauge_range('forward_power')
            min_val, max_val = range_info['min'], range_info['max']
            
            # 입력값을 즉시 저장
            power_text = self.power_input.text().strip()
            if not power_text:
                raise ValueError("파워 값을 입력하세요.")
            
            power = float(power_text)
            if min_val <= power <= max_val:  # ← 이제 정의됨!
                self.parent.network_manager.apply_power(power_text)
            else:
                raise ValueError(f"파워는 {min_val}에서 {max_val} 사이의 값이어야 합니다.")
                    
        except ValueError as e:
            self.parent.log_manager.write_log(f"[ERROR] 잘못된 파워 입력: {e}", "red")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self.parent, "입력 오류", str(e))