import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class SearchQueryValidator(BaseModel):
    q: str = Field(..., min_length=1, max_length=200)
    limit: Optional[int] = Field(default=16, ge=1, le=50)

    @field_validator("q")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        cleaned = re.sub(r'[<>"\'\x00-\x1f]', "", v.strip())
        if not cleaned:
            raise ValueError("Query string contains only invalid or control characters.")
        return cleaned

class VideoIDValidator(BaseModel):
    id: str = Field(..., pattern=r"^[A-Za-z0-9_-]{11}$")

class LyricsQueryValidator(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    artist: str = Field(..., min_length=1, max_length=200)
    duration: Optional[float] = Field(default=None, ge=0, le=7200)

    @field_validator("title", "artist")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        return re.sub(r'[<>"\'\x00-\x1f]', "", v.strip())

class UserCredentialsValidator(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number.")
        return v
