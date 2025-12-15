"""
VibeCurator Common Schemas
공통 스키마
"""

from typing import Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """에러 응답"""
    message: str
    detail: Optional[str] = None

