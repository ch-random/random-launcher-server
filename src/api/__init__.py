from typing import Optional

import fastapi
from fastapi import APIRouter, Body, Path, HTTPException
import datetime

from ..abc import *

api = APIRouter()

__all__ = [
    "api"
]

@api.get("/contents")
async def get_contents(platform: Optional[Platform]):
  """
  (platformが指定されればそのプラットフォームに対応する)すべてのコンテンツのメタデータを返す
  """
  pass

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
