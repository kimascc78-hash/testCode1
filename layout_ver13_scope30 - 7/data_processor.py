"""
Data Processor Module
데이터 처리 전담 모듈
"""

import time
import numpy as np
from collections import deque
from PyQt5.QtWidgets import QApplication
from rf_protocol import RFProtocol
from data_manager import StatusParser


class DataProcessor:
    """데이터 처리 관리자"""
    
    def __init__(self, parent):
        self.parent = parent
        self.data_queue = deque(maxlen=100)
        self.last_compression_size = 0
        self.compression_threshold = 1000
    
    def update_from_server(self, data, timestamp):
        """서버로부터 데이터 수신"""
        self.data_queue.append((data, timestamp))
    
    def process_data_queue(self):
        """데이터 큐 처리 - 상태 조회 로그 필터링 및 OpenGL 에러 방지"""
        processed_count = 0
        while self.data_queue and processed_count < 5:  # 한 번에 최대 5개만 처리
            data, timestamp = self.data_queue.popleft()
            if not data:
                continue
                
            parsed = RFProtocol.parse_response(data)
            if parsed and parsed["cmd"] == RFProtocol.CMD_DEVICE_STATUS_GET:
                # 상태 조회 명령어는 로그 설정에 따라 표시
                if not self.parent.log_manager.show_status_logs:
                    # 상태 조회 로그를 숨기는 경우, 로그 출력 없이 데이터만 처리
                    pass
                
                try:
                    status = StatusParser.parse_device_status(parsed["data"])
                    self.parent.ui_controller.update_status_table(status)
                    self.update_plot_data(status, timestamp)
                    self.parent.ui_controller.update_gauges(status)
                    self.parent.data_manager.add_data_entry(status)
                    
                    # 오실로스코프 다이얼로그에 데이터 전송
                    if self.parent.oscilloscope_dialog and self.parent.oscilloscope_dialog.isVisible():
                        self.parent.oscilloscope_dialog.update_data(status)
                    
                    if self.parent.auto_save_enabled and self.parent.data_manager.get_data_count() >= 100:
                        self.auto_save()
                    
                    processed_count += 1
                    
                except Exception as e:
                    self.parent.log_manager.write_log(f"[ERROR] 데이터 처리 실패: {e}", "red")
        
        # processEvents 호출을 줄임 - 데이터를 처리했을 때만 호출
        if processed_count > 0:
            QApplication.processEvents()
    
    def update_plot_data(self, status, timestamp):
        """플롯 데이터 업데이트 - 고정 간격 적용 및 안전한 처리"""
        try:
            # 고정 간격으로 시간 계산 (실제 timestamp 무시)
            relative_time = self.parent.sample_count * self.parent.sample_interval
            self.parent.sample_count += 1
            
            # 데이터 추가
            plot_data = self.parent.plot_data
            plot_data['forward'].append(status["forward_power"])
            plot_data['reflect'].append(status["reflect_power"])
            plot_data['delivery'].append(status["delivery_power"])
            plot_data['frequency'].append(status["frequency"])
            plot_data['gamma'].append(status["gamma"])
            plot_data['real_gamma'].append(status["real_gamma"])
            plot_data['image_gamma'].append(status["image_gamma"])
            plot_data['rf_phase'].append(status["rf_phase"])
            plot_data['temperature'].append(status["temperature"])
            plot_data['time'].append(relative_time)
            
            # 데이터 길이 동기화 확인
            self._synchronize_data_lengths()
            
            # 압축 관리
            current_size = len(plot_data['time'])
            if current_size - self.last_compression_size > self.compression_threshold:
                self.compress_old_data_safe()
                self.last_compression_size = current_size
            
            # 안전한 플롯 업데이트 - PlotManager에 위임
            self.parent.plot_manager.simple_plot_update()
            
            # 분석 매니저 업데이트
            self._update_analysis_managers()
                    
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 플롯 데이터 업데이트 실패: {e}", "red")
    
    def _synchronize_data_lengths(self):
        """데이터 길이 동기화"""
        plot_data = self.parent.plot_data
        expected_length = len(plot_data['time'])
        
        for key in plot_data:
            if key != 'time' and len(plot_data[key]) != expected_length:
                # 길이가 맞지 않으면 마지막 값으로 패딩 또는 제거
                while len(plot_data[key]) < expected_length:
                    if plot_data[key]:
                        plot_data[key].append(plot_data[key][-1])
                    else:
                        plot_data[key].append(0)
                while len(plot_data[key]) > expected_length:
                    plot_data[key].pop()
    
    def _update_analysis_managers(self):
        """분석 매니저들 업데이트"""
        plot_keys = ['forward', 'reflect', 'delivery', 'frequency', 'gamma', 
                    'real_gamma', 'image_gamma', 'rf_phase', 'temperature']
        
        for i, key in enumerate(plot_keys):
            if (self.parent.selected_plots[i] and 
                i < len(self.parent.dock_manager.analysis_managers)):
                self.parent.dock_manager.analysis_managers[i].update_data()
    
    def compress_old_data_safe(self):
        """안전한 데이터 압축 - 동기화 보장"""
        keep_recent = 5000
        plot_data = self.parent.plot_data
        
        try:
            # 모든 데이터 길이 확인
            data_lengths = {key: len(data) for key, data in plot_data.items()}
            min_length = min(data_lengths.values()) if data_lengths else 0
            
            if min_length <= keep_recent:
                return
            
            # 압축할 개수 계산
            compress_count = min_length - keep_recent
            
            # 원자적 압축 (모든 데이터를 동시에)
            compressed_data = {}
            for key in plot_data:
                if len(plot_data[key]) > keep_recent:
                    compressed_data[key] = plot_data[key][compress_count:]
                else:
                    compressed_data[key] = plot_data[key]
            
            # 압축된 데이터로 일괄 교체
            self.parent.plot_data = compressed_data
            
            self.parent.log_manager.write_log(f"[INFO] 데이터 압축 완료: 최근 {keep_recent}개 유지", "cyan")
            
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 데이터 압축 실패: {e}", "red")
    
    def auto_save(self):
        """자동 저장 실행"""
        self.parent.save_excel()
        self.parent.save_log()
        self.parent.data_manager.clear_data_log()
    
    def cleanup(self):
        """정리 작업"""
        try:
            # 데이터 큐 클리어
            self.data_queue.clear()
            self.parent.log_manager.write_log("[INFO] 데이터 프로세서 정리 완료", "cyan")
        except Exception as e:
            print(f"[WARNING] 데이터 프로세서 정리 중 오류: {e}")
