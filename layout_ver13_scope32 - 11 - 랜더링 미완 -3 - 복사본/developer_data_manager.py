"""
Developer Data Manager
개발자 명령어 데이터 생성 클래스
"""

import struct


class DeveloperDataManager:
    """개발자 명령어 데이터 생성 및 파싱"""
    
    # ========================================
    # Arc Management
    # ========================================
    
    @staticmethod
    def create_arc_management_data(settings):
        """
        Arc Management 설정 데이터 생성
        
        Args:
            settings (dict): {
                'en_reflected_arc_det': bool,
                'en_external_arc_input': bool,
                'rfpower_latch_state': bool,
                'en_arc_output_signal': bool,
                'suppression_time': int (0 or 5~511 μs),
                'initial_delay_time': int (0~10000 ms),
                'setpoint_delay_time': int (0~245 ms),
                'no_of_attempts': int (0=unlimited, 1~250),
                'reflected_arc_threshold': float
            }
        
        Returns:
            tuple: (success, data, message)
        """
        try:
            data = bytearray()
            
            # uint8_t en_reflected_arc_det
            data.extend(struct.pack('<B', 1 if settings.get('en_reflected_arc_det', False) else 0))
            
            # uint8_t en_external_arc_input
            data.extend(struct.pack('<B', 1 if settings.get('en_external_arc_input', False) else 0))
            
            # uint8_t rfpower_latch_state (0=Turn Off, 1=Turn On)
            data.extend(struct.pack('<B', 1 if settings.get('rfpower_latch_state', False) else 0))
            
            # uint8_t en_arc_output_signal
            data.extend(struct.pack('<B', 1 if settings.get('en_arc_output_signal', False) else 0))
            
            # uint16_t suppression_time
            data.extend(struct.pack('<H', int(settings.get('suppression_time', 0))))
            
            # uint16_t initial_delay_time
            data.extend(struct.pack('<H', int(settings.get('initial_delay_time', 0))))
            
            # uint16_t setpoint_delay_time
            data.extend(struct.pack('<H', int(settings.get('setpoint_delay_time', 0))))
            
            # uint16_t no_of_attempts
            data.extend(struct.pack('<H', int(settings.get('no_of_attempts', 0))))
            
            # float reflected_arc_threshold
            data.extend(struct.pack('<f', float(settings.get('reflected_arc_threshold', 0.0))))
            
            if len(data) != 16:
                return False, None, f"Arc Management 데이터 길이 오류: {len(data)}바이트"
            
            return True, bytes(data), "Arc Management 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"Arc Management 데이터 생성 실패: {str(e)}"
    
    @staticmethod
    def parse_arc_management_data(data):
        """Arc Management 데이터 파싱"""
        try:
            if len(data) < 16:
                return None
            
            settings = {}
            offset = 0
            
            settings['en_reflected_arc_det'] = struct.unpack('<B', data[offset:offset+1])[0] == 1
            offset += 1
            
            settings['en_external_arc_input'] = struct.unpack('<B', data[offset:offset+1])[0] == 1
            offset += 1
            
            settings['rfpower_latch_state'] = struct.unpack('<B', data[offset:offset+1])[0] == 1
            offset += 1
            
            settings['en_arc_output_signal'] = struct.unpack('<B', data[offset:offset+1])[0] == 1
            offset += 1
            
            settings['suppression_time'] = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            settings['initial_delay_time'] = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            settings['setpoint_delay_time'] = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            settings['no_of_attempts'] = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            settings['reflected_arc_threshold'] = struct.unpack('<f', data[offset:offset+4])[0]
            
            return settings
            
        except Exception as e:
            print(f"Arc Management 파싱 오류: {e}")
            return None
    
    # ========================================
    # Device Manager
    # ========================================
    
    @staticmethod
    def parse_device_manager_data(data):
        """
        Device Manager 데이터 파싱
        
        Returns:
            dict: {
                'model_name': str,
                'serial_no': str,
                'production_date': str,
                'hw_version': str,
                'fw_version': str
            }
        """
        try:
            if len(data) < 132:  # 32+12+24+32+32
                return None
            
            device_info = {}
            offset = 0
            
            # char modelname[32]
            device_info['model_name'] = data[offset:offset+32].decode('utf-8', errors='ignore').rstrip('\x00')
            offset += 32
            
            # char serialNo[12]
            device_info['serial_no'] = data[offset:offset+12].decode('utf-8', errors='ignore').rstrip('\x00')
            offset += 12
            
            # char productiondate[24]
            device_info['production_date'] = data[offset:offset+24].decode('utf-8', errors='ignore').rstrip('\x00')
            offset += 24
            
            # char hw_version[32]
            device_info['hw_version'] = data[offset:offset+32].decode('utf-8', errors='ignore').rstrip('\x00')
            offset += 32
            
            # char fw_version[32]
            device_info['fw_version'] = data[offset:offset+32].decode('utf-8', errors='ignore').rstrip('\x00')
            
            return device_info
            
        except Exception as e:
            print(f"Device Manager 파싱 오류: {e}")
            return None
    
    # ========================================
    # System Control
    # ========================================
    
    @staticmethod
    def create_save_config_data(config_type):
        """
        Config 저장 데이터 생성
        
        Args:
            config_type (int): 0=Kgen Config, 1=VIZ Config
        
        Returns:
            tuple: (success, data, message)
        """
        try:
            data = bytearray()
            data.extend(struct.pack('<B', 0x00))  # SUBCMD
            data.extend(struct.pack('<B', config_type))  # 0 or 1
            
            return True, bytes(data), f"Config 저장 데이터 생성 완료 (type={config_type})"
            
        except Exception as e:
            return False, None, f"Config 저장 데이터 생성 실패: {str(e)}"
    
    # ========================================
    # DDS Control 파싱
    # ========================================
    
    @staticmethod
    def parse_dds_control_data(data):
        """DDS Control 데이터 파싱"""
        try:
            if len(data) < 24:
                print(f"DDS 데이터 크기 부족: {len(data)}바이트 (기대: 24바이트)")
                return None
            
            settings = {}
            offset = 0
            
            # uint32_t DDS_Ch0_AmpGain
            settings['dds_ch0_amp_gain'] = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            
            # uint32_t DDS_Ch1_AmpGain
            settings['dds_ch1_amp_gain'] = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            
            # float DDS_Ch0_phaseoffset
            settings['dds_ch0_phase_offset'] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # float DDS_Ch1_phaseoffset
            settings['dds_ch1_phase_offset'] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # int32_t DDS_rf_freqoffset
            settings['dds_rf_freqoffset'] = struct.unpack('<i', data[offset:offset+4])[0]
            offset += 4
            
            # uint16_t SetAutoRFoffset
            settings['set_auto_rf_offset'] = struct.unpack('<H', data[offset:offset+2])[0]
            # offset += 2
            
            # uint16_t dummy_switch (skip)
            
            return settings
            
        except Exception as e:
            print(f"DDS Control 파싱 오류: {e}")
            return None
    
    # ========================================
    # AGC Setup 파싱
    # ========================================
    
    @staticmethod
    def parse_agc_setup_data(data):
        """AGC Setup 데이터 파싱"""
        try:
            if len(data) < 32:
                print(f"AGC 데이터 크기 부족: {len(data)}바이트 (기대: 32바이트)")
                return None
            
            settings = {}
            offset = 0
            
            # uint16_t AGCOnOff
            settings['agc_onoff'] = struct.unpack('<H', data[offset:offset+2])[0] == 1
            offset += 2
            
            # uint16_t RefSetupTime
            settings['ref_setup_time'] = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            # uint16_t AgcSetuptime[4]
            for i in range(4):
                settings[f'agc_setup_time_{i}'] = struct.unpack('<H', data[offset:offset+2])[0]
                offset += 2
            
            # float sensorgainrates[4]
            for i in range(4):
                settings[f'sensor_gain_rate_{i}'] = struct.unpack('<f', data[offset:offset+4])[0]
                offset += 4
            
            # float InitPowerGain
            settings['init_power_gain'] = struct.unpack('<f', data[offset:offset+4])[0]
            
            return settings
            
        except Exception as e:
            print(f"AGC Setup 파싱 오류: {e}")
            return None
    
    # ========================================
    # Fast Data Acquisition 파싱
    # ========================================
    
    @staticmethod
    def parse_fast_acq_data(data):
        """Fast Data Acquisition 데이터 파싱"""
        try:
            if len(data) < 8:
                print(f"Fast Acq 데이터 크기 부족: {len(data)}바이트 (기대: 8바이트)")
                return None
            
            settings = {}
            
            settings['memory_type'] = data[0]
            settings['trigger_source'] = data[1]
            settings['trigger_position'] = data[2]
            settings['control'] = data[3]
            settings['sample_rate'] = struct.unpack('<I', data[4:8])[0]
            
            return settings
            
        except Exception as e:
            print(f"Fast Acquisition 파싱 오류: {e}")
            return None
            
    # ========================================
    # SDD Config
    # ========================================

    @staticmethod
    def create_sdd_config_data(settings):
        """SDD Config 데이터 생성"""
        try:
            data = bytearray()
            
            # uint16_t GUI_model
            data.extend(struct.pack('<H', int(settings.get('gui_model', 1))))
            
            # uint16_t pulsing_freq_duty_count
            data.extend(struct.pack('<H', int(settings.get('pulsing_count', 100))))
            
            return True, bytes(data), "SDD Config 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"SDD Config 데이터 생성 실패: {str(e)}"

    @staticmethod
    def parse_sdd_config_data(data):
        """SDD Config 데이터 파싱"""
        try:
            if len(data) < 4:
                print(f"SDD 데이터 크기 부족: {len(data)}바이트 (기대: 4바이트)")
                return None
            
            settings = {}
            offset = 0
            
            # uint16_t GUI_model
            settings['gui_model'] = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            # uint16_t pulsing_freq_duty_count
            settings['pulsing_count'] = struct.unpack('<H', data[offset:offset+2])[0]
            
            return settings
            
        except Exception as e:
            print(f"SDD Config 파싱 오류: {e}")
            return None
    
    # ========================================
    # DDS Control
    # ========================================
    
    @staticmethod
    def create_dds_control_data(settings):
        """DDS Control 데이터 생성"""
        try:
            data = bytearray()
            
            # uint32_t DDS_Ch0_AmpGain
            data.extend(struct.pack('<I', int(settings.get('dds_ch0_amp_gain', 1024))))
            
            # uint32_t DDS_Ch1_AmpGain
            data.extend(struct.pack('<I', int(settings.get('dds_ch1_amp_gain', 1024))))
            
            # float DDS_Ch0_phaseoffset (CEX)
            data.extend(struct.pack('<f', float(settings.get('dds_ch0_phase_offset', 0.0))))
            
            # float DDS_Ch1_phaseoffset (RF)
            data.extend(struct.pack('<f', float(settings.get('dds_ch1_phase_offset', 0.0))))
            
            # int32_t DDS_rf_freqoffset
            data.extend(struct.pack('<i', int(settings.get('dds_rf_freqoffset', 0))))
            
            # uint16_t SetAutoRFoffset
            data.extend(struct.pack('<H', int(settings.get('set_auto_rf_offset', 0))))
            
            # uint16_t dummy_switch
            data.extend(struct.pack('<H', 0))
            
            return True, bytes(data), "DDS Control 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"DDS Control 데이터 생성 실패: {str(e)}"
    
    # ========================================
    # AGC Setup
    # ========================================
    
    @staticmethod
    def create_agc_setup_data(settings):
        """AGC Setup 데이터 생성"""
        try:
            data = bytearray()
            
            # uint16_t AGCOnOff
            data.extend(struct.pack('<H', 1 if settings.get('agc_onoff', False) else 0))
            
            # uint16_t RefSetupTime
            data.extend(struct.pack('<H', int(settings.get('ref_setup_time', 0))))
            
            # uint16_t AgcSetuptime[4]
            for i in range(4):
                data.extend(struct.pack('<H', int(settings.get(f'agc_setup_time_{i}', 0))))
            
            # float sensorgainrates[4]
            for i in range(4):
                data.extend(struct.pack('<f', float(settings.get(f'sensor_gain_rate_{i}', 0.0))))
            
            # float InitPowerGain
            data.extend(struct.pack('<f', float(settings.get('init_power_gain', 1.0))))
            
            return True, bytes(data), "AGC Setup 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"AGC Setup 데이터 생성 실패: {str(e)}"
    
    # ========================================
    # Fast Data Acquisition
    # ========================================
    
    @staticmethod
    def create_fast_acq_data(settings):
        """Fast Data Acquisition 데이터 생성"""
        try:
            data = bytearray()
            
            # uint8_t memory_type
            data.append(int(settings.get('memory_type', 0)))
            
            # uint8_t trigger_source
            data.append(int(settings.get('trigger_source', 0)))
            
            # uint8_t trigger_position
            data.append(int(settings.get('trigger_position', 0)))
            
            # uint8_t control
            data.append(int(settings.get('control', 0)))
            
            # uint32_t sample_rate
            data.extend(struct.pack('<I', int(settings.get('sample_rate', 10000))))
            
            return True, bytes(data), "Fast Acquisition 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"Fast Acquisition 데이터 생성 실패: {str(e)}"
            
            
    # ========================================
    # DCC Gate Bias Control
    # ========================================
    
    @staticmethod
    def create_dcc_gate_max_data(value):
        """
        DCC Gate Max 데이터 생성
        
        Args:
            value (float): Gate Max 값
        
        Returns:
            tuple: (success, data, message)
        """
        try:
            data = struct.pack('<f', float(value))
            
            if len(data) != 4:
                return False, None, f"DCC Gate Max 데이터 길이 오류: {len(data)}바이트"
            
            return True, data, "DCC Gate Max 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"DCC Gate Max 데이터 생성 실패: {str(e)}"
    
    @staticmethod
    def create_dcc_gate_min_data(value):
        """
        DCC Gate Min 데이터 생성
        
        Args:
            value (float): Gate Min 값
        
        Returns:
            tuple: (success, data, message)
        """
        try:
            data = struct.pack('<f', float(value))
            
            if len(data) != 4:
                return False, None, f"DCC Gate Min 데이터 길이 오류: {len(data)}바이트"
            
            return True, data, "DCC Gate Min 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"DCC Gate Min 데이터 생성 실패: {str(e)}"
    
    @staticmethod
    def create_dcc_factor_a_data(value):
        """
        DCC Factor A 데이터 생성
        
        Args:
            value (float): Factor A 값
        
        Returns:
            tuple: (success, data, message)
        """
        try:
            data = struct.pack('<f', float(value))
            
            if len(data) != 4:
                return False, None, f"DCC Factor A 데이터 길이 오류: {len(data)}바이트"
            
            return True, data, "DCC Factor A 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"DCC Factor A 데이터 생성 실패: {str(e)}"
    
    @staticmethod
    def create_dcc_factor_b_data(value):
        """
        DCC Factor B 데이터 생성
        
        Args:
            value (float): Factor B 값
        
        Returns:
            tuple: (success, data, message)
        """
        try:
            data = struct.pack('<f', float(value))
            
            if len(data) != 4:
                return False, None, f"DCC Factor B 데이터 길이 오류: {len(data)}바이트"
            
            return True, data, "DCC Factor B 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"DCC Factor B 데이터 생성 실패: {str(e)}"
    
    @staticmethod
    def parse_dcc_gate_bias_data(data):
        """
        DCC Gate Bias 단일 값 파싱 (GET 응답용)
        
        Args:
            data (bytes): 응답 데이터 (4바이트 float)
        
        Returns:
            float or None: 파싱된 값, 실패 시 None
        """
        try:
            if len(data) < 4:
                print(f"DCC Gate Bias 데이터 크기 부족: {len(data)}바이트 (기대: 4바이트)")
                return None
            
            value = struct.unpack('<f', data[:4])[0]
            return value
            
        except Exception as e:
            print(f"DCC Gate Bias 파싱 오류: {e}")
            return None        