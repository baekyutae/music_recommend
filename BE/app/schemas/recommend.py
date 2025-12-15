"""
VibeCurator Recommendation Schemas
추천 관련 스키마
"""

from typing import List, Optional
from pydantic import BaseModel


class SeedInfo(BaseModel):
    """시드 곡 정보"""
    song_id: int
    song_name: str
    artist: str
    genre: str


class RecommendItem(BaseModel):
    """추천 결과 항목"""
    rank: int
    song_id: int
    song_name: str
    artist: str
    genre: str
    score: float


class RecommendResponse(BaseModel):
    """추천 응답"""
    engine_version: str
    audio_model: str
    cached: bool
    method: str  # "demo" | "cf_only" | "hybrid"
    seed: SeedInfo
    items: List[RecommendItem]

