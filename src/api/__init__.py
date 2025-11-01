from typing import Optional

import multiprocessing

import fastapi
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import datetime

import zipfile

from ..abc import *
from ..content import ContentList, ContentManager

__all__ = [
    "api"
    "contents"
]

api = APIRouter()

content_manager = ContentManager()

@api.get("/contents")
async def get_contents(platform: Optional[Platform] = None, contents: ContentList = Depends(content_manager.on_fastapi_depends)):
    """
    (platformが指定されればそのプラットフォームに対応する)すべてのコンテンツのメタデータを返す
    """
    with contents.use() as c:
        return [csrc.content for csrc in c if platform is None or len(csrc.content.supported_platforms) == 0 or platform in csrc.content.supported_platforms]

@api.get("/content/{content_id}")
async def get_content_meta(content_id: str, contents: ContentList = Depends(content_manager.on_fastapi_depends)):
    """
    id == content_id であるコンテンツのメタデータで応答する
    """
    with contents.use() as c:
        for csrc in c:
            if csrc.content.id == content_id:
                return csrc.content
    raise HTTPException(status_code=404, detail="content not found")

@api.get("/content/{content_id}/zip", response_class=FileResponse)
async def get_content_zip(content_id: str, contents: ContentList = Depends(content_manager.on_fastapi_depends)):
    """
    id == content_id であるコンテンツのzipで応答する
    """
    src = None
    with contents.use() as c:
        for csrc in c:
            if csrc.content.id == content_id:
                src = csrc
                break

        if src is None:
            raise HTTPException(status_code=404, detail="content not found")

    return FileResponse(src.path, media_type="application/zip")

@api.get("/content/{content_id}/thumbnail", response_class=StreamingResponse)
async def get_content_thumbnail(content_id: str, contents: ContentList = Depends(content_manager.on_fastapi_depends)):
    """
    id == content_id であるコンテンツのサムネイル画像で応答する
    """
    src = None
    with contents.use() as c:
        for csrc in c:
            if csrc.content.id == content_id:
                src = csrc
                break

        if src is None:
            raise HTTPException(status_code=404, detail="content not found")

        if src.content.thumbnail is None:
            raise HTTPException(status_code=404, detail="no thumbnail")

        with zipfile.ZipFile(src.path) as zf:
            with zf.open(src.content.thumbnail) as f:
                data = f.read()

    async def iterdata():
        for b in data:
            yield b

    return StreamingResponse(iterdata(), media_type="image/*")

@api.get("/updates")
async def updates(since: datetime.datetime, platform: Optional[Platform] = None, contents: ContentList = Depends(content_manager.on_fastapi_depends)):
    """
    since以降に更新/削除されたコンテンツを返す
    """
    since = since.replace(tzinfo=datetime.timezone.utc)
    with contents.use() as c:
        return {
            "updated": [
                csrc.content for csrc in c
                if platform is None or len(csrc.content.supported_platforms) == 0 or platform in csrc.content.supported_platforms
                if csrc.content.last_modified >= since
            ],
            "removed": [
                r for r in c.removed
                if r.last_modified >= since
            ]
        }

