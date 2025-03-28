from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests

app = Flask(__name__, template_folder="templates")

app.secret_key = "jE9rvz9rXw9IlGgZRH43tnEN2QYk8O9G"

FASTAPI_URL = "http://127.0.0.1:8000" 

@app.route("/")
def home():
    return render_template("home.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        user_data = {
            "email": email,
            "username": username,
            "password": password,
            "role": "user"
        }

        response = requests.post(f"{FASTAPI_URL}/users/", data=user_data)

        print("Response Status:", response.status_code)
        print("Response Text:", response.text)  # Debugging

        if response.status_code in [200, 201]:  # Accept both 200 and 201 as success
            return redirect(url_for('home'))
        else:
            return render_template('register.html', error="Registration failed. Try again.")

    return render_template('register.html')



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        response = requests.post(f"{FASTAPI_URL}/token", data={"username": email, "password": password})
        if response.status_code == 200:
            data = response.json()
            session["token"] = data["access_token"]

            headers = {"Authorization": f"Bearer {session['token']}"}
            user_data = requests.get(f"{FASTAPI_URL}/users/me", headers=headers)

            if user_data.status_code == 200:
                user = user_data.json()

                if not user["is_approved"]:
                    return render_template("login.html", error="Your account is pending admin approval.")

                session["role"] = user["role"]
                session["username"] = user["username"]
                session["user_id"] = user["id"]
                session["email"] = user["email"]  # Store email in session

                if session["role"] == "admin":
                    return redirect(url_for("admin_dashboard"))
                elif session["role"] == "coordinator":
                    return redirect(url_for("coordinator_dashboard"))
                else:
                    return redirect(url_for("user_dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if "token" not in session or session["role"] not in ["admin", "coordinator"]:
        return redirect(url_for("login"))
    
    headers = {"Authorization": f"Bearer {session['token']}"}
    
    # User search
    user_search = request.args.get("search", "")
    users_response = requests.get(
        f"{FASTAPI_URL}/users/get",
        headers=headers,
        params={"search": user_search}
    )
    
    # Course search
    course_search = request.args.get("course_search", "")
    courses_response = requests.get(
        f"{FASTAPI_URL}/courses/get",
        headers=headers,
        params={"search": course_search}
    )
    
    return render_template(
        "admin_dashboard.html",
        users=users_response.json() if users_response.status_code == 200 else [],
        courses=courses_response.json() if courses_response.status_code == 200 else [],
        search=user_search,
        course_search=course_search
    )


@app.route("/approve_user/<int:user_id>")
def approve_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    headers = {"Authorization": f"Bearer {session['token']}"}
    
    # Correct the URL to match FastAPI's endpoint
    response = requests.put(
        f"{FASTAPI_URL}/users/{user_id}/approve",
        headers=headers
    )

    if response.status_code == 200:
        return redirect(url_for("admin_dashboard"))
    else:
        return "Error approving user", 400


@app.route("/delete_user/<int:user_id>")
def delete_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.delete(f"{FASTAPI_URL}/users/{user_id}", headers=headers)

    if response.status_code == 200:
        return redirect(url_for("admin_dashboard"))
    else:
        return "Error deleting user", 400


# Add to flask app.py
@app.route("/edit_user/<int:user_id>", methods=["GET"])
def edit_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    headers = {"Authorization": f"Bearer {session['token']}"}
    
    # Get specific user data
    response = requests.get(
        f"{FASTAPI_URL}/users/get?user_id={user_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        return "User not found", 404
        
    user = response.json()[0]
    return render_template("edit_user.html", user=user)

@app.route("/update_user/<int:user_id>", methods=["POST"])
def update_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    headers = {"Authorization": f"Bearer {session['token']}"}
    
    update_data = {
        "email": request.form.get("email"),
        "username": request.form.get("username"),
        "password": request.form.get("password"),
        "role": request.form.get("role"),
        "is_approved": "is_approved" in request.form
    }
    
    # Remove password if empty
    if not update_data["password"]:
        del update_data["password"]
    
    response = requests.put(
        f"{FASTAPI_URL}/users/{user_id}",
        headers=headers,
        data=update_data
    )
    
    if response.status_code == 200:
        return redirect(url_for("admin_dashboard"))
    else:
        return f"Error updating user: {response.text}", 400
        
@app.route("/dashboard/coordinator")
def coordinator_dashboard():
    if session.get("role") != "coordinator":
        return redirect(url_for("login"))

    headers = {"Authorization": f"Bearer {session['token']}"}
    
    # Search parameters
    user_search = request.args.get('search', '')
    course_search = request.args.get('course_search', '')
    
    # Get coordinator's data
    user_response = requests.get(f"{FASTAPI_URL}/users/me", headers=headers)
    if user_response.status_code != 200:
        return redirect(url_for("login"))
    user = user_response.json()
    
    # Get managed users
    users_response = requests.get(
        f"{FASTAPI_URL}/users/get",
        headers=headers,
        params={"search": user_search} if user_search else {}
    )
    managed_users = [u for u in users_response.json() if u['role'] == 'user'] if users_response.status_code == 200 else []
    
    # Get courses with search
    courses_response = requests.get(
        f"{FASTAPI_URL}/courses/get",
        headers=headers,
        params={"search": course_search} if course_search else {}
    )
    courses = courses_response.json() if courses_response.status_code == 200 else []

    return render_template("coordinator_dashboard.html",
                         user=user,
                         users_count=len(managed_users),
                         managed_users=managed_users,
                         courses=courses,
                         search_query=user_search,
                         course_search=course_search)
    
    
@app.route("/dashboard/user")
def user_dashboard():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    headers = {"Authorization": f"Bearer {session['token']}"}
    search_query = request.args.get('search', '')
    
    # Get user data
    user_response = requests.get(f"{FASTAPI_URL}/users/me", headers=headers)
    if user_response.status_code != 200:
        return redirect(url_for("login"))
    user = user_response.json()
    
    # Get courses with search filter
    courses_response = requests.get(
        f"{FASTAPI_URL}/courses/get",
        headers=headers,
        params={"search": search_query} if search_query else {}
    )
    courses = courses_response.json() if courses_response.status_code == 200 else []
    
    # Get enrolled courses
    enrolled_courses = {e["course_id"] for e in user.get("enrollments", [])}
    
    return render_template("user_dashboard.html",
                         user=user,
                         courses=courses,
                         enrolled_courses=enrolled_courses,
                         search_query=search_query)

@app.route("/courses")
def courses():
    if "token" not in session:
        return redirect(url_for("login"))
    
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.get(f"{FASTAPI_URL}/courses/get", headers=headers)
    courses = response.json() if response.status_code == 200 else []
    
    # Get enrollment status for users
    enrolled_courses = set()
    if session["role"] == "user":
        user_response = requests.get(f"{FASTAPI_URL}/users/me", headers=headers)
        if user_response.status_code == 200:
            user = user_response.json()
            enrolled_courses = {e["course_id"] for e in user.get("enrollments", [])}
    
    return render_template("courses.html", 
                         courses=courses,
                         enrolled_courses=enrolled_courses,
                         role=session["role"])

# Create Course Route
@app.route("/courses/create", methods=["GET", "POST"])
def create_course():
    if session["role"] not in ["admin", "coordinator"]:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        headers = {"Authorization": f"Bearer {session['token']}"}
        course_data = {
            "name": request.form.get("name"),
            "description": request.form.get("description"),
            "scheduled_at": request.form.get("scheduled_at")
        }
        
        response = requests.post(
            f"{FASTAPI_URL}/courses/create",
            headers=headers,
            data=course_data
        )
        
        if response.status_code == 200:
            return redirect(url_for("courses"))
        return render_template("create_course.html", error="Failed to create course")
    
    return render_template("create_course.html")

# Edit Course Route
@app.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
def edit_course(course_id):
    if session["role"] not in ["admin", "coordinator"]:
        return redirect(url_for("login"))
    
    headers = {"Authorization": f"Bearer {session['token']}"}
    
    if request.method == "POST":
        course_data = {
            "name": request.form.get("name"),
            "description": request.form.get("description"),
            "scheduled_at": request.form.get("scheduled_at")
        }
        
        response = requests.put(
            f"{FASTAPI_URL}/courses/{course_id}",
            headers=headers,
            data=course_data
        )
        
        if response.status_code == 200:
            return redirect(url_for("course_detail", course_id=course_id))
        return render_template("edit_course.html", error="Failed to update course")
    
    # GET request - load existing data
    response = requests.get(f"{FASTAPI_URL}/courses/get", headers=headers)
    courses = response.json() if response.status_code == 200 else []
    course = next((c for c in courses if c["id"] == course_id), None)
    
    if not course:
        return redirect(url_for("courses"))
    
    return render_template("edit_course.html", course=course)

# Delete Course Route
@app.route("/courses/<int:course_id>/delete")
def delete_course(course_id):
    if session["role"] != "admin":
        return redirect(url_for("login"))
    
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.delete(f"{FASTAPI_URL}/courses/{course_id}", headers=headers)
    
    if response.status_code == 200:
        return redirect(url_for("courses"))
    return "Failed to delete course", 400

# Course Detail Route
@app.route("/courses/<int:course_id>")
def course_detail(course_id):
    error = request.args.get('error')
    headers = {"Authorization": f"Bearer {session['token']}"}
    
    # Get course details
    course_response = requests.get(f"{FASTAPI_URL}/courses/get", headers=headers)
    courses = course_response.json() if course_response.status_code == 200 else []
    course = next((c for c in courses if c["id"] == course_id), None)
    
    if not course:
        return redirect(url_for("courses"))
    
    # Get enrolled users
    users_response = requests.get(
        f"{FASTAPI_URL}/courses/{course_id}/users", 
        headers=headers
    )
    enrolled_users = users_response.json() if users_response.status_code == 200 else []
    
    # Check if current user is enrolled
    is_enrolled = False
    if session["role"] == "user":
        user_id = session["user_id"]
        is_enrolled = any(u["id"] == user_id for u in enrolled_users)
    
    return render_template("course_detail.html",
                         course=course,
                         error=error,
                         enrolled_users=enrolled_users,
                         is_enrolled=is_enrolled)

# Enroll in Course Route
@app.route("/courses/<int:course_id>/enroll")
def enroll_course(course_id):
    if session.get("role") != "user":
        return redirect(url_for("login"))
    
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.post(
        f"{FASTAPI_URL}/courses/{course_id}/enroll",
        headers=headers
    )
    
    if response.status_code == 200:
        return redirect(url_for("course_detail", course_id=course_id))
    elif response.status_code == 400:
        # Redirect with error message
        return redirect(url_for("course_detail", course_id=course_id, error="You are already enrolled in this course"))
    else:
        # Handle other errors if needed
        return "Enrollment failed", 400

# Modify the view_user route to pass course_id
@app.route("/users/<int:user_id>")
def view_user(user_id):
    if session.get("role") not in ["admin", "coordinator"]:
        return redirect(url_for("login"))
    
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.get(f"{FASTAPI_URL}/users/{user_id}", headers=headers)
    
    if response.status_code != 200:
        return "User not found", 404
    
    return render_template(
        "user_detail.html",
        user=response.json(),
        course_id=request.args.get("course_id")
    )


# Add these new routes in Flask app.py
@app.route("/feedback")
def view_feedback():
    if 'role' not in session:
        return redirect(url_for('login'))
    
    headers = {"Authorization": f"Bearer {session['token']}"}
    
    # Get user's feedback
    feedback_response = requests.get(f"{FASTAPI_URL}/feedback/get", headers=headers)
    feedback = feedback_response.json() if feedback_response.status_code == 200 else []
    
    return render_template("view_feedback.html", feedback=feedback)

@app.route("/feedback/manage")
def manage_feedback():
    if session.get("role") not in ['admin', 'coordinator']:
        return redirect(url_for('login'))
    
    headers = {"Authorization": f"Bearer {session['token']}"}
    
    # Get all feedback
    feedback_response = requests.get(f"{FASTAPI_URL}/feedback/get", headers=headers)
    feedback = feedback_response.json() if feedback_response.status_code == 200 else []
    
    return render_template("manage_feedback.html", feedback=feedback)

@app.route("/feedback/submit", methods=['POST'])
def submit_feedback():
    if 'role' not in session:
        return redirect(url_for('login'))
    
    headers = {"Authorization": f"Bearer {session['token']}"}
    message = request.form.get('message')
    
    # Submit feedback
    response = requests.post(
        f"{FASTAPI_URL}/feedback/create",
        headers=headers,
        data={"message": message}
    )
    
    return redirect(url_for('view_feedback'))

@app.route("/feedback/respond/<int:feedback_id>", methods=['POST'])
def respond_to_feedback(feedback_id):
    if session.get("role") not in ['admin', 'coordinator']:
        return redirect(url_for('login'))
    
    headers = {"Authorization": f"Bearer {session['token']}"}
    response_message = request.form.get('response')
    
    # Update feedback with response (you'll need to add this endpoint to FastAPI)
    requests.put(
        f"{FASTAPI_URL}/feedback/{feedback_id}/respond",
        headers=headers,
        json={"response": response_message}
    )
    
    return redirect(url_for('manage_feedback'))

    
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
