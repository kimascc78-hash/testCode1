"""
Oscilloscope View Module
오실로스코프 스타일 9채널 통합 뷰 - 트리거 포인트 드래그 및 0점 동기화, Single 모드에서 pre/post 유지
"""

import time
from collections import deque
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, 
    QLabel, QGroupBox, QButtonGroup, QSizePolicy, QComboBox, QDoubleSpinBox, 
    QFrame  #선큰 추가
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRectF, QPointF
from PyQt5.QtGui import QFont
import pyqtgraph as pg
import numpy as np

from .adc_dac_data_source import AdcDacDataSource, StatusDataSource
from ui_widgets import SmartSpinBox, SmartDoubleSpinBox 
from settings_dialog import SettingsDialog, SettingsManager # 새로 추가

# pyqtgraph 성능 최적화 설정 (안정성 우선)
# antialias=False: 렌더링 속도 향상
# useOpenGL=True: GPU 가속 활성화
# enableExperimental=False: 안정성 우선
pg.setConfigOptions(antialias=False, useOpenGL=True, enableExperimental=False, foreground='w', background='k')

# ============================================
# 커스텀 ViewBox - 오른쪽 버튼 박스 확대
# ============================================
class CustomViewBox(pg.ViewBox):
    """오른쪽 버튼으로 박스 확대 기능을 지원하는 커스텀 ViewBox"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.right_button_pressed = False
        self.right_drag_start = None
    
    def mouseDragEvent(self, ev, axis=None):
        """마우스 드래그 이벤트 처리"""
        # 오른쪽 버튼 드래그 처리
        if ev.button() == Qt.RightButton:
            if ev.isStart():
                self.right_button_pressed = True
                self.right_drag_start = ev.pos()
                self.rbScaleBox.show()
                self.rbScaleBox.setPos(ev.buttonDownPos(Qt.RightButton))
            elif ev.isFinish():
                if self.right_button_pressed and self.right_drag_start is not None:
                    self.rbScaleBox.hide()
                    # 박스 영역으로 확대
                    ax = QRectF(pg.Point(ev.buttonDownPos(ev.button())), pg.Point(ev.pos()))
                    ax = self.childGroup.mapRectFromParent(ax)
                    self.showAxRect(ax)
                    self.axHistoryPointer += 1
                    self.axHistory = self.axHistory[:self.axHistoryPointer] + [ax]
                self.right_button_pressed = False
                self.right_drag_start = None
            else:
                if self.right_button_pressed:
                    self.updateScaleBox(ev.buttonDownPos(Qt.RightButton), ev.pos())
            ev.accept()
        else:
            # 왼쪽 버튼은 기본 Pan 동작
            super().mouseDragEvent(ev, axis)

# ============================================
# 커스텀 AxisItem - 눈금 값 자동 변환
# ============================================
class TimeAxisItem(pg.AxisItem):
    """시간 단위를 자동으로 변환하는 커스텀 축"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_unit = 's'  # 현재 단위 (ms, s, min, h)
        self.scale_factor = 1.0  # 스케일 팩터
        
        # ✅ SI 접두사 완전히 비활성화
        self.enableAutoSIPrefix(False)
    
    def set_unit(self, unit, scale_factor):
        """단위 설정"""
        self.current_unit = unit
        self.scale_factor = scale_factor
    
    def tickStrings(self, values, scale, spacing):
        """눈금 값을 현재 단위로 변환하여 문자열 반환"""
        strings = []
        
        for v in values:
            if self.current_unit == 'ms':
                # 밀리초: v는 초 단위, 밀리초로 변환
                converted_value = v * self.scale_factor
                # 밀리초: 정수 또는 소수점 1자리
                if abs(converted_value) >= 10:
                    strings.append(f"{converted_value:.0f}")
                else:
                    strings.append(f"{converted_value:.1f}")
                    
            elif self.current_unit == 's':
                # 초: v는 초 단위 그대로
                converted_value = v * self.scale_factor
                # 초: 소수점 1-2자리
                if abs(converted_value) >= 10:
                    strings.append(f"{converted_value:.1f}")
                else:
                    strings.append(f"{converted_value:.2f}")
                    
            elif self.current_unit == 'min':
                # 분: m:ss 형식 (3:20 = 3분 20초)
                total_seconds = abs(v)
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                if v < 0:
                    strings.append(f"-{minutes}:{seconds:02d}")
                else:
                    strings.append(f"{minutes}:{seconds:02d}")
                    
            else:  # 'h'
                # 시간: h:mm 형식 (1:30 = 1시간 30분)
                total_seconds = abs(v)
                hours = int(total_seconds // 3600)
                remaining_seconds = total_seconds % 3600
                minutes = int(remaining_seconds // 60)
                if v < 0:
                    strings.append(f"-{hours}:{minutes:02d}")
                else:
                    strings.append(f"{hours}:{minutes:02d}")
        
        return strings

# 옵션 1: 모던 하이테크 (추천)
# 옵션 2: 클래식 장비 스타일
# 옵션 3: 미래지향적 
# 옵션 4: 클린 & 프로페셔널
# 옵션 5: 하이테크 산세리프 (실제 장비 느낌)
SCOPE_FONTS = {
    'V0': "'Courier New', monospace",
    'V1': "'JetBrains Mono', 'Fira Code', 'SF Mono', 'Consolas', monospace",
    'V2': "'Orbitron', 'Exo 2', 'Roboto Mono', monospace",
    'V3': "'Segoe UI', 'SF Pro Text', 'Roboto', sans-serif",
    'V4': "'Source Code Pro', 'Ubuntu Mono', 'Lucida Console', monospace",
    'V5': "'Monaco', 'Menlo', 'DejaVu Sans Mono', monospace",
}

# 원하는 폰트 선택
SELECTED_FONT = SCOPE_FONTS['V1']  # 이 줄만 수정해서 테스트

#기본 테마
# 색상 및 크기, 위치 상수 정의
COLORS = {
    'BACKGROUND': '#3b4252',         # 미드나잇 블루 그레이 - 메인 배경색
    'TEXT': '#ffffff',               # 순백 - 기본 텍스트 색상
    'GROUPBOX_BORDER': '#00FFFF',    # 시안 - 그룹박스 테두리
    'GROUPBOX_TITLE': '#ffffff',     # 라임 그린 - 그룹박스 제목 색상
    'BUTTON_BG': '#333333',          # 다크 그레이 - 버튼 기본 배경
    'BUTTON_BORDER': '#555555',      # 미디엄 그레이 - 버튼 테두리
    'BUTTON_TEXT': '#cccccc',        # 라이트 그레이 - 버튼 텍스트
    'BUTTON_HOVER_BG': '#444444',    # 호버 그레이 - 버튼 호버 배경
    'BUTTON_HOVER_BORDER': '#777777', # 호버 테두리 - 버튼 호버시 테두리
    'BUTTON_CHECKED_BG': '#0066cc',  # 오션 블루 - 선택된 버튼 배경
    'BUTTON_CHECKED_BORDER': '#0088ff', # 브라이트 블루 - 선택된 버튼 테두리
    'RUN_BUTTON_BG': '#6366f1',      # 인디고 블루 - 활동적인 시작
    'RUN_BUTTON_BORDER': '#4f46e5',  # 딥 인디고 - 테두리
    'RUN_BUTTON_HOVER': '#818cf8',   # 라이트 인디고 - 호버
    'RUN_BUTTON_PRESSED': '#3730a3', # 다크 인디고 - 눌림
    'STOP_BUTTON_BG': '#64748b',     # 블루 그레이 - 차분한 정지
    'STOP_BUTTON_BORDER': '#475569', # 다크 블루 그레이 - 테두리
    'STOP_BUTTON_HOVER': '#94a3b8',  # 라이트 블루 그레이 - 호버
    'STOP_BUTTON_PRESSED': '#334155',# 딥 블루 그레이 - 눌림
    'LABEL_TEXT': '#cccccc',         # 라이트 그레이 - 라벨 텍스트
    'PLOT_BG': '#2a2a2a',            # 차콜 그레이 - 플롯 배경색
    'GRID_ALPHA': 0.05,               # 그리드 투명도 (30%)
    'CHANNELS': [                    # 9채널 신호 색상 팔레트
        '#00ff00', # CH1: 라임 그린 - Forward Power
        '#ffff00', # CH2: 옐로우 - Reflect Power  
        '#ff00ff', # CH3: 마젠타 - Delivery Power
        '#00ffff', # CH4: 시안 - Frequency
        '#ff8800', # CH5: 오렌지 - Gamma
        '#88ff00', # CH6: 옐로우 그린 - Real Gamma
        '#ff0088', # CH7: 핑크 - Image Gamma
        '#8800ff', # CH8: 바이올렛 - RF Phase
        '#ffffff'  # CH9: 화이트 - Temperature
    ],
    # UI 컴포넌트 크기 상수
    'MAX_LEFT_PENEL_WIDTH': 280,     # 좌측 패널 최대 너비
    'RF_CONTROL_WIDTH': 280,         # RF 컨트롤 패널 너비
    'RF_CONTROL_HEIGHT': 130,  # ← 100에서 135로 변경
    'CHANNEL_GRID_WIDTH': 280,       # 채널 그리드 너비
    'CHANNEL_GRID_HEIGHT': 190,      # 채널 그리드 높이
    'TIMEBASE_WIDTH': 280,           # 타임베이스 위젯 너비
    'TIMEBASE_HEIGHT': 130,          # 타임베이스 위젯 높이
    'TRIGGER_WIDTH': 280,            # 트리거 위젯 너비
    'TRIGGER_HEIGHT': 180,           # 트리거 위젯 높이
    'MEASUREMENT_WIDTH': 280,        # 측정 컨트롤 너비
    'MEASUREMENT_HEIGHT': 120,       # 측정 컨트롤 높이
    'CONTROLS_WIDTH': 280,           # 컨트롤 패널 너비
    'CONTROLS_HEIGHT': 70,          # 컨트롤 패널 높이 (확장됨)
    'MEASUREMENT_FONT_SIZE': 12,     # 측정값 폰트 크기
}

class ChannelGridWidget(QWidget):
    """9채널 선택 그리드 위젯"""
    
    channel_changed = pyqtSignal(int, bool)  # channel_index, enabled
    
    def __init__(self, parent=None):
        super().__init__(parent)
        #self.active_channels = [True, True] + [False] * 7
        self.active_channels = [False] * 9
        self.display_mode = 'multi'
        self.buttons = []
        self.channel_names = [
            "Fwd Pwr", "Ref Pwr", "Del Pwr", "Frequency", 
            "Gamma", "R Gamma", "I Gamma", "RF Phase", "Temp"
        ]
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        grid_group = QGroupBox("Channel Selection")
        grid_group.setFixedSize(COLORS['CHANNEL_GRID_WIDTH'], COLORS['CHANNEL_GRID_HEIGHT'])
        grid_layout = QGridLayout(grid_group)
        grid_layout.setContentsMargins(5, 5, 5, 15)
        grid_layout.setSpacing(1)
        
        grid_layout.setHorizontalSpacing(1)  # 좌우 간격 1px
        grid_layout.setVerticalSpacing(10)    # 위아래 간격 5px (또는 원하는 값)
        
        for i in range(9):
            btn = QPushButton(f"CH{i+1}\n{self.channel_names[i]}")
            btn.setCheckable(True)
            btn.setChecked(self.active_channels[i])
            btn.setFixedSize(80, 50)
            btn.clicked.connect(lambda checked, idx=i: self.toggle_channel(idx, checked))
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['BUTTON_BG']};
                    border: 2px solid {COLORS['BUTTON_BORDER']};
                    color: {COLORS['BUTTON_TEXT']};
                    font-size: 12px;
                    border-radius: 3px;
                }}
                QPushButton:checked {{
                    border-color: {COLORS['CHANNELS'][i]};
                    background-color: rgba({self._hex_to_rgb(COLORS['CHANNELS'][i])}, 0.3);
                    color: {COLORS['CHANNELS'][i]};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    border-color: {COLORS['BUTTON_HOVER_BORDER']};
                    background-color: {COLORS['BUTTON_HOVER_BG']};
                }}
            """)
            
            grid_layout.addWidget(btn, i // 3, i % 3)
            self.buttons.append(btn)
            
        layout.addWidget(grid_group)
        self.info_label = QLabel("Active: 2/9 channels")
        layout.addWidget(self.info_label)
        self.update_info()
    
    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return ','.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))
    
    def toggle_channel(self, channel_idx, checked):
        self.active_channels[channel_idx] = checked
        self.channel_changed.emit(channel_idx, self.active_channels[channel_idx])
        self.update_info()
    
    def update_buttons(self):
        for i, btn in enumerate(self.buttons):
            btn.setChecked(self.active_channels[i])
    
    def update_info(self):
        active_count = sum(self.active_channels)
        self.info_label.setText(f"Active: {active_count}/9 channels")

class TimebaseWidget(QWidget):
    """시간축 컨트롤 위젯 - 버튼 + 사용자 입력 필드"""
    
    timebase_changed = pyqtSignal(str)  # "1s", "2s" 등 버튼 선택
    custom_timebase_changed = pyqtSignal(float)  # 사용자 입력 (분 단위)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_timebase = '1s'
        self.current_custom_minutes = 0.5
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        group = QGroupBox("Time Base")
        group.setFixedSize(COLORS['TIMEBASE_WIDTH'], COLORS['TIMEBASE_HEIGHT'])
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(3, 3, 3, 3)  # 마진 축소: 5 → 3
        group_layout.setSpacing(2)  # 스페이싱 축소: 5 → 2
        
        # 현재 선택된 타임베이스 표시
        self.value_label = QLabel(f"Current: {self.current_timebase}/div")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setMaximumHeight(18)  # 라벨 높이 제한
        group_layout.addWidget(self.value_label)
        
        # 기존 버튼 그룹
        button_layout = QGridLayout()
        button_layout.setSpacing(2)  # 버튼 간격 축소: 5 → 2
        button_layout.setContentsMargins(0, 0, 0, 0)  # 마진 제거
        times = ['100ms', '500ms', '1s', '2s', '5s', '10s', '30s', '1m']
        
        self.button_group = QButtonGroup()
        
        for i, time_val in enumerate(times):
            btn = QPushButton(time_val)
            btn.setCheckable(True)
            btn.setFixedSize(55, 24)  # 버튼 크기 축소: 60x30 → 55x24
            if time_val == self.current_timebase:
                btn.setChecked(True)
            
            btn.clicked.connect(lambda checked, t=time_val: self.set_timebase(t))
            self.button_group.addButton(btn)
            button_layout.addWidget(btn, i // 4, i % 4)
        
        group_layout.addLayout(button_layout)
        
        # 사용자 정의 시간 입력 필드
        custom_layout = QHBoxLayout()
        custom_layout.setSpacing(1)  # 간격 축소: 3 → 1
        custom_layout.setContentsMargins(25, 0, 0, 0)  # 마진 제거
        
        custom_label = QLabel("User(min):")
        custom_label.setMaximumWidth(85)
        custom_label.setMaximumHeight(20)
        custom_layout.addWidget(custom_label)
        
        # QDoubleSpinBox: 0.5 ~ 1440분 (24시간)
        self.custom_spinbox = QDoubleSpinBox()
        self.custom_spinbox.setMinimum(0.5)
        self.custom_spinbox.setMaximum(1440.0)
        self.custom_spinbox.setValue(self.current_custom_minutes)
        self.custom_spinbox.setSingleStep(0.1)
        self.custom_spinbox.setDecimals(1)
        self.custom_spinbox.setFixedWidth(65)
        self.custom_spinbox.setMaximumHeight(25)
        custom_layout.addWidget(self.custom_spinbox)
        
        # Apply 버튼
        apply_btn = QPushButton("Apply")
        apply_btn.setFixedWidth(50)
        apply_btn.setFixedHeight(28)
        apply_btn.clicked.connect(self.on_apply_custom)
        custom_layout.addWidget(apply_btn)
        
        custom_layout.addStretch()
        group_layout.addLayout(custom_layout)
        
        layout.addWidget(group)
    
    def set_timebase(self, timebase):
        """버튼 선택시 호출"""
        self.current_timebase = timebase
        self.value_label.setText(f"Current: {timebase}/div")
        # 버튼 선택시 spinbox 값 표시 업데이트
        tb_sec = self._parse_timebase_to_sec(timebase)
        self.current_custom_minutes = tb_sec / 60
        self.custom_spinbox.blockSignals(True)
        self.custom_spinbox.setValue(self.current_custom_minutes)
        self.custom_spinbox.blockSignals(False)
        self.timebase_changed.emit(timebase)
    
    def on_apply_custom(self):
        """Apply 버튼 클릭시 호출"""
        minutes = self.custom_spinbox.value()
        self.current_custom_minutes = minutes
        self.current_timebase = f"{minutes:.1f}min"
        self.value_label.setText(f"Current: {minutes:.1f} min (= {minutes*60:.0f}s)")
        # 모든 버튼 체크 해제
        self.button_group.setExclusive(False)
        for btn in self.button_group.buttons():
            btn.setChecked(False)
        self.button_group.setExclusive(True)
        # 사용자 정의 시간으로 신호 발송
        self.custom_timebase_changed.emit(minutes)
    
    def _parse_timebase_to_sec(self, timebase):
        """버튼 값 → 초 변환"""
        try:
            if 'ms' in timebase:
                return float(timebase.replace('ms', '')) / 1000
            elif 's' in timebase:
                return float(timebase.replace('s', ''))
            elif 'm' in timebase:
                return float(timebase.replace('m', '')) * 60
            return 1.0
        except:
            return 1.0

class TriggerWidget(QWidget):
    """트리거 제어 위젯"""
    
    trigger_changed = pyqtSignal(dict)

    def __init__(self, channel_names, parent=None):
        super().__init__(parent)
        self.channel_names = channel_names
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        group = QGroupBox("Trigger")
        group.setFixedSize(COLORS['TRIGGER_WIDTH'], COLORS['TRIGGER_HEIGHT'])
        g_layout = QVBoxLayout(group)
        g_layout.setContentsMargins(5, 5, 5, 5)
        g_layout.setSpacing(5)

        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(5)
        self.mode_group = QButtonGroup()
        self.auto_btn = QPushButton("Auto")
        self.normal_btn = QPushButton("Normal")
        self.single_btn = QPushButton("Single")
        for btn in [self.auto_btn, self.normal_btn, self.single_btn]:
            btn.setCheckable(True)
            self.mode_group.addButton(btn)
        self.auto_btn.setChecked(True)
        mode_layout.addWidget(self.auto_btn)
        mode_layout.addWidget(self.normal_btn)
        mode_layout.addWidget(self.single_btn)
        g_layout.addLayout(mode_layout)

        source_layout = QHBoxLayout()
        source_layout.setSpacing(5)
        source_label = QLabel("Source:")
        self.source_combo = QComboBox()
        self.source_combo.addItems(self.channel_names)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_combo)
        g_layout.addLayout(source_layout)

        type_layout = QHBoxLayout()
        type_layout.setSpacing(5)
        type_label = QLabel("Type:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Rising Edge", "Falling Edge", "Level"])
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        g_layout.addLayout(type_layout)

        level_layout = QHBoxLayout()
        level_layout.setSpacing(5)
        level_label = QLabel("Level:")
        self.level_spin = SmartDoubleSpinBox()
        self.level_spin.setRange(-1e6, 1e6)
        self.level_spin.setValue(0.0)
        level_layout.addWidget(level_label)
        level_layout.addWidget(self.level_spin)
        g_layout.addLayout(level_layout)

        layout.addWidget(group)

        self.source_combo.currentIndexChanged.connect(self.emit_change)
        self.type_combo.currentIndexChanged.connect(self.emit_change)
        self.level_spin.valueChanged.connect(self.emit_change)
        for btn in [self.auto_btn, self.normal_btn, self.single_btn]:
            btn.clicked.connect(self.emit_change)

    def get_settings(self):
        mode = "auto" if self.auto_btn.isChecked() else "normal" if self.normal_btn.isChecked() else "single"
        source = self.source_combo.currentIndex()
        trig_type = "rising" if self.type_combo.currentText() == "Rising Edge" else \
                    "falling" if self.type_combo.currentText() == "Falling Edge" else "level"
        level = self.level_spin.value()
        return {"mode": mode, "source": source, "type": trig_type, "level": level}

    def emit_change(self):
        self.trigger_changed.emit(self.get_settings())

class MeasurementControlWidget(QWidget):
    """측정 영역 제어 위젯"""
    
    measurement_mode_changed = pyqtSignal(str)
    reset_measurement = pyqtSignal()
    snap_to_peak = pyqtSignal(int)
    
    def __init__(self, channel_names, parent=None):
        super().__init__(parent)
        self.channel_names = channel_names
        self.current_mode = "floating"
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        group = QGroupBox("Measurement Control")
        group.setFixedSize(COLORS['MEASUREMENT_WIDTH'], COLORS['MEASUREMENT_HEIGHT'])
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(5, 5, 5, 5)
        group_layout.setSpacing(5)
        
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(5)
        mode_label = QLabel("Mode:")
        self.float_btn = QPushButton("Float")
        self.fixed_btn = QPushButton("Fixed")
        
        self.float_btn.setCheckable(True)
        self.fixed_btn.setCheckable(True)
        self.float_btn.setChecked(True)
        
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.float_btn)
        self.mode_group.addButton(self.fixed_btn)
        
        self.float_btn.clicked.connect(lambda: self.set_measurement_mode("floating"))
        self.fixed_btn.clicked.connect(lambda: self.set_measurement_mode("fixed"))
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.float_btn)
        mode_layout.addWidget(self.fixed_btn)
        group_layout.addLayout(mode_layout)
        
        control_layout = QHBoxLayout()
        control_layout.setSpacing(5)
        
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_measurement.emit)
        
        self.center_btn = QPushButton("View All")
        self.center_btn.clicked.connect(self.center_measurement)
        
        control_layout.addWidget(self.reset_btn)
        control_layout.addWidget(self.center_btn)
        group_layout.addLayout(control_layout)
        
        snap_layout = QHBoxLayout()
        snap_layout.setSpacing(5)
        snap_label = QLabel("Snap to Peak:")
        self.snap_combo = QComboBox()
        self.snap_combo.addItems([f"CH{i+1}" for i in range(9)])
        self.snap_btn = QPushButton("Go")
        self.snap_btn.clicked.connect(self.on_snap_to_peak)
        
        snap_layout.addWidget(snap_label)
        snap_layout.addWidget(self.snap_combo)
        snap_layout.addWidget(self.snap_btn)
        group_layout.addLayout(snap_layout)
        
        layout.addWidget(group)
    
    def set_measurement_mode(self, mode):
        self.current_mode = mode
        self.measurement_mode_changed.emit(mode)
        if mode == "floating":
            self.float_btn.setChecked(True)
        else:
            self.fixed_btn.setChecked(True)
    
    def center_measurement(self):
        #self.reset_measurement.emit()
        """그래프 전체 데이터 보기 (View All)"""
        try:
            # 상위 위젯 탐색 (OscilloscopeView)
            parent = self.parent()
            while parent is not None and not hasattr(parent, "plot_widget"):
                parent = parent.parent()
            if parent is None:
                print("[ERROR] plot_widget not found in parent chain")
                return

            plot_widget = parent.plot_widget.plot_widget
            viewBox = plot_widget.getViewBox()

            # === 전체 데이터 범위 계산 ===
            all_x = []
            all_y = []

            for i in range(9):
                line = parent.plot_widget.plot_lines[i]
                if not line.isVisible():
                    continue
                data = line.getData()
                if data is None or len(data[0]) == 0:
                    continue
                all_x.extend(data[0])
                all_y.extend(data[1])

            if not all_x or not all_y:
                #print("[View All] No data to fit.")
                return

            x_min, x_max = min(all_x), max(all_x)
            y_min, y_max = min(all_y), max(all_y)

            # === 여유 공간 약간 추가 ===
            x_padding = (x_max - x_min) * 0.05 if x_max != x_min else 1
            y_padding = (y_max - y_min) * 0.1 if y_max != y_min else 1

            viewBox.setXRange(x_min - x_padding, x_max + x_padding, padding=0)
            viewBox.setYRange(y_min - y_padding, y_max + y_padding, padding=0)

            # 자동 단위 갱신
            parent.plot_widget.update_x_axis_unit()

            #print(f"[View All] X:[{x_min:.2f},{x_max:.2f}]  Y:[{y_min:.2f},{y_max:.2f}]")
        except Exception as e:
            print(f"[ERROR] View All: {e}")
    
    def on_snap_to_peak(self):
        channel_idx = self.snap_combo.currentIndex()
        self.snap_to_peak.emit(channel_idx)

class UnifiedPlotWidget(QWidget):
    """통합 플롯 위젯"""
    
    trigger_level_changed = pyqtSignal(float)
    stop_acquisition_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        #self.active_channels = [True, True] + [False] * 7
        self.active_channels = [False] * 9
        self.display_mode = 'multi'
        #self.buffer_size = 500  # 줄여서 부하 감소
        self.buffer_size = 12001  # 10 그리드 그리드당 1분 600초에대한 버퍼
        self.time_data = deque(maxlen=self.buffer_size)
        self.channel_data = [deque(maxlen=self.buffer_size) for _ in range(9)]
        self.pre_time_data = deque(maxlen=self.buffer_size)
        self.pre_channel_data = [deque(maxlen=self.buffer_size) for _ in range(9)]
        self.display_time = []
        self.display_channel_data = [[] for _ in range(9)]
        self.trigger_settings = None
        self.trigger_mode = "auto"
        self.acquiring = False
        self.triggered = False
        self.last_sweep_time = 0
        self.total_time = 10.0
        self.pre_time = 5.0
        self.post_time = 5.0
        self._updating = False
        self.measurement_mode = "floating"
        self.fixed_measurement_range = None
        self.last_time_range = None
        
        #############
        # 데이터 처리 타이머 설정
        self.settings_manager = SettingsManager() # yuri 추가
        #############
        
        # 고정 간격 적용을 위한 변수 추가 (1번 해결 방법)
        # 설정에서 가져오기 (나중에 업데이트됨)
        #self.sample_interval = 0.05  # 기본값
        self.sample_interval = 0.05  # 기본값
        self.sample_count = 0  # 샘플 카운터
        self.pre_sample_count = 0  # pre 버퍼용 카운터
        
        # ✅ 마우스 범위 조정 관련 플래그
        self.manual_range_mode = False  # 수동 범위 설정 모드
        self.auto_follow_time = True    # 자동 따라가기
        self.is_auto_ranging = False     # Auto Range 버튼 실행 중 플래그 ← 추가
        
        self.channel_names = [
            "Forward Power", "Reflect Power", "Delivery Power", "Frequency", 
            "Gamma", "Real Gamma", "Image Gamma", "RF Phase", "Temperature"
        ]
        self.channel_units = [
            "W", "W", "W", "MHz", "", "", "", "°", "°C"
        ]
        
        # X축 단위 동적 변경을 위한 변수
        self.current_x_unit = 's'  # 현재 X축 단위 (ms, s, min, h)
        self.x_scale_factor = 1.0  # X축 스케일 팩터
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)

        # 선큰 플롯을 프레임으로 감싸기
        plot_frame = QFrame()
        
        ##plot_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        plot_frame.setStyleSheet("""
            QFrame {
                border: 2px inset #555555;
                border-radius: 3px;
                background-color: #CCCCCC;
                margin: 2px;
            }
        """)
        
        plot_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        frame_layout = QVBoxLayout(plot_frame)
        frame_layout.setContentsMargins(3, 3, 3, 3)  # 아래쪽 여백 늘리기
        ##
        
        # ✅ 커스텀 TimeAxisItem 생성
        self.time_axis = TimeAxisItem(orientation='bottom')
        
        # ✅ 커스텀 ViewBox 생성
        custom_viewbox = CustomViewBox()
        
        # PlotWidget 생성 (커스텀 축 및 커스텀 ViewBox 사용)
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': self.time_axis}, viewBox=custom_viewbox)
        #self.plot_widget.setAntialiasing(True)  # GraphicsView 수준
        #self.plot_widget.getViewBox().setAntialiasing(True)  # ViewBox 수준
        self.plot_widget.getPlotItem().getAxis('bottom').setStyle(tickLength=-10)
        
        plotItem = self.plot_widget.getPlotItem()
        plotItem.setContentsMargins(10, 10, 10, 15)  # 아래쪽 여백 늘리기
        
        self.plot_widget.setBackground(COLORS['PLOT_BG'])
        self.plot_widget.showGrid(x=True, y=True, alpha=COLORS['GRID_ALPHA'])
        self.plot_widget.setLabel('left', 'Value', color=COLORS['TEXT'])
        self.plot_widget.setLabel('bottom', 'Time', units='s', color=COLORS['TEXT'], enableUnitPrefix=False)
        self.plot_widget.setClipToView(True)
        
        # ✅ 오른쪽 버튼 메뉴 비활성화
        self.plot_widget.setMenuEnabled(False)
        
        # ✅ ViewBox 마우스 설정
        viewBox = self.plot_widget.getViewBox()
        # 기본 모드는 Pan (왼쪽 버튼 드래그로 이동)
        # 오른쪽 버튼은 커스텀 ViewBox에서 박스 확대 처리
        viewBox.setMouseMode(viewBox.PanMode)
        
        self.plot_lines = []
        for i in range(9):
            line = self.plot_widget.plot(
                pen=pg.mkPen(color=COLORS['CHANNELS'][i], width=1),
                name=f"CH{i+1}: {self.channel_names[i]}",
                downsample=True,  # 다운샘플링 활성화
                downsampleMethod='peak'
            )
            line.setVisible(self.active_channels[i])
            self.plot_lines.append(line)
        
        frame_layout.addWidget(self.plot_widget)  # 선큰 프레임에 추가
        layout.addWidget(plot_frame)
        #layout.addWidget(self.plot_widget)
        
        self.legend = self.plot_widget.addLegend()
        for i in range(9):
            if self.active_channels[i]:
                self.legend.addItem(self.plot_lines[i], f"CH{i+1}: {self.channel_names[i]}")
        
        # ✅ ViewBox 범위 변경 감지 신호 연결
        viewBox = self.plot_widget.getViewBox()
        viewBox.sigRangeChanged.connect(self.on_range_changed)
        
        self.info_label = QLabel("Waiting for data...")
        layout.addWidget(self.info_label)
        
        self.region = pg.LinearRegionItem([-1, 1])
        self.plot_widget.addItem(self.region)
        self.region.sigRegionChangeFinished.connect(self.update_measurements)
        
        self.trigger_level_line = pg.InfiniteLine(pos=0, angle=0, movable=True, pen=pg.mkPen('y', style=Qt.DashLine))
        self.plot_widget.addItem(self.trigger_level_line)
        self.trigger_level_line.sigPositionChanged.connect(self.on_trigger_level_dragged)
        
        self.trigger_pos_line = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pg.mkPen('r', style=Qt.DashLine))
        self.plot_widget.addItem(self.trigger_pos_line)
        self.trigger_pos_line.sigPositionChanged.connect(self.on_trigger_pos_dragged)
        
        self.trigger_text = pg.TextItem(text="", color=(255, 255, 0), anchor=(0, 0))
        self.plot_widget.addItem(self.trigger_text)
        
        # ✅ 마우스 위치 마커 (작은 사각형) - 마우스가 가리키는 포인트 표시
        self.mouse_marker = pg.ScatterPlotItem(
            size=10,  # 사각형 크기
            brush=pg.mkBrush(color=(255, 255, 0, 200)),  # 노란색 반투명
            pen=pg.mkPen(color=(255, 255, 255), width=2),  # 흰색 테두리
            symbol='s'  # 's' = square (사각형)
        )
        self.plot_widget.addItem(self.mouse_marker)
        
        # ✅ 마우스 위치 표시 (QLabel - 화면 좌표 기반, 범례처럼 고정)
        self.mouse_position_label = QLabel()
        self.mouse_position_label.setParent(self.plot_widget)
        self.mouse_position_label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(0, 0, 0, 200);
                color: #00FFFF;
                padding: 5px 8px;
                border: 1px solid #00FFFF;
                border-radius: 3px;
                font-family: monospace;
                font-size: 11px;
            }}
        """)
        self.mouse_position_label.setAlignment(Qt.AlignRight)
        self.mouse_position_label.setText("")
        self.mouse_position_label.show()
        
        self.measure_group = QGroupBox("Measurements")
        #self.measure_group.setMinimumHeight(250)
        measure_layout = QVBoxLayout(self.measure_group)
        
        #measure_layout.setSpacing(2)                    # 라벨 간격 통일
        #measure_layout.setContentsMargins(3, 3, 3, 3)  # 마진 설정
        
        self.measure_labels = []
        for i in range(9):
            lbl = QLabel()
            lbl.setWordWrap(True)
            lbl.setVisible(self.active_channels[i])
            #lbl.setMinimumHeight(16)  # ✅ 최소 높이 설정
            lbl.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['CHANNELS'][i]};
                    font-size: {COLORS['MEASUREMENT_FONT_SIZE']}px;
                    font-weight: normal;
                    padding: 0px;
                    margin: 0px;
                    background-color: transparent;
                }}
            """)
            #print(f"CH{i+1} label font-size set to {COLORS['MEASUREMENT_FONT_SIZE']}px")
            measure_layout.addWidget(lbl)
            self.measure_labels.append(lbl)
        layout.addWidget(self.measure_group)
        
        # 렌더링 타이머 추가
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self.render_plots)
        # 설정에서 렌더링 주기 가져오기 (기본값 33ms)
        #render_interval = 33  
        render_interval = 66  
        self.render_timer.start(render_interval)  # ~30Hz
        
        # ✅ 마우스 이동 신호 연결
        self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_moved)
        
        
        # ✅ 마우스 위치 라벨 우상단 고정 (크기는 자동 조정)
        # render_plots에서 매 프레임마다 위치만 업데이트
    
    def on_trigger_level_dragged(self, line):
        new_level = line.value()
        self.trigger_level_changed.emit(new_level)
    
    def on_trigger_pos_dragged(self, line):
        if self._updating:
            return
        self._updating = True
        new_pos = line.value()
        shift = new_pos
        self.display_time = [t - shift for t in self.display_time]
        current_min, current_max = self.plot_widget.getAxis('bottom').range
        self.plot_widget.setXRange(current_min - shift, current_max - shift, padding=0)
        line.setValue(0)
        self.pre_time = max(-current_min, 0.01)
        self.post_time = max(current_max, 0.01)
        self.total_time = self.pre_time + self.post_time
        self.render_plots()
        ########
        print(f"Trigger point and zero point moved by shift: {shift}, new pre_time: {self.pre_time}, post_time: {self.post_time}")
        self._updating = False
    
    def update_trigger_display(self):
        if self.trigger_settings is None or self.trigger_mode == "auto":
            self.trigger_level_line.setVisible(False)
            self.trigger_pos_line.setVisible(False)
            self.trigger_text.setVisible(False)
            return
        level = self.trigger_settings["level"]
        trig_type = self.trigger_settings["type"]
        source = self.trigger_settings["source"]
        self.trigger_level_line.setValue(level)
        self.trigger_level_line.setVisible(True)
        if self.triggered:
            self.trigger_pos_line.setValue(0)
            self.trigger_pos_line.setVisible(True)
            if self.display_time:
                min_time = min(self.display_time)
                max_time = max(self.display_time)
                self.trigger_pos_line.setBounds([min_time, max_time])
        else:
            self.trigger_pos_line.setVisible(False)
        text = f"Trigger: {trig_type.upper()} at {level:.2f} on CH{source+1}"
        self.trigger_text.setText(text)
        self.trigger_text.setPos(0, 
                               level + 0.1 * (max(self.display_channel_data[source]) - min(self.display_channel_data[source])) 
                               if self.display_channel_data[source] else 0)
        self.trigger_text.setVisible(True)
    
    def set_measurement_mode(self, mode):
        self.measurement_mode = mode
        if mode == "fixed":
            current_range = self.region.getRegion()
            self.fixed_measurement_range = current_range
        else:
            self.fixed_measurement_range = None
    
    def reset_measurement_region(self):
        # 현재 보이는 X축 범위 가져오기 (화면 중앙 기준으로 재설정)
        current_min, current_max = self.plot_widget.getAxis('bottom').range
        if current_max - current_min <= 0:  # 유효하지 않은 범위면 기본값
            self.region.setRegion([-1, 1])
            return
        
        # 화면 중앙 계산
        center = (current_min + current_max) / 2
        half_width = (current_max - current_min) * 0.1  # 현재 뷰의 20% 폭
        new_range = [center - half_width, center + half_width]
        
        # region 이동
        self.region.setRegion(new_range)
        
        # fixed 모드라면 범위 저장
        if self.measurement_mode == "fixed":
            self.fixed_measurement_range = new_range
        
        # 디버그 로그 (필요 시 제거)
        #print(f"Reset region to screen center: {new_range}")
    
    def snap_to_peak(self, channel_idx):
        if (not self.active_channels[channel_idx] or 
            not self.display_channel_data[channel_idx] or
            len(self.display_channel_data[channel_idx]) == 0):
            return
        try:
            data = np.asarray(self.display_channel_data[channel_idx])  # np.array -> np.asarray
            time = np.asarray(self.display_time)  # np.array -> np.asarray
            if len(data) == 0 or len(time) == 0:
                return
            peak_idx = np.argmax(data)
            peak_time = time[peak_idx]
            time_span = max(time) - min(time)
            half_width = max(time_span * 0.05, 0.1)
            new_range = [peak_time - half_width, peak_time + half_width]
            self.region.setRegion(new_range)
            if self.measurement_mode == "fixed":
                self.fixed_measurement_range = new_range
        except Exception as e:
            print(f"Error in snap_to_peak: {e}")
    
    def adjust_measurement_region(self):
        if not self.display_time or len(self.display_time) == 0:
            return
        try:
            current_time_range = [min(self.display_time), max(self.display_time)]
            if self.measurement_mode == "floating":
                if self.last_time_range is None:
                    time_span = current_time_range[1] - current_time_range[0]
                    if time_span > 0:
                        new_end = current_time_range[1]
                        new_start = new_end - (time_span * 0.2)
                        self.region.setRegion([new_start, new_end])
                elif (self.last_time_range and 
                      len(self.last_time_range) == 2 and 
                      current_time_range != self.last_time_range):
                    if self.last_time_range[1] != current_time_range[1]:
                        current_region = self.region.getRegion()
                        time_shift = current_time_range[1] - self.last_time_range[1]
                        new_region = [current_region[0] + time_shift, current_region[1] + time_shift]
                        self.region.setRegion(new_region)
            elif self.measurement_mode == "fixed" and self.fixed_measurement_range:
                self.region.setRegion(self.fixed_measurement_range)
            self.last_time_range = current_time_range.copy()
        except Exception as e:
            print(f"Error in adjust_measurement_region: {e}")
    
    def update_channels(self, data_array, timestamp):
        """채널 데이터 업데이트 - 고정 간격 적용"""
        try:
            # 고정 간격으로 relative_time 계산 (timestamp 무시)
            relative_time = self.sample_count * self.sample_interval
            self.sample_count += 1

            if self.trigger_settings is None:
                # 비트리거 모드: 기본 버퍼 관리
                while self.time_data and relative_time - self.time_data[0] > self.total_time:
                    self.time_data.popleft()
                    for i in range(9):
                        if len(self.channel_data[i]) > 0:
                            self.channel_data[i].popleft()
                self.time_data.append(relative_time)
                for i in range(9):
                    self.channel_data[i].append(data_array[i])
                self.display_time = list(self.time_data)
                for i in range(9):
                    self.display_channel_data[i] = list(self.channel_data[i])
                # ✅ 자동 추적일 때만 측정 region 조정
                if self.auto_follow_time:
                    self.adjust_measurement_region()
                self.update_trigger_display()
                if self.display_time:
                    max_time = max(self.display_time)
                    # ✅ 자동 추적 활성화되어 있을 때만 범위 설정
                    if self.auto_follow_time:
                        self.plot_widget.setXRange(max_time - self.total_time, max_time, padding=0)
                        #display_end = max_time + self.sample_interval  # 9.95 + 0.05 = 10.00
                        #self.plot_widget.setXRange(display_end - self.total_time, display_end, padding=0)
            else:
                # 트리거 모드: pre/post 버퍼에 고정 간격 적용
                if not self.acquiring:
                    return
                
                # pre 버퍼: 고정 간격 pre_relative_time
                pre_relative_time = self.pre_sample_count * self.sample_interval
                self.pre_sample_count += 1
                
                while self.pre_time_data and pre_relative_time - self.pre_time_data[0] > self.pre_time:
                    self.pre_time_data.popleft()
                    for i in range(9):
                        if len(self.pre_channel_data[i]) > 0:
                            self.pre_channel_data[i].popleft()
                self.pre_time_data.append(pre_relative_time)
                for i in range(9):
                    self.pre_channel_data[i].append(data_array[i])
                
                trig_type = self.trigger_settings["type"]
                level = self.trigger_settings["level"]
                
                if self.trigger_mode == "auto" and pre_relative_time - self.last_sweep_time > 0.05 and not self.triggered:
                    self.triggered = True
                    self.display_time = list(self.pre_time_data)
                    for i in range(9):
                        self.display_channel_data[i] = list(self.pre_channel_data[i])
                    self.last_sweep_time = pre_relative_time
                    print(f"Auto trigger occurred at time: {pre_relative_time}, value: {data_array[self.trigger_settings['source']]}")
                
                if not self.triggered:
                    if len(self.pre_time_data) < 2:
                        return
                    source = self.trigger_settings["source"]
                    if len(self.pre_channel_data[source]) >= 2:
                        value = self.pre_channel_data[source][-1]
                        prev_value = self.pre_channel_data[source][-2]
                        triggered = False
                        if trig_type == "rising" and prev_value <= level and value > level:
                            triggered = True
                        elif trig_type == "falling" and prev_value >= level and value < level:
                            triggered = True
                        elif trig_type == "level" and value > level:
                            triggered = True
                        if triggered:
                            self.triggered = True
                            self.display_time = list(self.pre_time_data)
                            for i in range(9):
                                self.display_channel_data[i] = list(self.pre_channel_data[i])
                            print(f"Trigger occurred at time: {pre_relative_time}, value: {value}, type: {trig_type}")
                
                if self.triggered:
                    # post 버퍼: 트리거 후에도 고정 간격 추가
                    post_relative_time = self.sample_count * self.sample_interval  # 전체 카운터 사용
                    self.display_time.append(post_relative_time)
                    for i in range(9):
                        self.display_channel_data[i].append(data_array[i])
                    if post_relative_time >= self.post_time:
                        self.render_plots()
                        self.plot_widget.setXRange(-self.pre_time, self.post_time, padding=0)
                        self.last_sweep_time = post_relative_time
                        if self.trigger_mode == "single":
                            self.acquiring = False
                            self.stop_acquisition_signal.emit()
                            print(f"Single mode stopped, maintaining pre_time: {self.pre_time}, post_time: {self.post_time}")
                        self.triggered = False
            
            active_count = sum(self.active_channels)
            self.info_label.setText(
                f"Active Channels: {active_count}/9 | "
                f"Buffer: {len(self.time_data)}/{self.buffer_size} | "
                f"Mode: {self.display_mode.upper()} | "
                f"Measure: {self.measurement_mode.upper()} | "
                f"Pre/Post: {self.pre_time:.2f}/{self.post_time:.2f}s"
            )
        except Exception as e:
            print(f"Error in update_channels: {e}")
    
    def update_plots(self):
        """플롯 업데이트"""
        try:
            for i in range(9):
                if self.active_channels[i] and self.display_time and len(self.display_time) > 0:
                    if len(self.display_channel_data[i]) == len(self.display_time):
                        self.plot_lines[i].setData(self.display_time, self.display_channel_data[i])
                    else:
                        self.plot_lines[i].setData([], [])
                else:
                    self.plot_lines[i].setData([], [])
        except Exception as e:
            print(f"Error in update_plots: {e}")
    
    def update_measurements(self):
        """측정값 업데이트"""
        try:
            minX, maxX = self.region.getRegion()
            if not self.display_time or len(self.display_time) == 0:
                return
            time_array = np.asarray(self.display_time)
            for i in range(9):
                if not self.active_channels[i]:
                    continue
                if (not self.display_channel_data[i] or 
                    len(self.display_channel_data[i]) == 0 or
                    len(self.display_channel_data[i]) != len(time_array)):
                    self.measure_labels[i].setText(f"CH{i+1}: No data")
                    continue
                data_array = np.asarray(self.display_channel_data[i])
                mask = (time_array >= minX) & (time_array <= maxX)
                if np.sum(mask) < 1:
                    self.measure_labels[i].setText(f"CH{i+1}: No data in range")
                    continue
                selected_time = time_array[mask]
                selected_data = data_array[mask]
                if len(selected_data) == 0:
                    self.measure_labels[i].setText(f"CH{i+1}: No data in range")
                    continue
                min_val = np.min(selected_data)
                max_val = np.max(selected_data)
                mean_val = np.mean(selected_data)
                p2p = max_val - min_val
                rms = np.sqrt(np.mean(selected_data**2))
                delta_t = selected_time[-1] - selected_time[0] if len(selected_time) > 1 else 0
                #delta_t = delta_t + 0.05
                
                #############
                # 데이터 처리 타이머 설정
                interval_ms = 0.05  # 기본값
                try:
                    if hasattr(self, 'settings_manager'):
                        dc = self.settings_manager.settings.get("data_collection", {})
                        interval_ms = dc.get("status_interval_ms", 50) / 1000
                except:
                    pass
                delta_t = delta_t + interval_ms
                #############
                
                n_points = len(selected_time)
                text = f"CH{i+1}: Min={min_val:9.3f}  Max={max_val:9.3f}  Mean={mean_val:9.3f}  P-P={p2p:9.3f}  RMS={rms:9.3f} {self.channel_units[i]}  Δt={delta_t:5.2f}s, ΔPoints={n_points}"
                self.measure_labels[i].setText(text)
        except Exception as e:
            print(f"Error in update_measurements: {e}")
    
    def render_plots(self):
        """플롯과 측정값 렌더링"""
        try:
            self.update_plots()
            self.update_measurements()
            
            # ✅ X축 단위 자동 업데이트
            self.update_x_axis_unit()
            
            # ✅ 마우스 위치 라벨 우상단 고정 (매 프레임 위치만 업데이트)
            plot_widget_width = self.plot_widget.width()
            plot_widget_height = self.plot_widget.height()
            label_width = self.mouse_position_label.sizeHint().width()
            label_height = self.mouse_position_label.sizeHint().height()
            
            # 우상단에 10px 여유로 배치
            x_pos = plot_widget_width - label_width - 10
            y_pos = 10
            
            self.mouse_position_label.setGeometry(x_pos, y_pos, label_width + 10, label_height + 5)
        except Exception as e:
            print(f"Error in render_plots: {e}")
    
    def set_channel_active(self, channel_idx, active):
        try:
            self.active_channels[channel_idx] = active
            self.plot_lines[channel_idx].setVisible(active)
            self.measure_labels[channel_idx].setVisible(active)
            self.measure_labels[channel_idx].setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['CHANNELS'][channel_idx]};
                    font-size: {COLORS['MEASUREMENT_FONT_SIZE']}px;
                    font-weight: normal;
                    padding: 0px;
                    margin: 0px;
                    background-color: transparent;
                }}
            """)
            name = f"CH{channel_idx+1}: {self.channel_names[channel_idx]}"
            if active:
                self.legend.addItem(self.plot_lines[channel_idx], name)
            else:
                self.legend.removeItem(name)
        except Exception as e:
            print(f"Error in set_channel_active: {e}")
    
    def set_display_mode(self, mode):
        self.display_mode = mode
    
    def clear_data(self):
        try:
            self.time_data.clear()
            for channel in self.channel_data:
                channel.clear()
            self.pre_time_data.clear()
            for channel in self.pre_channel_data:
                channel.clear()
            self.display_time = []
            for i in range(9):
                self.display_channel_data[i] = []
            self.pre_time = self.total_time / 2
            self.post_time = self.total_time / 2
            self.sample_count = 0
            self.pre_sample_count = 0
            self.render_plots()
            self.region.setRegion([-1, 1])
            self.fixed_measurement_range = None
            self.last_time_range = None
            self.mouse_marker.clear()  # ✅ 마커도 초기화
        except Exception as e:
            print(f"Error in clear_data: {e}")
    
    def update_x_axis_unit(self):
        """
        현재 X축 범위에 따라 자동으로 단위 변경
        ms (밀리초), s (초), min (분), h (시간)
        """
        try:
            # 현재 X축 범위 가져오기
            viewBox = self.plot_widget.getViewBox()
            x_range = viewBox.viewRange()[0]
            time_span = abs(x_range[1] - x_range[0])  # 초 단위
            
            # 시간 범위에 따라 단위 결정
            new_unit = None
            new_scale = 1.0
            
            if time_span < 1.0:  # 1초 미만 -> 밀리초
                new_unit = 'ms'
                new_scale = 1000.0
            elif time_span < 60.0:  # 1초 ~ 60초 -> 초
                new_unit = 's'
                new_scale = 1.0
            elif time_span < 3600.0:  # 60초 ~ 3600초 (1시간) -> 분
                new_unit = 'min'
                new_scale = 1.0 / 60.0
            else:  # 3600초 이상 -> 시간
                new_unit = 'h'
                new_scale = 1.0 / 3600.0
            
            # 단위가 변경되었으면 업데이트
            if new_unit != self.current_x_unit:
                self.current_x_unit = new_unit
                self.x_scale_factor = new_scale
                
                # ✅ 커스텀 축에 단위 설정
                self.time_axis.set_unit(new_unit, new_scale)
                
                # X축 레이블 업데이트 (SI 접두사 비활성화)
                self.plot_widget.setLabel('bottom', 'Time', units=new_unit, color=COLORS['TEXT'], enableUnitPrefix=False)
                
                # 축 강제 업데이트
                self.time_axis.picture = None
                self.time_axis.update()
                
                # 디버그 출력
                #print(f"[X-Axis Unit] Changed to '{new_unit}' (span: {time_span:.2f}s, scale: {new_scale})")
        
        except Exception as e:
            print(f"Error in update_x_axis_unit: {e}")

    def stop_acquisition(self):
        self.acquiring = False
        self.stop_acquisition_signal.emit()

    # ✅ 범위 변경 감지 메서드
    def on_range_changed(self, vb, ranges):
        """
        뷰박스 범위가 변경되었을 때 호출
        사용자가 마우스로 조정했으면 auto_follow_time = False
        """
        try:
            # ✅ Auto Range 중이면 무시 ← 추가
            if hasattr(self, 'is_auto_ranging') and self.is_auto_ranging:
                return
            
            # ✅ X축 단위 자동 업데이트
            self.update_x_axis_unit()
                
            xRange = vb.getState()['viewRange'][0]
            
            if self.time_data:
                max_time = self.time_data[-1]
                expected_end = max_time
                
                # 사용자가 범위를 수동으로 조정했으면
                # 예상 범위와 1초 이상 차이 = 수동 조정
                if abs(xRange[1] - expected_end) > 1:
                    self.manual_range_mode = True
                    self.auto_follow_time = False
                    #print(f"[Manual Range] 수동 조정 모드 활성화")
        except Exception as e:
            pass
    
    # ✅ 마우스 위치 추적 메서드
    def on_mouse_moved(self, pos):
        """마우스 이동시 현재 위치의 X, Y 값 표시 및 마커 위치 업데이트"""
        try:
            from PyQt5.QtCore import QPointF
            
            # 마우스 화면 좌표를 플롯 데이터 좌표로 변환
            viewBox = self.plot_widget.getViewBox()
            
            # 마우스 위치가 PlotWidget 내부인지 확인
            mouse_point = viewBox.mapSceneToView(pos)
            x_time = mouse_point.x()
            y_mouse = mouse_point.y()  # 마우스가 가리키는 Y좌표 (데이터 공간)
            
            # X, Y가 유효한 범위인지 확인
            if not self.display_time or len(self.display_time) == 0:
                self.mouse_position_label.setText("")
                self.mouse_marker.clear()  # ✅ 마커 제거
                return
            
            time_min = min(self.display_time)
            time_max = max(self.display_time)
            
            # X범위 벗어나면 표시 안 함
            if x_time < time_min or x_time > time_max:
                self.mouse_position_label.setText("")
                self.mouse_marker.clear()  # ✅ 마커 제거
                return
            
            # ========================================
            # 마우스 시간과 가장 가까운 시간 찾기
            # ========================================
            closest_time_idx = 0
            min_time_diff = abs(self.display_time[0] - x_time)
            
            for time_idx, time_val in enumerate(self.display_time):
                time_diff = abs(time_val - x_time)
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_time_idx = time_idx
            
            # ========================================
            # 가장 가까운 채널의 Y값 찾기
            # ========================================
            closest_distance = float('inf')
            closest_value = None
            closest_channel = -1
            closest_actual_y = None  # 실제 데이터 포인트 Y값
            closest_time = None  # 찾은 포인트의 시간값
            
            for ch_idx in range(9):
                if not self.active_channels[ch_idx]:
                    continue
                
                if not self.display_channel_data[ch_idx] or len(self.display_channel_data[ch_idx]) == 0:
                    continue
                
                # ========================================
                # 방식 1: 실제 데이터 포인트 사용 (더 정확)
                # ========================================
                actual_y = self.display_channel_data[ch_idx][closest_time_idx]
                distance = abs(actual_y - y_mouse)
                
                if distance < closest_distance:
                    closest_distance = distance
                    closest_value = actual_y
                    closest_actual_y = actual_y
                    closest_channel = ch_idx
                    closest_time = self.display_time[closest_time_idx]  # ✅ 시간값 저장
            
            # 마우스 위치 텍스트 업데이트 및 마커 위치 업데이트
            if closest_channel >= 0 and closest_value is not None:
                # 채널 단위 가져오기
                unit = self.channel_units[closest_channel] if closest_channel < len(self.channel_units) else ""
                
                # X축 시간값 - 현재 단위로 변환
                if self.current_x_unit == 'ms':
                    # 밀리초
                    x_value = x_time * self.x_scale_factor
                    x_text = f"{x_value:.1f}{self.current_x_unit}"
                    
                elif self.current_x_unit == 's':
                    # 초
                    x_value = x_time * self.x_scale_factor
                    x_text = f"{x_value:.2f}{self.current_x_unit}"
                    
                elif self.current_x_unit == 'min':
                    # 분:초 형식 (3:20)
                    total_seconds = abs(x_time)
                    minutes = int(total_seconds // 60)
                    seconds = int(total_seconds % 60)
                    if x_time < 0:
                        x_text = f"-{minutes}:{seconds:02d}"
                    else:
                        x_text = f"{minutes}:{seconds:02d}"
                        
                else:  # 'h'
                    # 시:분 형식 (1:30)
                    total_seconds = abs(x_time)
                    hours = int(total_seconds // 3600)
                    remaining_seconds = total_seconds % 3600
                    minutes = int(remaining_seconds // 60)
                    if x_time < 0:
                        x_text = f"-{hours}:{minutes:02d}"
                    else:
                        x_text = f"{hours}:{minutes:02d}"
                
                # Y축 값 (단위 포함) - 실제 데이터 포인트 값 사용
                y_text = f"{closest_value:.4f}{unit}"
                
                # 채널 이름
                ch_name = self.channel_names[closest_channel] if closest_channel < len(self.channel_names) else f"CH{closest_channel+1}"
                
                # 최종 표시 텍스트 (QLabel용 - 줄바꿈 포함)
                text = f"X: {x_text}\nY: {y_text}\n({ch_name})"
                self.mouse_position_label.setText(text)
                
                # ✅ 마커 위치 업데이트: 찾은 포인트에 작은 사각형 표시
                self.mouse_marker.setData(
                    x=[closest_time],  # 시간값 (X좌표)
                    y=[closest_value]  # Y값 (Y좌표)
                )
            else:
                self.mouse_position_label.setText("")
                self.mouse_marker.clear()  # ✅ 값을 찾지 못하면 마커 제거
        
        except Exception as e:
            self.mouse_position_label.setText("")
            self.mouse_marker.clear()  # ✅ 에러 발생시 마커 제거
            print(f"[ERROR] on_mouse_moved: {e}")

class OscilloscopeView(QWidget):
    """오실로스코프 뷰 메인 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.rf_running = False
        
        # ========================================
        # ✅ Status용 변수들
        # ========================================
        self.status_data_queue = deque(maxlen=100)
        self.status_batch_size = 10
        # 설정에서 가져오기 (없으면 기본값 50ms)
        self.status_update_interval = 50  # 기본값
        try:
            if parent and hasattr(parent, 'parent_window'):
                if hasattr(parent.parent_window, 'settings_manager'):
                    settings = parent.parent_window.settings_manager.settings
                    if "data_collection" in settings:
                        self.status_update_interval = settings["data_collection"].get("status_interval_ms", 50)
        except:
            pass  # 설정 로드 실패 시 기본값 사용
        
        # ========================================
        # ✅ ADC/DAC용 변수들
        # ========================================
        self.adc_data_queue = deque(maxlen=50)
        self.adc_batch_size = 5
        self.adc_update_interval = 100  # ms
        
        # ========================================
        # 데이터 소스 모드
        # ========================================
        self.data_source_mode = "status"  # "status" or "adc_dac"
        
        # ========================================
        # Status 데이터 소스
        # ========================================
        self.status_source = StatusDataSource()
        self.status_source.data_ready.connect(self.on_status_data_ready)
        
        # ========================================
        # ADC/DAC 데이터 소스
        # ========================================
        self.adc_dac_source = None
        
        # ========================================
        # UI 및 타이머 초기화
        # ========================================
        self.init_ui()
        self.setup_connections()
        
        # ========================================
        # ✅ Status용 타이머
        # ========================================
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.process_status_batch)
        
        # ========================================
        # ✅ ADC/DAC용 타이머
        # ========================================
        self.adc_timer = QTimer(self)
        self.adc_timer.timeout.connect(self.process_adc_batch)
        
        # ========================================
        # ✅ Run 버튼 깜빡임 타이머
        # ========================================
        self.run_blink_timer = QTimer(self)
        self.run_blink_timer.timeout.connect(self._toggle_run_button_color)
        self.run_blink_state = False  # 깜빡임 상태

    # ========================================
    # ✅ Status 데이터 수신
    # ========================================
    def on_status_data_ready(self, status_data, timestamp):
        """Status 데이터 수신"""
        if not self.rf_running or self.data_source_mode != "status":
            return
        
        self.status_data_queue.append(('status', status_data, timestamp))
        
        if len(self.status_data_queue) > 80:
            print(f"[WARNING] Status queue high: {len(self.status_data_queue)}")

    # ========================================
    # ✅ ADC/DAC 소스 초기화
    # ========================================
    def initialize_adc_dac_source(self):
        """ADC/DAC 소스 초기화"""
        try:
            if hasattr(self.parent_window, 'parent_window'):
                main_window = self.parent_window.parent_window
                if hasattr(main_window, 'network_manager'):
                    self.adc_dac_source = AdcDacDataSource(
                        main_window.network_manager,
                        interval_ms=100
                    )
                    self.adc_dac_source.data_ready.connect(self.on_adc_dac_data_ready)
                    #print("[Oscilloscope] ADC/DAC source initialized with 100ms interval")
        except Exception as e:
            print(f"[Oscilloscope] ADC/DAC source init failed: {e}")
    
    # ========================================
    # ✅ ADC/DAC 데이터 수신
    # ========================================
    def on_adc_dac_data_ready(self, adc_dac_values, timestamp):
        """ADC/DAC 데이터 수신"""
        if not self.rf_running or self.data_source_mode != "adc_dac":
            return
        
        self.adc_data_queue.append(('adc_dac', adc_dac_values, timestamp))
        
        if len(self.adc_data_queue) > 40:
            print(f"[WARNING] ADC queue high: {len(self.adc_data_queue)}")
    
    # ========================================
    # ✅ Status 배치 처리
    # ========================================
    def process_status_batch(self):
        """Status 데이터 배치 처리"""
        if not self.status_data_queue:
            return
        
        try:
            process_count = min(self.status_batch_size, len(self.status_data_queue))
            
            for _ in range(process_count):
                data_item = self.status_data_queue.popleft()
                
                if len(data_item) == 3:
                    data_type, status_data, timestamp = data_item
                    
                    channel_data = [
                        status_data.get("forward_power", 0),
                        status_data.get("reflect_power", 0),
                        status_data.get("delivery_power", 0),
                        status_data.get("frequency", 0),
                        status_data.get("gamma", 0),
                        status_data.get("real_gamma", 0),
                        status_data.get("image_gamma", 0),
                        status_data.get("rf_phase", 0),
                        status_data.get("temperature", 0)
                    ]
                    
                    self.plot_widget.update_channels(channel_data, timestamp)
                    
        except Exception as e:
            print(f"[ERROR] process_status_batch: {e}")
            import traceback
            traceback.print_exc()
            
    # ========================================
    # ✅ ADC/DAC 배치 처리
    # ========================================
    def process_adc_batch(self):
        """ADC/DAC 데이터 배치 처리"""
        if not self.adc_data_queue:
            return
        
        try:
            process_count = min(self.adc_batch_size, len(self.adc_data_queue))
            
            for _ in range(process_count):
                data_item = self.adc_data_queue.popleft()
                
                if len(data_item) == 3:
                    data_type, adc_values, timestamp = data_item
                    
                    channel_data = list(adc_values) + [0]
                    
                    self.plot_widget.update_channels(channel_data, timestamp)
                    
        except Exception as e:
            print(f"[ERROR] process_adc_batch: {e}")
            import traceback
            traceback.print_exc()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        control_panel = self.create_control_panel()
        control_panel.setFixedWidth(COLORS['MAX_LEFT_PENEL_WIDTH'])
        control_panel.setFixedHeight(COLORS['RF_CONTROL_HEIGHT'] + 
                                     COLORS['CHANNEL_GRID_HEIGHT'] + 
                                     COLORS['TIMEBASE_HEIGHT'] + 
                                     COLORS['TRIGGER_HEIGHT'] + 
                                     COLORS['MEASUREMENT_HEIGHT'] + 
                                     COLORS['CONTROLS_HEIGHT'] + 79)
                                     
        layout.addWidget(control_panel)
        self.plot_widget = UnifiedPlotWidget()
        layout.addWidget(self.plot_widget, 1)
        self.apply_styles()
    
    def create_control_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        rf_group = QGroupBox("RF Control")
        rf_group.setFixedSize(280, 130)
        rf_layout = QVBoxLayout(rf_group)
        rf_layout.setContentsMargins(10, 10, 10, 10)
        rf_layout.setSpacing(5)

        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Data Source:"))

        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["Status Data", "ADC Raw"])
        self.data_source_combo.currentIndexChanged.connect(self.on_data_source_changed)

        source_layout.addWidget(self.data_source_combo)
        rf_layout.addLayout(source_layout)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.run_btn = QPushButton("RUN")
        self.stop_btn = QPushButton("STOP")
        self.run_btn.setFixedHeight(40)
        self.stop_btn.setFixedHeight(40)
        self.run_btn.clicked.connect(self.start_acquisition)
        self.stop_btn.clicked.connect(self.stop_acquisition)

        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.stop_btn)
        rf_layout.addLayout(button_layout)

        layout.addWidget(rf_group)
        
        self.channel_grid = ChannelGridWidget()
        layout.addWidget(self.channel_grid)
        
        self.timebase_widget = TimebaseWidget()
        layout.addWidget(self.timebase_widget)
        
        self.trigger_widget = TriggerWidget(self.channel_grid.channel_names)
        layout.addWidget(self.trigger_widget)
        
        self.measurement_control = MeasurementControlWidget(self.channel_grid.channel_names)
        layout.addWidget(self.measurement_control)
        
        controls_group = QGroupBox("Controls")
        controls_group.setFixedSize(COLORS['CONTROLS_WIDTH'], COLORS['CONTROLS_HEIGHT'])
        controls_layout = QVBoxLayout(controls_group)
        controls_layout.setContentsMargins(10, 1, 10, 1)
        controls_layout.setSpacing(10)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        clear_btn = QPushButton("Clear Data")
        clear_btn.clicked.connect(self.clear_data)

        auto_range_btn = QPushButton("Auto Range")
        auto_range_btn.clicked.connect(self.auto_range)

        button_layout.addWidget(clear_btn)
        button_layout.addWidget(auto_range_btn)
        controls_layout.addLayout(button_layout)
        
        layout.addWidget(controls_group)
        
        layout.addStretch()
        return panel
    
    def on_data_source_changed(self, index):
        """데이터 소스 변경"""
        was_running = self.rf_running
        
        if self.rf_running:
            self.stop_acquisition()
        
        if index == 0:  # Status Data
            self.data_source_mode = "status"
            #print("[Oscilloscope] Switched to Status Data mode")
            #print(f"  - Update interval: {self.status_update_interval}ms")
            #print(f"  - Batch size: {self.status_batch_size}")
            
            self.update_channel_names_for_status()
            
        else:  # ADC/DAC Raw
            self.data_source_mode = "adc_dac"
            #print("[Oscilloscope] Switched to ADC/DAC mode")
            #print(f"  - Update interval: {self.adc_update_interval}ms")
            #print(f"  - Batch size: {self.adc_batch_size}")
            
            if self.adc_dac_source is None:
                self.initialize_adc_dac_source()
            
            self.update_channel_names_for_adc()
        
        if was_running:
            self.start_acquisition()
    
    # def auto_range(self):
        # """플롯 자동 범위 조정 및 자동 추적 재개"""
        # viewBox = self.plot_widget.plot_widget.getViewBox()
        # viewBox.autoRange()
        
        # # ✅ 자동 추적 재개
        # self.plot_widget.auto_follow_time = True
        # self.plot_widget.manual_range_mode = False
        # #print("[Auto Range] 자동 추적 재개")
    
    def auto_range(self):
        """플롯 자동 범위 조정 및 자동 추적 재개"""
        try:
            viewBox = self.plot_widget.plot_widget.getViewBox()
            
            # ✅ 범위 조정 중임을 표시
            self.plot_widget.is_auto_ranging = True
            
            # 자동 범위 조정
            viewBox.autoRange()
            
            # ✅ 자동 추적 재개
            self.plot_widget.auto_follow_time = True
            self.plot_widget.manual_range_mode = False
            
            # ✅ 범위 조정 완료
            self.plot_widget.is_auto_ranging = False
            
            #print("[Auto Range] 자동 범위 조정 완료 + 자동 추적 재개")
        except Exception as e:
            print(f"[ERROR] auto_range: {e}")
            self.plot_widget.is_auto_ranging = False
    
    def setup_connections(self):
        self.channel_grid.channel_changed.connect(self.on_channel_changed)
        self.timebase_widget.timebase_changed.connect(self.on_timebase_changed)
        self.timebase_widget.custom_timebase_changed.connect(self.on_custom_timebase_changed)
        self.trigger_widget.trigger_changed.connect(self.on_trigger_changed)
        self.measurement_control.measurement_mode_changed.connect(self.plot_widget.set_measurement_mode)
        self.measurement_control.reset_measurement.connect(self.plot_widget.reset_measurement_region)
        self.measurement_control.snap_to_peak.connect(self.plot_widget.snap_to_peak)
        self.plot_widget.trigger_level_changed.connect(self.on_trigger_level_dragged)
        self.plot_widget.stop_acquisition_signal.connect(self.stop_acquisition)
    
    def on_trigger_level_dragged(self, new_level):
        self.trigger_widget.level_spin.setValue(new_level)
    
    def apply_styles(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['BACKGROUND']};
                color: {COLORS['TEXT']};
                font-family: {SELECTED_FONT};
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {COLORS['GROUPBOX_BORDER']};
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: {COLORS['GROUPBOX_TITLE']};
                background-color: {COLORS['BACKGROUND']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            QPushButton {{
                background-color: {COLORS['BUTTON_BG']};
                border: 2px solid {COLORS['BUTTON_BORDER']};
                color: {COLORS['BUTTON_TEXT']};
                padding: 6px;
                border-radius: 3px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {COLORS['BUTTON_HOVER_BORDER']};
                background-color: {COLORS['BUTTON_HOVER_BG']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['BUTTON_CHECKED_BG']};
                border-color: {COLORS['BUTTON_CHECKED_BORDER']};
            }}
            QLabel {{
                color: {COLORS['LABEL_TEXT']};
                font-size: 15px;
            }}
            QComboBox {{
                background-color: {COLORS['BUTTON_BG']};
                border: 1px solid {COLORS['BUTTON_BORDER']};
                border-radius: 3px;
                padding: 2px 5px;
                color: {COLORS['TEXT']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {COLORS['TEXT']};
            }}
            QDoubleSpinBox {{
                background-color: {COLORS['BUTTON_BG']};
                border: 1px solid {COLORS['BUTTON_BORDER']};
                border-radius: 3px;
                padding: 2px 5px;
                color: {COLORS['TEXT']};
            }}
        """)
        self.run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['RUN_BUTTON_BG']};
                border: 2px solid {COLORS['RUN_BUTTON_BORDER']};
                color: {COLORS['TEXT']};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['RUN_BUTTON_HOVER']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['RUN_BUTTON_PRESSED']};
            }}
            QPushButton:disabled {{
                background-color: #333333;
                color: #666666;
                border-color: #555555;
            }}
        """)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['STOP_BUTTON_BG']};
                border: 2px solid {COLORS['STOP_BUTTON_BORDER']};
                color: {COLORS['TEXT']};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['STOP_BUTTON_HOVER']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['STOP_BUTTON_PRESSED']};
            }}
            QPushButton:disabled {{
                background-color: #333333;
                color: #666666;
                border-color: #555555;
            }}
        """)
    
    def on_channel_changed(self, channel_idx, enabled):
        self.plot_widget.set_channel_active(channel_idx, enabled)
    
    def on_timebase_changed(self, timebase):
        """버튼 선택시 호출"""
        try:
            tb_sec = self.parse_timebase(timebase)
            new_total = 10 * tb_sec
            # 공용 메서드로 버퍼와 타임베이스 함께 업데이트
            self._update_buffer_and_timebase(new_total)
        except Exception as e:
            print(f"Error in on_timebase_changed: {e}")
    
    def on_custom_timebase_changed(self, minutes):
        """
        사용자 정의 타임베이스 변경
        minutes: 분 단위 (0.5 ~ 1440)
        """
        try:
            total_seconds = minutes * 60
            # 공용 메서드로 버퍼와 타임베이스 함께 업데이트
            self._update_buffer_and_timebase(total_seconds, is_custom=True, custom_minutes=minutes)
        except Exception as e:
            print(f"Error in on_custom_timebase_changed: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_buffer_and_timebase(self, total_seconds, is_custom=False, custom_minutes=0):
        """
        버퍼와 타임베이스를 함께 업데이트
        total_seconds: 표시할 총 시간 (초)
        is_custom: 커스텀 입력 여부
        custom_minutes: 커스텀 입력 값 (분)
        """
        try:
            # 1️⃣ 기존 비율 유지
            old_ratio = (self.plot_widget.pre_time / self.plot_widget.total_time 
                        if self.plot_widget.total_time > 0 else 0.5)
            
            # 2️⃣ total_time 업데이트
            self.plot_widget.total_time = total_seconds
            self.plot_widget.pre_time = old_ratio * self.plot_widget.total_time
            self.plot_widget.post_time = self.plot_widget.total_time - self.plot_widget.pre_time
            
            # 3️⃣ 필요한 샘플 개수 계산
            required_samples = int((total_seconds / self.plot_widget.sample_interval) + 100)
            
            # 4️⃣ 기존 데이터 백업
            old_time_data = list(self.plot_widget.time_data)
            old_channel_data = [list(self.plot_widget.channel_data[i]) for i in range(9)]
            old_pre_time_data = list(self.plot_widget.pre_time_data)
            old_pre_channel_data = [list(self.plot_widget.pre_channel_data[i]) for i in range(9)]
            
            # 5️⃣ 새로운 버퍼 크기로 deque 재생성
            self.plot_widget.buffer_size = max(required_samples, 1000)
            self.plot_widget.time_data = deque(maxlen=self.plot_widget.buffer_size)
            self.plot_widget.channel_data = [deque(maxlen=self.plot_widget.buffer_size) for _ in range(9)]
            self.plot_widget.pre_time_data = deque(maxlen=self.plot_widget.buffer_size)
            self.plot_widget.pre_channel_data = [deque(maxlen=self.plot_widget.buffer_size) for _ in range(9)]
            
            # 6️⃣ 이전 데이터 복원
            for t in old_time_data[-self.plot_widget.buffer_size:]:
                self.plot_widget.time_data.append(t)
            for i in range(9):
                for val in old_channel_data[i][-self.plot_widget.buffer_size:]:
                    self.plot_widget.channel_data[i].append(val)
            for t in old_pre_time_data[-self.plot_widget.buffer_size:]:
                self.plot_widget.pre_time_data.append(t)
            for i in range(9):
                for val in old_pre_channel_data[i][-self.plot_widget.buffer_size:]:
                    self.plot_widget.pre_channel_data[i].append(val)
            
            # 7️⃣ 플롯 범위 업데이트
            if len(self.plot_widget.time_data) > 0:
                current_time = self.plot_widget.time_data[-1]
                self.plot_widget.plot_widget.setXRange(
                    current_time - self.plot_widget.total_time, 
                    current_time, 
                    padding=0
                )
            elif self.plot_widget.trigger_settings:
                self.plot_widget.plot_widget.setXRange(
                    -self.plot_widget.pre_time, 
                    self.plot_widget.post_time, 
                    padding=0
                )
            
            # 8️⃣ 디버그 로그
            # if is_custom:
                # print(f"[Custom Timebase] {custom_minutes:.1f}min = {total_seconds:.0f}s, "
                      # f"Buffer: {self.plot_widget.buffer_size} samples, "
                      # f"Pre: {self.plot_widget.pre_time:.2f}s, "
                      # f"Post: {self.plot_widget.post_time:.2f}s")
            # else:
                # print(f"[Button Timebase] {total_seconds:.0f}s, "
                      # f"Buffer: {self.plot_widget.buffer_size} samples, "
                      # f"Pre: {self.plot_widget.pre_time:.2f}s, "
                      # f"Post: {self.plot_widget.post_time:.2f}s")
            
        except Exception as e:
            print(f"Error in _update_buffer_and_timebase: {e}")
            import traceback
            traceback.print_exc()
    
    def parse_timebase(self, timebase):
        try:
            if 'ms' in timebase:
                return float(timebase.replace('ms', '')) / 1000
            elif 's' in timebase:
                return float(timebase.replace('s', ''))
            elif 'm' in timebase:
                return float(timebase.replace('m', '')) * 60
            return 1.0
        except:
            return 1.0
    
    def on_trigger_changed(self, settings):
        try:
            if settings["mode"] == "auto":
                self.plot_widget.trigger_settings = None
                self.plot_widget.trigger_mode = "auto"
                self.plot_widget.clear_data()
                if self.rf_running:
                    self.plot_widget.acquiring = True
            else:
                self.plot_widget.trigger_settings = settings
                self.plot_widget.trigger_mode = settings["mode"]
                self.plot_widget.triggered = False
                self.plot_widget.last_sweep_time = 0
                if self.rf_running:
                    self.plot_widget.acquiring = True
            self.plot_widget.update_trigger_display()
        except Exception as e:
            print(f"Error in on_trigger_changed: {e}")
    
    def start_acquisition(self):
        """데이터 수집 시작"""
        try:
            self.rf_running = True
            self.plot_widget.acquiring = True
            self.plot_widget.triggered = False
            self.plot_widget.last_sweep_time = 0
            self.run_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            # ✅ Run 버튼 깜빡임 시작
            self.start_run_button_blink()
            
            self.plot_widget.sample_count = 0
            self.plot_widget.pre_sample_count = 0
            
            if self.data_source_mode == "status":
                self.status_data_queue.clear()
                self.status_timer.start(self.status_update_interval)
                #print(f"[Oscilloscope] Status acquisition started ({self.status_update_interval}ms)")
                
            else:  # adc_dac
                self.adc_data_queue.clear()
                
                if self.adc_dac_source:
                    self.adc_dac_source.start()
                    self.adc_timer.start(self.adc_update_interval)
                    #print(f"[Oscilloscope] ADC/DAC acquisition started ({self.adc_update_interval}ms)")
                else:
                    #print("[ERROR] ADC/DAC source not initialized!")
                    self.stop_acquisition()
                    return
                    
        except Exception as e:
            print(f"[ERROR] start_acquisition: {e}")
    
    # ========================================
    # ✅ Run 버튼 깜빡임 메서드들
    # ========================================
    def _toggle_run_button_color(self):
        """Run 버튼 색상 깜빡임"""
        if not self.run_btn:
            return
        
        self.run_blink_state = not self.run_blink_state
        
        if self.run_blink_state:
            # 밝은 인디고
            self.run_btn.setStyleSheet("""
                QPushButton {
                    background-color: #818cf8;
                    color: #ffffff;
                    font-weight: bold;
                    border: 2px solid #a5b4fc;
                    padding: 6px;
                    border-radius: 3px;
                    font-size: 12px;
                }
            """)
        else:
            # 어두운 인디고
            self.run_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6366f1;
                    color: #ffffff;
                    font-weight: bold;
                    border: 2px solid #4f46e5;
                    padding: 6px;
                    border-radius: 3px;
                    font-size: 12px;
                }
            """)
    
    def start_run_button_blink(self):
        """Run 버튼 깜빡임 시작 (1초 간격)"""
        if not self.run_blink_timer.isActive():
            self.run_blink_state = True
            self.run_blink_timer.start(1000)  # 1000ms = 1초
    
    def stop_run_button_blink(self):
        """Run 버튼 깜빡임 중지"""
        if self.run_blink_timer.isActive():
            self.run_blink_timer.stop()
        # 기본 스타일로 복원
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: #ffffff;
                font-weight: bold;
                border: 2px solid #4f46e5;
                padding: 6px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #818cf8;
                border: 2px solid #a5b4fc;
            }
        """)
    
    def stop_acquisition(self):
        """데이터 수집 중지"""
        try:
            self.rf_running = False
            self.plot_widget.acquiring = False
            self.run_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
            # ✅ Run 버튼 깜빡임 중지
            self.stop_run_button_blink()
            
            if self.status_timer.isActive():
                self.status_timer.stop()
                self.status_data_queue.clear()
                #print("[Oscilloscope] Status acquisition stopped")
            
            if self.adc_timer.isActive():
                self.adc_timer.stop()
                self.adc_data_queue.clear()
                #print("[Oscilloscope] ADC/DAC acquisition stopped")
            
            if self.adc_dac_source:
                self.adc_dac_source.stop()
                
        except Exception as e:
            print(f"[ERROR] stop_acquisition: {e}")
    
    def clear_data(self):
        """데이터 클리어"""
        self.plot_widget.clear_data()
        self.status_data_queue.clear()
        self.adc_data_queue.clear()
        print("[Oscilloscope] All data cleared")
    
    def update_channel_names_for_status(self):
        """Status 모드 채널 이름으로 변경"""
        status_names = [
            "Fwd Pwr", "Ref Pwr", "Del Pwr", "Frequency", 
            "Gamma", "R Gamma", "I Gamma", "RF Phase", "Temp"
        ]
        
        status_full_names = [
            "Forward Power", "Reflect Power", "Delivery Power", "Frequency", 
            "Gamma", "Real Gamma", "Image Gamma", "RF Phase", "Temperature"
        ]
        
        status_units = [
            "W", "W", "W", "MHz", "", "", "", "°", "°C"
        ]
        
        for i, btn in enumerate(self.channel_grid.buttons):
            btn.setText(f"CH{i+1}\n{status_names[i]}")
        
        self.plot_widget.channel_names = status_full_names
        self.plot_widget.channel_units = status_units
        
        self.plot_widget.legend.clear()
        for i in range(9):
            if self.plot_widget.active_channels[i]:
                self.plot_widget.legend.addItem(
                    self.plot_widget.plot_lines[i], 
                    f"CH{i+1}: {status_full_names[i]}"
                )
        
        self.trigger_widget.source_combo.clear()
        self.trigger_widget.source_combo.addItems(status_names)
        
        self.measurement_control.snap_combo.clear()
        self.measurement_control.snap_combo.addItems([f"CH{i+1}" for i in range(9)])
        
        print("[Oscilloscope] Channel names updated for Status mode")
    
    def update_channel_names_for_adc(self):
        """ADC/DAC 모드 채널 이름으로 변경"""
        adc_names = [
            "ADC 0", "ADC 1", "ADC 2", "ADC 3", 
            "ADC 4", "ADC 5", "ADC 6", "ADC 7", "Reserved"
        ]
        
        adc_full_names = [
            "ADC Channel 0", "ADC Channel 1", "ADC Channel 2", "ADC Channel 3", 
            "ADC Channel 4", "ADC Channel 5", "ADC Channel 6", "ADC Channel 7", 
            "Reserved"
        ]
        
        adc_units = [
            "LSB", "LSB", "LSB", "LSB", 
            "LSB", "LSB", "LSB", "LSB", "-"
        ]
        
        for i, btn in enumerate(self.channel_grid.buttons):
            btn.setText(f"CH{i+1}\n{adc_names[i]}")
        
        self.plot_widget.channel_names = adc_full_names
        self.plot_widget.channel_units = adc_units
        
        self.plot_widget.legend.clear()
        for i in range(9):
            if self.plot_widget.active_channels[i]:
                self.plot_widget.legend.addItem(
                    self.plot_widget.plot_lines[i], 
                    f"CH{i+1}: {adc_full_names[i]}"
                )
        
        self.trigger_widget.source_combo.clear()
        self.trigger_widget.source_combo.addItems(adc_names)
        
        self.measurement_control.snap_combo.clear()
        self.measurement_control.snap_combo.addItems([f"CH{i+1}" for i in range(9)])
        
        #print("[Oscilloscope] Channel names updated for ADC/DAC mode")
    
    def update_data(self, status_data):
        """외부에서 호출되는 Status 데이터 업데이트"""
        if not self.rf_running or self.data_source_mode != "status":
            return
        
        try:
            timestamp = time.time()
            self.status_data_queue.append(('status', status_data, timestamp))
        except Exception as e:
            print(f"[ERROR] update_data: {e}")