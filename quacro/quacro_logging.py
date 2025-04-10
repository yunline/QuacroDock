import logging
import traceback

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


LOG_TB_LEN = 3
def warn_tb(logger:logging.Logger, message, level=1):
    stack = traceback.extract_stack(limit=level+LOG_TB_LEN)[:-level]
    tb = ''.join(traceback.format_list(stack))
    logger.warning(f'Warning: {message}\n{tb.rstrip()}')


