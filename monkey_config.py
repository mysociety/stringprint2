from monkeytype.config import DefaultConfig
from contextlib import contextmanager
from typing import Iterator
import os


class MonkeyConfig(DefaultConfig):
    @contextmanager
    def cli_context(self, command: str) -> Iterator[None]:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proj.settings")
        import django

        django.setup()
        yield


config = MonkeyConfig()
