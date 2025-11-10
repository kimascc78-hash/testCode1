::pyinstaller --onedir --noconsole --hidden-import PyQt5.QtWidgets --hidden-import PyQt5.QtCore --hidden-import PyQt5.QtGui --hidden-import pandas --hidden-import openpyxl main_app.py

pyinstaller --onedir --noconsole ^
    --hidden-import PyQt5.QtWidgets ^
    --hidden-import PyQt5.QtCore ^
    --hidden-import PyQt5.QtGui ^
    --hidden-import pandas ^
    --hidden-import openpyxl ^
    --add-data "resources/manual/;resources/manual" ^
	--add-data "resources/manual/videos;resources/manual/videos" ^
	--add-data "resources/config;resources/config" ^
    VHF_UI.py