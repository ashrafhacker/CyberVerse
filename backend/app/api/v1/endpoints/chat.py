from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.social import ChatMessage, Team, TeamMember
from app.schemas.base import APIResponse, MessageResponse

router = APIRouter()


class SendMessageRequest(BaseModel):
    recipient_id: UUID | None = None
    team_id: UUID | None = None
    content: str = Field(..., min_length=1, max_length=2000)


class CreateTeamRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    privacy: str = Field("private", pattern="^(public|private|closed)$")
    tagline: str | None = Field(None, max_length=200)


@router.get("/conversations", response_model=APIResponse[list], summary="List direct message conversations")
async def list_conversations(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    sent = select(ChatMessage.recipient_id).where(
        ChatMessage.sender_id == user.id,
        ChatMessage.recipient_id.is_not(None),
    )
    received = select(ChatMessage.sender_id).where(
        ChatMessage.recipient_id == user.id,
        ChatMessage.sender_id.is_not(None),
    )
    peer_ids = (
        select(func.distinct(sent.c.recipient_id)).union(
            select(func.distinct(received.c.sender_id))
        )
    ).subquery()

    from app.models.user import User

    peer_ids_sub = (
        select(func.distinct(peer_ids.c.recipient_id)).union(
            select(func.distinct(received.c.sender_id))
        )
    )
    rows = await db.execute(
        select(User).where(User.id.in_(select(peer_ids_sub.c.recipient_id)))
    )
    users = rows.scalars().all()

    last_messages = {}
    if users:
        peer_ids_list = [u.id for u in users]
        last_result = await db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.sender_id.in_([user.id] + peer_ids_list),
                ChatMessage.recipient_id.in_([user.id] + peer_ids_list),
                ChatMessage.is_deleted.is_(False),
            )
            .order_by(ChatMessage.created_at.desc())
        )
        for m in last_result.scalars().all():
            peer = m.sender_id if m.sender_id != user.id else m.recipient_id
            if peer and peer not in last_messages:
                last_messages[peer] = m.content

    return APIResponse[list](
        data=[
            {
                "user_id": str(u.id),
                "full_name": u.full_name,
                "avatar_url": u.avatar_url,
                "last_message": last_messages.get(u.id),
            }
            for u in users
        ]
    )


@router.get("/messages/{peer_id}", response_model=APIResponse[list], summary="Get DM history with a peer")
async def get_messages(
    peer_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    before: str = Query(None),
):
    stmt = select(ChatMessage).where(
        (
            (ChatMessage.sender_id == user.id) & (ChatMessage.recipient_id == peer_id)
        )
        | (
            (ChatMessage.sender_id == peer_id) & (ChatMessage.recipient_id == user.id)
        ),
        ChatMessage.is_deleted.is_(False),
    )

    if before:
        stmt = stmt.where(ChatMessage.created_at < before)

    stmt = stmt.order_by(ChatMessage.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    messages = result.scalars().all()
    messages.reverse()

    return APIResponse[list](
        data=[
            {
                "id": str(m.id),
                "sender_id": str(m.sender_id) if m.sender_id else None,
                "content": m.content,
                "message_type": m.message_type,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "is_read": m.is_read,
            }
            for m in messages
        ]
    )


@router.post("/messages", response_model=APIResponse[dict], summary="Send a message")
async def send_message(
    request: SendMessageRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    if not request.recipient_id and not request.team_id:
        raise HTTPException(status_code=400, detail="recipient_id or team_id required")

    if request.team_id:
        membership = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == request.team_id,
                TeamMember.user_id == user.id,
            )
        )
        if not membership.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not a member of this team")

    message = ChatMessage(
        sender_id=user.id,
        recipient_id=request.recipient_id,
        team_id=request.team_id,
        content=request.content,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return APIResponse[dict](
        data={
            "id": str(message.id),
            "sender_id": str(message.sender_id),
            "content": message.content,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }
    )


@router.post("/teams", response_model=APIResponse[dict], summary="Create a team")
async def create_team(
    request: CreateTeamRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    import secrets

    team = Team(
        owner_id=user.id,
        slug=secrets.token_hex(4),
        name=request.name,
        description=request.description,
        tagline=request.tagline,
        privacy=request.privacy,
    )
    db.add(team)
    await db.flush()

    member = TeamMember(team_id=team.id, user_id=user.id, role="owner")
    db.add(member)
    await db.commit()
    await db.refresh(team)

    return APIResponse[dict](data={"id": str(team.id), "slug": team.slug, "name": team.name})


@router.get("/teams", response_model=APIResponse[list], summary="List my teams")
async def list_my_teams(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Team)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == user.id)
    )
    teams = result.scalars().all()
    return APIResponse[list](
        data=[
            {"id": str(t.id), "slug": t.slug, "name": t.name, "privacy": t.privacy}
            for t in teams
        ]
    )


@router.post("/teams/{team_id}/join", response_model=MessageResponse, summary="Join a team")
async def join_team(
    team_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if team.privacy == "closed":
        raise HTTPException(status_code=403, detail="This team requires an invitation")

    existing = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        return MessageResponse(message="Already a member")

    db.add(TeamMember(team_id=team_id, user_id=user.id, role="member"))
    await db.commit()
    return MessageResponse(message="Joined team")
