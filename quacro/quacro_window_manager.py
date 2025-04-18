import logging
import threading
import queue

import win32con

from . import (
    quacro_c_utils,
    quacro_win32,
    quacro_dock,
)

from .quacro_win32 import format_window
from .quacro_events import (
    Event,
    EventStop,
)
from .quacro_dock import (
    EventRequestActivateWindow,
    EventRequestCloseWindow,
)
from .quacro_c_utils import (
    EventCreateWindow,
    EventDestroyWindow,
    EventMoveSize,
    EventActivate,
    EventIconTitleUpdate,
    EventMinimized
)
from .quacro_window_group import WindowGrup


logger = logging.getLogger("window")

class WindowManager:
    window_groups: dict[str, WindowGrup]
    zero_level_groups: list[WindowGrup]
    primary_group: WindowGrup
    all_windows: set[int]

    dock_manager: quacro_dock.DockManager
    event_queue: queue.Queue[Event]

    event_loop_ready: threading.Event


    def __init__(self, window_groups, zero_level_groups, primary_group) -> None:
        self.event_queue = queue.Queue()
        self.dock_manager = quacro_dock.DockManager(
            self.event_queue
        )

        self.window_groups = window_groups
        self.zero_level_groups = zero_level_groups
        self.primary_group = primary_group
        self.primary_group.register_cb_on_add(
            self.on_primary_group_add
        )
        self.primary_group.register_cb_on_remove(
            self.on_primary_group_remove
        )
        self.all_windows = set()
        self.event_loop_ready = threading.Event()

    def on_primary_group_add(self, hwnd:int, all_windows:set[int]) -> None:
        logger.info(f"Window detected: {format_window(hwnd)}")
    
        dock = self.dock_manager.get_dock_by_window(hwnd, default=None)
        if dock is None:
            key = self.dock_manager.identify_window_key(hwnd)
            dock = self.dock_manager.create_dock(key)
        title = quacro_win32.get_window_title(hwnd)
        dock.create_tab(hwnd, title)

        if self.event_loop_ready.is_set():
            dock.set_sticking_target(hwnd)
            dock.update_misc()
            dock.stick_to_target(move_target=True)
            dock.show()
            

    def on_primary_group_remove(self, hwnd:int, all_windows:set[int]) -> None:
        logger.info(f"Window destroyed: {format_window(hwnd)}")

        dock = self.dock_manager.get_dock_by_window(hwnd)
        dock.remove_tab(hwnd)

        if len(dock.tabs)==0:
            self.dock_manager.destroy_dock(dock)

        if dock.target != hwnd:
            return

        # target is destroyed, show next target
        for candidate in dock.tabs:
            quacro_win32.W32.ShowWindow(candidate, win32con.SW_RESTORE)
            break
    
    def on_window_move_size(self, event:EventMoveSize) -> None:
        if event.hwnd in self.dock_manager.active_docks:
            dock = self.dock_manager.active_docks[event.hwnd]
            logger.debug(f"{dock} move: {event.rect}")
            dock.stick_to_target(move_target=True)
            return 

        if event.hwnd not in self.primary_group.current_windows:
            return

        logger.debug(f"Window {format_window(event.hwnd)} movesize: {event.rect}")
        dock = self.dock_manager.get_dock_by_window(event.hwnd)
        if event.hwnd==dock.target:
            dock.move_dock_to_target(event.rect)
        else:
            dock.set_sticking_target(event.hwnd)
            dock.stick_to_target(move_target=False)
    
    def on_window_activate(self, event:EventActivate) -> None:
        hwnd = event.hwnd

        if hwnd in self.dock_manager.active_docks:
            return

        if hwnd not in self.primary_group.current_windows:
            return
        
        if event.minimized:
            # minimized is handled in on_window_minimized
            return
        
        dock = self.dock_manager.get_dock_by_window(hwnd)

        # The window is activated and not minimized
        if not event.inactive: 
            logger.debug(f"Window activated: {format_window(hwnd)}")
            dock.set_sticking_target(hwnd)
            dock.update_misc()
            dock.stick_to_target(move_target=True)
            dock.show()
        else:
            logger.debug(f"Window inactivated: {format_window(hwnd)}")
    
    def on_window_minimized(self, event:EventMinimized):
        if event.hwnd in self.dock_manager.active_docks:
            return

        if event.hwnd not in self.primary_group.current_windows:
            return
        logger.debug(f"Window minimized: {format_window(event.hwnd)}")
        
        dock = self.dock_manager.get_dock_by_window(event.hwnd)

        if dock.target==event.hwnd:
            dock.target_lost()


    def on_window_icon_title_updata(self, event:EventIconTitleUpdate):
        if event.hwnd in self.dock_manager.active_docks:
            return
        if event.hwnd not in self.primary_group.current_windows:
            return
        logger.debug(f"Window title/icon updated: {format_window(event.hwnd)}")
        dock = self.dock_manager.get_dock_by_window(event.hwnd)
        dock.notify_icon_title_update(event.hwnd)
    
    def on_dock_activate_tab(self, event:EventRequestActivateWindow):
        logger.info(f"{event.dock} requests to activate: {format_window(event.hwnd)}")
        quacro_win32.W32.ShowWindow(event.hwnd, win32con.SW_RESTORE)

        event.dock.set_sticking_target(event.hwnd)
        event.dock.update_misc()
        
    def on_dock_close_tab(self, event:EventRequestCloseWindow):
        logger.info(f"{event.dock} requests to close: {format_window(event.hwnd)}")
        quacro_win32.W32.SendMessage(event.hwnd, win32con.WM_CLOSE, 0, 0)

    def on_create_window(self, event:EventCreateWindow) -> None:
        self.all_windows.add(event.hwnd)
        for group in self.zero_level_groups:
            group.add_window(event.hwnd, self.all_windows)

    def on_destroy_window(self, event:EventDestroyWindow) -> None:
        if event.hwnd in self.all_windows:
            self.all_windows.remove(event.hwnd)
        for group in self.zero_level_groups:
            group.remove_window(event.hwnd)


    def forward_hook_event(self) -> None:
        try:
            quacro_c_utils.event_queue_init()
            quacro_c_utils.setup_hook()
        except:
            raise
        else:
            while 1:
                event = quacro_c_utils.wait_for_hook_event()
                self.event_queue.put(event)
                if isinstance(event, EventStop):
                    break
        finally:
            self.event_queue.put(EventStop())
            quacro_c_utils.unins_hook()
            quacro_c_utils.event_queue_deinit()
            logger.info("hook event forwarder loop ended")
    
    def event_loop(self):
        @quacro_c_utils.enum_toplevel_window_callback
        def enum_winodw_callback(hwnd):
            self.on_create_window(EventCreateWindow(hwnd))
        quacro_c_utils.enum_toplevel_window(enum_winodw_callback)
        self.event_loop_ready.set()

        while 1:
            event = self.event_queue.get()
            if isinstance(event, EventStop):
                break
            if isinstance(event, EventCreateWindow):
                if self.dock_manager.is_dock_window(event.hwnd):
                    continue
                self.on_create_window(event)
            elif isinstance(event, EventDestroyWindow):
                if self.dock_manager.is_dock_window(event.hwnd):
                    continue
                self.on_destroy_window(event)
            elif isinstance(event, EventMoveSize):
                self.on_window_move_size(event)
            elif isinstance(event, EventActivate):
                self.on_window_activate(event)
            elif isinstance(event, EventRequestActivateWindow):
                self.on_dock_activate_tab(event)
            elif isinstance(event, EventRequestCloseWindow):
                self.on_dock_close_tab(event)
            elif isinstance(event, EventIconTitleUpdate):
                self.on_window_icon_title_updata(event)
            elif isinstance(event, EventMinimized):
                self.on_window_minimized(event)
            else:
                logger.warning(
                    f"Ignoring unknown hook event type '{type(event).__name__}'"
                )

        logger.info("event loop ended")


