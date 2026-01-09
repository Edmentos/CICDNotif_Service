from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from datetime import datetime


class Base(DeclarativeBase):
    pass


# Stores all notifications sent to users for audit trail and history
class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)  # welcome or goodbye
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)  # user can mark as read
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)  # true if email sent successfully

