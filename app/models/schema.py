import warnings
from enum import Enum
from typing import Any, List, Optional, Union

import pydantic
from pydantic import BaseModel

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Field name.*shadows an attribute in parent.*",
)


class VideoConcatMode(str, Enum):
    random = "random"
    sequential = "sequential"


class VideoTransitionMode(str, Enum):
    none = None
    fadeIn = "FadeIn"
    fadeOut = "FadeOut"


class VideoAspect(str, Enum):
    landscape = "16:9"
    portrait = "9:16"
    square = "1:1"

    def to_resolution(self):
        resolutions = {
            VideoAspect.landscape.value: (1920, 1080),
            VideoAspect.portrait.value: (1080, 1920),
            VideoAspect.square.value: (1080, 1080),
        }
        return resolutions.get(self, (1080, 1920))


class _Config:
    arbitrary_types_allowed = True


@pydantic.dataclasses.dataclass(config=_Config)
class MaterialInfo:
    provider: str = "pexels"
    url: str = ""
    duration: int = 0


class BaseVideoParams(BaseModel):
    videoScript: str
    videoLanguage: Optional[str] = ""
    voiceName: Optional[str] = "zh-CN-XiaoxiaoNeural-Female"
    voiceVolume: Optional[float] = 1.0
    voiceRate: Optional[float] = 1.2
    bgmType: Optional[str] = "random"
    bgmFile: Optional[str] = ""
    bgmVolume: Optional[float] = 0.2
    videoSource: Optional[str] = "local"


class VideoParams(BaseVideoParams):
    videoSubject: str
    videoTerms: Optional[str | list] = None
    originalFilename: Optional[str] = None
    videoAspect: Optional[VideoAspect] = VideoAspect.portrait.value
    videoConcatMode: Optional[VideoConcatMode] = VideoConcatMode.random.value
    videoTransitionMode: Optional[VideoTransitionMode] = None
    videoClipDuration: Optional[int] = 5
    videoCount: Optional[int] = 1
    videoMaterials: Optional[List[MaterialInfo]] = None

    subtitleEnabled: Optional[bool] = True
    subtitlePosition: Optional[str] = "bottom"
    customPosition: float = 70.0
    fontName: Optional[str] = "STHeitiMedium.ttc"
    textForeColor: Optional[str] = "#FFFFFF"
    textBackgroundColor: Union[bool, str] = True
    fontSize: int = 60
    strokeColor: Optional[str] = "#000000"
    strokeWidth: float = 1.5
    nThreads: Optional[int] = 2
    paragraphNumber: Optional[int] = 1


class SubtitleRequest(BaseVideoParams):
    subtitlePosition: Optional[str] = "bottom"
    fontName: Optional[str] = "STHeitiMedium.ttc"
    textForeColor: Optional[str] = "#FFFFFF"
    textBackgroundColor: Union[bool, str] = True
    fontSize: int = 60
    strokeColor: Optional[str] = "#000000"
    strokeWidth: float = 1.5
    subtitleEnabled: Optional[str] = "true"


class AudioRequest(BaseVideoParams):
    pass


class BaseResponse(BaseModel):
    status: int = 200
    message: Optional[str] = "success"
    data: Any = None


class TaskVideoRequest(VideoParams):
    pass


class TaskQueryRequest(BaseModel):
    pass


class VideoScriptParams:
    videoSubject: Optional[str] = "Spring flower field"
    videoLanguage: Optional[str] = ""
    paragraphNumber: Optional[int] = 1


class VideoTermsParams:
    videoSubject: Optional[str] = "Spring flower field"
    videoScript: Optional[str] = (
        "Spring flower field, displayed like a poem and painting. In the season of revival of all things, the earth is dressed in a gorgeous and colorful costume. Golden spring flowers, pink cherry blossoms, white pear blossoms, gorgeous tulips..."
    )
    amount: Optional[int] = 5


class VideoScriptRequest(VideoScriptParams, BaseModel):
    pass


class VideoTermsRequest(VideoTermsParams, BaseModel):
    pass


class TaskResponse(BaseResponse):
    class TaskResponseData(BaseModel):
        taskId: str

    data: TaskResponseData

    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {"taskId": "6c85c8cc-a77a-42b9-bc30-947815aa0558"},
            },
        }


class TaskQueryResponse(BaseResponse):
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {
                    "state": 1,
                    "progress": 100,
                    "videos": [
                        "http://127.0.0.1:8080/tasks/6c85c8cc-a77a-42b9-bc30-947815aa0558/final-1.mp4"
                    ],
                    "combinedVideos": [
                        "http://127.0.0.1:8080/tasks/6c85c8cc-a77a-42b9-bc30-947815aa0558/combined-1.mp4"
                    ],
                },
            },
        }


class TaskDeletionResponse(BaseResponse):
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {
                    "state": 1,
                    "progress": 100,
                    "videos": [
                        "http://127.0.0.1:8080/tasks/6c85c8cc-a77a-42b9-bc30-947815aa0558/final-1.mp4"
                    ],
                    "combinedVideos": [
                        "http://127.0.0.1:8080/tasks/6c85c8cc-a77a-42b9-bc30-947815aa0558/combined-1.mp4"
                    ],
                },
            },
        }


class VideoScriptResponse(BaseResponse):
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {
                    "video_script": "Spring flower field, is a beautiful painting of nature. In this season, the earth wakes up, everything grows, flowers bloom, forming a colorful sea of flowers..."
                },
            },
        }


class VideoTermsResponse(BaseResponse):
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {"video_terms": ["sky", "tree"]},
            },
        }


class BgmRetrieveResponse(BaseResponse):
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {
                    "files": [
                        {
                            "name": "example.mp3",
                            "size": 1891269,
                            "file": "/ShortsTurbo/resource/songs/example.mp3",
                        }
                    ]
                },
            },
        }


class BgmUploadResponse(BaseResponse):
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {"file": "/ShortsTurbo/resource/songs/example.mp3"},
            },
        }
