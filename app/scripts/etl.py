import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    while True:
        time.sleep(1)
        logger.warning(datetime.now())
