"""
VibeCurator Songs API
곡 조회 및 검색 라우터
"""

from fastapi import APIRouter, Request, HTTPException, Query
from typing import List

from ..schemas.songs import SongItem, SongResponse, SearchResponse

router = APIRouter(tags=["songs"])


@router.get("/songs/{song_id}", response_model=SongResponse)
async def get_song(request: Request, song_id: int) -> SongResponse:
    """
    곡 정보 조회
    
    - song_id: 조회할 곡 ID
    """
    state = request.app.state
    
    if state.meta_registry is None:
        raise HTTPException(status_code=503, detail="Metadata not loaded")
    
    meta = state.meta_registry.songs.get(song_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    
    return SongResponse(
        song=SongItem(
            song_id=meta.song_id,
            song_name=meta.song_name,
            artist=meta.artist,
            genre=meta.genre,
            issue_year=meta.issue_year
        )
    )


@router.get("/search", response_model=SearchResponse)
async def search_songs(
    request: Request,
    q: str = Query(..., min_length=1, description="검색어"),
    limit: int = Query(default=20, ge=1, le=100, description="결과 개수")
) -> SearchResponse:
    """
    곡 검색 (곡명 + 아티스트)
    
    - q: 검색어 (대소문자 무시)
    - limit: 최대 결과 개수 (1~100)
    """
    state = request.app.state
    
    if state.meta_registry is None:
        raise HTTPException(status_code=503, detail="Metadata not loaded")
    
    # 검색어 정규화
    query_lower = q.lower().strip()
    
    # 검색 인덱스에서 매칭
    results: List[SongItem] = []
    for song_id, search_text in state.meta_registry.search_index:
        if query_lower in search_text:
            meta = state.meta_registry.songs.get(song_id)
            if meta:
                results.append(SongItem(
                    song_id=meta.song_id,
                    song_name=meta.song_name,
                    artist=meta.artist,
                    genre=meta.genre,
                    issue_year=meta.issue_year
                ))
                if len(results) >= limit:
                    break
    
    return SearchResponse(
        query=q,
        total=len(results),
        items=results
    )

