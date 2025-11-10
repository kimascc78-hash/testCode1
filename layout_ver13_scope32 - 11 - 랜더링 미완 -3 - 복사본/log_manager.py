"""
Log Manager Module
로그 관리 전담 모듈
"""

import datetime
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QTextCursor


class LogManager:
    """로그 관리자"""
    
    def __init__(self, parent):
        self.parent = parent
        self.show_status_logs = False
        
        # 로그 위젯 생성
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        
        # 로그 스타일 설정
        self.log.setStyleSheet("""
            QTextEdit { 
                background-color: #252535; 
                border: 1px solid #00f0ff; 
                border-radius: 5px; 
                color: #ffffff; 
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
    
    def get_log_widget(self):
        """로그 위젯 반환"""
        return self.log
    
    def get_log_content(self):
        """로그 내용 반환"""
        return self.log.toPlainText()
    
    def write_log(self, message, color="white"):
        """로그 메시지 작성 - 시인성 개선"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # 메시지 타입별 포맷팅
        if "[SEND]" in message:
            formatted_msg = self._format_send_message(timestamp, message)
        elif "[RECV]" in message or "Received" in message:
            formatted_msg = self._format_recv_message(timestamp, message)
        elif "[ERROR]" in message:
            formatted_msg = self._format_error_message(timestamp, message)
        elif "[WARNING]" in message:
            formatted_msg = self._format_warning_message(timestamp, message)
        elif "[SUCCESS]" in message:
            formatted_msg = self._format_success_message(timestamp, message)
        elif "[INFO]" in message:
            formatted_msg = self._format_info_message(timestamp, message)
        elif "[CONFIG]" in message:
            formatted_msg = self._format_config_message(timestamp, message)
        else:
            formatted_msg = self._format_default_message(timestamp, message, color)
        
        try:
            self.log.append(formatted_msg)
            # 자동 스크롤 (최신 로그가 보이도록)
            self.log.moveCursor(QTextCursor.End)
        except Exception as e:
            print(f"[LOG_ERROR] {timestamp} {message} (Error: {e})")
    
    def _format_send_message(self, timestamp, message):
        """전송 메시지 포맷팅 - 정렬 개선"""
        formatted_msg = f'<span style="color:#00ff88; font-weight:bold;">[{timestamp}]</span> '
        formatted_msg += f'<span style="color:#88ddff; font-weight:bold;">📤 SEND:</span>'
        
        # 원본 메시지에서 [SEND] 부분 제거
        clean_message = message.replace("[SEND] ", "")
        
        # HTML에서 정렬 유지를 위해 <pre> 태그 사용
        formatted_msg += f'<pre style="color:#cccccc; font-family: monospace; margin: 0; white-space: pre-wrap;">{clean_message}</pre>'
        
        return formatted_msg
    
    def _format_recv_message(self, timestamp, message):
        """수신 메시지 포맷팅 - 정렬 개선"""
        formatted_msg = f'<span style="color:#00ff88; font-weight:bold;">[{timestamp}]</span> '
        formatted_msg += f'<span style="color:#ff88dd; font-weight:bold;">📥 RECV:</span>'
        
        # 원본 메시지에서 [RECV] 부분 제거
        clean_message = message.replace("[RECV] ", "")
        
        # HTML에서 정렬 유지를 위해 <pre> 태그 사용
        formatted_msg += f'<pre style="color:#cccccc; font-family: monospace; margin: 0; white-space: pre-wrap;">{clean_message}</pre>'
        
        return formatted_msg
    
    def _format_error_message(self, timestamp, message):
        """에러 메시지 포맷팅"""
        formatted_msg = f'<span style="color:#00ff88; font-weight:bold;">[{timestamp}]</span> '
        formatted_msg += f'<span style="color:#ff4444; font-weight:bold;">❌ ERROR:</span> '
        formatted_msg += f'<span style="color:#ffaaaa;">{message.split("] ")[1] if "] " in message else message}</span>'
        return formatted_msg
    
    def _format_warning_message(self, timestamp, message):
        """경고 메시지 포맷팅"""
        formatted_msg = f'<span style="color:#00ff88; font-weight:bold;">[{timestamp}]</span> '
        formatted_msg += f'<span style="color:#ffaa00; font-weight:bold;">WARNING:</span> '
        formatted_msg += f'<span style="color:#ffddaa;">{message.split("] ")[1] if "] " in message else message}</span>'
        return formatted_msg
    
    def _format_success_message(self, timestamp, message):
        """성공 메시지 포맷팅"""
        formatted_msg = f'<span style="color:#00ff88; font-weight:bold;">[{timestamp}]</span> '
        formatted_msg += f'<span style="color:#44ff44; font-weight:bold;">SUCCESS:</span> '
        formatted_msg += f'<span style="color:#aaffaa;">{message.split("] ")[1] if "] " in message else message}</span>'
        return formatted_msg
    
    def _format_info_message(self, timestamp, message):
        """정보 메시지 포맷팅"""
        formatted_msg = f'<span style="color:#00ff88; font-weight:bold;">[{timestamp}]</span> '
        formatted_msg += f'<span style="color:#00ddff; font-weight:bold;">INFO:</span> '
        formatted_msg += f'<span style="color:#aaddff;">{message.split("] ")[1] if "] " in message else message}</span>'
        return formatted_msg
    
    def _format_config_message(self, timestamp, message):
        """설정 메시지 포맷팅"""
        formatted_msg = f'<span style="color:#00ff88; font-weight:bold;">[{timestamp}]</span> '
        formatted_msg += f'<span style="color:#ff8800; font-weight:bold;">CONFIG:</span> '
        formatted_msg += f'<span style="color:#ffccaa;">{message.split("] ")[1] if "] " in message else message}</span>'
        return formatted_msg
    
    def _format_default_message(self, timestamp, message, color):
        """기본 메시지 포맷팅"""
        formatted_msg = f'<span style="color:#00ff88; font-weight:bold;">[{timestamp}]</span> '
        formatted_msg += f'<span style="color:{color};">{message}</span>'
        return formatted_msg
    
    def clear_log(self):
        """로그 클리어"""
        self.log.clear()
        self.write_log("═══════════════════════════════════════════════════════", "white")
        self.write_log("[INFO] 로그가 클리어되었습니다.", "cyan")
        self.write_log("═══════════════════════════════════════════════════════", "white")
    
    def toggle_status_logs(self):
        """상태 조회 로그 표시 토글"""
        self.show_status_logs = not self.show_status_logs
        status_text = "표시" if self.show_status_logs else "숨김"
        self.write_log(f"[CONFIG] 상태 조회 로그 {status_text} 설정", "yellow")
        return self.show_status_logs