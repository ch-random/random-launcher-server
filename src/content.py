import datetime

import dataclasses
from pydantic import BaseModel

from multiprocessing import Lock

from typing import Optional, Union

from .abc import *

__all__ = [
    "Content",
    "ContentSource",
    "ContentListSafe",
    "ContentList"
]

class Content(BaseModel):
    #id: str # 要る?
    author: Optional[str] = None
    name: str
    display_name: Optional[str] = None

    short_description: Optional[str] = None # lead
    description: Optional[str] = None
    thumbnail: Optional[str] = None # icon

    content_type: ContentType
    supported_platforms: list[Platform]

    action: Union[Action, dict[Platform, Action]]

    last_modified: datetime.datetime

@dataclasses.dataclass
class ContentSource:
    path: str
    content: Content = None

class ContentList:
    def __init__(self, contents: list = None):
        self.lock = Lock()
        if contents is not None:
            self.contents = [*contents]
        else:
            self.contents = []

    def use(self):
        return ContentListSafe(target=self)

class ContentListSafe:
    def __init__(self, target: ContentList):
        self.locked = False
        self.target = target

    def __enter__(self):
        self.target.lock.acquire()
        self.locked = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.locked = False
        self.target.lock.release()

    def handle_content(self, src: ContentSource) -> list[str]:
        paths = []

        if not self.locked:
            raise RuntimeError("only use after locked")

        if src.content is not None:
            total = len(self.target.contents)
            completed = False
            for i in range(total-1, -1, -1):
                target = self.target.contents[i]
                if target.content.name == src.content.name:
                    if not completed:
                        if target.content.last_modified <= src.content.last_modified:
                            self.target.contents[i] = src
                            if src.path != target.path and target.path not in paths:
                                paths.append(target.path)
                        completed = True
                    else:
                        if src.path != target.path and target.path not in paths:
                            paths.append(target.path)
                        self.target.contents.pop(i)
            if not completed:
                self.target.contents.append(src)
        else:
            self.remove_content(src.path)

        return paths

    def remove_content(self, path: str):
        if not self.locked:
            raise RuntimeError("only use after locked")

        total = len(self.target.contents)
        for i in range(total-1, -1, -1):
            if self.target.contents[i].path == path:
                self.target.contents.pop(i)

    def __repr__(self):
        if self.locked:
            return self.target.contents.__repr__()
        else:
            return "<ContentListSafe [unlocked]>"

    def filter(self, func):
        if not self.locked:
            raise RuntimeError("only use after locked")

        return [content for content in self.target.contents if func(content)]

    def __len__(self):
        if not self.locked:
            raise RuntimeError("only use after locked")

        return len(self.target.contents)

    def __getitem__(self, key):
        if not self.locked:
            raise RuntimeError("only use after locked")

        return self.target.contents.__getitem__(key)

    def __iter__(self):
        if not self.locked:
            raise RuntimeError("only use after locked")

        return self.target.contents.__iter__()

class ContentManager:
    def __init__(self, conn = None):
        self.content_list = ContentList()
        self.conn = conn

    def set_connection(self, conn):
        if self.conn is not None:
            try:
                self.conn.close()
            except:
                pass
        self.conn = conn

    def on_fastapi_depends(self):
        if self.conn is not None:
            self.content_sync()

        return self.content_list

    def content_sync(self):
        try:
            with self.content_list.use() as c:
                while self.conn.poll(0):
                    csrc = self.conn.recv()
                    for path in c.handle_content(csrc):
                        self.conn.send(path)
                print(c)
        except EOFError:
            # connection closed
            self.conn = None