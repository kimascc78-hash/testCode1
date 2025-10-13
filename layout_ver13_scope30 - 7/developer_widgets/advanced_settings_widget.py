"""
Advanced Settings Widget
고급 설정 컨테이너 (Accordion)
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout


class AdvancedSettingsWidget(QWidget):
    """고급 설정 컨테이너"""
    
    def __init__(self, parent, network_manager):
        super().__init__(parent)
        self.parent = parent
        self.network_manager = network_manager
        
        # 모든 위젯 리스트 (상호 연결용)
        self.widgets = []
        
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # SDD Config
        from developer_widgets.sdd_widget import SDDWidget
        self.sdd_widget = SDDWidget(self, self.network_manager)
        self.sdd_widget.setChecked(True)
        self.sdd_widget.toggled.connect(lambda checked: self.on_widget_toggled(self.sdd_widget, checked))
        layout.addWidget(self.sdd_widget)
        self.widgets.append(self.sdd_widget)
        
        # DDS Control
        from developer_widgets.dds_widget import DDSWidget
        self.dds_widget = DDSWidget(self, self.network_manager)
        self.dds_widget.setChecked(False)
        self.dds_widget.toggled.connect(lambda checked: self.on_widget_toggled(self.dds_widget, checked))
        layout.addWidget(self.dds_widget)
        self.widgets.append(self.dds_widget)
        
        # AGC Setup
        from developer_widgets.agc_widget import AGCWidget
        self.agc_widget = AGCWidget(self, self.network_manager)
        self.agc_widget.setChecked(False)
        self.agc_widget.toggled.connect(lambda checked: self.on_widget_toggled(self.agc_widget, checked))
        layout.addWidget(self.agc_widget)
        self.widgets.append(self.agc_widget)
        
        # Fast Data Acquisition
        from developer_widgets.fast_acq_widget import FastAcqWidget
        self.fast_acq_widget = FastAcqWidget(self, self.network_manager)
        self.fast_acq_widget.setChecked(False)
        self.fast_acq_widget.toggled.connect(lambda checked: self.on_widget_toggled(self.fast_acq_widget, checked))
        layout.addWidget(self.fast_acq_widget)
        self.widgets.append(self.fast_acq_widget)
        
        # Gate Bias Config
        from developer_widgets.gate_bias_widget import GateBiasWidget
        self.gate_bias_widget = GateBiasWidget(self, self.network_manager)
        self.gate_bias_widget.setChecked(False)
        self.gate_bias_widget.toggled.connect(lambda checked: self.on_widget_toggled(self.gate_bias_widget, checked))
        layout.addWidget(self.gate_bias_widget)
        self.widgets.append(self.gate_bias_widget)
        
        layout.addStretch()
    
    def on_widget_toggled(self, sender_widget, checked):
        """위젯 토글 시 다른 위젯들 닫기 (Accordion 효과)"""
        if checked:  # 펼쳐질 때만
            for widget in self.widgets:
                if widget != sender_widget and widget.isChecked():
                    widget.setChecked(False)