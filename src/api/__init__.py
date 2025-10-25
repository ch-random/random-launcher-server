from typing import Optional

import multiprocessing

import fastapi
from fastapi import APIRouter, Body, Depends, Path, HTTPException
import datetime

from ..abc import *
from ..content import ContentList, ContentManager

__all__ = [
    "api"
    "contents"
]

api = APIRouter()

content_manager = ContentManager()

@api.get("/contents")
async def get_contents(platform: Optional[Platform], contents: ContentList = Depends(content_manager.on_fastapi_depends)):
    """
    (platformが指定されればそのプラットフォームに対応する)すべてのコンテンツのメタデータを返す
    """
    with contents.use() as c:
        print([*c])

@api.get("/content/{content_id}")
async def get_content_meta(content_id: str):
    """
    id == content_id であるコンテンツのメタデータで応答する
    """
    pass

@api.get("/content/{content_id}")
async def get_content_zip(content_id: str):
    """
    id == content_id であるコンテンツのメタデータで応答する
    """
    pass

@api.get("/content/{content_id}/thumbnail")
async def get_content_zip(content_id: str):
    """
    id == content_id であるコンテンツのサムネイル画像で応答する
    """
    pass

@api.get("/updates")
async def updates(since: datetime.datetime):
    """
    since以降に更新/削除されたコンテンツを返す
    """
    pass
