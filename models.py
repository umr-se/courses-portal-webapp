from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey
from database import Base
from sqlalchemy.orm import relationship

class DBUser(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    username = Column(String(255))
    hashed_password = Column(String(255))
    role = Column(String(50), default="user")
    is_approved = Column(Boolean, default=False)
    # Fix relationship configuration
    enrollments = relationship("DBCourseEnrollment", back_populates="user", cascade="all, delete-orphan")

class DBCourse(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    description = Column(String(1000))
    scheduled_at = Column(DateTime, nullable=False)  # New field
    enrollments = relationship("DBCourseEnrollment", back_populates="course", cascade="all, delete-orphan")

class DBCourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("DBUser", back_populates="enrollments")
    course = relationship("DBCourse", back_populates="enrollments")
    
class DBFeedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), ForeignKey("users.email"))
    message = Column(String(1000))
    timestamp = Column(DateTime)
    response = Column(String(1000))  # New column
    responder_email = Column(String(255))  # New column

# class DBCoordinator(Base):
#     __tablename__ = "coordinators"
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(255))
#     email = Column(String(255))