"""
Plot Manager Module - 극단적 단순화 버전
스크롤 차트 방식: 왼쪽(과거) → 오른쪽(현재)
X축: 분:초 형식 표시 (MM:SS)
"""

import numpy as np
from PyQt5.QtCore import QTimer, QObject, pyqtSignal

#class PlotManager:
class PlotManager(QObject):  # QObject 상속 추가 격자 테스트
    """플롯 관리자 - 초간단 버전"""
    plots_initialized = pyqtSignal()  # 새 시그널: 초기화 완료 알림 격자 테스트
    
    def __init__(self, parent):
        super(PlotManager, self).__init__(parent)  # QObject 초기화 (parent 전달) 격자 테스트
        self.parent = parent
        self.update_counter = 0
        # 설정에서 가져오기 (없으면 기본값 4)
        self.update_interval = 4  # 기본값
        try:
            if hasattr(parent, 'settings_manager'):
                settings = parent.settings_manager.settings
                if "data_collection" in settings:
                    self.update_interval = settings["data_collection"].get("main_graph_update_count", 4)
        except:
            pass  # 설정 로드 실패 시 기본값 사용
        self.time_axis_initialized = False  # 시간 축 포맷 초기화 플래그
    
    @staticmethod
    def format_time_tick(value, scale, spacing):
        """초를 분:초 형식(MM:SS)으로 변환"""
        minutes = int(value // 60)
        seconds = int(value % 60)
        return f'{minutes:02d}:{seconds:02d}'
    
    def setup_time_axis_format(self, plot_item):
        """플롯의 X축을 시간 형식으로 설정"""
        try:
            axis = plot_item.getAxis('bottom')
            
            # ========================================
            # ✅ SI 접두어 비활성화 (ks 표시 방지)
            # ========================================
            axis.enableAutoSIPrefix(False)
            
            # ========================================
            # ✅ X축 라벨: 분:초 형식 표시
            # ========================================
            axis.setLabel('Time (M:S)')  # 또는 'Time (분:초)'
            
            # tickStrings 메서드를 오버라이드하여 분:초 형식으로 표시
            original_tick_strings = axis.tickStrings
            
            def time_tick_strings(values, scale, spacing):
                """초를 MM:SS 형식으로 변환하는 커스텀 tick formatter"""
                strings = []
                for v in values:
                    minutes = int(v // 60)
                    seconds = int(v % 60)
                    strings.append(f'{minutes:02d}:{seconds:02d}')
                return strings
            
            axis.tickStrings = time_tick_strings
        except Exception as e:
            pass
    
    def simple_plot_update(self):
        """스크롤 차트 스타일 플롯 업데이트 - 왼쪽(과거) → 오른쪽(현재)"""
        # 업데이트 간격 체크
        self.update_counter += 1
        if self.update_counter < self.update_interval:
            return
        
        self.update_counter = 0
        
        plot_keys = ['forward', 'reflect', 'delivery', 'frequency', 'gamma', 
                    'real_gamma', 'image_gamma', 'rf_phase', 'temperature']
        
        time_deque = self.parent.plot_data['time']
        if len(time_deque) < 2:
            return
        
        # ========================================
        # ✅ 시간 축 포맷 초기화 (최초 1회만)
        # ========================================
        if not self.time_axis_initialized:
            for i in range(len(self.parent.dock_manager.plot_widgets)):
                if self.parent.selected_plots[i]:
                    plot_item = self.parent.dock_manager.plot_widgets[i].getPlotItem()
                    self.setup_time_axis_format(plot_item)
            self.time_axis_initialized = True
        
        # ========================================
        # ✅ 스크롤 차트 업데이트
        # ========================================
        display_time = self.parent.settings_manager.settings["plot_settings"]["display_time_seconds"]
        
        for i, key in enumerate(plot_keys):
            if not self.parent.selected_plots[i]:
                continue
            
            try:
                value_deque = self.parent.plot_data[key]
                
                # ========================================
                # ✅ NumPy 배열로 변환
                # ========================================
                time_data_np = np.array(time_deque, dtype=float)
                value_data_np = np.array(value_deque, dtype=float)
                
                if len(time_data_np) < 2 or len(value_data_np) < 2:
                    continue
                
                # ========================================
                # ✅ 스크롤 차트: 왼쪽(과거) → 오른쪽(현재)
                # ========================================
                # 실제 시간 그대로 사용 (정규화 없음)
                # 예: [50.0, 50.05, ..., 100.0] → 그대로 사용
                
                if i < len(self.parent.dock_manager.plot_lines):
                    plot_item = self.parent.dock_manager.plot_widgets[i].getPlotItem()
                    
                    # ========================================
                    # ✅ 데이터 렌더링 (실제 시간 사용)
                    # ========================================
                    self.parent.dock_manager.plot_lines[i].setData(
                        time_data_np,   # 실제 시간 (0, 0.05, 0.1, ... 계속 증가)
                        value_data_np
                    )
                    
                    # ========================================
                    # ✅ X축: 최근 display_time 범위 (왼쪽=과거, 오른쪽=현재)
                    # ========================================
                    current_time = time_data_np[-1]  # 현재 시간 (최신 데이터)
                    start_time = max(0, current_time - display_time)  # 시작 시간
                    plot_item.setXRange(start_time, current_time, padding=0)
                    # 예: current_time=100 → X축 범위: 50~100
                    # X축 라벨은 자동으로 MM:SS 형식으로 표시됨
                    
            except Exception as e:
                # 에러 로그는 필요하면 활성화
                # self.parent.log_manager.write_log(f"[ERROR] 플롯 업데이트 중 오류: {e}", "red")
                pass
                
    # def simple_plot_update(self):
        # """오실로스코프 스타일 플롯 업데이트 - 줌 가능"""
        # # 업데이트 간격 체크
        # self.update_counter += 1
        # if self.update_counter < self.update_interval:
            # return
        
        # self.update_counter = 0
        
        # plot_keys = ['forward', 'reflect', 'delivery', 'frequency', 'gamma', 
                    # 'real_gamma', 'image_gamma', 'rf_phase', 'temperature']
        
        # time_deque = self.parent.plot_data['time']
        # if len(time_deque) < 2:
            # return
        
        # # X축 고정 범위
        # display_time = self.parent.settings_manager.settings["plot_settings"]["display_time_seconds"]
        
        # # Down-sampling 설정
        # MAX_VISIBLE_POINTS = 2000
        
        # for i, key in enumerate(plot_keys):
            # if not self.parent.selected_plots[i]:
                # continue
            
            # try:
                # value_deque = self.parent.plot_data[key]
                
                # # NumPy 배열로 변환
                # time_data_np = np.array(time_deque, dtype=float)
                # value_data_np = np.array(value_deque, dtype=float)
                
                # if len(time_data_np) < 2 or len(value_data_np) < 2:
                    # continue
                
                # # 시간 정규화
                # time_shift = display_time - time_data_np[-1]
                # time_data_shifted = time_data_np + time_shift
                
                # # Down-sampling 적용
                # if len(time_data_shifted) > MAX_VISIBLE_POINTS:
                    # indices = np.linspace(0, len(time_data_shifted)-1, MAX_VISIBLE_POINTS, dtype=int)
                    # time_data_shifted = time_data_shifted[indices]
                    # value_data_np = value_data_np[indices]
                
                # if i < len(self.parent.dock_manager.plot_lines):
                    # plot_item = self.parent.dock_manager.plot_widgets[i].getPlotItem()
                    # view_box = plot_item.getViewBox()
                    
                    # # 데이터 렌더링
                    # self.parent.dock_manager.plot_lines[i].setData(
                        # time_data_shifted, 
                        # value_data_np
                    # )
                    
                    # # ✅ X축 자동 범위가 활성화된 경우만 고정 범위 설정
                    # if view_box.autoRangeEnabled()[0]:
                        # # 자동 범위 모드 → 오실로스코프 스타일
                        # plot_item.setXRange(0, display_time, padding=0)
                        # # ✅ 다시 자동 범위 비활성화 (사용자 줌을 가능하게)
                        # plot_item.disableAutoRange(axis='x')
                    # # 자동 범위가 비활성화된 경우 → 사용자가 줌/팬 중 → 건드리지 않음
                    
            # except Exception as e:
                # pass
            
    def safe_initialize_plots(self):
        try:
            for i, plot_widget in enumerate(self.parent.dock_manager.plot_widgets):
                if self.parent.selected_plots[i]:
                    plot_widget.show()
                    plot_widget.repaint()
                    plot_widget.update()  # 추가: 초기 렌더링 강제
            
            QTimer.singleShot(100, self.parent.dock_manager.initialize_dock_sizes)
            
            self.plots_initialized.emit()  # 시그널 발생
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