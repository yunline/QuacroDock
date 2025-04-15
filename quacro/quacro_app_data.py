import os
import sys
import logging
import typing
import json

logger = logging.getLogger("app_data")

APPDATA_PATH = "./quacro_dock_data"
LOG_PATH = os.path.join(APPDATA_PATH, "logs")

HP_DLL_NAME = "quacro_hook_proc.dll"
HP_DLL_PATH = os.path.join(
    APPDATA_PATH, HP_DLL_NAME
)

CACHE_PATH = os.path.join(APPDATA_PATH, "quacro_cache.json")

CACHE_KEY_NULL = "NULL"
CACHE_KEY_DOCK_WIDTH = "DOCK_WIDTH"

def create_dir_if_not_exist(path):
    if not os.path.exists(path):
        logger.info(f"Creating dir '{path}")
        os.mkdir(path)
    elif os.path.isfile(path):
        raise OSError(
            f"Unable to create dir '{path}' "
            f"since a file have the same name has been exist"
        )

def init_app_data():
    create_dir_if_not_exist(APPDATA_PATH)
    create_dir_if_not_exist(LOG_PATH)
    cache_get(CACHE_KEY_NULL, None) # init cache file


def extract_hook_proc_dll():
    if getattr(sys, "frozen", False): # when running as exe
       HP_DLL_SRC_PATH = os.path.join(
           sys._MEIPASS, HP_DLL_NAME
        )
    else: # when running as python script
        HP_DLL_SRC_PATH = os.path.join(
           "./", HP_DLL_NAME
        )
    
    src_file = open(HP_DLL_SRC_PATH, "rb")

    try:
        dst_file = open(HP_DLL_PATH, "wb")
    except:
        logger.warning(f"Unable to write '{HP_DLL_PATH}'")
        logger.info("Falling back to read and verify")
        
        dst_file = open(HP_DLL_PATH, "rb")

        if dst_file.read()!=src_file.read():
            dst_file.close()
            raise OSError("Unable to extract hook proc dll")
        logger.info(f"Hook proc dll is verified")
    else:
        dst_file.write(src_file.read())
        logger.info(f"Hook proc dll is extracted")
    finally:
        src_file.close()
    dst_file.close()

def _load_cache_json() -> dict[str, typing.Any]:
    data: dict[str, typing.Any]
    try:
        cache_file = open(CACHE_PATH, "+r", encoding="utf8")
    except FileNotFoundError as err:
        logger.warning(f"Error when reading cache: {err}")
        logger.info(f"Overwriting the cache file")
        try:
            with open(CACHE_PATH, "w", encoding="utf8") as cache_file:
                data = {}
                json.dump(data, cache_file)
        except Exception as err:
            logger.error(f"Unable to write the cache: {err}")
    except Exception as err:
        logger.error(f"Unable to open cache: {err}")
    else:
        try:
            data = json.load(cache_file)
            if type(data) is not dict:
                raise ValueError("Invalid type of cache data")
        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            ValueError,
        ) as err:
            logger.warning(f"Error when decoding cache json: {err}")
            logger.info(f"Overwriting the cache file")
            cache_file.seek(0)
            cache_file.truncate()
            data = {}
            json.dump(data, cache_file)
        finally:
            cache_file.close()
    return data

_cache_data:dict[str, typing.Any]|None = None

T = typing.TypeVar("T")

def cache_get(key:str, default:T) -> T:
    global _cache_data
    if _cache_data is None:
        _cache_data = _load_cache_json()

    if key in _cache_data:
        value = _cache_data[key]
        if type(value) is not type(default):
            return default
        return value
    return default

def cache_set(key:str, value:typing.Any):
    global _cache_data
    if _cache_data is None:
        _cache_data = _load_cache_json()
    _cache_data[key] = value
    try:
        with open(CACHE_PATH, "w") as cache_file:
            json.dump(_cache_data, cache_file)
    except Exception as err:
        logger.error(f"Unable to write the cache: {err}")



