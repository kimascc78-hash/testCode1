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
import sys

# 상수 설정
DATA_DIR = "data"

class DataManager:
    """데이터 및 설정 관리 클래스"""
    
    def __init__(self):
        self.data_log = []
        self.ensure_config_dir()
    
    def ensure_config_dir(self):
        #####
        # 실행 파일의 경로를 찾기 (PyInstaller 대응)
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 실행 파일인 경우
            base_path = sys._MEIPASS
        else:
            # 일반 Python 스크립트로 실행되는 경우
            base_path = os.path.dirname(os.path.abspath(__file__))
        #####
        """설정 디렉토리 생성"""
        CONFIG_DIR = os.path.join(base_path, 'resources', 'config')  # 올바른 문자열 경로
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
                DATA_DIR, #data 디렉토리
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
                DATA_DIR, 
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
            
            # 이 32바이트, 매뉴얼은 33바이트이므로 1바이트 패딩
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


class TuningSettingsManager:
    """튜닝 설정 관리 클래스 - 개별 명령어 지원 + 0값 포함 전송"""
    
    def __init__(self):
        #####
        # 실행 파일의 경로를 찾기 (PyInstaller 대응)
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 실행 파일인 경우
            base_path = sys._MEIPASS
        else:
            # 일반 Python 스크립트로 실행되는 경우
            base_path = os.path.dirname(os.path.abspath(__file__))
        #####
        """설정 디렉토리 생성"""
        CONFIG_DIR = os.path.join(base_path, 'resources', 'config')  # 올바른 문자열 경로
        
        self.settings_file = os.path.join(CONFIG_DIR, "tuning_settings.json")
        self.default_settings = {
            # === 제어 ===
            "Control Mode": "User Port",
            "Regulation Mode": "Forward Power",
            
            # === 램프 ===
            "Ramp Mode": "Disable",
            "Ramp Up Time": "0",
            "Ramp Down Time": "0",
            
            # === CEX ===
            "CEX Enable": "Disable",
            "CEX Mode": "Master",
            "CEX Output Phase": "0",
            "RF Output Phase": "0",
            
            # ========================================
            # === Pulse Configuration (펌웨어 구조체 기준) ===
            # ========================================
            "Pulsing Type": "Amplitude",      # 0x01: 0=amplitude, 1=phase
            "Pulsing Mode": "Master",         # 0x02: 0=master, 1=slave
            "Pulse On/Off": "Off",            # 0x03: 0=off, 1=on
            "Sync Output": "Off",             # 0x04: 0=off, 1=on
            "Pulse0 Level": "100.0",          # 0x05: float[4] %
            "Pulse1 Level": "75.0",
            "Pulse2 Level": "50.0",
            "Pulse3 Level": "0.0",
            "Pulse0 Duty": "20.0",            # 0x06: float[4] %
            "Pulse1 Duty": "20.0",
            "Pulse2 Duty": "20.0",
            "Pulse3 Duty": "20.0",
            "Output Sync Delay": "0",         # 0x07: int32 µs
            "Input Sync Delay": "0",          # 0x08: int32 µs
            "Width Control": "0",             # 0x09: int32 0.5µs
            "Pulse Frequency": "10000",       # 0x0A: int32 0.5µs
            
            # === 주파수 튜닝 ===
            "Freq Tuning": "Disable",
            "Retuning Mode": "Disable",
            "Setting Mode": "Disable",
            "Min Frequency": "0",
            "Max Frequency": "0",
            "Start Frequency": "0",
            "Min Step": "0",
            "Max Step": "0",
            "Stop Gamma": "0",
            "Return Gamma": "0",
            "Set RF Frequency": "0",
            
            # === Bank Function ===
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
            
            # === 네트워크 ===
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

    def save_user_defaults(self, settings):
        """사용자 기본값 저장 - 현재 설정을 기본값으로 저장"""
        #####
        # 실행 파일의 경로를 찾기 (PyInstaller 대응)
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        #####
        CONFIG_DIR = os.path.join(base_path, 'resources', 'config')
        user_defaults_file = os.path.join(CONFIG_DIR, "user_default_tuning.json")

        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(user_defaults_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return True, "현재 설정이 기본값으로 저장되었습니다."
        except Exception as e:
            return False, f"사용자 기본값 저장 실패: {str(e)}"

    def load_user_defaults(self):
        """사용자 기본값 로드"""
        #####
        # 실행 파일의 경로를 찾기 (PyInstaller 대응)
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        #####
        CONFIG_DIR = os.path.join(base_path, 'resources', 'config')
        user_defaults_file = os.path.join(CONFIG_DIR, "user_default_tuning.json")

        if os.path.exists(user_defaults_file):
            try:
                with open(user_defaults_file, 'r', encoding='utf-8') as f:
                    user_defaults = json.load(f)
                return True, user_defaults, "사용자 기본값을 로드했습니다."
            except Exception as e:
                return False, None, f"사용자 기본값 로드 실패: {str(e)}"
        else:
            return False, None, "사용자 기본값이 없습니다. 시스템 기본값을 사용합니다."

    def delete_user_defaults(self):
        """사용자 기본값 삭제"""
        #####
        # 실행 파일의 경로를 찾기 (PyInstaller 대응)
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        #####
        CONFIG_DIR = os.path.join(base_path, 'resources', 'config')
        user_defaults_file = os.path.join(CONFIG_DIR, "user_default_tuning.json")

        try:
            if os.path.exists(user_defaults_file):
                os.remove(user_defaults_file)
                return True, "사용자 기본값이 삭제되었습니다."
            else:
                return True, "삭제할 사용자 기본값이 없습니다."
        except Exception as e:
            return False, f"사용자 기본값 삭제 실패: {str(e)}"

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
            
            # 매뉴얼에 따른 12바이트 구조
            data = struct.pack('<HHff', 
                              cex_enable,       # 2바이트: CEX Enable
                              cex_mode,         # 2바이트: CEX Mode
                              cex_output_phase, # 4바이트: CEX Output Phase
                              rf_output_phase)  # 4바이트: RF Output Phase
            
            return True, data, "CEX 설정 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"CEX 설정 데이터 생성 실패: {str(e)}"
    
    # ========================================
    # === 펌웨어 구조체 기준 Pulse 함수들 (10개) ===
    # ========================================
    
    def create_pulsing_type_data(self, settings):
        """
        Pulsing Type 데이터 생성 (SUBCMD 0x01, 1바이트)
        0: amplitude, 1: phase
        """
        try:
            pulsing_type = 0 if settings.get("Pulsing Type", "Amplitude") == "Amplitude" else 1
            data = struct.pack('<B', pulsing_type)
            return True, data, "Pulsing Type 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Pulsing Type 데이터 생성 실패: {str(e)}"

    def create_pulsing_mode_data(self, settings):
        """
        Pulsing Mode 데이터 생성 (SUBCMD 0x02, 1바이트)
        0: master, 1: slave
        """
        try:
            pulsing_mode = 0 if settings.get("Pulsing Mode", "Master") == "Master" else 1
            data = struct.pack('<B', pulsing_mode)
            return True, data, "Pulsing Mode 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Pulsing Mode 데이터 생성 실패: {str(e)}"

    def create_sync_output_data(self, settings):
        """
        Sync Output 데이터 생성 (SUBCMD 0x04, 1바이트)
        0: off, 1: on
        """
        try:
            sync_output = 1 if settings.get("Sync Output", "Off") == "On" else 0
            data = struct.pack('<B', sync_output)
            return True, data, "Sync Output 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Sync Output 데이터 생성 실패: {str(e)}"

    def create_width_control_data(self, settings):
        """
        Width Control 데이터 생성 (SUBCMD 0x09, 4바이트)
        int32, unit: 0.5µs
        """
        try:
            width_control = int(float(settings.get("Width Control", "0")))
            data = struct.pack('<i', width_control)  # int32
            return True, data, "Width Control 데이터 생성 완료"
        except Exception as e:
            return False, None, f"Width Control 데이터 생성 실패: {str(e)}"
    
    def create_pulse_level_data(self, settings):
        """
        Pulse Level 데이터 생성 (SUBCMD 0x05, 16바이트)
        4개의 float 값 (Pulse0~3 Level, %)
        """
        try:
            data = struct.pack('<ffff',
                float(settings.get("Pulse0 Level", "100.0")),
                float(settings.get("Pulse1 Level", "75.0")),
                float(settings.get("Pulse2 Level", "50.0")),
                float(settings.get("Pulse3 Level", "0.0"))
            )
            
            if len(data) != 16:
                return False, None, f"Pulse Level 데이터 길이 오류: {len(data)}바이트"
            
            return True, data, "Pulse Level 데이터 생성 완료 (16바이트)"
            
        except Exception as e:
            return False, None, f"Pulse Level 데이터 생성 실패: {str(e)}"
    
    def create_pulse_duty_data(self, settings):
        """
        Pulse Duty 데이터 생성 (SUBCMD 0x06, 16바이트)
        4개의 float 값 (Pulse0~3 Duty, %)
        """
        try:
            data = struct.pack('<ffff',
                float(settings.get("Pulse0 Duty", "20.0")),
                float(settings.get("Pulse1 Duty", "20.0")),
                float(settings.get("Pulse2 Duty", "20.0")),
                float(settings.get("Pulse3 Duty", "20.0"))
            )
            
            if len(data) != 16:
                return False, None, f"Pulse Duty 데이터 길이 오류: {len(data)}바이트"
            
            return True, data, "Pulse Duty 데이터 생성 완료 (16바이트)"
            
        except Exception as e:
            return False, None, f"Pulse Duty 데이터 생성 실패: {str(e)}"
    
    def create_pulse_sync_out_delay_data(self, settings):
        """
        Pulse Output Sync Delay 데이터 생성 (SUBCMD 0x07, 4바이트)
        """
        try:
            delay = int(float(settings.get("Output Sync Delay", "0")))
            data = struct.pack('<i', delay)  # int32
            
            return True, data, "Output Sync Delay 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"Output Sync Delay 데이터 생성 실패: {str(e)}"
    
    def create_pulse_sync_in_delay_data(self, settings):
        """
        Pulse Input Sync Delay 데이터 생성 (SUBCMD 0x08, 4바이트)
        """
        try:
            delay = int(float(settings.get("Input Sync Delay", "0")))
            data = struct.pack('<i', delay)  # int32
            
            return True, data, "Input Sync Delay 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"Input Sync Delay 데이터 생성 실패: {str(e)}"
    
    def create_pulse_frequency_data(self, settings):
        """
        Pulse Frequency 데이터 생성 (SUBCMD 0x0A, 4바이트)
        """
        try:
            freq = int(float(settings.get("Pulse Frequency", "10000")))
            data = struct.pack('<i', freq)  # int32
            
            return True, data, "Pulse Frequency 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"Pulse Frequency 데이터 생성 실패: {str(e)}"
    
    # ========================================
    
    def create_rf_frequency_data(self, settings):
        """RF 주파수 설정 데이터 생성"""
        try:
            rf_freq = int(float(settings["Set RF Frequency"]) * 1000000)  # MHz to Hz
            data = struct.pack('<I', rf_freq)  # 4바이트
            
            return True, data, "RF 주파수 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"RF 주파수 데이터 생성 실패: {str(e)}"
    
    def create_freq_tuning_retuning_data(self, settings):
        """재튜닝 모드 설정"""
        try:
            retuning_mode_map = {
                "Disable": 0,   # a time tuning
                "Enable": 1,    # retuning
            }
            
            mode = retuning_mode_map.get(settings["Retuning Mode"], 0)
            data = struct.pack('<B', mode)  # 1바이트
            
            return True, data, "재튜닝 모드 설정"
            
        except Exception as e:
            return False, None, f"재튜닝 모드 데이터 생성 실패: {str(e)}"

    def create_freq_tuning_setting_mode_data(self, settings):
        """주파수 설정 모드"""
        try:
            setting_mode_map = {
                "Disable": 0,   # fixed frequency
                "preset": 1,    # preset mode
                "auto": 2       # auto mode
            }
            
            mode = setting_mode_map.get(settings["Setting Mode"], 0)
            data = struct.pack('<B', mode)  # 1바이트
            
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
    
    # ========================================
    # === 헬퍼 메서드 (리팩토링) ===
    # ========================================

    def _add_command(self, commands, cmd, subcmd, data, description):
        """명령어를 commands 리스트에 추가하는 헬퍼 메서드"""
        commands.append({
            'cmd': cmd,
            'subcmd': subcmd,
            'data': data,
            'description': description
        })

    def _try_add_command(self, commands, create_func, cmd, subcmd, description, settings=None):
        """데이터 생성 함수 호출 후 성공 시 명령어 추가"""
        if settings is not None:
            success, data, msg = create_func(settings)
        else:
            success, data, msg = create_func()

        if success:
            self._add_command(commands, cmd, subcmd, data, description)
        return success

    # ========================================
    # === 전체 튜닝 명령어 생성 ===
    # ========================================

    def get_tuning_commands(self, settings):
        """튜닝 설정을 개별 명령어로 분리하여 반환 - 주파수 튜닝 명령어 추가"""
        commands = []
        
        try:
            # 1. 제어 모드 설정 (항상 전송)
            self._try_add_command(commands, self.create_control_mode_data,
                                RFProtocol.CMD_CONTROL_MODE_SET,
                                RFProtocol.SUBCMD_CONTROL_MODE_SET,
                                '제어 모드 설정', settings)

            # 2. 조절 모드 설정 (항상 전송)
            self._try_add_command(commands, self.create_regulation_mode_data,
                                RFProtocol.CMD_REGULATION_MODE_SET,
                                RFProtocol.SUBCMD_REGULATION_MODE_SET,
                                '조절 모드 설정', settings)

            # 3. 램프 설정 (항상 전송 - 0값도 포함)
            self._try_add_command(commands, self.create_ramp_config_data,
                                RFProtocol.CMD_RAMP_CONFIG_SET,
                                RFProtocol.SUBCMD_RAMP_CONFIG_SET,
                                '램프 설정', settings)

            # 4. CEX 설정 (항상 전송 - 0값도 포함)
            self._try_add_command(commands, self.create_cex_config_data,
                                RFProtocol.CMD_CEX_CONFIG_SET,
                                RFProtocol.SUBCMD_CEX_CONFIG_SET,
                                'CEX 설정', settings)
            
            # 5. Pulse 설정 
            tab_name = None
            for tn in ["control", "ramp", "cex", "pulse", "frequency", "bank", "network"]:
                if tn in str(settings):
                    tab_name = tn
                    break
            
            if tab_name == "pulse" or "Pulse" in str(settings):
                
                # 1. Pulsing Type (SUBCMD 0x01)
                success, data, msg = self.create_pulsing_type_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_PULSE_SET,
                        'subcmd': RFProtocol.SUBCMD_PULSE_TYPE,
                        'data': data,
                        'description': '펄싱 타입 설정'
                    })
                
                # 2. Pulsing Mode (SUBCMD 0x02)
                success, data, msg = self.create_pulsing_mode_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_PULSE_SET,
                        'subcmd': RFProtocol.SUBCMD_PULSE_MODE,
                        'data': data,
                        'description': '펄싱 모드 설정'
                    })
                
                # 3. Pulse On/Off (SUBCMD 0x03)
                pulse_onoff = 1 if settings.get("Pulse On/Off", "Off") == "On" else 0
                data = struct.pack('<B', pulse_onoff)
                commands.append({
                    'cmd': RFProtocol.CMD_PULSE_SET,
                    'subcmd': RFProtocol.SUBCMD_PULSE_OFFON,  # ✅ 수정
                    'data': data,
                    'description': '펄스 On/Off 설정'
                })
                
                # 4. Sync Output (SUBCMD 0x04)
                success, data, msg = self.create_sync_output_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_PULSE_SET,
                        'subcmd': RFProtocol.SUBCMD_PULSE_SYNC_OUTPUT,
                        'data': data,
                        'description': '동기 출력 설정'
                    })
                
                # 5. Pulse Level (SUBCMD 0x05, 16바이트)
                success, data, msg = self.create_pulse_level_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_PULSE_SET,
                        'subcmd': RFProtocol.SUBCMD_PULSE_LEVEL,
                        'data': data,
                        'description': '펄스 레벨 설정'
                    })
                
                # 6. Pulse Duty (SUBCMD 0x06, 16바이트)
                success, data, msg = self.create_pulse_duty_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_PULSE_SET,
                        'subcmd': RFProtocol.SUBCMD_PULSE_DUTY,
                        'data': data,
                        'description': '펄스 듀티 설정'
                    })
                
                # 7. Output Sync Delay (SUBCMD 0x07)
                success, data, msg = self.create_pulse_sync_out_delay_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_PULSE_SET,
                        'subcmd': RFProtocol.SUBCMD_PULSE_SYNC_OUT_DELAY,
                        'data': data,
                        'description': '출력 동기 지연 설정'
                    })
                
                # 8. Input Sync Delay (SUBCMD 0x08)
                success, data, msg = self.create_pulse_sync_in_delay_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_PULSE_SET,
                        'subcmd': RFProtocol.SUBCMD_PULSE_SYNC_IN_DELAY,
                        'data': data,
                        'description': '입력 동기 지연 설정'
                    })
                
                # 9. Width Control (SUBCMD 0x09)
                success, data, msg = self.create_width_control_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_PULSE_SET,
                        'subcmd': RFProtocol.SUBCMD_PULSE_WIDTH_CONTROL,
                        'data': data,
                        'description': '펄스 폭 제어 설정'
                    })
                
                # 10. Pulse Frequency (SUBCMD 0x0A)
                success, data, msg = self.create_pulse_frequency_data(settings)
                if success:
                    commands.append({
                        'cmd': RFProtocol.CMD_PULSE_SET,
                        'subcmd': RFProtocol.SUBCMD_PULSE_FREQ,
                        'data': data,
                        'description': '펄스 주파수 설정'
                    })
            
            # 6. RF 주파수 설정 (0값도 전송)
            success, data, msg = self.create_rf_frequency_data(settings)
            if success:
                commands.append({
                    'cmd': RFProtocol.CMD_SET_FREQUENCY,
                    'subcmd': RFProtocol.SUBCMD_SET_FREQUENCY,
                    'data': data,
                    'description': 'RF 주파수 설정'
                })
            
            # 7. 주파수 튜닝 설정들
            
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
            
            return True, commands, f"이 {len(commands)}개의 설정 명령어 생성 완료 (주파수 튜닝 포함)"
            
        except Exception as e:
            return False, [], f"명령어 생성 실패: {str(e)}"
    
    def get_tab_commands(self, tab_name, settings):
        """특정 탭의 명령어만 생성 - 주파수 튜닝 명령어 추가"""
        commands = []
        
        try:
            if tab_name == "control":
                # 제어 모드 설정
                self._try_add_command(commands, self.create_control_mode_data,
                                    RFProtocol.CMD_CONTROL_MODE_SET,
                                    RFProtocol.SUBCMD_CONTROL_MODE_SET,
                                    '제어 모드 설정', settings)

                # 조절 모드 설정
                self._try_add_command(commands, self.create_regulation_mode_data,
                                    RFProtocol.CMD_REGULATION_MODE_SET,
                                    RFProtocol.SUBCMD_REGULATION_MODE_SET,
                                    '조절 모드 설정', settings)

            elif tab_name == "ramp":
                # 램프 설정
                self._try_add_command(commands, self.create_ramp_config_data,
                                    RFProtocol.CMD_RAMP_CONFIG_SET,
                                    RFProtocol.SUBCMD_RAMP_CONFIG_SET,
                                    '램프 설정', settings)

            elif tab_name == "cex":
                # CEX 설정
                self._try_add_command(commands, self.create_cex_config_data,
                                    RFProtocol.CMD_CEX_CONFIG_SET,
                                    RFProtocol.SUBCMD_CEX_CONFIG_SET,
                                    'CEX 설정', settings)
                    
            elif tab_name == "pulse":
                # === 펌웨어 구조체 기준 Pulse 명령어 (10개 전체) ===
                # 1. Pulsing Type (SUBCMD 0x01)
                self._try_add_command(commands, self.create_pulsing_type_data,
                                    RFProtocol.CMD_PULSE_SET,
                                    RFProtocol.SUBCMD_PULSE_TYPE,
                                    '펄싱 타입 설정', settings)

                # 2. Pulsing Mode (SUBCMD 0x02)
                self._try_add_command(commands, self.create_pulsing_mode_data,
                                    RFProtocol.CMD_PULSE_SET,
                                    RFProtocol.SUBCMD_PULSE_MODE,
                                    '펄싱 모드 설정', settings)

                # 3. Pulse On/Off (SUBCMD 0x03)
                pulse_onoff = 1 if settings.get("Pulse On/Off", "Off") == "On" else 0
                data = struct.pack('<B', pulse_onoff)
                self._add_command(commands, RFProtocol.CMD_PULSE_SET,
                                RFProtocol.SUBCMD_PULSE_OFFON,
                                data, '펄스 On/Off 설정')

                # 4. Sync Output (SUBCMD 0x04)
                self._try_add_command(commands, self.create_sync_output_data,
                                    RFProtocol.CMD_PULSE_SET,
                                    RFProtocol.SUBCMD_PULSE_SYNC_OUTPUT,
                                    '동기 출력 설정', settings)

                # 5. Pulse Level (SUBCMD 0x05, 16바이트)
                self._try_add_command(commands, self.create_pulse_level_data,
                                    RFProtocol.CMD_PULSE_SET,
                                    RFProtocol.SUBCMD_PULSE_LEVEL,
                                    '펄스 레벨 설정', settings)

                # 6. Pulse Duty (SUBCMD 0x06, 16바이트)
                self._try_add_command(commands, self.create_pulse_duty_data,
                                    RFProtocol.CMD_PULSE_SET,
                                    RFProtocol.SUBCMD_PULSE_DUTY,
                                    '펄스 듀티 설정', settings)

                # 7. Output Sync Delay (SUBCMD 0x07)
                self._try_add_command(commands, self.create_pulse_sync_out_delay_data,
                                    RFProtocol.CMD_PULSE_SET,
                                    RFProtocol.SUBCMD_PULSE_SYNC_OUT_DELAY,
                                    '출력 동기 지연 설정', settings)

                # 8. Input Sync Delay (SUBCMD 0x08)
                self._try_add_command(commands, self.create_pulse_sync_in_delay_data,
                                    RFProtocol.CMD_PULSE_SET,
                                    RFProtocol.SUBCMD_PULSE_SYNC_IN_DELAY,
                                    '입력 동기 지연 설정', settings)

                # 9. Width Control (SUBCMD 0x09)
                self._try_add_command(commands, self.create_width_control_data,
                                    RFProtocol.CMD_PULSE_SET,
                                    RFProtocol.SUBCMD_PULSE_WIDTH_CONTROL,
                                    '펄스 폭 제어 설정', settings)

                # 10. Pulse Frequency (SUBCMD 0x0A)
                self._try_add_command(commands, self.create_pulse_frequency_data,
                                    RFProtocol.CMD_PULSE_SET,
                                    RFProtocol.SUBCMD_PULSE_FREQ,
                                    '펄스 주파수 설정', settings)

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
            
            elif tab_name == "network":
                # 네트워크 설정은 장비로 전송하지 않음 (클라이언트 설정만)
                pass

            return True, commands, f"{tab_name} 탭 {len(commands)}개 명령어 생성 완료"

        except Exception as e:
            return False, [], f"{tab_name} 탭 명령어 생성 실패: {str(e)}"

    # ========================================
    # === 장비에서 설정 읽기 (GET 명령어) ===
    # ========================================

    def get_tab_read_commands(self, tab_name):
        """탭별 GET 명령어 목록 반환"""
        try:
            commands = []

            if tab_name == "control":
                # 제어 모드 조회
                commands.append({
                    'cmd': RFProtocol.CMD_CONTROL_MODE_GET,
                    'subcmd': RFProtocol.SUBCMD_CONTROL_MODE_GET,
                    'data': None,
                    'description': '제어 모드 조회'
                })
                # 조절 모드 조회
                commands.append({
                    'cmd': RFProtocol.CMD_REGULATION_MODE_GET,
                    'subcmd': RFProtocol.SUBCMD_REGULATION_MODE_GET,
                    'data': None,
                    'description': '조절 모드 조회'
                })

            elif tab_name == "ramp":
                # 램프 설정 조회
                commands.append({
                    'cmd': RFProtocol.CMD_RAMP_CONFIG_GET,
                    'subcmd': RFProtocol.SUBCMD_RAMP_CONFIG_GET,
                    'data': None,
                    'description': '램프 설정 조회'
                })

            elif tab_name == "cex":
                # CEX 설정 조회
                commands.append({
                    'cmd': RFProtocol.CMD_CEX_CONFIG_GET,
                    'subcmd': RFProtocol.SUBCMD_CEX_CONFIG_GET,
                    'data': None,
                    'description': 'CEX 설정 조회'
                })

            elif tab_name == "pulse":
                # 펄스 설정 조회 (10개 항목)
                pulse_subcmds = [
                    (RFProtocol.SUBCMD_PULSE_TYPE, "펄스 타입"),
                    (RFProtocol.SUBCMD_PULSE_MODE, "펄스 모드"),
                    (RFProtocol.SUBCMD_PULSE_OFFON, "펄스 On/Off"),
                    (RFProtocol.SUBCMD_PULSE_SYNC_OUTPUT, "싱크 출력"),
                    (RFProtocol.SUBCMD_PULSE_LEVEL, "펄스 레벨"),
                    (RFProtocol.SUBCMD_PULSE_DUTY, "펄스 듀티"),
                    (RFProtocol.SUBCMD_PULSE_SYNC_OUT_DELAY, "출력 싱크 지연"),
                    (RFProtocol.SUBCMD_PULSE_SYNC_IN_DELAY, "입력 싱크 지연"),
                    (RFProtocol.SUBCMD_PULSE_WIDTH_CONTROL, "폭 제어"),
                    (RFProtocol.SUBCMD_PULSE_FREQ, "펄스 주파수")
                ]
                for subcmd, desc in pulse_subcmds:
                    commands.append({
                        'cmd': RFProtocol.CMD_PULSE_GET,
                        'subcmd': subcmd,
                        'data': None,
                        'description': f'{desc} 조회'
                    })

            elif tab_name == "frequency":
                # RF 주파수 조회
                commands.append({
                    'cmd': RFProtocol.CMD_GET_FREQUENCY,
                    'subcmd': RFProtocol.SUBCMD_GET_FREQUENCY,
                    'data': None,
                    'description': 'RF 주파수 조회'
                })
                # 주파수 튜닝 설정 조회
                freq_tuning_subcmds = [
                    (RFProtocol.SUBCMD_FREQ_TUNING_ENABLE, "주파수 튜닝 활성화"),
                    (RFProtocol.SUBCMD_FREQ_TUNING_RETUNING, "재튜닝 모드"),
                    (RFProtocol.SUBCMD_FREQ_TUNING_MODE, "설정 모드"),
                    (RFProtocol.SUBCMD_FREQ_TUNING_MIN_FREQ, "최소 주파수"),
                    (RFProtocol.SUBCMD_FREQ_TUNING_MAX_FREQ, "최대 주파수"),
                    (RFProtocol.SUBCMD_FREQ_TUNING_START_FREQ, "시작 주파수"),
                    (RFProtocol.SUBCMD_FREQ_TUNING_MIN_STEP, "최소 스텝"),
                    (RFProtocol.SUBCMD_FREQ_TUNING_MAX_STEP, "최대 스텝"),
                    (RFProtocol.SUBCMD_FREQ_TUNING_STOP_GAMMA, "정지 감마"),
                    (RFProtocol.SUBCMD_FREQ_TUNING_RETURN_GAMMA, "복귀 감마")
                ]
                for subcmd, desc in freq_tuning_subcmds:
                    commands.append({
                        'cmd': RFProtocol.CMD_FREQUENCY_TUNING_GET,
                        'subcmd': subcmd,
                        'data': None,
                        'description': f'{desc} 조회'
                    })

            elif tab_name == "bank":
                # Bank 설정 조회
                commands.append({
                    'cmd': RFProtocol.CMD_BANK_GET,
                    'subcmd': RFProtocol.SUBCMD_BANK1_ENABLE,
                    'data': None,
                    'description': 'Bank1 활성화 조회'
                })
                commands.append({
                    'cmd': RFProtocol.CMD_BANK_GET,
                    'subcmd': RFProtocol.SUBCMD_BANK1_EQUATION_ENABLE,
                    'data': None,
                    'description': 'Bank1 방정식 활성화 조회'
                })
                commands.append({
                    'cmd': RFProtocol.CMD_BANK_GET,
                    'subcmd': RFProtocol.SUBCMD_BANK1_PARAMS,
                    'data': None,
                    'description': 'Bank1 파라미터 조회'
                })
                commands.append({
                    'cmd': RFProtocol.CMD_BANK_GET,
                    'subcmd': RFProtocol.SUBCMD_BANK2_ENABLE,
                    'data': None,
                    'description': 'Bank2 활성화 조회'
                })
                commands.append({
                    'cmd': RFProtocol.CMD_BANK_GET,
                    'subcmd': RFProtocol.SUBCMD_BANK2_EQUATION_ENABLE,
                    'data': None,
                    'description': 'Bank2 방정식 활성화 조회'
                })
                commands.append({
                    'cmd': RFProtocol.CMD_BANK_GET,
                    'subcmd': RFProtocol.SUBCMD_BANK2_PARAMS,
                    'data': None,
                    'description': 'Bank2 파라미터 조회'
                })

            elif tab_name == "network":
                # 네트워크는 장비에서 읽지 않음 (클라이언트 측 설정)
                pass

            return True, commands, f"{tab_name} 탭 {len(commands)}개 GET 명령어 생성 완료"

        except Exception as e:
            return False, [], f"{tab_name} 탭 GET 명령어 생성 실패: {str(e)}"

    def parse_tab_responses(self, tab_name, responses):
        """탭별 응답 통합 파싱 - 설정 딕셔너리 반환"""
        try:
            settings = {}

            if tab_name == "control":
                for response in responses:
                    if response['subcmd'] == RFProtocol.SUBCMD_CONTROL_MODE_GET:
                        settings['Control Mode'] = self._parse_control_mode(response['data'])
                    elif response['subcmd'] == RFProtocol.SUBCMD_REGULATION_MODE_GET:
                        settings['Regulation Mode'] = self._parse_regulation_mode(response['data'])

            elif tab_name == "ramp":
                for response in responses:
                    if response['subcmd'] == RFProtocol.SUBCMD_RAMP_CONFIG_GET:
                        ramp_settings = self._parse_ramp_config(response['data'])
                        settings.update(ramp_settings)

            elif tab_name == "cex":
                for response in responses:
                    if response['subcmd'] == RFProtocol.SUBCMD_CEX_CONFIG_GET:
                        cex_settings = self._parse_cex_config(response['data'])
                        settings.update(cex_settings)

            elif tab_name == "pulse":
                pulse_data = {}
                for response in responses:
                    subcmd = response['subcmd']
                    data = response['data']
                    if subcmd == RFProtocol.SUBCMD_PULSE_TYPE:
                        pulse_data['type'] = struct.unpack('<B', data)[0] if len(data) >= 1 else 0
                    elif subcmd == RFProtocol.SUBCMD_PULSE_MODE:
                        pulse_data['mode'] = struct.unpack('<B', data)[0] if len(data) >= 1 else 0
                    elif subcmd == RFProtocol.SUBCMD_PULSE_OFFON:
                        pulse_data['offon'] = struct.unpack('<B', data)[0] if len(data) >= 1 else 0
                    elif subcmd == RFProtocol.SUBCMD_PULSE_SYNC_OUTPUT:
                        pulse_data['sync_output'] = struct.unpack('<B', data)[0] if len(data) >= 1 else 0
                    elif subcmd == RFProtocol.SUBCMD_PULSE_LEVEL:
                        pulse_data['levels'] = struct.unpack('<ffff', data) if len(data) >= 16 else (0, 0, 0, 0)
                    elif subcmd == RFProtocol.SUBCMD_PULSE_DUTY:
                        pulse_data['duties'] = struct.unpack('<ffff', data) if len(data) >= 16 else (0, 0, 0, 0)
                    elif subcmd == RFProtocol.SUBCMD_PULSE_SYNC_OUT_DELAY:
                        pulse_data['sync_out_delay'] = struct.unpack('<I', data)[0] if len(data) >= 4 else 0
                    elif subcmd == RFProtocol.SUBCMD_PULSE_SYNC_IN_DELAY:
                        pulse_data['sync_in_delay'] = struct.unpack('<I', data)[0] if len(data) >= 4 else 0
                    elif subcmd == RFProtocol.SUBCMD_PULSE_WIDTH_CONTROL:
                        pulse_data['width_control'] = struct.unpack('<I', data)[0] if len(data) >= 4 else 0
                    elif subcmd == RFProtocol.SUBCMD_PULSE_FREQ:
                        pulse_data['frequency'] = struct.unpack('<I', data)[0] if len(data) >= 4 else 0

                settings.update(self._convert_pulse_data_to_settings(pulse_data))

            elif tab_name == "frequency":
                freq_data = {}
                for response in responses:
                    subcmd = response['subcmd']
                    data = response['data']
                    if subcmd == RFProtocol.SUBCMD_GET_FREQUENCY:
                        freq_data['rf_frequency'] = struct.unpack('<f', data)[0] if len(data) >= 4 else 0.0
                    elif subcmd == RFProtocol.SUBCMD_FREQ_TUNING_ENABLE:
                        freq_data['tuning_enable'] = struct.unpack('<B', data)[0] if len(data) >= 1 else 0
                    elif subcmd == RFProtocol.SUBCMD_FREQ_TUNING_RETUNING:
                        freq_data['retuning'] = struct.unpack('<B', data)[0] if len(data) >= 1 else 0
                    elif subcmd == RFProtocol.SUBCMD_FREQ_TUNING_MODE:
                        freq_data['mode'] = struct.unpack('<B', data)[0] if len(data) >= 1 else 0
                    elif subcmd == RFProtocol.SUBCMD_FREQ_TUNING_MIN_FREQ:
                        freq_data['min_freq'] = struct.unpack('<f', data)[0] if len(data) >= 4 else 0.0
                    elif subcmd == RFProtocol.SUBCMD_FREQ_TUNING_MAX_FREQ:
                        freq_data['max_freq'] = struct.unpack('<f', data)[0] if len(data) >= 4 else 0.0
                    elif subcmd == RFProtocol.SUBCMD_FREQ_TUNING_START_FREQ:
                        freq_data['start_freq'] = struct.unpack('<f', data)[0] if len(data) >= 4 else 0.0
                    elif subcmd == RFProtocol.SUBCMD_FREQ_TUNING_MIN_STEP:
                        freq_data['min_step'] = struct.unpack('<f', data)[0] if len(data) >= 4 else 0.0
                    elif subcmd == RFProtocol.SUBCMD_FREQ_TUNING_MAX_STEP:
                        freq_data['max_step'] = struct.unpack('<f', data)[0] if len(data) >= 4 else 0.0
                    elif subcmd == RFProtocol.SUBCMD_FREQ_TUNING_STOP_GAMMA:
                        freq_data['stop_gamma'] = struct.unpack('<f', data)[0] if len(data) >= 4 else 0.0
                    elif subcmd == RFProtocol.SUBCMD_FREQ_TUNING_RETURN_GAMMA:
                        freq_data['return_gamma'] = struct.unpack('<f', data)[0] if len(data) >= 4 else 0.0

                settings.update(self._convert_frequency_data_to_settings(freq_data))

            elif tab_name == "bank":
                bank_data = {}
                for response in responses:
                    subcmd = response['subcmd']
                    data = response['data']
                    if subcmd == RFProtocol.SUBCMD_BANK1_ENABLE:
                        bank_data['bank1_enable'] = struct.unpack('<H', data)[0] if len(data) >= 2 else 0
                    elif subcmd == RFProtocol.SUBCMD_BANK1_EQUATION_ENABLE:
                        bank_data['bank1_eq_enable'] = struct.unpack('<H', data)[0] if len(data) >= 2 else 0
                    elif subcmd == RFProtocol.SUBCMD_BANK1_PARAMS:
                        if len(data) >= 20:
                            bank_data['bank1_params'] = struct.unpack('<fffff', data)
                    elif subcmd == RFProtocol.SUBCMD_BANK2_ENABLE:
                        bank_data['bank2_enable'] = struct.unpack('<H', data)[0] if len(data) >= 2 else 0
                    elif subcmd == RFProtocol.SUBCMD_BANK2_EQUATION_ENABLE:
                        bank_data['bank2_eq_enable'] = struct.unpack('<H', data)[0] if len(data) >= 2 else 0
                    elif subcmd == RFProtocol.SUBCMD_BANK2_PARAMS:
                        if len(data) >= 20:
                            bank_data['bank2_params'] = struct.unpack('<fffff', data)

                settings.update(self._convert_bank_data_to_settings(bank_data))

            return True, settings, f"{tab_name} 탭 응답 파싱 완료"

        except Exception as e:
            return False, {}, f"{tab_name} 탭 응답 파싱 실패: {str(e)}"

    # ========================================
    # === 개별 응답 파싱 헬퍼 함수들 ===
    # ========================================

    def _parse_control_mode(self, data):
        """제어 모드 파싱"""
        try:
            if not data or len(data) < 2:
                return "Ethernet"
            mode_value = struct.unpack('<H', data)[0]
            mode_map = {0: "User Port", 1: "Serial", 2: "Ethernet",
                       3: "EtherCAT", 4: "Serial+User", 5: "Ethernet+User"}
            return mode_map.get(mode_value, "Ethernet")
        except:
            return "Ethernet"

    def _parse_regulation_mode(self, data):
        """조절 모드 파싱"""
        try:
            if not data or len(data) < 2:
                return "Forward Power"
            mode_value = struct.unpack('<H', data)[0]
            mode_map = {0: "Forward Power", 1: "Load Power", 2: "Voltage", 3: "Current"}
            return mode_map.get(mode_value, "Forward Power")
        except:
            return "Forward Power"

    def _parse_ramp_config(self, data):
        """램프 설정 파싱"""
        try:
            if not data or len(data) < 20:
                return {"Ramp Mode": "Disable", "Ramp Up Time": "0", "Ramp Down Time": "0"}

            ramp_mode, ramp_up, ramp_down, _, _ = struct.unpack('<IIIII', data)
            return {
                "Ramp Mode": "Enable" if ramp_mode == 1 else "Disable",
                "Ramp Up Time": str(ramp_up),
                "Ramp Down Time": str(ramp_down)
            }
        except:
            return {"Ramp Mode": "Disable", "Ramp Up Time": "0", "Ramp Down Time": "0"}

    def _parse_cex_config(self, data):
        """CEX 설정 파싱"""
        try:
            if not data or len(data) < 12:
                return {"CEX Enable": "Disable", "CEX Mode": "Master",
                       "CEX Output Phase": "0.0", "RF Output Phase": "0.0"}

            cex_enable, cex_mode, cex_out_phase, rf_out_phase = struct.unpack('<HHff', data)
            return {
                "CEX Enable": "Enable" if cex_enable == 1 else "Disable",
                "CEX Mode": "Master" if cex_mode == 0 else "Slave",
                "CEX Output Phase": f"{cex_out_phase:.1f}",
                "RF Output Phase": f"{rf_out_phase:.1f}"
            }
        except:
            return {"CEX Enable": "Disable", "CEX Mode": "Master",
                   "CEX Output Phase": "0.0", "RF Output Phase": "0.0"}

    def _convert_pulse_data_to_settings(self, pulse_data):
        """펄스 원시 데이터를 설정 딕셔너리로 변환"""
        try:
            type_map = {0: "Internal", 1: "External"}
            mode_map = {0: "Fixed", 1: "Step"}

            settings = {
                "Pulsing Type": type_map.get(pulse_data.get('type', 0), "Internal"),
                "Pulsing Mode": mode_map.get(pulse_data.get('mode', 0), "Fixed"),
                "Pulse On/Off": "On" if pulse_data.get('offon', 0) == 1 else "Off",
                "Sync Output": "Enable" if pulse_data.get('sync_output', 0) == 1 else "Disable"
            }

            levels = pulse_data.get('levels', (0, 0, 0, 0))
            for i, level in enumerate(levels):
                settings[f"Pulse{i} Level"] = f"{level:.1f}"

            duties = pulse_data.get('duties', (0, 0, 0, 0))
            for i, duty in enumerate(duties):
                settings[f"Pulse{i} Duty"] = f"{duty:.1f}"

            settings["Output Sync Delay"] = str(pulse_data.get('sync_out_delay', 0))
            settings["Input Sync Delay"] = str(pulse_data.get('sync_in_delay', 0))
            settings["Width Control"] = str(pulse_data.get('width_control', 0))
            settings["Pulse Frequency"] = str(pulse_data.get('frequency', 0))

            return settings
        except:
            return {}

    def _convert_frequency_data_to_settings(self, freq_data):
        """주파수 원시 데이터를 설정 딕셔너리로 변환"""
        try:
            retuning_map = {0: "Disable", 1: "Enable"}
            mode_map = {0: "Auto", 1: "Manual"}

            return {
                "Set RF Frequency": f"{freq_data.get('rf_frequency', 0.0):.2f}",
                "Freq Tuning": "Enable" if freq_data.get('tuning_enable', 0) == 1 else "Disable",
                "Retuning Mode": retuning_map.get(freq_data.get('retuning', 0), "Disable"),
                "Setting Mode": mode_map.get(freq_data.get('mode', 0), "Auto"),
                "Min Frequency": f"{freq_data.get('min_freq', 0.0):.2f}",
                "Max Frequency": f"{freq_data.get('max_freq', 0.0):.2f}",
                "Start Frequency": f"{freq_data.get('start_freq', 0.0):.2f}",
                "Min Step": f"{freq_data.get('min_step', 0.0):.3f}",
                "Max Step": f"{freq_data.get('max_step', 0.0):.3f}",
                "Stop Gamma": f"{freq_data.get('stop_gamma', 0.0):.3f}",
                "Return Gamma": f"{freq_data.get('return_gamma', 0.0):.3f}"
            }
        except:
            return {}

    def _convert_bank_data_to_settings(self, bank_data):
        """Bank 원시 데이터를 설정 딕셔너리로 변환"""
        try:
            settings = {
                "Bank1 Enable": "Enable" if bank_data.get('bank1_enable', 0) == 1 else "Disable",
                "Bank1 Equation Enable": "Enable" if bank_data.get('bank1_eq_enable', 0) == 1 else "Disable",
                "Bank2 Enable": "Enable" if bank_data.get('bank2_enable', 0) == 1 else "Disable",
                "Bank2 Equation Enable": "Enable" if bank_data.get('bank2_eq_enable', 0) == 1 else "Disable"
            }

            if 'bank1_params' in bank_data:
                x0, a, b, c, d = bank_data['bank1_params']
                settings.update({
                    "Bank1 X0": f"{x0:.2f}",
                    "Bank1 A": f"{a:.6f}",
                    "Bank1 B": f"{b:.6f}",
                    "Bank1 C": f"{c:.6f}",
                    "Bank1 D": f"{d:.6f}"
                })

            if 'bank2_params' in bank_data:
                x0, a, b, c, d = bank_data['bank2_params']
                settings.update({
                    "Bank2 X0": f"{x0:.2f}",
                    "Bank2 A": f"{a:.6f}",
                    "Bank2 B": f"{b:.6f}",
                    "Bank2 C": f"{c:.6f}",
                    "Bank2 D": f"{d:.6f}"
                })

            return settings
        except:
            return {}


class StatusParser:
    """상태 데이터 파싱 클래스"""
    
    @staticmethod
    def parse_device_status(data):
        """장비 상태 데이터 파싱 - VHF 매뉴얼 56바이트 버전"""
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
            status["set_power"] = struct.unpack('<f', data[offset:offset+4])[0]
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
        #####
        # 실행 파일의 경로를 찾기 (PyInstaller 대응)
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 실행 파일인 경우
            base_path = sys._MEIPASS
        else:
            # 일반 Python 스크립트로 실행되는 경우
            base_path = os.path.dirname(os.path.abspath(__file__))
        #####
        """설정 디렉토리 생성"""
        CONFIG_DIR = os.path.join(base_path, 'resources', 'config')  # 올바른 문자열 경로
        
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