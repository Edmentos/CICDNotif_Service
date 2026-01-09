from pydantic import BaseModel, EmailStr
from datetime import datetime


# Shows all details about a notification sent by the service
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

