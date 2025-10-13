"""
Plot Analysis Module
오실로스코프 스타일의 플롯 분석 기능 - 시간 델타값 추가
"""

import numpy as np
from collections import deque
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QCheckBox, QGridLayout, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
import pyqtgraph as pg
from pyqtgraph import LinearRegionItem


class StatisticsCalculator:
    """통계 계산 클래스 - 시간 델타값 추가"""
    
    @staticmethod
    def calculate_statistics(data_points, time_points=None):
        """데이터 포인트들의 통계값 계산 (시간 델타값 포함)"""
        if not data_points or len(data_points) == 0:
            return None
            
        data_array = np.array(data_points)
        
        stats = {
            'count': len(data_points),
            'average': np.mean(data_array),
            'maximum': np.max(data_array),
            'minimum': np.min(data_array),
            'rms': np.sqrt(np.mean(data_array**2)),
            'std_dev': np.std(data_array),
            'peak_to_peak': np.max(data_array) - np.min(data_array),
            'median': np.median(data_array)
        }
        
        # 시간 정보가 있는 경우 - 시간 델타값 추가
        if time_points and len(time_points) == len(data_points) and len(time_points) > 1:
            time_array = np.array(time_points)
            
            # 기본 시간 통계
            stats['duration'] = time_array[-1] - time_array[0]
            stats['start_time'] = time_array[0]
            stats['end_time'] = time_array[-1]
            
            # 시간 델타값들 추가
            stats['delta_value'] = float(data_array[-1] - data_array[0])  # 시작-끝 값 변화량
            stats['delta_time'] = float(time_array[-1] - time_array[0])   # 시간 구간
            
            # 변화율 계산 (0으로 나누기 방지)
            if stats['delta_time'] > 0:
                stats['slope'] = stats['delta_value'] / stats['delta_time']  # 평균 기울기 (단위/초)
                stats['rate_per_sec'] = abs(stats['delta_value']) / stats['delta_time']  # 절대 변화율
            else:
                stats['slope'] = 0.0
                stats['rate_per_sec'] = 0.0
            
            # 순간 변화율 (연속된 점들 간의 변화율)
            if len(data_array) > 1:
                time_diffs = np.diff(time_array)
                value_diffs = np.diff(data_array)
                
                # 0으로 나누기 방지
                valid_indices = time_diffs > 0
                if np.any(valid_indices):
                    instant_rates = value_diffs[valid_indices] / time_diffs[valid_indices]
                    stats['max_rate'] = float(np.max(np.abs(instant_rates)))  # 최대 순간 변화율
                    stats['avg_rate'] = float(np.mean(np.abs(instant_rates)))  # 평균 순간 변화율
                else:
                    stats['max_rate'] = 0.0
                    stats['avg_rate'] = 0.0
            else:
                stats['max_rate'] = 0.0
                stats['avg_rate'] = 0.0
                
        else:
            # 시간 정보가 없는 경우 기본값
            stats['duration'] = 0
            stats['start_time'] = 0
            stats['end_time'] = 0
            stats['delta_value'] = 0.0
            stats['delta_time'] = 0.0
            stats['slope'] = 0.0
            stats['rate_per_sec'] = 0.0
            stats['max_rate'] = 0.0
            stats['avg_rate'] = 0.0
        
        return stats


class AnalysisRegionItem(LinearRegionItem):
    """커스텀 분석 영역 아이템"""
    
    region_changed = pyqtSignal(float, float)  # x1, x2 값 변경 시그널
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setBrush(pg.mkBrush(0, 240, 255, 50))  # 반투명 청록색
        self.setHoverBrush(pg.mkBrush(0, 240, 255, 80))
        self.sigRegionChanged.connect(self._on_region_changed)
        
    def _on_region_changed(self):
        """영역 변경 시 호출"""
        x1, x2 = self.getRegion()
        self.region_changed.emit(min(x1, x2), max(x1, x2))


class AdvancedStatisticsPanel(QWidget):
    """고급 통계 패널 (대형/플로팅용) - 시간 델타값 포함"""
    
    export_requested = pyqtSignal(dict)
    clear_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_stats = None
        self.current_x1 = 0
        self.current_x2 = 0
        self.current_unit = ""
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화 - 체크박스 제거, 구분선 유지"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # 범위 표시
        self.range_label = QLabel("Range: 데이터 없음")
        self.range_label.setStyleSheet("color: #1a1a1a; font-size: 14px; margin: 2px 0;")
        layout.addWidget(self.range_label)
        
        # 기본 통계 그룹 - 구분선 유지
        basic_group = QFrame()
        basic_group.setStyleSheet("QFrame { border: 1px solid #444444; border-radius: 3px; margin: 2px; }")
        basic_layout = QVBoxLayout(basic_group)
        basic_layout.setContentsMargins(5, 5, 5, 5)
        
        basic_title = QLabel("기본 통계")
        basic_title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 12px;")
        basic_layout.addWidget(basic_title)
        
        self.basic_stats_widget = QWidget()
        self.basic_stats_layout = QGridLayout(self.basic_stats_widget)
        self.basic_stats_layout.setContentsMargins(0, 0, 0, 0)
        self.basic_stats_layout.setSpacing(3)
        basic_layout.addWidget(self.basic_stats_widget)
        layout.addWidget(basic_group)
        
        # 시간 델타 통계 그룹 - 구분선 유지
        delta_group = QFrame()
        delta_group.setStyleSheet("QFrame { border: 1px solid #444444; border-radius: 3px; margin: 2px; }")
        delta_layout = QVBoxLayout(delta_group)
        delta_layout.setContentsMargins(5, 5, 5, 5)
        
        delta_title = QLabel("시간 델타")
        delta_title.setStyleSheet("color: #ffaa00; font-weight: bold; font-size: 12px;")
        delta_layout.addWidget(delta_title)
        
        self.delta_stats_widget = QWidget()
        self.delta_stats_layout = QGridLayout(self.delta_stats_widget)
        self.delta_stats_layout.setContentsMargins(0, 0, 0, 0)
        self.delta_stats_layout.setSpacing(3)
        delta_layout.addWidget(self.delta_stats_widget)
        layout.addWidget(delta_group)
        
        # 통계 라벨들 초기화
        self.stat_labels = {}
        self._create_stat_labels()
        
        # 버튼 그룹 (기존과 동일)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)
        
        self.export_btn = QPushButton("Export")
        self.clear_btn = QPushButton("Clear")
        self.snapshot_btn = QPushButton("Snapshot")
        
        for btn in [self.export_btn, self.clear_btn, self.snapshot_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3e3e4e;
                    border: 1px solid #00f0ff;
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: #ffffff;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #00f0ff;
                    color: #1e1e2e;
                }
            """)
            button_layout.addWidget(btn)
        
        self.export_btn.clicked.connect(self._on_export_clicked)
        self.clear_btn.clicked.connect(self.clear_requested.emit)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
    def _create_stat_labels(self):
        """통계 라벨들 생성"""
        # 기본 통계 라벨들
        basic_stats = [
            ('개수', 'count'), ('지속시간', 'duration'),
            ('평균', 'average'), ('최대', 'maximum'),
            ('최소', 'minimum'), ('RMS', 'rms'),
            ('P-P', 'peak_to_peak'), ('표준편차', 'std_dev')
        ]
        
        for i, (name, key) in enumerate(basic_stats):
            label = QLabel(f"{name}:")
            label.setStyleSheet("color: #FFFF1a; font-size: 13px;")
            value = QLabel("0.00")
            value.setStyleSheet("""
                color: #ffffff; 
                font-size: 13px; 
                font-weight: bold;
                background: #2a2a3a;
                border-left: 2px solid #00f0ff;
                padding: 2px 4px;
                border-radius: 2px;
            """)
            
            row, col = i // 2, (i % 2) * 2
            self.basic_stats_layout.addWidget(label, row, col)
            self.basic_stats_layout.addWidget(value, row, col + 1)
            self.stat_labels[key] = value
        
        # 시간 델타 통계 라벨들
        delta_stats = [
            ('값 변화', 'delta_value'), ('평균 기울기', 'slope'),
            ('변화율/초', 'rate_per_sec'), ('최대 순간변화율', 'max_rate'),
            ('평균 순간변화율', 'avg_rate')
        ]
        
        for i, (name, key) in enumerate(delta_stats):
            label = QLabel(f"{name}:")
            label.setStyleSheet("color: #FFFF1a; font-size: 13px;")
            value = QLabel("0.00")
            value.setStyleSheet("""
                color: #ffffff; 
                font-size: 13px; 
                font-weight: bold;
                background: #3a2a2a;
                border-left: 2px solid #ffaa00;
                padding: 2px 4px;
                border-radius: 2px;
            """)
            
            row, col = i // 2, (i % 2) * 2
            self.delta_stats_layout.addWidget(label, row, col)
            self.delta_stats_layout.addWidget(value, row, col + 1)
            self.stat_labels[key] = value
    
    def _on_export_clicked(self):
        """내보내기 버튼 클릭"""
        if self.current_stats:
            export_data = {
                'statistics': self.current_stats,
                'range': (self.current_x1, self.current_x2),
                'unit': self.current_unit
            }
            self.export_requested.emit(export_data)
    
    def update_statistics(self, stats, x1, x2, unit=""):
        """통계값 업데이트 - 체크박스 없이 항상 표시"""
        self.current_stats = stats
        self.current_x1 = x1
        self.current_x2 = x2
        self.current_unit = unit
        
        if stats and len(stats) > 0:  # enable_checkbox 체크 제거
            self.range_label.setText(f"Range: {x1:.2f}s → {x2:.2f}s")
            
            # 각 통계값 업데이트
            formats = {
                # 기본 통계
                'count': lambda x: f"{int(x)}",
                'duration': lambda x: f"{x:.2f}s",
                'average': lambda x: f"{x:.1f}{unit}",
                'maximum': lambda x: f"{x:.1f}{unit}",
                'minimum': lambda x: f"{x:.1f}{unit}",
                'rms': lambda x: f"{x:.1f}{unit}",
                'peak_to_peak': lambda x: f"{x:.1f}{unit}",
                'std_dev': lambda x: f"{x:.1f}{unit}",
                
                # 시간 델타 통계
                'delta_value': lambda x: f"{x:+.1f}{unit}",
                'slope': lambda x: f"{x:+.2f}{unit}/s",
                'rate_per_sec': lambda x: f"{x:.2f}{unit}/s",
                'max_rate': lambda x: f"{x:.2f}{unit}/s",
                'avg_rate': lambda x: f"{x:.2f}{unit}/s"
            }
            
            for key, formatter in formats.items():
                if key in stats and key in self.stat_labels:
                    self.stat_labels[key].setText(formatter(stats[key]))
                elif key in self.stat_labels:
                    # 기본값 표시 로직...
                    pass
        else:
            self.range_label.setText("Range: 데이터 없음")
            # 데이터가 없을 때 기본값 표시
            for key in self.stat_labels:
                if key == 'count':
                    self.stat_labels[key].setText("0")
                elif key == 'duration':
                    self.stat_labels[key].setText("0.00s")
                elif key in ['delta_value', 'slope']:
                    self.stat_labels[key].setText(f"+0.00{unit}" if key != 'slope' else f"+0.00{unit}/s")
                else:
                    self.stat_labels[key].setText(f"0.00{unit}" + ("/s" if "rate" in key or "slope" in key else ""))


class PlotAnalysisManager:
    """플롯 분석 관리자"""
    
    def __init__(self, plot_widget, plot_data, plot_time_data):
        self.plot_widget = plot_widget
        self.plot_data = plot_data  # deque 데이터
        self.plot_time_data = plot_time_data  # deque 시간 데이터
        
        self.analysis_region = None
        self.is_enabled = False
        
        # 통계 계산기
        self.calculator = StatisticsCalculator()
        
        # 업데이트 타이머 (성능 최적화)
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._calculate_statistics)
        
        self.statistics_callback = None  # 통계값 업데이트 콜백
        
    def enable_analysis(self, callback=None):
        """분석 기능 활성화"""
        if self.is_enabled:
            return
            
        self.is_enabled = True
        self.statistics_callback = callback
        
        # 분석 영역 생성
        self.analysis_region = AnalysisRegionItem()
        self.analysis_region.region_changed.connect(self._on_region_changed)
        
        # 초기 영역 설정 (전체 데이터의 중간 40% 영역)
        if len(self.plot_time_data) > 10:
            time_data = list(self.plot_time_data)
            start_time = time_data[0]
            end_time = time_data[-1]
            duration = end_time - start_time
            center = start_time + duration * 0.5
            region_width = duration * 0.4
            
            self.analysis_region.setRegion([
                center - region_width/2,
                center + region_width/2
            ])
        else:
            self.analysis_region.setRegion([0, 10])
            
        self.plot_widget.addItem(self.analysis_region)
        
        # 즉시 통계 계산하여 초기값 표시
        QTimer.singleShot(200, self._calculate_statistics)
    
    def disable_analysis(self):
        """분석 기능 비활성화"""
        if not self.is_enabled:
            return
            
        self.is_enabled = False
        
        if self.analysis_region:
            self.plot_widget.removeItem(self.analysis_region)
            self.analysis_region = None
            
        self.statistics_callback = None
        
    def _on_region_changed(self, x1, x2):
        """분석 영역 변경 시 호출"""
        if not self.is_enabled:
            return
            
        # 성능 최적화: 짧은 지연 후 계산
        self.update_timer.start(50)  # 50ms 지연
        
    def _calculate_statistics(self):
        """통계값 계산 및 콜백 호출"""
        if not self.is_enabled or not self.analysis_region or not self.statistics_callback:
            return
            
        x1, x2 = self.analysis_region.getRegion()
        
        # 선택된 범위의 데이터 추출
        time_list = list(self.plot_time_data)
        data_list = list(self.plot_data)
        
        if len(time_list) != len(data_list) or len(time_list) == 0:
            return
            
        # 범위 내 데이터 필터링
        selected_data = []
        selected_time = []
        
        for i, time_val in enumerate(time_list):
            if x1 <= time_val <= x2:
                selected_data.append(data_list[i])
                selected_time.append(time_val)
                
        if len(selected_data) == 0:
            return
            
        # 통계 계산 (시간 델타값 포함)
        stats = self.calculator.calculate_statistics(selected_data, selected_time)
        
        # 콜백 호출
        if stats:
            self.statistics_callback(stats, x1, x2)
            
    def update_data(self):
        """데이터 업데이트 시 호출"""
        if self.is_enabled:
            self._calculate_statistics()
