"""
Hybrid RF Protocol and Communication Module
동기/비동기 모드를 모두 지원하는 하이브리드 통신 시스템
"""

import socket
import struct
import time
import threading
import queue
from dataclasses import dataclass
from typing import Optional, Tuple, Union
from PyQt5.QtCore import QThread, pyqtSignal
from settings_dialog import SettingsDialog, SettingsManager # 새로 추가

# 상수 설정
RECONNECT_MAX_ATTEMPTS = 10
#RECONNECT_BASE_DELAY = 1.0
#RECONNECT_BASE_DELAY = 0.2 # 속도 최적화 테스트 
RECONNECT_BASE_DELAY = 0.1 # 속도 최적화 테스트 
SOCKET_TIMEOUT = 5.0


@dataclass
class CommandResult:
    """명령어 실행 결과"""
    success: bool
    message: str
    response_data: Optional[bytes] = None
    error_code: Optional[int] = None
    execution_time: float = 0.0


class RFProtocol:
    """RF 장비 통신 프로토콜 정의 - VHF 매뉴얼 전체 반영"""
    _SOM_ = 0x16
    _EOM_ = 0x1A
    _DID_ = 0x00

    # ========================================
    # === 기본 명령어 (VHF 매뉴얼 Page 6) ===
    # ========================================
    
    # RF On/Off
    CMD_RF_ON = 0x00
    SUBCMD_RF_ON = 0x01
    CMD_RF_OFF = 0x00
    SUBCMD_RF_OFF = 0x02
    
    # ========================================
    # === 장비 상태 조회 ===
    # ========================================
    CMD_DEVICE_STATUS_GET = 0x10
    SUBCMD_DEVICE_STATUS = 0x01
    
    # ========================================
    # === 파워 설정 (CMD=0x07/0x87) ===
    # ========================================
    CMD_SET_POWER = 0x07
    SUBCMD_SET_POWER = 0x03
    CMD_GET_POWER = 0x87
    SUBCMD_GET_POWER = 0x03
    
    # ========================================
    # === 제어 모드 (CMD=0x07/0x87) ===
    # ========================================
    CMD_CONTROL_MODE_SET = 0x07
    SUBCMD_CONTROL_MODE_SET = 0x01
    CMD_CONTROL_MODE_GET = 0x87
    SUBCMD_CONTROL_MODE_GET = 0x01
    
    # ========================================
    # === 파워 조절 모드 (CMD=0x01/0x81) ===
    # ========================================
    CMD_REGULATION_MODE_SET = 0x01
    SUBCMD_REGULATION_MODE_SET = 0x02
    CMD_REGULATION_MODE_GET = 0x81
    SUBCMD_REGULATION_MODE_GET = 0x02
    
    # ========================================
    # === 램프 설정 (CMD=0x01/0x81) ===
    # ========================================
    CMD_RAMP_CONFIG_SET = 0x01
    SUBCMD_RAMP_CONFIG_SET = 0x0B
    CMD_RAMP_CONFIG_GET = 0x81
    SUBCMD_RAMP_CONFIG_GET = 0x0B
    
    # ========================================
    # === VHF 매뉴얼 기준 Pulse Configuration ===
    # === (CMD=0x02/0x82, Page 17-20) ===
    # ========================================
    CMD_PULSE_SET = 0x02
    CMD_PULSE_GET = 0x82
    
    # 개별 파라미터 SUBCMD (펌웨어 코드 기준)
    SUBCMD_PULSE_TYPE = 0x01           # pulsing_type (1바이트)
    SUBCMD_PULSE_MODE = 0x02           # pulsing_mode (1바이트)
    SUBCMD_PULSE_OFFON = 0x03          # pulsing_offon (1바이트) - On/Off 제어
    SUBCMD_PULSE_SYNC_OUTPUT = 0x04    # sync_output (1바이트)
    SUBCMD_PULSE_LEVEL = 0x05          # pulse_level[4] (16바이트 - float×4)
    SUBCMD_PULSE_DUTY = 0x06           # pulse_duty[4] (16바이트 - float×4)
    SUBCMD_PULSE_SYNC_OUT_DELAY = 0x07 # sync_out_delay (4바이트)
    SUBCMD_PULSE_SYNC_IN_DELAY = 0x08  # sync_in_delay (4바이트)
    SUBCMD_PULSE_WIDTH_CONTROL = 0x09  # width_control (4바이트)
    SUBCMD_PULSE_FREQ = 0x0A           # pulse_freq (4바이트)
    
    # VHF 매뉴얼 기준 간소화된 Pulse 명령어 (data_manager.py와 호환)
    # SUBCMD_PULSE_MODE_SET = 0x03      # Pulse on/off 설정 (VHF 매뉴얼 Page 17)
    # SUBCMD_PULSE_PARAMS_SET = 0x05    # Pulse 파라미터 설정 33바이트 (Page 19-20)
    # SUBCMD_PULSE_MODE_GET = 0x03
    # SUBCMD_PULSE_PARAMS_GET = 0x05
    
    # ========================================
    # === RF 주파수 설정 (CMD=0x04/0x84) ===
    # ========================================
    CMD_SET_FREQUENCY = 0x04
    SUBCMD_SET_FREQUENCY = 0x09
    CMD_GET_FREQUENCY = 0x84
    SUBCMD_GET_FREQUENCY = 0x09
    
    # ========================================
    # === 주파수 튜닝 (CMD=0x04/0x84, Page 21-32) ===
    # ========================================
    CMD_FREQUENCY_TUNING = 0x04
    CMD_FREQUENCY_TUNING_GET = 0x84
    
    SUBCMD_FREQ_TUNING_ENABLE = 0x01
    SUBCMD_FREQ_TUNING_RETUNING = 0x02
    SUBCMD_FREQ_TUNING_MODE = 0x03
    SUBCMD_FREQ_TUNING_MIN_FREQ = 0x06
    SUBCMD_FREQ_TUNING_MAX_FREQ = 0x07
    SUBCMD_FREQ_TUNING_START_FREQ = 0x08
    SUBCMD_FREQ_TUNING_MIN_STEP = 0x0A
    SUBCMD_FREQ_TUNING_MAX_STEP = 0x0B
    SUBCMD_FREQ_TUNING_STOP_GAMMA = 0x0E
    SUBCMD_FREQ_TUNING_RETURN_GAMMA = 0x0F
    
    # ========================================
    # === CEX 설정 (CMD=0x01/0x81) ===
    # ========================================
    CMD_CEX_CONFIG_SET = 0x01
    SUBCMD_CEX_CONFIG_SET = 0x0C
    CMD_CEX_CONFIG_GET = 0x81
    SUBCMD_CEX_CONFIG_GET = 0x0C
    
    # ========================================
    # === 알람 클리어 (CMD=0x04) ===
    # ========================================
    CMD_ALARM_CLEAR = 0x04
    SUBCMD_ALARM_CLEAR = 0x15
    
    # ========================================
    # === Bank Function (RF On trigger & Timed RF off) ===
    # === (CMD=0x19/0x99, Page 34-44) ===
    # ========================================
    
    # Bank SET 명령어
    CMD_BANK_SET = 0x19
    SUBCMD_BANK1_ENABLE = 0x01
    SUBCMD_BANK1_EQUATION_ENABLE = 0x02
    SUBCMD_BANK1_RESTART = 0x03
    SUBCMD_BANK1_RF_TRIGGER = 0x04
    SUBCMD_BANK1_PARAMS = 0x05
    SUBCMD_BANK2_ENABLE = 0x06
    SUBCMD_BANK2_EQUATION_ENABLE = 0x07
    SUBCMD_BANK2_RESTART = 0x08
    SUBCMD_BANK2_RF_TRIGGER = 0x09
    SUBCMD_BANK2_PARAMS = 0x0A
    
    # Bank GET 명령어
    CMD_BANK_GET = 0x99
    
    # ========================================
    # === 네트워크 설정 (Page 44-45) ===
    # ========================================
    
    # MAC Address 조회
    CMD_NETWORK_MAC_GET = 0x92
    SUBCMD_NETWORK_MAC_GET = 0x00
    
    # TCP/IP 설정
    CMD_NETWORK_TCPIP_SET = 0x11
    SUBCMD_NETWORK_TCPIP_SET = 0x00
    
    # TCP/IP 조회
    CMD_NETWORK_TCPIP_GET = 0x91
    SUBCMD_NETWORK_TCPIP_GET = 0x00

    # ========================================
    # === Developer Commands (개발자 전용) ===
    # ========================================

    # Arc Management (CMD=0x03/0x83)
    CMD_ARC_MANAGEMENT_SET = 0x03
    CMD_ARC_MANAGEMENT_GET = 0x83
    SUBCMD_ARC_MANAGEMENT = 0x00

    # SDD Config (CMD=0x05/0x85)
    CMD_SDD_CONFIG_SET = 0x05
    CMD_SDD_CONFIG_GET = 0x85
    SUBCMD_SDD_CONFIG = 0x00

    # Fast Data Acquisition (CMD=0x06/0x86)
    CMD_FAST_ACQ_SET = 0x06
    CMD_FAST_ACQ_GET = 0x86
    SUBCMD_FAST_ACQ = 0x00

    # DDS Control (CMD=0x08/0x88)
    CMD_DDS_CTL_SET = 0x08
    CMD_DDS_CTL_GET = 0x88
    SUBCMD_DDS_CTL = 0x00

    # Calibration Control (CMD=0x09/0x89)
    CMD_CAL_CTL_SET = 0x09
    CMD_CAL_CTL_GET = 0x89
    SUBCMD_CAL_CTL = 0x00

    # Calibration Tables
    CMD_CAL_RFSET_TABLE_SET = 0x0A
    CMD_CAL_RFSET_TABLE_GET = 0x8A
    SUBCMD_CAL_RFSET_TARGET = 0x01
    SUBCMD_CAL_RFSET_DACC = 0x02
    SUBCMD_CAL_RFSET_DACL = 0x03
    SUBCMD_CAL_RFSET_DACH = 0x04

    CMD_CAL_FWDLOAD_TABLE_SET = 0x0B
    CMD_CAL_FWDLOAD_TABLE_GET = 0x8B
    SUBCMD_CAL_FWDLOAD_TARGET = 0x01
    SUBCMD_CAL_FWDLOAD_DAC = 0x02

    CMD_CAL_REF_TABLE_SET = 0x0C
    CMD_CAL_REF_TABLE_GET = 0x8C
    SUBCMD_CAL_REF_TARGET = 0x01
    SUBCMD_CAL_REF_DAC = 0x02

    CMD_CAL_RFSETIN_TABLE_SET = 0x0D
    CMD_CAL_RFSETIN_TABLE_GET = 0x8D
    SUBCMD_CAL_RFSETIN_TARGET = 0x01
    SUBCMD_CAL_RFSETIN_ADC = 0x03

    CMD_CAL_DCBIAS_TABLE_SET = 0x13
    CMD_CAL_DCBIAS_TABLE_GET = 0x93
    SUBCMD_CAL_DCBIAS_TARGET = 0x01
    SUBCMD_CAL_DCBIAS_ADC = 0x02
    
    # Calibration constant
    CALBUFNO = 26  # kgen_config.h의 #define CALBUFNO 26

    # AGC Setup (CMD=0x0E/0x8E)
    CMD_AGC_SETUP_SET = 0x0E
    CMD_AGC_SETUP_GET = 0x8E
    SUBCMD_AGC_SETUP = 0x00

    # Device Manager (CMD=0x0F/0x8F)
    CMD_DEVICE_MANAGER_SET = 0x0F
    CMD_DEVICE_MANAGER_GET = 0x8F
    SUBCMD_DEVICE_MANAGER = 0x00

    # System Control (CMD=0x10)
    CMD_SYSTEM_CONTROL = 0x10
    SUBCMD_SAVE_CONFIG = 0x00
    SUBCMD_GET_STATE = 0x01
    SUBCMD_GET_ADC_DAC = 0x02
    SUBCMD_GET_GATE_BIAS = 0x03
    SUBCMD_GET_DCC_IF = 0x04

    # DCC Gate Bias Control
    CMD_DCC_GATE_MAX_SET = 0x14
    CMD_DCC_GATE_MAX_GET = 0x94
    CMD_DCC_GATE_MIN_SET = 0x15
    CMD_DCC_GATE_MIN_GET = 0x95
    CMD_DCC_FACTOR_A_SET = 0x17
    CMD_DCC_FACTOR_A_GET = 0x97
    CMD_DCC_FACTOR_B_SET = 0x18
    CMD_DCC_FACTOR_B_GET = 0x98
    
    ######
    # DCC Gate Bias Control
    CMD_DCC_GATE_MAX_SET = 0x14
    CMD_DCC_GATE_MAX_GET = 0x94
    SUBCMD_DCC_GATE_MAX = 0x00

    CMD_DCC_GATE_MIN_SET = 0x15
    CMD_DCC_GATE_MIN_GET = 0x95
    SUBCMD_DCC_GATE_MIN = 0x00
    SUBCMD_DCC_GATE_MIN_ENABLE = 0x01

    CMD_DCC_FACTOR_A_SET = 0x17
    CMD_DCC_FACTOR_A_GET = 0x97
    SUBCMD_DCC_FACTOR_A = 0x00

    CMD_DCC_FACTOR_B_SET = 0x18
    CMD_DCC_FACTOR_B_GET = 0x98
    SUBCMD_DCC_FACTOR_B = 0x00

    # Global Config (Power Limits, VA Limit, Gate Bias)
    CMD_GLOBAL_CONFIG_SET = 0x01
    CMD_GLOBAL_CONFIG_GET = 0x81

    # Power Limits Subcmds
    SUBCMD_USER_POWER_LIMIT = 0x03
    SUBCMD_LOW_POWER_LIMIT = 0x04
    SUBCMD_MAX_POWER_LIMIT = 0x05
    SUBCMD_USER_REFLECTED_LIMIT = 0x06
    SUBCMD_MAX_REFLECTED_LIMIT = 0x07
    SUBCMD_USER_EXT_LIMIT = 0x08
    SUBCMD_MAX_EXT_VALUE = 0x09
    SUBCMD_MIN_EXT_VALUE = 0x0A

    # Gate Bias & VA Limit
    SUBCMD_GATE_BIAS = 0x0D  # 8 floats = 32 bytes
    SUBCMD_VA_LIMIT = 0x0E   # 2 floats = 8 bytes
    ######

    @staticmethod
    def create_frame(cmd, subcmd, data=None):
        """프로토콜 프레임 생성"""
        frame = bytearray([RFProtocol._SOM_, RFProtocol._SOM_, RFProtocol._DID_, cmd])
        data_len = len(data) + 1 if data else 1
        frame.append(data_len)
        frame.append(subcmd)
        if data:
            frame.extend(data)
        checksum = sum(frame[2:]) & 0xFF
        frame.append(checksum)
        frame.append(RFProtocol._EOM_)
        return bytes(frame)

    @staticmethod
    def parse_response(data):
        """수신된 데이터 파싱"""
        if len(data) < 6:
            return None
        if data[0] != RFProtocol._SOM_ or data[1] != RFProtocol._SOM_:
            return None
        if data[-1] != RFProtocol._EOM_:
            return None
        
        di = data[2]
        cmd = data[3]
        data_no = data[4]
        subcmd = data[5] if data_no > 0 else None
        
        if data_no > 1:
            data_body = data[6:-2]
        else:
            data_body = b''
        
        checksum = data[-2]
        calc_cs = sum(data[2:-2]) & 0xFF
        if calc_cs != checksum:
            return None
        
        return {
            "di": di,
            "cmd": cmd,
            "subcmd": subcmd,
            "data": data_body
        }

    @staticmethod
    def validate_command_data(cmd, subcmd, data):
        """명령어 데이터 유효성 검사"""
        if not isinstance(cmd, int) or not isinstance(subcmd, int):
            return False, "명령어는 정수여야 합니다"
        
        if cmd < 0 or cmd > 255 or subcmd < 0 or subcmd > 255:
            return False, "명령어는 0-255 범위여야 합니다"
        
        data_len = len(data) if data else 0
        
        expected_lengths = {
            # === 기본 명령어 ===
            (RFProtocol.CMD_RF_ON, RFProtocol.SUBCMD_RF_ON): 0,
            (RFProtocol.CMD_RF_OFF, RFProtocol.SUBCMD_RF_OFF): 0,
            
            # === 파워 설정 ===
            (RFProtocol.CMD_SET_POWER, RFProtocol.SUBCMD_SET_POWER): 4,
            (RFProtocol.CMD_GET_POWER, RFProtocol.SUBCMD_GET_POWER): 0,
            
            # === 제어 모드 ===
            (RFProtocol.CMD_CONTROL_MODE_SET, RFProtocol.SUBCMD_CONTROL_MODE_SET): 2,
            (RFProtocol.CMD_CONTROL_MODE_GET, RFProtocol.SUBCMD_CONTROL_MODE_GET): 0,
            
            # === 조절 모드 ===
            (RFProtocol.CMD_REGULATION_MODE_SET, RFProtocol.SUBCMD_REGULATION_MODE_SET): 2,
            (RFProtocol.CMD_REGULATION_MODE_GET, RFProtocol.SUBCMD_REGULATION_MODE_GET): 0,
            
            # === 램프 설정 ===
            (RFProtocol.CMD_RAMP_CONFIG_SET, RFProtocol.SUBCMD_RAMP_CONFIG_SET): 20,
            (RFProtocol.CMD_RAMP_CONFIG_GET, RFProtocol.SUBCMD_RAMP_CONFIG_GET): 0,
            
            # === 펌웨어 코드 기준 Pulse Configuration (CMD=0x02/0x82) ===
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_TYPE): 1,
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_MODE): 1,
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_OFFON): 1,
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_SYNC_OUTPUT): 1,
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_LEVEL): 16,  # float×4
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_DUTY): 16,   # float×4
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_SYNC_OUT_DELAY): 4,
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_SYNC_IN_DELAY): 4,
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_WIDTH_CONTROL): 4,
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_FREQ): 4,
            
            # GET 명령어 (데이터 없음)
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_TYPE): 0,
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_MODE): 0,
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_OFFON): 0,
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_SYNC_OUTPUT): 0,
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_LEVEL): 0,
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_DUTY): 0,
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_SYNC_OUT_DELAY): 0,
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_SYNC_IN_DELAY): 0,
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_WIDTH_CONTROL): 0,
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_FREQ): 0,
            
            # === CEX 설정 ===
            (RFProtocol.CMD_CEX_CONFIG_SET, RFProtocol.SUBCMD_CEX_CONFIG_SET): 12,
            (RFProtocol.CMD_CEX_CONFIG_GET, RFProtocol.SUBCMD_CEX_CONFIG_GET): 0,
            
            # === RF 주파수 ===
            (RFProtocol.CMD_SET_FREQUENCY, RFProtocol.SUBCMD_SET_FREQUENCY): 4,
            (RFProtocol.CMD_GET_FREQUENCY, RFProtocol.SUBCMD_GET_FREQUENCY): 0,
            
            # === 주파수 튜닝 ===
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_ENABLE): 1,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_RETUNING): 1,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MODE): 1,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MIN_FREQ): 4,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MAX_FREQ): 4,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_START_FREQ): 4,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MIN_STEP): 4,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MAX_STEP): 4,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_STOP_GAMMA): 4,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_RETURN_GAMMA): 4,
            
            # === Bank Function ===
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_ENABLE): 4,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_EQUATION_ENABLE): 4,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_RESTART): 4,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_RF_TRIGGER): 4,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_PARAMS): 20,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_ENABLE): 4,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_EQUATION_ENABLE): 4,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_RESTART): 4,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_RF_TRIGGER): 4,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_PARAMS): 20,
            
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK1_ENABLE): 0,
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK1_EQUATION_ENABLE): 0,
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK1_RESTART): 0,
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK1_RF_TRIGGER): 0,
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK1_PARAMS): 0,
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK2_ENABLE): 0,
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK2_EQUATION_ENABLE): 0,
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK2_RESTART): 0,
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK2_RF_TRIGGER): 0,
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK2_PARAMS): 0,
            
            # === 알람 클리어 ===
            (RFProtocol.CMD_ALARM_CLEAR, RFProtocol.SUBCMD_ALARM_CLEAR): 2,

            # === DCC Gate Bias Control (112 bytes - 27 floats + 1 uint32) ===
            (RFProtocol.CMD_DCC_GATE_MAX_SET, RFProtocol.SUBCMD_DCC_GATE_MAX): 112,
            (RFProtocol.CMD_DCC_GATE_MAX_GET, RFProtocol.SUBCMD_DCC_GATE_MAX): 0,
            (RFProtocol.CMD_DCC_GATE_MIN_SET, RFProtocol.SUBCMD_DCC_GATE_MIN): 112,
            (RFProtocol.CMD_DCC_GATE_MIN_GET, RFProtocol.SUBCMD_DCC_GATE_MIN): 0,
            (RFProtocol.CMD_DCC_GATE_MIN_SET, RFProtocol.SUBCMD_DCC_GATE_MIN_ENABLE): 4,
            (RFProtocol.CMD_DCC_GATE_MIN_GET, RFProtocol.SUBCMD_DCC_GATE_MIN_ENABLE): 0,
            (RFProtocol.CMD_DCC_FACTOR_A_SET, RFProtocol.SUBCMD_DCC_FACTOR_A): 112,
            (RFProtocol.CMD_DCC_FACTOR_A_GET, RFProtocol.SUBCMD_DCC_FACTOR_A): 0,
            (RFProtocol.CMD_DCC_FACTOR_B_SET, RFProtocol.SUBCMD_DCC_FACTOR_B): 112,
            (RFProtocol.CMD_DCC_FACTOR_B_GET, RFProtocol.SUBCMD_DCC_FACTOR_B): 0,
            
            ########## 20251024
            # === Global Config ===
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_USER_POWER_LIMIT): 4,
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_LOW_POWER_LIMIT): 4,
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_MAX_POWER_LIMIT): 4,
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_USER_REFLECTED_LIMIT): 4,
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_MAX_REFLECTED_LIMIT): 4,
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_USER_EXT_LIMIT): 4,
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_MAX_EXT_VALUE): 4,
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_MIN_EXT_VALUE): 4,
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_GATE_BIAS): 32,
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_VA_LIMIT): 8,

            # GET commands for Global Config (데이터 없음)
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_USER_POWER_LIMIT): 0,
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_LOW_POWER_LIMIT): 0,
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_MAX_POWER_LIMIT): 0,
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_USER_REFLECTED_LIMIT): 0,
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_MAX_REFLECTED_LIMIT): 0,
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_USER_EXT_LIMIT): 0,
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_MAX_EXT_VALUE): 0,
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_MIN_EXT_VALUE): 0,
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_GATE_BIAS): 0,
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_VA_LIMIT): 0,
            ########## 20251024
            
            
            # === 네트워크 설정 ===
            (RFProtocol.CMD_NETWORK_MAC_GET, RFProtocol.SUBCMD_NETWORK_MAC_GET): 0,
            (RFProtocol.CMD_NETWORK_TCPIP_SET, RFProtocol.SUBCMD_NETWORK_TCPIP_SET): 20,
            (RFProtocol.CMD_NETWORK_TCPIP_GET, RFProtocol.SUBCMD_NETWORK_TCPIP_GET): 0,
            
            # === Calibration Tables ===
            (RFProtocol.CMD_CAL_RFSET_TABLE_SET, RFProtocol.SUBCMD_CAL_RFSET_TARGET): 104,
            (RFProtocol.CMD_CAL_RFSET_TABLE_SET, RFProtocol.SUBCMD_CAL_RFSET_DACC): 52,
            (RFProtocol.CMD_CAL_RFSET_TABLE_SET, RFProtocol.SUBCMD_CAL_RFSET_DACL): 52,
            (RFProtocol.CMD_CAL_RFSET_TABLE_SET, RFProtocol.SUBCMD_CAL_RFSET_DACH): 52,
            
            (RFProtocol.CMD_CAL_FWDLOAD_TABLE_SET, RFProtocol.SUBCMD_CAL_FWDLOAD_TARGET): 104,
            (RFProtocol.CMD_CAL_FWDLOAD_TABLE_SET, RFProtocol.SUBCMD_CAL_FWDLOAD_DAC): 52,
            
            (RFProtocol.CMD_CAL_REF_TABLE_SET, RFProtocol.SUBCMD_CAL_REF_TARGET): 104,
            (RFProtocol.CMD_CAL_REF_TABLE_SET, RFProtocol.SUBCMD_CAL_REF_DAC): 52,
            
            (RFProtocol.CMD_CAL_RFSETIN_TABLE_SET, RFProtocol.SUBCMD_CAL_RFSETIN_TARGET): 104,
            (RFProtocol.CMD_CAL_RFSETIN_TABLE_SET, RFProtocol.SUBCMD_CAL_RFSETIN_ADC): 52,
            
            (RFProtocol.CMD_CAL_DCBIAS_TABLE_SET, RFProtocol.SUBCMD_CAL_DCBIAS_TARGET): 104,
            (RFProtocol.CMD_CAL_DCBIAS_TABLE_SET, RFProtocol.SUBCMD_CAL_DCBIAS_ADC): 52,
            
            # === 장비 상태 조회 ===
            (RFProtocol.CMD_DEVICE_STATUS_GET, RFProtocol.SUBCMD_DEVICE_STATUS): 0,
        }
        
        expected_len = expected_lengths.get((cmd, subcmd))
        if expected_len is not None and data_len != expected_len:
            return False, f"데이터 길이 불일치: 기대={expected_len}, 실제={data_len}"
        
        return True, "유효한 명령어"

    @staticmethod
    def get_command_description(cmd, subcmd):
        """명령어 설명 반환 - VHF 매뉴얼 전체 반영"""
        command_map = {
            # === 기본 명령어 ===
            (RFProtocol.CMD_RF_ON, RFProtocol.SUBCMD_RF_ON): "RF 출력 켜기",
            (RFProtocol.CMD_RF_OFF, RFProtocol.SUBCMD_RF_OFF): "RF 출력 끄기",
            
            # === 장비 상태 ===
            (RFProtocol.CMD_DEVICE_STATUS_GET, RFProtocol.SUBCMD_DEVICE_STATUS): "장비 상태 조회",
            
            # === 파워 설정 ===
            (RFProtocol.CMD_SET_POWER, RFProtocol.SUBCMD_SET_POWER): "출력 파워 설정",
            (RFProtocol.CMD_GET_POWER, RFProtocol.SUBCMD_GET_POWER): "설정 파워 조회",
            
            # === 제어 모드 ===
            (RFProtocol.CMD_CONTROL_MODE_SET, RFProtocol.SUBCMD_CONTROL_MODE_SET): "제어 모드 설정",
            (RFProtocol.CMD_CONTROL_MODE_GET, RFProtocol.SUBCMD_CONTROL_MODE_GET): "제어 모드 조회",
            
            # === 조절 모드 ===
            (RFProtocol.CMD_REGULATION_MODE_SET, RFProtocol.SUBCMD_REGULATION_MODE_SET): "조절 모드 설정",
            (RFProtocol.CMD_REGULATION_MODE_GET, RFProtocol.SUBCMD_REGULATION_MODE_GET): "조절 모드 조회",
            
            # === 램프 설정 ===
            (RFProtocol.CMD_RAMP_CONFIG_SET, RFProtocol.SUBCMD_RAMP_CONFIG_SET): "램프 설정",
            (RFProtocol.CMD_RAMP_CONFIG_GET, RFProtocol.SUBCMD_RAMP_CONFIG_GET): "램프 설정 조회",
            
            # === Pulse 명령어 (세부 제어용) ===
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_TYPE): "펄스 타입 설정",
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_MODE): "펄스 모드 설정",
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_OFFON): "펄스 On/Off 설정",
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_SYNC_OUTPUT): "펄스 동기 출력 설정",
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_LEVEL): "펄스 레벨 설정",
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_DUTY): "펄스 듀티 설정",
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_SYNC_OUT_DELAY): "펄스 출력 동기 지연 설정",
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_SYNC_IN_DELAY): "펄스 입력 동기 지연 설정",
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_WIDTH_CONTROL): "펄스 폭 제어 설정",
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_FREQ): "펄스 주파수 설정",
            
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_TYPE): "펄스 타입 조회",
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_MODE): "펄스 모드 조회",
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_OFFON): "펄스 On/Off 조회",
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_SYNC_OUTPUT): "펄스 동기 출력 조회",
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_LEVEL): "펄스 레벨 조회",
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_DUTY): "펄스 듀티 조회",
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_SYNC_OUT_DELAY): "펄스 출력 동기 지연 조회",
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_SYNC_IN_DELAY): "펄스 입력 동기 지연 조회",
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_WIDTH_CONTROL): "펄스 폭 제어 조회",
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_FREQ): "펄스 주파수 조회",
            
            # === 간소화된 Pulse 명령어 (data_manager 호환) ===
            # (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_MODE_SET): "펄스 모드 설정",
            # (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_PARAMS_SET): "펄스 파라미터 설정",
            # (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_MODE_GET): "펄스 모드 조회",
            # (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_PARAMS_GET): "펄스 파라미터 조회",
            
            # === CEX 설정 ===
            (RFProtocol.CMD_CEX_CONFIG_SET, RFProtocol.SUBCMD_CEX_CONFIG_SET): "CEX 설정",
            (RFProtocol.CMD_CEX_CONFIG_GET, RFProtocol.SUBCMD_CEX_CONFIG_GET): "CEX 설정 조회",
            
            # === RF 주파수 ===
            (RFProtocol.CMD_SET_FREQUENCY, RFProtocol.SUBCMD_SET_FREQUENCY): "RF 주파수 설정",
            (RFProtocol.CMD_GET_FREQUENCY, RFProtocol.SUBCMD_GET_FREQUENCY): "RF 주파수 조회",
            
            # === 주파수 튜닝 ===
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_ENABLE): "주파수 튜닝 활성화",
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_RETUNING): "재튜닝 모드 설정",
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MODE): "튜닝 모드 설정",
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MIN_FREQ): "최소 주파수 설정",
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MAX_FREQ): "최대 주파수 설정",
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_START_FREQ): "시작 주파수 설정",
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MIN_STEP): "최소 스텝 설정",
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MAX_STEP): "최대 스텝 설정",
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_STOP_GAMMA): "정지 감마 설정",
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_RETURN_GAMMA): "복귀 감마 설정",
            
            # === Bank Function ===
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_ENABLE): "Bank1 활성화 설정",
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_EQUATION_ENABLE): "Bank1 방정식 활성화",
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_RESTART): "Bank1 재시작",
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_RF_TRIGGER): "Bank1 RF 트리거",
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_PARAMS): "Bank1 파라미터 설정",
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_ENABLE): "Bank2 활성화 설정",
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_EQUATION_ENABLE): "Bank2 방정식 활성화",
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_RESTART): "Bank2 재시작",
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_RF_TRIGGER): "Bank2 RF 트리거",
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_PARAMS): "Bank2 파라미터 설정",
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK1_ENABLE): "Bank1 활성화 조회",
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK1_EQUATION_ENABLE): "Bank1 방정식 조회",
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK1_PARAMS): "Bank1 파라미터 조회",
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK2_ENABLE): "Bank2 활성화 조회",
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK2_EQUATION_ENABLE): "Bank2 방정식 조회",
            (RFProtocol.CMD_BANK_GET, RFProtocol.SUBCMD_BANK2_PARAMS): "Bank2 파라미터 조회",
            
            # === 알람 클리어 ===
            (RFProtocol.CMD_ALARM_CLEAR, RFProtocol.SUBCMD_ALARM_CLEAR): "알람 클리어",
            
            # === 네트워크 설정 ===
            (RFProtocol.CMD_NETWORK_MAC_GET, RFProtocol.SUBCMD_NETWORK_MAC_GET): "MAC 주소 조회",
            (RFProtocol.CMD_NETWORK_TCPIP_SET, RFProtocol.SUBCMD_NETWORK_TCPIP_SET): "TCP/IP 설정",
            (RFProtocol.CMD_NETWORK_TCPIP_GET, RFProtocol.SUBCMD_NETWORK_TCPIP_GET): "TCP/IP 조회",
            
            # === Developer Commands ===
            (RFProtocol.CMD_ARC_MANAGEMENT_SET, 0x00): "Arc Management 설정",
            (RFProtocol.CMD_ARC_MANAGEMENT_GET, 0x00): "Arc Management 조회",
            (RFProtocol.CMD_SDD_CONFIG_SET, 0x00): "SDD Config 설정",
            (RFProtocol.CMD_SDD_CONFIG_GET, 0x00): "SDD Config 조회",
            (RFProtocol.CMD_FAST_ACQ_SET, 0x00): "Fast Acquisition 설정",
            (RFProtocol.CMD_FAST_ACQ_GET, 0x00): "Fast Acquisition 조회",
            (RFProtocol.CMD_DDS_CTL_SET, 0x00): "DDS Control 설정",
            (RFProtocol.CMD_DDS_CTL_GET, 0x00): "DDS Control 조회",
            (RFProtocol.CMD_CAL_CTL_SET, 0x00): "Calibration Control 설정",
            (RFProtocol.CMD_CAL_CTL_GET, 0x00): "Calibration Control 조회",
            (RFProtocol.CMD_AGC_SETUP_SET, 0x00): "AGC Setup 설정",
            (RFProtocol.CMD_AGC_SETUP_GET, 0x00): "AGC Setup 조회",
            (RFProtocol.CMD_DEVICE_MANAGER_GET, 0x00): "Device Manager 조회",
            (RFProtocol.CMD_SYSTEM_CONTROL, RFProtocol.SUBCMD_SAVE_CONFIG): "Config 저장",
            (RFProtocol.CMD_SYSTEM_CONTROL, RFProtocol.SUBCMD_GET_STATE): "System State 조회",
            (RFProtocol.CMD_SYSTEM_CONTROL, RFProtocol.SUBCMD_GET_ADC_DAC): "ADC/DAC 조회",
            (RFProtocol.CMD_SYSTEM_CONTROL, RFProtocol.SUBCMD_GET_GATE_BIAS): "Gate Bias 조회",
            (RFProtocol.CMD_SYSTEM_CONTROL, RFProtocol.SUBCMD_GET_DCC_IF): "DCC Interface 조회",
            
            
            # === DCC Gate Bias Control
            (RFProtocol.CMD_DCC_GATE_MAX_SET, RFProtocol.SUBCMD_DCC_GATE_MAX): "DCC Gate Maximum 설정",
            (RFProtocol.CMD_DCC_GATE_MAX_GET, RFProtocol.SUBCMD_DCC_GATE_MAX): "DCC Gate Maximum 조회",
            (RFProtocol.CMD_DCC_GATE_MIN_SET, RFProtocol.SUBCMD_DCC_GATE_MIN): "DCC Gate Minimum 설정",
            (RFProtocol.CMD_DCC_GATE_MIN_GET, RFProtocol.SUBCMD_DCC_GATE_MIN): "DCC Gate Minimum 조회",
            (RFProtocol.CMD_DCC_FACTOR_A_SET, RFProtocol.SUBCMD_DCC_FACTOR_A): "DCC Factor A 설정",
            (RFProtocol.CMD_DCC_FACTOR_A_GET, RFProtocol.SUBCMD_DCC_FACTOR_A): "DCC Factor A 조회",
            (RFProtocol.CMD_DCC_FACTOR_B_SET, RFProtocol.SUBCMD_DCC_FACTOR_B): "DCC Factor B 설정",
            (RFProtocol.CMD_DCC_FACTOR_B_GET, RFProtocol.SUBCMD_DCC_FACTOR_B): "DCC Factor B 조회",
            
            #############20251024
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_USER_POWER_LIMIT): "사용자 출력 제한 설정",
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_LOW_POWER_LIMIT): "저출력 제한 설정",
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_MAX_POWER_LIMIT): "최대 출력 제한 설정",
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_USER_REFLECTED_LIMIT): "사용자 반사 출력 제한 설정",
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_MAX_REFLECTED_LIMIT): "최대 반사 출력 제한 설정",
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_USER_EXT_LIMIT): "사용자 외부 피드백 제한 설정",
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_MAX_EXT_VALUE): "최대 외부 피드백 값 설정",
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_MIN_EXT_VALUE): "최소 외부 피드백 값 설정",
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_GATE_BIAS): "게이트 바이어스 설정",
            (RFProtocol.CMD_GLOBAL_CONFIG_SET, RFProtocol.SUBCMD_VA_LIMIT): "VA 제한 설정",

            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_USER_POWER_LIMIT): "사용자 출력 제한 조회",
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_LOW_POWER_LIMIT): "저출력 제한 조회",
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_MAX_POWER_LIMIT): "최대 출력 제한 조회",
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_USER_REFLECTED_LIMIT): "사용자 반사 출력 제한 조회",
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_MAX_REFLECTED_LIMIT): "최대 반사 출력 제한 조회",
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_USER_EXT_LIMIT): "사용자 외부 피드백 제한 조회",
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_MAX_EXT_VALUE): "최대 외부 피드백 값 조회",
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_MIN_EXT_VALUE): "최소 외부 피드백 값 조회",
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_GATE_BIAS): "게이트 바이어스 조회",
            (RFProtocol.CMD_GLOBAL_CONFIG_GET, RFProtocol.SUBCMD_VA_LIMIT): "VA 제한 조회",
            #############20251024
            
            # === Calibration Tables ===
            (RFProtocol.CMD_CAL_RFSET_TABLE_SET, RFProtocol.SUBCMD_CAL_RFSET_TARGET): "RF Set DAC Table - Target 설정",
            (RFProtocol.CMD_CAL_RFSET_TABLE_SET, RFProtocol.SUBCMD_CAL_RFSET_DACC): "RF Set DAC Table - DAC Center 설정",
            (RFProtocol.CMD_CAL_RFSET_TABLE_SET, RFProtocol.SUBCMD_CAL_RFSET_DACL): "RF Set DAC Table - DAC Low 설정",
            (RFProtocol.CMD_CAL_RFSET_TABLE_SET, RFProtocol.SUBCMD_CAL_RFSET_DACH): "RF Set DAC Table - DAC High 설정",
            
            (RFProtocol.CMD_CAL_RFSET_TABLE_GET, RFProtocol.SUBCMD_CAL_RFSET_TARGET): "RF Set DAC Table - Target 조회",
            (RFProtocol.CMD_CAL_RFSET_TABLE_GET, RFProtocol.SUBCMD_CAL_RFSET_DACC): "RF Set DAC Table - DAC Center 조회",
            (RFProtocol.CMD_CAL_RFSET_TABLE_GET, RFProtocol.SUBCMD_CAL_RFSET_DACL): "RF Set DAC Table - DAC Low 조회",
            (RFProtocol.CMD_CAL_RFSET_TABLE_GET, RFProtocol.SUBCMD_CAL_RFSET_DACH): "RF Set DAC Table - DAC High 조회",
            
            (RFProtocol.CMD_CAL_FWDLOAD_TABLE_SET, RFProtocol.SUBCMD_CAL_FWDLOAD_TARGET): "FWD/LOAD Table - Target 설정",
            (RFProtocol.CMD_CAL_FWDLOAD_TABLE_SET, RFProtocol.SUBCMD_CAL_FWDLOAD_DAC): "FWD/LOAD Table - DAC 설정",
            (RFProtocol.CMD_CAL_FWDLOAD_TABLE_GET, RFProtocol.SUBCMD_CAL_FWDLOAD_TARGET): "FWD/LOAD Table - Target 조회",
            (RFProtocol.CMD_CAL_FWDLOAD_TABLE_GET, RFProtocol.SUBCMD_CAL_FWDLOAD_DAC): "FWD/LOAD Table - DAC 조회",
            
            (RFProtocol.CMD_CAL_REF_TABLE_SET, RFProtocol.SUBCMD_CAL_REF_TARGET): "REF Table - Target 설정",
            (RFProtocol.CMD_CAL_REF_TABLE_SET, RFProtocol.SUBCMD_CAL_REF_DAC): "REF Table - DAC 설정",
            (RFProtocol.CMD_CAL_REF_TABLE_GET, RFProtocol.SUBCMD_CAL_REF_TARGET): "REF Table - Target 조회",
            (RFProtocol.CMD_CAL_REF_TABLE_GET, RFProtocol.SUBCMD_CAL_REF_DAC): "REF Table - DAC 조회",
            
            (RFProtocol.CMD_CAL_RFSETIN_TABLE_SET, RFProtocol.SUBCMD_CAL_RFSETIN_TARGET): "RF Set IN Table - Target 설정",
            (RFProtocol.CMD_CAL_RFSETIN_TABLE_SET, RFProtocol.SUBCMD_CAL_RFSETIN_ADC): "RF Set IN Table - ADC 설정",
            (RFProtocol.CMD_CAL_RFSETIN_TABLE_GET, RFProtocol.SUBCMD_CAL_RFSETIN_TARGET): "RF Set IN Table - Target 조회",
            (RFProtocol.CMD_CAL_RFSETIN_TABLE_GET, RFProtocol.SUBCMD_CAL_RFSETIN_ADC): "RF Set IN Table - ADC 조회",
            
            (RFProtocol.CMD_CAL_DCBIAS_TABLE_SET, RFProtocol.SUBCMD_CAL_DCBIAS_TARGET): "DC Bias Table - Target 설정",
            (RFProtocol.CMD_CAL_DCBIAS_TABLE_SET, RFProtocol.SUBCMD_CAL_DCBIAS_ADC): "DC Bias Table - ADC 설정",
            (RFProtocol.CMD_CAL_DCBIAS_TABLE_GET, RFProtocol.SUBCMD_CAL_DCBIAS_TARGET): "DC Bias Table - Target 조회",
            (RFProtocol.CMD_CAL_DCBIAS_TABLE_GET, RFProtocol.SUBCMD_CAL_DCBIAS_ADC): "DC Bias Table - ADC 조회",
        }
        
        return command_map.get((cmd, subcmd), f"알 수 없는 명령어 (CMD=0x{cmd:02x}, SUBCMD=0x{subcmd:02x})")


class BatchCommandTracker:
    """배치 명령어 실행 추적기"""
    
    def __init__(self, total_commands, callback=None):
        self.total_commands = total_commands
        self.completed_commands = 0
        self.successful_commands = 0
        self.failed_commands = []
        self.callback = callback
        self.start_time = time.time()
        
    def on_command_completed(self, command_id, success, message):
        """개별 명령어 완료 처리"""
        self.completed_commands += 1
        
        if success:
            self.successful_commands += 1
        else:
            self.failed_commands.append(f"{command_id}: {message}")
        
        if self.completed_commands >= self.total_commands:
            self._handle_batch_completion()
    
    def _handle_batch_completion(self):
        """배치 완료 처리"""
        execution_time = time.time() - self.start_time
        
        result = {
            'total': self.total_commands,
            'successful': self.successful_commands,
            'failed': len(self.failed_commands),
            'failed_list': self.failed_commands,
            'execution_time': execution_time
        }
        
        if self.callback:
            self.callback(result)


class HybridRFClientThread(QThread):
    """하이브리드 RF 클라이언트 - 동기/비동기 지원"""
    
    data_received = pyqtSignal(bytes, float)
    connection_established = pyqtSignal()
    connection_failed = pyqtSignal(str)
    command_completed = pyqtSignal(str, bool, str)
    batch_completed = pyqtSignal(dict)

    def __init__(self, host="127.0.0.1", port=5000):
        super().__init__()
        self.host = host
        self.port = port
        self.running = True
        
        self.status_socket = None
        self.command_queue = queue.Queue(maxsize=50)
        
        self.status_lock = threading.RLock()
        self.command_lock = threading.RLock()
        
        self.connection_attempts = 0
        self.frame_count = 0
        self.is_status_paused = False
        self.parent = None
        
        self.settings_manager = SettingsManager() # yuri 추가
        #############
        # 데이터 처리 타이머 설정
        interval_ms = 50  # 기본값
        try:
            if hasattr(self, 'settings_manager'):
                dc = self.settings_manager.settings.get("data_collection", {})
                interval_ms = dc.get("status_interval_ms", 50)
        except:
            pass
        #############
        
        # Status polling 주기 (초 단위)
        self.status_polling_interval = interval_ms/1000  # 기본값 50ms yuri kim
        
        self.batch_tracker = None
        self.cleanup_completed = False
        self.connection_state = "unknown"
        
        import atexit
        atexit.register(self._emergency_cleanup)
        
    def _set_connection_state(self, new_state):
        """연결 상태 변경 시에만 로그 출력"""
        if self.connection_state != new_state:
            old_state = self.connection_state
            self.connection_state = new_state
            
            if new_state == "connected" and old_state != "connected":
                self.write_log("[INFO] 서버 연결 상태: 정상", "green")
            elif new_state == "disconnected" and old_state != "disconnected":
                self.write_log("[WARNING] 서버 연결 상태: 끊어짐", "yellow")
    
    def _emergency_cleanup(self):
        """비상 정리"""
        if not getattr(self, 'cleanup_completed', False):
            try:
                self.stop()
                time.sleep(0.5)
            except Exception as e:
                print(f"[RF_CLIENT] 비상 정리 오류: {e}")

    def _format_hex_data(self, data):
        """데이터를 16진수 문자열로 포맷"""
        if not data:
            return "None"
        
        hex_str = data.hex().upper()
        grouped = []
        for i in range(0, len(hex_str), 16):
            group = hex_str[i:i+16]
            formatted_group = ' '.join(group[j:j+2] for j in range(0, len(group), 2))
            grouped.append(formatted_group)
        
        return ' | '.join(grouped)

    def _create_socket(self):
        """소켓 생성"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        if hasattr(socket, 'SO_LINGER'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
    
        return sock

    def _receive_full_frame(self, socket_obj, timeout=SOCKET_TIMEOUT):
        """완전한 프레임 수신"""
        received_data = bytearray()
        start_time = time.time()
        original_timeout = socket_obj.gettimeout()
        
        try:
            socket_obj.settimeout(timeout)
            
            while time.time() - start_time < timeout:
                try:
                    data = socket_obj.recv(64)
                    if not data:
                        return None, time.time(), "[RECV] 서버에 의해 연결 종료"
                    
                    received_data.extend(data)
                    
                    if len(received_data) >= 6 and received_data[0] == RFProtocol._SOM_ and received_data[1] == RFProtocol._SOM_:
                        data_no = received_data[4]
                        expected_size = 6 + data_no + 1
                        
                        if len(received_data) >= expected_size:
                            frame = bytes(received_data[:expected_size])
                            parsed = RFProtocol.parse_response(frame)
                            
                            with threading.Lock():
                                self.frame_count += 1
                            
                            is_status_query = (parsed and 
                                             parsed["cmd"] == RFProtocol.CMD_DEVICE_STATUS_GET and 
                                             parsed["subcmd"] == RFProtocol.SUBCMD_DEVICE_STATUS)
                            
                            if not is_status_query:
                                cmd_desc = "알 수 없음"
                                if parsed:
                                    cmd_desc = RFProtocol.get_command_description(parsed["cmd"], parsed["subcmd"])
                                
                                subcmd_value = frame[5] if len(frame) > 5 else 0
                                
                                log_msg = (f"[RECV] 프레임 #{self.frame_count} 수신: {cmd_desc}\n"
                                         f"    └─ CMD=0x{frame[3]:02X}, SUBCMD=0x{subcmd_value:02X}\n"
                                         f"    └─ 데이터: {self._format_hex_data(parsed['data'] if parsed else b'')}\n"
                                         f"    └─ 원시: {self._format_hex_data(frame)}")
                            else:
                                log_msg = f"[RECV] 상태 데이터 수신 (프레임 #{self.frame_count})"
                            
                            if not parsed:
                                log_msg += "\n    ⚠️ 프레임 파싱 실패"
                            
                            return frame, time.time(), log_msg
                            
                except socket.error as e:
                    return None, time.time(), f"[RECV] 수신 오류: {e}"
                    
        except socket.timeout:
            return None, time.time(), f"[RECV] 타임아웃: {timeout}초"
        finally:
            socket_obj.settimeout(original_timeout)
        
        return None, time.time(), f"[RECV] 불완전한 프레임: {self._format_hex_data(received_data)}"

    def run(self):
        """메인 스레드"""
        command_worker = threading.Thread(target=self._command_worker, daemon=True)
        command_worker.start()
        
        while self.running:
            if not self.status_socket or self.status_socket.fileno() == -1:
                self._set_connection_state("disconnected")
                self._reconnect_status()
            else:
                try:
                    if not self.is_status_paused:
                        with self.status_lock:
                            self.status_socket.send(RFProtocol.create_frame(
                                RFProtocol.CMD_DEVICE_STATUS_GET, 
                                RFProtocol.SUBCMD_DEVICE_STATUS
                            ))
                            
                            received_data, timestamp, log_msg = self._receive_full_frame(self.status_socket, timeout=2.0)
                            
                            if received_data:
                                self._set_connection_state("connected")
                                try:
                                    if hasattr(self.parent, 'show_status_logs') and self.parent.show_status_logs:
                                        self.write_log(log_msg)
                                    self.data_received.emit(received_data, timestamp)
                                    self.connection_attempts = 0
                                except RuntimeError as e:
                                    if "deleted" in str(e) or "destroyed" in str(e):
                                        print("[CRITICAL] MainWindow 객체 파괴 감지. 스레드 종료.")
                                        self.running = False # 스레드 루프 종료
                                        continue # 루프 탈출
                                    raise e # 다른 RuntimeError는 다시 발생
                            else:
                                self._set_connection_state("disconnected")
                                
                                self.data_received.emit(b"", timestamp)
                                if "타임아웃" in log_msg or "파싱 실패" in log_msg:
                                    self.write_log(log_msg)
                                    
                except (socket.timeout, socket.error) as e:
                    self._set_connection_state("disconnected")
                    
                    self.data_received.emit(b"", time.time())
                    if isinstance(e, socket.error) and hasattr(e, 'errno') and e.errno == 10054:##############
                        self._close_status_socket()
                
                time.sleep(self.status_polling_interval)

    def _command_worker(self):
        """명령어 처리 워커 스레드"""
        while self.running:
            try:
                command_item = self.command_queue.get(timeout=1.0)
                
                if command_item is None:
                    break
                
                command_id, cmd, subcmd, data, timeout, wait_response, is_sync = command_item
                
                result = self._execute_command(cmd, subcmd, data, timeout, wait_response)
                
                if is_sync:
                    pass
                else:
                    self.command_completed.emit(command_id, result.success, result.message)
                    
                    if self.batch_tracker:
                        self.batch_tracker.on_command_completed(command_id, result.success, result.message)
                
                self.command_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.write_log(f"[ERROR] 명령어 워커 오류: {e}")

    def _execute_command(self, cmd, subcmd, data, timeout, wait_response):
        """단일 명령어 실행"""
        command_socket = None
        start_time = time.time()
        
        try:
            with self.command_lock:
                if not self.running:
                    return CommandResult(False, "클라이언트가 종료 중입니다", execution_time=time.time() - start_time)
                
                command_socket = self._create_optimized_socket()
                command_socket.settimeout(timeout)
                
                try:
                    command_socket.connect((self.host, self.port))
                except Exception as connect_error:
                    return CommandResult(False, f"연결 실패: {connect_error}", execution_time=time.time() - start_time)
                
                cmd_desc = RFProtocol.get_command_description(cmd, subcmd)
                frame = RFProtocol.create_frame(cmd, subcmd, data)
                
                command_socket.sendall(frame)
                
                if wait_response:
                    received_data, _, recv_log_msg = self._receive_full_frame(command_socket, timeout)
                    
                    if received_data:
                        if cmd in [RFProtocol.CMD_RF_ON, RFProtocol.CMD_RF_OFF, RFProtocol.CMD_SET_POWER,
                                   RFProtocol.CMD_CONTROL_MODE_SET, RFProtocol.CMD_REGULATION_MODE_SET,
                                   RFProtocol.CMD_RAMP_CONFIG_SET, RFProtocol.CMD_CEX_CONFIG_SET,
                                   RFProtocol.CMD_PULSE_SET, RFProtocol.CMD_SET_FREQUENCY,
                                   RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.CMD_BANK_SET,
                                   RFProtocol.CMD_ARC_MANAGEMENT_SET, RFProtocol.CMD_ARC_MANAGEMENT_GET,
                                   RFProtocol.CMD_SDD_CONFIG_SET, RFProtocol.CMD_SDD_CONFIG_GET,
                                   RFProtocol.CMD_FAST_ACQ_SET, RFProtocol.CMD_FAST_ACQ_GET,
                                   RFProtocol.CMD_DDS_CTL_SET, RFProtocol.CMD_DDS_CTL_GET,
                                   RFProtocol.CMD_CAL_CTL_SET, RFProtocol.CMD_CAL_CTL_GET,
                                   RFProtocol.CMD_CAL_RFSET_TABLE_SET, RFProtocol.CMD_CAL_RFSET_TABLE_GET,
                                   RFProtocol.CMD_CAL_FWDLOAD_TABLE_SET, RFProtocol.CMD_CAL_FWDLOAD_TABLE_GET,
                                   RFProtocol.CMD_CAL_REF_TABLE_SET, RFProtocol.CMD_CAL_REF_TABLE_GET,
                                   RFProtocol.CMD_CAL_RFSETIN_TABLE_SET, RFProtocol.CMD_CAL_RFSETIN_TABLE_GET,
                                   RFProtocol.CMD_CAL_DCBIAS_TABLE_SET, RFProtocol.CMD_CAL_DCBIAS_TABLE_GET,
                                   RFProtocol.CMD_AGC_SETUP_SET, RFProtocol.CMD_AGC_SETUP_GET,
                                   RFProtocol.CMD_DEVICE_MANAGER_GET,
                                   RFProtocol.CMD_SYSTEM_CONTROL,
                                   RFProtocol.CMD_DCC_GATE_MAX_SET, RFProtocol.CMD_DCC_GATE_MAX_GET,
                                   RFProtocol.CMD_DCC_GATE_MIN_SET, RFProtocol.CMD_DCC_GATE_MIN_GET,
                                   RFProtocol.CMD_DCC_FACTOR_A_SET, RFProtocol.CMD_DCC_FACTOR_A_GET,
                                   RFProtocol.CMD_DCC_FACTOR_B_SET, RFProtocol.CMD_DCC_FACTOR_B_GET]:
                            self.write_log(recv_log_msg, "magenta")
                        
                        return self._parse_command_result(received_data, cmd_desc, start_time)
                    else:
                        return CommandResult(
                            False,
                            f"{cmd_desc} 응답 수신 실패: {recv_log_msg}",
                            execution_time=time.time() - start_time
                        )
                else:
                    return CommandResult(
                        True,
                        f"{cmd_desc} 전송 완료",
                        execution_time=time.time() - start_time
                    )
                    
        except Exception as e:
            return CommandResult(
                False,
                f"명령어 실행 오류: {e}",
                execution_time=time.time() - start_time
            )
            
        finally:
            if command_socket:
                try:
                    command_socket.shutdown(socket.SHUT_RDWR)
                    command_socket.close()
                except:
                    pass
         
    def _create_optimized_socket(self):
        """최적화된 소켓 생성"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        
        if hasattr(socket, 'SO_LINGER'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
        
        return sock
            
    def _create_send_log(self, cmd_desc, cmd, subcmd, data, frame):
        """전송 로그 생성"""
        send_log = (f"[SEND] {cmd_desc}\n"
                   f"    ├─ 명령어: CMD=0x{cmd:02X}, SUBCMD=0x{subcmd:02X}\n"
                   f"    ├─ 데이터 크기: {len(data) if data else 0} 바이트\n")
        
        if data and len(data) > 0:
            send_log += f"    ├─ 페이로드: {self._format_hex_data(data)}\n"
        
        send_log += f"    └─ 완성 프레임: {self._format_hex_data(frame)}"
        return send_log
        
    def _parse_command_result(self, received_data, cmd_desc, start_time):
        """명령어 결과 파싱"""
        parsed = RFProtocol.parse_response(received_data)
        execution_time = time.time() - start_time
        
        if parsed:
            cmd = parsed['cmd']
            
            # GET 명령어 (0x80 이상)는 항상 성공으로 처리
            if cmd >= 0x80:
                return CommandResult(
                    success=True,
                    message=f"{cmd_desc} 성공",
                    response_data=received_data,
                    error_code=0,
                    execution_time=execution_time
                )
            
            # ✅ 추가: CMD_SYSTEM_CONTROL의 GET SUBCMD들도 성공으로 처리
            if cmd == RFProtocol.CMD_SYSTEM_CONTROL and len(parsed['data']) > 1:
                # SUBCMD_GET_GATE_BIAS, SUBCMD_GET_ADC_DAC, SUBCMD_GET_DCC_IF 등
                # 이들은 데이터를 반환하므로 첫 바이트를 에러 코드로 보지 않음
                return CommandResult(
                    success=True,
                    message=f"{cmd_desc} 성공",
                    response_data=received_data,
                    error_code=0,
                    execution_time=execution_time
                )
            
            # SET 명령어만 첫 바이트를 에러 코드로 검사
            if len(parsed['data']) >= 1:
                error_code = parsed['data'][0]
                
                if error_code == 0:
                    return CommandResult(
                        success=True,
                        message=f"{cmd_desc} 성공",
                        response_data=received_data,
                        error_code=error_code,
                        execution_time=execution_time
                    )
                else:
                    error_msgs = {
                        1: "범위 초과", 2: "잘못된 조건", 
                        3: "정의되지 않음", 4: "명령어 오류"
                    }
                    error_msg = error_msgs.get(error_code, f"알 수 없는 오류 ({error_code})")
                    return CommandResult(
                        success=False,
                        message=f"{cmd_desc} 실패: {error_msg}",
                        response_data=received_data,
                        error_code=error_code,
                        execution_time=execution_time
                    )
        
        return CommandResult(
            success=True,
            message=f"{cmd_desc} 완료 (응답 파싱 실패)",
            response_data=received_data,
            execution_time=execution_time
        )

    def send_command(self, cmd, subcmd, data=None, wait_response=True, timeout=10.0, sync=False):
        """명령어 전송"""
        
        is_valid, msg = RFProtocol.validate_command_data(cmd, subcmd, data)
        if not is_valid:
            if sync:
                return CommandResult(False, f"명령어 검증 실패: {msg}")
            else:
                error_msg = f"[ERROR] 명령어 검증 실패: {msg}"
                self.write_log(error_msg)
                return error_msg, None
        
        if sync:
            return self._execute_command_sync(cmd, subcmd, data, timeout, wait_response)
        else:
            return self._queue_command_async(cmd, subcmd, data, timeout, wait_response)
    
    def _execute_command_sync(self, cmd, subcmd, data, timeout, wait_response) -> CommandResult:
        """동기 명령어 실행"""
        try:
            self.pause_status_polling()
            
            cmd_desc = RFProtocol.get_command_description(cmd, subcmd)
            frame = RFProtocol.create_frame(cmd, subcmd, data)
            
            send_log = self._create_send_log(cmd_desc, cmd, subcmd, data, frame)
            self.write_log(send_log, "cyan")
            
            result = self._execute_command(cmd, subcmd, data, timeout, wait_response)
            
            if result.success:
                self.write_log(f"[SUCCESS] {cmd_desc} 동기 실행 완료 ({result.execution_time:.2f}s)", "green")
            else:
                self.write_log(f"[ERROR] {cmd_desc} 동기 실행 실패: {result.message}", "red")
            
            return result
            
        except Exception as e:
            error_result = CommandResult(
                False, 
                f"동기 명령어 실행 중 예외: {str(e)}",
                execution_time=0.0
            )
            self.write_log(f"[CRITICAL] 동기 명령어 실행 예외: {e}", "red")
            return error_result
            
        finally:
            self.resume_status_polling()
    
    def _queue_command_async(self, cmd, subcmd, data, timeout, wait_response):
        """비동기 명령어 대기열 추가"""
        import uuid
        command_id = str(uuid.uuid4())[:8]
        
        try:
            command_item = (command_id, cmd, subcmd, data, timeout, wait_response, False)
            self.command_queue.put(command_item, block=False)
            
            cmd_desc = RFProtocol.get_command_description(cmd, subcmd)
            return f"[QUEUE] {cmd_desc} 대기열 추가: {command_id}", None
            
        except queue.Full:
            error_msg = "[ERROR] 명령어 대기열이 가득 참"
            self.write_log(error_msg)
            return error_msg, None

    def send_batch_commands(self, commands_list, callback=None):
        """배치 명령어 전송"""
        if not commands_list:
            return False, "전송할 명령어가 없습니다"
        
        self.batch_tracker = BatchCommandTracker(len(commands_list), callback)
        
        success_count = 0
        for i, command_info in enumerate(commands_list):
            cmd = command_info['cmd']
            subcmd = command_info['subcmd'] 
            data = command_info.get('data')
            timeout = command_info.get('timeout', 10.0)
            wait_response = command_info.get('wait_response', True)
            
            send_msg, _ = self._queue_command_async(cmd, subcmd, data, timeout, wait_response)
            
            if "[ERROR]" not in send_msg:
                success_count += 1
            
            time.sleep(0.005)
        
        return True, f"{success_count}/{len(commands_list)}개 명령어가 대기열에 추가되었습니다"

    def pause_status_polling(self):
        """상태조회 일시 중단"""
        self.is_status_paused = True

    def resume_status_polling(self):
        """상태조회 재개"""
        self.is_status_paused = False

    def _reconnect_status(self):
        """상태조회 소켓 재연결"""
        if self.connection_attempts < RECONNECT_MAX_ATTEMPTS:
            self.connection_attempts += 1
            try:
                self.status_socket = self._create_socket()
                self.status_socket.connect((self.host, self.port))
                self.connection_established.emit()
                self.connection_attempts = 0
                
            except (socket.timeout, ConnectionRefusedError, socket.error) as e:
                self._close_status_socket()
                time.sleep(RECONNECT_BASE_DELAY * (2 ** min(self.connection_attempts, 5)))
        else:
            failure_msg = "상태조회 최대 연결 시도 횟수 초과"
            self.connection_failed.emit(failure_msg)
            self.write_log(f"[ERROR] {failure_msg}")
    
    def _close_status_socket(self):
        """상태조회 소켓 종료"""
        if self.status_socket:
            try:
                self.status_socket.close()
            except:
                pass
            self.status_socket = None

    def stop(self):
        """스레드 정지"""
        if getattr(self, 'cleanup_completed', False):
            return
            
        try:
            self.write_log("[INFO] RF 클라이언트 정리 시작...")
            
            self.running = False
            
            try:
                self.command_queue.put(None, timeout=1.0)
            except:
                pass
            
            self._force_close_status_socket()
            
            if self.isRunning():
                self.wait(3000)
                if self.isRunning():
                    self.terminate()
                    self.wait(1000)
            
            self.cleanup_completed = True
            self.write_log("[INFO] RF 클라이언트 정리 완료")
            
        except Exception as e:
            try:
                self.write_log(f"[WARNING] RF 클라이언트 정리 중 오류: {e}")
            except:
                print(f"[RF_CLIENT] 정리 중 오류: {e}")
            self.cleanup_completed = True

    def _force_close_status_socket(self):
        """상태조회 소켓 강제 종료"""
        if self.status_socket:
            try:
                try:
                    self.status_socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                
                self.status_socket.close()
                time.sleep(0.1)
                
            except Exception as e:
                pass
            finally:
                self.status_socket = None

    def write_log(self, message, color="white"):
        """
        로그를 MainWindow의 log_manager로 전달 (스레드 안전)
        """
        try:
            # 🚨 self.parent에 접근하는 모든 로직을 이 try 블록 안에 넣습니다.
            if (self.parent and 
                hasattr(self.parent, 'log_manager') and 
                self.parent.log_manager and
                hasattr(self.parent.log_manager, 'write_log')):
                
                # --- 기존의 로그 출력 로직 (타입별) ---
                if "[SEND]" in message:
                    self.parent.log_manager.write_log(message, "cyan")
                elif "[RECV]" in message:
                    if "상태 데이터 수신" in message:
                        self.parent.log_manager.write_log(message, "gray")
                    else:
                        self.parent.log_manager.write_log(message, "magenta")
                elif "[ERROR]" in message or "[CRITICAL]" in message:
                    self.parent.log_manager.write_log(message, "red")
                elif "[WARNING]" in message:
                    self.parent.log_manager.write_log(message, "yellow")
                elif "[SUCCESS]" in message or "[INFO]" in message:
                    self.parent.log_manager.write_log(message, "cyan")
                else:
                    self.parent.log_manager.write_log(message, color)
                # ------------------------------------
            else:
                # self.parent가 없거나 로그 관리자가 없는 경우
                print(f"[RF_CLIENT] {message}")
                
        except RuntimeError as e:
            # 🚨 wrapped C/C++ object has been deleted 오류 포착 (최종 방어)
            if "deleted" in str(e) or "destroyed" in str(e):
                print(f"[RF_CLIENT] 로그 출력 실패: wrapped C/C++ object of type MainWindow has been deleted (처리됨)")
                print(f"[RF_CLIENT] {message}")
                return # 안전하게 종료
            raise e # 다른 RuntimeError는 다시 발생시킵니다.
        
        except Exception as e:
            # 기타 예상치 못한 예외 처리
            print(f"[RF_CLIENT] 로그 출력 실패: {e}")
            print(f"[RF_CLIENT] {message}")

# 기존 호환성을 위한 별칭
RFClientThread = HybridRFClientThread