"""
Status Monitor Dialog Module - Document Compliant Version with Minimal Header
RF Generator Enhanced Status Monitor - 문서 기준 비트 필드 정의
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QGroupBox, QFrame, QSizePolicy, QWidget, QCheckBox, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette

# =============================================================================
# 사용자 설정 가능한 임계값 및 메시지 상수
# =============================================================================

class StatusThresholds:
    """상태 임계값 설정 클래스"""
    
    # Forward Power 임계값 (Watts)
    FORWARD_POWER_CAUTION = 400.0     # 주의 레벨: 400W 이상
    FORWARD_POWER_WARNING = 700.0     # 경고 레벨: 700W 이상 (현재 미사용)
    
    # Reflect Power 임계값 (Watts)
    REFLECT_POWER_WARNING = 20.0      # 경고 레벨: 20W 이상
    REFLECT_POWER_ERROR = 50.0        # 오류 레벨: 50W 이상
    
    # Temperature 임계값 (Celsius)
    TEMPERATURE_WARNING = 50.0        # 경고 레벨: 50°C 이상
    TEMPERATURE_ERROR = 70.0          # 오류 레벨: 70°C 이상
    TEMPERATURE_LOW = 20.0            # 저온 표시: 20°C 미만

class StatusMessages:
    """상태 메시지 설정 클래스"""
    
    # RF 상태 메시지
    RF_ON_MESSAGE = "RF ON"
    RF_OFF_MESSAGE = "RF OFF"
    
    # LED 상태 메시지 (문서 기준: 0=정상, 1=문제)
    LED_AC_ON = "AC ON"
    LED_AC_OFF = "AC OFF (Fail)"
    LED_INTERLOCK_OK = "Interlock OK"
    LED_INTERLOCK_FAIL = "Interlock Failure"
    LED_NO_ALARM = "No Alarm"
    LED_ALARM_ACTIVE = "Alarm"
    LED_NORMAL_TEMP = "Normal Temp"
    LED_OVER_TEMP = "Over Temp"
    LED_NORMAL_POWER = "Normal State"
    LED_LIMITED_POWER = "Limited Power"
    LED_RF_OFF = "RF OFF"
    LED_RF_ON = "RF ON"
    
    # 알람 상태 메시지
    ALARM_OK_MESSAGE = "OK"
    ALARM_FAIL_MESSAGE = "FAIL"
    ALARM_NORMAL_MESSAGE = "NORMAL"
    ALARM_ERROR_MESSAGE = "ERROR"
    
    # 연결 상태 메시지
    CONNECTION_ESTABLISHED = "통신 연결됨"
    CONNECTION_LOST = "통신 연결 없음: 장비와 연결을 확인하세요"
    
    # 단위 표시
    POWER_UNIT = "W"
    FREQUENCY_UNIT = "MHz"
    TEMPERATURE_UNIT = "°C"
    PHASE_UNIT = "°"
    VOLTAGE_UNIT = "V"

class StatusColors:
    """상태별 색상 정의 클래스 - DCC Interface와 통일"""

    # 기본 상태 색상 (DCC Interface와 동일한 Material Design 팔레트)
    NORMAL_BG = "#4CAF50"      # 정상: 녹색 (Material Green 500)
    NORMAL_TEXT = "#ffffff"

    CAUTION_BG = "#FFC107"     # 주의: 황색 (Material Amber 500)
    CAUTION_TEXT = "#000000"

    WARNING_BG = "#FF9800"     # 경고: 주황색 (Material Orange 500)
    WARNING_TEXT = "#000000"

    ERROR_BG = "#F44336"       # 오류: 빨간색 (Material Red 500)
    ERROR_TEXT = "#ffffff"

    INACTIVE_BG = "#9E9E9E"    # 비활성: 회색 (Material Grey 500)
    INACTIVE_TEXT = "#ffffff"

    SPECIAL_BG = "#2196F3"     # 특수: 파란색 (Material Blue 500)
    SPECIAL_TEXT = "#ffffff"

    DISCONNECTED_BG = "#555555"  # 연결끊김: 어두운 회색
    DISCONNECTED_TEXT = "#ffffff"

class DynamicStatusThresholds:
    """동적 상태 임계값 클래스"""
    
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
    
    @property
    def FORWARD_POWER_CAUTION(self):
        return self.settings_manager.get_threshold("forward_power", "caution")
    
    @property
    def FORWARD_POWER_WARNING(self):
        return self.settings_manager.get_threshold("forward_power", "warning")
    
    @property
    def FORWARD_POWER_ERROR(self):
        return self.settings_manager.get_threshold("forward_power", "error")
    
    @property
    def REFLECT_POWER_WARNING(self):
        return self.settings_manager.get_threshold("reflect_power", "warning")
    
    @property
    def REFLECT_POWER_ERROR(self):
        return self.settings_manager.get_threshold("reflect_power", "error")
    
    @property
    def TEMPERATURE_WARNING(self):
        return self.settings_manager.get_threshold("temperature", "warning")
    
    @property
    def TEMPERATURE_ERROR(self):
        return self.settings_manager.get_threshold("temperature", "error")
    
    @property
    def TEMPERATURE_LOW(self):
        return self.settings_manager.get_threshold("temperature", "low")

class DisplayFormats:
    """표시 형식 설정 클래스"""
    
    # 소수점 자리수
    POWER_DECIMALS = 1          # 전력: 소수점 1자리
    FREQUENCY_DECIMALS = 2      # 주파수: 소수점 2자리  
    TEMPERATURE_DECIMALS = 1    # 온도: 소수점 1자리
    GAMMA_DECIMALS = 3          # 감마: 소수점 3자리
    PHASE_DECIMALS = 2          # 위상: 소수점 2자리
    VOLTAGE_DECIMALS = 2        # 전압: 소수점 2자리

# =============================================================================
# 기존 색상 상수 (다이얼로그 UI용)
# =============================================================================

STATUS_COLORS = {
    "normal": {"background": StatusColors.NORMAL_BG, "text": StatusColors.NORMAL_TEXT, "border": "#388E3C"},
    "caution": {"background": StatusColors.CAUTION_BG, "text": StatusColors.CAUTION_TEXT, "border": "#FFA000"},
    "warning": {"background": StatusColors.WARNING_BG, "text": StatusColors.WARNING_TEXT, "border": "#F57C00"},
    "error": {"background": StatusColors.ERROR_BG, "text": StatusColors.ERROR_TEXT, "border": "#D32F2F"},
    "inactive": {"background": StatusColors.INACTIVE_BG, "text": StatusColors.INACTIVE_TEXT, "border": "#757575"},
    "special": {"background": StatusColors.SPECIAL_BG, "text": StatusColors.SPECIAL_TEXT, "border": "#1976D2"},
    "disconnected": {"background": StatusColors.DISCONNECTED_BG, "text": StatusColors.DISCONNECTED_TEXT, "border": "#333333"}
}

DIALOG_COLORS = {
    "background": "#2e3440",
    "text": "#ffffff", 
    "title": "#88c0d0",
    "group_background": "#3b4252",
    "group_border": "#4c566a",
    "group_title_bg": "#2e3440",
    "description": "#d8dee9",
    "disconnected_text": "#ff4444"
}

BUTTON_COLORS = {
    "refresh": {"normal": "#5e81ac", "hover": "#81a1c1"},
    "alarm_clear": {"normal": "#a3be8c", "hover": "#8fbcbb"}, #알람 클리어
    "close": {"normal": "#bf616a", "hover": "#d08770"}
}

# =============================================================================
# 미니멀 헤더 위젯 (StatusMonitorDialog보다 먼저 정의) - 수정된 버전
# =============================================================================

class MinimalHeaderWidget(QWidget):
    """미니멀 스타일 상단 헤더 위젯 - 설정 연동 및 프로그레스바 완전 수정"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_monitor = parent
        self.value_displays = {}
        self.progress_bars = {}
        
        # 설정 매니저 참조
        self.settings_manager = None
        if hasattr(parent, 'settings_manager'):
            self.settings_manager = parent.settings_manager
        elif hasattr(parent, 'parent_window') and hasattr(parent.parent_window, 'settings_manager'):
            self.settings_manager = parent.parent_window.settings_manager
        
        self.init_ui()
        
    def get_metric_range(self, metric_id):
        """설정에서 메트릭 범위 가져오기"""
        if self.settings_manager:
            if metric_id == 'delivery_power':
                # delivery_power는 forward_power와 동일한 범위 사용
                range_info = self.settings_manager.get_gauge_range('forward_power')
            else:
                range_info = self.settings_manager.get_gauge_range(metric_id)
            
            return range_info["min"], range_info["max"]
        else:
            # 기본값 (설정 파일이 없을 경우)
            defaults = {
                'forward_power': (0, 3000),
                'reflect_power': (0, 300),
                'delivery_power': (0, 3000),  # forward_power와 동일
                'temperature': (20, 80)
            }
            return defaults.get(metric_id, (0, 100))
        
    def init_ui(self):
        # 메인 헤더 컨테이너
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 헤더 프레임 - 여백 최소화
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #3b4252;
                border-radius: 0px;
                border-left: 3px solid #88c0d0;
            }}
        """)
        header_frame.setFixedHeight(85)  # 높이 줄임
        
        # 헤더 내부 레이아웃 - 여백 줄임
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 10, 10, 10)  # 좌우 여백 대폭 줄임
        header_layout.setSpacing(5)
        
        # 4개 주요 수치 생성 - 설정 기반 범위
        metrics = [
            ('forward_power', 'FORWARD POWER(W)', 'W'),
            ('reflect_power', 'REFLECT POWER(W)', 'W'), 
            ('delivery_power', 'DELIVERY POWER(W)', 'W'),
            ('temperature', 'TEMPERATURE(°C)', '°C')
        ]
        
        for i, (metric_id, label, unit) in enumerate(metrics):
            min_val, max_val = self.get_metric_range(metric_id)
            metric_widget = self.create_metric_widget(metric_id, label, unit, min_val, max_val)
            header_layout.addWidget(metric_widget)
            
        main_layout.addWidget(header_frame)
        
    def create_metric_widget(self, metric_id, label, unit, min_val, max_val):
        """개별 수치 표시 위젯 생성 - 컴팩트 버전"""
        container = QWidget()
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)  # 여백 최소화
        layout.setSpacing(0)  # 간격 최소화
        
        # 라벨 - 작고 컴팩트하게
        label_widget = QLabel(label)
        label_widget.setAlignment(Qt.AlignLeft)
        label_widget.setStyleSheet("""
            QLabel {
                color: #81a1c1;
                font-size: 15px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
        """)
        
        # 값 표시 - 크기 조정
        value_widget = QLabel("0.00")  # 기본값 표시
        #value_widget.setAlignment(Qt.AlignLeft)
        value_widget.setAlignment(Qt.AlignCenter)
        value_widget.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 36px;
                font-weight: bold;
                font-family: 'Arial', monospace;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        # 프로그레스 바 컨테이너
        progress_container = QWidget()
        progress_container.setFixedHeight(4)
        progress_container.setStyleSheet("background-color: #434c5e; border-radius: 2px;")
        
        # 프로그레스 바 채움 부분
        progress_fill = QWidget(progress_container)
        progress_fill.setFixedHeight(4)
        progress_fill.setFixedWidth(2)  # 최소 너비
        progress_fill.move(0, 0)
        progress_fill.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #44ff44, stop:1 #66ff88);
                border-radius: 2px;
            }
        """)
        
        # 위젯들 조립
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        layout.addWidget(progress_container)
        
        # 참조 저장
        self.value_displays[metric_id] = value_widget
        self.progress_bars[metric_id] = {
            'fill': progress_fill,
            'container': progress_container,
            'min': min_val,
            'max': max_val,
            'unit': unit
        }
        
        return container
        
    def update_metric(self, metric_id, value, status_type="normal"):
        """개별 수치 업데이트 - 설정 기반 범위 사용"""
        if metric_id not in self.value_displays:
            return
            
        value_widget = self.value_displays[metric_id]
        progress_info = self.progress_bars[metric_id]
        
        # 값 표시 업데이트 - 명확한 숫자 포맷
        if isinstance(value, (int, float)) and value >= 0:
            if progress_info['unit'] == '°C':
                formatted_value = f"{value:.1f}"
            else:
                formatted_value = f"{value:.2f}"
            value_widget.setText(formatted_value)
        else:
            value_widget.setText("0.00")
            
        # 프로그레스 바 업데이트 - 설정 기반 범위로 계산
        container_width = 255  # 기본 컨테이너 너비
        if isinstance(value, (int, float)) and value > 0:
            # 설정에서 가져온 실제 범위 사용
            progress_percentage = min(100, max(0, (value - progress_info['min']) / 
                                    (progress_info['max'] - progress_info['min']) * 100))
            progress_width = max(2, int(container_width * progress_percentage / 100))
            progress_info['fill'].setFixedWidth(progress_width)
        else:
            progress_info['fill'].setFixedWidth(2)
            
        # 상태 색상 적용
        color_style = self.get_status_color_style(status_type)
        progress_info['fill'].setStyleSheet(color_style)
        
    def get_status_color_style(self, status_type):
        """상태별 색상 스타일 - DCC Interface와 통일"""
        base_style = "QWidget { border-radius: 2px; "

        if status_type == "error":
            return base_style + "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F44336, stop:1 #E57373); }"
        elif status_type == "warning":
            return base_style + "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF9800, stop:1 #FFB74D); }"
        elif status_type == "caution":
            return base_style + "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FFC107, stop:1 #FFD54F); }"
        elif status_type == "disconnected":
            return base_style + "background-color: #666666; }"
        else:  # normal
            return base_style + "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4CAF50, stop:1 #81C784); }"

# =============================================================================
# 상태 표시 위젯
# =============================================================================

class StatusIndicator(QLabel):
    """상태 표시 위젯"""
    
    def __init__(self, text, status="disconnected", parent=None):
        super().__init__(text, parent)
        self.status_type = status
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(35)
        self.setFont(QFont("Arial", 10, QFont.Bold))
        self.update_style()
        
    def set_status(self, status, text=None):
        self.status_type = status
        if text:
            self.setText(text)
        self.update_style()
        
    def update_style(self):
        color_config = STATUS_COLORS.get(self.status_type, STATUS_COLORS["disconnected"])
        style = f"""
            QLabel {{
                background-color: {color_config["background"]};
                color: {color_config["text"]};
                border: 1px solid {color_config["border"]};
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
                text-align: center;
            }}
        """
        self.setStyleSheet(style)

# =============================================================================
# 메인 상태 모니터 다이얼로그 - 모든 문제점 해결된 버전
# =============================================================================

class StatusMonitorDialog(QDialog):
    """RF Generator Enhanced Status Monitor 다이얼로그 - 완전 수정 버전"""
    
    status_update_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.status_indicators = {}
        self.is_connected = False

        # 자동 갱신 설정
        self.auto_refresh_enabled = True  # 기본값: 활성화
        self.refresh_interval = 500  # 기본값: 500ms (원래대로 복원)
        self.is_refreshing = False  # 갱신 중 플래그

        # 설정 매니저 참조 추가
        self.settings_manager = None
        if hasattr(parent, 'settings_manager'):
            self.settings_manager = parent.settings_manager
        
        # 동적 임계값 사용 (기존과 동일)
        if hasattr(parent, 'settings_manager'):
            self.thresholds = DynamicStatusThresholds(parent.settings_manager)
        else:
            self.thresholds = StatusThresholds
            
        # LED 비트 정의 (문서 3.4절 기준)
        self.led_bit_definitions = {
            0: ("AC Power", StatusMessages.LED_AC_OFF, StatusMessages.LED_AC_ON),
            1: ("Interlock", StatusMessages.LED_INTERLOCK_OK, StatusMessages.LED_INTERLOCK_FAIL),
            2: ("Alarm", StatusMessages.LED_NO_ALARM, StatusMessages.LED_ALARM_ACTIVE),
            3: ("Over Temp", StatusMessages.LED_NORMAL_TEMP, StatusMessages.LED_OVER_TEMP),
            4: ("Power Limit", StatusMessages.LED_NORMAL_POWER, StatusMessages.LED_LIMITED_POWER),
            5: ("RF Output", StatusMessages.LED_RF_OFF, StatusMessages.LED_RF_ON)
        }
        
        # 알람 비트 정의 (문서 3.5절 기준)
        self.alarm_bit_definitions = {
            "aux_power": (0, 3, "AUX Power Vol"),
            "ac_phase": (3, 3, "AC Phase"),
            6: "PFC Fail",
            7: "Max Power Limit", 
            8: "Gate Driver Amp",
            9: "Fan Fail",
            10: "Over Temp",
            "interlock": (11, 4, "Interlock Status"),
            15: "Under FWD Power"
        }
        
        self.init_ui()
        self.setup_update_timer()
        
    def init_ui(self):
        """UI 초기화 - 개선된 미니멀 헤더 포함"""
        self.setWindowTitle("RF Generator Status Monitor")
        self.setMinimumSize(1000, 800)
        self.resize(1100, 850)
        
        # 스타일 설정
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DIALOG_COLORS["background"]};
                color: {DIALOG_COLORS["text"]};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {DIALOG_COLORS["group_border"]};
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: {DIALOG_COLORS["group_background"]};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: {DIALOG_COLORS["title"]};
                font-size: 14px;
                background-color: {DIALOG_COLORS["group_title_bg"]};
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)  # 간격 줄임
        
        # 타이틀
        title_label = QLabel("Status Monitor")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet(f"color: {DIALOG_COLORS['title']}; margin: 5px; font-size: 18px;")
        main_layout.addWidget(title_label)
        
        # 연결 상태 라벨
        self.connection_label = QLabel(StatusMessages.CONNECTION_LOST)
        self.connection_label.setAlignment(Qt.AlignCenter)
        self.connection_label.setStyleSheet(f"color: {DIALOG_COLORS['disconnected_text']}; font-size: 14px; font-weight: bold;")
        main_layout.addWidget(self.connection_label)

        # 자동 갱신 컨트롤 (옵션 1: 콤팩트 인라인 배치)
        refresh_control_layout = QHBoxLayout()
        refresh_control_layout.addStretch()

        self.auto_refresh_checkbox = QCheckBox("Auto Refresh")
        self.auto_refresh_checkbox.setChecked(self.auto_refresh_enabled)
        self.auto_refresh_checkbox.setStyleSheet("color: #d8dee9; font-size: 12px;")
        self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
        refresh_control_layout.addWidget(self.auto_refresh_checkbox)

        self.refresh_interval_combo = QComboBox()
        self.refresh_interval_combo.addItems([
            "100ms", "200ms", "500ms", "1000ms", "2000ms", "3000ms", "5000ms"
        ])
        self.refresh_interval_combo.setCurrentText("500ms")
        self.refresh_interval_combo.setStyleSheet("""
            QComboBox {
                background-color: #3b4252;
                color: #d8dee9;
                border: 1px solid #4c566a;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 80px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #d8dee9;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #3b4252;
                color: #d8dee9;
                selection-background-color: #5e81ac;
            }
        """)
        self.refresh_interval_combo.currentTextChanged.connect(self.change_refresh_interval)
        refresh_control_layout.addWidget(self.refresh_interval_combo)

        self.manual_refresh_btn = QPushButton("⟳ Refresh Now")
        self.manual_refresh_btn.clicked.connect(self.refresh_status)
        self.manual_refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_COLORS["refresh"]["normal"]};
                border: none;
                border-radius: 5px;
                padding: 6px 12px;
                color: white;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_COLORS["refresh"]["hover"]};
            }}
        """)
        refresh_control_layout.addWidget(self.manual_refresh_btn)

        # LED 표시등 (갱신 중 깜빡임)
        self.status_led = QLabel("●")
        self.status_led.setStyleSheet("color: #4CAF50; font-size: 16px;")
        refresh_control_layout.addWidget(self.status_led)

        main_layout.addLayout(refresh_control_layout)

        # ★ 개선된 미니멀 헤더 추가
        self.minimal_header = MinimalHeaderWidget(self)
        main_layout.addWidget(self.minimal_header)
    
        
        # 기존 컨텐츠 레이아웃
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        system_group = self.create_system_parameters_section()
        content_layout.addWidget(system_group)
        led_group = self.create_led_status_section()
        content_layout.addWidget(led_group)
        alarm_group = self.create_alarm_status_section()
        content_layout.addWidget(alarm_group)
        
        main_layout.addLayout(content_layout)
        
        # 컬러 가이드
        guide_frame = self.create_color_guide()
        main_layout.addWidget(guide_frame)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 알람 클리어 버튼
        alarm_clear_btn = QPushButton("알람 클리어")
        alarm_clear_btn.clicked.connect(self.clear_alarm)
        alarm_clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_COLORS["alarm_clear"]["normal"]};
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_COLORS["alarm_clear"]["hover"]};
            }}
        """)
        button_layout.addWidget(alarm_clear_btn)

        # DCC Interface 버튼
        dcc_interface_btn = QPushButton("DCC Interface")
        dcc_interface_btn.clicked.connect(self.show_dcc_interface)
        dcc_interface_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #8fbcbb;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #88c0d0;
            }}
        """)
        button_layout.addWidget(dcc_interface_btn)

        # 닫기 버튼
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_COLORS["close"]["normal"]};
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_COLORS["close"]["hover"]};
            }}
        """)
        button_layout.addWidget(close_btn)

        main_layout.addLayout(button_layout)
        
    def create_system_parameters_section(self):
        """System Parameters 섹션 - 4가지 값 포함"""
        group = QGroupBox("System Parameters")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # 모든 파라미터 포함 (원래대로 복원)
        params = [
            ("RF Status", "N/A", "disconnected"),
            ("Control Mode", "N/A", "disconnected"),
            ("Set Power", "N/A", "disconnected"),
            ("Forward Power", "N/A", "disconnected"),  # 다시 추가
            ("Reflect Power", "N/A", "disconnected"),  # 다시 추가
            ("Delivery Power", "N/A", "disconnected"),  # 다시 추가
            ("Frequency", "N/A", "disconnected"),
            ("Temperature", "N/A", "disconnected")     # 다시 추가
        ]
        
        for param_name, value, status in params:
            param_layout = QVBoxLayout()
            param_layout.setSpacing(3)
            name_label = QLabel(param_name)
            name_label.setStyleSheet(f"color: {DIALOG_COLORS['description']}; font-size: 11px; font-weight: normal;")
            param_layout.addWidget(name_label)
            indicator = StatusIndicator(value, status)
            self.status_indicators[f"system_{param_name.lower().replace(' ', '_')}"] = indicator
            param_layout.addWidget(indicator)
            layout.addLayout(param_layout)
            
        layout.addStretch()
        return group

        
    def create_led_status_section(self):
        """LED 상태 모니터 섹션"""
        group = QGroupBox("LED Status Monitor")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        
        for bit_pos, (led_name, msg_0, msg_1) in self.led_bit_definitions.items():
            indicator = StatusIndicator(f"{led_name}: N/A", "disconnected")
            key = f"led_{led_name.lower().replace(' ', '_')}"
            self.status_indicators[key] = indicator
            layout.addWidget(indicator)
            
        layout.addStretch()
        return group
        
    def create_alarm_status_section(self):
        """알람 상태 모니터 섹션"""
        group = QGroupBox("Alarm Status Monitor")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # 단일 비트 알람들
        single_bit_alarms = [6, 7, 8, 9, 10, 15]
        for bit_pos in single_bit_alarms:
            if bit_pos in self.alarm_bit_definitions:
                alarm_name = self.alarm_bit_definitions[bit_pos]
                indicator = StatusIndicator(f"{alarm_name}: N/A", "disconnected")
                key = f"alarm_{alarm_name.lower().replace(' ', '_')}"
                self.status_indicators[key] = indicator
                layout.addWidget(indicator)
        
        # 다중 비트 필드들
        multi_bit_fields = ["aux_power", "ac_phase", "interlock"]
        for field_name in multi_bit_fields:
            if field_name in self.alarm_bit_definitions:
                _, _, display_name = self.alarm_bit_definitions[field_name]
                indicator = StatusIndicator(f"{display_name}: N/A", "disconnected")
                key = f"alarm_{field_name}"
                self.status_indicators[key] = indicator
                layout.addWidget(indicator)
                
        layout.addStretch()
        return group
        
    def create_color_guide(self):
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background-color: {DIALOG_COLORS['group_background']}; border-radius: 8px; }}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)
        
        title_label = QLabel("시각적 상태 표시 가이드")
        title_label.setStyleSheet(f"color: {DIALOG_COLORS['title']}; font-weight: bold; font-size: 12px;")
        layout.addWidget(title_label)
        
        guide_layout = QHBoxLayout()
        guide_layout.setSpacing(20)
        
        color_guides = [
            ("정상 상태 (Normal/OK)", "normal"),
            ("주의 상태 (Caution/Limited)", "caution"),
            ("경고 상태 (Warning)", "warning"),
            ("오류/알람 (Error/Alarm)", "error"),
            ("비활성 (Inactive/Off)", "inactive"),
            ("특수 상태 (Special)", "special"),
            ("통신 연결 없음 (Disconnected)", "disconnected")
        ]
        
        for text, status in color_guides:
            guide_item = QVBoxLayout()
            guide_item.setSpacing(3)
            sample = StatusIndicator("●", status)
            sample.setMinimumHeight(20)
            sample.setMaximumHeight(20)
            sample.setMinimumWidth(30)
            sample.setMaximumWidth(30)
            guide_item.addWidget(sample, 0, Qt.AlignCenter)
            desc_label = QLabel(text)
            desc_label.setStyleSheet(f"color: {DIALOG_COLORS['description']}; font-size: 11px; text-align: center;")
            desc_label.setAlignment(Qt.AlignCenter)
            desc_label.setWordWrap(True)
            guide_item.addWidget(desc_label)
            guide_layout.addLayout(guide_item)
            
        layout.addLayout(guide_layout)
        return frame
        
    def setup_update_timer(self):
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_status_from_parent)

        if self.auto_refresh_enabled:
            self.update_timer.start(self.refresh_interval)

    def toggle_auto_refresh(self, state):
        """자동 갱신 on/off 토글"""
        self.auto_refresh_enabled = (state == Qt.Checked)
        if self.auto_refresh_enabled:
            self.update_timer.start(self.refresh_interval)
            self.status_led.setStyleSheet("color: #4CAF50; font-size: 16px;")
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log(
                    f"[INFO] 자동 갱신 활성화: {self.refresh_interval}ms",
                    "cyan"
                )
        else:
            self.update_timer.stop()
            self.status_led.setStyleSheet("color: #757575; font-size: 16px;")
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log(
                    "[INFO] 자동 갱신 비활성화",
                    "yellow"
                )

    def change_refresh_interval(self, text):
        """갱신 간격 변경"""
        # "500ms" -> 500 변환
        interval = int(text.replace("ms", ""))
        self.refresh_interval = interval

        # 타이머가 실행 중이면 재시작
        if self.auto_refresh_enabled and self.update_timer.isActive():
            self.update_timer.stop()
            self.update_timer.start(self.refresh_interval)

            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log(
                    f"[INFO] 갱신 간격 변경: {self.refresh_interval}ms",
                    "cyan"
                )
        
    def check_connection(self):
        try:
            # 1. 네트워크 매니저의 연결 상태 확인
            if (hasattr(self.parent_window, 'network_manager') and 
                hasattr(self.parent_window.network_manager, 'client_thread') and
                self.parent_window.network_manager.client_thread and
                self.parent_window.network_manager.client_thread.status_socket and
                self.parent_window.network_manager.client_thread.status_socket.fileno() != -1):
                
                # 2. 최근 데이터 수신 시간 확인 (예: 5초 이내)
                if (hasattr(self.parent_window, 'data_manager') and 
                    self.parent_window.data_manager.data_log):
                    
                    import datetime
                    now = datetime.datetime.now()
                    latest_entry = self.parent_window.data_manager.data_log[-1]
                    latest_time = datetime.datetime.strptime(latest_entry["Time"], "%Y-%m-%d %H:%M:%S")
                    
                    if (now - latest_time).total_seconds() < 5.0:
                        self.is_connected = True
                        return True
            
            self.is_connected = False
            return False
        except Exception:
            self.is_connected = False
            return False
            
    def update_status_from_parent(self):
        # LED 깜빡임 (주황색)
        self.status_led.setStyleSheet("color: #FF9800; font-size: 16px;")

        if self.check_connection():
            self.connection_label.setText(StatusMessages.CONNECTION_ESTABLISHED)
            self.connection_label.setStyleSheet(f"color: {DIALOG_COLORS['title']}; font-size: 14px; font-weight: bold;")
            try:
                latest_data = self.parent_window.data_manager.data_log[-1]
                self.update_status_display(latest_data)
            except Exception as e:
                if hasattr(self.parent_window, 'log_manager'):
                    self.parent_window.log_manager.write_log(f"[ERROR] 상태 모니터 업데이트 실패: {e}", "red")
        else:
            self.connection_label.setText(StatusMessages.CONNECTION_LOST)
            self.connection_label.setStyleSheet(f"color: {DIALOG_COLORS['disconnected_text']}; font-size: 14px; font-weight: bold;")
            for key, indicator in self.status_indicators.items():
                indicator.set_status("disconnected", f"{key.split('_', 1)[1].replace('_', ' ').title()}: N/A")
            # 미니멀 헤더도 연결 끊김 상태로 업데이트
            if hasattr(self, 'minimal_header'):
                for metric_id in ['forward_power', 'reflect_power', 'delivery_power', 'temperature']:
                    self.minimal_header.update_metric(metric_id, 0, "disconnected")

        # LED 복구 (녹색)
        if self.auto_refresh_enabled:
            self.status_led.setStyleSheet("color: #4CAF50; font-size: 16px;")
    
    def parse_led_state(self, led_state_value):
        """LED 상태 비트별 파싱 - 문서 기준"""
        led_states = {}
        for bit_pos, (led_name, msg_0, msg_1) in self.led_bit_definitions.items():
            bit_value = bool(led_state_value & (1 << bit_pos))
            led_states[led_name] = {
                'bit_value': bit_value,
                'message': msg_1 if bit_value else msg_0,
                'status_type': self.determine_led_status_type(led_name, bit_value)
            }
        return led_states
    
    def determine_led_status_type(self, led_name, bit_value):
        """LED 상태 타입 결정 - 문서 기준 로직"""
        # AC Power: 1=정상(AC ON), 0=문제(AC OFF/Fail)
        if led_name == "AC Power":
            return "normal" if bit_value else "error"
        # Interlock: 0=정상(OK), 1=문제(Failure)  
        elif led_name == "Interlock":
            return "error" if bit_value else "normal"
        # Alarm: 0=정상(No Alarm), 1=문제(Alarm)
        elif led_name == "Alarm":
            return "error" if bit_value else "normal"
        # Over Temp: 0=정상(Normal), 1=문제(Over Temp)
        elif led_name == "Over Temp":
            return "warning" if bit_value else "normal"
        # Power Limit: 0=정상(Normal), 1=주의(Limited)
        elif led_name == "Power Limit":
            return "caution" if bit_value else "normal"
        # RF Output: 1=정상(RF ON), 0=비활성(RF OFF)
        elif led_name == "RF Output":
            return "normal" if bit_value else "inactive"
        else:
            return "normal" if bit_value else "inactive"
    
    def parse_alarm_state(self, alarm_state_value):
        """알람 상태 비트별 파싱 - 문서 기준 16비트"""
        alarm_states = {}
        
        # 단일 비트 알람들
        single_bit_alarms = [6, 7, 8, 9, 10, 15]
        for bit_pos in single_bit_alarms:
            if bit_pos in self.alarm_bit_definitions:
                alarm_name = self.alarm_bit_definitions[bit_pos]
                is_active = bool(alarm_state_value & (1 << bit_pos))
                alarm_states[alarm_name] = {
                    'active': is_active,
                    'message': f"{alarm_name}: {StatusMessages.ALARM_ERROR_MESSAGE if is_active else StatusMessages.ALARM_OK_MESSAGE}",
                    'status_type': "error" if is_active else "normal"
                }
        
        # 다중 비트 필드들
        # AUX Power Vol (비트 0-2)
        aux_power_value = (alarm_state_value >> 0) & 0x07  # 3비트 마스크
        alarm_states["AUX Power Vol"] = {
            'value': aux_power_value,
            'message': f"AUX Power Vol: {aux_power_value}",
            'status_type': "warning" if aux_power_value != 0 else "normal"
        }
        
        # AC Phase (비트 3-5)
        ac_phase_value = (alarm_state_value >> 3) & 0x07  # 3비트 마스크
        alarm_states["AC Phase"] = {
            'value': ac_phase_value,
            'message': f"AC Phase: {ac_phase_value}",
            'status_type': "warning" if ac_phase_value != 0 else "normal"
        }
        
        # Interlock Status (비트 11-14)
        interlock_value = (alarm_state_value >> 11) & 0x0F  # 4비트 마스크
        alarm_states["Interlock Status"] = {
            'value': interlock_value,
            'message': f"Interlock: 0x{interlock_value:X}",
            'status_type': "error" if interlock_value != 0 else "normal"
        }
        
        return alarm_states
    
    def determine_power_status(self, power_value, power_type="forward"):
        """전력 상태 결정 - 동적 임계값 사용"""
        if power_type == "forward":
            if hasattr(self.thresholds, 'FORWARD_POWER_ERROR') and power_value > self.thresholds.FORWARD_POWER_ERROR:
                return "error"
            elif hasattr(self.thresholds, 'FORWARD_POWER_WARNING') and power_value > self.thresholds.FORWARD_POWER_WARNING:
                return "warning"
            elif hasattr(self.thresholds, 'FORWARD_POWER_CAUTION') and power_value > self.thresholds.FORWARD_POWER_CAUTION:
                return "caution"
            else:
                return "normal"
        elif power_type == "reflect":
            if hasattr(self.thresholds, 'REFLECT_POWER_ERROR') and power_value > self.thresholds.REFLECT_POWER_ERROR:
                return "error"
            elif hasattr(self.thresholds, 'REFLECT_POWER_WARNING') and power_value > self.thresholds.REFLECT_POWER_WARNING:
                return "warning"
            else:
                return "normal"
        else:
            return "normal"
    
    def determine_temperature_status(self, temperature):
        """온도 상태 결정 - 동적 임계값 사용"""
        if hasattr(self.thresholds, 'TEMPERATURE_ERROR') and temperature > self.thresholds.TEMPERATURE_ERROR:
            return "error"
        elif hasattr(self.thresholds, 'TEMPERATURE_WARNING') and temperature > self.thresholds.TEMPERATURE_WARNING:
            return "warning"
        elif hasattr(self.thresholds, 'TEMPERATURE_LOW') and temperature < self.thresholds.TEMPERATURE_LOW:
            return "special"  # 저온 표시
        else:
            return "normal"
    
    def format_power_display(self, power_value):
        """전력 표시 형식 - 동적 정밀도 사용"""
        if hasattr(self.parent_window, 'settings_manager'):
            precision = self.parent_window.settings_manager.get_status_monitor_setting("power_precision")
            return f"{power_value:.{precision}f} W"
        else:
            return f"{power_value:.2f} W"
    
    def format_frequency_display(self, frequency_value):
        """주파수 표시 형식 - 동적 정밀도 사용"""
        if hasattr(self.parent_window, 'settings_manager'):
            precision = self.parent_window.settings_manager.get_status_monitor_setting("frequency_precision")
            return f"{frequency_value:.{precision}f} MHz"
        else:
            return f"{frequency_value:.2f} MHz"
    
    def format_temperature_display(self, temperature_value):
        """온도 표시 형식 - 동적 정밀도 사용"""
        if hasattr(self.parent_window, 'settings_manager'):
            precision = self.parent_window.settings_manager.get_status_monitor_setting("temperature_precision")
            return f"{temperature_value:.{precision}f}°C"
        else:
            return f"{temperature_value:.1f}°C"
    
    def update_status_display(self, status_data):
        """상태 표시 업데이트 - 4가지 값 모두 포함"""
        try:
            # 미니멀 헤더 업데이트
            self.update_minimal_header(status_data)
            
            # System Parameters 업데이트 - 모든 항목 포함
            rf_status = StatusMessages.RF_ON_MESSAGE if status_data.get("RF Status") == "On" else StatusMessages.RF_OFF_MESSAGE
            rf_status_type = "normal" if status_data.get("RF Status") == "On" else "inactive"
            if "system_rf_status" in self.status_indicators:
                self.status_indicators["system_rf_status"].set_status(rf_status_type, rf_status)
            
            if "system_control_mode" in self.status_indicators:
                control_mode = status_data.get("Control Mode", "Unknown")
                self.status_indicators["system_control_mode"].set_status("normal", control_mode)
            
            if "system_set_power" in self.status_indicators:
                set_power = status_data.get('Set Power', 0)
                set_power_text = f"{set_power} {StatusMessages.POWER_UNIT}"
                self.status_indicators["system_set_power"].set_status("normal", set_power_text)
                
            # 4가지 값 다시 추가
            if "system_forward_power" in self.status_indicators:
                fwd_power = status_data.get("Forward Power", 0)
                fwd_status = self.determine_power_status(fwd_power, "forward")
                fwd_power_text = self.format_power_display(fwd_power)
                self.status_indicators["system_forward_power"].set_status(fwd_status, fwd_power_text)
                
            if "system_reflect_power" in self.status_indicators:
                ref_power = status_data.get("Reflect Power", 0)
                ref_status = self.determine_power_status(ref_power, "reflect")
                ref_power_text = self.format_power_display(ref_power)
                self.status_indicators["system_reflect_power"].set_status(ref_status, ref_power_text)
                
            if "system_delivery_power" in self.status_indicators:
                del_power = status_data.get("Delivery Power", 0)
                del_power_text = self.format_power_display(del_power)
                self.status_indicators["system_delivery_power"].set_status("normal", del_power_text)
            
            if "system_frequency" in self.status_indicators:
                frequency = status_data.get("Frequency", 0)
                frequency_text = self.format_frequency_display(frequency)
                self.status_indicators["system_frequency"].set_status("normal", frequency_text)
                
            if "system_temperature" in self.status_indicators:
                temperature = status_data.get("Temperature", 0)
                temp_status = self.determine_temperature_status(temperature)
                temp_text = self.format_temperature_display(temperature)
                self.status_indicators["system_temperature"].set_status(temp_status, temp_text)
            
            # LED Status Monitor 업데이트 - 문서 기준 비트 파싱
            led_state_raw = status_data.get("LED State", "0x0000")
            try:
                if isinstance(led_state_raw, str) and led_state_raw.startswith("0x"):
                    led_state_value = int(led_state_raw, 16)
                else:
                    led_state_value = int(led_state_raw)
                
                led_states = self.parse_led_state(led_state_value)
                
                for led_name, led_info in led_states.items():
                    key = f"led_{led_name.lower().replace(' ', '_')}"
                    if key in self.status_indicators:
                        self.status_indicators[key].set_status(
                            led_info['status_type'], 
                            led_info['message']
                        )
                        
            except (ValueError, TypeError) as e:
                print(f"LED 상태 파싱 오류: {e}")
            
            # Alarm Status Monitor 업데이트 - 문서 기준 16비트 파싱
            alarm_state_raw = status_data.get("Alarm State", "None")
            try:
                if alarm_state_raw != "None":
                    if isinstance(alarm_state_raw, str) and "0x" in alarm_state_raw:
                        hex_part = alarm_state_raw.split("0x")[1]
                        alarm_state_value = int(hex_part, 16)
                    else:
                        alarm_state_value = 0
                else:
                    alarm_state_value = 0
                
                alarm_states = self.parse_alarm_state(alarm_state_value)
                
                # 단일 비트 알람들 업데이트
                single_bit_alarms = ["PFC Fail", "Max Power Limit", "Gate Driver Amp", "Fan Fail", "Over Temp", "Under FWD Power"]
                for alarm_name in single_bit_alarms:
                    if alarm_name in alarm_states:
                        key = f"alarm_{alarm_name.lower().replace(' ', '_')}"
                        if key in self.status_indicators:
                            alarm_info = alarm_states[alarm_name]
                            self.status_indicators[key].set_status(
                                alarm_info['status_type'],
                                alarm_info['message']
                            )
                
                # 다중 비트 필드들 업데이트
                multi_bit_fields = ["aux_power", "ac_phase", "interlock"]
                for field_name in multi_bit_fields:
                    display_name = self.alarm_bit_definitions[field_name][2]
                    if display_name in alarm_states:
                        key = f"alarm_{field_name}"
                        if key in self.status_indicators:
                            field_info = alarm_states[display_name]
                            self.status_indicators[key].set_status(
                                field_info['status_type'],
                                field_info['message']
                            )
                        
            except (ValueError, TypeError) as e:
                print(f"알람 상태 파싱 오류: {e}")
                
        except Exception as e:
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log(f"[ERROR] 상태 모니터 업데이트 실패: {e}", "red")
    
    def update_minimal_header(self, status_data):
        """미니멀 헤더 업데이트 - Delivery Power 색상 수정"""
        if not hasattr(self, 'minimal_header'):
            return
            
        # Forward Power
        fwd_power = status_data.get("Forward Power", 0)
        fwd_status = self.determine_power_status(fwd_power, "forward")
        self.minimal_header.update_metric('forward_power', fwd_power, fwd_status)
        
        # Reflect Power  
        ref_power = status_data.get("Reflect Power", 0)
        ref_status = self.determine_power_status(ref_power, "reflect")
        self.minimal_header.update_metric('reflect_power', ref_power, ref_status)
        
        # Delivery Power - Forward Power와 동일한 임계값 사용
        del_power = status_data.get("Delivery Power", 0)
        del_status = self.determine_power_status(del_power, "forward")  # "forward" 타입으로 변경
        self.minimal_header.update_metric('delivery_power', del_power, del_status)
        
        # Temperature
        temperature = status_data.get("Temperature", 0)
        temp_status = self.determine_temperature_status(temperature)
        self.minimal_header.update_metric('temperature', temperature, temp_status)
    
    def refresh_status(self):
        """수동 새로 고침"""
        self.status_update_requested.emit()
        self.update_status_from_parent()  # 즉시 업데이트

        if self.check_connection():
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log("[INFO] 상태 모니터 수동 새로 고침", "cyan")
        else:
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log("[WARNING] 통신 연결 없음: 장비와 연결을 확인하세요", "yellow")
    
    def closeEvent(self, event):
        if self.update_timer:
            self.update_timer.stop()
        super().closeEvent(event)
        
        
    def clear_alarm(self):
        """알람 클리어 명령 전송"""
        try:
            # 네트워크 연결 확인
            if not self.check_connection():
                if hasattr(self.parent_window, 'log_manager'):
                    self.parent_window.log_manager.write_log(
                        "[WARNING] 통신 연결 없음: 장비와 연결을 확인하세요", 
                        "yellow"
                    )
                return
            
            # 알람 클리어 명령 전송
            from rf_protocol import RFProtocol
            from PyQt5.QtWidgets import QMessageBox
            
            # 클리어할 알람 타입 (0x0000 = 모든 알람 클리어)
            clear_data = bytes([0x00, 0x00])
            
            # 명령 전송 (동기 모드)
            result = self.parent_window.network_manager.client_thread.send_command(
                cmd=RFProtocol.CMD_ALARM_CLEAR,
                subcmd=RFProtocol.SUBCMD_ALARM_CLEAR,
                data=clear_data,
                wait_response=True,
                sync=True,
                timeout=5.0
            )
            
            # 결과 처리
            if result.success:
                if hasattr(self.parent_window, 'log_manager'):
                    self.parent_window.log_manager.write_log(
                        "[SUCCESS] 알람이 클리어되었습니다", 
                        "green"
                    )
                
                # 상태 즉시 갱신
                self.refresh_status()
                
                # 사용자에게 알림
                QMessageBox.information(
                    self, 
                    "알람 클리어", 
                    "알람이 성공적으로 클리어되었습니다."
                )
            else:
                error_msg = f"알람 클리어 실패: {result.message}"
                if hasattr(self.parent_window, 'log_manager'):
                    self.parent_window.log_manager.write_log(
                        f"[ERROR] {error_msg}", 
                        "red"
                    )
                
                # 에러 메시지 표시
                QMessageBox.warning(
                    self,
                    "알람 클리어 실패",
                    error_msg
                )
                
        except Exception as e:
            error_msg = f"알람 클리어 중 오류 발생: {str(e)}"
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log(
                    f"[ERROR] {error_msg}",
                    "red"
                )

    def show_dcc_interface(self):
        """DCC Interface 다이얼로그 표시"""
        try:
            from dcc_interface_dialog import DCCInterfaceDialog

            dcc_dialog = DCCInterfaceDialog(self.parent_window)
            dcc_dialog.exec_()  # 모달 다이얼로그로 표시

            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log("[INFO] DCC Interface 다이얼로그 열림", "cyan")

        except Exception as e:
            error_msg = f"DCC Interface 다이얼로그 열기 실패: {str(e)}"
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log(
                    f"[ERROR] {error_msg}",
                    "red"
                )