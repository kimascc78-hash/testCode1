import socket
import struct
import numpy as np
import threading
import time
import os
from collections import defaultdict

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

class TestScenarioManager:
    """테스트 시나리오 관리 클래스 - 다양한 상태 조합 테스트"""
    
    def __init__(self):
        self.current_scenario = 0
        self.scenarios = [
            self.normal_operation,
            self.high_forward_power_test,
            self.reflect_power_warning_test,
            self.reflect_power_error_test,
            self.temperature_warning_test,
            self.temperature_error_test,
            self.low_temperature_test,
            self.led_alarm_combination_test,
            self.multi_bit_alarm_test,
            self.all_systems_failure_test
        ]
        
    def get_current_scenario_data(self, base_status, current_time):
        """현재 시나리오에 따른 테스트 데이터 생성"""
        scenario_func = self.scenarios[self.current_scenario % len(self.scenarios)]
        return scenario_func(base_status, current_time)
    
    def normal_operation(self, status, t):
        """정상 운영 시나리오"""
        # StatusThresholds.FORWARD_POWER_CAUTION = 400W 미만으로 유지
        status["forward_power"] = 300 + 50 * np.sin(2 * np.pi * 0.5 * t)
        # StatusThresholds.REFLECT_POWER_WARNING = 20W 미만으로 유지  
        status["reflect_power"] = 10 + 5 * np.sin(2 * np.pi * 0.8 * t)
        # StatusThresholds.TEMPERATURE_WARNING = 50°C 미만으로 유지
        status["temperature"] = 35 + 5 * np.sin(2 * np.pi * 0.1 * t)
        # LED: AC Power ON, 나머지 정상
        status["led_state"] = 0x0021  # 비트 0(AC Power), 5(RF Output) ON
        # 알람: 모두 정상
        status["alarm_state"] = 0x0000
        return "정상 운영"
    
    def high_forward_power_test(self, status, t):
        """높은 Forward Power 테스트 - Caution 레벨"""
        # StatusThresholds.FORWARD_POWER_CAUTION = 400W 이상
        status["forward_power"] = 450 + 100 * np.sin(2 * np.pi * 0.3 * t)
        status["reflect_power"] = 15 + 3 * np.sin(2 * np.pi * 0.8 * t)
        status["temperature"] = 40 + 3 * np.sin(2 * np.pi * 0.1 * t)
        status["led_state"] = 0x0031  # Power Limit LED 추가
        status["alarm_state"] = 0x0000
        return "높은 Forward Power (Caution)"
    
    def reflect_power_warning_test(self, status, t):
        """Reflect Power 경고 레벨 테스트"""
        status["forward_power"] = 500 + 50 * np.sin(2 * np.pi * 0.5 * t)
        # StatusThresholds.REFLECT_POWER_WARNING = 20W 이상
        status["reflect_power"] = 25 + 10 * np.sin(2 * np.pi * 0.8 * t)
        status["temperature"] = 42 + 2 * np.sin(2 * np.pi * 0.1 * t)
        status["led_state"] = 0x0025  # Alarm LED 추가
        status["alarm_state"] = 0x0000
        return "Reflect Power 경고"
    
    def reflect_power_error_test(self, status, t):
        """Reflect Power 오류 레벨 테스트"""
        status["forward_power"] = 600 + 100 * np.sin(2 * np.pi * 0.5 * t)
        # StatusThresholds.REFLECT_POWER_ERROR = 50W 이상
        status["reflect_power"] = 60 + 20 * np.sin(2 * np.pi * 0.8 * t)
        status["temperature"] = 45 + 3 * np.sin(2 * np.pi * 0.1 * t)
        status["led_state"] = 0x0027  # Alarm + Interlock LED
        status["alarm_state"] = 0x0080  # Max Power Limit 알람
        return "Reflect Power 오류"
    
    def temperature_warning_test(self, status, t):
        """온도 경고 레벨 테스트"""
        status["forward_power"] = 400 + 50 * np.sin(2 * np.pi * 0.5 * t)
        status["reflect_power"] = 18 + 5 * np.sin(2 * np.pi * 0.8 * t)
        # StatusThresholds.TEMPERATURE_WARNING = 50°C 이상
        status["temperature"] = 55 + 5 * np.sin(2 * np.pi * 0.1 * t)
        status["led_state"] = 0x002D  # Over Temp LED 추가
        status["alarm_state"] = 0x0400  # Over Temp 알람 (비트 10)
        return "온도 경고"
    
    def temperature_error_test(self, status, t):
        """온도 오류 레벨 테스트"""
        status["forward_power"] = 350 + 30 * np.sin(2 * np.pi * 0.5 * t)
        status["reflect_power"] = 15 + 3 * np.sin(2 * np.pi * 0.8 * t)
        # StatusThresholds.TEMPERATURE_ERROR = 70°C 이상
        status["temperature"] = 75 + 5 * np.sin(2 * np.pi * 0.1 * t)
        status["led_state"] = 0x002F  # Over Temp + 기타 LED
        status["alarm_state"] = 0x0600  # Over Temp + Fan Fail
        return "온도 위험"
    
    def low_temperature_test(self, status, t):
        """저온 테스트 - Special 상태"""
        status["forward_power"] = 200 + 50 * np.sin(2 * np.pi * 0.5 * t)
        status["reflect_power"] = 8 + 2 * np.sin(2 * np.pi * 0.8 * t)
        # StatusThresholds.TEMPERATURE_LOW = 20°C 미만
        status["temperature"] = 15 + 3 * np.sin(2 * np.pi * 0.1 * t)
        status["led_state"] = 0x0021  # 기본 LED
        status["alarm_state"] = 0x0000
        return "저온 환경"
    
    def led_alarm_combination_test(self, status, t):
        """LED 및 알람 조합 테스트"""
        status["forward_power"] = 500 + 50 * np.sin(2 * np.pi * 0.5 * t)
        status["reflect_power"] = 30 + 10 * np.sin(2 * np.pi * 0.8 * t)
        status["temperature"] = 48 + 5 * np.sin(2 * np.pi * 0.1 * t)
        # 여러 LED 조합 테스트
        status["led_state"] = 0x003F  # 모든 LED 활성화
        # 단일 비트 알람들 조합
        status["alarm_state"] = 0x02C0  # PFC Fail + Gate Driver + Fan Fail
        return "LED/알람 조합"
    
    def multi_bit_alarm_test(self, status, t):
        """다중 비트 알람 필드 테스트"""
        status["forward_power"] = 400 + 100 * np.sin(2 * np.pi * 0.5 * t)
        status["reflect_power"] = 25 + 8 * np.sin(2 * np.pi * 0.8 * t)
        status["temperature"] = 52 + 8 * np.sin(2 * np.pi * 0.1 * t)
        status["led_state"] = 0x0027  # Interlock + Alarm + AC Power
        # 다중 비트 필드 테스트
        status["alarm_state"] = (
            0x0003 |  # AUX Power Vol (비트 0-2): 값 3
            0x0018 |  # AC Phase (비트 3-5): 값 3  
            0x7800 |  # Interlock (비트 11-14): 값 15
            0x8000    # Under FWD Power (비트 15)
        )
        return "다중 비트 알람"
    
    def all_systems_failure_test(self, status, t):
        """전체 시스템 장애 테스트"""
        status["forward_power"] = 800 + 100 * np.sin(2 * np.pi * 0.5 * t)
        status["reflect_power"] = 80 + 20 * np.sin(2 * np.pi * 0.8 * t)
        status["temperature"] = 85 + 10 * np.sin(2 * np.pi * 0.1 * t)
        # 모든 LED 문제 상태
        status["led_state"] = 0x001E  # AC Power OFF, 나머지 문제 상태
        # 모든 알람 활성화
        status["alarm_state"] = 0xFFFF  # 16비트 모두 활성화
        return "전체 시스템 장애"

class RFServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
            "led_state": 0x0001,  # 초기값: 비트 0 (AC Power) ON
            "alarm_state": 0x0001  # 초기값: 비트 0 (PFC Fail) ON
        })
        self.running = True
        self.global_frame_count = 0
        self.frame_count_lock = threading.Lock()
        
        # 테스트 시나리오 매니저 추가
        self.scenario_manager = TestScenarioManager()
        self.auto_switch = True  # 자동 전환 활성화 플래그
        
        # 시나리오 전환 타이머 추가 (30초마다 시나리오 변경)
        self.scenario_timer = threading.Timer(30.0, self.switch_scenario)
        self.scenario_timer.daemon = True
        self.scenario_timer.start()
        
        # 키보드 입력 처리 스레드
        self.keyboard_thread = threading.Thread(target=self.keyboard_input_handler, daemon=True)
        self.keyboard_thread.start()

    def get_client_key(self, addr):
        ip, port = addr
        return ip

    def keyboard_input_handler(self):
        """키보드 입력 처리 스레드"""
        import sys
        
        print("\n=== 키보드 컨트롤 ===")
        print("숫자 키 (0-9): 시나리오 직접 선택")
        print("a: 자동 전환 ON/OFF 토글")
        print("n: 다음 시나리오")
        print("p: 이전 시나리오") 
        print("s: 현재 상태 표시")
        print("h: 도움말 표시")
        print("q: 서버 종료")
        print("==================\n")
        
        while self.running:
            try:
                # 크로스 플랫폼 키보드 입력
                if sys.platform.startswith('win'):
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8').lower()
                        self.process_keyboard_input(key)
                else:
                    # Linux/Mac용 - select 사용
                    import select
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1).lower()
                        self.process_keyboard_input(key)
                
                time.sleep(0.1)  # CPU 사용률 제한
                
            except Exception as e:
                print(f"[키보드] 입력 처리 오류: {e}")
                time.sleep(1)
    
    def process_keyboard_input(self, key):
        """키보드 입력 처리"""
        try:
            total_scenarios = len(self.scenario_manager.scenarios)
            
            # 숫자 키 - 시나리오 직접 선택
            if key.isdigit():
                scenario_num = int(key)
                if 0 <= scenario_num < total_scenarios:
                    self.scenario_manager.current_scenario = scenario_num
                    scenario_name = self.get_scenario_name(scenario_num)
                    print(f"\n[키보드] 시나리오 {scenario_num + 1} 선택: {scenario_name}")
                    self.display_current_scenario()
                else:
                    print(f"\n[키보드] 잘못된 시나리오 번호: {scenario_num} (0-{total_scenarios-1} 사용 가능)")
            
            # 자동 전환 토글
            elif key == 'a':
                self.auto_switch = not self.auto_switch
                status = "활성화" if self.auto_switch else "비활성화"
                print(f"\n[키보드] 자동 전환 {status}")
                
                if self.auto_switch:
                    # 자동 전환 재시작
                    if hasattr(self, 'scenario_timer'):
                        self.scenario_timer.cancel()
                    self.scenario_timer = threading.Timer(30.0, self.switch_scenario)
                    self.scenario_timer.daemon = True
                    self.scenario_timer.start()
                else:
                    # 자동 전환 중지
                    if hasattr(self, 'scenario_timer'):
                        self.scenario_timer.cancel()
            
            # 다음 시나리오
            elif key == 'n':
                self.scenario_manager.current_scenario = (self.scenario_manager.current_scenario + 1) % total_scenarios
                scenario_name = self.get_scenario_name(self.scenario_manager.current_scenario)
                print(f"\n[키보드] 다음 시나리오: {scenario_name}")
                self.display_current_scenario()
            
            # 이전 시나리오
            elif key == 'p':
                self.scenario_manager.current_scenario = (self.scenario_manager.current_scenario - 1) % total_scenarios
                scenario_name = self.get_scenario_name(self.scenario_manager.current_scenario)
                print(f"\n[키보드] 이전 시나리오: {scenario_name}")
                self.display_current_scenario()
            
            # 현재 상태 표시
            elif key == 's':
                self.display_current_scenario()
                self.display_scenario_list()
            
            # 도움말
            elif key == 'h':
                self.display_help()
            
            # 서버 종료
            elif key == 'q':
                print("\n[키보드] 서버 종료 요청...")
                self.stop()
                return
            
            else:
                print(f"\n[키보드] 알 수 없는 키: '{key}' (h: 도움말)")
                
        except Exception as e:
            print(f"[키보드] 처리 오류: {e}")
    
    def get_scenario_name(self, scenario_index):
        """시나리오 이름 반환"""
        scenario_names = [
            "정상 운영",
            "높은 Forward Power (Caution)",
            "Reflect Power 경고",
            "Reflect Power 오류",
            "온도 경고",
            "온도 위험",
            "저온 환경",
            "LED/알람 조합",
            "다중 비트 알람",
            "전체 시스템 장애"
        ]
        return scenario_names[scenario_index] if scenario_index < len(scenario_names) else f"시나리오 {scenario_index}"
    
    def display_current_scenario(self):
        """현재 시나리오 정보 표시"""
        current = self.scenario_manager.current_scenario
        total = len(self.scenario_manager.scenarios)
        scenario_name = self.get_scenario_name(current)
        auto_status = "ON" if self.auto_switch else "OFF"
        
        print(f"\n=== 현재 시나리오 ===")
        print(f"번호: {current} ({current + 1}/{total})")
        print(f"이름: {scenario_name}")
        print(f"자동 전환: {auto_status}")
        print(f"==================")
    
    def display_scenario_list(self):
        """시나리오 목록 표시"""
        print(f"\n=== 시나리오 목록 ===")
        for i in range(len(self.scenario_manager.scenarios)):
            current_mark = " ★" if i == self.scenario_manager.current_scenario else "  "
            scenario_name = self.get_scenario_name(i)
            print(f"{i}: {scenario_name}{current_mark}")
        print(f"===================")
    
    def display_help(self):
        """도움말 표시"""
        print(f"\n=== 키보드 컨트롤 도움말 ===")
        print(f"숫자 키 (0-9): 시나리오 직접 선택")
        print(f"a: 자동 전환 ON/OFF 토글 (현재: {'ON' if self.auto_switch else 'OFF'})")
        print(f"n: 다음 시나리오")
        print(f"p: 이전 시나리오")
        print(f"s: 현재 상태 및 시나리오 목록 표시")
        print(f"h: 이 도움말 표시")
        print(f"q: 서버 종료")
        print(f"===========================")
        self.display_scenario_list()

    def switch_scenario(self):
        """자동 시나리오 전환"""
        if not self.auto_switch:
            return  # 자동 전환이 비활성화된 경우 리턴
            
        self.scenario_manager.current_scenario += 1
        total_scenarios = len(self.scenario_manager.scenarios)
        current = self.scenario_manager.current_scenario % total_scenarios
        scenario_name = self.get_scenario_name(current)
        
        print(f"\n[자동전환] 시나리오 {current + 1}/{total_scenarios}: {scenario_name}")
        
        # 다음 자동 전환 예약 (자동 전환이 활성화된 경우만)
        if self.auto_switch:
            self.scenario_timer = threading.Timer(30.0, self.switch_scenario)
            self.scenario_timer.daemon = True  
            self.scenario_timer.start()

    def start(self):
        try:
            self.server.bind((self.host, self.port))
            self.server.listen(MAX_CLIENTS)
            print(f"RF Test Server started on {self.host}:{self.port}")
            print("Supported commands:")
            print("- Device Status Request (0x10, 0x01)")
            print("- RF On/Off (0x00, 0x01/0x02)")
            print("- Set Power (0x07, 0x03)")
            print("- Control Mode (0x07, 0x01)")
            print("- Regulation Mode (0x01, 0x02)")
            print("- Ramp Configuration (0x01, 0x0B)")
            print("- CEX Configuration (0x01, 0x0C)")
            print("- Pulse Settings (0x02, various)")
            print("- RF Frequency (0x04, 0x09)")
            print("- Frequency Tuning (0x04, various)")
            print("- Alarm Clear (0x04, 0x15)")
            print("★ Client states managed by IP address only")
        except Exception as e:
            print(f"Failed to start server: {e}")
            return

        while self.running:
            try:
                self.server.settimeout(1.0)
                client, addr = self.server.accept()
                client.settimeout(SOCKET_TIMEOUT)
                print(f"New client connected from {addr}")
                self.clients.append(client)
                threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Server error: {e}")

    def handle_client(self, client, addr):
        client_key = self.get_client_key(addr)
        client_state = self.client_states[client_key]
        print(f"[SERVER] Client {addr} using state key: {client_key}")
        
        while self.running:
            try:
                data = client.recv(64)
                if not data:
                    if client in self.clients:
                        self.clients.remove(client)
                    client.close()
                    print(f"Client disconnected from {addr}")
                    break
                
                with self.frame_count_lock:
                    self.global_frame_count += 1
                    client_state["frame_count"] += 1
                
                parsed = RFProtocol.parse_frame(data)
                
                if not parsed:
                    print(f"Invalid frame from {addr}: hex={data.hex()}")
                    continue

                response = None
                cmd, subcmd = parsed["cmd"], parsed["subcmd"]

                if cmd == RFProtocol.CMD_DEVICE_STATUS_GET and subcmd == RFProtocol.SUBCMD_DEVICE_STATUS:
                    status = self.create_complete_status(client_state, time.time())
                    response = RFProtocol.create_frame(cmd, subcmd, self.create_status_response(status))

                elif cmd == RFProtocol.CMD_RF_ON and subcmd == RFProtocol.SUBCMD_RF_ON:
                    client_state["rf_enabled"] = True
                    print(f"[SERVER] RF On for {addr} (key: {client_key})")
                    response = RFProtocol.create_frame(cmd, subcmd, struct.pack('<B', 0))

                elif cmd == RFProtocol.CMD_RF_OFF and subcmd == RFProtocol.SUBCMD_RF_OFF:
                    client_state["rf_enabled"] = False
                    print(f"[SERVER] RF Off for {addr} (key: {client_key})")
                    response = RFProtocol.create_frame(cmd, subcmd, struct.pack('<B', 0))

                else:
                    # 기타 명령어들에 대한 기본 응답
                    response = RFProtocol.create_frame(cmd, subcmd if subcmd else 0, struct.pack('<B', 0))

                if response:
                    client.sendall(response)
                    
            except Exception as e:
                print(f"Error handling client {addr}: {e}")
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
        """완전한 상태 데이터 생성 - 시나리오 기반"""
        t = (current_time - client_state["start_time"]) % 30  # 30초 주기
        
        # 기본 상태 생성
        status = {
            "rf_on_off": 1 if client_state["rf_enabled"] else 0,
            "set_power": client_state["set_power"],
            "control_mode": client_state["control_mode"],
            "alarm_state": client_state["alarm_state"],
            "forward_power": 500.0,
            "reflect_power": 50.0,
            "delivery_power": 450.0,
            "frequency": float(client_state["rf_frequency"]),
            "gamma": 0.5,
            "real_gamma": 0.25,
            "image_gamma": 0.15,
            "rf_phase": 0.0,
            "temperature": 40.0,
            "system_state": 0x0000,
            "led_state": 0x0001,
            "firmware_version": 1.22
        }
        
        # 현재 시나리오 적용
        scenario_name = self.scenario_manager.get_current_scenario_data(status, t)
        
        # Delivery Power 계산 (Forward - Reflect)
        status["delivery_power"] = max(0, status["forward_power"] - status["reflect_power"])
        
        # 주기적으로 시나리오 정보 출력 (10초마다)
        if int(t) % 10 == 0:
            print(f"[SCENARIO] 현재: {scenario_name}")
            print(f"  Forward Power: {status['forward_power']:.1f}W")
            print(f"  Reflect Power: {status['reflect_power']:.1f}W") 
            print(f"  Temperature: {status['temperature']:.1f}°C")
            print(f"  LED State: 0x{status['led_state']:04X}")
            print(f"  Alarm State: 0x{status['alarm_state']:04X}")
        
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
            print(f"[ERROR] 상태 데이터 길이 오류: 기댓값={expected_length}, 실제값={len(data)}")
            while len(data) < expected_length:
                data.extend(b'\x00')
            data = data[:expected_length]
        
        return data

    def stop(self):
        """서버 정지 - 타이머 및 스레드 정리 포함"""
        print("\n[서버] 종료 중...")
        self.running = False
        
        # 시나리오 타이머 정리
        if hasattr(self, 'scenario_timer'):
            self.scenario_timer.cancel()
        
        # 키보드 스레드는 daemon=True로 설정되어 자동 종료됨
        
        # 기존 정리 코드
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        
        try:
            self.server.close()
        except:
            pass
            
        print("[서버] RF Test Server stopped")

# 사용법 개선
if __name__ == "__main__":
    import sys
    
    # Linux/Mac에서 키보드 입력을 위한 설정
    if not sys.platform.startswith('win'):
        import termios, tty
        
        # 터미널 설정 저장
        old_settings = termios.tcgetattr(sys.stdin)
        
        def restore_terminal():
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        
        # 프로그램 종료 시 터미널 설정 복원
        import atexit
        atexit.register(restore_terminal)
        
        # 즉시 입력 모드 설정
        tty.setraw(sys.stdin.fileno())
    
    os.makedirs(CONFIG_DIR, exist_ok=True)
    server = RFServer()
    
    print("\n=== RF Generator Enhanced Test Server ===")
    print("임계값 및 상수 설정 테스트를 위한 대화형 시나리오 서버")
    print("\n시나리오 목록:")
    for i in range(10):
        scenario_names = [
            "정상 운영 (모든 값 정상 범위)",
            "높은 Forward Power (Caution 레벨)", 
            "Reflect Power 경고",
            "Reflect Power 오류",
            "온도 경고", 
            "온도 위험",
            "저온 환경",
            "LED/알람 조합",
            "다중 비트 알람",
            "전체 시스템 장애"
        ]
        print(f"{i}: {scenario_names[i]}")
    
    print(f"\n키보드 제어:")
    print(f"- 숫자 키 (0-9): 시나리오 즉시 선택")
    print(f"- a: 자동 전환 ON/OFF")
    print(f"- n/p: 다음/이전 시나리오")
    print(f"- s: 현재 상태 표시")
    print(f"- h: 도움말")
    print(f"- q: 서버 종료")
    print(f"\n자동 전환: 30초마다 (a키로 토글 가능)")
    print(f"=========================================\n")
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[Ctrl+C] 서버 종료 요청...")
        server.stop()
    finally:
        # Linux/Mac 터미널 설정 복원
        if not sys.platform.startswith('win'):
            try:
                restore_terminal()
            except:
                pass
