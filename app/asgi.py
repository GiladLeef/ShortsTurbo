"""Application implementation - ASGI."""

import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import config
from app.models.exception import HttpException
from app.router import root_api_router
from app.utils import utils


def exceptionHandler(request: Request, e: HttpException):
    return JSONResponse(
        status_code=e.statusCode,
        content=utils.get_response(e.statusCode, e.data, e.message),
    )


def validationExceptionHandler(request: Request, e: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content=utils.get_response(
            status=400, data=e.errors(), message="field required"
        ),
    )


def getApplication() -> FastAPI:
    """Initialize FastAPI application.

    Returns:
       FastAPI: Application object instance.

    """
    instance = FastAPI(
        title=config.projectName,
        description=config.projectDescription,
        version=config.projectVersion,
        debug=False,
    )
    instance.include_router(root_api_router)
    instance.add_exception_handler(HttpException, exceptionHandler)
    instance.add_exception_handler(RequestValidationError, validationExceptionHandler)
    return instance


app = getApplication()

# Configures the CORS middleware for the FastAPI app
corsAllowedOriginsStr = os.getenv("CORS_ALLOWED_ORIGINS", "")
origins = corsAllowedOriginsStr.split(",") if corsAllowedOriginsStr else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

taskDir = utils.task_dir()
app.mount(
    "/tasks", StaticFiles(directory=taskDir, html=True, follow_symlink=True), name=""
)

publicDir = utils.public_dir()
app.mount("/", StaticFiles(directory=publicDir, html=True), name="")


@app.on_event("shutdown")
def shutdownEvent():
    logger.info("Shutdown event")


@app.on_event("startup")
def startupEvent():
    logger.info("Startup event")
