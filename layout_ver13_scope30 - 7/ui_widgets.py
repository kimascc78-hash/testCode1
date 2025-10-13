"""
UI Widgets Module - 플로팅 기반 단순화된 도킹 시스템
"""

from PyQt5.QtWidgets import QWidget, QDockWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QPainter, QPen, QColor, QFont
import pyqtgraph as pg
import json
import os


class GaugeWidget(QWidget):
    """원형 게이지 위젯"""
    
    def __init__(self, title, min_value, max_value, unit, color, parent=None):
        super().__init__(parent)
        self.title = title
        self.min_value = min_value
        self.max_value = max_value
        self.unit = unit
        self.color = color
        self.value = min_value
        
        self.setMinimumSize(140, 140)
        self.setMaximumSize(180, 180)

    def set_value(self, value):
        """게이지 값 설정"""
        self.value = max(self.min_value, min(self.max_value, value))
        self.update()
    
    def update_range(self, min_value, max_value):
        """게이지 범위 업데이트"""
        self.min_value = min_value
        self.max_value = max_value
        # 현재 값이 새 범위를 벗어나면 조정
        self.value = max(self.min_value, min(self.max_value, self.value))
        self.update()
    
    def update_color(self, color):
        """게이지 색상 업데이트"""
        self.color = color
        self.update()

    def paintEvent(self, event):
        """게이지 그리기"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width, height = self.width(), self.height()
        size = min(width, height)
        center = width / 2, height / 2
        radius = size / 2 - 20

        # 배경 원
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#252535"))
        painter.drawEllipse(int(center[0] - radius), int(center[1] - radius), 
                          int(2 * radius), int(2 * radius))

        # 배경 호
        painter.setPen(QPen(QColor("#3e3e4e"), 10))
        painter.drawArc(int(center[0] - radius), int(center[1] - radius), 
                       int(2 * radius), int(2 * radius), 45 * 16, 270 * 16)

        # 값 호
        painter.setPen(QPen(QColor(self.color), 10))
        angle = 270 * (self.value - self.min_value) / (self.max_value - self.min_value)
        painter.drawArc(int(center[0] - radius), int(center[1] - radius), 
                       int(2 * radius), int(2 * radius), 45 * 16, int(angle * 16))

        # 텍스트
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Roboto Mono", 10))
        
        title_y = int(center[1] - radius * 0.3)
        value_y = int(center[1] + radius * 0.3)
        
        painter.drawText(0, title_y, width, 20, Qt.AlignCenter, self.title)
        painter.drawText(0, value_y, width, 20, Qt.AlignCenter, f"{self.value:.2f} {self.unit}")


class SimpleDockSizeManager:
    """단순화된 크기 관리자"""
    
    def __init__(self, config_dir="data"):
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "dock_sizes.json")
        self.dock_sizes = {}
        
        os.makedirs(config_dir, exist_ok=True)
        self.load_sizes()
    
    def save_sizes(self):
        """크기 설정 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                serializable_sizes = {}
                for dock_name, sizes in self.dock_sizes.items():
                    serializable_sizes[dock_name] = {
                        "docked": {"width": sizes["docked"].width(), "height": sizes["docked"].height()},
                        "floating": {"width": sizes["floating"].width(), "height": sizes["floating"].height()}
                    }
                json.dump(serializable_sizes, f, indent=2)
            return True
        except Exception as e:
            return False
    
    def load_sizes(self):
        """크기 설정 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for dock_name, sizes in data.items():
                        self.dock_sizes[dock_name] = {
                            "docked": QSize(sizes["docked"]["width"], sizes["docked"]["height"]),
                            "floating": QSize(sizes["floating"]["width"], sizes["floating"]["height"])
                        }
            return True
        except Exception as e:
            return False
    
    def get_dock_size(self, dock_name, is_floating=False):
        """도킹 위젯의 적절한 크기 반환"""
        if dock_name in self.dock_sizes:
            return self.dock_sizes[dock_name]["floating" if is_floating else "docked"]
        else:
            # 기본 크기
            if is_floating:
                return QSize(600, 800)
            else:
                return QSize(260, 400)
    
    def set_dock_size(self, dock_name, size, is_floating=False):
        """도킹 위젯 크기 설정"""
        if dock_name not in self.dock_sizes:
            self.dock_sizes[dock_name] = {
                "docked": QSize(260, 400),
                "floating": QSize(600, 800)
            }
        
        self.dock_sizes[dock_name]["floating" if is_floating else "docked"] = size
        self.save_sizes()


class AnalysisDockWidget(QDockWidget):
    """분석 기능 통합 도킹 위젯 - 플로팅 상태 기반 기능 전환"""
    
    # 플로팅 상태 변경 시그널 (고급 분석 기능 활성화/비활성화)
    analysis_mode_changed = pyqtSignal(bool)  # True: 고급 분석 활성화, False: 기본 모드
    
    def __init__(self, title, parent=None, preset="standard"):
        super().__init__(title, parent)
        
        self.dock_name = title.replace(" ", "_").lower()
        self.preset = preset
        self.parent_window = parent
        
        # 크기 관리자
        self.size_manager = SimpleDockSizeManager()
        
        # 상태 추적
        self.analysis_enabled = False
        self.size_restore_timer = QTimer()
        self.size_restore_timer.setSingleShot(True)
        self.size_restore_timer.timeout.connect(self._restore_size_delayed)
        
        # 도킹 위젯 설정
        self.setup_dock_widget()
        self.apply_initial_size()
        self.setup_connections()
    
    def setup_dock_widget(self):
        """도킹 위젯 기본 설정"""
        self.setFeatures(
            QDockWidget.DockWidgetMovable | 
            QDockWidget.DockWidgetFloatable |
            QDockWidget.DockWidgetClosable
        )
        
        self.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | 
            Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea
        )
        
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
    
    def setup_connections(self):
        """시그널 연결"""
        self.topLevelChanged.connect(self._on_floating_changed)
    
    def apply_initial_size(self):
        """초기 크기 적용"""
        is_floating = self.isFloating()
        
        # 크기 설정
        target_size = self.size_manager.get_dock_size(self.dock_name, is_floating)
        
        if is_floating:
            self.setMinimumSize(450, 600)
            self.setMaximumSize(16777215, 16777215)  # 플로팅 시 크기 제한 해제
        else:
            self.setMinimumSize(260, 400)
            self.setMaximumSize(260, 400)  # 도킹 시 적절한 크기 제한
        
        # 지연 실행으로 크기 적용
        QTimer.singleShot(100, lambda: self.resize(target_size))
        
        # 초기 분석 모드 설정
        self.analysis_enabled = is_floating
    
    def _on_floating_changed(self, is_floating):
        """플로팅 상태 변경 처리 - 핵심 로직"""
        # 현재 크기 저장
        current_size = self.size()
        self.size_manager.set_dock_size(self.dock_name, current_size, not is_floating)
        
        # 새로운 상태에 맞는 크기와 제한 설정
        target_size = self.size_manager.get_dock_size(self.dock_name, is_floating)
        
        if is_floating:
            # 플로팅: 크기 제한 해제, 고급 분석 기능 활성화
            self.setMinimumSize(450, 600)
            self.setMaximumSize(16777215, 16777215)
            self.analysis_enabled = True
        else:
            # 도킹: 적절한 크기 제한, 기본 기능만
            self.setMinimumSize(260, 400)
            self.setMaximumSize(260, 400)
            self.analysis_enabled = False
            # ⭐ 새로 추가된 부분
            self._request_dock_redistribution()
        
        # 분석 모드 변경 시그널 발생
        self.analysis_mode_changed.emit(self.analysis_enabled)
        
        # 크기 복원 (지연 실행)
        self.size_restore_timer.start(150)
        
        # 로그 출력
        if hasattr(self.parent_window, 'log_manager'):
            status = "플로팅 (고급 분석)" if is_floating else "도킹 (기본 모드)"
            self.parent_window.log_manager.write_log(
                f"[INFO] {self.windowTitle()} 상태 변경: {status}", "cyan"
            )
    
    def _request_dock_redistribution(self):
        """도킹 위젯들의 자동 재분배 요청"""
        if hasattr(self.parent_window, 'dock_manager'):
            QTimer.singleShot(200, self.parent_window.dock_manager.redistribute_docked_widgets)
    
    def _restore_size_delayed(self):
        """지연된 크기 복원"""
        target_size = self.size_manager.get_dock_size(self.dock_name, self.isFloating())
        self.resize(target_size)
    
    def is_analysis_enabled(self):
        """고급 분석 기능 활성화 상태 반환"""
        return self.analysis_enabled
    
    def save_current_size(self):
        """현재 크기 저장"""
        current_size = self.size()
        self.size_manager.set_dock_size(self.dock_name, current_size, self.isFloating())


# 기존과의 호환성을 위한 별칭
CustomDockWidget = AnalysisDockWidget


def setup_dock_size_preferences(dock_widget, docked_width=260, docked_height=400, 
                               floating_width=600, floating_height=800):
    """도킹 위젯의 선호 크기를 설정하는 도우미 함수"""
    if hasattr(dock_widget, 'size_manager'):
        dock_widget.size_manager.set_dock_size(
            dock_widget.dock_name,
            QSize(docked_width, docked_height),
            False
        )
        dock_widget.size_manager.set_dock_size(
            dock_widget.dock_name,
            QSize(floating_width, floating_height),
            True
        )