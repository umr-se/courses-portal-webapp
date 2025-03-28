# Courses Portal WebApp (Python) – A Course Management System 

## Overview
Courses Portal WebApp is a FastAPI-based web application designed for role-based course management and user access control. The system includes three roles: **Admin, Coordinator, and User**, each with specific functionalities.

## Features

### 👤 User
- Registers on the platform and awaits Admin approval.
- Once approved, users can log in and enroll in available courses.
- Users can provide feedback, which Admins and Coordinators can respond to.

### 🛠️ Coordinator
- Views approved users.
- Creates and edits courses.
- Monitors enrollments.
- Participates in feedback discussions but **cannot delete courses**.

### 👑 Admin
- Has full control over the system.
- Approves or rejects users.
- Creates, updates, and deletes courses.
- Manages enrollments.
- Handles feedback responses.

## 🔐 Security & Authentication
Implemented **JWT-based Authentication & Authorization** to ensure secure access control.

## 💻 Tech Stack
- **Backend:** FastAPI 
- **Database:** MySQL 
- **Frontend:** Flask, HTML, CSS 

## 💬 Key Feature
A **real-time feedback chat system** enables seamless communication between users, coordinators, and admins.

## Installation

1. **Clone the repository**:
   ```sh
   git clone https://github.com/umr-se/courses-portal-webapp.git
   cd courses-portal-webapp
   ```
2. **Requirements**:   
   ```sh
   pip install venv myenv 
   ```
   ```sh
   pip install -r requirements.txt
   ```   
3. **Steps to Start !!**   
   ```sh
   uvicorn app:app --reload 
   ```
   ```sh
   cd frontend
   flask run
   ```
## Screenshots 

![pic_1](https://github.com/user-attachments/assets/138de0cb-ba08-4bea-9751-94fee3775d7e)
![pic_2](https://github.com/user-attachments/assets/7a24521d-cb08-481a-ab7f-8e022895be70)
![pic_3](https://github.com/user-attachments/assets/f498165d-e669-477f-93f5-b00a4722a6a8)
![pic_5](https://github.com/user-attachments/assets/4a518c36-1eab-45b1-a520-cbb07fe4a915)
![pic_4](https://github.com/user-attachments/assets/49467d61-be65-461b-8911-a38316760654)
