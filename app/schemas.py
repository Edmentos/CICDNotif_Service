from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import List


class UserCreate(BaseModel):
	email: EmailStr
	name: str = Field(..., min_length=1)
	age: int = Field(..., ge=0)


class User(BaseModel):
	id: int
	email: EmailStr
	name: str
	age: int
	welcome_email_sent: bool

	class Config:
		orm_mode = True


# Shows all details about a notification
class NotificationResponse(BaseModel):
	id: int
	user_email: EmailStr
	notification_type: str
	subject: str
	message: str
	sent_at: datetime
	is_read: bool
	delivered: bool

	class Config:
		orm_mode = True


# Used when marking a notification as read
class NotificationMarkRead(BaseModel):
	is_read: bool

