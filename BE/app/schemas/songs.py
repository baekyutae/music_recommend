"""
VibeCurator Song Schemas
곡 관련 스키마
"""

from typing import List, Optional
from pydantic import BaseModel


class SongItem(BaseModel):
    """곡 정보"""
    song_id: int
    song_name: str
    artist: str
    genre: str
    issue_year: Optional[int] = None


class SongResponse(BaseModel):
    """단일 곡 응답"""
    song: SongItem


class SearchResponse(BaseModel):
    """검색 응답"""
    query: str
    total: int
    items: List[SongItem]

