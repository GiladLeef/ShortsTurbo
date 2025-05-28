import traceback
from typing import Any

from loguru import logger


class HttpException(Exception):
    def __init__(
        self, taskId: str, statusCode: int, message: str = "", data: Any = None
    ):
        self.message = message
        self.statusCode = statusCode
        self.data = data
        # Retrieve the exception stack trace information.
        tbStr = traceback.format_exc().strip()
        if not tbStr or tbStr == "NoneType: None":
            msg = f"HttpException: {statusCode}, {taskId}, {message}"
        else:
            msg = f"HttpException: {statusCode}, {taskId}, {message}\n{tbStr}"

        if statusCode == 400:
            logger.warning(msg)
        else:
            logger.error(msg)
