import sys
import win32con
import ctypes
import ctypes.wintypes
import logging

from .quacro_logging import warn_tb

logger = logging.getLogger('win32')

BUF_LEN = 512

class W32:
    """Win32 api import"""
    # Pack win32 api in a class
    # to prevent leaking everywhere in the namespace
    GetModuleHandle = ctypes.windll.kernel32.GetModuleHandleW
    ExtractIcon = ctypes.windll.shell32.ExtractIconW
    GetWindowRect = ctypes.windll.user32.GetWindowRect
    SendMessage = ctypes.windll.user32.SendMessageW
    ShowWindow = ctypes.windll.user32.ShowWindow
    GetWindowLong = ctypes.windll.user32.GetWindowLongW
    SetWindowLong = ctypes.windll.user32.SetWindowLongW
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetClassName = ctypes.windll.user32.GetClassNameW
    GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
    OpenProcess = ctypes.windll.kernel32.OpenProcess
    GetModuleBaseName = ctypes.windll.kernel32.K32GetModuleBaseNameW
    GetModuleFileNameEx = ctypes.windll.kernel32.K32GetModuleFileNameExW
    CloseHandle = ctypes.windll.kernel32.CloseHandle
    GetLastError = ctypes.windll.kernel32.GetLastError
    FormatMessage = ctypes.windll.kernel32.FormatMessageW
    GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow
    SetWindowPos = ctypes.windll.user32.SetWindowPos
    ShowWindow = ctypes.windll.user32.ShowWindow
    GetWindowPlacement = ctypes.windll.user32.GetWindowPlacement
    MessageBox = ctypes.windll.user32.MessageBoxW
    DwmSetWindowAttribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
    SwitchToThisWindow = ctypes.windll.user32.SwitchToThisWindow

    def __new__(cls,*args,**kwargs):
        raise TypeError("'W32' class can not be instantiated.")

def get_last_error():
    error_code = W32.GetLastError()
    buf = ctypes.c_wchar_p()
    W32.FormatMessage(
        win32con.FORMAT_MESSAGE_ALLOCATE_BUFFER | 
        win32con.FORMAT_MESSAGE_FROM_SYSTEM |
        win32con.FORMAT_MESSAGE_IGNORE_INSERTS,
        win32con.NULL,
        error_code,
        0,
        ctypes.byref(buf),
        0,
        win32con.NULL
    )
    return (error_code, buf.value)

def warn_last_error():
    error_msg = f"Win32 api error: {get_last_error()}"
    warn_tb(logger ,error_msg, level=4)

def msgbox(text:str, caption:str|None=None, flags:int=0):
    text_buf = ctypes.create_unicode_buffer(text)
    if caption is not None:
        caption_buf = ctypes.create_unicode_buffer(caption)
    return W32.MessageBox(
        win32con.NULL,
        text_buf,
        win32con.NULL if caption is None else caption_buf,
        flags
    )

def info_msgbox(text:str, caption:str|None=None):
    msgbox(text, caption, flags=win32con.MB_OK|win32con.MB_ICONINFORMATION)

def fatal_msgbox(text:str, caption:str|None=None):
    msgbox(text, caption, flags=win32con.MB_OK|win32con.MB_ICONERROR)


def get_window_thread_process_id(hwnd):
    pid = ctypes.wintypes.DWORD(0)
    thread_id = W32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if thread_id==0:
        warn_last_error()
        return 0,0
    return thread_id, pid.value

def get_window_exe_path(hwnd):
    thread_id, pid = get_window_thread_process_id(hwnd)
    if pid==0:
        return ''
    process_handle = W32.OpenProcess(
        win32con.PROCESS_QUERY_LIMITED_INFORMATION,
        False, 
        ctypes.wintypes.DWORD(pid)
    )
    if not process_handle:
        warn_last_error()
        return ''
    buf = ctypes.create_unicode_buffer(BUF_LEN)
    result = W32.GetModuleFileNameEx(
        process_handle,
        win32con.NULL,
        buf,
        BUF_LEN,
    )
    if result==0:
        warn_last_error()
        W32.CloseHandle(process_handle)
        return ''
    W32.CloseHandle(process_handle)
    return buf.value

def get_window_title(hwnd):
    buf = ctypes.create_unicode_buffer(BUF_LEN)
    result = W32.GetWindowText(hwnd, buf, BUF_LEN)
    if result==0:
        error = get_last_error()
        if error[0]:
            warn_tb(logger, error, level=2)
        return ''
    return buf.value

if __debug__:
    def format_window(hwnd):
        return f"[{hwnd}]'{get_window_title(hwnd)}'"
else:
    def format_window(hwnd):
        return f"[{hwnd}]"

def get_window_class_name(hwnd):
    buf = ctypes.create_unicode_buffer(BUF_LEN)
    result = W32.GetClassName(hwnd, buf, BUF_LEN)
    if result==0:
        warn_last_error()
        return ''
    return buf.value

def get_exe_hicon():
    return W32.ExtractIcon(
        W32.GetModuleHandle(win32con.NULL),
        sys.executable, 
        0
    )

def get_window_rect(hwnd) -> ctypes.wintypes.RECT|None:
    rect = ctypes.wintypes.RECT()
    result = W32.GetWindowRect(hwnd, ctypes.byref(rect))
    if not result:
        warn_last_error()
        return None
    return rect

def send_moving_message(hwnd):
    """Get window rect and send as WM_MOVING message"""
    rect = ctypes.wintypes.RECT()
    W32.GetWindowRect(hwnd, ctypes.byref(rect))
    W32.SendMessage(hwnd, win32con.WM_MOVING, 0, ctypes.byref(rect))

class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("showCmd", ctypes.c_uint),
        ("ptMinPosition", ctypes.wintypes.POINT),
        ("ptMaxPosition", ctypes.wintypes.POINT),
        ("rcNormalPosition", ctypes.wintypes.RECT),
        ("rcDevice", ctypes.wintypes.RECT),
    ]

def is_window_minimized(hwnd):
    placement = WINDOWPLACEMENT()
    placement.length = ctypes.sizeof(WINDOWPLACEMENT)
    result = W32.GetWindowPlacement(hwnd, ctypes.byref(placement))
    if result==0:
        warn_last_error()
        return False
    return placement.showCmd==win32con.SW_SHOWMINIMIZED
