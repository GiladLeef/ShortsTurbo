import os
import shutil
import socket

import toml
from loguru import logger

rootDir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
configFile = f"{rootDir}/config.toml"


def loadConfig():
    if os.path.isdir(configFile):
        shutil.rmtree(configFile)

    if not os.path.isfile(configFile):
        exampleFile = f"{rootDir}/config.example.toml"
        if os.path.isfile(exampleFile):
            shutil.copyfile(exampleFile, configFile)
            logger.info("Copied config.example.toml to config.toml")

    logger.info(f"Loading config from file: {configFile}")

    try:
        config = toml.load(configFile)
    except Exception as e:
        logger.warning(f"Load config failed: {str(e)}, trying to load as utf-8-sig")
        with open(configFile, mode="r", encoding="utf-8-sig") as fp:
            cfgContent = fp.read()
            config = toml.loads(cfgContent)
    return config


def saveConfig():
    with open(configFile, "w", encoding="utf-8") as f:
        cfg["app"] = app
        cfg["azure"] = azure
        cfg["siliconflow"] = siliconflow
        cfg["ui"] = ui
        f.write(toml.dumps(cfg))


cfg = loadConfig()
app = cfg.get("app", {})
whisper = cfg.get("whisper", {})
proxy = cfg.get("proxy", {})
azure = cfg.get("azure", {})
siliconflow = cfg.get("siliconflow", {})
ui = cfg.get("ui", {"hide_log": False})

hostname = socket.gethostname()

logLevel = cfg.get("log_level", "INFO")
listenHost = cfg.get("listen_host", "0.0.0.0")
listenPort = cfg.get("listen_port", 8080)
projectName = cfg.get("project_name", "ShortsTurbo")
projectDescription = cfg.get(
    "project_description",
    "<a href='https://github.com/GiladLeef/ShortsTurbo'>https://github.com/GiladLeef/ShortsTurbo</a>",
)
projectVersion = cfg.get("project_version", "1.0.0")

imagemagickPath = app.get("imagemagick_path", "")
if imagemagickPath and os.path.isfile(imagemagickPath):
    os.environ["IMAGEMAGICK_BINARY"] = imagemagickPath

ffmpegPath = app.get("ffmpeg_path", "")
if ffmpegPath and os.path.isfile(ffmpegPath):
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpegPath

logger.info(f"{projectName} v{projectVersion}")
