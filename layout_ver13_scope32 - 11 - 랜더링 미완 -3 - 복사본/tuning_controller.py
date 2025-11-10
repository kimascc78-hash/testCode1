"""
Tuning Controller Module
튜닝 설정 관리 전담 모듈
"""

import time
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QApplication
from PyQt5.QtCore import Qt, QTimer
from tuning_dialog import ImprovedTuningDialog


class TuningController:
    """튜닝 컨트롤러"""
    
    def __init__(self, parent):
        self.parent = parent
        self.progress_dialog = None
    
    def show_tuning_dialog(self):
        """튜닝 설정 다이얼로그 표시 - 탭별 적용 지원"""
        dialog = ImprovedTuningDialog(self.parent.tuning_settings, self.parent)
        
        # 탭별 적용 시그널 연결
        dialog.tab_applied.connect(self.apply_tab_tuning)
        
        if dialog.exec_() == dialog.Accepted:
            old_settings = self.parent.tuning_settings.copy()
            self.parent.tuning_settings = dialog.get_settings()
            self.parent.log_manager.write_log("[INFO] 튜닝 설정이 업데이트되었습니다.", "cyan")
            
            try:
                self.apply_tuning_to_device()
                success, msg = self.parent.tuning_manager.save_settings(self.parent.tuning_settings)
                self.parent.log_manager.write_log(f"[INFO] {msg}", "cyan")
            except Exception as e:
                self.parent.tuning_settings = old_settings
                self.parent.log_manager.write_log(f"[ERROR] 튜닝 설정 적용 실패: {e}", "red")
                QMessageBox.warning(self.parent, "설정 적용 실패", f"장비에 설정을 적용하는 중 오류가 발생했습니다:\n{e}")
    
    def apply_tab_tuning(self, tab_name, tab_settings):
        """탭별 튜닝 설정 적용 - 최적화된 버전"""
        try:
            # 진행 상황 표시 시작
            self.show_progress_start(tab_name)
            
            # 현재 전체 설정에 탭 설정 병합
            temp_settings = self.parent.tuning_settings.copy()
            temp_settings.update(tab_settings)
            
            # 탭별 명령어 생성
            success, commands, msg = self.parent.tuning_manager.get_tab_commands(tab_name, temp_settings)
            if not success:
                self.parent.log_manager.write_log(f"[ERROR] 명령어 생성 실패: {msg}", "red")
                raise Exception(msg)
            
            if not commands:
                # 네트워크 탭인 경우 특별 처리
                if tab_name == "network":
                    self.parent.log_manager.write_log(f"[INFO] {tab_name} 탭은 클라이언트 설정만 포함하며, 장치로 전송할 명령어가 없습니다.", "cyan")
                    
                    # 설정 저장은 진행
                    self.parent.tuning_settings.update(tab_settings)
                    success, msg = self.parent.tuning_manager.save_settings(self.parent.tuning_settings)
                    if success:
                        self.parent.log_manager.write_log(f"[CONFIG] 네트워크 설정이 로컬에 저장되었습니다.", "yellow")
                        
                        # 진행 상황 표시 숨기기
                        self.hide_progress()
                        
                        # 성공 메시지 (비블로킹)
                        QTimer.singleShot(100, lambda: QMessageBox.information(
                            None, "설정 저장 완료", 
                            "네트워크 설정이 저장되었습니다.\n\n"
                            "참고: 네트워크 설정은 클라이언트 설정이므로\n"
                            "장치로 전송되지 않습니다."
                        ))
                    else:
                        self.parent.log_manager.write_log(f"[ERROR] 설정 저장 실패: {msg}", "red")
                        self.hide_progress()
                        QTimer.singleShot(100, lambda: QMessageBox.warning(
                            None, "저장 실패", f"네트워크 설정 저장 중 오류가 발생했습니다:\n{msg}"
                        ))
                    return
                else:
                    # 다른 탭에서 명령어가 없는 경우 경고
                    self.parent.log_manager.write_log(f"[WARNING] {tab_name} 탭에서 전송할 명령어가 없습니다.", "yellow")
                    self.hide_progress()
                    return
            
            self.parent.log_manager.write_log(f"[CONFIG] {tab_name.upper()} 탭 설정 적용 시작 ({len(commands)}개 명령어)", "yellow")
            
            # 각 명령어를 순차적으로 전송 (최적화된 버전)
            success_count = 0
            failed_commands = []
            
            for i, command in enumerate(commands):
                try:
                    # 진행률 업데이트
                    progress = int((i / len(commands)) * 100)
                    self.update_progress(progress, f"적용 중: {command['description']}")
                    
                    # 최적화된 동기 모드로 명령어 실행
                    result = self.parent.network_manager.client_thread.send_command(
                        command['cmd'],
                        command['subcmd'], 
                        command['data'],
                        wait_response=True,
                        timeout=5.0,  # 20초 -> 5초로 단축
                        sync=True
                    )
                    
                    # 결과 처리
                    if result is None:
                        raise Exception("명령어 실행 결과가 None입니다")
                    
                    if hasattr(result, 'success'):
                        if result.success:
                            self.parent.log_manager.write_log(f"[SUCCESS] {command['description']} 적용 완료", "green")
                            success_count += 1
                        else:
                            error_msg = result.message
                            self.parent.log_manager.write_log(f"[ERROR] {command['description']} 실패: {error_msg}", "red")
                            failed_commands.append(f"{command['description']} - {error_msg}")
                    else:
                        self.parent.log_manager.write_log(f"[WARNING] {command['description']}: 예상치 못한 응답 형식", "yellow")
                        success_count += 1
                    
                    # 명령어 간 최소 지연 (1초 -> 0.3초로 단축)
                    # time.sleep(0.3)
                    # 명령어 간 최소 지연 (0.3 -> 0.01)
                    time.sleep(0.01) # 속도 최적화 테스트
                    
                    
                except Exception as cmd_error:
                    error_msg = f"{command['description']}: {str(cmd_error)}"
                    self.parent.log_manager.write_log(f"[ERROR] {error_msg}", "red")
                    failed_commands.append(error_msg)
                    
                    # 심각한 오류 시 중단
                    if "연결" in str(cmd_error) or "socket" in str(cmd_error).lower():
                        self.parent.log_manager.write_log(f"[CRITICAL] 연결 오류로 중단: {cmd_error}", "red")
                        break
            
            # 진행률 완료
            self.update_progress(100, "완료")
            
            # 결과 처리
            self._handle_tab_apply_result(tab_name, success_count, len(commands), failed_commands, tab_settings)
            
        except Exception as e:
            error_msg = f"{tab_name} 탭 설정 적용 중 심각한 오류: {str(e)}"
            self.parent.log_manager.write_log(f"[CRITICAL] {error_msg}", "red")
            QMessageBox.critical(None, "심각한 오류", f"{error_msg}\n\n프로그램을 재시작해주세요.")
            
        finally:
            # 진행 상황 표시 숨기기
            self.hide_progress()
    
    def apply_tuning_to_device(self):
        """장비에 튜닝 설정 적용 - 개별 명령어로 분리 전송"""
        try:
            # 개별 명령어 목록 생성
            success, commands, msg = self.parent.tuning_manager.get_tuning_commands(self.parent.tuning_settings)
            if not success:
                raise Exception(msg)
            
            self.parent.log_manager.write_log("═══════════════════════════════════════════════════════", "white")
            self.parent.log_manager.write_log(f"[CONFIG] 전체 튜닝 설정 적용 시작 ({len(commands)}개 명령어)", "yellow")
            self.parent.log_manager.write_log("═══════════════════════════════════════════════════════", "white")
            
            # 각 명령어를 순차적으로 전송
            success_count = 0
            failed_commands = []
            
            for i, command in enumerate(commands):
                try:
                    self.parent.log_manager.write_log(f"[SEND] {i+1}/{len(commands)} - {command['description']}", "cyan")
                    
                    # 명령어 전송
                    send_msg, recv_msg = self.parent.network_manager.client_thread.send_command(
                        command['cmd'],
                        command['subcmd'],
                        command['data'],
                        wait_response=True
                    )
                    
                    if recv_msg:
                        # 응답 파싱하여 에러 코드 확인
                        if "hex=" in recv_msg:
                            response_data = recv_msg.split("hex=")[1].split(",")[0]
                            try:
                                response_bytes = bytes.fromhex(response_data)
                                from rf_protocol import RFProtocol
                                parsed = RFProtocol.parse_response(response_bytes)
                                if parsed and len(parsed['data']) >= 1:
                                    error_code = parsed['data'][0]
                                    if error_code == 0:
                                        self.parent.log_manager.write_log(f"[SUCCESS] {command['description']} 적용 완료", "green")
                                        success_count += 1
                                    else:
                                        error_msgs = {
                                            1: "범위 초과", 2: "잘못된 조건", 
                                            3: "정의되지 않음", 4: "명령어 오류"
                                        }
                                        error_msg = error_msgs.get(error_code, f"알 수 없는 오류 ({error_code})")
                                        self.parent.log_manager.write_log(f"[ERROR] {command['description']} 실패: {error_msg}", "red")
                                        failed_commands.append(f"{command['description']} - {error_msg}")
                                else:
                                    self.parent.log_manager.write_log(f"[WARNING] {command['description']}: 응답 데이터 파싱 실패", "yellow")
                                    success_count += 1
                            except Exception:
                                self.parent.log_manager.write_log(f"[WARNING] {command['description']}: 응답 파싱 오류", "yellow")
                                success_count += 1
                        else:
                            self.parent.log_manager.write_log(f"[WARNING] {command['description']}: 응답 형식 인식 실패", "yellow")
                            success_count += 1
                    else:
                        raise Exception(f"{command['description']}: 장비로부터 응답을 받지 못했습니다.")
                    
                    # 명령어 간 짧은 지연 (장비 처리 시간 확보)
                    time.sleep(0.1)
                    
                except Exception as cmd_error:
                    error_msg = f"{command['description']}: {str(cmd_error)}"
                    self.parent.log_manager.write_log(f"[ERROR] {error_msg}", "red")
                    failed_commands.append(error_msg)
            
            # 결과 요약
            self.parent.log_manager.write_log("═══════════════════════════════════════════════════════", "white")
            total_commands = len(commands)
            if success_count == total_commands:
                self.parent.log_manager.write_log(f"[SUCCESS] 모든 튜닝 설정이 성공적으로 적용되었습니다. ({success_count}/{total_commands})", "green")
            elif success_count > 0:
                self.parent.log_manager.write_log(f"[WARNING] 일부 튜닝 설정만 적용되었습니다. ({success_count}/{total_commands})", "yellow")
                if failed_commands:
                    self.parent.log_manager.write_log(f"[ERROR] 실패한 설정들: {', '.join(failed_commands)}", "red")
            else:
                self.parent.log_manager.write_log(f"[ERROR] 모든 튜닝 설정 적용에 실패했습니다.", "red")
                if failed_commands:
                    self.parent.log_manager.write_log(f"[ERROR] 실패 목록: {', '.join(failed_commands)}", "red")
                raise Exception("모든 설정 적용 실패")
            
            self.parent.log_manager.write_log("═══════════════════════════════════════════════════════", "white")
            
            # IP 주소 변경 확인
            if self.parent.tuning_settings["IP Address"] != self.parent.network_manager.client_thread.host:
                self.parent.log_manager.write_log("[INFO] IP 주소가 변경되어 연결을 재설정합니다.", "cyan")
                self.parent.network_manager.disconnect_server()
                self.parent.network_manager.client_thread.host = self.parent.tuning_settings["IP Address"]
                self.parent.network_manager.connect_server()
            
            # 성공한 설정이 있으면 정상 처리로 간주
            if success_count > 0:
                return
            
        except Exception as e:
            self.parent.log_manager.write_log(f"[ERROR] 튜닝 설정 적용 중 오류: {str(e)}", "red")
            raise e
    
    def show_progress_start(self, tab_name):
        """진행 상황 표시 시작"""
        if not self.progress_dialog:
            self.progress_dialog = QProgressDialog(self.parent)
            self.progress_dialog.setWindowTitle("설정 적용 중")
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setAutoClose(False)
            self.progress_dialog.setAutoReset(False)
            self.progress_dialog.setCancelButton(None)  # 취소 버튼 숨기기
            self.progress_dialog.setMinimumDuration(0)
        
            # 폰트 색상 스타일 적용
            self.progress_dialog.setStyleSheet("""
                QProgressDialog {
                    background-color: #1e1e2e;
                    color: #ffffff;
                    font-family: 'Roboto Mono', monospace;
                    font-size: 12px;
                }
                QProgressDialog QLabel {
                    color: #00f0ff;
                    font-weight: bold;
                    font-size: 13px;
                }
                QProgressBar {
                    border: 2px solid #00f0ff;
                    border-radius: 5px;
                    text-align: center;
                    background-color: #2e2e3e;
                }
                QProgressBar::chunk {
                    background-color: #00f0ff;
                    border-radius: 3px;
                }
            """)
        
        self.progress_dialog.setLabelText(f"{tab_name} 탭 설정을 장비에 적용하는 중...")
        self.progress_dialog.setRange(0, 100)
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()
        QApplication.processEvents()
    
    def update_progress(self, value, message=""):
        """진행률 업데이트"""
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            if message:
                current_text = self.progress_dialog.labelText().split('\n')[0]
                self.progress_dialog.setLabelText(f"{current_text}\n{message}")
            QApplication.processEvents()
    
    def hide_progress(self):
        """진행 상황 표시 숨기기"""
        if self.progress_dialog:
            self.progress_dialog.hide()
    
    def _handle_tab_apply_result(self, tab_name, success_count, total_commands, failed_commands, tab_settings):
        """탭 적용 결과 처리 - 최적화된 버전"""
        
        if success_count == total_commands:
            success_msg = f"{tab_name.upper()} 탭 모든 설정이 성공적으로 적용되었습니다. ({success_count}/{total_commands})"
            self.parent.log_manager.write_log(f"[SUCCESS] {success_msg}", "green")
            
            # 성공한 설정을 전역 설정에 반영
            self.parent.tuning_settings.update(tab_settings)
            success, msg = self.parent.tuning_manager.save_settings(self.parent.tuning_settings)
            if success:
                self.parent.log_manager.write_log(f"[CONFIG] 설정 저장 완료", "yellow")
            
            # ⭐ 네트워크 탭이고 IP가 변경되었으면 재연결 확인
            if tab_name == "network" and "IP Address" in tab_settings:
                if self.parent.network_manager.client_thread:
                    old_ip = self.parent.network_manager.client_thread.host
                    new_ip = tab_settings["IP Address"]
                    
                    if old_ip != new_ip:
                        self.parent.log_manager.write_log(f"[INFO] IP 변경 감지: {old_ip} → {new_ip}", "cyan")
                        
                        # 사용자에게 재연결 확인
                        reply = QMessageBox.question(
                            None, "재연결 확인",
                            f"IP 주소가 변경되었습니다.\n\n"
                            f"이전 IP: {old_ip}\n"
                            f"변경 IP: {new_ip}\n\n"
                            f"새 IP로 재연결하시겠습니까?",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes  # 기본값: 예
                        )
                        
                        if reply == QMessageBox.Yes:
                            # 재연결 시도
                            self.parent.log_manager.write_log("[INFO] 새 IP로 재연결 시작...", "cyan")
                            try:
                                self.parent.network_manager.disconnect_server()
                                time.sleep(0.5)  # 연결 종료 대기
                                self.parent.network_manager.connect_server()
                                self.parent.log_manager.write_log(f"[SUCCESS] {new_ip}로 재연결 시도 완료", "green")
                            except Exception as e:
                                self.parent.log_manager.write_log(f"[ERROR] 재연결 실패: {e}", "red")
                                QMessageBox.warning(None, "재연결 실패", 
                                    f"새 IP로 재연결하는 중 오류가 발생했습니다:\n\n{e}")
                        else:
                            # 사용자가 재연결 취소
                            self.parent.log_manager.write_log("[INFO] 사용자가 재연결을 취소했습니다.", "yellow")
                            QMessageBox.information(None, "안내", 
                                "설정은 저장되었습니다.\n"
                                "새 IP로 연결하려면 수동으로 재연결하세요.")
            
            # "적용 완료" 메시지 - 네트워크 탭이 아닐 때만 표시
            if not (tab_name == "network" and "IP Address" in tab_settings):
                QTimer.singleShot(100, lambda: QMessageBox.information(None, "적용 완료", success_msg))
                
        elif success_count > 0:
            warning_msg = f"{tab_name.upper()} 탭 일부 설정만 적용되었습니다. ({success_count}/{total_commands})"
            self.parent.log_manager.write_log(f"[WARNING] {warning_msg}", "yellow")
            for failed in failed_commands:
                self.parent.log_manager.write_log(f"[ERROR] 실패: {failed}", "red")
            
            QTimer.singleShot(100, lambda: QMessageBox.warning(
                None, "부분 적용", 
                f"{warning_msg}\n\n실패한 설정:\n" + "\n".join(failed_commands[:3])
            ))
            
        else:
            error_msg = f"{tab_name.upper()} 탭 모든 설정 적용에 실패했습니다."
            self.parent.log_manager.write_log(f"[ERROR] {error_msg}", "red")
            QTimer.singleShot(100, lambda: QMessageBox.critical(
                None, "적용 실패", 
                f"{error_msg}\n\n오류 목록:\n" + "\n".join(failed_commands[:3])
            ))
            raise Exception("모든 설정 적용 실패")