import os
import sys
import logging

logger = logging.getLogger("app_data")

APPDATA_PATH = "./quacro_dock_data"
LOG_PATH = os.path.join(APPDATA_PATH, "logs")

HP_DLL_NAME = "quacro_hook_proc.dll"
HP_DLL_PATH = os.path.join(
    APPDATA_PATH, HP_DLL_NAME
)

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
        logger.info(f"Unable to write '{HP_DLL_PATH}'. Falling back to read and verify")
        
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



