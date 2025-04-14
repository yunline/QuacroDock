import logging
import tomllib
import threading
import queue

import win32con

from . import (
    quacro_window_filters,
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
)
from .quacro_errors import ConfigError
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


    def __init__(self) -> None:
        self.event_queue = queue.Queue()
        self.dock_manager = quacro_dock.DockManager(
            self.event_queue
        )

        self.window_groups = {}
        self.zero_level_groups = []
        self.all_windows = set()
        self.event_loop_ready = threading.Event()

    def load_window_filter_toml(self, config_filename:str) -> None:
        with open(config_filename,"rb") as toml_file:
            configs_raw = tomllib.load(toml_file)

        groups:dict[str, WindowGrup] = {}

        has_primary = False
        for name in configs_raw:
            cfg = configs_raw[name]
            grp = WindowGrup(name)
            groups[name] = grp
            if type(cfg) is not dict:
                raise ConfigError("Type of window group config must be dict")
            if "primary" in cfg:
                primary = cfg["primary"]
                if type(primary) is not bool:
                    raise ConfigError("Type of config 'primary' must be bool")
                if primary:
                    if has_primary:
                        raise ConfigError("Only one group can be set as primary")
                    has_primary = True
                    self.primary_group = grp
                    self.primary_group.register_cb_on_add(
                        self.on_primary_group_add
                    )
                    self.primary_group.register_cb_on_remove(
                        self.on_primary_group_remove
                    )
                    grp.primary = True
        if not has_primary:
            raise ConfigError("No primary group is specified")

        for name in groups:
            cfg = configs_raw[name]
            grp = groups[name]

            if "source_groups" not in cfg:
                raise ConfigError(f"Config 'source_group' is not found in '{name}'")
            elif cfg["source_groups"]=="all_windows":
                self.zero_level_groups.append(grp)
            elif type(cfg["source_groups"]) is not list:
                raise ConfigError(
                    "The value of 'source_group' must be a list of group name or 'all_windows'"
                )
            elif len(cfg["source_groups"])==0:
                raise ConfigError("'source_groups' is empty")
            else:
                for source_name in cfg["source_groups"]:
                    if type(source_name) is not str:
                        raise ConfigError("Item of 'source_groups' must be str")
                    if source_name not in groups:
                        raise ConfigError(f"Source group '{source_name}' not found")
                    grp.source_groups.append(groups[source_name])
                    groups[source_name].sink_groups.append(grp)

            if "filter_when" in cfg:
                if type(cfg["filter_when"]) is not str:
                    raise ConfigError("Type of 'filter_when' must be str")
                
                if cfg["filter_when"] == "window_created":
                    grp.only_filter_when_window_created = True
                elif cfg["filter_when"] == "each_update":
                    grp.only_filter_when_window_created = False
                else:
                    ConfigError("Invalid value of 'filter_when'")
            else:
                grp.only_filter_when_window_created = True

            if "filter" not in cfg:
                pass
            elif type(cfg["filter"]) is not dict:
                raise ConfigError(
                    f"Incorrect type of config 'filter'. "
                    f"Expected 'dict', got '{type(cfg['filter']).__name__}'"
                )
            else:
                for filter_name in cfg["filter"]:
                    _filter = quacro_window_filters.generate_filter(
                        filter_name, 
                        cfg["filter"][filter_name],
                    )
                    grp.filters.append(_filter)
                # END for filter_name in cfg["filter"]
        # END for name in groups    

        # DFS, check if there are loop referenced groups or unused groups
        stack:list[WindowGrup] = [self.primary_group]
        walked_names:set[str] = set()
        while stack:
            poped = stack.pop()
            if poped.name in walked_names:
                raise ConfigError(f"Group '{poped.name}' loop referenced")
            walked_names.add(poped.name)
            stack.extend(poped.source_groups)
        
        all_names = set(groups)
        diff = all_names - walked_names
        if diff:
            raise ConfigError(f"Unused window group(s): {diff}")
        
        self.window_groups = groups
    # END def load_window_filter_config

    def on_primary_group_add(self, hwnd:int, all_windows:set[int]) -> None:
        logger.info(f"Window detected: {format_window(hwnd)}")
    
        dock = self.dock_manager.get_dock_by_window(hwnd, default=None)
        if dock is None:
            key = self.dock_manager.identify_window_key(hwnd)
            dock = self.dock_manager.create_dock(key)
        title = quacro_win32.get_window_title(hwnd)
        dock.create_tab(hwnd, title)
        if dock.resolve_sticking_target():
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

        # target is destroyed, try to find next target
        for candidate in dock.tabs:
            quacro_win32.W32.ShowWindow(candidate, win32con.SW_RESTORE)
            if dock.resolve_sticking_target():
                dock.update_misc()
                dock.stick_to_target(move_target=True)
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
        
        if hwnd not in self.primary_group.current_windows:
            return
        
        dock = self.dock_manager.get_dock_by_window(hwnd)

        if event.minimized:
            logger.debug(f"Window minimized: {format_window(hwnd)}")
            if dock.target==event.hwnd:
                dock.target_lost()
            return

        # The window is activated and not minimized
        if not event.inactive: 
            logger.debug(f"Window activated: {format_window(hwnd)}")
            dock.set_sticking_target(hwnd)
            dock.update_misc()
            dock.stick_to_target(move_target=True)
            dock.show(raise_dock_to_top=True)
            
    
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
            else:
                logger.warn(
                    f"Ignoring unknown hook event type '{type(event).__name__}'"
                )

        logger.info("event loop ended")


