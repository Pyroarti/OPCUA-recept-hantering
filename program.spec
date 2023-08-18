from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT, MERGE
from pathlib import Path


spec_hooks = []
hidden_imports = []


app_name = "LMT recipe manager"
main_script = "main.py"
icon_file = "static\Assets\LMT-logo.ico"


data_files = [
    ("configs/ip_addresses.json", "configs"),
    ("configs/name_space.json", "configs"),
    ("configs/opcua_config.json", "configs"),
    ("configs/sql_config.json", "configs"),
    ("configs/webserver_config.json", "configs"),
    ("language/english.json", "language"),
    ("language/swedish.json", "language"),
    ("logs/data_encrypt.log", "logs"),
    ("logs/gui.log", "logs"),
    ("logs/ms_sql.log", "logs"),
    ("logs/opcua_alarms.log", "logs"),
    ("logs/opcua_client.log", "logs"),
    ("logs/opcua_prog_alarm.log", "logs"),
    ("logs/webserver.log", "logs"),
    ("src/create_log.py", "src"),
    ("src/data_encrypt.py", "src"),
    ("src/gui.py", "src"),
    ("src/ip_checker.py", "src"),
    ("src/ms_sql.py", "src"),
    ("src/opcua_alarm.py", "src"),
    ("src/opcua_client.py", "src"),
    ("src/webserver.py", "src"),
    ("src/__init__.py", "src"),
    ("static/Assets/lmt-logo.ico", "static/Assets"),
    ("static/Assets/LMT-logo.png", "static/Assets"),
    ("static/Assets/lås_logo.png", "static/Assets"),
    ("templates/index.html", "templates"),
    ("C:\Python\Lib\site-packages\customtkinter", "customtkinter"),
]


a = Analysis(
    [main_script],
    pathex=[str(Path(SPEC).parent.resolve())],
    binaries=[],
    datas=data_files,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    hiddenimports=hidden_imports,
    cipher=None,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="output_folder",
)
