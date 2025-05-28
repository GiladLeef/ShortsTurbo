import uvicorn
from loguru import logger

from app.config import config

if __name__ == "__main__":
    logger.info(
        "Starting server, docs: http://127.0.0.1:" + str(config.listenPort) + "/docs"
    )
    uvicorn.run(
        app="app.asgi:app",
        host=config.listenHost,
        port=config.listenPort,
        log_level="warning",
    )
