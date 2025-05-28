import json
from typing import Dict

import redis

from app.controllers.manager.base_manager import TaskManager
from app.models.schema import VideoParams
from app.services import task as tm

FUNC_MAP = {
    "start": tm.start,
}


class RedisTaskManager(TaskManager):
    def __init__(self, maxConcurrentTasks: int, redisUrl: str):
        self.redisClient = redis.Redis.from_url(redisUrl)
        super().__init__(maxConcurrentTasks)

    def createQueue(self):
        return "task_queue"

    def enqueue(self, task: Dict):
        taskWithSerializableParams = task.copy()

        if "params" in task["kwargs"] and isinstance(
            task["kwargs"]["params"], VideoParams
        ):
            taskWithSerializableParams["kwargs"]["params"] = task["kwargs"][
                "params"
            ].dict()

        taskWithSerializableParams["func"] = task["func"].__name__
        self.redisClient.rpush(self.queue, json.dumps(taskWithSerializableParams))

    def dequeue(self):
        taskJson = self.redisClient.lpop(self.queue)
        if taskJson:
            taskInfo = json.loads(taskJson)
            taskInfo["func"] = FUNC_MAP[taskInfo["func"]]

            if "params" in taskInfo["kwargs"] and isinstance(
                taskInfo["kwargs"]["params"], dict
            ):
                taskInfo["kwargs"]["params"] = VideoParams(
                    **taskInfo["kwargs"]["params"]
                )

            return taskInfo
        return None

    def isQueueEmpty(self):
        return self.redisClient.llen(self.queue) == 0
