"""
System Data Manager
시스템 제어 데이터 생성 및 파싱
"""

import struct


class SystemDataManager:
    """시스템 제어 데이터 생성 및 파싱"""
    
    # ========================================
    # Power Limits (8 floats = 32 bytes)
    # ========================================
    
    @staticmethod
    def create_power_limits_data(settings):
        """
        Power Limits 데이터 생성
        
        Args:
            settings (dict): {
                'user_power_limit': float,
                'low_power_limit': float,
                'max_power_limit': float,
                'user_reflected_power_limit': float,
                'max_reflected_power_limit': float,
                'user_ext_feedback_limit': float,
                'max_ext_feedback_value': float,
                'min_ext_feedback_value': float
            }
        
        Returns:
            tuple: (success, data, message)
        """
        try:
            data = struct.pack('<ffffffff',
                float(settings.get('user_power_limit', 0.0)),
                float(settings.get('low_power_limit', 0.0)),
                float(settings.get('max_power_limit', 0.0)),
                float(settings.get('user_reflected_power_limit', 0.0)),
                float(settings.get('max_reflected_power_limit', 0.0)),
                float(settings.get('user_ext_feedback_limit', 0.0)),
                float(settings.get('max_ext_feedback_value', 0.0)),
                float(settings.get('min_ext_feedback_value', 0.0))
            )
            
            if len(data) != 32:
                return False, None, f"Power Limits 데이터 길이 오류: {len(data)}바이트"
            
            return True, data, "Power Limits 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"Power Limits 데이터 생성 실패: {str(e)}"
    
    @staticmethod
    def parse_power_limits_data(data):
        """Power Limits 데이터 파싱"""
        try:
            if len(data) < 32:
                print(f"Power Limits 데이터 크기 부족: {len(data)}바이트 (기대: 32바이트)")
                return None
            
            values = struct.unpack('<ffffffff', data[:32])
            
            return {
                'user_power_limit': values[0],
                'low_power_limit': values[1],
                'max_power_limit': values[2],
                'user_reflected_power_limit': values[3],
                'max_reflected_power_limit': values[4],
                'user_ext_feedback_limit': values[5],
                'max_ext_feedback_value': values[6],
                'min_ext_feedback_value': values[7]
            }
            
        except Exception as e:
            print(f"Power Limits 파싱 오류: {e}")
            return None
    
    # ========================================
    # VA Limit (2 floats = 8 bytes)
    # ========================================
    
    @staticmethod
    def create_va_limit_data(settings):
        """
        VA Limit 데이터 생성
        
        Args:
            settings (dict): {
                'va_limit_1': float,
                'va_limit_2': float
            }
        
        Returns:
            tuple: (success, data, message)
        """
        try:
            data = struct.pack('<ff',
                float(settings.get('va_limit_1', 0.0)),
                float(settings.get('va_limit_2', 0.0))
            )
            
            if len(data) != 8:
                return False, None, f"VA Limit 데이터 길이 오류: {len(data)}바이트"
            
            return True, data, "VA Limit 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"VA Limit 데이터 생성 실패: {str(e)}"
    
    @staticmethod
    def parse_va_limit_data(data):
        """VA Limit 데이터 파싱"""
        try:
            if len(data) < 8:
                print(f"VA Limit 데이터 크기 부족: {len(data)}바이트 (기대: 8바이트)")
                return None
            
            values = struct.unpack('<ff', data[:8])
            
            return {
                'va_limit_1': values[0],
                'va_limit_2': values[1]
            }
            
        except Exception as e:
            print(f"VA Limit 파싱 오류: {e}")
            return None
    
    # ========================================
    # DCC Interface (28 bytes)
    # ========================================
    
    @staticmethod
    def create_dcc_control_data(dc_onoff):
        """
        DCC 제어 데이터 생성 (DC On/Off만)
        
        Args:
            dc_onoff (bool): DC 전원 On/Off
        
        Returns:
            tuple: (success, data, message)
        """
        try:
            data = struct.pack('<I', 1 if dc_onoff else 0)
            
            if len(data) != 4:
                return False, None, f"DCC Control 데이터 길이 오류: {len(data)}바이트"
            
            return True, data, "DCC Control 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"DCC Control 데이터 생성 실패: {str(e)}"
    
    @staticmethod
    def parse_dcc_interface_data(data):
        """
        DCC Interface 데이터 파싱
        
        Returns:
            dict: {
                'dc_onoff': bool,
                'dcc_status': int (32-bit),
                'dc_voltage': float,
                'dc_current': float,
                'pfc_current': float,
                'rf_amp_temp': float,
                'water_temp': float,
                'status_bits': dict (28 bits parsed)
            }
        """
        try:
            if len(data) < 28:
                print(f"DCC Interface 데이터 크기 부족: {len(data)}바이트 (기대: 28바이트)")
                return None
            
            offset = 0
            dcc_if = {}
            
            # uint32_t dc_onoff_set
            dcc_if['dc_onoff'] = bool(struct.unpack('<I', data[offset:offset+4])[0])
            offset += 4
            
            # uint32_t dcc_status (비트 필드)
            dcc_if['dcc_status'] = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            
            # float DCout_voltage
            dcc_if['dc_voltage'] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # float DCout_current
            dcc_if['dc_current'] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # float PFCout_currnt
            dcc_if['pfc_current'] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # float RFAmp_Temp
            dcc_if['rf_amp_temp'] = struct.unpack('<f', data[offset:offset+4])[0]
            offset += 4
            
            # float Waterplate_Temp
            dcc_if['water_temp'] = struct.unpack('<f', data[offset:offset+4])[0]
            
            # 비트 필드 파싱 (kgen_config.h Line 232-260 참조)
            status = dcc_if['dcc_status']
            dcc_if['status_bits'] = {
                'dc_status': bool(status & (1 << 0)),
                'pfc_status': bool(status & (1 << 1)),
                'interlock': bool(status & (1 << 2)),
                'ac_fail': bool(status & (1 << 3)),
                'fan1_fail': bool(status & (1 << 4)),
                'fan2_fail': bool(status & (1 << 5)),
                'over_amp_temper': bool(status & (1 << 6)),
                'over_water_temper': bool(status & (1 << 7)),
                'waterflow_fail': bool(status & (1 << 8)),
                'over_dc_out': bool(status & (1 << 9)),
                'over_pfc': bool(status & (1 << 10)),
                'over_pfc_vt': bool(status & (1 << 11)),
                'fan3_fail': bool(status & (1 << 12)),
                'fan4_fail': bool(status & (1 << 13)),
                'fan5_fail': bool(status & (1 << 14)),
                'fan6_fail': bool(status & (1 << 15)),
                'dcc_dcout_voltage': bool(status & (1 << 16)),
                'dcc_dcout_current': bool(status & (1 << 17)),
                'dcc_pfcout_current': bool(status & (1 << 18)),
                'dcc_rfamp_temp': bool(status & (1 << 19)),
                'dcc_waterplate_temp': bool(status & (1 << 20)),
                'gate_pa1_isens': bool(status & (1 << 21)),
                'gate_pa1_vsens': bool(status & (1 << 22)),
                'gate_pa1_temp': bool(status & (1 << 23)),
                'gate_pa2_isens': bool(status & (1 << 24)),
                'gate_pa2_vsens': bool(status & (1 << 25)),
                'gate_pa2_temp': bool(status & (1 << 26)),
                'gate_bias12': bool(status & (1 << 27))
            }
            
            return dcc_if
            
        except Exception as e:
            print(f"DCC Interface 파싱 오류: {e}")
            return None
    
    # ========================================
    # Ctlminmax_t (100 bytes = 24 floats + 1 uint32)
    # ========================================
    
    @staticmethod
    def create_ctlminmax_data(settings):
        """
        Ctlminmax_t 데이터 생성
        
        구조체 (kgen_config.h Line 252-272):
        - 5개 DCC floats
        - 3개 PA1 기본 + 4개 return + 4개 bias = 11 floats
        - 3개 PA2 기본 + 4개 return + 4개 bias = 11 floats
        - 1개 Enable_flag (uint32)
        총 27 floats + 1 uint32 = 112 bytes
        
        Args:
            settings (dict): 27개 float + 1개 enable_flag
        
        Returns:
            tuple: (success, data, message)
        """
        try:
            data = bytearray()
            
            # 정확한 필드 순서 (kgen_config.h Line 254-271)
            field_names = [
                # DCC (5개)
                'dcc_dcout_voltage', 
                'dcc_dcout_current', 
                'dcc_pfcout_current',
                'dcc_rfamp_temp', 
                'dcc_waterplate_temp',
                
                # PA1 (11개: 3 + 4 + 4)
                'gate_pa1_isens', 
                'gate_pa1_vsens', 
                'gate_pa1_temp',
                'gate_pa1_return_0', 
                'gate_pa1_return_1', 
                'gate_pa1_return_2', 
                'gate_pa1_return_3',
                'gate_pa1_bias_0', 
                'gate_pa1_bias_1', 
                'gate_pa1_bias_2', 
                'gate_pa1_bias_3',
                
                # PA2 (11개: 3 + 4 + 4)
                'gate_pa2_isens', 
                'gate_pa2_vsens', 
                'gate_pa2_temp',
                'gate_pa2_return_0', 
                'gate_pa2_return_1', 
                'gate_pa2_return_2', 
                'gate_pa2_return_3',
                'gate_pa2_bias_0',
                'gate_pa2_bias_1',
                'gate_pa2_bias_2',
                'gate_pa2_bias_3'
            ]
            
            # 27개 float 패킹
            for name in field_names:
                value = float(settings.get(name, 0.0))
                data.extend(struct.pack('<f', value))
            
            # Enable_flag (uint32_t)
            enable_flag = int(settings.get('enable_flag', 0))
            data.extend(struct.pack('<I', enable_flag))
            
            # 크기 검증: 27 floats * 4 + 1 uint32 * 4 = 112 bytes
            if len(data) != 112:
                return False, None, f"Ctlminmax 데이터 길이 오류: {len(data)}바이트 (기대: 112)"
            
            return True, bytes(data), "Ctlminmax 데이터 생성 완료"
            
        except Exception as e:
            return False, None, f"Ctlminmax 데이터 생성 실패: {str(e)}"
    
    @staticmethod
    def parse_ctlminmax_data(data):
        """Ctlminmax_t 데이터 파싱"""
        try:
            if len(data) < 112:
                print(f"Ctlminmax 데이터 크기 부족: {len(data)}바이트 (기대: 112바이트)")
                return None
            
            offset = 0
            result = {}
            
            # 정확한 필드 순서 (27개 float)
            field_names = [
                # DCC (5개)
                'dcc_dcout_voltage', 'dcc_dcout_current', 'dcc_pfcout_current',
                'dcc_rfamp_temp', 'dcc_waterplate_temp',
                
                # PA1 (11개)
                'gate_pa1_isens', 'gate_pa1_vsens', 'gate_pa1_temp',
                'gate_pa1_return_0', 'gate_pa1_return_1', 'gate_pa1_return_2', 'gate_pa1_return_3',
                'gate_pa1_bias_0', 'gate_pa1_bias_1', 'gate_pa1_bias_2', 'gate_pa1_bias_3',
                
                # PA2 (11개)
                'gate_pa2_isens', 'gate_pa2_vsens', 'gate_pa2_temp',
                'gate_pa2_return_0', 'gate_pa2_return_1', 'gate_pa2_return_2', 'gate_pa2_return_3',
                'gate_pa2_bias_0', 'gate_pa2_bias_1', 'gate_pa2_bias_2', 'gate_pa2_bias_3'
            ]
            
            # 27개 float 파싱
            for name in field_names:
                result[name] = struct.unpack('<f', data[offset:offset+4])[0]
                offset += 4
            
            # Enable_flag (uint32_t)
            result['enable_flag'] = struct.unpack('<I', data[offset:offset+4])[0]
            
            return result
            
        except Exception as e:
            print(f"Ctlminmax 파싱 오류: {e}")
            return None
            
    #########
    @staticmethod
    def create_gate_bias_data(settings):
        """
        Gate Bias 데이터 생성 (8 floats = 32 bytes)
        CMD=0x01, SUBCMD=0x0D (펌웨어 Line 692)
        """
        data = struct.pack('<ffffffff',
            float(settings.get('module1_bias_0', 0.0)),
            float(settings.get('module1_bias_1', 0.0)),
            float(settings.get('module1_bias_2', 0.0)),
            float(settings.get('module1_bias_3', 0.0)),
            float(settings.get('module2_bias_0', 0.0)),
            float(settings.get('module2_bias_1', 0.0)),
            float(settings.get('module2_bias_2', 0.0)),
            float(settings.get('module2_bias_3', 0.0))
        )
        return True, data, "Gate Bias 데이터 생성 완료"

    @staticmethod
    def parse_gate_bias_data(data):
        """Gate Bias 데이터 파싱"""
        values = struct.unpack('<ffffffff', data[:32])
        return {
            'module1_bias_0': values[0],
            'module1_bias_1': values[1],
            'module1_bias_2': values[2],
            'module1_bias_3': values[3],
            'module2_bias_0': values[4],
            'module2_bias_1': values[5],
            'module2_bias_2': values[6],
            'module2_bias_3': values[7]
        }