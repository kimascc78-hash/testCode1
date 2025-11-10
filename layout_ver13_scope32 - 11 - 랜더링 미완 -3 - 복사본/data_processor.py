"""
Data Processor Module
데이터 처리 전담 모듈
"""

import time
import numpy as np
from collections import deque
#from PyQt5.QtWidgets import QApplication
from rf_protocol import RFProtocol
from data_manager import StatusParser


class DataProcessor:
    """데이터 처리 관리자"""
    PLOT_UPDATE_RATE = 1
    
    def __init__(self, parent):
        self.parent = parent
        self.data_queue = deque(maxlen=200)
        self.process_count_since_last_plot = 0 # 그래프 업데이트 빈도 조절용 카운터
        self.last_power_sync_time = 0  # 251103✅ 이 줄 추가
    
    def update_from_server(self, data, timestamp):
        """서버로부터 데이터 수신"""
        self.data_queue.append((data, timestamp))
    
    def process_data_queue(self):
        """데이터 큐 처리 - 상태 조회 로그 필터링 및 OpenGL 에러 방지"""
        processed_count = 0
        while self.data_queue and processed_count < 30:  # 한 번에 최대 5개만 처리
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
                    # 1. UI 업데이트 (테이블, 게이지) - 필수적
                    status = StatusParser.parse_device_status(parsed["data"])
                    self.parent.rf_enabled = bool(status["rf_on_off"]) #추가 251103 rf on/off 버튼 동기화
                    self.parent.ui_controller.update_rf_button_text(self.parent.rf_enabled)#추가 251103 rf on/off 버튼 동기화
                    
                    # 추가 251103 ✅ Set Power 값 동기화    
                    # ✅ Set Power 값 동기화 (포커스 없고, skip_power_sync 아닐 때만)
                    current_time = time.time()
                    if current_time - self.last_power_sync_time >= 1.0:
                        if not self.parent.ui_controller.power_input.hasFocus():
                            current_text = self.parent.ui_controller.power_input.text().strip()
                            new_text = f"{status['set_power']:.1f}"
                            if current_text != new_text:
                                self.parent.ui_controller.power_input.setText(new_text)
                        self.last_power_sync_time = current_time

                    # 2. 데이터 저장 (✅ elapsed_time 전달)
                    #elapsed_time = self.parent.sample_count * self.parent.sample_interval
                    #self.parent.data_manager.add_data_entry(status, elapsed_time)
                        
                    self.parent.ui_controller.update_status_table(status)
                    self.parent.ui_controller.update_gauges(status)
                    
                    # 2. 데이터 저장
                    self.parent.data_manager.add_data_entry(status)
                    
                    # 3. 플롯 데이터 업데이트 (단순히 데이터만 큐에 추가)
                    self.update_plot_data(status, timestamp)
                    
                    # 4. 오실로스코프 다이얼로그
                    if self.parent.oscilloscope_dialog and self.parent.oscilloscope_dialog.isVisible():
                        self.parent.oscilloscope_dialog.update_data(status)
                    
                    # 5. 자동 저장 체크
                    if self.parent.auto_save_enabled and self.parent.data_manager.get_data_count() >= 1200: #60초 마다 저장
                        self.auto_save()
                    
                    processed_count += 1
                        
                except Exception as e:
                    self.parent.log_manager.write_log(f"[ERROR] 데이터 처리 실패: {e}", "red")
            
            # ⚠️ QApplication.processEvents() 호출 제거 완료!
            
            # 그래프 업데이트 빈도 조절 로직 추가
            if processed_count > 0:
                self.process_count_since_last_plot += processed_count
                if self.process_count_since_last_plot >= self.PLOT_UPDATE_RATE:
                    # 그래프 업데이트 및 분석 매니저 호출은 여기서 제어
                    self.parent.plot_manager.simple_plot_update()
                self._update_analysis_managers()
                self.process_count_since_last_plot = 0
    
    def update_plot_data(self, status, timestamp):
        """플롯 데이터 업데이트 - 고정 간격 적용 및 안전한 처리"""
        try:
            # ✅ sample_count는 계속 증가 (올바름)
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
                    plot_data[key].popleft()  # 왼쪽(오래된 데이터) 제거
    
    def _update_analysis_managers(self):
        """분석 매니저들 업데이트"""
        plot_keys = ['forward', 'reflect', 'delivery', 'frequency', 'gamma', 
                    'real_gamma', 'image_gamma', 'rf_phase', 'temperature']
        
        for i, key in enumerate(plot_keys):
            if (self.parent.selected_plots[i] and 
                i < len(self.parent.dock_manager.analysis_managers)):
                self.parent.dock_manager.analysis_managers[i].update_data()
    
    def auto_save(self):
        """자동 저장 실행"""
        self.parent.save_excel()
        #self.parent.save_log() #로그는 파일로 저장하지 않는다.
        self.parent.data_manager.clear_data_log()
    
    def cleanup(self):
        """정리 작업"""
        try:
            # 데이터 큐 클리어
            self.data_queue.clear()
            self.parent.log_manager.write_log("[INFO] 데이터 프로세서 정리 완료", "cyan")
        except Exception as e:
            print(f"[WARNING] 데이터 프로세서 정리 중 오류: {e}")