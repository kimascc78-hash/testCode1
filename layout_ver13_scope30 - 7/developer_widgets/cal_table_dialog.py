"""
Calibration Table Editor Dialog
26-point calibration table editor with graph visualization
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QFileDialog, QMessageBox, QHeaderView, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import struct
import csv
from rf_protocol import RFProtocol

try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class CalTableDialog(QDialog):
    """Calibration Table Editor"""
    
    # 테이블 타입 정의
    TABLE_TYPES = {
        'RF Set DAC': {
            'cmd_get': RFProtocol.CMD_CAL_RFSET_TABLE_GET,
            'cmd_set': RFProtocol.CMD_CAL_RFSET_TABLE_SET,
            'subcmd_target': RFProtocol.SUBCMD_CAL_RFSET_TARGET,
            'columns': ['Target (float)', 'DAC Center (uint16)', 'DAC Low (uint16)', 'DAC High (uint16)'],
            'has_3_dac': True
        },
        'User FWD/LOAD': {
            'cmd_get': RFProtocol.CMD_CAL_FWDLOAD_TABLE_GET,
            'cmd_set': RFProtocol.CMD_CAL_FWDLOAD_TABLE_SET,
            'subcmd_target': RFProtocol.SUBCMD_CAL_FWDLOAD_TARGET,
            'columns': ['Target (float)', 'DAC (uint16)'],
            'has_3_dac': False
        },
        'User REF': {
            'cmd_get': RFProtocol.CMD_CAL_REF_TABLE_GET,
            'cmd_set': RFProtocol.CMD_CAL_REF_TABLE_SET,
            'subcmd_target': RFProtocol.SUBCMD_CAL_REF_TARGET,
            'columns': ['Target (float)', 'DAC (uint16)'],
            'has_3_dac': False
        },
        'User RF Set IN': {
            'cmd_get': RFProtocol.CMD_CAL_RFSETIN_TABLE_GET,
            'cmd_set': RFProtocol.CMD_CAL_RFSETIN_TABLE_SET,
            'subcmd_target': RFProtocol.SUBCMD_CAL_RFSETIN_TARGET,
            'columns': ['Target (float)', 'ADC (uint16)'],
            'has_3_dac': False
        },
        'User DC Bias': {
            'cmd_get': RFProtocol.CMD_CAL_DCBIAS_TABLE_GET,
            'cmd_set': RFProtocol.CMD_CAL_DCBIAS_TABLE_SET,
            'subcmd_target': RFProtocol.SUBCMD_CAL_DCBIAS_TARGET,
            'columns': ['Target (float)', 'ADC (uint16)'],
            'has_3_dac': False
        }
    }
    
    def __init__(self, parent, network_manager, table_name):
        super().__init__(parent)
        self.parent = parent
        self.network_manager = network_manager
        self.table_name = table_name
        self.table_info = self.TABLE_TYPES[table_name]
        
        self.setWindowTitle(f"Calibration Table Editor - {table_name}")
        self.setMinimumSize(900, 750)
        
        self.init_ui()
        self.load_from_device()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 상단 정보
        info_label = QLabel(f"📊 {self.table_name} Calibration Table (26 Points)")
        info_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #87ceeb;")
        layout.addWidget(info_label)
        
        # 테이블
        table_group = QGroupBox("Calibration Data")
        table_layout = QVBoxLayout(table_group)
        
        self.table = QTableWidget(26, len(self.table_info['columns']))
        self.table.setHorizontalHeaderLabels(self.table_info['columns'])
        # 셀 값 변경 시 그래프 업데이트
        self.table.itemChanged.connect(self.on_cell_changed)
        
        self.table.verticalHeader().setVisible(True)
        
        # ========================================
        # 헤더 스타일 수정
        # ========================================
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2e2e3e;
                gridline-color: #555555;
            }
            QHeaderView::section {
                background-color: #1e1e2e;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #555555;
                font-weight: bold;
            }
            QTableWidget::item {
                color: #ffffff;
                padding: 5px;
            }
        """)
        
        # 컬럼 너비 설정
        header = self.table.horizontalHeader()
        for i in range(len(self.table_info['columns'])):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        # 행 번호 헤더 스타일
        self.table.verticalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #1e1e2e;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #555555;
            }
        """)
        
        # 셀 스타일
        for row in range(26):
            for col in range(len(self.table_info['columns'])):
                item = QTableWidgetItem("")
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor("#ffffff"))  # 텍스트 색상
                if col == 0:  # Target (float)
                    item.setBackground(QColor("#2e3e4e"))
                else:  # DAC/ADC (uint16)
                    item.setBackground(QColor("#3e4e5e"))
                self.table.setItem(row, col, item)
        
        table_layout.addWidget(self.table)
        layout.addWidget(table_group)
        
        # 그래프 (matplotlib 사용 가능 시)
        if MATPLOTLIB_AVAILABLE:
            self.canvas = self.create_graph()
            layout.addWidget(self.canvas)
        else:
            # matplotlib 없을 때 안내 라벨
            no_graph_label = QLabel("📊 그래프 표시: matplotlib 설치 필요")
            no_graph_label.setStyleSheet("color: #888888; padding: 20px;")
            no_graph_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_graph_label)
        
        # 하단 버튼
        button_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load from Device")
        load_btn.clicked.connect(self.load_from_device)
        button_layout.addWidget(load_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        apply_btn.clicked.connect(self.apply_to_device)
        button_layout.addWidget(apply_btn)
        
        import_btn = QPushButton("Import CSV")
        import_btn.clicked.connect(self.import_csv)
        button_layout.addWidget(import_btn)
        
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self.export_csv)
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def on_cell_changed(self, item):
        """셀 값 변경 시 호출"""
        if MATPLOTLIB_AVAILABLE:
            self.update_graph()
    
    def create_graph(self):
        """그래프 생성"""
        figure = Figure(figsize=(8, 3), facecolor='#1e1e2e')
        canvas = FigureCanvasQTAgg(figure)
        
        # tight_layout으로 여백 자동 조정
        figure.subplots_adjust(left=0.08, right=0.95, top=0.95, bottom=0.15)
        
        self.ax = figure.add_subplot(111, facecolor='#2e2e3e')
        self.ax.set_xlabel('Point Index', color='white')
        self.ax.set_ylabel('Value', color='white')
        self.ax.tick_params(colors='white')
        self.ax.grid(True, alpha=0.3)
        
        return canvas
    
    def update_graph(self):
        """그래프 업데이트"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        if not hasattr(self, 'ax'):
            return
        
        self.ax.clear()
        
        # Target 값
        targets = []
        for row in range(26):
            try:
                val = float(self.table.item(row, 0).text())
                targets.append(val)
            except:
                targets.append(0)
        
        self.ax.plot(range(26), targets, 'o-', color='#00ff00', label='Target')
        
        # DAC/ADC 값
        if self.table_info['has_3_dac']:
            # RF Set DAC (3개 컬럼)
            dac_c, dac_l, dac_h = [], [], []
            for row in range(26):
                try:
                    dac_c.append(int(self.table.item(row, 1).text()))
                except:
                    dac_c.append(0)
                
                try:
                    dac_l.append(int(self.table.item(row, 2).text()))
                except:
                    dac_l.append(0)
                
                try:
                    dac_h.append(int(self.table.item(row, 3).text()))
                except:
                    dac_h.append(0)
            
            # 배열 크기 검증
            assert len(dac_c) == 26, f"dac_c length: {len(dac_c)}"
            assert len(dac_l) == 26, f"dac_l length: {len(dac_l)}"
            assert len(dac_h) == 26, f"dac_h length: {len(dac_h)}"
            
            self.ax.plot(range(26), dac_c, 's-', color='#00aaff', label='DAC Center')
            self.ax.plot(range(26), dac_l, '^-', color='#ffaa00', label='DAC Low')
            self.ax.plot(range(26), dac_h, 'v-', color='#ff00aa', label='DAC High')
        else:
            # 일반 테이블 (1개 컬럼)
            dac_vals = []
            for row in range(26):
                try:
                    dac_vals.append(int(self.table.item(row, 1).text()))
                except:
                    dac_vals.append(0)
            
            # 배열 크기 검증
            assert len(dac_vals) == 26, f"dac_vals length: {len(dac_vals)}"
            
            col_name = self.table_info['columns'][1].split()[0]
            self.ax.plot(range(26), dac_vals, 's-', color='#00aaff', label=col_name)
        
        self.ax.set_xlabel('Point Index', color='white')
        self.ax.set_ylabel('Value', color='white')
        self.ax.legend(facecolor='#2e2e3e', edgecolor='white', labelcolor='white')
        self.ax.grid(True, alpha=0.3)
        
        # 레이아웃 자동 조정
        self.canvas.figure.tight_layout()
        
        self.canvas.draw()
    
    def load_from_device(self):
        """장치에서 로드"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        try:
            # Target 값 로드
            result = self.network_manager.client_thread.send_command(
                self.table_info['cmd_get'],
                self.table_info['subcmd_target'],
                wait_response=True,
                sync=True
            )
            
            if result.success and result.response_data:
                parsed = RFProtocol.parse_response(result.response_data)
                if parsed and len(parsed['data']) >= 104:  # 26 * 4 bytes
                    targets = struct.unpack('<26f', parsed['data'][:104])
                    
                    for row in range(26):
                        self.table.item(row, 0).setText(f"{targets[row]:.2f}")
            
            # DAC/ADC 값 로드 (테이블 타입에 따라)
            if self.table_info['has_3_dac']:
                # RF Set DAC - 3개 컬럼
                self.load_rf_set_dac_columns()
            else:
                # 일반 - 1개 컬럼
                self.load_single_dac_column()
            
            self.update_graph()
            #QMessageBox.information(self, "완료", "장치에서 테이블을 로드했습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"로드 실패: {e}")
    
    def load_rf_set_dac_columns(self):
        """RF Set DAC 3개 컬럼 로드"""
        subcmds = [
            RFProtocol.SUBCMD_CAL_RFSET_DACC,
            RFProtocol.SUBCMD_CAL_RFSET_DACL,
            RFProtocol.SUBCMD_CAL_RFSET_DACH
        ]
        
        for col_idx, subcmd in enumerate(subcmds):
            result = self.network_manager.client_thread.send_command(
                self.table_info['cmd_get'],
                subcmd,
                wait_response=True,
                sync=True
            )
            
            if result.success and result.response_data:
                parsed = RFProtocol.parse_response(result.response_data)
                if parsed and len(parsed['data']) >= 52:  # 26 * 2 bytes
                    dac_vals = struct.unpack('<26H', parsed['data'][:52])
                    
                    for row in range(26):
                        self.table.item(row, col_idx + 1).setText(str(dac_vals[row]))
    
    def load_single_dac_column(self):
        """단일 DAC/ADC 컬럼 로드"""
        # SUBCMD 매핑
        subcmd_map = {
            'User FWD/LOAD': RFProtocol.SUBCMD_CAL_FWDLOAD_DAC,
            'User REF': RFProtocol.SUBCMD_CAL_REF_DAC,
            'User RF Set IN': RFProtocol.SUBCMD_CAL_RFSETIN_ADC,
            'User DC Bias': RFProtocol.SUBCMD_CAL_DCBIAS_ADC
        }
        
        subcmd = subcmd_map[self.table_name]
        
        result = self.network_manager.client_thread.send_command(
            self.table_info['cmd_get'],
            subcmd,
            wait_response=True,
            sync=True
        )
        
        if result.success and result.response_data:
            parsed = RFProtocol.parse_response(result.response_data)
            if parsed and len(parsed['data']) >= 52:  # 26 * 2 bytes
                dac_vals = struct.unpack('<26H', parsed['data'][:52])
                
                for row in range(26):
                    self.table.item(row, 1).setText(str(dac_vals[row]))
    
    def apply_to_device(self):
        """장치에 적용"""
        if not self.network_manager.client_thread:
            QMessageBox.warning(self, "오류", "네트워크가 연결되지 않았습니다.")
            return
        
        reply = QMessageBox.question(
            self, "확인",
            f"{self.table_name} 테이블을 장치에 적용하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # Target 값 전송
            targets = []
            for row in range(26):
                try:
                    targets.append(float(self.table.item(row, 0).text()))
                except:
                    targets.append(0.0)
            
            target_data = struct.pack('<26f', *targets)
            
            result = self.network_manager.client_thread.send_command(
                self.table_info['cmd_set'],
                self.table_info['subcmd_target'],
                data=target_data,
                wait_response=True,
                sync=True
            )
            
            if not result.success:
                raise Exception(f"Target 전송 실패: {result.message}")
            
            # DAC/ADC 값 전송
            if self.table_info['has_3_dac']:
                self.apply_rf_set_dac_columns()
            else:
                self.apply_single_dac_column()
            
            QMessageBox.information(self, "완료", "테이블이 장치에 적용되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"적용 실패: {e}")
    
    def apply_rf_set_dac_columns(self):
        """RF Set DAC 3개 컬럼 적용"""
        subcmds = [
            RFProtocol.SUBCMD_CAL_RFSET_DACC,
            RFProtocol.SUBCMD_CAL_RFSET_DACL,
            RFProtocol.SUBCMD_CAL_RFSET_DACH
        ]
        
        for col_idx, subcmd in enumerate(subcmds):
            dac_vals = []
            for row in range(26):
                try:
                    dac_vals.append(int(self.table.item(row, col_idx + 1).text()))
                except:
                    dac_vals.append(0)
            
            dac_data = struct.pack('<26H', *dac_vals)
            
            result = self.network_manager.client_thread.send_command(
                self.table_info['cmd_set'],
                subcmd,
                data=dac_data,
                wait_response=True,
                sync=True
            )
            
            if not result.success:
                raise Exception(f"DAC 컬럼 {col_idx} 전송 실패")
    
    def apply_single_dac_column(self):
        """단일 DAC/ADC 컬럼 적용"""
        subcmd_map = {
            'User FWD/LOAD': RFProtocol.SUBCMD_CAL_FWDLOAD_DAC,
            'User REF': RFProtocol.SUBCMD_CAL_REF_DAC,
            'User RF Set IN': RFProtocol.SUBCMD_CAL_RFSETIN_ADC,
            'User DC Bias': RFProtocol.SUBCMD_CAL_DCBIAS_ADC
        }
        
        subcmd = subcmd_map[self.table_name]
        
        dac_vals = []
        for row in range(26):
            try:
                dac_vals.append(int(self.table.item(row, 1).text()))
            except:
                dac_vals.append(0)
        
        dac_data = struct.pack('<26H', *dac_vals)
        
        result = self.network_manager.client_thread.send_command(
            self.table_info['cmd_set'],
            subcmd,
            data=dac_data,
            wait_response=True,
            sync=True
        )
        
        if not result.success:
            raise Exception(f"DAC/ADC 전송 실패")
    
    def import_csv(self):
        """CSV에서 가져오기"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import CSV", "", "CSV Files (*.csv)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # 헤더 스킵
                
                for row_idx, row_data in enumerate(reader):
                    if row_idx >= 26:
                        break
                    
                    for col_idx, value in enumerate(row_data):
                        if col_idx < len(self.table_info['columns']):
                            self.table.item(row_idx, col_idx).setText(value.strip())
            
            self.update_graph()
            QMessageBox.information(self, "완료", "CSV 파일을 가져왔습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"CSV 가져오기 실패: {e}")
    
    def export_csv(self):
        """CSV로 내보내기"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", f"{self.table_name.replace('/', '_')}.csv", 
            "CSV Files (*.csv)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.table_info['columns'])
                
                for row in range(26):
                    row_data = []
                    for col in range(len(self.table_info['columns'])):
                        row_data.append(self.table.item(row, col).text())
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "완료", "CSV 파일로 저장했습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"CSV 저장 실패: {e}")