import typing

from . import quacro_window_filters

WindowGroupCallBack:typing.TypeAlias = typing.Callable[[int,set[int]],None]|None

class WindowGrup:
    filters: list[quacro_window_filters.Filter]
    source_groups: list["WindowGrup"]
    sink_groups: list["WindowGrup"]
    
    only_filter_when_window_created: bool

    cb_on_add: WindowGroupCallBack = None
    cb_on_remove: WindowGroupCallBack = None

    name: str
    current_windows: set[int]

    primary: bool

    def __init__(self, name:str):
        self.name = name
        self.current_windows = set()
        self.sink_groups = []
        self.source_groups = []
        self.filters = []
        self.primary = False
    
    def register_cb_on_add(self, cb:WindowGroupCallBack) -> None:
        self.cb_on_add = cb
    
    def register_cb_on_remove(self, cb:WindowGroupCallBack) -> None:
        self.cb_on_remove = cb
    
    def filter_window(self, hwnd: int) -> bool:
        for filter_ in self.filters:
            if not filter_.test(hwnd):
                return False
        return True

    def _add_window(self, hwnd):
        if hwnd in self.current_windows:
            return
        if self.filter_window(hwnd):
            self.current_windows.add(hwnd)
            if self.cb_on_add is not None:
                self.cb_on_add(hwnd, self.current_windows)
            for group in self.sink_groups:
                group.add_window(hwnd, self.current_windows)
    
    def add_window(self, hwnd:int, all_windows: set[int]):
        if self.only_filter_when_window_created:
            self._add_window(hwnd)
        else:
            for hwnd in all_windows:
                self._add_window(hwnd) 

    def remove_window(self, hwnd:int):
        if hwnd not in self.current_windows:
            return
        self.current_windows.remove(hwnd)
        if self.cb_on_remove is not None:
            self.cb_on_remove(hwnd, self.current_windows)
        for group in self.sink_groups:
            group.remove_window(hwnd)
