"""
Network Manager Module
네트워크 통신 관리 전담 모듈
"""

import struct
import time
from rf_protocol import RFClientThread, RFProtocol


class NetworkManager:
    """네트워크 통신 관리자"""
    
    def __init__(self, parent):
        self.parent = parent
        self.client_thread = None
        
    def init_communication(self):
        """통신 스레드 및 타이머 초기화"""
        ip = self.parent.tuning_settings["IP Address"]
        port = 5000
        
        self.client_thread = RFClientThread(host=ip, port=port)
        self.client_thread.parent = self.parent
        self.client_thread.data_received.connect(self.parent.data_processor.update_from_server)
        self.client_thread.connection_established.connect(self.on_connection_established)
        self.client_thread.connection_failed.connect(self.on_connection_failed)
        self.client_thread.start()
        
        # 연결 시 샘플 카운터 리셋
        self.parent.sample_count = 0
        self.parent.start_time = time.time()
        
        self.parent.log_manager.write_log(f"[INFO] 서버 연결 시도: {ip}:{port}", "cyan")
    
    def connect_server(self):
        """서버 연결"""
        try:
            ip = self.parent.tuning_settings["IP Address"]
            port = 5000
            self.stop_client()
            
            self.client_thread = RFClientThread(host=ip, port=port)
            self.client_thread.parent = self.parent
            self.client_thread.data_received.connect(self.parent.data_processor.update_from_server)
            self.client_thread.connection_established.connect(self.on_connection_established)
            self.client_thread.connection_failed.connect(self.on_connection_failed)
            self.client_thread.start()
            
            # 연결 시 샘플 카운터 리셋
            self.parent.sample_count = 0
            self.parent.start_time = time.time()
            
            self.parent.log_manager.write_log(f"[INFO] 서버 연결 시도: {ip}:{port}", "cyan")
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 연결 실패: {e}", "red")
    
    def disconnect_server(self):
        """서버 연결 해제"""
        self.stop_client()
        self.parent.log_manager.write_log("[INFO] 서버 연결 해제", "cyan")
    
    def stop_client(self):
        """클라이언트 스레드 정지"""
        if self.client_thread:
            self.client_thread.stop()
    
    def toggle_rf(self):
        """RF On/Off 토글"""
        cmd = RFProtocol.CMD_RF_ON if not self.parent.rf_enabled else RFProtocol.CMD_RF_OFF
        subcmd = RFProtocol.SUBCMD_RF_ON if not self.parent.rf_enabled else RFProtocol.SUBCMD_RF_OFF
        
        action = "On" if not self.parent.rf_enabled else "Off"
        self.parent.log_manager.write_log(f"[INFO] RF {action} 명령 전송 중...", "cyan")
        
        try:
            result = self.client_thread.send_command(
                cmd, subcmd, 
                wait_response=True, 
                timeout=5.0,
                sync=True
            )
            
            if hasattr(result, 'success'):
                if result.success:
                    self.parent.rf_enabled = not self.parent.rf_enabled
                    # UI 컨트롤러에게 버튼 텍스트 업데이트 요청
                    self.parent.ui_controller.update_rf_button_text(self.parent.rf_enabled)
                    self.parent.log_manager.write_log(f"[SUCCESS] RF {action} 설정 완료", "green")
                else:
                    self.parent.log_manager.write_log(f"[ERROR] RF {action} 실패: {result.message}", "red")
            else:
                self.parent.log_manager.write_log(f"[ERROR] RF {action} 명령 처리 오류: 잘못된 응답 형태", "red")
                
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] RF {action} 명령 실행 중 예외 발생: {str(e)}", "red")
    
    def apply_power(self, power_text):
        """파워 설정 적용"""
        try:
            power = int(power_text)
            #if 0 <= power <= 3000:
            self.parent.log_manager.write_log(f"[INFO] 파워 설정 명령 전송 중: {power}W", "cyan")
            
            try:
                result = self.client_thread.send_command(
                    RFProtocol.CMD_SET_POWER, 
                    RFProtocol.SUBCMD_SET_POWER, 
                    struct.pack('<I', power), 
                    wait_response=True,
                    timeout=5.0,
                    sync=True
                )
                
                if hasattr(result, 'success'):
                    if result.success:
                        self.parent.log_manager.write_log(f"[SUCCESS] 파워 설정 완료: {power}W", "green")
                    else:
                        self.parent.log_manager.write_log(f"[ERROR] 파워 설정 실패: {result.message}", "red")
                else:
                    self.parent.log_manager.write_log(f"[ERROR] 파워 설정 명령 처리 오류: 잘못된 응답 형태", "red")
                    
            except Exception as cmd_error:
                self.parent.log_manager.write_log(f"[ERROR] 파워 설정 명령 실행 중 예외 발생: {str(cmd_error)}", "red")
                    
            #else:
            #    raise ValueError("Power must be between 0 and 1000")
                
        except ValueError as e:
            self.parent.log_manager.write_log(f"[ERROR] 잘못된 파워 입력: {e}", "red")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self.parent, "입력 오류", str(e))
    
    def on_connection_established(self):
        """연결 성공 이벤트"""
        self.parent.sample_count = 0
        self.parent.start_time = time.time()
        self.parent.log_manager.write_log("[INFO] 서버 연결 성공 - 타이머 리셋", "cyan")
    
    def on_connection_failed(self, message):
        """연결 실패 이벤트"""
        self.parent.log_manager.write_log(f"[ERROR] 서버 연결 실패: {message}", "red")
    
    def cleanup(self):
        """정리 작업"""
        try:
            if self.client_thread:
                self.client_thread.stop()
        except Exception as e:
            print(f"[WARNING] 통신 스레드 정지 중 오류: {e}")
