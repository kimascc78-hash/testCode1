"""
Data Manager Module
데이터 처리, 저장 및 설정 관리 모듈 - 튜닝 설정 개별 명령어 지원 + 0값 포함 전송
"""

import os
import json
import gzip
import datetime
import pandas as pd
import struct
from rf_protocol import RFProtocol

# 상수 설정
CONFIG_DIR = "data"


class DataManager:
    """데이터 및 설정 관리 클래스"""
    
    def __init__(self):
        self.data_log = []
        self.ensure_config_dir()
    
    def ensure_config_dir(self):
        """설정 디렉토리 생성"""
        os.makedirs(CONFIG_DIR, exist_ok=True)
    
    def add_data_entry(self, status):
        """데이터 로그에 항목 추가"""
        control_modes = {
            0: "User Port", 1: "Serial", 2: "Ethernet", 
            3: "EtherCAT", 4: "Serial+User", 5: "Ethernet+User"
        }
        
        alarm_text = "None" if status["alarm_state"] == 0 else f"Alarm 0x{status['alarm_state']:04x}"
        
        entry = {
            "Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "RF Status": "On" if status["rf_on_off"] else "Off",
            "Control Mode": control_modes.get(status["control_mode"], "Unknown"),
            "System State": f"0x{status['system_state']:04x}",
            "LED State": f"0x{status['led_state']:04x}",
            "Alarm State": alarm_text,
            "Set Power": status["set_power"],
            "Forward Power": status["forward_power"],
            "Reflect Power": status["reflect_power"],
            "Delivery Power": status["delivery_power"],
            "Frequency": status["frequency"],
            "Gamma": status["gamma"],
            "Real Gamma": status["real_gamma"],
            "Image Gamma": status["image_gamma"],
            "RF Phase": status["rf_phase"],
            "Temperature": status["temperature"],
            "Firmware Version": status["firmware_version"]
        }
        
        self.data_log.append(entry)
    
    def save_excel(self):
        """데이터를 CSV 파일로 저장"""
        if not self.data_log:
            return False, "저장할 데이터가 없습니다."
        
        try:
            df = pd.DataFrame(self.data_log)
            file_path = os.path.join(
                CONFIG_DIR, 
                f"rf_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            return True, f"데이터 저장 완료: {file_path}"
        except Exception as e:
            return False, f"데이터 저장 실패: {str(e)}"
    
    def save_log(self, log_content):
        """로그를 압축 파일로 저장"""
        try:
            file_path = os.path.join(
                CONFIG_DIR, 
                f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt.gz"
            )
            
            with gzip.open(file_path, "wt", encoding="utf-8") as f:
                # 최근 100줄만 저장
                log_lines = log_content.split('\n')[-100:]
                for line in log_lines:
                    f.write(f"{line}\n")
            
            return True, f"로그 저장 완료 (압축): {file_path}"
        except Exception as e:
            return False, f"로그 저장 실패: {str(e)}"
    
    def clear_data_log(self):
        """데이터 로그 초기화"""
        self.data_log.clear()
    
    def get_data_count(self):
        """데이터 로그 개수 반환"""
        return len(self.data_log)

##
    # ========================================
    # === VHF Pulse 명령어 데이터 생성 함수 ===
    # ========================================

    def create_pulse_mode_data(self, settings):
        """Pulse 모드 설정 데이터 생성 - VHF 매뉴얼 기준 (1바이트)"""
        try:
            pulse_mode_map = {
                "OFF": 0,           # CW mode
                "Pulse 0": 1,       # pulse 0 only
                "Pulse 0,1": 2,     # pulse 0 and 1
                "Pulse 0,1,2": 3    # pulse 0, 1, and 2
            }
            
            mode = pulse_mode_map.get(settings.get("Pulse Mode", "OFF"), 0)
            data = struct.pack('<B', mode)  # 1바이트
            
            return True, data, "Pulse 모드 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"Pulse 모드 데이터 생성 실패: {str(e)}"

    def create_pulse_params_data(self, settings):
        """Pulse 시간 파라미터 데이터 생성 - VHF 매뉴얼 33바이트 (Page 19-20)"""
        try:
            data = bytearray()
            
            # Pulse 0: high duty, low duty, repeat times (12바이트)
            data.extend(struct.pack('<I', int(settings.get("Pulse0 High Duty", 1000))))   # 4byte (us)
            data.extend(struct.pack('<I', int(settings.get("Pulse0 Low Duty", 1000))))    # 4byte (us)
            data.extend(struct.pack('<I', int(settings.get("Pulse0 Repeat", 1))))         # 4byte
            
            # Pulse 1: high duty, low duty, repeat times (12바이트)
            data.extend(struct.pack('<I', int(settings.get("Pulse1 High Duty", 1000))))   # 4byte (us)
            data.extend(struct.pack('<I', int(settings.get("Pulse1 Low Duty", 1000))))    # 4byte (us)
            data.extend(struct.pack('<I', int(settings.get("Pulse1 Repeat", 1))))         # 4byte
            
            # Pulse 2: high duty, low duty (8바이트, repeat 없음)
            data.extend(struct.pack('<I', int(settings.get("Pulse2 High Duty", 1000))))   # 4byte (us)
            data.extend(struct.pack('<I', int(settings.get("Pulse2 Low Duty", 1000))))    # 4byte (us)
            
            # 총 32바이트, 매뉴얼은 33바이트이므로 1바이트 패딩
            data.extend(b'\x00')
            
            if len(data) != 33:
                return False, None, f"Pulse 파라미터 데이터 길이 오류: {len(data)}바이트 (기대: 33바이트)"
            
            return True, bytes(data), "Pulse 파라미터 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"Pulse 파라미터 데이터 생성 실패: {str(e)}"

    # ========================================
    # === Bank Function 데이터 생성 함수 ===
    # ========================================

    def create_bank_enable_data(self, bank_num, enable):
        """Bank Enable/Disable 데이터 생성 (4바이트)"""
        try:
            data = struct.pack('<I', 1 if enable else 0)  # uint32
            return True, data, f"Bank{bank_num} Enable 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Bank Enable 데이터 생성 실패: {str(e)}"

    def create_bank_equation_enable_data(self, bank_num, enable):
        """Bank Equation Enable/Disable 데이터 생성 (4바이트)"""
        try:
            data = struct.pack('<I', 1 if enable else 0)  # uint32
            return True, data, f"Bank{bank_num} Equation Enable 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Bank Equation Enable 데이터 생성 실패: {str(e)}"

    def create_bank_restart_data(self, bank_num):
        """Bank Restart 데이터 생성 (4바이트)"""
        try:
            data = struct.pack('<I', 1)  # uint32, 1=restart
            return True, data, f"Bank{bank_num} Restart 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Bank Restart 데이터 생성 실패: {str(e)}"

    def create_bank_rf_trigger_data(self, bank_num):
        """Bank RF Trigger 데이터 생성 (4바이트)"""
        try:
            data = struct.pack('<I', 1)  # uint32, 1=trigger
            return True, data, f"Bank{bank_num} RF Trigger 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Bank RF Trigger 데이터 생성 실패: {str(e)}"

    def create_bank_params_data(self, settings, bank_num):
        """Bank Parameters 데이터 생성 - 20바이트 (VHF 매뉴얼 Page 38-39)
        
        방정식: Y(n) = A*X(n)^3 + B*X(n)^2 + C*X(n) + D
        X(0): 초기값
        X(n+1) = Y(n)
        """
        try:
            data = bytearray()
            
            # X(0): initial value (float, 4byte)
            x0 = float(settings.get(f"Bank{bank_num} X0", 1.0))
            data.extend(struct.pack('<f', x0))
            
            # A: constant (float, 4byte)
            a = float(settings.get(f"Bank{bank_num} A", 0.0))
            data.extend(struct.pack('<f', a))
            
            # B: constant (float, 4byte)
            b = float(settings.get(f"Bank{bank_num} B", 0.0))
            data.extend(struct.pack('<f', b))
            
            # C: constant (float, 4byte)
            c = float(settings.get(f"Bank{bank_num} C", 1.0))
            data.extend(struct.pack('<f', c))
            
            # D: constant (float, 4byte)
            d = float(settings.get(f"Bank{bank_num} D", 0.0))
            data.extend(struct.pack('<f', d))
            
            if len(data) != 20:
                return False, None, f"Bank{bank_num} Parameters 데이터 길이 오류: {len(data)}바이트"
            
            return True, bytes(data), f"Bank{bank_num} Parameters 데이터 생성 완료 (X0={x0}, A={a}, B={b}, C={c}, D={d})"
            
        except Exception as e:
            return False, None, f"Bank{bank_num} Parameters 데이터 생성 실패: {str(e)}"
##

class TuningSettingsManager:
    """튜닝 설정 관리 클래스 - 개별 명령어 지원 + 0값 포함 전송"""
    
    def __init__(self):
        self.settings_file = os.path.join(CONFIG_DIR, "tuning_settings.json")
        self.default_settings = {
            "Control Mode": "User Port",
            "Regulation Mode": "Forward Power",
            "Ramp Mode": "Disable",
            "Ramp Up Time": "0",
            "Ramp Down Time": "0",
            "CEX Enable": "Disable",
            "CEX Mode": "Master",
            "CEX Output Phase": "0",
            "RF Output Phase": "0",
            "Pulse Mode": "Master",
            "Pulse On/Off": "Off (CW)",
            "Pulse Duty": "0",
            "Output Sync": "0",
            "Input Sync": "0",
            "Pulse Frequency": "0",
            "Freq Tuning": "Disable",
            "Retuning Mode": "One-Time",
            "Setting Mode": "Fixed",
            "Min Frequency": "0",
            "Max Frequency": "0",
            "Start Frequency": "0",
            "Min Step": "0",
            "Max Step": "0",
            "Stop Gamma": "0",
            "Return Gamma": "0",
            "Set RF Frequency": "0",
             # === Bank Function 설정 추가 ===
            "Bank1 Enable": "Disable",
            "Bank1 Equation Enable": "Disable",
            "Bank1 X0": "1.0",
            "Bank1 A": "0.0",
            "Bank1 B": "0.0",
            "Bank1 C": "1.0",
            "Bank1 D": "0.0",
            "Bank2 Enable": "Disable",
            "Bank2 Equation Enable": "Disable",
            "Bank2 X0": "1.0",
            "Bank2 A": "0.0",
            "Bank2 B": "0.0",
            "Bank2 C": "1.0",
            "Bank2 D": "0.0",
            
            # 네트워크
            "IP Address": "127.0.0.1",
            "Subnet Mask": "255.255.255.0",
            "Gateway": "192.168.0.1",
            "DNS": "0.0.0.0"
        }
        os.makedirs(CONFIG_DIR, exist_ok=True)
    
    def load_settings(self):
        """설정 파일에서 로드"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # 기본 설정에 로드된 설정을 업데이트
                    settings = self.default_settings.copy()
                    settings.update(loaded_settings)
                    return True, settings, "저장된 튜닝 설정을 로드했습니다."
            except Exception as e:
                return False, self.default_settings.copy(), f"튜닝 설정 로드 실패: {str(e)}"
        else:
            return True, self.default_settings.copy(), "기본 튜닝 설정을 사용합니다."
    
    def save_settings(self, settings):
        """설정을 파일에 저장"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return True, "튜닝 설정이 저장되었습니다."
        except Exception as e:
            return False, f"튜닝 설정 저장 실패: {str(e)}"
    
    def create_control_mode_data(self, settings):
        """제어 모드 설정 데이터 생성"""
        try:
            control_mode_map = {
                "User Port": 0, "Serial": 1, "Ethernet": 2, 
                "EtherCAT": 3, "Serial+User": 4, "Ethernet+User": 5
            }
            
            mode = control_mode_map.get(settings["Control Mode"], 0)
            data = struct.pack('<H', mode)  # 2바이트 (매뉴얼 기준)
            
            return True, data, "제어 모드 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"제어 모드 데이터 생성 실패: {str(e)}"
    
    def create_regulation_mode_data(self, settings):
        """조절 모드 설정 데이터 생성"""
        try:
            regulation_mode_map = {
                "Forward Power": 0, "Load Power": 1, "Voltage": 2, "Current": 3
            }
            
            mode = regulation_mode_map.get(settings["Regulation Mode"], 0)
            data = struct.pack('<H', mode)  # 2바이트 (매뉴얼 기준)
            
            return True, data, "조절 모드 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"조절 모드 데이터 생성 실패: {str(e)}"
    
    def create_ramp_config_data(self, settings):
        """램프 설정 데이터 생성 (매뉴얼 기준 20바이트)"""
        try:
            # 램프 모드 변환
            ramp_mode = 1 if settings["Ramp Mode"] == "Enable" else 0
            
            # 시간값을 밀리초로 변환
            ramp_up_time = int(float(settings["Ramp Up Time"]))
            ramp_down_time = int(float(settings["Ramp Down Time"]))
            
            # 매뉴얼에 따른 20바이트 구조 (5개의 UINT)
            # Byte[3:0] : Ramp Mode (4 bytes)
            # Byte[7:4] : Ramp Up Time (4 bytes)  
            # Byte[11:8] : Ramp Down Time (4 bytes)
            # Byte[15:12] : Reserved (4 bytes)
            # Byte[19:16] : Reserved (4 bytes)
            data = struct.pack('<IIIII', 
                              ramp_mode,      # 4바이트: 램프 모드
                              ramp_up_time,   # 4바이트: 램프 업 시간
                              ramp_down_time, # 4바이트: 램프 다운 시간
                              0,              # 4바이트: 예약 영역 1
                              0)              # 4바이트: 예약 영역 2
            
            return True, data, "램프 설정 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"램프 설정 데이터 생성 실패: {str(e)}"
    
    def create_cex_config_data(self, settings):
        """CEX 설정 데이터 생성 (매뉴얼 기준 12바이트)"""
        try:
            # CEX Enable/Disable
            cex_enable = 1 if settings["CEX Enable"] == "Enable" else 0
            
            # CEX Mode (Master/Slave)
            cex_mode = 0 if settings["CEX Mode"] == "Master" else 1
            
            # Phase 값들
            cex_output_phase = float(settings["CEX Output Phase"])
            rf_output_phase = float(settings["RF Output Phase"])
            
            # 매뉴얼에 따른 12바이트 구조 (패딩 바이트 제거)
            # Byte[1:0] : CEX Enable/Disable (2 bytes)
            # Byte[3:2] : CEX Mode (2 bytes)
            # Byte[7:4] : CEX Output Phase Offset (4 bytes float)
            # Byte[11:8] : RF Output Phase Offset (4 bytes float)
            data = struct.pack('<HHff', 
                              cex_enable,       # 2바이트: CEX Enable
                              cex_mode,         # 2바이트: CEX Mode
                              cex_output_phase, # 4바이트: CEX Output Phase
                              rf_output_phase)  # 4바이트: RF Output Phase
            
            return True, data, "CEX 설정 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"CEX 설정 데이터 생성 실패: {str(e)}"
    
    def create_pulse_mode_data(self, settings):
        """펄스 모드 설정 데이터 생성"""
        try:
            pulse_mode = 0 if settings["Pulse Mode"] == "Master" else 1
            data = struct.pack('<B', pulse_mode)  # 1바이트
            
            return True, data, "펄스 모드 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"펄스 모드 데이터 생성 실패: {str(e)}"
    
    def create_pulse_onoff_data(self, settings):
        """펄스 On/Off 설정 데이터 생성"""
        try:
            pulse_onoff = 1 if settings["Pulse On/Off"] == "On (Pulse)" else 0
            data = struct.pack('<B', pulse_onoff)  # 1바이트
            
            return True, data, "펄스 On/Off 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"펄스 On/Off 데이터 생성 실패: {str(e)}"
    
    def create_pulse_duty_data(self, settings):
        """펄스 듀티 설정 데이터 생성 (16바이트)"""
        try:
            pulse_duty = float(settings["Pulse Duty"])
            
            # 매뉴얼에 따르면 4개의 float 값 (16바이트)
            # 첫 번째는 실제 듀티값, 나머지는 예약 파라미터
            data = struct.pack('<ffff', 
                              pulse_duty,     # 메인 듀티 값
                              0.0,           # 예약 파라미터 1
                              0.0,           # 예약 파라미터 2  
                              0.0)           # 예약 파라미터 3
            
            return True, data, "펄스 듀티 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"펄스 듀티 데이터 생성 실패: {str(e)}"
    
    def create_pulse_output_sync_data(self, settings):
        """펄스 출력 동기 설정 데이터 생성"""
        try:
            output_sync = int(float(settings["Output Sync"]))
            data = struct.pack('<I', output_sync)  # 4바이트
            
            return True, data, "펄스 출력 동기 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"펄스 출력 동기 데이터 생성 실패: {str(e)}"

    def create_pulse_input_sync_data(self, settings):
        """펄스 입력 동기 설정 데이터 생성"""
        try:
            input_sync = int(float(settings["Input Sync"]))
            data = struct.pack('<I', input_sync)  # 4바이트
            
            return True, data, "펄스 입력 동기 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"펄스 입력 동기 데이터 생성 실패: {str(e)}"
    
    def create_pulse_frequency_data(self, settings):
        """펄스 주파수 설정 데이터 생성"""
        try:
            pulse_freq = int(float(settings["Pulse Frequency"]))
            data = struct.pack('<I', pulse_freq)  # 4바이트
            
            return True, data, "펄스 주파수 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"펄스 주파수 데이터 생성 실패: {str(e)}"
    
    def create_rf_frequency_data(self, settings):
        """RF 주파수 설정 데이터 생성"""
        try:
            rf_freq = int(float(settings["Set RF Frequency"]) * 1000000)  # MHz to Hz
            data = struct.pack('<I', rf_freq)  # 4바이트
            
            return True, data, "RF 주파수 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"RF 주파수 데이터 생성 실패: {str(e)}"
            
            
    #####
    def create_freq_tuning_enable_data(self, settings):
        """주파수 튜닝 활성화/비활성화 설정"""
        try:
            enable = 1 if settings["Freq Tuning"] == "Enable" else 0
            data = struct.pack('<B', enable)  # 1바이트
            
            return True, data, "주파수 튜닝 활성화 설정"
            
        except Exception as e:
            return False, None, f"주파수 튜닝 활성화 데이터 생성 실패: {str(e)}"

    def create_freq_tuning_retuning_data(self, settings):
        """재튜닝 모드 설정"""
        try:
            retuning_mode_map = {
                "One-Time": 0, "Continuous": 1, "Auto": 2
            }
            
            mode = retuning_mode_map.get(settings["Retuning Mode"], 0)
            data = struct.pack('<H', mode)  # 2바이트 (USHORT)
            
            return True, data, "재튜닝 모드 설정"
            
        except Exception as e:
            return False, None, f"재튜닝 모드 데이터 생성 실패: {str(e)}"

    def create_freq_tuning_setting_mode_data(self, settings):
        """주파수 설정 모드"""
        try:
            setting_mode_map = {
                "Fixed": 0, "Variable": 1, "Sweep": 2
            }
            
            mode = setting_mode_map.get(settings["Setting Mode"], 0)
            data = struct.pack('<H', mode)  # 2바이트 (USHORT)
            
            return True, data, "주파수 설정 모드"
            
        except Exception as e:
            return False, None, f"주파수 설정 모드 데이터 생성 실패: {str(e)}"

    def create_freq_tuning_min_freq_data(self, settings):
        """최소 주파수 설정"""
        try:
            min_freq = int(float(settings["Min Frequency"]) * 1000000)  # MHz to Hz
            data = struct.pack('<I', min_freq)  # 4바이트 (UINT)
            
            return True, data, "최소 주파수 설정"
            
        except Exception as e:
            return False, None, f"최소 주파수 데이터 생성 실패: {str(e)}"

    def create_freq_tuning_max_freq_data(self, settings):
        """최대 주파수 설정"""
        try:
            max_freq = int(float(settings["Max Frequency"]) * 1000000)  # MHz to Hz
            data = struct.pack('<I', max_freq)  # 4바이트 (UINT)
            
            return True, data, "최대 주파수 설정"
            
        except Exception as e:
            return False, None, f"최대 주파수 데이터 생성 실패: {str(e)}"

    def create_freq_tuning_start_freq_data(self, settings):
        """시작 주파수 설정"""
        try:
            start_freq = int(float(settings["Start Frequency"]) * 1000000)  # MHz to Hz
            data = struct.pack('<I', start_freq)  # 4바이트 (UINT)
            
            return True, data, "시작 주파수 설정"
            
        except Exception as e:
            return False, None, f"시작 주파수 데이터 생성 실패: {str(e)}"

    def create_freq_tuning_min_step_data(self, settings):
        """최소 스텝 설정"""
        try:
            min_step = int(float(settings["Min Step"]) * 1000)  # kHz to Hz
            data = struct.pack('<I', min_step)  # 4바이트 (UINT)
            
            return True, data, "최소 스텝 설정"
            
        except Exception as e:
            return False, None, f"최소 스텝 데이터 생성 실패: {str(e)}"

    def create_freq_tuning_max_step_data(self, settings):
        """최대 스텝 설정"""
        try:
            max_step = int(float(settings["Max Step"]) * 1000)  # kHz to Hz
            data = struct.pack('<I', max_step)  # 4바이트 (UINT)
            
            return True, data, "최대 스텝 설정"
            
        except Exception as e:
            return False, None, f"최대 스텝 데이터 생성 실패: {str(e)}"

    def create_freq_tuning_stop_gamma_data(self, settings):
        """정지 감마 설정"""
        try:
            stop_gamma = float(settings["Stop Gamma"])
            data = struct.pack('<f', stop_gamma)  # 4바이트 (FLOAT)
            
            return True, data, "정지 감마 설정"
            
        except Exception as e:
            return False, None, f"정지 감마 데이터 생성 실패: {str(e)}"

    def create_freq_tuning_return_gamma_data(self, settings):
        """복귀 감마 설정"""
        try:
            return_gamma = float(settings["Return Gamma"])
            data = struct.pack('<f', return_gamma)  # 4바이트 (FLOAT)
            
            return True, data, "복귀 감마 설정"
            
        except Exception as e:
            return False, None, f"복귀 감마 데이터 생성 실패: {str(e)}"
    #####
    # ========================================
    # === Bank Function 명령어 생성 함수 ===
    # ========================================

    def create_bank1_enable_data(self, settings):
        """Bank1 Enable 데이터 생성"""
        try:
            enable = 1 if settings.get("Bank1 Enable", "Disable") == "Enable" else 0
            data = struct.pack('<I', enable)
            return True, data, "Bank1 Enable 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Bank1 Enable 데이터 생성 실패: {str(e)}"

    def create_bank1_equation_enable_data(self, settings):
        """Bank1 Equation Enable 데이터 생성"""
        try:
            enable = 1 if settings.get("Bank1 Equation Enable", "Disable") == "Enable" else 0
            data = struct.pack('<I', enable)
            return True, data, "Bank1 Equation Enable 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Bank1 Equation Enable 데이터 생성 실패: {str(e)}"

    def create_bank1_params_data(self, settings):
        """Bank1 Parameters 데이터 생성 (20바이트)"""
        try:
            data = bytearray()
            data.extend(struct.pack('<f', float(settings.get("Bank1 X0", 1.0))))
            data.extend(struct.pack('<f', float(settings.get("Bank1 A", 0.0))))
            data.extend(struct.pack('<f', float(settings.get("Bank1 B", 0.0))))
            data.extend(struct.pack('<f', float(settings.get("Bank1 C", 1.0))))
            data.extend(struct.pack('<f', float(settings.get("Bank1 D", 0.0))))
            
            if len(data) != 20:
                return False, None, f"Bank1 Parameters 길이 오류: {len(data)}바이트"
            
            return True, bytes(data), "Bank1 Parameters 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Bank1 Parameters 데이터 생성 실패: {str(e)}"

    def create_bank2_enable_data(self, settings):
        """Bank2 Enable 데이터 생성"""
        try:
            enable = 1 if settings.get("Bank2 Enable", "Disable") == "Enable" else 0
            data = struct.pack('<I', enable)
            return True, data, "Bank2 Enable 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Bank2 Enable 데이터 생성 실패: {str(e)}"

    def create_bank2_equation_enable_data(self, settings):
        """Bank2 Equation Enable 데이터 생성"""
        try:
            enable = 1 if settings.get("Bank2 Equation Enable", "Disable") == "Enable" else 0
            data = struct.pack('<I', enable)
            return True, data, "Bank2 Equation Enable 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Bank2 Equation Enable 데이터 생성 실패: {str(e)}"

    def create_bank2_params_data(self, settings):
        """Bank2 Parameters 데이터 생성 (20바이트)"""
        try:
            data = bytearray()
            data.extend(struct.pack('<f', float(settings.get("Bank2 X0", 1.0))))
            data.extend(struct.pack('<f', float(settings.get("Bank2 A", 0.0))))
            data.extend(struct.pack('<f', float(settings.get("Bank2 B", 0.0))))
            data.extend(struct.pack('<f', float(settings.get("Bank2 C", 1.0))))
            data.extend(struct.pack('<f', float(settings.get("Bank2 D", 0.0))))
            
            if len(data) != 20:
                return False, None, f"Bank2 Parameters 길이 오류: {len(data)}바이트"
            
            return True, bytes(data), "Bank2 Parameters 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Bank2 Parameters 데이터 생성 실패: {str(e)}"
    #####
    def create_pulse_mode_data(self, settings):
        """Pulse 모드 설정 데이터 생성 - VHF 매뉴얼 기준 (1바이트)"""
        try:
            pulse_mode_map = {
                "OFF": 0,
                "Pulse 0": 1,
                "Pulse 0,1": 2,
                "Pulse 0,1,2": 3
            }
            
            mode = pulse_mode_map.get(settings.get("Pulse Mode", "OFF"), 0)
            data = struct.pack('<B', mode)
            
            return True, data, "Pulse 모드 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"Pulse 모드 데이터 생성 실패: {str(e)}"

    def create_pulse_params_data(self, settings):
        """Pulse 시간 파라미터 데이터 생성 - VHF 매뉴얼 33바이트"""
        try:
            data = bytearray()
            
            # Pulse 0: 12바이트
            data.extend(struct.pack('<I', int(settings.get("Pulse0 High Duty", 1000))))
            data.extend(struct.pack('<I', int(settings.get("Pulse0 Low Duty", 1000))))
            data.extend(struct.pack('<I', int(settings.get("Pulse0 Repeat", 1))))
            
            # Pulse 1: 12바이트
            data.extend(struct.pack('<I', int(settings.get("Pulse1 High Duty", 1000))))
            data.extend(struct.pack('<I', int(settings.get("Pulse1 Low Duty", 1000))))
            data.extend(struct.pack('<I', int(settings.get("Pulse1 Repeat", 1))))
            
            # Pulse 2: 8바이트
            data.extend(struct.pack('<I', int(settings.get("Pulse2 High Duty", 1000))))
            data.extend(struct.pack('<I', int(settings.get("Pulse2 Low Duty", 1000))))
            
            # 패딩 1바이트
            data.extend(b'\x00')
            
            if len(data) != 33:
                return False, None, f"Pulse 파라미터 데이터 길이 오류: {len(data)}바이트"
            
            return True, bytes(data), "Pulse 파라미터 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"Pulse 파라미터 데이터 생성 실패: {str(e)}"
    #####
    def get_tuning_commands(self, settings):
        """튜닝 설정을 개별 명령어로 분리하여 반환 - 주파수 튜닝 명령어 추가"""
        commands = []
        
        try:
            # 1. 제어 모드 설정 (항상 전송)
            success, data, msg = self.create_control_mode_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_CONTROL_MODE_SET,
                    'subcmd': RFProtocol.SUBCMD_CONTROL_MODE_SET,
                    'data': data,
                    'description': '제어 모드 설정'
                })
            
            # 2. 조절 모드 설정 (항상 전송)
            success, data, msg = self.create_regulation_mode_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_REGULATION_MODE_SET,
                    'subcmd': RFProtocol.SUBCMD_REGULATION_MODE_SET,
                    'data': data,
                    'description': '조절 모드 설정'
                })
            
            # 3. 램프 설정 (항상 전송 - 0값도 포함)
            success, data, msg = self.create_ramp_config_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_RAMP_CONFIG_SET,
                    'subcmd': RFProtocol.SUBCMD_RAMP_CONFIG_SET,
                    'data': data,
                    'description': '램프 설정'
                })
            
            # 4. CEX 설정 (항상 전송 - 0값도 포함)
            success, data, msg = self.create_cex_config_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_CEX_CONFIG_SET,
                    'subcmd': RFProtocol.SUBCMD_CEX_CONFIG_SET,
                    'data': data,
                    'description': 'CEX 설정'
                })
            ########
            # 5. 펄스 설정 (VHF 매뉴얼 기준)
            # Pulse 모드 설정
            success, data, msg = self.create_pulse_mode_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_PULSE_SET,
                    'subcmd': RFProtocol.SUBCMD_PULSE_MODE_SET,
                    'data': data,
                    'description': '펄스 모드 설정'
                })

            # Pulse 파라미터 설정
            success, data, msg = self.create_pulse_params_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_PULSE_SET,
                    'subcmd': RFProtocol.SUBCMD_PULSE_PARAMS_SET,
                    'data': data,
                    'description': '펄스 파라미터 설정'
                })
            ########
            
            # 6. RF 주파수 설정 (0값도 전송)
            success, data, msg = self.create_rf_frequency_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_SET_FREQUENCY,
                    'subcmd': RFProtocol.SUBCMD_SET_FREQUENCY,
                    'data': data,
                    'description': 'RF 주파수 설정'
                })
            
            # 7. 주파수 튜닝 설정들 (새로 추가) ===========================
            
            # 주파수 튜닝 활성화/비활성화
            success, data, msg = self.create_freq_tuning_enable_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                    'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_ENABLE,
                    'data': data,
                    'description': '주파수 튜닝 활성화 설정'
                })
            
            # 재튜닝 모드 설정
            success, data, msg = self.create_freq_tuning_retuning_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                    'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_RETUNING,
                    'data': data,
                    'description': '재튜닝 모드 설정'
                })
            
            # 주파수 설정 모드
            success, data, msg = self.create_freq_tuning_setting_mode_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                    'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_MODE,
                    'data': data,
                    'description': '주파수 설정 모드'
                })
            
            # 최소 주파수
            success, data, msg = self.create_freq_tuning_min_freq_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                    'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_MIN_FREQ,
                    'data': data,
                    'description': '최소 주파수 설정'
                })
            
            # 최대 주파수
            success, data, msg = self.create_freq_tuning_max_freq_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                    'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_MAX_FREQ,
                    'data': data,
                    'description': '최대 주파수 설정'
                })
            
            # 시작 주파수
            success, data, msg = self.create_freq_tuning_start_freq_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                    'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_START_FREQ,
                    'data': data,
                    'description': '시작 주파수 설정'
                })
            
            # 최소 스텝
            success, data, msg = self.create_freq_tuning_min_step_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                    'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_MIN_STEP,
                    'data': data,
                    'description': '최소 스텝 설정'
                })
            
            # 최대 스텝
            success, data, msg = self.create_freq_tuning_max_step_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                    'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_MAX_STEP,
                    'data': data,
                    'description': '최대 스텝 설정'
                })
            
            # 정지 감마
            success, data, msg = self.create_freq_tuning_stop_gamma_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                    'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_STOP_GAMMA,
                    'data': data,
                    'description': '정지 감마 설정'
                })
            
            # 복귀 감마
            success, data, msg = self.create_freq_tuning_return_gamma_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                    'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_RETURN_GAMMA,
                    'data': data,
                    'description': '복귀 감마 설정'
                })
            
            # ================================================================
            
            return True, commands, f"총 {len(commands)}개의 설정 명령어 생성 완료 (주파수 튜닝 포함)"
            
        except Exception as e:
            return False, [], f"명령어 생성 실패: {str(e)}"
    #####
    #####
    def get_tab_commands(self, tab_name, settings):
        """특정 탭의 명령어만 생성 - 주파수 튜닝 명령어 추가"""
        commands = []
        
        try:
            if tab_name == "control":
                # 제어 모드 설정
                success, data, msg = self.create_control_mode_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_CONTROL_MODE_SET,
                        'subcmd': RFProtocol.SUBCMD_CONTROL_MODE_SET,
                        'data': data,
                        'description': '제어 모드 설정'
                    })
                
                # 조절 모드 설정
                success, data, msg = self.create_regulation_mode_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_REGULATION_MODE_SET,
                        'subcmd': RFProtocol.SUBCMD_REGULATION_MODE_SET,
                        'data': data,
                        'description': '조절 모드 설정'
                    })
                    
            elif tab_name == "ramp":
                # 램프 설정
                success, data, msg = self.create_ramp_config_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_RAMP_CONFIG_SET,
                        'subcmd': RFProtocol.SUBCMD_RAMP_CONFIG_SET,
                        'data': data,
                        'description': '램프 설정'
                    })
                    
            elif tab_name == "cex":
                # CEX 설정
                success, data, msg = self.create_cex_config_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_CEX_CONFIG_SET,
                        'subcmd': RFProtocol.SUBCMD_CEX_CONFIG_SET,
                        'data': data,
                        'description': 'CEX 설정'
                    })
                    
            elif tab_name == "pulse":
                # === VHF 매뉴얼 기준 Pulse 명령어 (수정) ===
    
                # Pulse 모드 설정 (CMD=0x02, SUBCMD=0x03)
                success, data, msg = self.create_pulse_mode_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_PULSE_SET,  # 수정됨
                        'subcmd': RFProtocol.SUBCMD_PULSE_MODE_SET,  # 수정됨
                        'data': data,
                        'description': '펄스 모드 설정'
                    })
                
                # Pulse 파라미터 설정 (CMD=0x02, SUBCMD=0x05, 33바이트)
                success, data, msg = self.create_pulse_params_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_PULSE_SET,  # 수정됨
                        'subcmd': RFProtocol.SUBCMD_PULSE_PARAMS_SET,  # 수정됨
                        'data': data,
                        'description': '펄스 파라미터 설정'
                    })
                    
            elif tab_name == "frequency":
                # RF 주파수 설정 (기존)
                success, data, msg = self.create_rf_frequency_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_SET_FREQUENCY,
                        'subcmd': RFProtocol.SUBCMD_SET_FREQUENCY,
                        'data': data,
                        'description': 'RF 주파수 설정'
                    })
                
                # === 새로 추가: 주파수 튜닝 관련 명령어들 ===
                
                # 주파수 튜닝 활성화/비활성화
                success, data, msg = self.create_freq_tuning_enable_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                        'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_ENABLE,
                        'data': data,
                        'description': '주파수 튜닝 활성화 설정'
                    })
                
                # 재튜닝 모드 설정
                success, data, msg = self.create_freq_tuning_retuning_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                        'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_RETUNING,
                        'data': data,
                        'description': '재튜닝 모드 설정'
                    })
                
                # 주파수 설정 모드
                success, data, msg = self.create_freq_tuning_setting_mode_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                        'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_MODE,
                        'data': data,
                        'description': '주파수 설정 모드'
                    })
                
                # 최소 주파수
                success, data, msg = self.create_freq_tuning_min_freq_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                        'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_MIN_FREQ,
                        'data': data,
                        'description': '최소 주파수 설정'
                    })
                
                # 최대 주파수
                success, data, msg = self.create_freq_tuning_max_freq_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                        'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_MAX_FREQ,
                        'data': data,
                        'description': '최대 주파수 설정'
                    })
                
                # 시작 주파수
                success, data, msg = self.create_freq_tuning_start_freq_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                        'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_START_FREQ,
                        'data': data,
                        'description': '시작 주파수 설정'
                    })
                
                # 최소 스텝
                success, data, msg = self.create_freq_tuning_min_step_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                        'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_MIN_STEP,
                        'data': data,
                        'description': '최소 스텝 설정'
                    })
                
                # 최대 스텝
                success, data, msg = self.create_freq_tuning_max_step_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                        'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_MAX_STEP,
                        'data': data,
                        'description': '최대 스텝 설정'
                    })
                
                # 정지 감마
                success, data, msg = self.create_freq_tuning_stop_gamma_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                        'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_STOP_GAMMA,
                        'data': data,
                        'description': '정지 감마 설정'
                    })
                
                # 복귀 감마
                success, data, msg = self.create_freq_tuning_return_gamma_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_FREQUENCY_TUNING,
                        'subcmd': RFProtocol.SUBCMD_FREQ_TUNING_RETURN_GAMMA,
                        'data': data,
                        'description': '복귀 감마 설정'
                    })
                
                # ================================================
            #####
            elif tab_name == "bank":
                # === Bank Function 설정 ===
                
                # Bank1 Enable
                success, data, msg = self.create_bank1_enable_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_BANK_SET,
                        'subcmd': RFProtocol.SUBCMD_BANK1_ENABLE,
                        'data': data,
                        'description': 'Bank1 활성화 설정'
                    })
                
                # Bank1 Equation Enable
                success, data, msg = self.create_bank1_equation_enable_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_BANK_SET,
                        'subcmd': RFProtocol.SUBCMD_BANK1_EQUATION_ENABLE,
                        'data': data,
                        'description': 'Bank1 방정식 활성화'
                    })
                
                # Bank1 Parameters
                success, data, msg = self.create_bank1_params_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_BANK_SET,
                        'subcmd': RFProtocol.SUBCMD_BANK1_PARAMS,
                        'data': data,
                        'description': 'Bank1 파라미터 설정'
                    })
                
                # Bank2 Enable
                success, data, msg = self.create_bank2_enable_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_BANK_SET,
                        'subcmd': RFProtocol.SUBCMD_BANK2_ENABLE,
                        'data': data,
                        'description': 'Bank2 활성화 설정'
                    })
                
                # Bank2 Equation Enable
                success, data, msg = self.create_bank2_equation_enable_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_BANK_SET,
                        'subcmd': RFProtocol.SUBCMD_BANK2_EQUATION_ENABLE,
                        'data': data,
                        'description': 'Bank2 방정식 활성화'
                    })
                
                # Bank2 Parameters
                success, data, msg = self.create_bank2_params_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_BANK_SET,
                        'subcmd': RFProtocol.SUBCMD_BANK2_PARAMS,
                        'data': data,
                        'description': 'Bank2 파라미터 설정'
                    })
            #####
            elif tab_name == "network":
                # 네트워크 설정은 장비로 전송하지 않음 (클라이언트 설정만)
                # 하지만 빈 명령어 목록이 아닌 정보성 메시지 반환
                pass
            
            return True, commands, f"{tab_name} 탭 {len(commands)}개 명령어 생성 완료"
            
        except Exception as e:
            return False, [], f"{tab_name} 탭 명령어 생성 실패: {str(e)}"
    #####
    
class StatusParser:
    """상태 데이터 파싱 클래스"""
    
    @staticmethod
    def parse_device_status(data):
        """장비 상태 데이터 파싱 - VHF 매뉴얼 56바이트 버전"""
        # === 수정: 길이 검증 52 -> 56 ===
        if len(data) != 56:
            raise ValueError(f"예상치 못한 데이터 길이: {len(data)}, 기대=56 (VHF 매뉴얼 기준)")
        
        try:
            status = {}
            offset = 0
            
            # === HF와 동일: Byte 0 ===
            status["rf_on_off"] = struct.unpack('<B', data[offset:offset+1])[0]
            offset += 1
            
            # === HF와 동일: Byte 1 ===
            status["control_mode"] = struct.unpack('<B', data[offset:offset+1])[0]
            offset += 1
            
            # === HF와 동일: Bytes 2-3 ===
            status["system_state"] = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            # === HF와 동일: Bytes 4-5 ===
            status["led_state"] = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            # === HF와 동일: Bytes 6-7 ===
            status["alarm_state"] = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            # === HF와 동일: Bytes 8-11 ===
            status["set_power"] = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            
            # === HF와 동일: Bytes 12-15 ===
            status["forward_power"] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # === HF와 동일: Bytes 16-19 ===
            status["reflect_power"] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # === HF와 동일: Bytes 20-23 ===
            status["delivery_power"] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # === HF와 동일: Bytes 24-27 (Hz를 MHz로 변환) ===
            status["frequency"] = struct.unpack('<f', data[offset:offset+4])[0] / 1_000_000
            offset += 4
            
            # === HF와 동일: Bytes 28-31 ===
            status["gamma"] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # === HF와 동일: Bytes 32-35 ===
            status["real_gamma"] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # === HF와 동일: Bytes 36-39 ===
            status["image_gamma"] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # === HF와 동일: Bytes 40-43 ===
            status["rf_phase"] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # === HF와 동일: Bytes 44-47 (Factory Info 1으로 temperature) ===
            status["temperature"] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # === 추가: Bytes 48-51 - Factory Info 2 (uint32) ===
            factory_info_2 = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            
            # === 수정: Bytes 52-55 (Factory Info 3으로 firmware_version) ===
            status["firmware_version"] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            return status
            
        except struct.error as e:
            raise ValueError(f"데이터 파싱 실패: {str(e)}")


class ConfigManager:
    """전체 설정 관리 클래스"""
    
    def __init__(self):
        self.dock_state_file = os.path.join(CONFIG_DIR, "dock_state.bin")
        os.makedirs(CONFIG_DIR, exist_ok=True)
    
    def save_dock_state(self, state_data):
        """도킹 상태 저장"""
        try:
            with open(self.dock_state_file, 'wb') as f:
                f.write(state_data)
            return True, "도킹 상태 저장 완료"
        except Exception as e:
            return False, f"도킹 상태 저장 실패: {str(e)}"
    
    def load_dock_state(self):
        """도킹 상태 로드"""
        if os.path.exists(self.dock_state_file):
            try:
                with open(self.dock_state_file, 'rb') as f:
                    return True, f.read(), "도킹 상태 로드 완료"
            except Exception as e:
                return False, None, f"도킹 상태 로드 실패: {str(e)}"
        else:
            return False, None, "저장된 도킹 상태가 없습니다."