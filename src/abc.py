import dataclasses
from enum import StrEnum

__all__ = [
    "Platform",
    "ContentType",
    "CategoryType",
    "Action"
]

class Platform(StrEnum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"

class ContentType(StrEnum):
    NATIVE = "native" # application
    WEBAPP = "webapp" # online_content
    MEDIA = "media" # media, graphics_art, music, video

class CategoryType(StrEnum):
    COMMON = "common" # その他
    GAME = "game"
    MUSIC = "music"
    VIDEO = "video"
    ART = "art"

@dataclasses.dataclass
class Action: # 仮名
    path: str # URLまたは相対パス
