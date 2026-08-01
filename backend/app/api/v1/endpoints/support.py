from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.support import FAQItem, SupportTicket, TicketMessage
from app.schemas.base import APIResponse, MessageResponse, PaginatedResponse

router = APIRouter()


class CreateTicketRequest(BaseModel):
    subject: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    category: str = Field("other", pattern="^(account|billing|technical|content|gameplay|premium|other)$")
    priority: str = Field("medium", pattern="^(low|medium|high|urgent)$")


class ReplyTicketRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


@router.post("/tickets", response_model=APIResponse[dict], summary="Create a support ticket")
async def create_ticket(
    request: CreateTicketRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    import secrets

    ticket = SupportTicket(
        ticket_number=f"CV-{secrets.token_hex(4).upper()}",
        user_id=user.id,
        subject=request.subject,
        description=request.description,
        category=request.category,
        priority=request.priority,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    return APIResponse[dict](
        data={
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "status": ticket.status.value if hasattr(ticket.status, "value") else ticket.status,
        }
    )


@router.get("/tickets", response_model=APIResponse[PaginatedResponse], summary="List my tickets")
async def list_tickets(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(SupportTicket).where(SupportTicket.user_id == user.id)
    total = (await db.execute(select(func.count(SupportTicket.id)).where(SupportTicket.user_id == user.id))).scalar_one()

    result = await db.execute(
        stmt.order_by(SupportTicket.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    tickets = result.scalars().all()

    items = [
        {
            "id": str(t.id),
            "ticket_number": t.ticket_number,
            "subject": t.subject,
            "status": t.status.value if hasattr(t.status, "value") else t.status,
            "priority": t.priority.value if hasattr(t.priority, "value") else t.priority,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tickets
    ]

    data = PaginatedResponse.create(items, total, page, page_size)
    return APIResponse[PaginatedResponse](data=data)


@router.get("/tickets/{ticket_id}", response_model=APIResponse[dict], summary="Get ticket details")
async def get_ticket(
    ticket_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SupportTicket).where(
            SupportTicket.id == ticket_id,
            SupportTicket.user_id == user.id,
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    messages_result = await db.execute(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at.asc())
    )
    messages = messages_result.scalars().all()

    return APIResponse[dict](
        data={
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "description": ticket.description,
            "status": ticket.status.value if hasattr(ticket.status, "value") else ticket.status,
            "priority": ticket.priority.value if hasattr(ticket.priority, "value") else ticket.priority,
            "category": ticket.category.value if hasattr(ticket.category, "value") else ticket.category,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            "messages": [
                {
                    "id": str(m.id),
                    "content": m.content,
                    "is_staff_reply": m.is_staff_reply,
                    "author_id": str(m.author_id),
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        }
    )


@router.post("/tickets/{ticket_id}/reply", response_model=APIResponse[dict], summary="Reply to a ticket")
async def reply_ticket(
    ticket_id: UUID,
    request: ReplyTicketRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SupportTicket).where(
            SupportTicket.id == ticket_id,
            SupportTicket.user_id == user.id,
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status.value in ("resolved", "closed"):
        ticket.status = "reopened"

    message = TicketMessage(
        ticket_id=ticket.id,
        author_id=user.id,
        content=request.content,
        is_staff_reply=False,
    )
    db.add(message)
    await db.commit()

    return APIResponse[dict](
        data={
            "id": str(message.id),
            "content": message.content,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }
    )


@router.get("/faq", response_model=APIResponse[list], summary="List FAQ items")
async def list_faq(
    db: AsyncSession = Depends(get_db),
    category: str = Query(None),
):
    stmt = select(FAQItem).where(FAQItem.is_published.is_(True))
    if category:
        stmt = stmt.where(FAQItem.category == category)
    result = await db.execute(stmt.order_by(FAQItem.order))
    items = result.scalars().all()

    return APIResponse[list](
        data=[
            {
                "id": str(f.id),
                "category": f.category,
                "question": f.question,
                "answer": f.answer,
                "tags": f.tags,
            }
            for f in items
        ]
    )