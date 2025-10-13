"""
Settings Dialog Module
GUI 설정 다이얼로그 - 범위, 색상, 임계값, 게이지 설정 등
"""

import json
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QFormLayout,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox,
    QScrollArea, QLabel, QMessageBox, QColorDialog, QCheckBox, QSlider
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPalette


class ColorButton(QPushButton):
    """색상 선택 버튼"""
    
    color_changed = pyqtSignal(str)  # 색상 변경 시그널
    
    def __init__(self, color="#ffffff", parent=None):
        super().__init__(parent)
        self.current_color = color
        self.setFixedSize(40, 30)
        self.clicked.connect(self.choose_color)
        self.update_style()
    
    def choose_color(self):
        """색상 선택 다이얼로그"""
        color = QColorDialog.getColor(QColor(self.current_color), self)
        if color.isValid():
            self.current_color = color.name()
            self.update_style()
            self.color_changed.emit(self.current_color)
    
    def set_color(self, color):
        """색상 설정"""
        self.current_color = color
        self.update_style()
    
    def get_color(self):
        """현재 색상 반환"""
        return self.current_color
    
    def update_style(self):
        """버튼 스타일 업데이트"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color};
                border: 2px solid #666666;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #00f0ff;
            }}
        """)


class SettingsDialog(QDialog):
    """GUI 설정 다이얼로그"""
    
    settings_applied = pyqtSignal(dict)  # 설정 적용 시그널
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.settings = self.load_default_settings()
        
        # 기존 설정이 있다면 로드
        self.load_settings()
        
        self.init_ui()
        self.load_values_to_ui()
    
    def load_default_settings(self):
        """기본 설정값 로드"""
        return {
            # 색상 설정
            "colors": {
                "graph_max": "#00f0ff",      # Forward Power
                "graph_min": "#ff0000",      # Reflect Power  
                "graph_delivery": "#ff9900", # Delivery Power
                "graph_avg": "#00ff00",      # Frequency
                "graph_volt": "#ffff00",     # Gamma
                "graph_real_gamma": "#33ccff",   # Real Gamma
                "graph_image_gamma": "#cc33ff",  # Image Gamma
                "graph_phase": "#ff3333",    # RF Phase
                "graph_temp": "#ff00ff"      # Temperature
            },
            
            # 게이지 범위 설정
            "gauge_ranges": {
                "forward_power": {"min": 0, "max": 3000, "unit": "W"},
                "reflect_power": {"min": 0, "max": 300, "unit": "W"},
                "delivery_power": {"min": 0, "max": 3000, "unit": "W"},
                "frequency": {"min": 0, "max": 30, "unit": "MHz"},
                "gamma": {"min": 0, "max": 1, "unit": ""},
                "real_gamma": {"min": 0, "max": 1, "unit": ""},
                "image_gamma": {"min": 0, "max": 1, "unit": ""},
                "rf_phase": {"min": 0, "max": 360, "unit": "°"},
                "temperature": {"min": 20, "max": 80, "unit": "°C"}
            },
            
            # 임계값 설정
            "thresholds": {
                "forward_power": {
                    "caution": 400.0,
                    "warning": 700.0,
                    "error": 1000.0
                },
                "reflect_power": {
                    "warning": 20.0,
                    "error": 50.0
                },
                "temperature": {
                    "low": 20.0,
                    "warning": 50.0,
                    "error": 70.0
                }
            },
            
            # 플롯 설정
            "plot_settings": {
                "max_points": 10000,
                "update_interval": 30,
                "line_width": 2,
                "antialiasing": True,
                "grid_alpha": 0.3,
                "auto_range": True
            },
            
            # 상태 모니터 설정
            "status_monitor": {
                "alarm_blink_duration": 2000,
                "temperature_precision": 1,
                "power_precision": 2,
                "frequency_precision": 2
            }
        }
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("GUI 설정")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        
        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        
        # 각 탭 생성
        self.create_colors_tab()
        self.create_gauge_ranges_tab()
        self.create_thresholds_tab()
        self.create_plot_settings_tab()
        self.create_status_monitor_tab()
        
        main_layout.addWidget(self.tab_widget)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 기본값 복원 버튼
        reset_btn = QPushButton("기본값 복원")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        # 취소/적용 버튼
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("적용")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_btn)
        
        main_layout.addLayout(button_layout)
        
        # 스타일 적용
        self.apply_styles()
    
    def create_colors_tab(self):
        """색상 설정 탭"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 색상 설정 그룹
        colors_group = QGroupBox("그래프 색상 설정")
        colors_layout = QFormLayout(colors_group)
        
        self.color_buttons = {}
        color_labels = [
            ("graph_max", "Forward Power", "순방향 전력"),
            ("graph_min", "Reflect Power", "반사 전력"),
            ("graph_delivery", "Delivery Power", "전달 전력"),
            ("graph_avg", "Frequency", "주파수"),
            ("graph_volt", "Gamma", "감마"),
            ("graph_real_gamma", "Real Gamma", "실수 감마"),
            ("graph_image_gamma", "Image Gamma", "허수 감마"),
            ("graph_phase", "RF Phase", "RF 위상"),
            ("graph_temp", "Temperature", "온도")
        ]
        
        for key, eng_name, kor_name in color_labels:
            color_btn = ColorButton(self.settings["colors"][key])
            color_btn.color_changed.connect(
                lambda color, k=key: self.update_color_setting(k, color)
            )
            self.color_buttons[key] = color_btn
            
            label = QLabel(f"{kor_name} ({eng_name}):")
            label.setStyleSheet("color: #4169e1; font-weight: bold;")
            colors_layout.addRow(label, color_btn)
        
        layout.addWidget(colors_group)
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        self.tab_widget.addTab(tab, "색상")
    
    def create_gauge_ranges_tab(self):
        """게이지 범위 설정 탭"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 게이지 범위 설정 그룹
        gauge_group = QGroupBox("게이지 범위 설정")
        gauge_layout = QFormLayout(gauge_group)
        
        self.gauge_inputs = {}
        gauge_labels = [
            ("forward_power", "Forward Power", "순방향 전력"),
            ("reflect_power", "Reflect Power", "반사 전력"),
            ("delivery_power", "Delivery Power", "전달 전력"),
            ("frequency", "Frequency", "주파수"),
            ("gamma", "Gamma", "감마"),
            ("real_gamma", "Real Gamma", "실수 감마"),
            ("image_gamma", "Image Gamma", "허수 감마"),
            ("rf_phase", "RF Phase", "RF 위상"),
            ("temperature", "Temperature", "온도")
        ]
        
        for key, eng_name, kor_name in gauge_labels:
            range_data = self.settings["gauge_ranges"][key]
            
            # 최소값 입력
            min_input = QDoubleSpinBox()
            min_input.setRange(-9999, 9999)
            min_input.setValue(range_data["min"])
            
            # 최대값 입력
            max_input = QDoubleSpinBox()
            max_input.setRange(-9999, 9999)
            max_input.setValue(range_data["max"])
            
            # 단위 라벨
            unit_label = QLabel(range_data["unit"])
            
            # 레이아웃
            range_layout = QHBoxLayout()
            range_layout.addWidget(QLabel("최소:"))
            range_layout.addWidget(min_input)
            range_layout.addWidget(QLabel("최대:"))
            range_layout.addWidget(max_input)
            range_layout.addWidget(unit_label)
            range_layout.addStretch()
            
            range_widget = QWidget()
            range_widget.setLayout(range_layout)
            
            self.gauge_inputs[key] = {"min": min_input, "max": max_input}
            
            label = QLabel(f"{kor_name} ({eng_name}):")
            label.setStyleSheet("color: #4169e1; font-weight: bold;")
            gauge_layout.addRow(label, range_widget)
        
        layout.addWidget(gauge_group)
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        self.tab_widget.addTab(tab, "게이지 범위")
    
    def create_thresholds_tab(self):
        """임계값 설정 탭"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # Forward Power 임계값
        fwd_group = QGroupBox("Forward Power 임계값")
        fwd_layout = QFormLayout(fwd_group)
        
        self.fwd_caution = QDoubleSpinBox()
        self.fwd_caution.setRange(0, 9999)
        self.fwd_caution.setSuffix(" W")
        self.fwd_caution.setValue(self.settings["thresholds"]["forward_power"]["caution"])
        
        self.fwd_warning = QDoubleSpinBox()
        self.fwd_warning.setRange(0, 9999)
        self.fwd_warning.setSuffix(" W")
        self.fwd_warning.setValue(self.settings["thresholds"]["forward_power"]["warning"])
        
        self.fwd_error = QDoubleSpinBox()
        self.fwd_error.setRange(0, 9999)
        self.fwd_error.setSuffix(" W")
        self.fwd_error.setValue(self.settings["thresholds"]["forward_power"]["error"])
        
        fwd_layout.addRow("주의 (노란색):", self.fwd_caution)
        fwd_layout.addRow("경고 (주황색):", self.fwd_warning)
        fwd_layout.addRow("오류 (빨간색):", self.fwd_error)
        
        layout.addWidget(fwd_group)
        
        # Reflect Power 임계값
        ref_group = QGroupBox("Reflect Power 임계값")
        ref_layout = QFormLayout(ref_group)
        
        self.ref_warning = QDoubleSpinBox()
        self.ref_warning.setRange(0, 9999)
        self.ref_warning.setSuffix(" W")
        self.ref_warning.setValue(self.settings["thresholds"]["reflect_power"]["warning"])
        
        self.ref_error = QDoubleSpinBox()
        self.ref_error.setRange(0, 9999)
        self.ref_error.setSuffix(" W")
        self.ref_error.setValue(self.settings["thresholds"]["reflect_power"]["error"])
        
        ref_layout.addRow("경고 (주황색):", self.ref_warning)
        ref_layout.addRow("오류 (빨간색):", self.ref_error)
        
        layout.addWidget(ref_group)
        
        # Temperature 임계값
        temp_group = QGroupBox("Temperature 임계값")
        temp_layout = QFormLayout(temp_group)
        
        self.temp_low = QDoubleSpinBox()
        self.temp_low.setRange(-50, 200)
        self.temp_low.setSuffix(" °C")
        self.temp_low.setValue(self.settings["thresholds"]["temperature"]["low"])
        
        self.temp_warning = QDoubleSpinBox()
        self.temp_warning.setRange(-50, 200)
        self.temp_warning.setSuffix(" °C")
        self.temp_warning.setValue(self.settings["thresholds"]["temperature"]["warning"])
        
        self.temp_error = QDoubleSpinBox()
        self.temp_error.setRange(-50, 200)
        self.temp_error.setSuffix(" °C")
        self.temp_error.setValue(self.settings["thresholds"]["temperature"]["error"])
        
        temp_layout.addRow("저온 (파란색):", self.temp_low)
        temp_layout.addRow("경고 (주황색):", self.temp_warning)
        temp_layout.addRow("오류 (빨간색):", self.temp_error)
        
        layout.addWidget(temp_group)
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        self.tab_widget.addTab(tab, "임계값")
    
    def create_plot_settings_tab(self):
        """플롯 설정 탭"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 플롯 성능 설정
        performance_group = QGroupBox("플롯 성능 설정")
        performance_layout = QFormLayout(performance_group)
        
        self.max_points = QSpinBox()
        self.max_points.setRange(1000, 100000)
        self.max_points.setValue(self.settings["plot_settings"]["max_points"])
        
        self.update_interval = QSpinBox()
        self.update_interval.setRange(10, 1000)
        self.update_interval.setSuffix(" ms")
        self.update_interval.setValue(self.settings["plot_settings"]["update_interval"])
        
        performance_layout.addRow("최대 데이터 포인트:", self.max_points)
        performance_layout.addRow("업데이트 간격:", self.update_interval)
        
        layout.addWidget(performance_group)
        
        # 플롯 외관 설정
        appearance_group = QGroupBox("플롯 외관 설정")
        appearance_layout = QFormLayout(appearance_group)
        
        self.line_width = QSpinBox()
        self.line_width.setRange(1, 10)
        self.line_width.setValue(self.settings["plot_settings"]["line_width"])
        
        self.antialiasing = QCheckBox()
        self.antialiasing.setChecked(self.settings["plot_settings"]["antialiasing"])
        
        self.grid_alpha = QSlider(Qt.Horizontal)
        self.grid_alpha.setRange(0, 100)
        self.grid_alpha.setValue(int(self.settings["plot_settings"]["grid_alpha"] * 100))
        self.grid_alpha_label = QLabel(f"{self.grid_alpha.value()}%")
        self.grid_alpha.valueChanged.connect(
            lambda v: self.grid_alpha_label.setText(f"{v}%")
        )
        
        grid_layout = QHBoxLayout()
        grid_layout.addWidget(self.grid_alpha)
        grid_layout.addWidget(self.grid_alpha_label)
        grid_widget = QWidget()
        grid_widget.setLayout(grid_layout)
        
        self.auto_range = QCheckBox()
        self.auto_range.setChecked(self.settings["plot_settings"]["auto_range"])
        
        appearance_layout.addRow("선 두께:", self.line_width)
        appearance_layout.addRow("안티앨리어싱:", self.antialiasing)
        appearance_layout.addRow("격자 투명도:", grid_widget)
        appearance_layout.addRow("자동 범위 조정:", self.auto_range)
        
        layout.addWidget(appearance_group)
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        self.tab_widget.addTab(tab, "플롯 설정")
    
    def create_status_monitor_tab(self):
        """상태 모니터 설정 탭"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # 상태 모니터 설정
        status_group = QGroupBox("상태 모니터 설정")
        status_layout = QFormLayout(status_group)
        
        self.alarm_blink_duration = QSpinBox()
        self.alarm_blink_duration.setRange(500, 10000)
        self.alarm_blink_duration.setSuffix(" ms")
        self.alarm_blink_duration.setValue(self.settings["status_monitor"]["alarm_blink_duration"])
        
        self.temp_precision = QSpinBox()
        self.temp_precision.setRange(0, 5)
        self.temp_precision.setValue(self.settings["status_monitor"]["temperature_precision"])
        
        self.power_precision = QSpinBox()
        self.power_precision.setRange(0, 5)
        self.power_precision.setValue(self.settings["status_monitor"]["power_precision"])
        
        self.freq_precision = QSpinBox()
        self.freq_precision.setRange(0, 5)
        self.freq_precision.setValue(self.settings["status_monitor"]["frequency_precision"])
        
        status_layout.addRow("알람 깜빡임 지속시간:", self.alarm_blink_duration)
        status_layout.addRow("온도 소수점 자리수:", self.temp_precision)
        status_layout.addRow("전력 소수점 자리수:", self.power_precision)
        status_layout.addRow("주파수 소수점 자리수:", self.freq_precision)
        
        layout.addWidget(status_group)
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        self.tab_widget.addTab(tab, "상태 모니터")
    
    def apply_styles(self):
        """다이얼로그 스타일 적용"""
        style_sheet = """
            QDialog {
                background-color: #2e2e3e;
                color: #e6e6fa;
                font-family: 'Roboto Mono', monospace;
            }
            QTabWidget::pane {
                border: 1px solid #00f0ff;
                background: #252535;
            }
            QTabBar::tab {
                background: #2e2e3e;
                color: #d0d0d0;
                padding: 8px 12px;
                margin-right: 2px;
                border: 1px solid #444;
            }
            QTabBar::tab:selected {
                background: #00f0ff;
                color: #1e1e2e;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background: #3a3a4a;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #00f0ff;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #f0f8ff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #87ceeb;
                font-size: 13px;
            }
            QLabel {
                color: #dcdcdc;
                font-size: 12px;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #2e2e3e;
                border: 1px solid #00f0ff;
                border-radius: 3px;
                padding: 4px;
                color: #e0ffff;
                min-height: 20px;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #00d4aa;
                background-color: #363646;
            }
            QPushButton {
                background-color: #3e3e4e;
                border: 1px solid #00f0ff;
                border-radius: 5px;
                padding: 6px 12px;
                color: #f5f5f5;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #00f0ff;
                color: #1e1e2e;
                border: 1px solid #00d4aa;
            }
            QPushButton:pressed {
                background-color: #00a0aa;
                color: #ffffff;
            }
            QPushButton:default {
                background-color: #006064;
                border: 2px solid #00f0ff;
                color: #ffffff;
            }
            QCheckBox {
                color: #dcdcdc;
                font-size: 11px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #00f0ff;
                border-radius: 3px;
                background: #2e2e3e;
            }
            QCheckBox::indicator:checked {
                background: #00f0ff;
                border: 1px solid #00d4aa;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #2e2e3e;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #00f0ff;
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #00d4aa;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #2e2e3e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #00f0ff;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00d4aa;
            }
        """
        self.setStyleSheet(style_sheet)
    
    def update_color_setting(self, key, color):
        """색상 설정 업데이트"""
        self.settings["colors"][key] = color
    
    def load_values_to_ui(self):
        """설정값을 UI에 로드"""
        # 색상은 이미 ColorButton 생성 시 설정됨
        pass
    
    def collect_settings_from_ui(self):
        """UI에서 설정값 수집"""
        # 게이지 범위 설정 수집
        for key, inputs in self.gauge_inputs.items():
            self.settings["gauge_ranges"][key]["min"] = inputs["min"].value()
            self.settings["gauge_ranges"][key]["max"] = inputs["max"].value()
        
        # 임계값 설정 수집
        self.settings["thresholds"]["forward_power"]["caution"] = self.fwd_caution.value()
        self.settings["thresholds"]["forward_power"]["warning"] = self.fwd_warning.value()
        self.settings["thresholds"]["forward_power"]["error"] = self.fwd_error.value()
        
        self.settings["thresholds"]["reflect_power"]["warning"] = self.ref_warning.value()
        self.settings["thresholds"]["reflect_power"]["error"] = self.ref_error.value()
        
        self.settings["thresholds"]["temperature"]["low"] = self.temp_low.value()
        self.settings["thresholds"]["temperature"]["warning"] = self.temp_warning.value()
        self.settings["thresholds"]["temperature"]["error"] = self.temp_error.value()
        
        # 플롯 설정 수집
        self.settings["plot_settings"]["max_points"] = self.max_points.value()
        self.settings["plot_settings"]["update_interval"] = self.update_interval.value()
        self.settings["plot_settings"]["line_width"] = self.line_width.value()
        self.settings["plot_settings"]["antialiasing"] = self.antialiasing.isChecked()
        self.settings["plot_settings"]["grid_alpha"] = self.grid_alpha.value() / 100.0
        self.settings["plot_settings"]["auto_range"] = self.auto_range.isChecked()
        
        # 상태 모니터 설정 수집
        self.settings["status_monitor"]["alarm_blink_duration"] = self.alarm_blink_duration.value()
        self.settings["status_monitor"]["temperature_precision"] = self.temp_precision.value()
        self.settings["status_monitor"]["power_precision"] = self.power_precision.value()
        self.settings["status_monitor"]["frequency_precision"] = self.freq_precision.value()
    
    def reset_to_defaults(self):
        """기본값으로 복원"""
        reply = QMessageBox.question(
            self, "기본값 복원", 
            "모든 설정을 기본값으로 복원하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.settings = self.load_default_settings()
            
            # UI 업데이트
            for key, color_btn in self.color_buttons.items():
                color_btn.set_color(self.settings["colors"][key])
            
            # 게이지 범위 업데이트
            for key, inputs in self.gauge_inputs.items():
                range_data = self.settings["gauge_ranges"][key]
                inputs["min"].setValue(range_data["min"])
                inputs["max"].setValue(range_data["max"])
            
            # 임계값 업데이트
            self.fwd_caution.setValue(self.settings["thresholds"]["forward_power"]["caution"])
            self.fwd_warning.setValue(self.settings["thresholds"]["forward_power"]["warning"])
            self.fwd_error.setValue(self.settings["thresholds"]["forward_power"]["error"])
            
            self.ref_warning.setValue(self.settings["thresholds"]["reflect_power"]["warning"])
            self.ref_error.setValue(self.settings["thresholds"]["reflect_power"]["error"])
            
            self.temp_low.setValue(self.settings["thresholds"]["temperature"]["low"])
            self.temp_warning.setValue(self.settings["thresholds"]["temperature"]["warning"])
            self.temp_error.setValue(self.settings["thresholds"]["temperature"]["error"])
            
            # 플롯 설정 업데이트
            self.max_points.setValue(self.settings["plot_settings"]["max_points"])
            self.update_interval.setValue(self.settings["plot_settings"]["update_interval"])
            self.line_width.setValue(self.settings["plot_settings"]["line_width"])
            self.antialiasing.setChecked(self.settings["plot_settings"]["antialiasing"])
            self.grid_alpha.setValue(int(self.settings["plot_settings"]["grid_alpha"] * 100))
            self.auto_range.setChecked(self.settings["plot_settings"]["auto_range"])
            
            # 상태 모니터 설정 업데이트
            self.alarm_blink_duration.setValue(self.settings["status_monitor"]["alarm_blink_duration"])
            self.temp_precision.setValue(self.settings["status_monitor"]["temperature_precision"])
            self.power_precision.setValue(self.settings["status_monitor"]["power_precision"])
            self.freq_precision.setValue(self.settings["status_monitor"]["frequency_precision"])
            
            QMessageBox.information(self, "복원 완료", "모든 설정이 기본값으로 복원되었습니다.")
    
    def apply_settings(self):
        """설정 적용"""
        # UI에서 설정값 수집
        self.collect_settings_from_ui()
        
        # 설정 유효성 검사
        if not self.validate_settings():
            return
        
        # 설정 저장
        self.save_settings()
        
        # 설정 적용 시그널 발생
        self.settings_applied.emit(self.settings)
        
        # 부모 윈도우에 로그 출력
        if hasattr(self.parent_window, 'log_manager'):
            self.parent_window.log_manager.write_log("[CONFIG] GUI 설정이 적용되었습니다.", "yellow")
        
        QMessageBox.information(self, "적용 완료", "설정이 성공적으로 적용되었습니다.")
        self.accept()
    
    def validate_settings(self):
        """설정값 유효성 검사"""
        # 게이지 범위 검사
        for key, range_data in self.settings["gauge_ranges"].items():
            if range_data["min"] >= range_data["max"]:
                QMessageBox.warning(
                    self, "설정 오류", 
                    f"{key}의 최소값이 최대값보다 크거나 같습니다."
                )
                return False
        
        # 임계값 검사 - Forward Power
        fwd_thresholds = self.settings["thresholds"]["forward_power"]
        if not (fwd_thresholds["caution"] <= fwd_thresholds["warning"] <= fwd_thresholds["error"]):
            QMessageBox.warning(
                self, "설정 오류", 
                "Forward Power 임계값은 주의 ≤ 경고 ≤ 오류 순서여야 합니다."
            )
            return False
        
        # 임계값 검사 - Reflect Power
        ref_thresholds = self.settings["thresholds"]["reflect_power"]
        if ref_thresholds["warning"] >= ref_thresholds["error"]:
            QMessageBox.warning(
                self, "설정 오류", 
                "Reflect Power 경고값이 오류값보다 크거나 같습니다."
            )
            return False
        
        # 임계값 검사 - Temperature
        temp_thresholds = self.settings["thresholds"]["temperature"]
        if not (temp_thresholds["low"] <= temp_thresholds["warning"] <= temp_thresholds["error"]):
            QMessageBox.warning(
                self, "설정 오류", 
                "Temperature 임계값은 저온 ≤ 경고 ≤ 오류 순서여야 합니다."
            )
            return False
        
        return True
    
    def save_settings(self):
        """설정 저장"""
        try:
            config_dir = "data"
            os.makedirs(config_dir, exist_ok=True)
            
            settings_file = os.path.join(config_dir, "gui_settings.json")
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", f"설정 저장에 실패했습니다: {e}")
            return False
    
    def load_settings(self):
        """저장된 설정 로드"""
        try:
            settings_file = os.path.join("data", "gui_settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                
                # 기본 설정과 병합 (새로운 설정 항목 추가 대응)
                self._merge_settings(loaded_settings)
                
                return True
        except Exception as e:
            if hasattr(self.parent_window, 'log_manager'):
                self.parent_window.log_manager.write_log(f"[WARNING] GUI 설정 로드 실패: {e}", "yellow")
            return False
    
    def _merge_settings(self, loaded_settings):
        """기본 설정과 로드된 설정 병합"""
        def merge_dict(default, loaded):
            """재귀적으로 딕셔너리 병합"""
            for key, value in loaded.items():
                if key in default:
                    if isinstance(default[key], dict) and isinstance(value, dict):
                        merge_dict(default[key], value)
                    else:
                        default[key] = value
        
        merge_dict(self.settings, loaded_settings)
    
    def get_settings(self):
        """현재 설정 반환"""
        return self.settings.copy()


class SettingsManager:
    """설정 관리자 클래스"""
    
    def __init__(self):
        self.settings = {}
        self.load_settings()
    
    def load_settings(self):
        """설정 로드"""
        try:
            settings_file = os.path.join("data", "gui_settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                return True
        except Exception:
            # 기본 설정 사용
            dialog = SettingsDialog()
            self.settings = dialog.load_default_settings()
            return False
    
    def get_color(self, key):
        """색상 설정 반환"""
        return self.settings.get("colors", {}).get(key, "#ffffff")
    
    def get_gauge_range(self, key):
        """게이지 범위 설정 반환"""
        return self.settings.get("gauge_ranges", {}).get(key, {"min": 0, "max": 100, "unit": ""})
    
    def get_threshold(self, category, level):
        """임계값 설정 반환"""
        return self.settings.get("thresholds", {}).get(category, {}).get(level, 0)
    
    def get_plot_setting(self, key):
        """플롯 설정 반환"""
        defaults = {
            "max_points": 10000,
            "update_interval": 30,
            "line_width": 2,
            "antialiasing": True,
            "grid_alpha": 0.3,
            "auto_range": True
        }
        return self.settings.get("plot_settings", {}).get(key, defaults.get(key))
    
    def get_status_monitor_setting(self, key):
        """상태 모니터 설정 반환"""
        defaults = {
            "alarm_blink_duration": 2000,
            "temperature_precision": 1,
            "power_precision": 2,
            "frequency_precision": 2
        }
        return self.settings.get("status_monitor", {}).get(key, defaults.get(key))
    
    def update_settings(self, new_settings):
        """설정 업데이트"""
        self.settings = new_settings
    
    def apply_to_main_window(self, main_window):
        """메인 윈도우에 설정 적용"""
        try:
            # 플롯 매니저 설정 적용
            if hasattr(main_window, 'plot_manager'):
                main_window.plot_manager.max_points = self.get_plot_setting("max_points")
            
            # 도크 매니저 설정 적용 (색상)
            if hasattr(main_window, 'dock_manager'):
                self._apply_dock_colors(main_window.dock_manager)
            
            # 게이지 설정 적용
            self._apply_gauge_settings(main_window)
            
            # 상태 모니터 설정 적용
            if hasattr(main_window, 'status_monitor_dialog') and main_window.status_monitor_dialog:
                self._apply_status_monitor_settings(main_window.status_monitor_dialog)
            
            # 로그 출력
            if hasattr(main_window, 'log_manager'):
                main_window.log_manager.write_log("[CONFIG] GUI 설정이 적용되었습니다.", "yellow")
                
        except Exception as e:
            if hasattr(main_window, 'log_manager'):
                main_window.log_manager.write_log(f"[ERROR] GUI 설정 적용 실패: {e}", "red")
    
    def _apply_dock_colors(self, dock_manager):
        """도크 매니저에 색상 설정 적용"""
        try:
            colors = self.settings.get("colors", {})
            color_keys = [
                "graph_max", "graph_min", "graph_delivery", "graph_avg", 
                "graph_volt", "graph_real_gamma", "graph_image_gamma", 
                "graph_phase", "graph_temp"
            ]
            
            for i, color_key in enumerate(color_keys):
                if i < len(dock_manager.plot_lines) and color_key in colors:
                    # 플롯 라인 색상 업데이트
                    import pyqtgraph as pg
                    dock_manager.plot_lines[i].setPen(
                        pg.mkPen(color=colors[color_key], width=self.get_plot_setting("line_width"))
                    )
        except Exception as e:
            print(f"색상 적용 오류: {e}")
    
    def _apply_gauge_settings(self, main_window):
        """게이지 설정 적용"""
        try:
            if not hasattr(main_window, 'dock_manager') or not main_window.dock_manager.gauges:
                return
            
            gauge_keys = [
                "forward_power", "reflect_power", "delivery_power", "frequency",
                "gamma", "real_gamma", "image_gamma", "rf_phase", "temperature"
            ]
            
            for i, gauge_key in enumerate(gauge_keys):
                if i < len(main_window.dock_manager.gauges):
                    gauge = main_window.dock_manager.gauges[i]
                    range_settings = self.get_gauge_range(gauge_key)
                    
                    # 게이지 범위 업데이트
                    gauge.min_value = range_settings["min"]
                    gauge.max_value = range_settings["max"]
                    gauge.update()  # 다시 그리기
                    
        except Exception as e:
            print(f"게이지 설정 적용 오류: {e}")
    
    def _apply_status_monitor_settings(self, status_monitor):
        """상태 모니터 설정 적용"""
        try:
            # 상태 모니터의 설정을 업데이트하는 로직
            # (status_monitor_dialog.py의 StatusThresholds 클래스를 업데이트)
            pass
        except Exception as e:
            print(f"상태 모니터 설정 적용 오류: {e}")