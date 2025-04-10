import json
import base64
import queue
import threading
from typing import Any, Callable
import logging

import webview
import win32con

from . import (
    quacro_events,
    quacro_win32,
    quacro_web_data,
    quacro_c_utils,
)
from .quacro_win32 import format_window

logger = logging.getLogger("dock")

webview.DRAG_REGION_SELECTOR = "#top_bar"

DEFAULT_DOCK_WIDTH = 200
DOCK_WIDTH_MIN = 75
DOCK_WIDTH_MAX = 250

class Dock:
    window: webview.Window
    hwnd:int
    being_destroyed: bool = False
    dom_loaded:threading.Event
    dock_manager:"DockManager"
    _move_no_message: Callable

    # A valid key should not be None
    _key:Any|None = None

    tabs: set[int]
    target: int|None = None

    def __repr__(self):
        return f'Dock(id {hex(id(self))})'

    def __init__(self, manager:"DockManager"):
        self.dock_manager = manager
        self.tabs = set()
        self.dom_loaded = threading.Event()
        self.window = webview.create_window(
            'QuacroDock',
            hidden=True,
            frameless=True, 
            resizable=False, 
            focus=False,
            min_size=(0,0),
            html=quacro_web_data.frontend_html
        )

        # Originally move() can't emit WM_MOVING event.
        # We inject, then it can.
        self._move_no_message = self.window.move
        self.window.move = self._move_inj # type: ignore

        # load self.hwnd
        if self.window.events.before_show.is_set():
            self.window_cb_before_show()
        else:
            self.window.events.before_show += self.window_cb_before_show

        self.window.events.loaded += self.window_cb_on_loaded
        self.window.events.closing += self.window_cb_closing
        self.window.expose(self.api_activate_tab)
        self.window.expose(self.api_close_tab)
        self.window.expose(self.api_get_icon)
        self.window.expose(self.api_horizontal_resize)
    
    def _move_inj(self,x,y):
        self._move_no_message(x,y)
        quacro_win32.send_moving_message(self.hwnd)

    def hide(self):
        quacro_win32.W32.ShowWindow(self.hwnd, win32con.SW_HIDE)
    
    def show(self, raise_dock_to_top=False):
        """Show the dock with taskbar icon hidden"""
        quacro_win32.W32.ShowWindow(self.hwnd, win32con.SW_SHOWNOACTIVATE)
        # bring dock to top
        if raise_dock_to_top:
            quacro_win32.W32.SwitchToThisWindow(self.hwnd)
            # switch back to target window
            if self.target is not None:
                quacro_win32.W32.SwitchToThisWindow(self.target)
        # hide thr taskbar icon
        style = quacro_win32.W32.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
        style |= win32con.WS_EX_TOOLWINDOW
        style &= ~(win32con.WS_EX_APPWINDOW)
        quacro_win32.W32.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, style)
        
    def _destroy(self):
        self.being_destroyed = True
        self.window.destroy()

    _width = DEFAULT_DOCK_WIDTH
    @property
    def width(self): # read-only
        return self._width
    
    def window_cb_before_show(self):
        assert self.window.native is not None
        self.hwnd = self.window.native.Handle.ToInt64()
        logger.debug(f"{self} window handle: [{self.hwnd}]")
    
    def window_cb_on_loaded(self):
        js = "var tab_lst = new TabList();"
        self.window.evaluate_js(js)

        self.dom_loaded.set()
    
    def window_cb_closing(self):
        if self.being_destroyed:
            return True
        return False

    def api_activate_tab(self, tab_id: int):
        event = EventRequestActivateWindow(tab_id, self)
        self.dock_manager.event_queue.put(event)

    def api_close_tab(self, tab_id: int):
        event = EventRequestCloseWindow(tab_id, self)
        self.dock_manager.event_queue.put(event)
    
    def api_get_icon(self, tab_id: int):
        logger.debug(f"Getting icon for {tab_id}")
        icon_png = quacro_c_utils.read_window_icon(tab_id)
        if icon_png is None:
            return None
        b64_icon = base64.b64encode(icon_png).decode('ascii')
        return "data:image/png;base64," + b64_icon
    
    def api_horizontal_resize(self, x):
        rect = quacro_win32.get_window_rect(self.hwnd)
        if rect is None:
            return
        x_pos = int(x)
        width = rect.right-x_pos
        if width<=DOCK_WIDTH_MIN:
            width = DOCK_WIDTH_MIN
            x_pos = rect.right - width
        elif width>=DOCK_WIDTH_MAX:
            width = DOCK_WIDTH_MAX
            x_pos = rect.right - width
        flags = win32con.SWP_NOZORDER
        result = quacro_win32.W32.SetWindowPos(
            self.hwnd, 0,
            x_pos, rect.top,
            width, rect.bottom-rect.top,
            flags
        )
        if not result:
            raise OSError("Failed to set dock position")
        self._width = width
        logger.debug(f"{self} resize (w:{width} x:{x_pos})")
        

    def create_tab(self, hwnd:int, title:str):
        _title = json.dumps(title)
        _tab_id = json.dumps(hwnd)
        js = f"tab_lst.create_tab({_title}, {_tab_id});"
        self.window.evaluate_js(js)
        self.tabs.add(hwnd)
    
    def remove_tab(self, hwnd:int):
        _hwnd = json.dumps(hwnd)
        js = f"tab_lst.remove_tab({_hwnd});"
        self.window.evaluate_js(js)
        self.tabs.remove(hwnd)
    
    def activate_tab(self, hwnd:int):
        _hwnd = json.dumps(hwnd)
        js = f"tab_lst.activate_tab({_hwnd});"
        self.window.evaluate_js(js)
    
    def target_lost(self):
        logger.debug(f"{self} target lost")
        self.target = None
        self.hide()
    
    def update_misc(self):
        if self.target is None:
            return
        self.activate_tab(self.target)
        for window in self.tabs:
            if window != self.target:
                quacro_win32.W32.ShowWindow(window, win32con.SW_MINIMIZE)

    def resolve_sticking_target(self):
        if not self.tabs:
            return False
        fg_window = quacro_win32.W32.GetForegroundWindow()
        if fg_window not in self.tabs:
            self.target_lost()
            return False
        self.target = fg_window
        return True
    
    def set_sticking_target(self,hwnd):
        self.target = hwnd

    def stick_to_target(self, move_target=True):
        if self.target is None:
            return
        logger.debug(f"{self} sticking to {format_window(self.target)}")
        target_rect = quacro_win32.get_window_rect(self.target)
        if target_rect is None:
            self.target_lost()
            return
        self_rect = quacro_win32.get_window_rect(self.hwnd)
        if self_rect is None:
            raise OSError("Failed to get rect for a dock window")

        if move_target:
            self.move_target_to_dock(
                (self_rect.left, self_rect.top, self_rect.right, self_rect.bottom),
                (target_rect.left, target_rect.top, target_rect.right, target_rect.bottom)
            )
        else:
            self.move_dock_to_target((
                target_rect.left, 
                target_rect.top, 
                target_rect.right, 
                target_rect.bottom
            ))

    def move_target_to_dock(self, self_rect, target_rect):
        target_x = self_rect[0] + self.width
        target_y = self_rect[1]
        self_w = self.width
        self_h = target_rect[3] - target_rect[1]
        quacro_win32.W32.SetWindowPos(
            self.target, 0,
            target_x, target_y,
            0, 0,
            win32con.SWP_NOSIZE|
            win32con.SWP_NOZORDER|
            win32con.SWP_NOACTIVATE
        )
        quacro_win32.W32.SetWindowPos(
            self.hwnd, self.target,
            0, 0,
            self_w, self_h,
            win32con.SWP_NOMOVE
        )

    def move_dock_to_target(self, rect):
        pos_x = rect[0]-self.width
        pos_y = rect[1]
        size_x = self.width
        size_y = rect[3]-rect[1]
        quacro_win32.W32.SetWindowPos(
            self.hwnd, self.target,
            pos_x, pos_y,
            size_x, size_y,
            0
        )
        

class DockEvent(quacro_events.Event):
    hwnd: int
    dock: "Dock"

    def __init__(self, hwnd:int, dock:"Dock"):
        self.hwnd = hwnd
        self.dock = dock

class EventRequestCloseWindow(DockEvent):
    pass

class EventRequestActivateWindow(DockEvent):
    pass


class DockManager:
    active_docks: dict[int, Dock]
    key_dock_map: dict[Any, Dock]
    event_queue:queue.Queue[quacro_events.Event]
    pre_created_dock:Dock

    identify_window_key: Callable

    def __init__(self, event_queue) -> None:
        self.active_docks = {}
        self.key_dock_map = {}
        self.event_queue = event_queue
        self.pre_created_dock = Dock(self)

        self.identify_window_key = lambda hwnd:1
    
    def is_dock_window(self,hwnd:int)->bool:
        if hwnd in self.active_docks:
            return True
        if hasattr(self.pre_created_dock, "hwnd"):
            if hwnd == self.pre_created_dock.hwnd:
                return True
        return False
    
    def create_dock(self, key=None) -> Dock:
        new_dock = self.pre_created_dock
        self.pre_created_dock = Dock(self)
        new_dock.dom_loaded.wait()
        self.active_docks[new_dock.hwnd] = new_dock
        if key is not None:
            self.key_dock_map[key] = new_dock
            new_dock._key = key
        logger.debug(f"{self.pre_created_dock} pre-created")
        logger.info(f"{new_dock} activated")
        return new_dock
    
    def get_dock_by_window(self, hwnd:int, **kw) -> Dock|Any:

        key = self.identify_window_key(hwnd)
        if key in self.key_dock_map:
            return self.key_dock_map[key]
        elif kw and "default" in kw:
            return kw["default"]
        else:
            raise KeyError(f"Can't find dock for window: {hwnd}")
    
    def destroy_dock(self, dock:Dock) -> None:
        del self.active_docks[dock.hwnd]
        if dock._key is not None:
            del self.key_dock_map[dock._key]
        dock._destroy()
        logger.info(f"{dock} destroyed")
    
    def quit(self) -> None:
        for hwnd in self.active_docks:
            self.active_docks[hwnd]._destroy()
        self.pre_created_dock._destroy()

