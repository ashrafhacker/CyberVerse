from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


class GameChallengeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str
    category: str
    difficulty: str = Field(..., pattern="^(Beginner|Intermediate|Advanced|Expert)$")
    points: int = Field(..., ge=0)
    xp: int = Field(..., ge=0)
    time_limit: int = Field(..., ge=1, le=1440)
    status: str = Field(default="draft", pattern="^(draft|published|archived)$")
    is_published: bool = False
    flag_hash: str
    hints: List[str] = []
    environment_config: dict = {}


class GameChallengeCreate(GameChallengeBase):
    pass


class GameChallengeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = Field(None, pattern="^(Beginner|Intermediate|Advanced|Expert)$")
    points: Optional[int] = Field(None, ge=0)
    xp: Optional[int] = Field(None, ge=0)
    time_limit: Optional[int] = Field(None, ge=1, le=1440)
    status: Optional[str] = Field(None, pattern="^(draft|published|archived)$")
    is_published: Optional[bool] = None
    flag_hash: Optional[str] = None
    hints: Optional[List[str]] = None
    environment_config: Optional[dict] = None


class GameChallengeResponse(GameChallengeBase):
    id: str
    author_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GameChallengeListResponse(BaseModel):
    challenges: List[GameChallengeResponse]
    total: int
    page: int
    page_size: int


class ChallengeAttemptResponse(BaseModel):
    id: str
    challenge_id: str
    user_id: str
    team_id: Optional[str]
    status: str
    score: int
    xp_awarded: int
    started_at: datetime
    completed_at: Optional[datetime]
    execution_metadata: dict

    class Config:
        from_attributes = True


class ChallengeSubmissionCreate(BaseModel):
    flag: str


class ChallengeSubmissionResponse(BaseModel):
    correct: bool
    message: str
    xp_awarded: Optional[int] = None


class TournamentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str
    start_at: datetime
    end_at: datetime
    max_players: int = Field(..., ge=1, le=10000)
    max_teams: int = Field(..., ge=1, le=1000)
    rules: str
    season_id: Optional[str] = None


class TournamentCreate(TournamentBase):
    pass


class TournamentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    max_players: Optional[int] = Field(None, ge=1, le=10000)
    max_teams: Optional[int] = Field(None, ge=1, le=1000)
    rules: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(upcoming|active|completed|cancelled)$")
    season_id: Optional[str] = None


class TournamentResponse(TournamentBase):
    id: str
    status: str
    created_by: Optional[str] = None
    registered_players: int
    registered_teams: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TournamentListResponse(BaseModel):
    tournaments: List[TournamentResponse]
    total: int
    page: int
    page_size: int


class TournamentRegistrationCreate(BaseModel):
    team_id: Optional[str] = None


class TournamentRegistrationResponse(BaseModel):
    id: str
    tournament_id: str
    user_id: str
    team_id: Optional[str]
    registered_at: datetime

    class Config:
        from_attributes = True


class GameTeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    tag: str = Field(..., min_length=2, max_length=10, pattern="^[A-Z0-9]+$")
    description: str = ""
    avatar: Optional[str] = None
    max_members: int = Field(default=5, ge=1, le=20)
    is_private: bool = False


class GameTeamCreate(GameTeamBase):
    pass


class GameTeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    tag: Optional[str] = Field(None, min_length=2, max_length=10, pattern="^[A-Z0-9]+$")
    description: Optional[str] = None
    avatar: Optional[str] = None
    max_members: Optional[int] = Field(None, ge=1, le=20)
    is_private: Optional[bool] = None


class GameTeamResponse(GameTeamBase):
    id: str
    captain_id: str
    member_count: int
    xp: int
    rank: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GameTeamListResponse(BaseModel):
    teams: List[GameTeamResponse]
    total: int
    page: int
    page_size: int


class GameTeamMemberCreate(BaseModel):
    role: str = "member"


class GameTeamMemberResponse(BaseModel):
    id: str
    team_id: str
    user_id: str
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


class ArenaStatsResponse(BaseModel):
    active_challenges: int
    total_players: int
    active_environments: int
    current_season: Optional[dict] = None