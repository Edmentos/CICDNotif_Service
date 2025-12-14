from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, DateTime
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    welcome_email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DeletedUser(Base):
    __tablename__ = "deleted_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    goodbye_email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

