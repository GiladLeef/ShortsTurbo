import math
import os.path
import re
from os import path

from loguru import logger

from app.config import config
from app.models import const
from app.models.schema import VideoConcatMode, VideoParams
from app.services import material, subtitle, video, voice
from app.services import state as sm
from app.utils import utils


def generateScript(taskId, params):
    logger.info("Generating video script")
    videoScript = params.videoScript.strip()
    if not videoScript:
        logger.error("No script provided and automatic script generation is disabled")
        return None
    
    if not videoScript:
        sm.state.update_task(taskId, state=const.TASK_STATE_FAILED)
        logger.error("Failed to generate video script")
        return None

    return videoScript


def generateTerms(taskId, params, videoScript):
    logger.info("Generating video terms")
    videoTerms = params.videoTerms
    
    if not videoTerms:
        if hasattr(params, 'originalFilename') and params.originalFilename:
            filename = params.originalFilename
            baseName = re.sub(r'\.txt$', '', filename)
            extractedTerms = re.sub(r'[_\-]', ' ', baseName).split()
            videoTerms = extractedTerms + ["nature", "landscape", "people", "business"]
        else:
            videoTerms = ["scenery", "people", "city", "nature", "business", "technology"]
    else:
        if isinstance(videoTerms, str):
            if len(videoTerms) > 100 and '\n' in videoTerms:
                if hasattr(params, 'originalFilename') and params.originalFilename:
                    filename = params.originalFilename
                    baseName = re.sub(r'\.txt$', '', filename)
                    extractedTerms = re.sub(r'[_\-]', ' ', baseName).split()
                    videoTerms = extractedTerms + ["nature", "landscape", "people", "business"]
                else:
                    videoTerms = ["scenery", "people", "city", "nature", "business", "technology"]
            else:
                videoTerms = [term.strip() for term in re.split(r'[,，]', videoTerms)]
        elif isinstance(videoTerms, list):
            videoTerms = [term.strip() for term in videoTerms]
        else:
            videoTerms = ["scenery", "people", "city", "nature", "business", "technology"]

    logger.info(f"Using search terms: {videoTerms}")

    if not videoTerms:
        videoTerms = ["scenery", "people", "city", "nature", "business", "technology"]
        logger.info(f"Using default search terms: {videoTerms}")

    return videoTerms


def saveScriptData(taskId, videoScript, videoTerms, params):
    scriptFile = path.join(utils.taskDir(taskId), "script.json")
    scriptData = {
        "video_script": videoScript,
        "video_terms": params.videoTerms,
        "video_subject": params.videoSubject,
    }

    with open(scriptFile, "w", encoding="utf-8") as f:
        f.write(utils.toJson(scriptData))


def generateAudio(taskId, params, videoScript):
    logger.info("Generating audio")
    audioFile = path.join(utils.taskDir(taskId), "audio.mp3")
    subMaker = voice.tts(
        text=videoScript,
        voice_name=voice.parse_voice_name(params.voiceName),
        voice_rate=params.voiceRate,
        voice_file=audioFile,
    )
    if subMaker is None:
        sm.state.update_task(taskId, state=const.TASK_STATE_FAILED)
        logger.error("Failed to generate audio. Check if the voice language matches the script language or if network is available.")
        return None, None, None

    audioDuration = math.ceil(voice.get_audio_duration(subMaker))
    return audioFile, audioDuration, subMaker


def generateSubtitle(taskId, params, videoScript, subMaker, audioFile):
    if not params.subtitleEnabled:
        return ""

    subtitlePath = path.join(utils.taskDir(taskId), "subtitle.srt")
    subtitleProvider = config.app.get("subtitle_provider", "edge").strip().lower()
    logger.info(f"Generating subtitle, provider: {subtitleProvider}")

    subtitleFallback = False
    if subtitleProvider == "edge":
        voice.create_subtitle(
            text=videoScript, sub_maker=subMaker, subtitle_file=subtitlePath
        )
        if not os.path.exists(subtitlePath):
            subtitleFallback = True
            logger.warning("Subtitle file not found, fallback to whisper")

    if subtitleProvider == "whisper" or subtitleFallback:
        subtitle.create(audio_file=audioFile, subtitle_file=subtitlePath)
        logger.info("Correcting subtitle")
        subtitle.correct(subtitle_file=subtitlePath, video_script=videoScript)

    subtitleLines = subtitle.file_to_subtitles(subtitlePath)
    if not subtitleLines:
        logger.warning(f"Subtitle file is invalid: {subtitlePath}")
        return ""

    return subtitlePath


def getVideoMaterials(taskId, params, videoTerms, audioDuration):
    if params.videoSource == "local":
        logger.info("Preprocessing local materials")
        materials = video.preprocess_video(
            materials=params.videoMaterials, clip_duration=params.videoClipDuration
        )
        if not materials:
            sm.state.update_task(taskId, state=const.TASK_STATE_FAILED)
            logger.error("No valid materials found, please check the materials and try again")
            return None
        return [materialInfo.url for materialInfo in materials]
    else:
        logger.info(f"Downloading videos from {params.videoSource}")
        downloadedVideos = material.download_videos(
            task_id=taskId,
            search_terms=videoTerms,
            source=params.videoSource,
            video_aspect=params.videoAspect,
            video_contact_mode=params.videoConcatMode,
            audio_duration=audioDuration * params.videoCount,
            max_clip_duration=params.videoClipDuration,
        )
        if not downloadedVideos:
            sm.state.update_task(taskId, state=const.TASK_STATE_FAILED)
            logger.error("Failed to download videos, maybe the network is not available. If you are in China, please use a VPN")
            return None
        return downloadedVideos


def generateFinalVideos(taskId, params, downloadedVideos, audioFile, subtitlePath):
    finalVideoPaths = []
    combinedVideoPaths = []
    videoConcatMode = (
        params.videoConcatMode if params.videoCount == 1 else VideoConcatMode.random
    )
    videoTransitionMode = params.videoTransitionMode

    progress = 50
    for i in range(params.videoCount):
        index = i + 1
        combinedVideoPath = path.join(
            utils.taskDir(taskId), f"combined-{index}.mp4"
        )
        logger.info(f"Combining video: {index} => {combinedVideoPath}")
        video.combine_videos(
            combined_video_path=combinedVideoPath,
            video_paths=downloadedVideos,
            audio_file=audioFile,
            video_aspect=params.videoAspect,
            video_concat_mode=videoConcatMode,
            video_transition_mode=videoTransitionMode,
            max_clip_duration=params.videoClipDuration,
            threads=params.nThreads,
        )

        progress += 50 / params.videoCount / 2
        sm.state.update_task(taskId, progress=progress)

        finalVideoPath = path.join(utils.taskDir(taskId), f"final-{index}.mp4")

        logger.info(f"Generating video: {index} => {finalVideoPath}")
        video.generate_video(
            video_path=combinedVideoPath,
            audio_path=audioFile,
            subtitle_path=subtitlePath,
            output_file=finalVideoPath,
            params=params,
        )

        progress += 50 / params.videoCount / 2
        sm.state.update_task(taskId, progress=progress)

        finalVideoPaths.append(finalVideoPath)
        combinedVideoPaths.append(combinedVideoPath)

    return finalVideoPaths, combinedVideoPaths


def start(taskId, params: VideoParams, stopAt: str = "video"):
    logger.info(f"Starting task: {taskId}, stop at: {stopAt}")
    sm.state.update_task(taskId, state=const.TASK_STATE_PROCESSING, progress=5)

    if type(params.videoConcatMode) is str:
        params.videoConcatMode = VideoConcatMode(params.videoConcatMode)

    videoScript = generateScript(taskId, params)
    if not videoScript or "Error: " in videoScript:
        sm.state.update_task(taskId, state=const.TASK_STATE_FAILED)
        return

    sm.state.update_task(taskId, state=const.TASK_STATE_PROCESSING, progress=10)

    if stopAt == "script":
        sm.state.update_task(
            taskId, state=const.TASK_STATE_COMPLETE, progress=100, script=videoScript
        )
        return {"script": videoScript}

    videoTerms = ""
    if params.videoSource != "local":
        videoTerms = generateTerms(taskId, params, videoScript)
        if not videoTerms:
            sm.state.update_task(taskId, state=const.TASK_STATE_FAILED)
            return

    saveScriptData(taskId, videoScript, videoTerms, params)

    if stopAt == "terms":
        sm.state.update_task(
            taskId, state=const.TASK_STATE_COMPLETE, progress=100, terms=videoTerms
        )
        return {"script": videoScript, "terms": videoTerms}

    sm.state.update_task(taskId, state=const.TASK_STATE_PROCESSING, progress=20)

    audioFile, audioDuration, subMaker = generateAudio(taskId, params, videoScript)
    if not audioFile:
        sm.state.update_task(taskId, state=const.TASK_STATE_FAILED)
        return

    sm.state.update_task(taskId, state=const.TASK_STATE_PROCESSING, progress=30)

    if stopAt == "audio":
        sm.state.update_task(
            taskId,
            state=const.TASK_STATE_COMPLETE,
            progress=100,
            audio_file=audioFile,
        )
        return {"audio_file": audioFile, "audio_duration": audioDuration}

    subtitlePath = generateSubtitle(taskId, params, videoScript, subMaker, audioFile)

    if stopAt == "subtitle":
        sm.state.update_task(
            taskId,
            state=const.TASK_STATE_COMPLETE,
            progress=100,
            subtitle_path=subtitlePath,
        )
        return {"subtitle_path": subtitlePath}

    sm.state.update_task(taskId, state=const.TASK_STATE_PROCESSING, progress=40)

    downloadedVideos = getVideoMaterials(taskId, params, videoTerms, audioDuration)
    if not downloadedVideos:
        sm.state.update_task(taskId, state=const.TASK_STATE_FAILED)
        return

    if stopAt == "materials":
        sm.state.update_task(
            taskId,
            state=const.TASK_STATE_COMPLETE,
            progress=100,
            materials=downloadedVideos,
        )
        return {"materials": downloadedVideos}

    sm.state.update_task(taskId, state=const.TASK_STATE_PROCESSING, progress=50)

    finalVideoPaths, combinedVideoPaths = generateFinalVideos(
        taskId, params, downloadedVideos, audioFile, subtitlePath
    )

    if not finalVideoPaths:
        sm.state.update_task(taskId, state=const.TASK_STATE_FAILED)
        return

    logger.success(f"Task {taskId} finished, generated {len(finalVideoPaths)} videos")

    kwargs = {
        "videos": finalVideoPaths,
        "combined_videos": combinedVideoPaths,
        "script": videoScript,
        "terms": videoTerms,
        "audio_file": audioFile,
        "audio_duration": audioDuration,
        "subtitle_path": subtitlePath,
        "materials": downloadedVideos,
    }
    sm.state.update_task(
        taskId, state=const.TASK_STATE_COMPLETE, progress=100, **kwargs
    )
    return kwargs
