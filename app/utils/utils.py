import json
import locale
import os
from pathlib import Path
import threading
from typing import Any
from uuid import uuid4

import urllib3
from loguru import logger

from app.models import const

urllib3.disable_warnings()


def getResponse(status: int, data: Any = None, message: str = ""):
    obj = {"status": status}
    if data:
        obj["data"] = data
    if message:
        obj["message"] = message
    return obj


def toJson(obj):
    try:
        def serialize(o):
            if isinstance(o, (int, float, bool, str)) or o is None:
                return o
            elif isinstance(o, bytes):
                return "*** binary data ***"
            elif isinstance(o, dict):
                return {k: serialize(v) for k, v in o.items()}
            elif isinstance(o, (list, tuple)):
                return [serialize(item) for item in o]
            elif hasattr(o, "__dict__"):
                return serialize(o.__dict__)
            else:
                return None

        serializedObj = serialize(obj)
        return json.dumps(serializedObj, ensure_ascii=False, indent=4)
    except Exception:
        return None


def getUuid(removeHyphen: bool = False):
    u = str(uuid4())
    if removeHyphen:
        u = u.replace("-", "")
    return u


def rootDir():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def storageDir(subDir: str = "", create: bool = False):
    d = os.path.join(rootDir(), "storage")
    if subDir:
        d = os.path.join(d, subDir)
    if create and not os.path.exists(d):
        os.makedirs(d)
    return d


def resourceDir(subDir: str = ""):
    d = os.path.join(rootDir(), "resource")
    if subDir:
        d = os.path.join(d, subDir)
    return d


def taskDir(subDir: str = ""):
    d = os.path.join(storageDir(), "tasks")
    if subDir:
        d = os.path.join(d, subDir)
    if not os.path.exists(d):
        os.makedirs(d)
    return d


def fontDir(subDir: str = ""):
    d = resourceDir("fonts")
    if subDir:
        d = os.path.join(d, subDir)
    if not os.path.exists(d):
        os.makedirs(d)
    return d


def songDir(subDir: str = ""):
    d = resourceDir("songs")
    if subDir:
        d = os.path.join(d, subDir)
    if not os.path.exists(d):
        os.makedirs(d)
    return d


def publicDir(subDir: str = ""):
    d = resourceDir("public")
    if subDir:
        d = os.path.join(d, subDir)
    if not os.path.exists(d):
        os.makedirs(d)
    return d


def runInBackground(func, *args, **kwargs):
    def run():
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Background task error: {e}")

    thread = threading.Thread(target=run)
    thread.start()
    return thread


def timeConvertSecondsToHmsm(seconds) -> str:
    hours = int(seconds // 3600)
    seconds = seconds % 3600
    minutes = int(seconds // 60)
    milliseconds = int(seconds * 1000) % 1000
    seconds = int(seconds % 60)
    return "{:02d}:{:02d}:{:02d},{:03d}".format(hours, minutes, seconds, milliseconds)


def textToSrt(idx: int, msg: str, startTime: float, endTime: float) -> str:
    startTimeStr = timeConvertSecondsToHmsm(startTime)
    endTimeStr = timeConvertSecondsToHmsm(endTime)
    srt = """%d
%s --> %s
%s
        """ % (idx, startTimeStr, endTimeStr, msg)
    return srt


def strContainsPunctuation(word):
    for p in const.PUNCTUATIONS:
        if p in word:
            return True
    return False


def splitStringByPunctuations(s):
    result = []
    txt = ""

    previousChar = ""
    nextChar = ""
    for i in range(len(s)):
        char = s[i]
        if char == "\n":
            result.append(txt.strip())
            txt = ""
            continue

        if i > 0:
            previousChar = s[i - 1]
        if i < len(s) - 1:
            nextChar = s[i + 1]

        if char == "." and previousChar.isdigit() and nextChar.isdigit():
            txt += char
            continue

        if char not in const.PUNCTUATIONS:
            txt += char
        else:
            result.append(txt.strip())
            txt = ""
    result.append(txt.strip())
    result = list(filter(None, result))
    return result


def md5(text):
    import hashlib
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def getSystemLocale():
    try:
        loc = locale.getdefaultlocale()
        languageCode = loc[0].split("_")[0]
        return languageCode
    except Exception:
        return "en"


def parseExtension(filename):
    return Path(filename).suffix.lower().lstrip('.')
