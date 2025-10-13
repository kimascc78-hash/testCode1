# style_manager.py
"""
Global Style Manager
전역 스타일 관리
"""

def get_global_messagebox_style():
    """QMessageBox 전역 스타일"""
    return """
    QMessageBox {
        background-color: #2e2e3e;
    }
    QMessageBox QLabel {
        color: #ffffff;
        font-size: 13px;
        min-width: 300px;
        padding: 10px;
    }
    QMessageBox QPushButton {
        background-color: #4a4a5a;
        color: #ffffff;
        border: 1px solid #5a5a6a;
        padding: 6px 20px;
        border-radius: 3px;
        min-width: 80px;
        font-size: 12px;
    }
    QMessageBox QPushButton:hover {
        background-color: #5a5a6a;
    }
    QMessageBox QPushButton:pressed {
        background-color: #3a3a4a;
    }
    QMessageBox QDialogButtonBox {
        button-layout: 0;
    }
    """

def apply_global_styles(app):
    """전역 스타일 적용"""
    current_style = app.styleSheet()
    app.setStyleSheet(current_style + get_global_messagebox_style())
    
    # main.py의 apply_global_styles(app) 다음에
    print("전역 스타일 적용 완료")
    #print(app.styleSheet())  # 스타일 내용 출력