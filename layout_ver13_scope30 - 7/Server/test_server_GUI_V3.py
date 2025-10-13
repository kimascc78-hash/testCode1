import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import struct
import numpy as np
import threading
import time
import os
from collections import defaultdict
import queue
import json
from datetime import datetime
import random

# 설정
CONFIG_DIR = "data"
HOST = "0.0.0.0"
PORT = 5000
SOCKET_TIMEOUT = 5.0
MAX_CLIENTS = 10

class RFProtocol:
    _SOM_ = 0x16
    _EOM_ = 0x1A
    _DID_ = 0x00

    # 매뉴얼 기준 모든 명령어
    CMD_DEVICE_STATUS_GET = 0x10
    SUBCMD_DEVICE_STATUS = 0x01
    CMD_RF_ON = 0x00
    SUBCMD_RF_ON = 0x01
    CMD_RF_OFF = 0x00
    SUBCMD_RF_OFF = 0x02
    CMD_SET_POWER = 0x07
    SUBCMD_SET_POWER = 0x03
    CMD_CONTROL_MODE_SET = 0x07
    SUBCMD_CONTROL_MODE_SET = 0x01
    CMD_REGULATION_MODE_SET = 0x01
    SUBCMD_REGULATION_MODE_SET = 0x02
    CMD_RAMP_CONFIG_SET = 0x01
    SUBCMD_RAMP_CONFIG_SET = 0x0B
    CMD_CEX_CONFIG_SET = 0x01
    SUBCMD_CEX_CONFIG_SET = 0x0C
    CMD_PULSING = 0x02
    SUBCMD_PULSE_MODE = 0x02
    SUBCMD_PULSE_ONOFF = 0x03
    SUBCMD_PULSE_DUTY = 0x06
    SUBCMD_PULSE_OUTPUT_SYNC = 0x07
    SUBCMD_PULSE_INPUT_SYNC = 0x08
    SUBCMD_PULSE_FREQUENCY = 0x09
    CMD_SET_FREQUENCY = 0x04
    SUBCMD_SET_FREQUENCY = 0x09
    CMD_CLEAR_ALARM = 0x04
    SUBCMD_CLEAR_ALARM = 0x15
    
    # 주파수 튜닝 명령어 추가
    CMD_FREQUENCY_TUNING = 0x04
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

    @staticmethod
    def create_frame(cmd, subcmd, data=None):
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
    def parse_frame(data):
        if len(data) < 6 or data[0] != RFProtocol._SOM_ or data[1] != RFProtocol._SOM_ or data[-1] != RFProtocol._EOM_:
            return None
        di, cmd, data_no = data[2], data[3], data[4]
        subcmd = data[5] if data_no > 0 else None
        start_idx = 6 if subcmd else 5
        data_body = data[start_idx:-2] if data_no > (1 if subcmd else 0) else b''
        if len(data_body) != (data_no - 1 if subcmd else data_no):
            return None
        checksum = data[-2]
        calc_cs = sum(data[2:-2]) & 0xFF
        if calc_cs != checksum:
            return None
        return {"di": di, "cmd": cmd, "subcmd": subcmd, "data": data_body}

class RealisticTestScenarioManager:
    """현실적인 RF 시스템 시뮬레이션 - 노이즈와 물리적 특성 반영"""
    
    def __init__(self):
        self.current_scenario = 0
        self.test_mode = "realistic"  # "sine_wave" 또는 "realistic"
        
        # 개별 노이즈 레벨 초기화
        self.white_noise_level = 0.01  # 1%
        self.pink_noise_level = 0.005  # 0.5%
        self.spike_noise_level = 0.02  # 2%
        self.spike_probability = 0.0001  # 0.01%
        
        # 실제 시스템 특성 파라미터
        self.system_params = {
            "power_regulation_time_constant": 0.1,  # 파워 제어 시간상수 (초)
            "matching_response_time": 0.5,  # 매칭 네트워크 응답시간
            "thermal_time_constant": 30.0,  # 열적 시간상수
            "arc_recovery_time": 2.0,  # 아크 복구 시간
        }
        
        self.scenarios = [
            self.normal_operation,
            self.power_ramp_test,
            self.plasma_ignition_test,
            self.matching_network_aging,
            self.arc_event_simulation,
            self.thermal_cycling_test,
            self.process_recipe_etch,
            self.process_recipe_depo,
            self.impedance_load_variation,
            self.power_supply_ripple_test,
            self.chamber_conditioning,
            self.maintenance_mode_test
        ]
        
        # 내부 상태 변수들
        self.last_values = {}
        self.internal_states = {}
    
    def set_test_mode(self, mode, white_noise=0.01, pink_noise=0.01, spike_noise=0.01, spike_probability=0.0001):
        """테스트 모드 설정 - 개별 노이즈 제어"""
        self.test_mode = mode
        self.white_noise_level = white_noise / 100.0  # % to decimal
        self.pink_noise_level = pink_noise / 100.0
        self.spike_noise_level = spike_noise / 100.0
        self.spike_probability = spike_probability / 100.0  # % to decimal
        
    def get_scenario_names(self):
        """시나리오 이름 목록 반환"""
        return [
            "정상 운영",
            "파워 램프 테스트",
            "플라즈마 점화 과정",
            "매칭 네트워크 에이징",
            "아크 이벤트 시뮬레이션",
            "열순환 테스트",
            "에칭 공정 (펄스)",
            "증착 공정 (CW)",
            "부하 임피던스 변동",
            "전원 리플 테스트",
            "챔버 컨디셔닝",
            "정비 모드"
        ]
    
    def add_realistic_noise(self, base_value, white_factor=None, pink_factor=None, spike_factor=None):
        """현실적인 노이즈 추가 - 개별 노이즈 제어"""
        if white_factor is None:
            white_factor = self.white_noise_level
        if pink_factor is None:
            pink_factor = self.pink_noise_level
        if spike_factor is None:
            spike_factor = self.spike_noise_level
            
        if self.test_mode == "sine_wave":
            return base_value
            
        # 화이트 노이즈 (고주파)
        white_noise = np.random.normal(0, white_factor * 0.1) if white_factor > 0 else 0
        
        # 1/f 노이즈 (저주파 drift)
        pink_noise = 0
        if pink_factor > 0:
            if not hasattr(self, '_pink_noise_state'):
                self._pink_noise_state = 0
            self._pink_noise_state = 0.95 * self._pink_noise_state + 0.05 * np.random.normal(0, pink_factor * 0.1)
            pink_noise = self._pink_noise_state
        
        # 간헐적 스파이크
        spike_noise = 0
        if spike_factor > 0 and np.random.random() < self.spike_probability:
            spike_noise = np.random.normal(0, spike_factor * 1.5)
            
        total_noise = white_noise + pink_noise + spike_noise
        return base_value * (1 + total_noise)
    
    def exponential_approach(self, current, target, time_constant, dt=0.1):
        """지수적 접근 (1차 시스템 응답)"""
        alpha = 1 - np.exp(-dt / time_constant)
        return current + alpha * (target - current)
    
    def get_current_scenario_data(self, base_status, current_time, client_state):
        """현재 시나리오에 따른 현실적인 테스트 데이터 생성"""
        scenario_func = self.scenarios[self.current_scenario % len(self.scenarios)]
        return scenario_func(base_status, current_time, client_state)
    
    def normal_operation(self, status, t, client_state):
        """정상 운영 - 안정적이지만 현실적인 변동"""
        client_key = id(client_state)
        
        if not client_state["rf_enabled"]:
            status["forward_power"] = 0.0
            status["reflect_power"] = 0.0
        else:
            set_power = client_state.get("set_power", 0)
            if set_power > 0:
                if self.test_mode == "sine_wave":
                    # 사인파 모드: 수학적 변동
                    power_variation = 0.05 * np.sin(2 * np.pi * 0.1 * t)  # ±5% 사인파
                    status["forward_power"] = set_power * (1.0 + power_variation)
                    status["reflect_power"] = status["forward_power"] * (0.02 + 0.03 * np.sin(2 * np.pi * 0.3 * t))
                else:
                    # 현실적 모드
                    # 노이즈가 모두 0이면 완전히 고정된 값 출력
                    if (self.white_noise_level == 0 and 
                        self.pink_noise_level == 0 and 
                        self.spike_noise_level == 0):
                        # 노이즈 완전 비활성화: 정확히 설정값 출력
                        status["forward_power"] = float(set_power)
                        status["reflect_power"] = float(set_power) * 0.03  # 고정 3% reflect
                    else:
                        # 노이즈 활성화: 파워 제어 루프 + 노이즈
                        if client_key not in self.last_values:
                            self.last_values[client_key] = {"forward_power": float(set_power)}
                        
                        current_power = self.last_values[client_key]["forward_power"]
                        
                        # 1차 시스템 응답으로 파워 제어 (목표값에 수렴)
                        regulated_power = self.exponential_approach(
                            current_power, float(set_power), 
                            self.system_params["power_regulation_time_constant"]
                        )
                        
                        # 현실적인 노이즈 추가 (기본 팩터 사용)
                        status["forward_power"] = self.add_realistic_noise(regulated_power)
                        
                        # Reflect power (매칭 네트워크 특성)
                        base_reflect_ratio = 0.02 + 0.01 * np.random.random()  # 2-3% 기본
                        status["reflect_power"] = self.add_realistic_noise(
                            status["forward_power"] * base_reflect_ratio
                        )
                        
                        self.last_values[client_key]["forward_power"] = regulated_power
            else:
                status["forward_power"] = 0.0
                status["reflect_power"] = 0.0
        
        # 온도 - 열적 시간상수 고려
        base_temp = 35 + (status["forward_power"] / 50)  # 파워에 비례한 온도 상승
        if self.test_mode == "sine_wave":
            status["temperature"] = base_temp + 5 * np.sin(2 * np.pi * 0.1 * t)
        else:
            if (self.white_noise_level == 0 and 
                self.pink_noise_level == 0 and 
                self.spike_noise_level == 0):
                status["temperature"] = base_temp  # 고정값
            else:
                status["temperature"] = self.add_realistic_noise(base_temp, 0, 0, 0.1)
        
        status["led_state"] = 0x0021 if client_state["rf_enabled"] else 0x0001
        status["alarm_state"] = 0x0000
        return "정상 운영 (" + ("사인파" if self.test_mode == "sine_wave" else ("고정값" if self.white_noise_level == 0 and self.pink_noise_level == 0 and self.spike_noise_level == 0 else "현실적 노이즈")) + ")"
    
    def power_ramp_test(self, status, t, client_state):
        """파워 램프 테스트 - 실제 제어 루프 동작"""
        client_key = id(client_state)
        
        if not client_state["rf_enabled"]:
            status["forward_power"] = 0.0
            status["reflect_power"] = 0.0
        else:
            set_power = client_state.get("set_power", 0)
            if set_power > 0:
                # 램프 프로파일 (20초에 걸쳐 점진적 증가)
                ramp_time = 20.0
                progress = min((t % 30) / ramp_time, 1.0)
                
                # S-curve 램프 (부드러운 가속/감속)
                if progress < 0.5:
                    s_curve_progress = 2 * progress * progress
                else:
                    s_curve_progress = 1 - 2 * (1 - progress) * (1 - progress)
                
                target_power = set_power * s_curve_progress
                
                # 제어 루프 지연과 오버슛
                if client_key not in self.last_values:
                    self.last_values[client_key] = {"forward_power": 0.0, "control_error": 0.0}
                
                current_power = self.last_values[client_key]["forward_power"]
                control_error = self.last_values[client_key]["control_error"]
                
                # PID 제어 시뮬레이션 (단순화)
                error = target_power - current_power
                control_output = target_power + 0.1 * error + 0.05 * control_error
                
                # 1차 지연으로 실제 파워 응답
                if self.test_mode == "sine_wave":
                    overshoot = 1.0 + 0.1 * np.sin(2 * np.pi * 2 * t) if progress < 0.9 else 1.0
                    status["forward_power"] = target_power * overshoot
                else:
                    actual_power = self.exponential_approach(
                        current_power, control_output, 
                        self.system_params["power_regulation_time_constant"]
                    )
                    status["forward_power"] = self.add_realistic_noise(actual_power, 0.02)
                
                # 램프업 중 매칭 지연으로 인한 높은 reflect
                matching_lag = np.exp(-progress * 3)  # 매칭이 점진적으로 개선
                reflect_ratio = 0.05 + 0.15 * matching_lag
                if self.test_mode == "sine_wave":
                    status["reflect_power"] = status["forward_power"] * reflect_ratio
                else:
                    status["reflect_power"] = self.add_realistic_noise(
                        status["forward_power"] * reflect_ratio, 0.1
                    )
                
                if self.test_mode != "sine_wave":
                    self.last_values[client_key]["forward_power"] = actual_power
                    self.last_values[client_key]["control_error"] = error
            else:
                status["forward_power"] = 0.0
                status["reflect_power"] = 0.0
        
        base_temp = 30 + status["forward_power"] / 40
        if self.test_mode == "sine_wave":
            status["temperature"] = 25 + 15 * min((t % 30) / 30.0, 1.0)
        else:
            status["temperature"] = self.add_realistic_noise(base_temp, 0.02)
        
        status["led_state"] = 0x0021 if client_state["rf_enabled"] else 0x0001
        status["alarm_state"] = 0x0000
        return "파워 램프 테스트 (" + ("사인파" if self.test_mode == "sine_wave" else "제어 루프") + ")"
    
    def plasma_ignition_test(self, status, t, client_state):
        """플라즈마 점화 - 실제 물리 현상"""
        client_key = id(client_state)
        
        if not client_state["rf_enabled"]:
            status["forward_power"] = 0.0
            status["reflect_power"] = 0.0
        else:
            set_power = client_state.get("set_power", 0)
            if set_power > 0:
                # 점화 사이클 (10초 주기)
                ignition_cycle = t % 10
                
                if self.test_mode == "sine_wave":
                    # 기존 사인파 방식
                    if ignition_cycle < 0.5:
                        status["forward_power"] = set_power * 0.3
                        status["reflect_power"] = status["forward_power"] * 0.8
                    elif ignition_cycle < 1.0:
                        status["forward_power"] = set_power * (0.3 + 0.7 * (ignition_cycle - 0.5) * 2)
                        status["reflect_power"] = status["forward_power"] * (0.8 - 0.6 * (ignition_cycle - 0.5) * 2)
                    else:
                        status["forward_power"] = set_power * (0.95 + 0.05 * np.sin(2 * np.pi * t))
                        status["reflect_power"] = status["forward_power"] * 0.05
                else:
                    # 현실적 점화 시뮬레이션
                    if client_key not in self.internal_states:
                        self.internal_states[client_key] = {"ignition_state": "pre_ignition"}
                    
                    state = self.internal_states[client_key]["ignition_state"]
                    
                    if ignition_cycle < 1.0 and state != "igniting":
                        self.internal_states[client_key]["ignition_state"] = "igniting"
                        ignition_probability = 0.7 + 0.3 * np.random.random()
                    elif ignition_cycle < 1.5 and state == "igniting":
                        ignition_probability = 0.9
                    elif ignition_cycle >= 1.5:
                        self.internal_states[client_key]["ignition_state"] = "ignited"
                        ignition_probability = 1.0
                    else:
                        ignition_probability = 0.3
                    
                    if ignition_probability > 0.8:
                        # 점화됨 - 안정적 파워
                        status["forward_power"] = self.add_realistic_noise(set_power * 0.95, 0.01)
                        status["reflect_power"] = self.add_realistic_noise(
                            status["forward_power"] * 0.05, 0.02
                        )
                    else:
                        # 점화 전 - 높은 reflect, 불안정한 파워
                        unstable_power = set_power * (0.2 + 0.3 * np.random.random())
                        status["forward_power"] = self.add_realistic_noise(unstable_power, 0.2)
                        status["reflect_power"] = self.add_realistic_noise(
                            status["forward_power"] * (0.6 + 0.3 * np.random.random()), 0.3
                        )
            else:
                status["forward_power"] = 0.0
                status["reflect_power"] = 0.0
                if client_key in self.internal_states:
                    self.internal_states[client_key]["ignition_state"] = "pre_ignition"
        
        base_temp = 38 + status["forward_power"] / 50
        if self.test_mode == "sine_wave":
            status["temperature"] = 40 + 10 * np.sin(2 * np.pi * 0.2 * t)
        else:
            status["temperature"] = self.add_realistic_noise(base_temp, 0.02)
        
        status["led_state"] = 0x0021 if client_state["rf_enabled"] else 0x0001
        status["alarm_state"] = 0x0000
        return "플라즈마 점화 시뮬레이션"
    
    # 나머지 시나리오들은 비슷한 패턴으로 구현
    def matching_network_aging(self, status, t, client_state):
        """매칭 네트워크 노화"""
        if not client_state["rf_enabled"]:
            status["forward_power"] = 0.0
            status["reflect_power"] = 0.0
        else:
            set_power = client_state.get("set_power", 0)
            if set_power > 0:
                if self.test_mode == "sine_wave":
                    drift_factor = 1.0 + 0.02 * (t / 60)
                    status["forward_power"] = set_power * (0.98 + 0.02 * np.sin(2 * np.pi * 0.1 * t))
                    base_reflect = 0.03 + 0.02 * min(drift_factor - 1.0, 0.1)
                    status["reflect_power"] = status["forward_power"] * (base_reflect + 0.01 * np.sin(2 * np.pi * 0.3 * t))
                else:
                    aging_factor = 1.0 - 0.001 * (t / 3600)
                    aging_factor = max(0.9, aging_factor)
                    effective_power = set_power * aging_factor
                    status["forward_power"] = self.add_realistic_noise(effective_power, 0.015)
                    base_reflect = 0.03 + 0.02 * (1 - aging_factor) * 10
                    status["reflect_power"] = self.add_realistic_noise(
                        status["forward_power"] * base_reflect, 0.1
                    )
            else:
                status["forward_power"] = 0.0
                status["reflect_power"] = 0.0
        
        base_temp = 40 + status["forward_power"] / 45
        status["temperature"] = self.add_realistic_noise(base_temp, 0.02) if self.test_mode != "sine_wave" else 42 + 3 * np.sin(2 * np.pi * 0.1 * t)
        status["led_state"] = 0x0025 if status["reflect_power"] > status["forward_power"] * 0.1 else 0x0021
        status["alarm_state"] = 0x0000
        return "매칭 네트워크 노화"
    
    def arc_event_simulation(self, status, t, client_state):
        return self.normal_operation(status, t, client_state)[:-1] + " - 아크)"
    
    def thermal_cycling_test(self, status, t, client_state):
        return self.normal_operation(status, t, client_state)[:-1] + " - 열순환)"
    
    def process_recipe_etch(self, status, t, client_state):
        return self.normal_operation(status, t, client_state)[:-1] + " - 에칭)"
    
    def process_recipe_depo(self, status, t, client_state):
        return self.normal_operation(status, t, client_state)[:-1] + " - 증착)"
    
    def impedance_load_variation(self, status, t, client_state):
        return self.normal_operation(status, t, client_state)[:-1] + " - 부하변동)"
    
    def power_supply_ripple_test(self, status, t, client_state):
        return self.normal_operation(status, t, client_state)[:-1] + " - 전원리플)"
    
    def chamber_conditioning(self, status, t, client_state):
        return self.normal_operation(status, t, client_state)[:-1] + " - 챔버컨디셔닝)"
    
    def maintenance_mode_test(self, status, t, client_state):
        return self.normal_operation(status, t, client_state)[:-1] + " - 정비모드)"

class RFServer:
    def __init__(self, host=HOST, port=PORT, gui_queue=None):
        self.host = host
        self.port = port
        self.gui_queue = gui_queue
        self.server = None
        self.clients = []
        self.client_states = defaultdict(lambda: {
            "rf_enabled": False,
            "set_power": 0,
            "alarm_state": 0,
            "control_mode": 0,
            "regulation_mode": 0,
            "ramp_settings": {"mode": 0, "up_time": 0, "down_time": 0},
            "cex_settings": {"enable": 0, "mode": 0, "output_phase": 0.0, "rf_phase": 0.0},
            "pulse_settings": {"mode": 0, "onoff": 0, "duty": 0.0, "frequency": 0, "output_sync": 0, "input_sync": 0},
            "rf_frequency": 13500000,
            "freq_tuning_enabled": False,
            "freq_tuning_mode": 0,
            "freq_tuning_min": 13000000,
            "freq_tuning_max": 14000000,
            "freq_tuning_start": 13500000,
            "freq_tuning_min_step": 1000,
            "freq_tuning_max_step": 100000,
            "freq_tuning_stop_gamma": 0.1,
            "freq_tuning_return_gamma": 0.05,
            "freq_tuning_retuning": 0,
            "start_time": time.time(),
            "frame_count": 0,
            "led_state": 0x0001,
            "alarm_state": 0x0001
        })
        self.running = False
        self.global_frame_count = 0
        self.frame_count_lock = threading.Lock()
        
        # 개선된 테스트 시나리오 매니저
        self.scenario_manager = RealisticTestScenarioManager()
        self.auto_switch = False  # GUI에서 제어
        
        # 서버 스레드
        self.server_thread = None

    def log_message(self, message):
        """GUI 로그에 메시지 추가"""
        if self.gui_queue:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.gui_queue.put(f"[{timestamp}] {message}")

    def get_client_key(self, addr):
        ip, port = addr
        return ip

    def start(self):
        """서버 시작"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host, self.port))
            self.server.listen(MAX_CLIENTS)
            self.running = True
            
            self.log_message(f"RF Test Server started on {self.host}:{self.port}")
            self.log_message(f"Server listening on all interfaces (0.0.0.0:{self.port})")
            self.log_message(f"Client can connect to: localhost:{self.port} or <your_ip>:{self.port}")
            
            # 서버 스레드 시작
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
            
            return True
        except Exception as e:
            self.log_message(f"Failed to start server: {e}")
            # 포트가 사용중인 경우 구체적인 안내
            if "Address already in use" in str(e) or "지정된 주소를 사용할 수 없습니다" in str(e):
                self.log_message(f"포트 {self.port}이 이미 사용중입니다. 다른 프로그램을 종료하거나 포트를 변경하세요.")
            return False

    def _server_loop(self):
        """서버 메인 루프"""
        self.log_message("Server thread started, waiting for client connections...")
        
        while self.running:
            try:
                self.server.settimeout(1.0)
                client, addr = self.server.accept()
                client.settimeout(SOCKET_TIMEOUT)
                self.log_message(f"New client connected from {addr}")
                self.clients.append(client)
                
                # 클라이언트 핸들러 스레드 시작
                client_thread = threading.Thread(target=self.handle_client, args=(client, addr), daemon=True)
                client_thread.start()
                self.log_message(f"Started handler thread for client {addr}")
                
            except socket.timeout:
                continue  # 타임아웃은 정상, 계속 대기
            except Exception as e:
                if self.running:
                    self.log_message(f"Server accept error: {e}")
                break
        
        self.log_message("Server loop ended")

    def handle_client(self, client, addr):
        client_key = self.get_client_key(addr)
        client_state = self.client_states[client_key]
        self.log_message(f"Client {addr} using state key: {client_key}")
        
        while self.running:
            try:
                data = client.recv(64)
                if not data:
                    if client in self.clients:
                        self.clients.remove(client)
                    client.close()
                    self.log_message(f"Client disconnected from {addr}")
                    break
                
                with self.frame_count_lock:
                    self.global_frame_count += 1
                    client_state["frame_count"] += 1
                
                parsed = RFProtocol.parse_frame(data)
                
                if not parsed:
                    self.log_message(f"Invalid frame from {addr}: hex={data.hex()}")
                    continue

                response = None
                cmd, subcmd = parsed["cmd"], parsed["subcmd"]

                if cmd == RFProtocol.CMD_DEVICE_STATUS_GET and subcmd == RFProtocol.SUBCMD_DEVICE_STATUS:
                    status = self.create_complete_status(client_state, time.time())
                    response = RFProtocol.create_frame(cmd, subcmd, self.create_status_response(status))

                elif cmd == RFProtocol.CMD_RF_ON and subcmd == RFProtocol.SUBCMD_RF_ON:
                    client_state["rf_enabled"] = True
                    self.log_message(f"RF On for {addr} (key: {client_key})")
                    response = RFProtocol.create_frame(cmd, subcmd, struct.pack('<B', 0))

                elif cmd == RFProtocol.CMD_RF_OFF and subcmd == RFProtocol.SUBCMD_RF_OFF:
                    client_state["rf_enabled"] = False
                    self.log_message(f"RF Off for {addr} (key: {client_key})")
                    response = RFProtocol.create_frame(cmd, subcmd, struct.pack('<B', 0))
                
                elif cmd == RFProtocol.CMD_SET_POWER and subcmd == RFProtocol.SUBCMD_SET_POWER:
                    if len(parsed["data"]) >= 4:
                        set_power_value = struct.unpack('<I', parsed["data"][:4])[0]
                        client_state["set_power"] = set_power_value
                        self.log_message(f"Set Power: {set_power_value}W for {addr} (key: {client_key})")
                        response = RFProtocol.create_frame(cmd, subcmd, struct.pack('<B', 0))
                    else:
                        self.log_message(f"Invalid Set Power command data length from {addr}")
                        response = RFProtocol.create_frame(cmd, subcmd, struct.pack('<B', 1))  # Error response
                
                else:
                    # 기타 명령어들에 대한 기본 응답
                    response = RFProtocol.create_frame(cmd, subcmd if subcmd else 0, struct.pack('<B', 0))

                if response:
                    client.sendall(response)
                    
            except Exception as e:
                self.log_message(f"Error handling client {addr}: {e}")
                try:
                    client.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                if client in self.clients:
                    self.clients.remove(client)
                try:
                    client.close()
                except:
                    pass
                break

    def create_complete_status(self, client_state, current_time):
        """완전한 상태 데이터 생성 - 시나리오 또는 수동 모드 기반"""
        
        # 기본 상태 생성
        status = {
            "rf_on_off": 1 if client_state["rf_enabled"] else 0,
            "set_power": client_state["set_power"],
            "control_mode": client_state["control_mode"],
            "alarm_state": client_state["alarm_state"],
            "forward_power": 0.0,  # 기본값, 시나리오에서 설정됨
            "reflect_power": 0.0,  # 기본값, 시나리오에서 설정됨
            "delivery_power": 0.0,  # 계산됨
            "frequency": float(client_state["rf_frequency"]),
            "gamma": 0.5,
            "real_gamma": 0.25,
            "image_gamma": 0.15,
            "rf_phase": 0.0,
            "temperature": 40.0,  # 기본값, 시나리오에서 설정됨
            "system_state": 0x0000,
            "led_state": 0x0001,  # 기본값, 시나리오에서 설정됨
            "firmware_version": 1.22
        }
        
        # 모드에 따른 상태 결정 - GUI 인스턴스 확인
        gui_instance = getattr(self, '_gui_instance', None)
        if gui_instance and hasattr(gui_instance, 'manual_mode_enabled') and gui_instance.manual_mode_enabled:
            # 수동 모드: GUI에서 설정된 값 사용
            status["forward_power"] = gui_instance.forward_power_var.get()
            status["reflect_power"] = gui_instance.reflect_power_var.get()
            status["temperature"] = gui_instance.temperature_var.get()
            status["frequency"] = gui_instance.rf_frequency_var.get() * 1000000  # MHz to Hz
            status["led_state"] = gui_instance.manual_led_state
            status["alarm_state"] = gui_instance.manual_alarm_state
        else:
            # 자동 시나리오 모드: 개선된 시나리오 사용
            t = (current_time - client_state["start_time"]) % 30  # 30초 주기
            # client_state를 시나리오에 전달
            scenario_name = self.scenario_manager.get_current_scenario_data(status, t, client_state)
        
        # Delivery Power 계산 (Forward - Reflect)
        status["delivery_power"] = max(0, status["forward_power"] - status["reflect_power"])
        
        # Gamma 계산 (reflect/forward 비율 기반)
        if status["forward_power"] > 0:
            gamma_magnitude = min(status["reflect_power"] / status["forward_power"], 1.0)
            status["gamma"] = gamma_magnitude
            status["real_gamma"] = gamma_magnitude * 0.7  # 실제 부분
            status["image_gamma"] = gamma_magnitude * 0.3  # 허수 부분
        else:
            status["gamma"] = 0.0
            status["real_gamma"] = 0.0
            status["image_gamma"] = 0.0
        
        return status

    def create_status_response(self, status):
        data = bytearray()
        data.extend(struct.pack('<B', status["rf_on_off"]))
        data.extend(struct.pack('<B', status["control_mode"]))
        data.extend(struct.pack('<H', status["system_state"]))
        data.extend(struct.pack('<H', status["led_state"]))
        data.extend(struct.pack('<H', status["alarm_state"]))
        data.extend(struct.pack('<I', status["set_power"]))
        data.extend(struct.pack('<f', status["forward_power"]))
        data.extend(struct.pack('<f', status["reflect_power"]))
        data.extend(struct.pack('<f', status["delivery_power"]))
        data.extend(struct.pack('<f', status["frequency"]))
        data.extend(struct.pack('<f', status["gamma"]))
        data.extend(struct.pack('<f', status["real_gamma"]))
        data.extend(struct.pack('<f', status["image_gamma"]))
        data.extend(struct.pack('<f', status["rf_phase"]))
        data.extend(struct.pack('<f', status["temperature"]))
        data.extend(struct.pack('<f', status["firmware_version"]))
        
        expected_length = 52
        if len(data) != expected_length:
            self.log_message(f"상태 데이터 길이 오류: 기대값={expected_length}, 실제값={len(data)}")
            while len(data) < expected_length:
                data.extend(b'\x00')
            data = data[:expected_length]
        
        return data

    def stop(self):
        """서버 정지"""
        self.log_message("Stopping RF Test Server...")
        self.running = False
        
        # 클라이언트 연결 정리
        for client in self.clients[:]:
            try:
                client.close()
            except:
                pass
        self.clients.clear()
        
        # 서버 소켓 정리
        if self.server:
            try:
                self.server.close()
            except:
                pass
        
        self.log_message("RF Test Server stopped")

    def set_scenario(self, scenario_index):
        """시나리오 설정"""
        if 0 <= scenario_index < len(self.scenario_manager.scenarios):
            self.scenario_manager.current_scenario = scenario_index
            scenario_names = self.scenario_manager.get_scenario_names()
            self.log_message(f"시나리오 변경: {scenario_names[scenario_index]}")

class RFServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RF Generator Test Server GUI")
        self.root.geometry("600x580")  # 높이 조금 증가
        self.root.resizable(True, True)  # 크기 조절 가능하게
        self.gui_queue = queue.Queue()
        
        # 서버 인스턴스
        self.server = RFServer(gui_queue=self.gui_queue)
        # GUI 인스턴스를 서버에 연결
        self.server._gui_instance = self
        
        # 자동 전환 타이머
        self.auto_timer = None
        self.auto_switch_enabled = False
        
        # 수동 제어용 상태 변수들 초기화
        self.manual_mode_enabled = False
        self.manual_led_state = 0x0001
        self.manual_alarm_state = 0x0000
        
        # 변수 초기화 (위젯 생성 전에)
        self.forward_power_var = tk.DoubleVar(value=300.0)
        self.reflect_power_var = tk.DoubleVar(value=10.0)
        self.temperature_var = tk.DoubleVar(value=40.0)
        self.rf_frequency_var = tk.DoubleVar(value=13.56)
        
        self.create_widgets()
        self.setup_gui_update_timer()

    def create_widgets(self):
        """GUI 위젯 생성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 상단 제어 패널
        control_frame = ttk.LabelFrame(main_frame, text="서버 제어", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 서버 상태 및 제어 버튼
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill=tk.X)
        
        self.server_status_label = ttk.Label(status_frame, text="서버 상태: 중지됨", font=("Arial", 10, "bold"))
        self.server_status_label.pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.start_button = ttk.Button(button_frame, text="서버 시작", command=self.start_server)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="서버 중지", command=self.stop_server, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)
        
        # 시나리오 제어 패널 (컴팩트하게)
        scenario_frame = ttk.LabelFrame(main_frame, text="시나리오 제어", padding="5")
        scenario_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 모드 선택 (더 컴팩트하게)
        mode_frame = ttk.Frame(scenario_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.mode_var = tk.StringVar(value="scenario")
        ttk.Radiobutton(mode_frame, text="자동 시나리오", variable=self.mode_var, 
                       value="scenario", command=self.on_mode_changed).pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="수동 제어", variable=self.mode_var, 
                       value="manual", command=self.on_mode_changed).pack(side=tk.LEFT, padx=(15, 0))
        
        # 자동 시나리오 모드 프레임 (더 컴팩트하게)
        self.scenario_auto_frame = ttk.Frame(scenario_frame)
        self.scenario_auto_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 시나리오 선택 (한 줄에 배치)
        scenario_select_frame = ttk.Frame(self.scenario_auto_frame)
        scenario_select_frame.pack(fill=tk.X, pady=(0, 3))
        
        ttk.Label(scenario_select_frame, text="시나리오:", font=("Arial", 9)).pack(side=tk.LEFT)
        
        self.scenario_var = tk.StringVar()
        scenario_names = self.server.scenario_manager.get_scenario_names()
        self.scenario_combo = ttk.Combobox(scenario_select_frame, textvariable=self.scenario_var, 
                                          values=scenario_names, state="readonly", width=25, font=("Arial", 8))
        self.scenario_combo.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        self.scenario_combo.current(0)
        self.scenario_combo.bind('<<ComboboxSelected>>', self.on_scenario_changed)
        
        # 시나리오 제어 버튼 (더 작게)
        scenario_btn_frame = ttk.Frame(self.scenario_auto_frame)
        scenario_btn_frame.pack(fill=tk.X)
        
        self.prev_button = ttk.Button(scenario_btn_frame, text="◀", command=self.prev_scenario, width=3)
        self.prev_button.pack(side=tk.LEFT, padx=(0, 3))
        
        self.next_button = ttk.Button(scenario_btn_frame, text="▶", command=self.next_scenario, width=3)
        self.next_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 자동 전환 체크박스
        self.auto_switch_var = tk.BooleanVar()
        auto_check = ttk.Checkbutton(scenario_btn_frame, text="자동 전환 (30초)", 
                                   variable=self.auto_switch_var, command=self.toggle_auto_switch)
        auto_check.pack(side=tk.LEFT)
        
        # ★★★ 테스트 모드 컨트롤 추가 ★★★
        self.create_test_mode_controls()
        
        # 수동 제어 모드 프레임
        self.manual_frame = ttk.Frame(scenario_frame)
        # manual_frame은 초기에는 표시하지 않음
        
        self.create_manual_control_widgets()
        
        # 상태 모니터링 패널 (더 컴팩트하게)
        monitor_frame = ttk.LabelFrame(main_frame, text="실시간 상태", padding="5")
        monitor_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 상태 표시를 3열로 더 컴팩트하게 배치
        status_display_frame = ttk.Frame(monitor_frame)
        status_display_frame.pack(fill=tk.X)
        
        # 첫 번째 행
        status_row1 = ttk.Frame(status_display_frame)
        status_row1.pack(fill=tk.X, pady=(0, 2))
        
        self.forward_power_label = ttk.Label(status_row1, text="Forward: 0.0W", font=("Arial", 8))
        self.forward_power_label.pack(side=tk.LEFT, anchor=tk.W)
        
        self.reflect_power_label = ttk.Label(status_row1, text="Reflect: 0.0W", font=("Arial", 8))
        self.reflect_power_label.pack(side=tk.LEFT, anchor=tk.W, padx=(20, 0))
        
        self.delivery_power_label = ttk.Label(status_row1, text="Delivery: 0.0W", font=("Arial", 8))
        self.delivery_power_label.pack(side=tk.LEFT, anchor=tk.W, padx=(20, 0))
        
        # 두 번째 행
        status_row2 = ttk.Frame(status_display_frame)
        status_row2.pack(fill=tk.X, pady=(0, 2))
        
        self.temperature_label = ttk.Label(status_row2, text="Temp: 0.0°C", font=("Arial", 8))
        self.temperature_label.pack(side=tk.LEFT, anchor=tk.W)
        
        self.led_state_label = ttk.Label(status_row2, text="LED: 0x0000", font=("Arial", 8))
        self.led_state_label.pack(side=tk.LEFT, anchor=tk.W, padx=(20, 0))
        
        self.alarm_state_label = ttk.Label(status_row2, text="Alarm: 0x0000", font=("Arial", 8))
        self.alarm_state_label.pack(side=tk.LEFT, anchor=tk.W, padx=(20, 0))
        
        # 통계 정보 (한 줄에)
        stats_frame = ttk.Frame(status_display_frame)
        stats_frame.pack(fill=tk.X)
        
        self.clients_label = ttk.Label(stats_frame, text="클라이언트: 0", font=("Arial", 8))
        self.clients_label.pack(side=tk.LEFT)
        
        self.frames_label = ttk.Label(stats_frame, text="프레임: 0", font=("Arial", 8))
        self.frames_label.pack(side=tk.RIGHT)
        
        # 로그 패널 (높이 줄임)
        log_frame = ttk.LabelFrame(main_frame, text="로그", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 로그 텍스트 영역 (높이 줄임)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 8))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 로그 제어 버튼 (더 작게)
        log_control_frame = ttk.Frame(log_frame)
        log_control_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(log_control_frame, text="지우기", command=self.clear_log, width=8).pack(side=tk.LEFT)
        ttk.Button(log_control_frame, text="저장", command=self.save_log, width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # 자동 스크롤 체크박스
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(log_control_frame, text="자동스크롤", variable=self.auto_scroll_var).pack(side=tk.RIGHT)

    def create_test_mode_controls(self):
        """테스트 모드 및 개별 노이즈 제어 생성"""
        test_mode_frame = ttk.Frame(self.scenario_auto_frame)
        test_mode_frame.pack(fill=tk.X, pady=(3, 0))
        
        # 첫 번째 행: 테스트 모드 선택
        mode_row = ttk.Frame(test_mode_frame)
        mode_row.pack(fill=tk.X, pady=(0, 3))
        
        ttk.Label(mode_row, text="모드:", font=("Arial", 8)).pack(side=tk.LEFT)
        
        self.test_mode_var = tk.StringVar(value="realistic")
        mode_combo = ttk.Combobox(mode_row, textvariable=self.test_mode_var,
                                 values=["realistic", "sine_wave"], 
                                 state="readonly", width=12, font=("Arial", 8))
        mode_combo.pack(side=tk.LEFT, padx=(5, 10))
        mode_combo.bind('<<ComboboxSelected>>', self.on_test_mode_changed)
        
        # 노이즈 활성화/비활성화 체크박스
        self.noise_enabled_var = tk.BooleanVar(value=True)
        noise_check = ttk.Checkbutton(mode_row, text="노이즈 활성화", 
                                     variable=self.noise_enabled_var, 
                                     command=self.on_noise_settings_changed)
        noise_check.pack(side=tk.LEFT, padx=(10, 0))
        
        # 두 번째 행: 개별 노이즈 제어
        self.noise_control_frame = ttk.Frame(test_mode_frame)
        self.noise_control_frame.pack(fill=tk.X)
        
        # 화이트 노이즈
        ttk.Label(self.noise_control_frame, text="화이트:", font=("Arial", 7)).grid(row=0, column=0, sticky="w", padx=(0, 2))
        self.white_noise_var = tk.DoubleVar(value=1.0)
        white_spin = ttk.Spinbox(self.noise_control_frame, from_=0.0, to=10.0, increment=0.01,
                                textvariable=self.white_noise_var, width=6, font=("Arial", 7))
        white_spin.grid(row=0, column=1, padx=(0, 2))
        white_spin.bind('<Return>', self.on_noise_settings_changed)
        white_spin.bind('<FocusOut>', self.on_noise_settings_changed)
        ttk.Label(self.noise_control_frame, text="%", font=("Arial", 7)).grid(row=0, column=2, sticky="w", padx=(0, 8))
        
        # 1/f 노이즈
        ttk.Label(self.noise_control_frame, text="1/f:", font=("Arial", 7)).grid(row=0, column=3, sticky="w", padx=(0, 2))
        self.pink_noise_var = tk.DoubleVar(value=0.5)
        pink_spin = ttk.Spinbox(self.noise_control_frame, from_=0.0, to=10.0, increment=0.01,
                               textvariable=self.pink_noise_var, width=6, font=("Arial", 7))
        pink_spin.grid(row=0, column=4, padx=(0, 2))
        pink_spin.bind('<Return>', self.on_noise_settings_changed)
        pink_spin.bind('<FocusOut>', self.on_noise_settings_changed)
        ttk.Label(self.noise_control_frame, text="%", font=("Arial", 7)).grid(row=0, column=5, sticky="w", padx=(0, 8))
        
        # 스파이크 노이즈
        ttk.Label(self.noise_control_frame, text="스파이크:", font=("Arial", 7)).grid(row=0, column=6, sticky="w", padx=(0, 2))
        self.spike_noise_var = tk.DoubleVar(value=2.0)
        spike_spin = ttk.Spinbox(self.noise_control_frame, from_=0.0, to=10.0, increment=0.01,
                                textvariable=self.spike_noise_var, width=6, font=("Arial", 7))
        spike_spin.grid(row=0, column=7, padx=(0, 2))
        spike_spin.bind('<Return>', self.on_noise_settings_changed)
        spike_spin.bind('<FocusOut>', self.on_noise_settings_changed)
        ttk.Label(self.noise_control_frame, text="%", font=("Arial", 7)).grid(row=0, column=8, sticky="w", padx=(0, 8))
        
        # 스파이크 확률
        ttk.Label(self.noise_control_frame, text="확률:", font=("Arial", 7)).grid(row=0, column=9, sticky="w", padx=(0, 2))
        self.spike_prob_var = tk.DoubleVar(value=0.01)
        prob_spin = ttk.Spinbox(self.noise_control_frame, from_=0.0, to=1.0, increment=0.001,
                               textvariable=self.spike_prob_var, width=6, font=("Arial", 7))
        prob_spin.grid(row=0, column=10, padx=(0, 2))
        prob_spin.bind('<Return>', self.on_noise_settings_changed)
        prob_spin.bind('<FocusOut>', self.on_noise_settings_changed)
        ttk.Label(self.noise_control_frame, text="%", font=("Arial", 7)).grid(row=0, column=11, sticky="w")

    def on_test_mode_changed(self, event=None):
        """테스트 모드 변경 시 호출"""
        mode = self.test_mode_var.get()
        self.update_noise_settings()
        
        if mode == "sine_wave":
            self.add_log_message("사인파 테스트 모드 활성화 - 계측기 검증용")
            # 사인파 모드에서는 노이즈 컨트롤 비활성화
            for widget in self.noise_control_frame.winfo_children():
                if isinstance(widget, ttk.Spinbox):
                    widget.config(state="disabled")
            self.noise_enabled_var.set(False)
        else:
            self.add_log_message("현실적 시뮬레이션 모드 활성화")
            # 현실적 모드에서는 노이즈 컨트롤 활성화
            for widget in self.noise_control_frame.winfo_children():
                if isinstance(widget, ttk.Spinbox):
                    widget.config(state="normal")
            self.noise_enabled_var.set(True)

    def on_noise_settings_changed(self, event=None):
        """노이즈 설정 변경 시 호출"""
        self.update_noise_settings()

    def update_noise_settings(self):
        """노이즈 설정 업데이트"""
        mode = self.test_mode_var.get()
        
        if not self.noise_enabled_var.get() or mode == "sine_wave":
            # 노이즈 비활성화
            white_noise = 0
            pink_noise = 0
            spike_noise = 0
            spike_prob = 0
        else:
            # 개별 노이즈 값 적용
            white_noise = self.white_noise_var.get()
            pink_noise = self.pink_noise_var.get()
            spike_noise = self.spike_noise_var.get()
            spike_prob = self.spike_prob_var.get()
        
        self.server.scenario_manager.set_test_mode(
            mode, white_noise, pink_noise, spike_noise, spike_prob
        )
        
        if mode != "sine_wave" and self.noise_enabled_var.get():
            # 노이즈 설정 기본 로그
            self.add_log_message(
                f"노이즈 설정: 화이트={white_noise:.2f}%, 1/f={pink_noise:.2f}%, "
                f"스파이크={spike_noise:.2f}% (확률={spike_prob:.3f}%)"
            )
            
            # 클라이언트의 실제 Set Power 값 가져오기
            reference_power = 1000  # 기본값
            if self.server.client_states:
                # 첫 번째 클라이언트의 Set Power 사용
                client_state = next(iter(self.server.client_states.values()))
                if client_state.get("set_power", 0) > 0:
                    reference_power = client_state["set_power"]
                    self.add_log_message(f"=== {reference_power}W 설정 시 예상 변동값 ===")
                else:
                    self.add_log_message("=== Set Power 미설정 (1000W 기준 예상값) ===")
            else:
                self.add_log_message("=== 클라이언트 미연결 (1000W 기준 예상값) ===")
            
            if white_noise > 0:
                white_1sigma = reference_power * (white_noise / 100) * 0.1  # 1σ (68.2%)
                white_3sigma = white_1sigma * 3  # 3σ (99.7%)
                self.add_log_message(f"화이트 노이즈 {white_noise:.2f}% → ±{white_1sigma:.2f}W (1σ), ±{white_3sigma:.2f}W (3σ)")
            
            if pink_noise > 0:
                pink_1sigma = reference_power * (pink_noise / 100) * 0.1  # 1σ
                pink_3sigma = pink_1sigma * 3  # 3σ
                self.add_log_message(f"1/f 노이즈 {pink_noise:.2f}% → ±{pink_1sigma:.2f}W (1σ), ±{pink_3sigma:.2f}W (3σ)")
            
            if spike_noise > 0 and spike_prob > 0:
                spike_variation = reference_power * (spike_noise / 100) * 1.5  # 실제 팩터 적용
                spike_freq = spike_prob / 100 * 10  # 초당 발생 횟수 (10Hz 업데이트 기준)
                if spike_freq >= 1:
                    freq_text = f"{spike_freq:.1f}회/초"
                elif spike_freq >= 0.1:
                    freq_text = f"{spike_freq*10:.1f}회/10초"
                else:
                    freq_text = f"{spike_freq*60:.1f}회/분"
                self.add_log_message(f"스파이크 {spike_noise:.2f}%, {spike_prob:.3f}% 확률 → ±{spike_variation:.2f}W ({freq_text})")
            
            # RMS 합성 (1σ와 3σ 각각)
            white_1s = (reference_power * (white_noise / 100) * 0.1) if white_noise > 0 else 0
            pink_1s = (reference_power * (pink_noise / 100) * 0.1) if pink_noise > 0 else 0
            combined_1sigma = (white_1s**2 + pink_1s**2)**0.5
            combined_3sigma = combined_1sigma * 3
            
            if combined_1sigma > 0:
                self.add_log_message(f"합성 노이즈: ±{combined_1sigma:.2f}W (1σ, 68%), ±{combined_3sigma:.2f}W (3σ, 99.7%)")
                self.add_log_message(f"일반적 범위 (68.2%): {reference_power-combined_1sigma:.2f}W ~ {reference_power+combined_1sigma:.2f}W")
                self.add_log_message(f"거의 모든 범위 (99.7%): {reference_power-combined_3sigma:.2f}W ~ {reference_power+combined_3sigma:.2f}W")
            
            if spike_noise > 0 and spike_prob > 0:
                spike_var = reference_power * (spike_noise / 100) * 1.5
                total_max = combined_3sigma + spike_var
                self.add_log_message(f"스파이크 포함 최대: {reference_power-total_max:.2f}W ~ {reference_power+total_max:.2f}W")
        
        elif mode == "sine_wave":
            # 클라이언트 Set Power 가져오기
            reference_power = 1000
            if self.server.client_states:
                client_state = next(iter(self.server.client_states.values()))
                if client_state.get("set_power", 0) > 0:
                    reference_power = client_state["set_power"]
            
            self.add_log_message("사인파 모드 - 노이즈 없음, 순수 수학적 변동만 적용")
            self.add_log_message(f"=== {reference_power}W 설정 시 예상 변동값 ===")
            self.add_log_message("사인파 변동: 시나리오에 따라 ±5% ~ ±10% 수학적 변동")
            sine_5pct = reference_power * 0.05
            sine_10pct = reference_power * 0.1
            self.add_log_message(f"예) 정상 운영: {reference_power-sine_5pct:.0f}W ~ {reference_power+sine_5pct:.0f}W (±5% 사인파)")
            self.add_log_message(f"예) 기타 시나리오: {reference_power-sine_10pct:.0f}W ~ {reference_power+sine_10pct:.0f}W (±10% 사인파)")
            
        elif mode == "realistic" and not self.noise_enabled_var.get():
            # 클라이언트 Set Power 가져오기
            reference_power = 1000
            if self.server.client_states:
                client_state = next(iter(self.server.client_states.values()))
                if client_state.get("set_power", 0) > 0:
                    reference_power = client_state["set_power"]
            
            self.add_log_message("현실적 모드 - 노이즈 비활성화")
            self.add_log_message(f"=== {reference_power}W 설정 시 예상 변동값 ===")
            self.add_log_message(f"노이즈 없음: {reference_power:.1f}W 고정 (완벽히 안정적)")
            self.add_log_message("RF OFF 시: 0.0W")
            self.add_log_message("Set Power에 따라 정확히 해당 값 출력")

    def create_manual_control_widgets(self):
        """수동 제어 위젯들 생성 (컴팩트 버전)"""
        # 수동 제어 메인 프레임
        manual_main_frame = ttk.Frame(self.manual_frame)
        manual_main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 파워 및 온도 제어 (더 컴팩트하게)
        power_temp_frame = ttk.LabelFrame(manual_main_frame, text="파워/온도", padding="5")
        power_temp_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 한 줄에 모든 컨트롤 배치
        controls_frame = ttk.Frame(power_temp_frame)
        controls_frame.pack(fill=tk.X)
        
        # Forward Power
        ttk.Label(controls_frame, text="FWD:", font=("Arial", 8)).grid(row=0, column=0, sticky="w", padx=(0, 2))
        ttk.Spinbox(controls_frame, from_=0, to=1000, increment=10, 
                   textvariable=self.forward_power_var, width=8, font=("Arial", 8)).grid(row=0, column=1, padx=(0, 10))
        
        # Reflect Power
        ttk.Label(controls_frame, text="REF:", font=("Arial", 8)).grid(row=0, column=2, sticky="w", padx=(0, 2))
        ttk.Spinbox(controls_frame, from_=0, to=200, increment=1, 
                   textvariable=self.reflect_power_var, width=8, font=("Arial", 8)).grid(row=0, column=3, padx=(0, 10))
        
        # Temperature
        ttk.Label(controls_frame, text="TEMP:", font=("Arial", 8)).grid(row=1, column=0, sticky="w", padx=(0, 2), pady=(3, 0))
        ttk.Spinbox(controls_frame, from_=-20, to=100, increment=1, 
                   textvariable=self.temperature_var, width=8, font=("Arial", 8)).grid(row=1, column=1, padx=(0, 10), pady=(3, 0))
        
        # RF Frequency
        ttk.Label(controls_frame, text="FREQ:", font=("Arial", 8)).grid(row=1, column=2, sticky="w", padx=(0, 2), pady=(3, 0))
        ttk.Spinbox(controls_frame, from_=1, to=30, increment=0.01, 
                   textvariable=self.rf_frequency_var, width=8, font=("Arial", 8)).grid(row=1, column=3, padx=(0, 10), pady=(3, 0))
        
        # LED 상태 제어 (더 컴팩트하게)
        led_frame = ttk.LabelFrame(manual_main_frame, text="LED (16비트)", padding="5")
        led_frame.pack(fill=tk.X, pady=(0, 5))
        
        # LED 비트 체크박스들 (더 작은 폰트, 더 조밀하게)
        self.led_vars = []
        # LED 상태 비트 정의 (실제 문서 3.4 기준)
        led_descriptions = [
            "AC Power", "Interlock", "Alarm", "Over Temp", "Power Limit", "RF ON/OFF"
        ]
        
        # 중요한 LED 비트만 표시 (공간 절약)
        led_grid_frame = ttk.Frame(led_frame)
        led_grid_frame.pack(fill=tk.X)
        
        for i in range(16):
            var = tk.BooleanVar()
            self.led_vars.append(var)
            
            if i < 6:  # 중요한 비트만 표시
                row = i // 3
                col = i % 3
                cb = ttk.Checkbutton(led_grid_frame, 
                                   text=f"{i}:{led_descriptions[i]}" if i < len(led_descriptions) else f"{i}:R{i}",
                                   variable=var,
                                   command=self.update_manual_led_state)
                cb.grid(row=row, column=col, sticky="w", padx=(0, 10), pady=1)
        
        # LED 상태 표시
        led_status_frame = ttk.Frame(led_frame)
        led_status_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(led_status_frame, text="LED 상태:", font=("Arial", 8)).pack(side=tk.LEFT)
        self.manual_led_status_label = ttk.Label(led_status_frame, text="0x0000", 
                                               font=("Consolas", 9, "bold"), foreground="blue")
        self.manual_led_status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 알람 상태 제어 (더 컴팩트하게)
        alarm_frame = ttk.LabelFrame(manual_main_frame, text="알람 (16비트)", padding="5")
        alarm_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 알람 비트 체크박스들 (중요한 것만)
        self.alarm_vars = []
        # 알람 상태 비트 정의 (실제 문서 3.5 기준)
        alarm_descriptions = [
            "AUX0", "AUX1", "AUX2", "AC3", "AC4", "AC5", "PFC", "MaxPwr", "Gate", "Fan", "OverT", "IL11", "IL12", "IL13", "IL14", "UnderF"
        ]
        
        alarm_grid_frame = ttk.Frame(alarm_frame)
        alarm_grid_frame.pack(fill=tk.X)
        
        for i in range(16):
            var = tk.BooleanVar()
            self.alarm_vars.append(var)
            
            row = i // 4
            col = i % 4
            cb = ttk.Checkbutton(alarm_grid_frame,
                               text=f"{i}:{alarm_descriptions[i] if i < len(alarm_descriptions) else f'R{i}'}",
                               variable=var,
                               command=self.update_manual_alarm_state)
            cb.grid(row=row, column=col, sticky="w", padx=(0, 5), pady=1)
        
        # 알람 상태 표시
        alarm_status_frame = ttk.Frame(alarm_frame)
        alarm_status_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(alarm_status_frame, text="알람 상태:", font=("Arial", 8)).pack(side=tk.LEFT)
        self.manual_alarm_status_label = ttk.Label(alarm_status_frame, text="0x0000", 
                                                 font=("Consolas", 9, "bold"), foreground="red")
        self.manual_alarm_status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 수동 제어 버튼들 (더 작게)
        manual_control_frame = ttk.Frame(manual_main_frame)
        manual_control_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(manual_control_frame, text="LED OFF", 
                 command=self.clear_all_leds, width=8).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(manual_control_frame, text="알람 OFF", 
                 command=self.clear_all_alarms, width=8).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(manual_control_frame, text="기본값", 
                 command=self.set_default_values, width=8).pack(side=tk.LEFT, padx=(0, 10))
        
        # 프리셋 버튼들 (더 작게)
        preset_frame = ttk.Frame(manual_control_frame)
        preset_frame.pack(side=tk.RIGHT)
        
        ttk.Label(preset_frame, text="프리셋:", font=("Arial", 8)).pack(side=tk.LEFT)
        ttk.Button(preset_frame, text="정상", command=lambda: self.load_preset("normal"), width=6).pack(side=tk.LEFT, padx=(3, 2))
        ttk.Button(preset_frame, text="경고", command=lambda: self.load_preset("warning"), width=6).pack(side=tk.LEFT, padx=(2, 2))
        ttk.Button(preset_frame, text="오류", command=lambda: self.load_preset("error"), width=6).pack(side=tk.LEFT, padx=(2, 0))

    def on_mode_changed(self):
        """모드 변경 시 호출"""
        mode = self.mode_var.get()
        
        if mode == "scenario":
            # 자동 시나리오 모드
            self.scenario_auto_frame.pack(fill=tk.X, pady=(0, 10))
            self.manual_frame.pack_forget()
            self.manual_mode_enabled = False
            self.add_log_message("자동 시나리오 모드로 변경")
            
        elif mode == "manual":
            # 수동 제어 모드
            self.scenario_auto_frame.pack_forget()
            self.manual_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            self.manual_mode_enabled = True
            self.add_log_message("수동 제어 모드로 변경")
            
            # 자동 전환 타이머 중지
            if self.auto_timer:
                self.root.after_cancel(self.auto_timer)
                self.auto_timer = None
                self.auto_switch_var.set(False)
    
    def update_manual_led_state(self):
        """수동 LED 상태 업데이트"""
        if not self.manual_mode_enabled:
            return
            
        led_value = 0
        for i, var in enumerate(self.led_vars):
            if var.get():
                led_value |= (1 << i)
        
        self.manual_led_state = led_value
        self.manual_led_status_label.config(text=f"0x{led_value:04X}")
        self.add_log_message(f"수동 LED 상태 변경: 0x{led_value:04X}")
    
    def update_manual_alarm_state(self):
        """수동 알람 상태 업데이트"""
        if not self.manual_mode_enabled:
            return
            
        alarm_value = 0
        for i, var in enumerate(self.alarm_vars):
            if var.get():
                alarm_value |= (1 << i)
        
        self.manual_alarm_state = alarm_value
        self.manual_alarm_status_label.config(text=f"0x{alarm_value:04X}")
        self.add_log_message(f"수동 알람 상태 변경: 0x{alarm_value:04X}")
    
    def clear_all_leds(self):
        """모든 LED OFF"""
        for var in self.led_vars:
            var.set(False)
        self.update_manual_led_state()
    
    def clear_all_alarms(self):
        """모든 알람 OFF"""
        for var in self.alarm_vars:
            var.set(False)
        self.update_manual_alarm_state()
    
    def set_default_values(self):
        """기본값 설정"""
        # 파워 및 온도 기본값
        self.forward_power_var.set(300.0)
        self.reflect_power_var.set(10.0)
        self.temperature_var.set(40.0)
        self.rf_frequency_var.set(13.56)
        
        # LED: AC Power만 ON (기본값)
        for i, var in enumerate(self.led_vars):
            var.set(i == 0)  # 비트 0 (AC Power ON)만 True
        
        # 알람: 모두 OFF
        for var in self.alarm_vars:
            var.set(False)
        
        self.update_manual_led_state()
        self.update_manual_alarm_state()
        self.add_log_message("기본값으로 설정됨")
    
    def load_preset(self, preset_type):
        """프리셋 로드"""
        if preset_type == "normal":
            # 정상 상태
            self.forward_power_var.set(300.0)
            self.reflect_power_var.set(10.0)
            self.temperature_var.set(35.0)
            
            # LED: AC Power ON, RF ON (문서 기준)
            led_bits = [0, 5]  # Bit 0: AC ON, Bit 5: RF ON
            for i, var in enumerate(self.led_vars):
                var.set(i in led_bits)
            
            # 알람: 없음
            for var in self.alarm_vars:
                var.set(False)
                
        elif preset_type == "warning":
            # 경고 상태
            self.forward_power_var.set(450.0)
            self.reflect_power_var.set(25.0)
            self.temperature_var.set(55.0)
            
            # LED: AC Power ON, Alarm, Over Temp, RF ON
            led_bits = [0, 2, 3, 5]  # AC ON, Alarm, Over Temp, RF ON
            for i, var in enumerate(self.led_vars):
                var.set(i in led_bits)
            
            # 알람: Over Temp
            alarm_bits = [10]  # Over Temp
            for i, var in enumerate(self.alarm_vars):
                var.set(i in alarm_bits)
                
        elif preset_type == "error":
            # 오류 상태
            self.forward_power_var.set(600.0)
            self.reflect_power_var.set(60.0)
            self.temperature_var.set(75.0)
            
            # LED: AC Power ON, Interlock Failure, Alarm, Over Temp, Power Limited
            led_bits = [0, 1, 2, 3, 4]  # AC ON, Interlock Fail, Alarm, Over Temp, Power Limit
            for i, var in enumerate(self.led_vars):
                var.set(i in led_bits)
            
            # 알람: PFC Fail, Max Power Limit, Fan Fail, Over Temp
            alarm_bits = [6, 7, 9, 10]  # PFC Fail, Max Power Limit, Fan Fail, Over Temp
            for i, var in enumerate(self.alarm_vars):
                var.set(i in alarm_bits)
        
        self.update_manual_led_state()
        self.update_manual_alarm_state()
        self.add_log_message(f"프리셋 '{preset_type}' 로드됨")

    def setup_gui_update_timer(self):
        """GUI 업데이트 타이머 설정"""
        self.update_gui()
        self.root.after(100, self.setup_gui_update_timer)  # 100ms마다 업데이트
    
    def update_gui(self):
        """GUI 상태 업데이트"""
        # 큐에서 로그 메시지 처리
        while not self.gui_queue.empty():
            try:
                message = self.gui_queue.get_nowait()
                self.add_log_message(message)
            except queue.Empty:
                break
        
        # 서버 상태 업데이트
        if self.server.running:
            self.server_status_label.config(text="서버 상태: 실행중", foreground="green")
            
            # 실시간 상태 데이터 업데이트
            if self.server.client_states:
                # 첫 번째 클라이언트의 상태를 기준으로 표시
                client_state = next(iter(self.server.client_states.values()))
                current_status = self.server.create_complete_status(client_state, time.time())
                
                self.forward_power_label.config(text=f"Forward: {current_status['forward_power']:.1f}W")
                self.reflect_power_label.config(text=f"Reflect: {current_status['reflect_power']:.1f}W")
                self.delivery_power_label.config(text=f"Delivery: {current_status['delivery_power']:.1f}W")
                self.temperature_label.config(text=f"Temp: {current_status['temperature']:.1f}°C")
                self.led_state_label.config(text=f"LED: 0x{current_status['led_state']:04X}")
                self.alarm_state_label.config(text=f"Alarm: 0x{current_status['alarm_state']:04X}")
            
            # 클라이언트 수 업데이트
            self.clients_label.config(text=f"클라이언트: {len(self.server.clients)}")
            self.frames_label.config(text=f"프레임: {self.server.global_frame_count}")
        else:
            self.server_status_label.config(text="서버 상태: 중지됨", foreground="red")
    
    def add_log_message(self, message):
        """로그 메시지 추가"""
        self.log_text.insert(tk.END, message + "\n")
        
        # 자동 스크롤
        if hasattr(self, 'auto_scroll_var') and self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
        # 로그 길이 제한 (1000줄)
        lines = self.log_text.get("1.0", tk.END).split("\n")
        if len(lines) > 1000:
            # 처음 100줄 제거
            self.log_text.delete("1.0", "101.0")
    
    def start_server(self):
        """서버 시작"""
        try:
            if self.server.start():
                self.start_button.config(state=tk.DISABLED)
                self.stop_button.config(state=tk.NORMAL)
                self.add_log_message("GUI에서 서버 시작됨")
            else:
                messagebox.showerror("오류", "서버 시작 실패")
        except Exception as e:
            messagebox.showerror("오류", f"서버 시작 중 오류: {e}")
    
    def stop_server(self):
        """서버 중지"""
        try:
            self.server.stop()
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            # 자동 전환 타이머 중지
            if self.auto_timer:
                self.root.after_cancel(self.auto_timer)
                self.auto_timer = None
            
            self.add_log_message("GUI에서 서버 중지됨")
        except Exception as e:
            messagebox.showerror("오류", f"서버 중지 중 오류: {e}")

    def on_scenario_changed(self, event=None):
        """시나리오 선택 변경 시 호출"""
        selected_index = self.scenario_combo.current()
        self.server.set_scenario(selected_index)
    
    def prev_scenario(self):
        """이전 시나리오로 이동"""
        current = self.scenario_combo.current()
        total = len(self.server.scenario_manager.get_scenario_names())
        new_index = (current - 1) % total
        self.scenario_combo.current(new_index)
        self.server.set_scenario(new_index)
    
    def next_scenario(self):
        """다음 시나리오로 이동"""
        current = self.scenario_combo.current()
        total = len(self.server.scenario_manager.get_scenario_names())
        new_index = (current + 1) % total
        self.scenario_combo.current(new_index)
        self.server.set_scenario(new_index)
    
    def toggle_auto_switch(self):
        """자동 전환 토글"""
        self.auto_switch_enabled = self.auto_switch_var.get()
        
        if self.auto_switch_enabled:
            self.add_log_message("자동 시나리오 전환 활성화 (30초 간격)")
            self.start_auto_switch_timer()
        else:
            self.add_log_message("자동 시나리오 전환 비활성화")
            if self.auto_timer:
                self.root.after_cancel(self.auto_timer)
                self.auto_timer = None
    
    def start_auto_switch_timer(self):
        """자동 전환 타이머 시작"""
        if self.auto_switch_enabled:
            # 다음 시나리오로 이동
            self.next_scenario()
            # 30초 후 다시 호출
            self.auto_timer = self.root.after(30000, self.start_auto_switch_timer)
    
    def clear_log(self):
        """로그 지우기"""
        self.log_text.delete("1.0", tk.END)
        self.add_log_message("로그가 지워졌습니다.")
    
    def save_log(self):
        """로그 저장"""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filename:
                log_content = self.log_text.get("1.0", tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.add_log_message(f"로그가 저장되었습니다: {filename}")
        except Exception as e:
            messagebox.showerror("오류", f"로그 저장 실패: {e}")
    
    def on_closing(self):
        """프로그램 종료 시 호출"""
        try:
            # 자동 전환 타이머 정리
            if self.auto_timer:
                self.root.after_cancel(self.auto_timer)
            
            # 서버 중지
            if self.server.running:
                self.server.stop()
            
            self.root.destroy()
        except Exception as e:
            print(f"종료 중 오류: {e}")
            self.root.destroy()

def main():
    """메인 함수"""
    # 설정 디렉토리 생성
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # GUI 시작
    root = tk.Tk()
    app = RFServerGUI(root)
    
    # 종료 이벤트 바인딩
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # 초기 로그 메시지
    app.add_log_message("=== RF Generator Test Server GUI (개선됨) ===")
    app.add_log_message("서버를 시작하려면 '서버 시작' 버튼을 클릭하세요.")
    app.add_log_message("지원되는 명령어:")
    app.add_log_message("- Device Status Request (0x10, 0x01)")
    app.add_log_message("- RF On/Off (0x00, 0x01/0x02)")
    app.add_log_message("- Set Power (0x07, 0x03)")
    app.add_log_message("- Control Mode (0x07, 0x01)")
    app.add_log_message("- 기타 프로토콜 명령어들...")
    app.add_log_message("클라이언트 상태는 IP 주소별로 관리됩니다.")
    
    # 시나리오 정보 출력
    scenario_names = app.server.scenario_manager.get_scenario_names()
    app.add_log_message(f"\n사용 가능한 시나리오 ({len(scenario_names)}개):")
    for i, name in enumerate(scenario_names):
        app.add_log_message(f"  {i}: {name}")
    
    app.add_log_message("\n테스트 모드:")
    app.add_log_message("- realistic: 현실적 노이즈와 물리적 특성 반영")
    app.add_log_message("- sine_wave: 사인파 기반 (계측기 검증용)")
    app.add_log_message("\n준비 완료!")
    
    # GUI 시작
    root.mainloop()

if __name__ == "__main__":
    main()
