from pydantic import BaseModel, EmailStr, Field


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

