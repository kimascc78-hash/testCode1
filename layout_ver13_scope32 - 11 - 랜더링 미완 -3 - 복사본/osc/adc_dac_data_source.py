"""
ADC/DAC Data Source Module
Oscilloscope용 ADC/DAC 데이터 수집 모듈
"""

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
import struct
import time
import sys
import os

# 상위 디렉토리의 rf_protocol import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rf_protocol import RFProtocol


class AdcDacDataSource(QObject):
    """ADC/DAC 데이터 소스"""
    
    data_ready = pyqtSignal(list, float)  # (8개 채널 데이터, timestamp)
    
    def __init__(self, network_manager, interval_ms=100):
        super().__init__()
        self.network_manager = network_manager
        self.interval_ms = interval_ms
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.fetch_data)
        
        self.is_running = False
    
    def start(self):
        """데이터 수집 시작"""
        if not self.network_manager or not self.network_manager.client_thread:
            #print("[ADC/DAC] Network manager not available")
            return False
        
        self.is_running = True
        self.timer.start(self.interval_ms)
        #print(f"[ADC/DAC] Started (interval={self.interval_ms}ms)")
        return True
    
    def stop(self):
        """데이터 수집 중지"""
        self.is_running = False
        self.timer.stop()
        #print("[ADC/DAC] Stopped")
    
    def set_interval(self, interval_ms):
        """업데이트 주기 변경"""
        self.interval_ms = interval_ms
        if self.is_running:
            self.timer.stop()
            self.timer.start(self.interval_ms)
    
    def fetch_data(self):
        """ADC/DAC 데이터 조회"""
        if not self.is_running:
            return
        
        try:
            result = self.network_manager.client_thread.send_command(
                RFProtocol.CMD_SYSTEM_CONTROL,
                RFProtocol.SUBCMD_GET_ADC_DAC,
                wait_response=True,
                sync=True
            )
            
            if result.success and result.response_data:
                parsed = RFProtocol.parse_response(result.response_data)
                if parsed and len(parsed['data']) >= 32:  # 8 * 4 bytes
                    values = struct.unpack('<8I', parsed['data'][:32])
                    timestamp = time.time()
                    self.data_ready.emit(list(values), timestamp)
                    
        except Exception as e:
            print(f"[ADC/DAC] Fetch error: {e}")


class StatusDataSource(QObject):
    """Status 데이터 소스 (기존 방식)"""
    
    data_ready = pyqtSignal(dict, float)  # (status_data, timestamp)
    
    def __init__(self):
        super().__init__()
    
    def update_data(self, status_data):
        """외부에서 호출"""
        timestamp = time.time()
        self.data_ready.emit(status_data, timestamp)