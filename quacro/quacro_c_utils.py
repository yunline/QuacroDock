import ctypes
import ctypes.wintypes

from .quacro_events import Event, EventStop

SCRIPT_ABI_VERSION = (0, 0, 2)

EVENT_TYPE_STOP = 0
EVENT_TYPE_CREATE_WINDOW = 1
EVENT_TYPE_DESTROY_WINDOW = 2
EVENT_TYPE_MOVE_SIZE = 3
EVENT_TYPE_ACTIVATE = 4
EVENT_TYPE_ICON_TITLE_UPDATE = 5
EVENT_TYPE_MINIMIZED = 6

if ctypes.sizeof(ctypes.c_voidp) == 8:
    # 64bit windows
    HWND = ctypes.c_uint64
else:
    # 32bit windows
    HWND = ctypes.c_uint32 # type: ignore

class ActivateInfo(ctypes.Structure):
    _fields_ = [
        ("inactive", ctypes.wintypes.BOOL),
        ("minimized", ctypes.wintypes.BOOL),
    ]

class EventData(ctypes.Union):
    _fields_ = [
        ("rect", ctypes.wintypes.RECT),
        ("activate_info", ActivateInfo)
    ]

class _IPCQueueItem(ctypes.Structure):
    _fields_ = [
        ("event_type", ctypes.c_int32),
        ("hwnd", HWND),
        ("data", EventData),
    ]

dll = ctypes.cdll.LoadLibrary("./quacro_utils.dll")

_get_error = dll.get_error
_get_error.argtypes = (ctypes.POINTER(ctypes.c_wchar_p),)

def error_check(result, func, arguments):
    if result!=-1:
        return result
    buf = ctypes.c_wchar_p()
    _get_error(ctypes.byref(buf))
    err_msg = buf.value
    raise OSError(f"Failed to call '{func.__name__}':\n{err_msg}")

event_queue_init = dll.event_queue_init
event_queue_init.argtypes = ()
event_queue_init.restype = ctypes.c_int
event_queue_init.errcheck = error_check

event_queue_deinit = dll.event_queue_deinit
event_queue_deinit.argtypes = ()
event_queue_deinit.restype = None

_wait_for_hook_event = dll.wait_for_hook_event
_wait_for_hook_event.argtypes = (ctypes.POINTER(_IPCQueueItem),)
_wait_for_hook_event.restype = ctypes.c_int
_wait_for_hook_event.errcheck = error_check


class WindowEvent(Event):
    hwnd: int

    def __init__(self, hwnd):
        self.hwnd = hwnd

class EventCreateWindow(WindowEvent):
    pass

class EventDestroyWindow(WindowEvent):
    pass

class EventMoveSize(WindowEvent):
    rect: tuple[int, int, int, int]

    def __init__(self, hwnd, rect):
        super().__init__(hwnd)
        self.rect = rect

class EventActivate(WindowEvent):
    inactive: bool
    minimized: bool

    def __init__(self, hwnd, inactive, minimized):
        super().__init__(hwnd)
        self.inactive = bool(inactive)
        self.minimized = bool(minimized)

class EventIconTitleUpdate(WindowEvent):
    pass

class EventMinimized(WindowEvent):
    pass

def wait_for_hook_event() -> Event:
    event = _IPCQueueItem()
    event_id = _wait_for_hook_event(ctypes.byref(event))
    if event_id==EVENT_TYPE_STOP:
        return EventStop()
    if event_id==EVENT_TYPE_CREATE_WINDOW:
        return EventCreateWindow(event.hwnd)
    if event_id==EVENT_TYPE_DESTROY_WINDOW:
        return EventDestroyWindow(event.hwnd)
    if event_id==EVENT_TYPE_MOVE_SIZE:
        rect = (
            event.data.rect.left,
            event.data.rect.top,
            event.data.rect.right,
            event.data.rect.bottom,
        )
        return EventMoveSize(event.hwnd, rect)
    if event_id==EVENT_TYPE_ACTIVATE:
        return EventActivate(
            event.hwnd,
            event.data.activate_info.inactive,
            event.data.activate_info.minimized
        )
    if event_id==EVENT_TYPE_ICON_TITLE_UPDATE:
        return EventIconTitleUpdate(event.hwnd)
    if event_id==EVENT_TYPE_MINIMIZED:
        return EventMinimized(event.hwnd)
    raise OSError(f"Unknown event type id {event_id}")

send_stop_event = dll.send_stop_event
send_stop_event.argtypes = ()
send_stop_event.restype = None

_get_abi_version = dll.get_abi_version
_get_abi_version.argtypes = (
    ctypes.POINTER(ctypes.c_uint16),
    ctypes.POINTER(ctypes.c_uint16),
    ctypes.POINTER(ctypes.c_uint16),
)

def get_dll_abi_version():
    major = ctypes.c_uint16(114)
    minor = ctypes.c_uint16(514)
    micro = ctypes.c_uint16(1919)
    _get_abi_version(
        ctypes.byref(major),
        ctypes.byref(minor),
        ctypes.byref(micro),
    )
    return (major.value, minor.value, micro.value)

load_hook_proc_dll = dll.load_hook_proc_dll
load_hook_proc_dll.argtypes = (ctypes.c_wchar_p,)
load_hook_proc_dll.restype = ctypes.c_int
load_hook_proc_dll.errcheck = error_check

setup_hook = dll.setup_hook
setup_hook.restype = ctypes.c_int
setup_hook.errcheck = error_check

unins_hook = dll.unins_hook
unins_hook.argtypes = ()
unins_hook.restype = None

_read_window_icon = dll.read_window_icon
_read_window_icon.argtypes = (HWND, ctypes.POINTER(ctypes.c_int))
_read_window_icon.restype = ctypes.c_void_p

_free_png_buffer = dll.free_png_buffer
_free_png_buffer.argtypes = (ctypes.c_void_p,)
_free_png_buffer.restype = None

def read_window_icon(hwnd) -> bytes|None:
    length = ctypes.c_int()
    png_ptr = _read_window_icon(hwnd, ctypes.byref(length))
    if png_ptr is None:
        return None
    
    png_buffer = ctypes.cast(png_ptr, ctypes.POINTER(ctypes.c_uint8*length.value))
    png = bytes(png_buffer.contents)
    
    # don't forget to free
    _free_png_buffer(png_ptr)

    return png

enum_toplevel_window_callback = ctypes.CFUNCTYPE(None, HWND)
enum_toplevel_window = dll.enum_toplevel_window
enum_toplevel_window.argtypes = (enum_toplevel_window_callback,)
enum_toplevel_window.restype = ctypes.c_int
enum_toplevel_window.errcheck = error_check

ACQUIRE_SILOCK_SUCCESS = 0
ACQUIRE_SILOCK_FAILED = -1
ACQUIRE_SILOCK_OCCUPIED = 1
acquire_single_instance_lock = dll.acquire_single_instance_lock
acquire_single_instance_lock.restype = ctypes.c_int
