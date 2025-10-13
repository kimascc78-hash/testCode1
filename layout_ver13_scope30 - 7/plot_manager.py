"""
Plot Manager Module
플롯 관리 전담 모듈
"""

import numpy as np
from PyQt5.QtCore import QTimer


class PlotManager:
    """플롯 관리자"""
    
    def __init__(self, parent):
        self.parent = parent
        self.max_points = 10000  # 최근 10000개만 표시 (성능 최적화)
    
    def simple_plot_update(self):
        """OpenGL 에러 방지용 안전한 플롯 업데이트"""
        plot_keys = ['forward', 'reflect', 'delivery', 'frequency', 'gamma', 
                    'real_gamma', 'image_gamma', 'rf_phase', 'temperature']
        
        for i, key in enumerate(plot_keys):
            if not self.parent.selected_plots[i] or key not in self.parent.plot_data:
                continue
                
            try:
                # 데이터 유효성 검사
                time_data = self.parent.plot_data['time']
                value_data = self.parent.plot_data[key]
                
                # 데이터 길이 체크
                if len(time_data) == 0 or len(value_data) == 0:
                    continue
                    
                # 길이 동기화
                min_len = min(len(time_data), len(value_data))
                if min_len < 2:  # 최소 2개 이상의 점이 필요
                    continue
                    
                # 최근 데이터만 가져오기
                start_idx = max(0, min_len - self.max_points)
                x_data = time_data[start_idx:min_len]
                y_data = value_data[start_idx:min_len]
                
                # 데이터 유효성 재확인
                if len(x_data) != len(y_data) or len(x_data) < 2:
                    continue
                    
                # NaN, Inf 값 체크 및 필터링
                x_array = np.array(x_data, dtype=np.float64)
                y_array = np.array(y_data, dtype=np.float64)
                
                
                # 유효한 데이터만 선택
                valid_mask = np.isfinite(x_array) & np.isfinite(y_array)
                if not np.any(valid_mask):
                    continue
                    
                x_clean = x_array[valid_mask]
                y_clean = y_array[valid_mask]
                
                # 최소 2개 이상의 점이 있어야 선을 그릴 수 있음
                if len(x_clean) < 2:
                    continue
                
                # 안전한 플롯 업데이트
                if i < len(self.parent.dock_manager.plot_lines):
                    self.parent.dock_manager.plot_lines[i].setData(x_clean.tolist(), y_clean.tolist())
                
            except Exception:
                # 개별 플롯 오류는 무시하고 계속 진행
                continue
    
    def safe_initialize_plots(self):
        """안전한 plot 초기화"""
        try:
            # 모든 plot 위젯 강제 표시
            for i, plot_widget in enumerate(self.parent.dock_manager.plot_widgets):
                if self.parent.selected_plots[i]:
                    plot_widget.show()
                    plot_widget.repaint()
            
            # plot 표시 후 dock 크기 초기화
            QTimer.singleShot(100, self.parent.dock_manager.initialize_dock_sizes)
            
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] Plot 초기화 오류: {e}", "red")
    
    def update_plot_ranges(self, plot_index, min_val, max_val):
        """플롯 범위 업데이트"""
        try:
            if 0 <= plot_index < len(self.parent.dock_manager.plot_widgets):
                plot_widget = self.parent.dock_manager.plot_widgets[plot_index]
                plot_widget.getPlotItem().getViewBox().setYRange(min_val, max_val, padding=0.1)
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 플롯 범위 업데이트 실패: {e}", "red")
    
    def clear_plot_data(self, plot_index):
        """특정 플롯 데이터 클리어"""
        try:
            if 0 <= plot_index < len(self.parent.dock_manager.plot_lines):
                self.parent.dock_manager.plot_lines[plot_index].setData([], [])
                self.parent.log_manager.write_log(f"[INFO] 플롯 {plot_index} 데이터 클리어", "cyan")
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 플롯 데이터 클리어 실패: {e}", "red")
    
    def clear_all_plots(self):
        """모든 플롯 데이터 클리어"""
        try:
            for i in range(len(self.parent.dock_manager.plot_lines)):
                self.clear_plot_data(i)
            self.parent.log_manager.write_log("[INFO] 모든 플롯 데이터 클리어", "cyan")
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 전체 플롯 클리어 실패: {e}", "red")
    
    def set_plot_visibility(self, plot_index, visible):
        """플롯 가시성 설정"""
        try:
            if 0 <= plot_index < len(self.parent.dock_manager.dock_widgets):
                dock = self.parent.dock_manager.dock_widgets[plot_index]
                dock.setVisible(visible)
                
                plot_name = self.parent.plot_labels[plot_index] if plot_index < len(self.parent.plot_labels) else f"Plot {plot_index}"
                status = "표시" if visible else "숨김"
                self.parent.log_manager.write_log(f"[INFO] {plot_name} {status}", "cyan")
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 플롯 가시성 설정 실패: {e}", "red")
    
    def export_plot_data(self, plot_index, filename=None):
        """플롯 데이터 내보내기"""
        try:
            if not filename:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_name = self.parent.plot_labels[plot_index] if plot_index < len(self.parent.plot_labels) else f"Plot_{plot_index}"
                filename = f"plot_data_{plot_name}_{timestamp}.csv"
            
            plot_keys = ['forward', 'reflect', 'delivery', 'frequency', 'gamma', 
                        'real_gamma', 'image_gamma', 'rf_phase', 'temperature']
            
            if plot_index < len(plot_keys):
                key = plot_keys[plot_index]
                time_data = self.parent.plot_data['time']
                value_data = self.parent.plot_data[key]
                
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Time(s)', f'{self.parent.plot_labels[plot_index]}'])
                    
                    min_len = min(len(time_data), len(value_data))
                    for i in range(min_len):
                        writer.writerow([time_data[i], value_data[i]])
                
                self.parent.log_manager.write_log(f"[INFO] 플롯 데이터 내보내기 완료: {filename}", "cyan")
                return True
            
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 플롯 데이터 내보내기 실패: {e}", "red")
            return False
    
    def get_plot_statistics(self, plot_index):
        """플롯 통계 정보 반환"""
        try:
            plot_keys = ['forward', 'reflect', 'delivery', 'frequency', 'gamma', 
                        'real_gamma', 'image_gamma', 'rf_phase', 'temperature']
            
            if plot_index < len(plot_keys):
                key = plot_keys[plot_index]
                data = self.parent.plot_data[key]
                
                if len(data) == 0:
                    return None
                
                data_array = np.array(data)
                valid_data = data_array[np.isfinite(data_array)]
                
                if len(valid_data) == 0:
                    return None
                
                stats = {
                    'count': len(valid_data),
                    'mean': np.mean(valid_data),
                    'std': np.std(valid_data),
                    'min': np.min(valid_data),
                    'max': np.max(valid_data),
                    'median': np.median(valid_data)
                }
                
                return stats
            
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 플롯 통계 계산 실패: {e}", "red")
            return None

    def update_plot_settings(self, settings_manager):
        """플롯 설정 업데이트"""
        try:
            # 최대 포인트 수 업데이트
            self.max_points = settings_manager.get_plot_setting("max_points")
            
            # 선 두께 및 색상 업데이트
            colors = settings_manager.settings.get("colors", {})
            line_width = settings_manager.get_plot_setting("line_width")
            
            color_keys = [
                "graph_max", "graph_min", "graph_delivery", "graph_avg", 
                "graph_volt", "graph_real_gamma", "graph_image_gamma", 
                "graph_phase", "graph_temp"
            ]
            
            for i, color_key in enumerate(color_keys):
                if (i < len(self.parent.dock_manager.plot_lines) and 
                    color_key in colors):
                    
                    import pyqtgraph as pg
                    self.parent.dock_manager.plot_lines[i].setPen(
                        pg.mkPen(color=colors[color_key], width=line_width)
                    )
            
            # 플롯 위젯 설정 업데이트
            grid_alpha = settings_manager.get_plot_setting("grid_alpha")
            auto_range = settings_manager.get_plot_setting("auto_range")
            antialiasing = settings_manager.get_plot_setting("antialiasing")
            
            for plot_widget in self.parent.dock_manager.plot_widgets:
                # 격자 투명도
                plot_widget.showGrid(x=True, y=True, alpha=grid_alpha)
                
                # 안티앨리어싱
                plot_widget.setRenderHint(QPainter.Antialiasing, antialiasing)
                
                # 자동 범위
                if auto_range:
                    plot_widget.getPlotItem().enableAutoRange(axis='y')
                else:
                    plot_widget.getPlotItem().disableAutoRange(axis='y')
            
            self.parent.log_manager.write_log("[CONFIG] 플롯 설정 업데이트 완료", "yellow")
            
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 플롯 설정 업데이트 실패: {e}", "red")
