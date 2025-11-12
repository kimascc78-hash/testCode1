"""
Refactored Main Window Module
분리된 컴포넌트들을 조립하는 메인 윈도우 - 상태창 색상 스타일 추가 + Status Monitor 통합
"""

import sys
import datetime
import time
import webbrowser
import os

from collections import deque
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QMessageBox, QApplication, QMenu
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtGui import QKeySequence

# 분리된 컴포넌트들 import
from network_manager import NetworkManager
from data_processor import DataProcessor
from ui_controller import UIController
from dock_manager import DockManager
from plot_manager import PlotManager
from tuning_controller import TuningController
from log_manager import LogManager
#from oscilloscope_dialog import OscilloscopeDialog
from osc import OscilloscopeDialog
from status_monitor_dialog import StatusMonitorDialog  
from settings_dialog import SettingsDialog, SettingsManager # 새로 추가
# 기존 모듈들
from data_manager import DataManager, TuningSettingsManager, ConfigManager
from developer_dialog import DeveloperDialog

class MainWindow(QMainWindow):
    """메인 윈도우 클래스 - 컴포넌트 조립자"""
    
    def __init__(self):
        super().__init__()
        
        # 1단계: 기본 설정
        self.init_basic_settings()
        
        # 2단계: 데이터 관리자들 초기화
        self.init_managers()
        
        # 3단계: 컴포넌트들 초기화
        self.init_components()
        
        # 4단계: UI 생성
        self.init_ui()
        
        # 5단계: 통신 및 타이머 시작
        self.init_communication()
        
        # 6단계: 설정 매니저 초기화 (init_managers 메서드에 추가)
        #self.settings_manager = SettingsManager()
        
        # 초기화 완료
        self.log_manager.write_log("[INFO] RF 파워 제너레이터 터미널 시작 (자동 분석 모드)", "cyan")
        
        # 신호 연결 후, 초기 설정 강제 적용 (타이밍 문제 우회)
        self.plot_manager.plots_initialized.connect(lambda: self.on_settings_applied(self.settings_manager.settings))  # 람다로 직접 호출
        #self.log_manager.write_log("[DEBUG] on_settings_applied 연결 완료 (초기 적용 강제)", "cyan")
    
    def _setup_data_timer(self):
        """데이터 처리 타이머 설정 및 시작"""
        self.data_process_timer = QTimer(self)

        # 설정에서 간격 가져오기 (성능 최적화: 50ms → 100ms)
        interval_ms = 100  # 기본값 (최적화)
        try:
            if hasattr(self, 'settings_manager'):
                dc = self.settings_manager.settings.get("data_collection", {})
                interval_ms = dc.get("status_interval_ms", 100)
        except:
            pass

        self.data_process_timer.setInterval(interval_ms)

        # DataProcessor의 주기적 처리 메서드와 연결
        self.data_process_timer.timeout.connect(self.data_processor.process_data_queue)

        # 타이머 시작
        self.data_process_timer.start()
        self.log_manager.write_log(f"[INFO] Data Processor Timer 시작 ({interval_ms}ms)", "cyan")
    
    def init_basic_settings(self):
        """기본 설정"""
        self.setWindowTitle("VHF")
        self.setMinimumSize(1300, 750)
        
        # 상태 변수
        self.auto_save_enabled = False
        self.rf_enabled = False
        self.applying_power = False  #251103✅ 추가
        self.oscilloscope_dialog = None
        self.status_monitor_dialog = None  # 새로 추가
        
        # 플롯 설정
        self.selected_plots = [
            True,   # Forward Power
            True,   # Reflect Power
            True,   # Delivery Power
            False,   # Frequency
            False,  # Gamma
            False,  # Real Gamma
            False,  # Image Gamma
            False,  # RF Phase
            True    # Temperature
        ]
        
        self.plot_labels = [
            "Fwd Pwr", "Ref Pwr", "Del Pwr", "Freq", "Gamma",
            "R Gamma", "I Gamma", "RF Phase", "Temp"
        ]
        
        # 시간 관리
        self.sample_interval = 0.05
        self.sample_count = 0
        self.start_time = time.time()
    
    def init_managers(self):
        """데이터 관리자들 초기화"""
        self.data_manager = DataManager()
        self.tuning_manager = TuningSettingsManager()
        self.config_manager = ConfigManager()
        self.settings_manager = SettingsManager() # yuri 추가
        
        # 튜닝 설정 로드
        success, self.tuning_settings, msg = self.tuning_manager.load_settings()
        print(f"[INFO] {msg}")  # 로그 매니저 생성 전이므로 print 사용
        
        # 플롯 데이터 초기화
        # self.plot_data = {
            # 'forward': [], 'reflect': [], 'delivery': [], 'frequency': [],
            # 'gamma': [], 'real_gamma': [], 'image_gamma': [], 'rf_phase': [],
            # 'temperature': [], 'time': []
        # }
        
        #-- 251103
        # ✅ 키가 없으면 기본값 50초 사용
        # 플롯 데이터 초기화 - 사용자 설정값 적용
        from collections import deque
        display_time_sec = self.settings_manager.settings["plot_settings"].get("display_time_seconds", 50)
        sample_interval = 0.05  # 50ms
        max_points = int(display_time_sec / sample_interval)
        #--
        
        # from collections import deque
        # self.plot_data = {
            # 'forward': deque(maxlen=1000), #50초 저장
            # 'reflect': deque(maxlen=1000),
            # 'delivery': deque(maxlen=1000),
            # 'frequency': deque(maxlen=1000),
            # 'gamma': deque(maxlen=1000),
            # 'real_gamma': deque(maxlen=1000),
            # 'image_gamma': deque(maxlen=1000),
            # 'rf_phase': deque(maxlen=1000),
            # 'temperature': deque(maxlen=1000),
            # 'time': deque(maxlen=1000)
        # }
        
        from collections import deque
        self.plot_data = {
            'forward': deque(maxlen=max_points), #유저 설정 저장
            'reflect': deque(maxlen=max_points),
            'delivery': deque(maxlen=max_points),
            'frequency': deque(maxlen=max_points),
            'gamma': deque(maxlen=max_points),
            'real_gamma': deque(maxlen=max_points),
            'image_gamma': deque(maxlen=max_points),
            'rf_phase': deque(maxlen=max_points),
            'temperature': deque(maxlen=max_points),
            'time': deque(maxlen=max_points)
        }
    
    def init_components(self):
        """컴포넌트들 초기화"""
        # 로그 매니저를 가장 먼저 생성 (다른 컴포넌트들이 로그를 사용할 수 있도록)
        self.log_manager = LogManager(self)
        
        # 나머지 컴포넌트들 생성
        self.network_manager = NetworkManager(self)
        self.data_processor = DataProcessor(self)
        self.ui_controller = UIController(self)
        self.dock_manager = DockManager(self)
        self.plot_manager = PlotManager(self)
        self.tuning_controller = TuningController(self)
    
    def init_ui(self):
        """UI 초기화"""
        # 스타일 적용
        self.apply_styles()
        
        # 도킹 옵션 설정
        self.setDockOptions(
            QMainWindow.AllowTabbedDocks | 
            QMainWindow.AllowNestedDocks 
        )
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 5)
        
        # UI 컴포넌트들 생성 (위임)
        self.ui_controller.create_menubar()
        self.ui_controller.create_settings_panel(main_layout)
        self.ui_controller.create_middle_section(main_layout)
        self.dock_manager.create_dock_widgets()
        QTimer.singleShot(500, self.plot_manager.safe_initialize_plots)  # 추가: 지연 초기화
        
        # 새 연결: 플롯 초기화 완료 시 설정 적용
        #self.plot_manager.plots_initialized.connect(self.apply_gui_settings) ##격자 테스트
        
        # 도킹 상태 복원
        self.dock_manager.restore_dock_state()
        
        # 키보드 단축키 설정
        self.setup_shortcuts()
        
        # 설정 적용
        #self.apply_gui_settings() #격자 테스트
        self.log_manager.write_log("[INFO] UI 초기화 완료", "cyan")
        
    ###################
    def apply_gui_settings(self):
        """GUI 설정 적용"""
        try:
            self.settings_manager.apply_to_main_window(self)
            self.log_manager.write_log("[CONFIG] GUI 설정 적용 완료", "yellow")
        except Exception as e:
            self.log_manager.write_log(f"[ERROR] GUI 설정 적용 실패: {e}", "red")
    
    # def show_settings_dialog(self):
        # """설정 다이얼로그 표시"""
        # dialog = SettingsDialog(self)
        
        # # 설정 적용 시그널 연결
        # dialog.settings_applied.connect(self.on_settings_applied)
        
        # if dialog.exec_() == dialog.Accepted:
            # self.log_manager.write_log("[CONFIG] GUI 설정이 업데이트되었습니다.", "yellow")
    
    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        
        dialog.settings_applied.connect(self.on_settings_applied)
        
        result = dialog.exec_()
        
        dialog.close()           # ← 윈도우 닫기
        dialog.deleteLater()     # ← 메모리에서 삭제 예약
        
        if result == dialog.Accepted:
            self.log_manager.write_log("[CONFIG] GUI 설정이 업데이트되었습니다.", "yellow")
            
    def on_settings_applied(self, new_settings):
        """설정 적용 처리"""
        try:
            # 설정 매니저 업데이트
            self.settings_manager.update_settings(new_settings)
            
            # 메인 윈도우에 설정 적용
            self.settings_manager.apply_to_main_window(self)
            
            # 도크 매니저 색상 업데이트
            self.update_dock_colors()
            
            # 게이지 범위 업데이트
            self.update_gauge_ranges()
            
            # 플롯 설정 업데이트
            self.update_plot_settings()
            
            #self.log_manager.write_log("[SUCCESS] GUI 설정이 성공적으로 적용되었습니다.", "green")
            
        except Exception as e:
            self.log_manager.write_log(f"[ERROR] 설정 적용 중 오류: {e}", "red")
    
    def update_dock_colors(self):
        """도크 색상 업데이트"""
        try:
            colors = self.settings_manager.settings.get("colors", {})
            color_keys = [
                "graph_max", "graph_min", "graph_delivery", "graph_avg", 
                "graph_volt", "graph_real_gamma", "graph_image_gamma", 
                "graph_phase", "graph_temp"
            ]
            
            for i, color_key in enumerate(color_keys):
                if (i < len(self.dock_manager.plot_lines) and 
                    color_key in colors):
                    
                    import pyqtgraph as pg
                    line_width = self.settings_manager.get_plot_setting("line_width")
                    
                    # 플롯 라인 색상 및 두께 업데이트
                    self.dock_manager.plot_lines[i].setPen(
                        pg.mkPen(color=colors[color_key], width=line_width)
                    )
                    
                    # 게이지 색상 업데이트
                    if i < len(self.dock_manager.gauges):
                        self.dock_manager.gauges[i].color = colors[color_key]
                        self.dock_manager.gauges[i].update()
                        
        except Exception as e:
            self.log_manager.write_log(f"[ERROR] 색상 업데이트 실패: {e}", "red")
    
    def update_gauge_ranges(self):
        """게이지 범위 업데이트"""
        try:
            gauge_keys = [
                "forward_power", "reflect_power", "delivery_power", "frequency",
                "gamma", "real_gamma", "image_gamma", "rf_phase", "temperature"
            ]
            
            for i, gauge_key in enumerate(gauge_keys):
                if i < len(self.dock_manager.gauges):
                    gauge = self.dock_manager.gauges[i]
                    range_settings = self.settings_manager.get_gauge_range(gauge_key)
                    
                    # 게이지 범위 업데이트
                    gauge.min_value = range_settings["min"]
                    gauge.max_value = range_settings["max"]
                    gauge.update()  # 다시 그리기
                    
        except Exception as e:
            self.log_manager.write_log(f"[ERROR] 게이지 범위 업데이트 실패: {e}", "red")
            
    def update_plot_settings(self):
        #self.log_manager.write_log("[DEBUG] update_plot_settings() 호출됨", "cyan")  # 메서드 시작 로그 추가
        
        try:
            grid_alpha = self.settings_manager.get_plot_setting("grid_alpha")
            alpha_int = int(grid_alpha * 255)  # 안전 변환 (옛 버전 대비)
            
            num_plots = len(self.dock_manager.plot_widgets)  # 리스트 길이 확인
            #self.log_manager.write_log(f"[DEBUG] plot_widgets 개수: {num_plots}", "cyan")  # 길이 로그 추가
            
            #if num_plots == 0:
            #   self.log_manager.write_log("[WARNING] plot_widgets가 비어 있음 - 플롯 초기화 확인 필요", "yellow")  # 빈 리스트 경고
            #   return  # 스킵
            
            for plot_widget in self.dock_manager.plot_widgets:
                plot_item = plot_widget.getPlotItem()
                
                #self.log_manager.write_log("[DEBUG] 플롯 위젯 처리 중...", "cyan")  # 루프 들어감 확인
                
                axes = ['bottom', 'left']
                for axis_name in axes:
                    axis = plot_item.getAxis(axis_name)
                    axis.setGrid(alpha_int)
                    axis.setZValue(1)  # z-value 보장
                
                plot_widget.showGrid(x=True, y=True, alpha=grid_alpha)
                plot_widget.repaint()
                plot_widget.update()
            
            #self.log_manager.write_log(f"[DEBUG] Grid alpha applied: float={grid_alpha}, int={alpha_int}", "cyan")  # 기존 로그 (루프 후)
        except Exception as e:
            self.log_manager.write_log(f"[ERROR] 플롯 설정 업데이트 실패: {str(e)}", "red")  # 예외 상세 로그
    
    def get_threshold_status(self, value, parameter_type):
        """임계값에 따른 상태 반환"""
        try:
            if parameter_type == "forward_power":
                caution = self.settings_manager.get_threshold("forward_power", "caution")
                warning = self.settings_manager.get_threshold("forward_power", "warning")
                error = self.settings_manager.get_threshold("forward_power", "error")
                
                if value >= error:
                    return "error"
                elif value >= warning:
                    return "warning"
                elif value >= caution:
                    return "caution"
                else:
                    return "normal"
                    
            elif parameter_type == "reflect_power":
                warning = self.settings_manager.get_threshold("reflect_power", "warning")
                error = self.settings_manager.get_threshold("reflect_power", "error")
                
                if value >= error:
                    return "error"
                elif value >= warning:
                    return "warning"
                else:
                    return "normal"
                    
            elif parameter_type == "temperature":
                low = self.settings_manager.get_threshold("temperature", "low")
                warning = self.settings_manager.get_threshold("temperature", "warning")
                error = self.settings_manager.get_threshold("temperature", "error")
                
                if value >= error:
                    return "error"
                elif value >= warning:
                    return "warning"
                elif value < low:
                    return "special"  # 저온
                else:
                    return "normal"
            
            return "normal"
            
        except Exception as e:
            self.log_manager.write_log(f"[ERROR] 임계값 상태 계산 실패: {e}", "red")
            return "normal"
    
    def format_value_with_precision(self, value, parameter_type):
        """설정된 정밀도로 값 포맷"""
        try:
            if parameter_type in ["forward_power", "reflect_power", "delivery_power"]:
                precision = self.settings_manager.get_status_monitor_setting("power_precision")
                return f"{value:.{precision}f}"
                
            elif parameter_type == "temperature":
                precision = self.settings_manager.get_status_monitor_setting("temperature_precision")
                return f"{value:.{precision}f}"
                
            elif parameter_type == "frequency":
                precision = self.settings_manager.get_status_monitor_setting("frequency_precision")
                return f"{value:.{precision}f}"
                
            else:
                return f"{value:.2f}"
                
        except Exception as e:
            return f"{value:.2f}"
    ###################
    def init_communication(self):
        """통신 스레드 및 타이머 초기화"""
        self.network_manager.init_communication()
        
        # 데이터 처리 타이머 설정
        interval_ms = 50  # 기본값
        try:
            if hasattr(self, 'settings_manager'):
                dc = self.settings_manager.settings.get("data_collection", {})
                interval_ms = dc.get("status_interval_ms", 50)
        except:
            pass
        
        self.data_process_timer = QTimer(self)
        self.data_process_timer.timeout.connect(self.data_processor.process_data_queue)
        self.data_process_timer.start(interval_ms)
    
    def apply_styles(self):
        """스타일 적용 - 상태 테이블 색상 강화"""
        colors = {
            "background": "#2e3440", "accent": "#00f0ff", "separator": "#666633",
            "graph_max": "#00f0ff", "graph_avg": "#00ff00", "graph_min": "#ff0000",
            "graph_volt": "#ffff00", "graph_temp": "#ff00ff", "graph_delivery": "#ff9900",
            "graph_real_gamma": "#33ccff", "graph_image_gamma": "#cc33ff", "graph_phase": "#ff3333"
        }
        
        # 스타일시트 적용 - 상태 테이블 스타일 강화
        self.setStyleSheet(f"""
            QMainWindow {{ 
                background-color: {colors['background']}; 
                color: #ffffff; 
                font-family: 'Roboto Mono', monospace; 
                font-size: 12px; 
            }}
            
            /* 기존 스타일들 유지 */
            QWidget {{ 
                background-color: {colors['background']}; 
                color: #ffffff; 
                font-family: 'Roboto Mono', monospace; 
            }}
            
            QLabel {{ 
                color: #dcdcdc; 
                font-size: 12px; 
                padding: 2px; 
            }}
            
            QPushButton {{ 
                background-color: #3e3e4e; 
                border: 1px solid {colors['accent']}; 
                color: #ffffff; 
                padding: 8px 12px; 
                border-radius: 4px; 
                font-weight: bold; 
                font-size: 12px; 
            }}
            
            QPushButton:hover {{ 
                background-color: {colors['accent']}; 
                color: #1e1e2e; 
            }}
            
            QPushButton:pressed {{ 
                background-color: #006064; 
            }}
            
            QLineEdit {{ 
                background-color: #2e2e3e; 
                border: 1px solid {colors['accent']}; 
                color: #ffffff; 
                padding: 6px; 
                border-radius: 3px; 
                font-size: 12px; 
            }}
            
            QLineEdit:focus {{ 
                border: 2px solid #00d4aa; 
                background-color: #363646; 
            }}
            
            QCheckBox {{ 
                color: #dcdcdc; 
                font-size: 11px; 
                spacing: 8px; 
            }}
            
            QCheckBox::indicator {{ 
                width: 16px; 
                height: 16px; 
                border: 1px solid {colors['accent']}; 
                border-radius: 3px; 
                background: #2e2e3e; 
            }}
            
            QCheckBox::indicator:checked {{ 
                background: {colors['accent']}; 
                border: 1px solid #00d4aa; 
            }}
            
            QCheckBox::indicator:checked::after {{ 
                content: "✓"; 
                color: #1e1e2e; 
                font-weight: bold; 
            }}
            
            QMenuBar {{ 
                background-color: #2e2e3e; 
                color: #ffffff; 
                border-bottom: 1px solid {colors['accent']}; 
                font-size: 12px; 
            }}
            
            QMenuBar::item {{ 
                background-color: transparent; 
                padding: 8px 12px; 
            }}
            
            QMenuBar::item:selected {{ 
                background-color: {colors['accent']}; 
                color: #1e1e2e; 
            }}
            
            QMenu {{ 
                background-color: #2e2e3e; 
                color: #ffffff; 
                border: 1px solid {colors['accent']}; 
                border-radius: 4px; 
            }}
            
            QMenu::item {{ 
                padding: 8px 16px; 
                border-radius: 2px; 
            }}
            
            QMenu::item:selected {{ 
                background-color: {colors['accent']}; 
                color: #1e1e2e; 
            }}
            
            QTextEdit {{ 
                background-color: #252535; 
                border: 1px solid {colors['accent']}; 
                border-radius: 5px; 
                color: #ffffff; 
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 8px;
            }}
            
            QDockWidget {{
                color: #ffffff;
                font-weight: bold;
                border: 2px solid {colors['separator']};
                margin: 2px 10px 2px 2px;
                titlebar-close-icon: none;
                titlebar-normal-icon: none;
            }}
            
            QDockWidget::title {{
                background-color: {colors['separator']};
                color: #ffffff;
                padding-left: 15px;
                padding-right: 8px;
                padding-top: 8px;
                padding-bottom: 8px;
                border-radius: 4px;
                text-align: center;
                font-size: 13px;
                font-weight: bold;
                border-bottom: 2px solid #444444;
                border-top: 1px solid #888888;
            }}
            
            QTabWidget::pane {{ 
                border: 1px solid {colors['accent']}; 
                background: #252535; 
            }}
            
            QTabBar::tab {{ 
                background: #2e2e3e; 
                color: #d0d0d0; 
                padding: 8px 12px; 
                margin-right: 2px; 
                border: 1px solid #444; 
                border-radius: 4px 4px 0 0; 
            }}
            
            QTabBar::tab:selected {{ 
                background: {colors['accent']}; 
                color: #1e1e2e; 
                font-weight: bold; 
            }}
            
            QTabBar::tab:hover {{ 
                background: #3a3a4a; 
                color: #ffffff; 
            }}
        """)
    
    def setup_shortcuts(self):
        """키보드 단축키 설정"""
        from PyQt5.QtWidgets import QShortcut
        
        # 튜닝 설정 다이얼로그
        tuning_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        tuning_shortcut.activated.connect(self.show_tuning_dialog)
        
        # 오실로스코프 다이얼로그
        oscilloscope_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        oscilloscope_shortcut.activated.connect(self.show_oscilloscope)
        
        # 상태 모니터 다이얼로그 (새로 추가)
        status_monitor_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        status_monitor_shortcut.activated.connect(self.show_status_monitor)
        
        # GUI 설정 다이얼로그 (새로 추가)
        settings_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        settings_shortcut.activated.connect(self.show_settings_dialog)
        
        # 로그 클리어
        clear_log_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_log_shortcut.activated.connect(self.log_manager.clear_log)
        
        # 데이터 저장
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_excel)
        
        # 모든 도킹 위젯 상태 저장
        save_state_shortcut = QShortcut(QKeySequence("F5"), self)
        save_state_shortcut.activated.connect(self.dock_manager.save_state)
        
        # 그래프 초기화 단축키
        clear_graphs_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        clear_graphs_shortcut.activated.connect(self.ui_controller.clear_all_graphs)
        
        self.log_manager.write_log("[INFO] 키보드 단축키 설정 완료", "cyan")
    
    # 메뉴 액션들
    def show_tuning_dialog(self):
        """튜닝 설정 다이얼로그 표시"""
        self.tuning_controller.show_tuning_dialog()
    
    def show_oscilloscope(self):
        """오실로스코프 다이얼로그 표시"""
        try:
            if self.oscilloscope_dialog is None or not self.oscilloscope_dialog.isVisible():
                self.oscilloscope_dialog = OscilloscopeDialog(self)
                
                # OSC 열린 직후 설정 적용
                try:
                    if hasattr(self, 'settings_manager'):
                        settings = self.settings_manager.settings
                        if "data_collection" in settings:
                            osc_view = self.oscilloscope_dialog.oscilloscope_view
                            dc = settings["data_collection"]
                            
                            # 샘플 간격
                            interval_ms = dc.get("status_interval_ms", 50)
                            osc_view.plot_widget.sample_interval = interval_ms / 1000.0
                            osc_view.status_update_interval = interval_ms
                            
                            # 렌더링 주기
                            render_ms = dc.get("osc_render_interval_ms", 33)
                            osc_view.plot_widget.render_timer.setInterval(render_ms)
                except Exception as e:
                    if hasattr(self, 'log_manager'):
                        self.log_manager.write_log(f"[WARNING] OSC 설정 적용 실패: {e}", "yellow")
                
                self.oscilloscope_dialog.show()
                self.log_manager.write_log("[INFO] 오실로스코프 뷰 열림", "cyan")
            else:
                self.oscilloscope_dialog.raise_()
                self.oscilloscope_dialog.activateWindow()
        except Exception as e:
            self.log_manager.write_log(f"[ERROR] 오실로스코프 뷰 열기 실패: {e}", "red")
    
    def show_status_monitor(self):
        """상태 모니터 다이얼로그 표시 (새로 추가)"""
        try:
            if self.status_monitor_dialog is None or not self.status_monitor_dialog.isVisible():
                self.status_monitor_dialog = StatusMonitorDialog(self)
                self.status_monitor_dialog.show()
                self.log_manager.write_log("[INFO] 상태 모니터 다이얼로그 열림", "cyan")
            else:
                self.status_monitor_dialog.raise_()
                self.status_monitor_dialog.activateWindow()
        except Exception as e:
            self.log_manager.write_log(f"[ERROR] 상태 모니터 다이얼로그 열기 실패: {e}", "red")
    
    def save_excel(self):
        """엑셀 저장"""
        success, msg = self.data_manager.save_excel()
        color = "cyan" if success else "yellow"
        self.log_manager.write_log(f"[INFO] {msg}", color)
    
    def save_log(self):
        """로그 저장"""
        log_content = self.log_manager.get_log_content()
        success, msg = self.data_manager.save_log(log_content)
        color = "cyan" if success else "red"
        self.log_manager.write_log(f"[INFO] {msg}", color)
    
    def toggle_auto_save(self):
        """자동 저장 토글"""
        self.auto_save_enabled = not self.auto_save_enabled
        
        # 메뉴 텍스트 업데이트
        for action in self.menuBar().findChildren(QMenu):
            if action.title() == "Log":
                for sub_action in action.actions():
                    if sub_action.text().startswith("자동 저장"):
                        sub_action.setText(f"자동 저장 {'끄기' if self.auto_save_enabled else '켜기'}")
        
        status = '활성화' if self.auto_save_enabled else '비활성화'
        self.log_manager.write_log(f"[INFO] 자동 저장 {status}", "cyan")
    
    def show_license(self):
        """라이센스 정보 표시"""
        QMessageBox.information(self, "License", "This software is licensed under the MIT License.")
    
    def show_web_manual(self):
        """웹 매뉴얼 열기"""
        try:
            # 실행 파일의 경로를 찾기 (PyInstaller 대응)
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 실행 파일인 경우
                base_path = sys._MEIPASS
            else:
                # 일반 Python 스크립트로 실행되는 경우
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            # 매뉴얼 파일 경로
            manual_path = os.path.join(base_path, 'resources', 'manual', 'VHF_RF_Generator_Manual_Ver_1_1.html')
            
            # 파일 존재 확인
            if os.path.exists(manual_path):
                # 파일을 절대 경로로 변환하고 브라우저로 열기
                manual_url = 'file:///' + os.path.abspath(manual_path).replace('\\', '/')
                webbrowser.open(manual_url)
                self.log_manager.write_log("[INFO] 웹 매뉴얼 열기 성공", "cyan")
            else:
                QMessageBox.warning(
                    self, 
                    "매뉴얼 파일 없음", 
                    f"매뉴얼 파일을 찾을 수 없습니다.\n경로: {manual_path}"
                )
            self.log_manager.write_log(f"[WARNING] 매뉴얼 파일 없음: {manual_path}", "yellow")
    
        except Exception as e:
            QMessageBox.critical(
                self, 
                "오류", 
                f"웹 매뉴얼을 열 수 없습니다.\n오류: {str(e)}"
            )
            self.log_manager.write_log(f"[ERROR] 웹 매뉴얼 열기 실패: {e}", "red")
    
    def show_about(self):
        """정보 표시"""
        QMessageBox.information(self, "About", "RF Power Generator Terminal\nVersion 1.0\nDeveloped by xAI")
    
    # 이벤트 핸들러들
    # main_window.py (MainWindow 클래스 내부)
    def apply_plot_settings(self):
        """사용자 설정에서 플롯 시간 설정 적용"""
        try:
            display_time_sec = self.settings_manager.settings["plot_settings"].get("display_time_seconds", 50)
            sample_interval = 0.05  # 50ms
            max_points = int(display_time_sec / sample_interval)
            
            # 1. 모든 deque 크기 변경
            from collections import deque
            for key in self.plot_data:
                old_deque = self.plot_data[key]
                self.plot_data[key] = deque(old_deque, maxlen=max_points)
            
            # 2. ✅ X축(시간축) 범위 업데이트
            if hasattr(self, 'dock_manager') and self.dock_manager:
                for plot_widget in self.dock_manager.plot_widgets:
                    if plot_widget:
                        # X축 범위를 display_time_sec로 설정
                        plot_widget.getPlotItem().getViewBox().setRange(xRange=[0, display_time_sec], padding=0)
            
            self.log_manager.write_log(f"[INFO] 플롯 표시 시간 변경: {display_time_sec}초 ({max_points}개 포인트)", "cyan")
        except Exception as e:
            self.log_manager.write_log(f"[ERROR] 플롯 설정 적용 실패: {e}", "red")
            
    
    def apply_data_collection_settings(self, settings):
        """데이터 수집 설정을 실제 시스템에 적용"""
        try:
            # data_collection 설정이 없으면 기본값 사용
            if "data_collection" not in settings:
                self.log_manager.write_log(
                    "[WARNING] data_collection 설정이 없습니다. 기본값 사용", 
                    "yellow"
                )
                return
            
            dc_settings = settings["data_collection"]
            interval_ms = dc_settings.get("status_interval_ms", 50)
            interval_sec = interval_ms / 1000.0
            is_advanced = dc_settings.get("advanced_mode", False)
            
            if is_advanced and "manual_settings" in dc_settings:
                # 고급 모드
                manual = dc_settings["manual_settings"]
                main_sample = manual.get("main_sample_interval", 50) / 1000.0
                main_timer = manual.get("main_timer_interval", 50)
                osc_sample = manual.get("osc_sample_interval", 50) / 1000.0
                osc_timer = manual.get("osc_timer_interval", 50)
            else:
                # 자동 모드
                main_sample = interval_sec
                main_timer = interval_ms
                osc_sample = interval_sec
                osc_timer = interval_ms
            
            # 1. 메인 윈도우 샘플 간격
            self.sample_interval = main_sample
            
            # 2. 메인 데이터 처리 타이머
            if hasattr(self, 'data_process_timer'):
                self.data_process_timer.setInterval(main_timer)
            
            # 3. OSC 설정 (열려있으면)
            if hasattr(self, 'oscilloscope_dialog') and self.oscilloscope_dialog:
                if self.oscilloscope_dialog.isVisible():
                    try:
                        osc_view = self.oscilloscope_dialog.oscilloscope_view
                        osc_view.plot_widget.sample_interval = osc_sample
                        osc_view.status_update_interval = osc_timer
                        
                        if osc_view.status_timer.isActive():
                            osc_view.status_timer.setInterval(osc_timer)
                    except Exception as e:
                        self.log_manager.write_log(f"[WARNING] OSC 설정 적용 실패: {e}", "yellow")
            
            # 4. 렌더링 설정
            osc_render_ms = dc_settings.get("osc_render_interval_ms", 33)
            main_graph_count = dc_settings.get("main_graph_update_count", 4)
            
            # OSC 렌더링 타이머
            if hasattr(self, 'oscilloscope_dialog') and self.oscilloscope_dialog:
                if self.oscilloscope_dialog.isVisible():
                    try:
                        osc_view = self.oscilloscope_dialog.oscilloscope_view
                        if hasattr(osc_view, 'plot_widget'):
                            if hasattr(osc_view.plot_widget, 'render_timer'):
                                osc_view.plot_widget.render_timer.setInterval(osc_render_ms)
                    except Exception as e:
                        self.log_manager.write_log(f"[WARNING] OSC 렌더링 설정 실패: {e}", "yellow")
            
            # 메인 그래프 업데이트 주기
            if hasattr(self, 'plot_manager'):
                self.plot_manager.update_interval = main_graph_count
            
            # 5. 네트워크 매니저 polling 주기
            if hasattr(self, 'network_manager'):
                if hasattr(self.network_manager, 'client_thread'):
                    if self.network_manager.client_thread:
                        self.network_manager.client_thread.status_polling_interval = interval_sec
            
            self.log_manager.write_log(
                f"[INFO] 데이터 수집 주기 변경: {interval_ms}ms", 
                "cyan"
            )
            
        except Exception as e:
            self.log_manager.write_log(
                f"[ERROR] 데이터 수집 설정 적용 실패: {e}", 
                "red"
            )

    def closeEvent(self, event):
        """
        윈도우 종료 이벤트 처리.
        1. 데이터 처리 QTimer를 정지합니다.
        2. 네트워크 스레드에 종료 요청을 보낸 후, 스레드가 완전히 종료될 때까지 대기합니다 (wait()).
           -> 'MainWindow has been deleted' 오류 방지
        """
        
        # 1. 데이터 처리 QTimer 정지 (GUI 느려짐 방지 조치)
        if hasattr(self, 'data_process_timer') and self.data_process_timer.isActive():
            self.data_process_timer.stop()
        
        try:
            # 상태 모니터 다이얼로그 타이머 중지
            #self.status_monitor_dialog.stop_timer()
            if hasattr(self, 'status_monitor_dialog') and self.status_monitor_dialog:
                if hasattr(self.status_monitor_dialog, 'stop_timer'):
                    self.status_monitor_dialog.stop_timer()
            
            # 2. 네트워크 통신 스레드 안전 종료 요청 및 대기
            self.log_manager.write_log("[INFO] 네트워크 통신 스레드 종료 요청...", "red")
            
            # 클라이언트 스레드 중지 요청
            self.network_manager.stop_client() 
            
            # 🚨 핵심 수정: 스레드가 완전히 종료될 때까지 대기 (time.sleep 제거) 🚨
            self.network_manager.wait_for_client_thread_termination() 
            self.log_manager.write_log("[INFO] 네트워크 스레드 종료 완료.", "red")
            
            # 3. 도킹 상태 저장
            self.dock_manager.save_state()
            
            # 4. 튜닝 설정 저장
            success, msg = self.tuning_manager.save_settings(self.tuning_settings)
            if success:
                self.log_manager.write_log(f"[INFO] {msg}", "cyan")
            
            # ❌ 원본 코드에 있던 time.sleep(0.5)를 제거합니다. ❌

            self.log_manager.write_log("[INFO] 애플리케이션 종료 완료", "green")
            
        except Exception as e:
            # 종료 처리 중 예상치 못한 오류가 발생해도 로그를 남기고 종료를 진행합니다.
            print(f"[CRITICAL] 종료 처리 중 오류: {e}")
            self.log_manager.write_log(f"[CRITICAL] 종료 처리 중 오류: {e}", "red")
        
        finally:
            # 이벤트 수락 후 메인 윈도우 삭제
            super().closeEvent(event)
    
    def showEvent(self, event):
        """윈도우가 표시될 때 plot 가시성 보장"""
        super().showEvent(event)
        
        if not hasattr(self, '_plots_shown'):
            self._plots_shown = True
            QTimer.singleShot(300, self.plot_manager.safe_initialize_plots)
            
    def show_developer_dialog(self):
        """Developer Tools 다이얼로그 표시"""
        #from developer_dialog import DeveloperDialog
        
        # 다이얼로그가 없거나 닫혔으면 새로 생성
        if not hasattr(self, 'developer_dialog') or self.developer_dialog is None:
            self.developer_dialog = DeveloperDialog(self, self.network_manager)
            self.log_manager.write_log("[INFO] Developer Tools 다이얼로그 생성", "cyan")
        
        # 다이얼로그 표시
        self.developer_dialog.show()
        self.developer_dialog.raise_()
        self.developer_dialog.activateWindow()
        
        self.log_manager.write_log("[INFO] Developer Tools 열림", "yellow")