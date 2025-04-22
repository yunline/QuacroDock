import logging
import traceback
import sys
import threading

if __debug__:
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO

def setup_log_config():
    logging.addLevelName(logging.DEBUG, "DBG")
    logging.addLevelName(logging.INFO, "INF")
    logging.addLevelName(logging.WARN, "WRN")
    logging.addLevelName(logging.ERROR, "ERR")
    logging.addLevelName(logging.FATAL, "FTL")

    logging.basicConfig(
        level=LOG_LEVEL,
        format = '[%(levelname)s] %(name)s: %(message)s'
    )

def set_except_hook(logger:logging.Logger):
    def sys_hook(exc_type, exc_value, exc_traceback):
        tb_list = traceback.format_exception(exc_type, exc_value, exc_traceback)
        logger.error(f"Unhandled exception:\n{''.join(tb_list)}")
    sys.excepthook = sys_hook
    
    def threading_hook(args):
        tb_list = traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
        logger.error(f"Unhandled exception in thread {args.thread.name}:\n{''.join(tb_list)}")
    threading.excepthook = threading_hook

LOG_TB_LEN = 3
def warn_tb(logger:logging.Logger, message, level=1):
    stack = traceback.extract_stack(limit=level+LOG_TB_LEN)[:-level]
    tb = ''.join(traceback.format_list(stack))
    logger.warning(f'Warning: {message}\n{tb.rstrip()}')


