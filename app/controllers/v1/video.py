import glob
import os
import pathlib
import shutil
from typing import Union

from fastapi import BackgroundTasks, Depends, Path, Query, Request, UploadFile
from fastapi.params import File
from fastapi.responses import FileResponse, StreamingResponse
from loguru import logger

from app.config import config
from app.controllers import base
from app.controllers.manager.memory_manager import InMemoryTaskManager
from app.controllers.manager.redis_manager import RedisTaskManager
from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.models.schema import (
    AudioRequest,
    BgmRetrieveResponse,
    BgmUploadResponse,
    SubtitleRequest,
    TaskDeletionResponse,
    TaskQueryRequest,
    TaskQueryResponse,
    TaskResponse,
    TaskVideoRequest,
)
from app.services import state as sm
from app.services import task as tm
from app.utils import utils

router = new_router()

enableRedis = config.app.get("enable_redis", False)
redisHost = config.app.get("redis_host", "localhost")
redisPort = config.app.get("redis_port", 6379)
redisDb = config.app.get("redis_db", 0)
redisPassword = config.app.get("redis_password", None)
maxConcurrentTasks = config.app.get("max_concurrent_tasks", 5)

redisUrl = f"redis://:{redisPassword}@{redisHost}:{redisPort}/{redisDb}"
if enableRedis:
    taskManager = RedisTaskManager(
        maxConcurrentTasks=maxConcurrentTasks, redisUrl=redisUrl
    )
else:
    taskManager = InMemoryTaskManager(maxConcurrentTasks=maxConcurrentTasks)


@router.post("/videos", response_model=TaskResponse, summary="Generate a short video")
def createVideo(
    backgroundTasks: BackgroundTasks, request: Request, body: TaskVideoRequest
):
    return createTask(request, body, stopAt="video")


@router.post("/subtitle", response_model=TaskResponse, summary="Generate subtitle only")
def createSubtitle(
    backgroundTasks: BackgroundTasks, request: Request, body: SubtitleRequest
):
    return createTask(request, body, stopAt="subtitle")


@router.post("/audio", response_model=TaskResponse, summary="Generate audio only")
def createAudio(
    backgroundTasks: BackgroundTasks, request: Request, body: AudioRequest
):
    return createTask(request, body, stopAt="audio")


def createTask(
    request: Request,
    body: Union[TaskVideoRequest, SubtitleRequest, AudioRequest],
    stopAt: str,
):
    taskId = utils.getUuid()
    requestId = base.get_task_id(request)
    try:
        task = {
            "task_id": taskId,
            "request_id": requestId,
            "params": body.model_dump(),
        }
        sm.state.update_task(taskId)
        taskManager.addTask(tm.start, task_id=taskId, params=body, stop_at=stopAt)
        logger.success(f"Task created: {utils.toJson(task)}")
        return utils.getResponse(200, task)
    except ValueError as e:
        raise HttpException(
            taskId=taskId, statusCode=400, message=f"{requestId}: {str(e)}"
        )

@router.get("/tasks", response_model=TaskQueryResponse, summary="Get all tasks")
def getAllTasks(request: Request, page: int = Query(1, ge=1), pageSize: int = Query(10, ge=1)):
    requestId = base.get_task_id(request)
    tasks, total = sm.state.get_all_tasks(page, pageSize)

    response = {
        "tasks": tasks,
        "total": total,
        "page": page,
        "page_size": pageSize,
    }
    return utils.getResponse(200, response)



@router.get(
    "/tasks/{task_id}", response_model=TaskQueryResponse, summary="Query task status"
)
def getTask(
    request: Request,
    taskId: str = Path(..., description="Task ID"),
    query: TaskQueryRequest = Depends(),
):
    endpoint = config.app.get("endpoint", "")
    if not endpoint:
        endpoint = str(request.base_url)
    endpoint = endpoint.rstrip("/")

    requestId = base.get_task_id(request)
    task = sm.state.get_task(taskId)
    if task:
        taskDir = utils.taskDir()

        def fileToUri(file):
            if not file.startswith(endpoint):
                uriPath = file.replace(taskDir, "tasks").replace("\\", "/")
                uriPath = f"{endpoint}/{uriPath}"
            else:
                uriPath = file
            return uriPath

        if "videos" in task:
            videos = task["videos"]
            urls = []
            for v in videos:
                urls.append(fileToUri(v))
            task["videos"] = urls
        if "combined_videos" in task:
            combinedVideos = task["combined_videos"]
            urls = []
            for v in combinedVideos:
                urls.append(fileToUri(v))
            task["combined_videos"] = urls
        return utils.getResponse(200, task)

    raise HttpException(
        taskId=taskId, statusCode=404, message=f"{requestId}: task not found"
    )


@router.delete(
    "/tasks/{task_id}",
    response_model=TaskDeletionResponse,
    summary="Delete a generated short video task",
)
def deleteVideo(request: Request, taskId: str = Path(..., description="Task ID")):
    requestId = base.get_task_id(request)
    task = sm.state.get_task(taskId)
    if task:
        tasksDir = utils.taskDir()
        currentTaskDir = os.path.join(tasksDir, taskId)
        if os.path.exists(currentTaskDir):
            shutil.rmtree(currentTaskDir)

        sm.state.delete_task(taskId)
        logger.success(f"Video deleted: {utils.toJson(task)}")
        return utils.getResponse(200)

    raise HttpException(
        taskId=taskId, statusCode=404, message=f"{requestId}: task not found"
    )


@router.get(
    "/musics", response_model=BgmRetrieveResponse, summary="Retrieve local BGM files"
)
def getBgmList(request: Request):
    suffix = "*.mp3"
    songDir = utils.songDir()
    files = glob.glob(os.path.join(songDir, suffix))
    bgmList = []
    for file in files:
        bgmList.append(
            {
                "name": os.path.basename(file),
                "size": os.path.getsize(file),
                "file": file,
            }
        )
    response = {"files": bgmList}
    return utils.getResponse(200, response)


@router.post(
    "/musics",
    response_model=BgmUploadResponse,
    summary="Upload the BGM file to the songs directory",
)
def uploadBgmFile(request: Request, file: UploadFile = File(...)):
    requestId = base.get_task_id(request)
    # check file ext
    if file.filename.endswith("mp3"):
        songDir = utils.songDir()
        savePath = os.path.join(songDir, file.filename)
        # save file
        with open(savePath, "wb+") as buffer:
            # If the file already exists, it will be overwritten
            file.file.seek(0)
            buffer.write(file.file.read())
        response = {"file": savePath}
        return utils.getResponse(200, response)

    raise HttpException(
        "", statusCode=400, message=f"{requestId}: Only *.mp3 files can be uploaded"
    )


@router.get("/stream/{file_path:path}")
async def streamVideo(request: Request, filePath: str):
    tasksDir = utils.taskDir()
    videoPath = os.path.join(tasksDir, filePath)
    rangeHeader = request.headers.get("Range")
    videoSize = os.path.getsize(videoPath)
    start, end = 0, videoSize - 1

    length = videoSize
    if rangeHeader:
        range_ = rangeHeader.split("bytes=")[1]
        start, end = [int(part) if part else None for part in range_.split("-")]
        if start is None:
            start = videoSize - end
            end = videoSize - 1
        if end is None:
            end = videoSize - 1
        length = end - start + 1

    def fileIterator(filePath, offset=0, bytesToRead=None):
        with open(filePath, "rb") as f:
            f.seek(offset, os.SEEK_SET)
            remaining = bytesToRead or videoSize
            while remaining > 0:
                bytesToRead = min(4096, remaining)
                data = f.read(bytesToRead)
                if not data:
                    break
                remaining -= len(data)
                yield data

    response = StreamingResponse(
        fileIterator(videoPath, start, length), media_type="video/mp4"
    )
    response.headers["Content-Range"] = f"bytes {start}-{end}/{videoSize}"
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Length"] = str(length)
    response.status_code = 206  # Partial Content

    return response


@router.get("/download/{file_path:path}")
async def downloadVideo(_: Request, filePath: str):
    """
    download video
    :param _: Request request
    :param filePath: video file path, eg: /cd1727ed-3473-42a2-a7da-4faafafec72b/final-1.mp4
    :return: video file
    """
    tasksDir = utils.taskDir()
    videoPath = os.path.join(tasksDir, filePath)
    filePathObj = pathlib.Path(videoPath)
    filename = filePathObj.stem
    extension = filePathObj.suffix
    headers = {"Content-Disposition": f"attachment; filename={filename}{extension}"}
    return FileResponse(
        path=videoPath,
        headers=headers,
        filename=f"{filename}{extension}",
        media_type=f"video/{extension[1:]}",
    )
