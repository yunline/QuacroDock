import typing
import re
import ctypes
import ctypes.wintypes as wintypes
import os

import win32con

from . import quacro_win32
from .quacro_errors import ConfigError


T = typing.TypeVar("T")

class Filter:
    name:str
    def __init__(self, config:dict):
        raise NotImplementedError
    def test(self, hwnd) -> bool:
        raise NotImplementedError

def get_param(
        param_name:str, 
        param_type:type[T], 
        config:dict, 
        filter_name:str,
        default:T|None=None
    ) -> T:
    if param_name not in config:
        if default is None:
            raise ConfigError(f"Filter '{filter_name}' requires parameter '{param_name}'")
        else:
            return default
            
    param = config[param_name]
    if type(param) is not param_type:
        raise ConfigError(f"Type of '{param_name}' must be '{param_type.__name__}'")
    return param

def get_list_param(param_name, config, filter_name, default=None, type_of_items=None, length=None) -> list:
    if param_name not in config:
        if default is None:
            raise ConfigError(f"Filter '{filter_name}' requires parameter '{param_name}'")
        else:
            return default
    
    lst = config[param_name]
    if type(lst) is not list:
        raise ConfigError(f"Type of '{param_name}' must be list")
    if type_of_items is not None:
        for item in lst:
            if type(item) is not type_of_items:
                raise ConfigError(f"Types of items in '{param_name}' must be '{type_of_items.__name__}'")
    if length is not None:
        if len(lst)!=length:
            raise ConfigError(f"Length of '{param_name}' must be {length}")
    return lst.copy()

class _StringFilter(Filter):
    target_name:str
    comparator: str
    regex_pattern: re.Pattern
    def __init__(self, config:dict):
        self.target_name = get_param(
            "target_value", str,
            config, self.name,
        )
        self.comparator = get_param(
            "comparator", str,
            config, self.name, 
            default="eq"
        )
        if self.comparator not in ['eq','ne','regex']:
            raise ConfigError(f"Value of 'comparator' must in ('eq', 'ne', 'regex')")
        if self.comparator=='regex':
            self.regex_pattern = re.compile(self.target_name)
    
    def _compare_str(self, string):
        if self.comparator=="eq":
            return string==self.target_name
        elif self.comparator=="ne":
            return string!=self.target_name
        elif self.comparator=="regex":
            return self.regex_pattern.match(string) is not None
        else:
            raise TypeError("Unexpected comparator")

class ProcessEXENameFilter(_StringFilter):
    name = "process_exe_name"
    
    def test(self, hwnd) -> bool:
        exe_path = quacro_win32.get_window_exe_path(hwnd)
        exe_name = os.path.basename(exe_path)
        return self._compare_str(exe_name)

class WindowClassNameFilter(_StringFilter):
    name = "window_class_name"

    def test(self, hwnd):
        window_classname = quacro_win32.get_window_class_name(hwnd)
        return self._compare_str(window_classname)

class WindowTitleFilter(_StringFilter):
    name = "window_title"

    def test(self, hwnd):
        title = quacro_win32.get_window_title(hwnd)
        return self._compare_str(title)

def get_rect_size(rect: tuple[int,int,int,int]) -> tuple[int,int]:
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    return (width, height)

def tolerant_eq(a, b, t):
    return abs(a-b)<=t

class WindowMinimumSizeFilter(Filter):
    name = "window_minimum_size"
    target_size: tuple[int,int]
    tolerance: int
    comparator: str

    class MINMAXINFO(ctypes.Structure):
        _fields_ = [
            ("ptReserved", wintypes.POINT),
            ("ptMaxSize", wintypes.POINT),
            ("ptMaxPosition", wintypes.POINT),
            ("ptMinTrackSize", wintypes.POINT),
            ("ptMaxTrackSize", wintypes.POINT),
        ]


    def __init__(self, config:dict):
        self.target_size = tuple(
            get_list_param(
                "target_value",
                config, self.name,
                type_of_items=int,
                length=2
            )
        )
        self.tolerance = get_param(
            "tolerance", int,
            config, self.name,
        )
        self.comparator = get_param(
            "comparator", str,
            config, self.name, 
            default="eq"
        )
        if self.comparator not in ['eq','ne']:
            raise ConfigError(f"Value of 'comparator' must in ('eq','ne')")

    
    def test(self, hwnd):
        mmi = self.MINMAXINFO()
        result = quacro_win32.W32.SendMessage(
            hwnd,
            win32con.WM_GETMINMAXINFO,
            0,
            ctypes.byref(mmi)
        )
        if result==0:
            min_w = mmi.ptMinTrackSize.x
            min_h = mmi.ptMinTrackSize.y
        else:
            min_w = 0
            min_h = 0

        if self.comparator=="eq":
            x_fit = tolerant_eq(min_w, self.target_size[0], self.tolerance)
            y_fit = tolerant_eq(min_h, self.target_size[1], self.tolerance)
            return x_fit and y_fit
        else:
            x_unfit = not tolerant_eq(min_w, self.target_size[0], self.tolerance)
            y_unfit = not tolerant_eq(min_h, self.target_size[1], self.tolerance)
            return x_unfit or y_unfit

        

filter_type_dict = {
    "process_exe_name": ProcessEXENameFilter,
    "window_class_name": WindowClassNameFilter,
    "window_minimum_size": WindowMinimumSizeFilter,
    "window_title": WindowTitleFilter
}



def generate_filter(filter_name:str, filter_config:dict) -> Filter:
    if filter_name not in filter_type_dict:
        raise ConfigError(f"Unknown filter type '{filter_name}'")
    if type(filter_config) is not dict:
        raise ConfigError("Type of filter config must be dict")
    filter_type = filter_type_dict[filter_name]
    return filter_type(filter_config)
    

