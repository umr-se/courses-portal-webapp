from datetime import datetime, timedelta
import tempfile
from typing import List, Optional
from fastapi import FastAPI, Depends, Form, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
import models
import schemas 
import auth
import csv
from io import StringIO
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import joinedload
from database import engine, get_db, SessionLocal
from auth import get_current_user
from auth import get_current_user, get_current_admin_or_coordinator

app = FastAPI(
    title="Courses API",
    description="API for Courses",
    version="3.0"
)

models.Base.metadata.create_all(bind=engine)

# New dependency to check admin or coordinator role
def get_current_admin_or_coordinator(current_user: models.DBUser = Depends(get_current_user)):
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource"
        )
    return current_user

@app.get("/", tags=["home"])
def home():
    return {"message": "Courses API is running!"}

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        admin = db.query(models.DBUser).filter(models.DBUser.email == "admin@example.com").first()
        if not admin:
            hashed_password = auth.pwd_context.hash("pass123")
            admin_user = models.DBUser(
                email="admin@example.com",
                username="admin",
                hashed_password=hashed_password,
                role="admin",
                is_approved=True  # Force approval
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)  # Explicit refresh
        else:
            # Ensure existing admin is approved
            if not admin.is_approved:
                admin.is_approved = True
                db.commit()
                db.refresh(admin)
    finally:
        db.close()

@app.post("/token", tags=["login"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_approved:  # Add approval check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending admin approval"
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.User, tags=["user"])
async def read_users_me(current_user: models.DBUser = Depends(get_current_user)):
    return current_user

# In app.py
@app.get("/users/pending", response_model=List[schemas.User], tags=["admin"])
async def get_pending_users(
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view pending users")
    pending_users = db.query(models.DBUser).filter(models.DBUser.is_approved == False).all()
    return pending_users

@app.put("/users/{user_id}/approve", response_model=schemas.User, tags=["admin"])
async def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can approve users")
    db_user = db.query(models.DBUser).filter(models.DBUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.is_approved = True
    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/users/{user_id}", response_model=dict, tags=["admin"])
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(get_current_user)
):
    """Delete a user (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete users")
    
    db_user = db.query(models.DBUser).filter(models.DBUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}

@app.put("/users/{user_id}", response_model=schemas.User, tags=["admin"])
async def update_user(
    user_id: int,
    email: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    is_approved: Optional[bool] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(get_current_user)
):
    """Update user details (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update users")
    
    db_user = db.query(models.DBUser).filter(models.DBUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update email if provided and not duplicate
    if email is not None and email != db_user.email:
        existing_user = db.query(models.DBUser).filter(models.DBUser.email == email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        db_user.email = email

    # Update other fields if provided
    if username is not None:
        db_user.username = username
    if role is not None:
        db_user.role = role
    if is_approved is not None:
        db_user.is_approved = is_approved
    if password is not None:
        db_user.hashed_password = auth.pwd_context.hash(password)

    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/users/", response_model=schemas.User, tags=["user"])
async def create_user(
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
    db: Session = Depends(get_db),
    #current_user: models.DBUser = Depends(get_current_user)  # Add admin check
):
    #if current_user.role != "admin":
        #raise HTTPException(status_code=403, detail="Only admins can create users")
    
    # Existing validation
    db_user = db.query(models.DBUser).filter(models.DBUser.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.pwd_context.hash(password)
    new_user = models.DBUser(
        email=email,
        username=username,
        hashed_password=hashed_password,
        role=role,
        is_approved=False  # Explicitly set approval status
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/get", response_model=List[schemas.User], tags=["user"])
async def get_users(
    user_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(get_current_user)
):
    query = db.query(models.DBUser)

    if user_id:
        query = query.filter(models.DBUser.id == user_id)
    elif search:
        search_filter = or_(
            models.DBUser.username.ilike(f"%{search}%"),
            models.DBUser.email.ilike(f"%{search}%"),
            models.DBUser.role.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    if current_user.role == "admin":
        users = query.all()
    elif current_user.role == "coordinator":
        # Include both regular users and the coordinator themselves
        users = query.filter(
            or_(
                models.DBUser.role == "user",
                models.DBUser.id == current_user.id
            )
        ).all()
    else:
        if user_id and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own information"
            )
        users = [current_user]

    return users
   

# Create course (Admin/Coordinator only)
@app.post("/courses/create", response_model=schemas.Course, tags=["Courses"])
async def create_course(
    name: str = Form(...),
    description: str = Form(...),
    scheduled_at: datetime = Form(...),  # New parameter
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(auth.get_current_admin_or_coordinator)
):
    db_course = models.DBCourse(
        name=name,
        description=description,
        scheduled_at=scheduled_at  # Include scheduled time
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return {
        "id": db_course.id,
        "name": db_course.name,
        "description": db_course.description,
        "scheduled_at": db_course.scheduled_at,
        "users_joined": 0
    }

# Delete course (Admin only)
@app.delete("/courses/{course_id}", response_model=dict, tags=["Courses"])
async def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(auth.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete courses")
    
    db_course = db.query(models.DBCourse).get(course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    db.delete(db_course)
    db.commit()
    return {"message": "Course deleted successfully"}

# Enroll user in course
@app.post("/courses/{course_id}/enroll", response_model=schemas.CourseEnrollment, tags=["Courses"])
async def enroll_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(auth.get_current_user)
):
    if current_user.role != "user":
        raise HTTPException(status_code=403, detail="Only regular users can enroll in courses")
    
    db_course = db.query(models.DBCourse).get(course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    existing = db.query(models.DBCourseEnrollment).filter_by(
        user_id=current_user.id,
        course_id=course_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled")
    
    enrollment = models.DBCourseEnrollment(
        user_id=current_user.id,
        course_id=course_id,
        enrolled_at=datetime.now()
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment

@app.get("/courses/get", response_model=List[schemas.Course], tags=["Courses"])
async def get_courses(
    search: Optional[str] = Query(None, description="Search by course name, description, or date"),
    db: Session = Depends(get_db)
):
    query = db.query(models.DBCourse)
    
    if search:
        # Search in name, description, or date (cast datetime to string for searching)
        search_filter = or_(
            models.DBCourse.name.ilike(f"%{search}%"),
            models.DBCourse.description.ilike(f"%{search}%"),
            cast(models.DBCourse.scheduled_at, String).ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    courses = query.all()
    result = []
    for course in courses:
        count = db.query(func.count(models.DBCourseEnrollment.id)).filter(
            models.DBCourseEnrollment.course_id == course.id
        ).scalar()
        result.append({
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "scheduled_at": course.scheduled_at,
            "users_joined": count
        })
    return result

# Get users in a specific course
@app.get("/courses/{course_id}/users", response_model=List[schemas.User], tags=["Courses"])
async def get_course_users(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(auth.get_current_admin_or_coordinator)
):
    db_course = db.query(models.DBCourse).get(course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    enrollments = db.query(models.DBCourseEnrollment).filter_by(course_id=course_id).all()
    user_ids = [e.user_id for e in enrollments]
    users = db.query(models.DBUser).filter(models.DBUser.id.in_(user_ids)).all()
    return users

# In FastAPI app.py
@app.get("/users/{user_id}", response_model=schemas.User, tags=["Users"])
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(auth.get_current_admin_or_coordinator)
):
    db_user = db.query(models.DBUser).get(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/courses/export", tags=["Courses"])
async def export_courses_data(
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(get_current_admin_or_coordinator)
):
    # Get all courses with their enrollments and users
    courses = db.query(models.DBCourse).options(
        joinedload(models.DBCourse.enrollments).joinedload(models.DBCourseEnrollment.user)
    ).all()

    # Create in-memory CSV file
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer)
    
    # Write CSV header
    csv_writer.writerow([
        'Course ID', 'Course Name', 'Course Description', 'Scheduled At',
        'User ID', 'User Email', 'Username', 'Enrollment Date'
    ])

    # Write data rows
    for course in courses:
        base_course_info = [
            course.id,
            course.name,
            course.description,
            course.scheduled_at.isoformat()  # Add scheduled time
        ]
        
        if course.enrollments:
            for enrollment in course.enrollments:
                csv_writer.writerow(base_course_info + [
                    enrollment.user.id,
                    enrollment.user.email,
                    enrollment.user.username,
                    enrollment.enrolled_at.isoformat()
                ])
        else:
            # Write course info even with no enrollments
            csv_writer.writerow(base_course_info + ['', '', '', ''])

    # Prepare response
    csv_buffer.seek(0)
    
    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=courses_export.csv",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@app.put("/feedback/{feedback_id}/respond", response_model=schemas.Feedback, tags=["Courses"])
async def respond_to_feedback(
    feedback_id: int,
    response_data: schemas.FeedbackResponse,
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(get_current_user)
):
    # Check user role
    if current_user.role not in ['admin', 'coordinator']:
        raise HTTPException(status_code=403, detail="Unauthorized role")

    # Fetch feedback
    db_feedback = db.query(models.DBFeedback).filter(models.DBFeedback.id == feedback_id).first()
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    # Update response fields
    db_feedback.response = response_data.response
    db_feedback.responder_email = current_user.email

    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@app.get("/feedback/get", response_model=List[schemas.Feedback], tags=["Courses"])
async def get_feedback(
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(get_current_user)  # Changed dependency
):
    """Get all feedback entries (accessible to all authenticated users)"""
    return db.query(models.DBFeedback).all()

@app.post("/feedback/create", response_model=schemas.Feedback, tags=["Courses"])
async def create_feedback(
    message: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(get_current_user)  # Changed dependency
):
    """Create new feedback (accessible to all authenticated users)"""
    db_feedback = models.DBFeedback(
        message=message,
        user_email=current_user.email,
        timestamp=datetime.now()
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@app.get("/coordinators/get", response_model=List[schemas.User], tags=["Coordinators"])
async def get_coordinators(
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(get_current_admin_or_coordinator)
):
    """Get all coordinators (admin/coordinator only)"""
    return db.query(models.DBUser).filter(models.DBUser.role == "coordinator").all()

@app.post("/coordinators/add", response_model=schemas.User, tags=["Coordinators"])
async def add_coordinator(
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(get_current_user)
):
    """Create new coordinator (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create coordinators")
    
    # Check for existing user
    existing_user = db.query(models.DBUser).filter(models.DBUser.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create coordinator user
    hashed_password = auth.pwd_context.hash(password)
    new_coordinator = models.DBUser(
        email=email,
        username=username,
        hashed_password=hashed_password,
        role="coordinator",
        is_approved=False  # Requires admin approval
    )
    
    db.add(new_coordinator)
    db.commit()
    db.refresh(new_coordinator)
    return new_coordinator

@app.get("/dashboard/", tags=["Dashboard"])
async def get_dashboard(
    db: Session = Depends(get_db),
    current_user: models.DBUser = Depends(get_current_user)  # Add authentication
):
    base_data = {
        "activities": db.query(models.DBActivity)
                       .order_by(models.DBActivity.date.desc())
                       .limit(5).all()
    }
    
    if current_user.role == "admin":
        # Add admin-only data
        base_data.update({
            "feedback": db.query(models.DBFeedback)
                         .order_by(models.DBFeedback.timestamp.desc())
                         .limit(3).all(),
            "chat_messages": db.query(models.DBChatMessage)
                             .order_by(models.DBChatMessage.timestamp.desc())
                             .limit(10).all()
        })
    
    return base_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)