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

# 상수 설정
RECONNECT_MAX_ATTEMPTS = 10
RECONNECT_BASE_DELAY = 1.0
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
    # HF와 다름: Pulse 명령어 구조 완전 변경
    CMD_PULSE_SET = 0x02
    SUBCMD_PULSE_MODE_SET = 0x03  # 수정: 0x02 -> 0x03
    SUBCMD_PULSE_PARAMS_SET = 0x05  # 신규: pulse time parameters (33byte)
    
    CMD_PULSE_GET = 0x82
    SUBCMD_PULSE_MODE_GET = 0x03
    SUBCMD_PULSE_PARAMS_GET = 0x05
    
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
    # HF와 동일
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
    # HF와 동일
    CMD_CEX_CONFIG_SET = 0x01
    SUBCMD_CEX_CONFIG_SET = 0x0C
    CMD_CEX_CONFIG_GET = 0x81
    SUBCMD_CEX_CONFIG_GET = 0x0C
    
    # ========================================
    # === 알람 클리어 (CMD=0x04) ===
    # ========================================
    # HF와 동일
    CMD_ALARM_CLEAR = 0x04
    SUBCMD_ALARM_CLEAR = 0x15
    
    # ========================================
    # === Bank Function (RF On trigger & Timed RF off) ===
    # === (CMD=0x19/0x99, Page 34-44) ===
    # === HF에 없음: 완전 신규 추가 ===
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
    # SUBCMD는 SET과 동일 (0x01~0x0A)
    
    # ========================================
    # === 네트워크 설정 (Page 44-45) ===
    # === HF와 다름: CMD 값 수정 ===
    # ========================================
    
    # MAC Address 조회
    CMD_NETWORK_MAC_GET = 0x97
    SUBCMD_NETWORK_MAC_GET = 0x00
    
    # TCP/IP 설정 - 수정: 0x15 -> 0x11
    CMD_NETWORK_TCPIP_SET = 0x11
    SUBCMD_NETWORK_TCPIP_SET = 0x00
    
    # TCP/IP 조회 - 수정: 0x95 -> 0x91, SUBCMD: 0x01 -> 0x00
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
        """수신된 데이터 파싱 - Developer 명령어 대응"""
        # 최소 길이 및 헤더/트레일러 검증
        if len(data) < 6:
            print(f"[parse_response] 길이 부족: {len(data)}")
            return None
        if data[0] != RFProtocol._SOM_ or data[1] != RFProtocol._SOM_:
            print(f"[parse_response] SOM 오류")
            return None
        if data[-1] != RFProtocol._EOM_:
            print(f"[parse_response] EOM 오류")
            return None
        
        # 헤더 파싱
        di = data[2]
        cmd = data[3]
        data_no = data[4]
        
        # SUBCMD 추출
        subcmd = data[5] if data_no > 0 else None
        
        # ✅ 핵심: 데이터는 항상 인덱스 6부터
        if data_no > 1:
            data_body = data[6:-2]
        else:
            data_body = b''
        
        # Checksum 검증
        checksum = data[-2]
        calc_cs = sum(data[2:-2]) & 0xFF
        if calc_cs != checksum:
            print(f"[parse_response] Checksum 오류: calc={calc_cs:02X}, recv={checksum:02X}")
            return None
        
        # 디버그 출력 - 조건식 미리 계산
        subcmd_str = f"0x{subcmd:02X}" if subcmd is not None else "None"
        #print(f"[parse_response] CMD=0x{cmd:02X}, SUBCMD={subcmd_str}, data_len={len(data_body)}")
        
        return {
            "di": di,
            "cmd": cmd,
            "subcmd": subcmd,
            "data": data_body
        }

    @staticmethod
    def validate_command_data(cmd, subcmd, data):
        """명령어 데이터 유효성 검사 - VHF 매뉴얼 전체 반영"""
        if not isinstance(cmd, int) or not isinstance(subcmd, int):
            return False, "명령어는 정수여야 합니다"
        
        if cmd < 0 or cmd > 255 or subcmd < 0 or subcmd > 255:
            return False, "명령어는 0-255 범위여야 합니다"
        
        # 데이터 길이 검사 (VHF 매뉴얼 기준)
        data_len = len(data) if data else 0
        
        expected_lengths = {
            # === 기본 명령어 ===
            # RF On/Off: 데이터 없음
            (RFProtocol.CMD_RF_ON, RFProtocol.SUBCMD_RF_ON): 0,
            (RFProtocol.CMD_RF_OFF, RFProtocol.SUBCMD_RF_OFF): 0,
            
            # === 파워 설정 ===
            # Set Power: 5바이트 (1byte subcmd + 4byte float)
            (RFProtocol.CMD_SET_POWER, RFProtocol.SUBCMD_SET_POWER): 4,
            # Get Power: 데이터 없음
            (RFProtocol.CMD_GET_POWER, RFProtocol.SUBCMD_GET_POWER): 0,
            
            # === 제어 모드 ===
            # Set Control Mode: 2바이트 (uint16)
            (RFProtocol.CMD_CONTROL_MODE_SET, RFProtocol.SUBCMD_CONTROL_MODE_SET): 2,
            # Get Control Mode: 데이터 없음
            (RFProtocol.CMD_CONTROL_MODE_GET, RFProtocol.SUBCMD_CONTROL_MODE_GET): 0,
            
            # === 조절 모드 ===
            # Set Regulation Mode: 2바이트 (uint16)
            (RFProtocol.CMD_REGULATION_MODE_SET, RFProtocol.SUBCMD_REGULATION_MODE_SET): 2,
            # Get Regulation Mode: 데이터 없음
            (RFProtocol.CMD_REGULATION_MODE_GET, RFProtocol.SUBCMD_REGULATION_MODE_GET): 0,
            
            # === 램프 설정 ===
            # Set Ramp: 20바이트 (uint32 enable + float start + uint32*3 times)
            (RFProtocol.CMD_RAMP_CONFIG_SET, RFProtocol.SUBCMD_RAMP_CONFIG_SET): 20,
            # Get Ramp: 데이터 없음
            (RFProtocol.CMD_RAMP_CONFIG_GET, RFProtocol.SUBCMD_RAMP_CONFIG_GET): 0,
            
            # === VHF 매뉴얼 기준 Pulse Configuration (CMD=0x02/0x82) ===
            # Set Pulse Mode: 1바이트 (0=off, 1=pulse0, 2=pulse0+1, 3=pulse0+1+2)
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_MODE_SET): 1,
            # Set Pulse Parameters: 33바이트 (pulse0/1/2 on/off/repeat times)
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_PARAMS_SET): 33,
            # Get Pulse Mode: 데이터 없음
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_MODE_GET): 0,
            # Get Pulse Parameters: 데이터 없음
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_PARAMS_GET): 0,
            
            # === CEX 설정 ===
            # Set CEX: 12바이트 (uint16 enable + uint16 mode + float*2 phase)
            (RFProtocol.CMD_CEX_CONFIG_SET, RFProtocol.SUBCMD_CEX_CONFIG_SET): 12,
            # Get CEX: 데이터 없음
            (RFProtocol.CMD_CEX_CONFIG_GET, RFProtocol.SUBCMD_CEX_CONFIG_GET): 0,
            
            # === RF 주파수 ===
            # Set RF Frequency: 4바이트 (uint32, Hz)
            (RFProtocol.CMD_SET_FREQUENCY, RFProtocol.SUBCMD_SET_FREQUENCY): 4,
            # Get RF Frequency: 4바이트 (uint32, Hz) - GET도 4바이트 반환
            (RFProtocol.CMD_GET_FREQUENCY, RFProtocol.SUBCMD_GET_FREQUENCY): 0,
            
            # === 주파수 튜닝 (CMD=0x04/0x84) ===
            # Set Frequency Tuning Enable: 1바이트 (0=disable, 1=enable)
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_ENABLE): 1,
            # Set Retuning Mode: 1바이트 (0=one-time, 1=continuous)
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_RETUNING): 2,
            # Set Tuning Mode: 1바이트 (0=fixed, 1=preset, 2=auto)
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MODE): 2,
            # Set Min/Max/Start Frequency: 4바이트 (uint32, Hz)
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MIN_FREQ): 4,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MAX_FREQ): 4,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_START_FREQ): 4,
            # Set Min/Max Step: 4바이트 (uint32, Hz)
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MIN_STEP): 4,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_MAX_STEP): 4,
            # Set Stop/Return Gamma: 4바이트 (float)
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_STOP_GAMMA): 4,
            (RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.SUBCMD_FREQ_TUNING_RETURN_GAMMA): 4,
            
            # === Bank Function (CMD=0x19/0x99) - VHF 매뉴얼 Page 34-44 ===
            # Bank1 Functions
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_ENABLE): 4,  # uint32
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_EQUATION_ENABLE): 4,  # uint32
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_RESTART): 4,  # uint32
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_RF_TRIGGER): 4,  # uint32
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK1_PARAMS): 20,  # 5*float (X0,A,B,C,D)
            # Bank2 Functions
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_ENABLE): 4,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_EQUATION_ENABLE): 4,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_RESTART): 4,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_RF_TRIGGER): 4,
            (RFProtocol.CMD_BANK_SET, RFProtocol.SUBCMD_BANK2_PARAMS): 20,
            # Bank GET Commands: 데이터 없음
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
            # Clear Alarm: 2바이트 (uint16, 1=clear)
            (RFProtocol.CMD_ALARM_CLEAR, RFProtocol.SUBCMD_ALARM_CLEAR): 2,
            
            # === 네트워크 설정 (CMD 수정됨: 0x11/0x91) ===
            # Get MAC Address: 데이터 없음
            (RFProtocol.CMD_NETWORK_MAC_GET, RFProtocol.SUBCMD_NETWORK_MAC_GET): 0,
            # Set TCP/IP: 20바이트 (4*uint32 IP+Mask+Gateway+DNS + 4*uint16 Options)
            (RFProtocol.CMD_NETWORK_TCPIP_SET, RFProtocol.SUBCMD_NETWORK_TCPIP_SET): 20,
            # Get TCP/IP: 데이터 없음
            (RFProtocol.CMD_NETWORK_TCPIP_GET, RFProtocol.SUBCMD_NETWORK_TCPIP_GET): 0,
            
            # Calibration Tables
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
            # Get Device Status: 데이터 없음 (응답은 56바이트)
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
            
            # === VHF Pulse 명령어 ===
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_MODE_SET): "펄스 모드 설정",
            (RFProtocol.CMD_PULSE_SET, RFProtocol.SUBCMD_PULSE_PARAMS_SET): "펄스 파라미터 설정",
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_MODE_GET): "펄스 모드 조회",
            (RFProtocol.CMD_PULSE_GET, RFProtocol.SUBCMD_PULSE_PARAMS_GET): "펄스 파라미터 조회",
            
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
            
            # === Bank Function (신규) ===
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
            
            # Developer Commands
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
            
            # Calibration Tables
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
        
        # 모든 명령어 완료 시 결과 처리
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
    command_completed = pyqtSignal(str, bool, str)  # command_id, success, message
    batch_completed = pyqtSignal(dict)  # 배치 처리 완료

    def __init__(self, host="127.0.0.1", port=5000):
        super().__init__()
        self.host = host
        self.port = port
        self.running = True
        
        # 소켓 관리
        self.status_socket = None
        self.command_queue = queue.Queue(maxsize=50)
        
        # 동기화
        self.status_lock = threading.RLock()
        self.command_lock = threading.RLock()
        
        # 상태 관리
        self.connection_attempts = 0
        self.frame_count = 0
        self.is_status_paused = False
        self.parent = None
        
        
        # 배치 처리 추적
        self.batch_tracker = None
        
        ##        
        # **핵심 추가**: 정리 상태 추적
        self.cleanup_completed = False
        
        # **추가**: 연결 상태 로그 제어
        self.connection_state = "unknown"  # "connected", "disconnected", "unknown"
        
        # **핵심 추가**: atexit 핸들러 등록
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
        """비상 정리 - 프로그램 종료 시 강제 호출"""
        if not getattr(self, 'cleanup_completed', False):
            try:
                self.stop()
                time.sleep(0.5)  # 정리 시간 확보
            except Exception as e:
                # 비상 정리에서는 print만 사용
                print(f"[RF_CLIENT] 비상 정리 오류: {e}")
        ##

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

    ##
    def _create_socket(self):
        """소켓 생성 - Windows 최적화"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Windows 전용: 연결 종료 시 즉시 정리
        if hasattr(socket, 'SO_LINGER'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
    
        return sock

    ##
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
                            
                            # 상태 조회 명령어인지 확인
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
        """메인 스레드 - 상태조회 전용"""
        command_worker = threading.Thread(target=self._command_worker, daemon=True)
        command_worker.start()
        
        while self.running:
            if not self.status_socket or self.status_socket.fileno() == -1:
                # **수정**: 연결 상태 설정 추가
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
                                # **수정**: 연결 상태 설정 추가
                                self._set_connection_state("connected")
                                
                                if hasattr(self.parent, 'show_status_logs') and self.parent.show_status_logs:
                                    self.write_log(log_msg)
                                
                                self.data_received.emit(received_data, timestamp)
                                self.connection_attempts = 0
                            else:
                                # **수정**: 연결 상태 설정 추가
                                self._set_connection_state("disconnected")
                                
                                self.data_received.emit(b"", timestamp)
                                if "타임아웃" in log_msg or "파싱 실패" in log_msg:
                                    self.write_log(log_msg)
                                    
                except (socket.timeout, socket.error) as e:
                    # **수정**: 연결 상태 설정 추가
                    self._set_connection_state("disconnected")
                    
                    self.data_received.emit(b"", time.time())
                    if isinstance(e, socket.error) and hasattr(e, 'errno') and e.errno == 10054:
                        self._close_status_socket()
                        # **삭제**: 기존 중복 로그 출력 제거
                        # self.write_log(f"[WARNING] 상태조회 연결 재설정: {e}")
                
                time.sleep(0.05)

    def _command_worker(self):
        """명령어 처리 워커 스레드"""
        while self.running:
            try:
                command_item = self.command_queue.get(timeout=1.0)
                
                if command_item is None:
                    break
                
                command_id, cmd, subcmd, data, timeout, wait_response, is_sync = command_item
                
                # 명령어 실행
                result = self._execute_command(cmd, subcmd, data, timeout, wait_response)
                
                # 동기 모드인 경우 결과를 command_id에 저장 (별도 처리)
                if is_sync:
                    # 동기 결과는 별도 메커니즘으로 처리 (큐나 이벤트)
                    pass
                else:
                    # 비동기 모드: 시그널 발생
                    self.command_completed.emit(command_id, result.success, result.message)
                    
                    # 배치 추적 업데이트
                    if self.batch_tracker:
                        self.batch_tracker.on_command_completed(command_id, result.success, result.message)
                
                self.command_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.write_log(f"[ERROR] 명령어 워커 오류: {e}")

    ##
    def _execute_command(self, cmd, subcmd, data, timeout, wait_response):
        """단일 명령어 실행 - 로그 개선"""
        command_socket = None
        start_time = time.time()
        
        try:
            with self.command_lock:
                if not self.running:
                    return CommandResult(False, "클라이언트가 종료 중입니다", execution_time=time.time() - start_time)
                
                # 명령어 전용 소켓 생성
                command_socket = self._create_optimized_socket()
                command_socket.settimeout(timeout)
                
                try:
                    command_socket.connect((self.host, self.port))
                except Exception as connect_error:
                    return CommandResult(False, f"연결 실패: {connect_error}", execution_time=time.time() - start_time)
                
                # 명령어 설명 및 프레임 생성
                cmd_desc = RFProtocol.get_command_description(cmd, subcmd)
                frame = RFProtocol.create_frame(cmd, subcmd, data)
                
                # 프레임 전송
                command_socket.sendall(frame)
                
                if wait_response:
                    # 응답 수신
                    received_data, _, recv_log_msg = self._receive_full_frame(command_socket, timeout)
                    
                    if received_data:
                        # 응답 로그 출력 (RF On/Off, Set Power는 항상 로그 출력)
                        # 응답 로그 출력 - 모든 설정 명령어에 대해 출력
                        if cmd in [RFProtocol.CMD_RF_ON, RFProtocol.CMD_RF_OFF, RFProtocol.CMD_SET_POWER,
                                   RFProtocol.CMD_CONTROL_MODE_SET, RFProtocol.CMD_REGULATION_MODE_SET,
                                   RFProtocol.CMD_RAMP_CONFIG_SET, RFProtocol.CMD_CEX_CONFIG_SET,
                                   RFProtocol.CMD_PULSE_SET, RFProtocol.CMD_SET_FREQUENCY,
                                   RFProtocol.CMD_FREQUENCY_TUNING, RFProtocol.CMD_BANK_SET,
                                   # Developer Commands
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
            # 소켓 정리
            if command_socket:
                try:
                    command_socket.shutdown(socket.SHUT_RDWR)
                    command_socket.close()
                except:
                    pass
         
    def _create_optimized_socket(self):
        """최적화된 소켓 생성"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # 최적화된 소켓 옵션
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # 빠른 연결을 위한 버퍼 크기 조정
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        
        # 즉시 종료 설정
        if hasattr(socket, 'SO_LINGER'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
        
        return sock
            
    def _create_send_log(self, cmd_desc, cmd, subcmd, data, frame):
        """전송 로그 생성 - RF 명령어에 특화"""
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
            
            # GET 명령어 확인 (CMD >= 0x80)
            if cmd >= 0x80:
                # GET 명령어: 응답 데이터에 에러 코드 없음, 전체가 실제 데이터
                return CommandResult(
                    success=True,
                    message=f"{cmd_desc} 성공",
                    response_data=received_data,
                    error_code=0,
                    execution_time=execution_time
                )
            
            # SET 명령어: 첫 바이트가 에러 코드
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
    ##

    def send_command(self, cmd, subcmd, data=None, wait_response=True, timeout=10.0, sync=False):
        """단순화된 명령어 전송 - 탭별 적용에서는 sync=True 사용"""
        
        # 명령어 유효성 검사
        is_valid, msg = RFProtocol.validate_command_data(cmd, subcmd, data)
        if not is_valid:
            if sync:
                return CommandResult(False, f"명령어 검증 실패: {msg}")
            else:
                error_msg = f"[ERROR] 명령어 검증 실패: {msg}"
                self.write_log(error_msg)
                return error_msg, None
        
        if sync:
            # 동기 모드: 즉시 실행하고 결과 반환
            return self._execute_command_sync(cmd, subcmd, data, timeout, wait_response)
        else:
            # 비동기 모드: 대기열에 추가
            return self._queue_command_async(cmd, subcmd, data, timeout, wait_response)
    
    def _execute_command_sync(self, cmd, subcmd, data, timeout, wait_response) -> CommandResult:
        """동기 명령어 실행 - 로깅 개선"""
        try:
            # 상태조회 일시 중단
            self.pause_status_polling()
            
            # 명령어 설명 및 로그 출력
            cmd_desc = RFProtocol.get_command_description(cmd, subcmd)
            frame = RFProtocol.create_frame(cmd, subcmd, data)
            
            # 전송 로그 생성 및 출력
            send_log = self._create_send_log(cmd_desc, cmd, subcmd, data, frame)
            self.write_log(send_log, "cyan")
            
            # 직접 실행
            result = self._execute_command(cmd, subcmd, data, timeout, wait_response)
            
            # 결과 로그 출력
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
            # 상태조회 재개
            self.resume_status_polling()
    
    def _queue_command_async(self, cmd, subcmd, data, timeout, wait_response):
        """비동기 명령어 대기열 추가"""
        import uuid
        command_id = str(uuid.uuid4())[:8]
        
        try:
            # 명령어를 대기열에 추가
            command_item = (command_id, cmd, subcmd, data, timeout, wait_response, False)  # False = 비동기
            self.command_queue.put(command_item, block=False)
            
            cmd_desc = RFProtocol.get_command_description(cmd, subcmd)
            return f"[QUEUE] {cmd_desc} 대기열 추가: {command_id}", None
            
        except queue.Full:
            error_msg = "[ERROR] 명령어 대기열이 가득 참"
            self.write_log(error_msg)
            return error_msg, None

    def send_batch_commands(self, commands_list, callback=None):
        """배치 명령어 전송 - 결과 추적 포함"""
        if not commands_list:
            return False, "전송할 명령어가 없습니다"
        
        # 배치 추적기 생성
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
            
            # 대기열 포화 방지
            time.sleep(0.1)
        
        return True, f"{success_count}/{len(commands_list)}개 명령어가 대기열에 추가되었습니다"

    def pause_status_polling(self):
        """상태조회 일시 중단"""
        self.is_status_paused = True

    def resume_status_polling(self):
        """상태조회 재개"""
        self.is_status_paused = False

    ##
    def _reconnect_status(self):
        """상태조회 소켓 재연결 - 안전한 로그 호출"""
        if self.connection_attempts < RECONNECT_MAX_ATTEMPTS:
            self.connection_attempts += 1
            try:
                self.status_socket = self._create_socket()
                self.status_socket.connect((self.host, self.port))
                self.connection_established.emit()
                self.connection_attempts = 0
                
                # **수정**: 개별 성공 로그 대신 상태 변경으로 처리
                # self.write_log(f"[INFO] 상태조회 소켓 연결 성공: {self.host}:{self.port}")
                
            except (socket.timeout, ConnectionRefusedError, socket.error) as e:
                self._close_status_socket()
                
                # **삭제**: 개별 재연결 시도 로그 제거 (너무 많이 출력됨)
                # self.write_log(f"[WARNING] 상태조회 연결 시도 {self.connection_attempts}/{RECONNECT_MAX_ATTEMPTS} 실패: {e}")
                
                time.sleep(RECONNECT_BASE_DELAY * (2 ** min(self.connection_attempts, 5)))
        else:
            failure_msg = "상태조회 최대 연결 시도 횟수 초과"
            self.connection_failed.emit(failure_msg)
            # **유지**: 최대 시도 초과는 중요하므로 로그 유지
            self.write_log(f"[ERROR] {failure_msg}")
    ##
    def _close_status_socket(self):
        """상태조회 소켓 종료"""
        if self.status_socket:
            try:
                self.status_socket.close()
            except:
                pass
            self.status_socket = None

    ##
    def stop(self):
        """스레드 정지 - 안전한 로그 호출"""
        if getattr(self, 'cleanup_completed', False):
            return
            
        try:
            self.write_log("[INFO] RF 클라이언트 정리 시작...")  # 색상 인자 제거
            
            # 1. 실행 상태 변경
            self.running = False
            
            # 2. 명령어 워커 종료 신호
            try:
                self.command_queue.put(None, timeout=1.0)
            except:
                pass
            
            # 3. 상태조회 소켓 정리 (강제)
            self._force_close_status_socket()
            
            # 4. 스레드 대기 (타임아웃 포함)
            if self.isRunning():
                self.wait(3000)  # 3초 대기
                if self.isRunning():
                    self.terminate()  # 강제 종료
                    self.wait(1000)   # 1초 더 대기
            
            # 5. 정리 완료 표시
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
                # 1. 소켓 셧다운
                try:
                    self.status_socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                
                # 2. 소켓 종료
                self.status_socket.close()
                
                # 3. 짧은 대기로 OS가 정리하도록 함
                time.sleep(0.1)
                
            except Exception as e:
                # 에러는 로그만 남기고 계속 진행
                pass
            finally:
                self.status_socket = None
    ##

    def write_log(self, message, color="white"):
        """로그 메시지 출력 - 안전한 로그 호출"""
        try:
            # parent와 log_manager가 제대로 연결되어 있는지 확인
            if (hasattr(self, 'parent') and 
                self.parent and 
                hasattr(self.parent, 'log_manager') and 
                self.parent.log_manager and
                hasattr(self.parent.log_manager, 'write_log')):
                
                # GUI 로그창에 출력
                if "[SEND]" in message:
                    self.parent.log_manager.write_log(message, "cyan")
                elif "[RECV]" in message:
                    if "상태 데이터 수신" in message:
                        self.parent.log_manager.write_log(message, "gray")
                    else:
                        self.parent.log_manager.write_log(message, "magenta")
                elif "[ERROR]" in message:
                    self.parent.log_manager.write_log(message, "red")
                elif "[WARNING]" in message:
                    self.parent.log_manager.write_log(message, "yellow")
                elif "[SUCCESS]" in message:
                    self.parent.log_manager.write_log(message, "green")
                elif "[INFO]" in message:
                    self.parent.log_manager.write_log(message, "cyan")
                elif "[CRITICAL]" in message:
                    self.parent.log_manager.write_log(message, "red")
                else:
                    self.parent.log_manager.write_log(message, color)
            else:
                # fallback - 연결이 안된 경우에만 print 사용
                print(f"[RF_CLIENT] {message}")
                
        except Exception as e:
            print(f"[RF_CLIENT] 로그 출력 실패: {e}")
            print(f"[RF_CLIENT] {message}")


# 기존 호환성을 위한 별칭
RFClientThread = HybridRFClientThread
