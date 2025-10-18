import datetime

from typing import Optional, Union
from enum import StrEnum

__all__ = [
    "Platform",
    "ContentType",
    "Action",
    "Content"
]

class Platform(StrEnum):
  WINDOWS = "windows"
  MACOS = "macos"
  LINUX = "linux"

class ContentType(StrEnum):
  NATIVE = "native" # application
  WEBAPP = "webapp" # online_content
  MEDIA = "media" # media, graphics_art, music, video

class Action: # 仮名
  path: str # URLまたは相対パス

class Content:
  id: str # 要る?
  author: Optional[str]
  name: str
  display_name: Optional[str]

  short_description: Optional[str] # lead
  description: Optional[str]
  thumbnail: Optional[str] # icon

  content_type: ContentType
  supported_platforms: list[Platform]

  action: Union[Action, dict[Platform, Action]]

  last_modified: datetime.datetime