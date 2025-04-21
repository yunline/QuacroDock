import logging
import threading
import os
import sys
import tomllib

from quacro import quacro_pywebview_inject

# inject before `import webview`
quacro_pywebview_inject.inject()

import webview
from infi.systray import SysTrayIcon

from quacro import (
    quacro_logging,
    quacro_app_data,
    quacro_c_utils,
    quacro_win32,
    quacro_window_manager,
    quacro_config,
)
from quacro.quacro_errors import ConfigError

quacro_logging.setup_log_config()

quacro_app_data.init_app_data()

logger = logging.getLogger("main")
logger.info("Hello Quacro Dock")

if getattr(sys, "frozen", False):
    logger.debug("Running in frozen environment")
    logger.debug(f"Temp path: '{getattr(sys,'_MEIPASS')}'")

logger.debug(f"Process started, PID:{os.getpid()}")

dll_abi_version = quacro_c_utils.get_dll_abi_version()
script_abi_version = quacro_c_utils.SCRIPT_ABI_VERSION
if dll_abi_version!=script_abi_version:
    error_msg = f"Incompatible abi version. "\
        f"dll:{dll_abi_version}, script:{script_abi_version}\n"\
        f"Run .\\build_dll.bat to rebuild dll"
    logger.error(error_msg)
    quacro_win32.fatal_msgbox(error_msg)
    raise SystemExit()
logger.info(f"ABI version {script_abi_version}")

result = quacro_c_utils.acquire_single_instance_lock()
if result==quacro_c_utils.ACQUIRE_SILOCK_SUCCESS:
    logger.info("Single instance lock acquired successfully")
else:
    if result==quacro_c_utils.ACQUIRE_SILOCK_OCCUPIED:
        error_msg = "An instance of QuacroDock has been running"
        quacro_win32.info_msgbox(error_msg)
    else:
        error_msg = "Failed to acquire single instance lock"
        quacro_win32.fatal_msgbox(error_msg)
    logger.error(error_msg)
    raise SystemExit()

quacro_app_data.extract_hook_proc_dll()
quacro_c_utils.load_hook_proc_dll(quacro_app_data.HP_DLL_PATH)

try:
    config_file = open("quacro_config.toml","rb")
except FileNotFoundError as err:
    logger.error(f"{type(err).__name__}: {err}")
    quacro_win32.fatal_msgbox("Config file 'quacro_config.toml' is not found")
    raise SystemExit

try:
    cfg_raw = tomllib.load(config_file)
except tomllib.TOMLDecodeError as err:
    logger.error(f"{type(err).__name__}: {err}")
    quacro_win32.fatal_msgbox(
        f"Unable to docode config 'quacro_config.toml':\n{err}"
    )
    raise SystemExit
finally:
    config_file.close()

try:
    cfg = quacro_config.Config.load_config(cfg_raw)
except ConfigError as err:
    logger.error(f"{type(err).__name__}: {err}")
    quacro_win32.fatal_msgbox(
        f"Invalid config:\n"
        f"In 'quacro_config.toml':\n{err}"
    )
    raise SystemExit
try:
    window_filter_config = cfg.load_window_filter_config()
except ConfigError as err:
    logger.error(f"{type(err).__name__}: {err}")
    quacro_win32.fatal_msgbox(
        f"Invalid window group config:\n"
        f"In 'quacro_config.toml', [window_group]:\n{err}"
    )
    raise SystemExit

window_manager = quacro_window_manager.WindowManager(
    *window_filter_config
)

dock_manager = window_manager.dock_manager

def on_quit(systray: SysTrayIcon):
    quacro_c_utils.send_stop_event()
    dock_manager.quit()
    systray.shutdown(join=False)

tray_menu_options = (
    ("Quit", None, on_quit),
)

tray_icon = SysTrayIcon(
    "", # left icon unset
    "QuacroDock",
    tray_menu_options
)

# set the tray icon as the exe icon
tray_icon._hicon = quacro_win32.get_exe_hicon()

event_loop_thread = threading.Thread(
    target=window_manager.event_loop
)

hook_event_forwarder_thread = threading.Thread(
    target=window_manager.forward_hook_event,
)

def start_threads_after_webview_init():
    dock_manager.pre_created_dock.dom_loaded.wait(timeout=5)
    logger.debug("Starting the event loop thread")
    event_loop_thread.start()
    if not window_manager.event_loop_ready.wait(timeout=5):
        on_quit(tray_icon)
        raise TimeoutError("Timeout waiting for event loop thread ready")
    logger.debug("Starting the hook event forwader thread")
    hook_event_forwarder_thread.start()
    logger.info("All threads started")

logger.debug("Starting tray icon thread")
tray_icon.start()

logger.debug("Starting webview")
webview.start(
    start_threads_after_webview_init,
    gui="edgechromium",
    private_mode=False
)

logger.info("Main thread ended")
