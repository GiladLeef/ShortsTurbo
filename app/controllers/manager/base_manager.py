import threading
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict
from loguru import logger


class TaskManager(ABC):
    def __init__(self, maxConcurrentTasks: int):
        self.maxConcurrentTasks = maxConcurrentTasks
        self.currentTasks = 0
        self.lock = threading.Lock()
        self.queue = self.createQueue()

    @abstractmethod
    def createQueue(self):
        pass

    def addTask(self, func: Callable, *args: Any, **kwargs: Any):
        with self.lock:
            if self.currentTasks < self.maxConcurrentTasks:
                logger.info(f"Executing task: {func.__name__}, current tasks: {self.currentTasks}")
                self.executeTask(func, *args, **kwargs)
            else:
                logger.info(f"Queueing task: {func.__name__}, current tasks: {self.currentTasks}")
                self.enqueue({"func": func, "args": args, "kwargs": kwargs})

    def executeTask(self, func: Callable, *args: Any, **kwargs: Any):
        thread = threading.Thread(
            target=self.runTask, args=(func, *args), kwargs=kwargs
        )
        thread.start()

    def runTask(self, func: Callable, *args: Any, **kwargs: Any):
        try:
            with self.lock:
                self.currentTasks += 1
            func(*args, **kwargs)
        finally:
            self.taskDone()

    def checkQueue(self):
        with self.lock:
            if (
                self.currentTasks < self.maxConcurrentTasks
                and not self.isQueueEmpty()
            ):
                taskInfo = self.dequeue()
                func = taskInfo["func"]
                args = taskInfo.get("args", ())
                kwargs = taskInfo.get("kwargs", {})
                self.executeTask(func, *args, **kwargs)

    def taskDone(self):
        with self.lock:
            self.currentTasks -= 1
        self.checkQueue()

    @abstractmethod
    def enqueue(self, task: Dict):
        pass

    @abstractmethod
    def dequeue(self):
        pass

    @abstractmethod
    def isQueueEmpty(self):
        pass
