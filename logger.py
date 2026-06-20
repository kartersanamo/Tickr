from __future__ import annotations

import datetime
import logging
import logging.config
import os
from logging.handlers import TimedRotatingFileHandler

import pytz
from pytz.tzinfo import BaseTzInfo


class TickrLogging:
    GRAY: str = "\033[90m"
    LIGHT_PINK: str = "\033[95m"
    RESET: str = "\033[0m"
    TIMEZONE: BaseTzInfo = pytz.timezone(zone="US/Eastern")

    class ESTFormatter(logging.Formatter):
        def formatTime(
            self,
            record: logging.LogRecord,
            datefmt: str | None = None,
        ) -> str:
            dt = datetime.datetime.fromtimestamp(record.created, TickrLogging.TIMEZONE)
            if datefmt:
                return dt.strftime(datefmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S.%f EST")

    class RotatingFileHandler(TimedRotatingFileHandler):
        def __init__(
            self,
            filename: str,
            when: str = "midnight",
            interval: int = 1,
            backupCount: int = 7,
            encoding: str | None = None,
            delay: bool = False,
            utc: bool = False,
            atTime: datetime.time | None = None,
        ) -> None:
            super().__init__(
                filename=filename,
                when=when,
                interval=interval,
                backupCount=backupCount,
                encoding=encoding,
                delay=delay,
                utc=utc,
                atTime=atTime,
            )
            if not hasattr(self, "suffix"):
                self.suffix = "%Y-%m-%d"

        def doRollover(self) -> None:
            if self.stream:
                self.stream.close()
                self.stream = None  # type: ignore[assignment]
            current_time = int(self.rolloverAt - self.interval)
            dt = datetime.datetime.fromtimestamp(current_time, TickrLogging.TIMEZONE)
            self.baseFilename = dt.strftime(self.suffix)
            if self.backupCount > 0:
                for path in self.getFilesToDelete():
                    os.remove(path)
            self.mode = "w"
            self.stream = self._open()
            self.rolloverAt = self.rolloverAt + self.interval

    def __init__(self, logs_dir: str = "logs") -> None:
        self._logs_dir = logs_dir
        self._configured = False

    @property
    def log_filename(self) -> str:
        current_time = datetime.datetime.now(TickrLogging.TIMEZONE)
        return f"{self._logs_dir}/{current_time.strftime('%Y-%m-%d')}.log"

    def build_config(self) -> dict[str, object]:
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "file": {
                    "format": "%(levelname)-10s %(asctime)s %(funcName)-15s : %(message)s",
                    "()": TickrLogging.ESTFormatter,
                },
                "standard": {
                    "format": (
                        f"{TickrLogging.GRAY}%(asctime)s{TickrLogging.RESET} "
                        f"%(levelname)-8s {TickrLogging.LIGHT_PINK}%(name)s"
                        f"{TickrLogging.RESET} %(message)s"
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                    "()": TickrLogging.ESTFormatter,
                },
            },
            "handlers": {
                "console": {
                    "level": "DEBUG",
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                },
                "file": {
                    "level": "DEBUG",
                    "()": TickrLogging.RotatingFileHandler,
                    "filename": self.log_filename,
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": 7,
                    "formatter": "file",
                },
            },
            "loggers": {
                "Tasks": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "Commands": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "discord": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }

    def configure(self) -> None:
        if self._configured:
            return
        os.makedirs(self._logs_dir, exist_ok=True)
        logging.config.dictConfig(config=self.build_config())
        self._configured = True

    def get_logger(self, name: str) -> logging.Logger:
        self.configure()
        return logging.getLogger(name)


tickr_logging = TickrLogging()
tickr_logging.configure()
