"""
Dock Manager Module - 플로팅 기반 단순화된 도킹 시스템
"""

import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QDockWidget
from PyQt5.QtCore import Qt, QSize, QTimer
from ui_widgets import GaugeWidget, AnalysisDockWidget
from plot_analysis import PlotAnalysisManager, AdvancedStatisticsPanel


class DockManager:
    """도킹 위젯 관리자 - 단순화된 버전"""
    
    def __init__(self, parent):
        self.parent = parent
        self.dock_widgets = []
        self.gauges = []
        self.plot_widgets = []
        self.plot_lines = []
        self.analysis_managers = []
        self.statistics_panels = {}
    
    def create_dock_widgets(self):
        """도킹 위젯들 생성 - 단순화된 버전"""
        colors = self._get_plot_colors()
        
        gauge_params = [
            ("Forward Power", 0, 3000, "W", colors["graph_max"]),
            ("Reflect Power", 0, 300, "W", colors["graph_min"]),
            ("Delivery Power", 0, 3000, "W", colors["graph_delivery"]),
            ("Frequency", 0, 30, "MHz", colors["graph_avg"]),
            ("Gamma", 0, 1, "", colors["graph_volt"]),
            ("Real Gamma", 0, 1, "", colors["graph_real_gamma"]),
            ("Image Gamma", 0, 1, "", colors["graph_image_gamma"]),
            ("RF Phase", 0, 360, "°", colors["graph_phase"]),
            ("Temperature", 20, 80, "°C", colors["graph_temp"])
        ]
        
        plot_data_keys = ['forward', 'reflect', 'delivery', 'frequency', 'gamma', 
                         'real_gamma', 'image_gamma', 'rf_phase', 'temperature']
        
        for idx, ((title, min_val, max_val, unit, color), data_key) in enumerate(zip(gauge_params, plot_data_keys)):
            # 핵심 변경: CustomDockWidget → AnalysisDockWidget
            dock = AnalysisDockWidget(title, self.parent, preset="standard")
            
            # 핵심 변경: 플로팅 상태 변경 시 분석 기능 토글
            dock.analysis_mode_changed.connect(
                lambda enabled, i=idx: self._on_analysis_mode_changed(i, enabled)
            )
            
            # 도킹 위젯 스타일 설정 (기존과 동일)
            dock.setStyleSheet(f"""
                QDockWidget {{
                    border: 2px solid #666633;
                    border-radius: 5px;
                    margin: 3px;
                    background: #1e1e2e;
                }}
                
                QDockWidget::title {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #666633, stop:1 #444411);
                    color: #ffffff;
                    padding: 8px 15px;
                    border-top-left-radius: 3px;
                    border-top-right-radius: 3px;
                    border-bottom: 2px solid #888855;
                    font-weight: bold;
                    font-size: 13px;
                }}
            """)
            
            dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
            
            # 내용 위젯 생성
            dock_content = self._create_dock_content(title, min_val, max_val, unit, color, data_key, idx)
            dock.setWidget(dock_content)
            
            self.dock_widgets.append(dock)
            self.parent.addDockWidget(Qt.TopDockWidgetArea, dock)
            dock.setVisible(self.parent.selected_plots[idx])
        
        self.parent.log_manager.write_log(f"[INFO] {len(self.dock_widgets)}개 도킹 위젯 생성 완료", "cyan")
        
        QTimer.singleShot(100, self.redistribute_docked_widgets)
    
    def _on_analysis_mode_changed(self, dock_index, analysis_enabled):
        """분석 모드 변경 처리 - 단순화된 버전"""
        if dock_index not in self.statistics_panels:
            return
        
        # 고급 분석 패널 표시/숨김
        advanced_panel = self.statistics_panels[dock_index]['advanced']
        
        if analysis_enabled:
            # 플로팅 상태: 고급 분석 활성화
            dock_content = self.dock_widgets[dock_index].widget()
            layout = dock_content.layout()
            
            # 분석 패널이 아직 추가되지 않았다면 추가
            if advanced_panel.parent() != dock_content:
                layout.addWidget(advanced_panel)
            
            # 분석 관리자 활성화
            analysis_manager = self.analysis_managers[dock_index]
            analysis_manager.enable_analysis(
                lambda stats, x1, x2, idx=dock_index: self._update_advanced_statistics(idx, stats, x1, x2)
            )
            
            # 즉시 통계 계산하여 초기값 표시
            QTimer.singleShot(100, analysis_manager._calculate_statistics)
            
            dock_title = self.dock_widgets[dock_index].windowTitle()
            self.parent.log_manager.write_log(f"[INFO] {dock_title} - 고급 분석 모드 활성화", "cyan")
            
        else:
            # 도킹 상태: 기본 모드
            if advanced_panel.parent():
                advanced_panel.parent().layout().removeWidget(advanced_panel)
                advanced_panel.setParent(None)
            
            # 분석 관리자 비활성화
            self.analysis_managers[dock_index].disable_analysis()
    
    def _create_dock_content(self, title, min_val, max_val, unit, color, data_key, idx):
        """도킹 위젯 내용 생성"""
        dock_content = QWidget()
        dock_content_layout = QVBoxLayout(dock_content)
        dock_content_layout.setSpacing(8)
        dock_content_layout.setContentsMargins(10, 10, 10, 10)
        
        # 게이지 생성
        gauge = GaugeWidget(title, min_val, max_val, unit, color)
        gauge.setMaximumHeight(180)
        gauge.setMinimumHeight(140)
        
        # 게이지를 왼쪽 정렬로 배치
        gauge_layout = QHBoxLayout()
        gauge_layout.setContentsMargins(0, 0, 0, 0)

        # 왼쪽에 작은 여백 추가
        #left_spacer = QWidget()
        #left_spacer.setFixedWidth(50)
        #gauge_layout.addWidget(left_spacer)
        #gauge_layout.addWidget(gauge, 0, Qt.AlignLeft)
        #gauge_layout.addStretch(1)
        
        #게이지 센터 정렬
        gauge_layout.addStretch(1)  # 왼쪽 여백
        gauge_layout.addWidget(gauge, 0, Qt.AlignCenter)  # 센터 정렬
        gauge_layout.addStretch(1)  # 오른쪽 여백
        
        gauge_container = QWidget()
        gauge_container.setLayout(gauge_layout)
        gauge_container.setMaximumHeight(180)
        gauge_container.setMinimumHeight(140)
        
        self.gauges.append(gauge)
        dock_content_layout.addWidget(gauge_container)
        
        # 플롯 생성
        plot = self._create_plot_widget(title, unit, min_val, max_val, color)
        self.plot_widgets.append(plot)
        dock_content_layout.addWidget(plot, 1)
        
        # 분석 관리자 생성
        analysis_manager = PlotAnalysisManager(
            plot, 
            self.parent.plot_data[data_key], 
            self.parent.plot_data['time']
        )
        self.analysis_managers.append(analysis_manager)
        
        # 고급 통계 패널 생성
        advanced_stats = AdvancedStatisticsPanel()
        advanced_stats.export_requested.connect(lambda data: self._export_analysis_data(idx, data))
        advanced_stats.clear_requested.connect(lambda: self._clear_analysis(idx))
        
        # 통계 패널을 딕셔너리에 저장
        self.statistics_panels[idx] = {
            'advanced': advanced_stats,
            'unit': unit
        }
        
        return dock_content
    
    def _create_plot_widget(self, title, unit, min_val, max_val, color):
        """플롯 위젯 생성"""
        plot = pg.PlotWidget()
        plot.setBackground("#1e1e2e")
        plot.showGrid(x=True, y=True)
        plot.setLabel('left', title, units=unit)
        plot.setLabel('bottom', 'Time', units='s')
        plot.setMinimumHeight(150)
        
        # OpenGL 대신 안전한 렌더링 설정
        #plot.getPlotItem().setClipToView(True)
        #plot.getPlotItem().setDownsampling(auto=True)
        
        #plot.getPlotItem().getViewBox().setRange(xRange=[0, 100], yRange=[min_val, max_val], padding=0)
        
        #plot_line = plot.plot(pen=pg.mkPen(color=color, width=2), antialias=False)
        #self.plot_lines.append(plot_line)
        
        ##########
        # 자동 범위 조정 활성화
        plot.getPlotItem().enableAutoRange(axis='y')
        plot.getPlotItem().setAutoVisible(y=True)
        
        # X축은 고정, Y축은 자동
        plot.getPlotItem().getViewBox().setRange(xRange=[0, 100], padding=0)
        
        plot_line = plot.plot(pen=pg.mkPen(color=color, width=2))
        self.plot_lines.append(plot_line)
        ##########
        
        #더블클릭으로 오토 범위
        def auto_range_on_double_click(event):
            if event.double():
                plot.getPlotItem().autoRange()
        
        plot.getPlotItem().scene().sigMouseClicked.connect(auto_range_on_double_click)
        
        return plot
    
    def _get_plot_colors(self):
        """플롯 색상 설정 반환"""
        return {
            "graph_max": "#00f0ff", "graph_avg": "#00ff00", "graph_min": "#ff0000",
            "graph_volt": "#ffff00", "graph_temp": "#ff00ff", "graph_delivery": "#ff9900",
            "graph_real_gamma": "#33ccff", "graph_image_gamma": "#cc33ff", "graph_phase": "#ff3333"
        }
    
    def _update_advanced_statistics(self, dock_index, stats, x1, x2):
        """고급 통계 패널 업데이트"""
        if dock_index in self.statistics_panels and stats is not None:
            unit = self.statistics_panels[dock_index]['unit']
            advanced_panel = self.statistics_panels[dock_index]['advanced']
            advanced_panel.update_statistics(stats, x1, x2, unit)
    
    def _export_analysis_data(self, dock_index, data):
        """분석 데이터 내보내기"""
        import json
        import datetime
        
        try:
            dock_title = self.dock_widgets[dock_index].windowTitle()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_{dock_title.replace(' ', '_')}_{timestamp}.json"
            
            export_data = {
                'parameter': dock_title,
                'timestamp': timestamp,
                'analysis_range': data['range'],
                'unit': data['unit'],
                'statistics': data['statistics']
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            self.parent.log_manager.write_log(f"[INFO] 분석 데이터 내보내기 완료: {filename}", "cyan")
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 분석 데이터 내보내기 실패: {e}", "red")
    
    def _clear_analysis(self, dock_index):
        """분석 영역 클리어"""
        analysis_manager = self.analysis_managers[dock_index]
        dock_title = self.dock_widgets[dock_index].windowTitle()
        
        if analysis_manager.is_enabled:
            current_callback = analysis_manager.statistics_callback
            analysis_manager.disable_analysis()
            analysis_manager.enable_analysis(current_callback)
            
        self.parent.log_manager.write_log(f"[INFO] {dock_title} 분석 영역 초기화", "cyan")
    
    def initialize_dock_sizes(self):
        """단순화된 초기 크기 설정"""
        # 각 도킹 위젯은 자체적으로 크기 관리
        # 복잡한 크기 모드 감지 로직 제거
        pass
    
    def save_state(self):
        """도킹 상태 저장 - 단순화"""
        try:
            # 도킹 상태 저장
            success, msg = self.parent.config_manager.save_dock_state(self.parent.saveState())
            if success:
                self.parent.log_manager.write_log(f"[INFO] {msg}", "cyan")
            else:
                self.parent.log_manager.write_log(f"[WARNING] 도킹 상태 저장 실패: {msg}", "yellow")
            
            # 각 도킹 위젯의 크기 저장 (자체 관리)
            for dock in self.dock_widgets:
                if hasattr(dock, 'save_current_size'):
                    dock.save_current_size()
            
            self.parent.log_manager.write_log("[INFO] 도킹 위젯 크기 설정 저장 완료", "cyan")
            
        except Exception as e:
            self.parent.log_manager.write_log(f"[WARNING] 도킹 상태 저장 중 오류: {e}", "yellow")
    
    def restore_dock_state(self):
        """도킹 상태 복원"""
        success, state_data, msg = self.parent.config_manager.load_dock_state()
        if success and state_data:
            self.parent.restoreState(state_data)
            self.parent.log_manager.write_log(f"[INFO] {msg}", "cyan")
            
    def redistribute_docked_widgets(self):
        """도킹된 위젯들을 균등하게 재분배 - 개선된 버전"""
        try:
            # 현재 도킹된 위젯들 찾기
            docked_widgets = []
            
            for dock in self.dock_widgets:
                if dock.isVisible() and not dock.isFloating():
                    docked_widgets.append(dock)
            
            if len(docked_widgets) <= 1:
                return
            
            self.parent.log_manager.write_log(f"[INFO] 도킹 위젯 재분배 시작: {len(docked_widgets)}개 위젯", "cyan")
            
            # 상단 도킹 영역에 모든 위젯을 균등하게 배치
            # 먼저 모든 위젯을 상단 영역으로 이동
            for i, dock in enumerate(docked_widgets):
                if i == 0:
                    # 첫 번째 위젯은 그대로 두고
                    self.parent.addDockWidget(Qt.TopDockWidgetArea, dock)
                else:
                    # 나머지는 첫 번째 위젯 옆에 배치
                    self.parent.addDockWidget(Qt.TopDockWidgetArea, dock)
                    
            # 크기 제한 재설정
            for dock in docked_widgets:
                dock.setMinimumSize(250, 450)
                dock.setMaximumSize(500, 650)
            
            # 균등 분배를 위한 강제 크기 조정
            self._force_equal_distribution(docked_widgets)
            
            self.parent.log_manager.write_log(f"[INFO] 도킹 위젯 재분배 완료", "cyan")
            
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 도킹 위젯 재분배 실패: {e}", "red")
    
    def _force_equal_distribution(self, docked_widgets):
        """강제로 균등 분배 적용"""
        if not docked_widgets:
            return
            
        # 메인 윈도우 크기 기반 계산
        main_width = self.parent.width()
        main_height = self.parent.height()
        
        # 상단 도킹 영역에서의 균등 분배
        widget_count = len(docked_widgets)
        target_width = (main_width - 50) // widget_count  # 여백 고려
        target_height = min(550, (main_height - 350))  # 적절한 높이
        
        # 순차적으로 크기 조정
        for i, dock in enumerate(docked_widgets):
            QTimer.singleShot(100 + i * 30, 
                lambda d=dock, w=target_width, h=target_height: 
                self._apply_widget_size(d, w, h)
            )
    
    def _apply_widget_size(self, dock, width, height):
        """개별 위젯에 크기 적용"""
        try:
            if dock and not dock.isFloating() and dock.isVisible():
                # 크기 제한 임시 해제
                dock.setMinimumSize(200, 300)
                dock.setMaximumSize(16777215, 16777215)
                
                # 크기 적용
                dock.resize(width, height)
                
                # 크기 제한 재설정
                QTimer.singleShot(100, lambda: self._restore_size_limits(dock))
                
        except Exception as e:
            self.parent.log_manager.write_log(f"[WARNING] 위젯 크기 적용 실패: {e}", "yellow")
    
    def _restore_size_limits(self, dock):
        """크기 제한 복원"""
        try:
            if dock and not dock.isFloating():
                dock.setMinimumSize(250, 400)
                dock.setMaximumSize(500, 650)
        except:
            pass
    
    def _get_area_name(self, area):
        """도킹 영역 이름 반환"""
        area_names = {
            Qt.LeftDockWidgetArea: "좌측",
            Qt.RightDockWidgetArea: "우측", 
            Qt.TopDockWidgetArea: "상단",
            Qt.BottomDockWidgetArea: "하단"
        }
        return area_names.get(area, "알 수 없음")