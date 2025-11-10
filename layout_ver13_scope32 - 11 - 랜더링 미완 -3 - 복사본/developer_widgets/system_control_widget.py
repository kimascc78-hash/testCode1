"""
System Control Widget
시스템 제어 컨테이너 (Accordion) - Power Limits, VA Limit, DCC Interface, Min/Max Control
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout


class SystemControlWidget(QWidget):
    """시스템 제어 컨테이너"""
    
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
        
        # ========================================
        # 1. Power Limits
        # ========================================
        from developer_widgets.system_widgets.power_limits_widget import PowerLimitsWidget
        self.power_limits_widget = PowerLimitsWidget(self, self.network_manager)
        self.power_limits_widget.setChecked(True)  # 기본 열림
        self.power_limits_widget.toggled.connect(
            lambda checked: self.on_widget_toggled(self.power_limits_widget, checked)
        )
        layout.addWidget(self.power_limits_widget)
        self.widgets.append(self.power_limits_widget)
        
        # ========================================
        # 2. VA Limit
        # ========================================
        from developer_widgets.system_widgets.va_limit_widget import VALimitWidget
        self.va_limit_widget = VALimitWidget(self, self.network_manager)
        self.va_limit_widget.setChecked(False)
        self.va_limit_widget.toggled.connect(
            lambda checked: self.on_widget_toggled(self.va_limit_widget, checked)
        )
        layout.addWidget(self.va_limit_widget)
        self.widgets.append(self.va_limit_widget)
        
        # ========================================
        # 3. DCC Interface
        # ========================================
        from developer_widgets.system_widgets.dcc_interface_widget import DCCInterfaceWidget
        self.dcc_interface_widget = DCCInterfaceWidget(self, self.network_manager)
        self.dcc_interface_widget.setChecked(False)
        self.dcc_interface_widget.toggled.connect(
            lambda checked: self.on_widget_toggled(self.dcc_interface_widget, checked)
        )
        layout.addWidget(self.dcc_interface_widget)
        self.widgets.append(self.dcc_interface_widget)
        
        # ========================================
        # 4. Min/Max Control
        # ========================================
        from developer_widgets.system_widgets.minmax_control_widget import MinMaxControlWidget
        self.minmax_control_widget = MinMaxControlWidget(self, self.network_manager)
        self.minmax_control_widget.setChecked(False)
        self.minmax_control_widget.toggled.connect(
            lambda checked: self.on_widget_toggled(self.minmax_control_widget, checked)
        )
        layout.addWidget(self.minmax_control_widget)
        self.widgets.append(self.minmax_control_widget)
        
        layout.addStretch()
    
    def on_widget_toggled(self, sender_widget, checked):
        """위젯 토글 시 다른 위젯들 닫기 (Accordion 효과)"""
        if checked:  # 펼쳐질 때만
            for widget in self.widgets:
                if widget != sender_widget and widget.isChecked():
                    widget.setChecked(False)