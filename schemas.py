from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: str
    username: str
    role: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_approved: bool
    class Config:
        from_attributes = True

class CourseBase(BaseModel):
    name: str
    description: str
    scheduled_at: datetime

class CourseCreate(CourseBase):
    pass

class Course(CourseBase):
    id: int
    users_joined: int
    class Config:
        from_attributes = True

class CourseEnrollment(BaseModel):
    id: int
    user_id: int
    course_id: int
    enrolled_at: datetime
    class Config:
        from_attributes = True

class Feedback(BaseModel):
    id: int
    user_email: str
    message: str
    timestamp: datetime
    response: Optional[str] = None
    responder_email: Optional[str] = None

    class Config:
        from_attributes = True
        
class FeedbackResponse(BaseModel):
    response: str        

