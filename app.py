
import random
from flask import Flask, request, render_template, redirect, jsonify, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import bcrypt
import jwt
import datetime
from functools import wraps
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///02.db'
app.secret_key = 'secret_key'

# Initialize the SQLAlchemy object with the app
db = SQLAlchemy(app)

# Email configurations
app.config['MAIL_SERVER'] = "smtp.googlemail.com"
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "U.nilayam@gmail.com"
app.config['MAIL_PASSWORD'] = "yqup vqbc fbzb wruj"

mail = Mail(app)

# JWT Secret Key
JWT_SECRET_KEY = 'your_jwt_secret_key'

from datetime import datetime

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    birthday = db.Column(db.Date, nullable=False)  # New column for birthday
    role = db.Column(db.Integer, default=0)
    def __init__(self, name, email, password, birthday, role=0):
        self.name = name
        self.email = email
        self.password = password
        self.birthday = birthday
        self.role = role
    def check_password(self, password):
        # Compare plain text password (no hashing)
        return self.password == password
  
with app.app_context():
    db.create_all()
def check_password(self, password):
        # Compare plain text password (no hashing)
        return self.password == password


def create_jwt(user_id, role):
    # Encode a new JWT token with the user ID, role, and expiration time
    return jwt.encode({
        'user_id': user_id,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=1)  # Token expiration time (1 hour)
    }, JWT_SECRET_KEY, algorithm='HS256')
    
def decode_jwt(token):
    try:
        # Decode the token using the secret key and HS256 algorithm
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

def check_jwt_role(required_role=0):
    token = session.get('token')
    if not token:
        return None, "You need to log in first."

    try:
        decoded_token = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        user_role = decoded_token.get('role')

        if user_role != required_role:
            return None, "You do not have the required permissions."

        return decoded_token['user_id'], None

    except jwt.ExpiredSignatureError:
        return None, "Session expired, please log in again."

    except jwt.InvalidTokenError:
        return None, "Invalid session, please log in again."


# Admin Route Protection Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id, error = check_jwt_role(required_role=1)
        if error:
            flash(error, "danger")
            return redirect('/admin-login')
        return f(*args, **kwargs)
    return decorated_function


# Routes

@app.route('/')
def index():
    return render_template('index.html')

from flask import render_template, request, redirect, flash
from datetime import datetime

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        birthday_str = request.form.get('birthday')  # Corrected 'Birthday' to 'birthday'

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already exists", 'error')
            return redirect('/register')

        # Ensure the birthday field is provided
        if not birthday_str:
            flash("Birthday is required", 'error')
            return redirect('/register')

        # Convert birthday string to date object
        try:
            birthday = datetime.strptime(birthday_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", 'error')
            return redirect('/register')

        # Create new user (password is stored in plain text)
        new_user = User(name=name, email=email, password=password, birthday=birthday)

        # Add user to the session and commit to the database
        db.session.add(new_user)
        db.session.commit()

        # Flash success message
        flash("Registration successful! Please log in.", 'success')

        # Redirect to login page after successful registration
        return redirect('/login')

    return render_template('register.html')

from flask import Flask, render_template, request, redirect, session

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            # Create JWT token
            token = create_jwt(user.id, user.role)
            session['user_token'] = token  # Store token in session

            # Redirect based on role
            if user.role == 1:
                return redirect('/admin-dashboard')  # Admin redirect
            else:
                return render_template('dashboard.html',user=user)  # User redirect

        else:
            return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')

@app.route('/submit_issue', methods=['GET', 'POST'])
def submit_issue():
    token = session.get('user_token')
    if not token:
        print("token not found")
        flash("Please log in to submit an issue.", "warning")
        return redirect(url_for('login'))

    decoded_token = decode_jwt(token)
    if not decoded_token:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for('login'))

    # Get user ID and email from token
    user_id = decoded_token.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user:
        flash("User not found. Please log in again.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        problem = request.form.get('problem')
        category = request.form.get('category')

        # Validate input fields
        if not problem or not category:
            flash("Please provide all required fields.", "warning")
            return render_template("ticket_raise.html")

        try:
            # Create and save the issue
            new_issue = Issuues(
                email=user.email,  # Fetch email from the logged-in user
                problem=problem,
                category=category,
                status="Submitted"
            )
            db.session.add(new_issue)
            db.session.commit()
            
           

            flash("Issue submitted successfully.", "success")
        except Exception as e:
            db.session.rollback()
            print("Database Error:", str(e))  # Debugging
            flash("An error occurred while saving your issue. Please try again.", "danger")
            return render_template("ticket_raise.html")

        return render_template('dashboard.html', user=user)  

    return render_template("ticket_raise.html")



# Admin Login
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Query the database for a user with the given email
        user = User.query.filter_by(email=email, role=1).first()  # it's admin (role=1)

        if user and user.check_password(password):
            # Create JWT token for the admin
            token = create_jwt(user.id, user.role)
            session['token'] = token
            return render_template('admindashboard.html', user=user)
        else:
            return render_template('admin.html', error="Invalid admin credentials")

    return render_template('admin.html')


# Admin Dashboard
@app.route('/admin-dashboard')
@admin_required
def admin_dashboard():
    user_id, _ = check_jwt_role(required_role=1)
    user = User.query.get(user_id)
    return render_template('admindashboard.html', user=user)



# Route for Admin Registration
@app.route('/aregister', methods=['GET', 'POST'])
@admin_required  # Ensure only admins can access this route
def admin_register():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        dob = request.form['dob']  # New field for date of birth
        
        # Convert string date to date object
        birthday = datetime.strptime(dob, '%Y-%m-%d').date()

        # Check if email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            return render_template('admin_register.html', error="Email already exists")

        # Create new admin
        new_admin = User(name=name, email=email, password=password, birthday=birthday, role=1)
        db.session.add(new_admin)
        db.session.commit()

        # Redirect to admin dashboard or other page
        return render_template('/admindashboard.html',user=user)

    return render_template('admin_register.html')



from flask import Flask, render_template, request, redirect, url_for, session, flash
import jwt
from datetime import datetime, timedelta
  # Import the db from your application

JWT_SECRET_KEY = "your_jwt_secret_key"  # Secret key used to encode and decode JWT

# Create JWT token
def create_jwt(user_id, role):
    return jwt.encode({
        'user_id': user_id,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=1)  # Token expiration time (1 hour)
    }, JWT_SECRET_KEY, algorithm='HS256')


# class OTPS(db.Model):
#     __tablename__ = 'OTPS'
#     id = db.Column(db.Integer, primary_key=True)
#     email = db.Column(db.String(120), nullable=False, unique=True)
#     otp_code_hash = db.Column(db.String(255), nullable=False)  # Store hashed OTP
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     def __repr__(self):
#         return f'<OTP {self.email}>'

class OTPS(db.Model):
    __tablename__ = 'OTPS'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    otp_code = db.Column(db.String(255), nullable=False)  # Correct column name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<OTP {self.email}>'

# Create tables
with app.app_context():
    db.create_all()

# Route to request email and generate OTP
@app.route("/get_email", methods=["GET", "POST"])
def get_email():
    if request.method == "POST":
        user_email = request.form["email"]
        otp = str(random.randint(100000, 999999))  # Generate a random OTP

        # Check if a user already exists with the given email
        existing_user = OTPS.query.filter_by(email=user_email).first()

        if existing_user:
            existing_user.otp_code = otp  # Store the OTP directly as a string
            existing_user.created_at = datetime.utcnow()  # Update the creation timestamp
        else:
            # Create a new OTP entry
            new_otp = OTPS(email=user_email, otp_code=otp)
            db.session.add(new_otp)

        db.session.commit()

        # Save the user_email in session
        session['user_email'] = user_email

        # Send the email
        msg = Message(
            subject="Your OTP Code",
            sender=app.config['MAIL_USERNAME'],
            recipients=[user_email],
        )
        msg.body = f"Your OTP is: {otp}"  # Send the plain OTP for validation

        try:
            mail.send(msg)
            flash("OTP sent to your email.", "success")
            return redirect(url_for('validate_otp', user_email=user_email))
        except Exception as e:
            flash("Error sending OTP. Please try again.", "error")
            return render_template("submit_email.html")

    return render_template("submit_email.html")

from werkzeug.security import generate_password_hash, check_password_hash
# Route to validate OTP
@app.route('/validate_otp', methods=['GET', 'POST'])
def validate_otp():
    user_email = request.args.get('user_email') or request.form.get('email')

    if request.method == 'POST':
        entered_otp = request.form.get('otp').strip()

        if not entered_otp:
            return render_template("email_otp.html", user_email=user_email, error="Please enter the OTP.")

        otp_record = OTPS.query.filter_by(email=user_email).first()

        if otp_record is None:
            return render_template("email_otp.html", user_email=user_email, error="No OTP found for this email.")

        if check_password_hash(otp_record.otp_code_hash, entered_otp):
            flash("OTP verified successfully.", "success")
            return redirect(url_for('admin_chng_pswd', user_email=user_email))
        else:
            return render_template("email_otp.html", user_email=user_email, error="Invalid OTP. Please try again.")

    return render_template("email_otp.html", user_email=user_email)

@app.route('/admin_change_password', methods=['GET', 'POST'])
def admin_chng_pswd():
    user_email = session.get('user_email')
    if not user_email:
        print("No email found in session.")
        return "Error: No email provided. Please start the process again.", 400

    print(f"Admin Change Password for user_email: {user_email}")

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        user = User.query.filter_by(email=user_email).first()
        if not user:
            return "Error: User not found.", 404

        if new_password != confirm_password:
            flash("Passwords do not match. Please try again.", "danger")
            return redirect(url_for('admin_chng_pswd'))

        user.password = confirm_password  # Use hashing in production
        db.session.commit()

        flash("Password updated successfully!", "success")
        return render_template('change_password.html', user_email=user_email)
    return render_template('change_password.html', user_email=user_email)



@app.route('/user_dashboard')
def user_dashboard():
    user_id, error = check_jwt_role(required_role=0)
    if error:
        flash(error, "danger")
        return redirect('/login')

    user = User.query.get(user_id)
    return render_template('dashboard.html', user=user)


# Ticket Submission (for users)
from flask import request, render_template

@app.route('/ticket_raise', methods=['GET','POST'])
def ticket_raise():
    try:
        email = request.form['email']  # Ensure the form contains 'email'
        category = request.form['category']
        problem = request.form['problem']
        
        # Your logic for processing the issue
        # Save the issue to the database or send it for further processing

        # Flash message for success or return the appropriate response
        flash('Issue submitted successfully!', 'success')
        return redirect(url_for('user_dashboard'))  # Redirect to the dashboard or wherever you want
        
    except KeyError as e:
        flash(f'Missing form field: {str(e)}', 'danger')
        return redirect(url_for('ticket_raise'))

from datetime import datetime, timedelta

from datetime import datetime, timedelta

from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

import io

class Issuues(db.Model):
    __tablename__ = 'issuues'  # Updated the table name
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=False)
    problem = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date_raised = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    remarks = db.Column(db.String(500), nullable=True)  
    assigned_to = db.Column(db.String(200), nullable=True)
      

    def __init__(self, email, problem, category, status="New"):
        self.email = email
        self.problem = problem
        self.category = category
        self.status = status
        self.date_raised = datetime.utcnow()  # Set the current date and time as the date raised
        self.due_date = self.date_raised + timedelta(days=2)  # Add 2 days to the raised date

class IssueHistory(db.Model):
    __tablename__ = 'issue_history'
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issuues.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    remarks = db.Column(db.String(500), nullable=True)

    issue = db.relationship('Issuues', backref=db.backref('history', lazy=True))

    def __init__(self, issue_id, status, remarks=None):
        self.issue_id = issue_id
        self.status = status
        self.remarks = remarks
        self.timestamp = datetime.utcnow()


@app.route('/get_issue', methods=['GET', 'POST'])
@admin_required
def get_issue():
    # Retrieve filter values from query parameters
    status_filter = request.args.get('status', 'All')
    start_date = request.args.get('start_date', None)
    end_date = request.args.get('end_date', None)
    issue_id = request.args.get('issue_id', None)  # Retrieve the issue_id if available

    # Retrieve all issues
    all_issues = Issuues.query.all()

    # Calculate stats
    total_tickets = len(all_issues)
    in_progress_count = sum(1 for issue in all_issues if issue.status == "In Progress")
    in_queued_count = sum(1 for issue in all_issues if issue.status == "In Queued")
    rejected_count = sum(1 for issue in all_issues if issue.status == "Rejected")
    on_hold_count = sum(1 for issue in all_issues if issue.status == "On Hold")
    completed_count = sum(1 for issue in all_issues if issue.status == "Completed")

    # Filter issues based on status
    if status_filter == 'All':
        issues = all_issues
    else:
        issues = [issue for issue in all_issues if issue.status == status_filter]

    # Filter by date range
    if start_date or end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_date = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None

        issues = [
            issue for issue in issues
            if (not start_date or issue.date_raised.date() >= start_date.date()) and
               (not end_date or issue.date_raised.date() <= end_date.date())
        ]
        

    # Sort issues by date raised in descending order
    issues.sort(key=lambda x: x.date_raised, reverse=True)

    # If an issue_id is provided, fetch the specific issue
    issue_details = None
    # if issue_id:
    #     issue_details = Issuues.query.get(issue_id)
        


    # Prepare the initial remarks and status for the selected issue
    current_remarks = issue_details.remarks if issue_details else ""
    current_status = issue_details.status if issue_details else "In Progress"
    due_date = issue_details.due_date if issue_details else None
    date_raised = issue_details.date_raised if issue_details else None
    print(f"fnvj:{current_remarks}")
    print(f"Issue Details: {issue_details}")
    print(f"Due Date: {due_date}")
    print(f"Date Raised: {date_raised}")
    Issue_History = IssueHistory.query.all()
    
    

    
    # Render the template with issues and stats
    return render_template(
        'get_issue.html',
        issues=issues,
        Issue_History = Issue_History,
        issue_details=issue_details,
        datetime=datetime,
        status_filter=status_filter,
        start_date=start_date.strftime('%Y-%m-%d') if start_date else '',
        end_date=end_date.strftime('%Y-%m-%d') if end_date else '',
        total_tickets=total_tickets,
        in_progress_count=in_progress_count,
        in_queued_count=in_queued_count,
        rejected_count=rejected_count,
        on_hold_count=on_hold_count,
        completed_count=completed_count,
        current_remarks=current_remarks,
        current_status=current_status,
        due_date=due_date.strftime('%Y-%m-%d') if due_date else '',
        date_raised=date_raised.strftime('%Y-%m-%d') if date_raised else '' 
    )
    
@app.route('/get_issue_details/<int:issue_id>', methods=['GET'])
def get_issue_details(issue_id):
    issue = Issuues.query.get(issue_id)  # Assuming SQLAlchemy ORM is used
    if issue:
        return jsonify({
            "success": True,
            "date_raised": issue.date_raised.strftime('%Y-%m-%d') if issue.date_raised else "N/A",
            "due_date": issue.due_date.strftime('%Y-%m-%d') if issue.due_date else "N/A"
        })
    else:
        return jsonify({"success": False, "message": "Issue not found"})
    
    
    
@app.route('/get_tickets_by_status')
def get_tickets_by_status():
    status = request.args.get('status')  # Get the status from the URL parameter
    token = session.get('user_token')
    
    # Ensure the user is logged in
    if not token:
        return jsonify({'error': 'User not logged in'}), 401
    
    decoded_token = decode_jwt(token)
    if not decoded_token:
        return jsonify({'error': 'Invalid session'}), 401

    user_id = decoded_token.get('user_id')
    if not user_id:
        return jsonify({'error': 'Invalid session data'}), 401

    # Retrieve the user and issues
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    all_user_issues = Issuues.query.filter_by(email=user.email).order_by(Issuues.date_raised.desc()).all()

    # Filter issues based on the status
    if status != 'All':
        issues = [issue for issue in all_user_issues if issue.status == status]
    else:
        issues = all_user_issues

    # Prepare the response data
    response_data = []
    for issue in issues:
        response_data.append({
            'id': issue.id,
            'email': issue.email,
            'problem': issue.problem,
            'status': issue.status,
            'remarks': issue.remarks or 'No remarks',  # Fix the 'remarks' field
            'date_raised': issue.date_raised,  # Include the 'date_raised' field
            'due_date': issue.due_date         # Include the 'due_date' field
        })
         
        
    return jsonify({'issues': response_data})



from sqlalchemy.exc import IntegrityError
from flask_migrate import Migrate
migrate = Migrate(app, db)



def decode_jwt(token):
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

from flask import Flask, render_template, session, redirect, url_for
  # Assuming the Issues model is in 'models.py'
from flask import Flask, render_template, session, redirect, url_for

@app.route('/fetch_issue_history/<int:issue_id>')
def fetch_issue_history(issue_id):
    history = IssueHistory.query.filter_by(issue_id=issue_id).all()
    history_data = []
    
    for entry in history:
        history_data.append({
            'status': entry.status,
            'remarks': entry.remarks,
            'timestamp': entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({'success': True, 'history': history_data})


# @app.route('/history')
# def history():
#     token = session.get('user_token')
#     if not token:
#         flash("Please log in to view your history.", "warning")
#         return redirect(url_for('login'))

#     print("Session token:", token)

#     decoded_token = decode_jwt(token)
#     if not decoded_token:
#         flash("Session expired. Please log in again.", "warning")
#         return redirect(url_for('login'))

#     print("Decoded token:", decoded_token)

#     user_id = decoded_token.get('user_id')
#     if not user_id:
#         flash("Invalid session data. Please log in again.", "warning")
#         return redirect(url_for('login'))

#     print("User ID from token:", user_id)

#     user = User.query.filter_by(id=user_id).first()
#     if not user:
#         flash("User not found. Please log in again.", "warning")
#         return redirect(url_for('login'))

#     print("User from database:", user)

#     user_issues = Issuues.query.filter_by(email=user.email).order_by(Issuues.date_raised.desc()).all()
#     return render_template('history.html', issues=user_issues)
@app.route('/history')
def history():
    token = session.get('user_token')
    if not token:
        flash("Please log in to view your history.", "warning")
        return redirect(url_for('login'))

    decoded_token = decode_jwt(token)
    if not decoded_token:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for('login'))

    user_id = decoded_token.get('user_id')
    if not user_id:
        flash("Invalid session data. Please log in again.", "warning")
        return redirect(url_for('login'))

    # Retrieve the user
    user = User.query.filter_by(id=user_id).first()
    if not user:
        flash("User not found. Please log in again.", "warning")
        return redirect(url_for('login'))

    # Fetch all issues raised by the user
    all_user_issues = Issuues.query.filter_by(email=user.email).order_by(Issuues.date_raised.desc()).all()

    # Retrieve filter parameters
    status_filter = request.args.get('status', 'All')
    start_date = request.args.get('start_date', None)
    end_date = request.args.get('end_date', None)

    # Filter issues based on the filters
    user_issues = all_user_issues
    if status_filter != 'All':
        user_issues = [issue for issue in user_issues if issue.status == status_filter]
    if start_date:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        user_issues = [issue for issue in user_issues if issue.date_raised >= start_date_obj]
    if end_date:
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        user_issues = [issue for issue in user_issues if issue.date_raised <= end_date_obj]

    # Fetch all issue histories related to these issues
    issue_ids = [issue.id for issue in user_issues]
    issue_history = IssueHistory.query.filter(IssueHistory.issue_id.in_(issue_ids)).order_by(IssueHistory.timestamp.desc()).all()
    print("issuehistory",issue_history)

    # Organize issue history by issue_id for easy access
    issue_history_dict = {}
    for history in issue_history:
        if history.issue_id not in issue_history_dict:
            issue_history_dict[history.issue_id] = []
        issue_history_dict[history.issue_id].append(history)

    # Calculate stats
    total_tickets = len(all_user_issues)
    in_progress_count = sum(1 for issue in all_user_issues if issue.status == "In Progress")
    in_queued_count = sum(1 for issue in all_user_issues if issue.status == "In Queued")
    rejected_count = sum(1 for issue in all_user_issues if issue.status == "Rejected")
    on_hold_count = sum(1 for issue in all_user_issues if issue.status == "On Hold")
    completed_count = sum(1 for issue in all_user_issues if issue.status == "Completed")
    submitted_count = sum(1 for issue in all_user_issues if issue.status == "Submitted")

    return render_template(
        'history.html',
        issues=user_issues,
        issue_history=issue_history_dict,
        total_tickets=total_tickets,
        in_progress_count=in_progress_count,
        in_queued_count=in_queued_count,
        rejected_count=rejected_count,
        on_hold_count=on_hold_count,
        completed_count=completed_count,
        submitted_count=submitted_count,
        current_filter=status_filter,
        start_date=start_date,
        end_date=end_date
    )





@app.route('/logout', methods=['POST'])
def logout():
    # Clear the session or any authentication tokens
    session.pop('token', None)  # You can add more session variables as needed

    # Flash a message if needed
    flash('You have been logged out successfully.', 'success')
    
    
    
#################################


        

@app.route('/view_history/<int:issue_id>', methods=['GET'])
def view_history(issue_id):
    # Fetch issue history data from the database
    # You will replace the sample data with real database queries
    issue = Issuues.query.get(issue_id)

    history_data = [
        {'timestamp': '2024-12-01', 'action': 'Created', 'status': 'In Progress'},
        {'timestamp': '2024-12-02', 'action': 'Status Updated', 'status': 'Completed'}
    ]
    return render_template('issue_history.html', history=history_data,issue=issue)

# @app.route('/get_issue_history/<int:issue_id>', methods=['GET'])
# @admin_required
# def get_issue_history(issue_id):
#     issue = Issuues.query.get(issue_id)
#     if issue:grt
#         history = IssueHistory.query.filter_by(issue_id=issue_id).order_by(IssueHistory.timestamp.asc()).all()
#         # Convert the history into a list of dictionaries to return as JSON
#         history_data = [{'timestamp': h.timestamp, 'action': h.action, 'status': h.status} for h in history]
#         return jsonify({'history': history_data})
#     else:
#         return jsonify({'history': []})


@app.route('/get_issue_history', methods=['GET'])
def get_issue_history():
    issue_id = request.args.get('issue_id')
    if not issue_id:
        return jsonify({"error": "Issue ID not provided"}), 400

    # Query the IssueHistory table for the provided issue_id
    histories = IssueHistory.query.filter_by(issue_id=issue_id).order_by(IssueHistory.timestamp.desc()).all()

    # Format the history data
    history_list = [{
        "timestamp": history.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "status": history.status,
        "remarks": history.remarks
    } for history in histories]

    return jsonify({"histories": history_list})




######
import os

app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    

# Create database tables
with app.app_context():
   
    db.create_all()
    


# Route for uploading images (GET and POST)
@app.route('/admin_upload_land', methods=['GET', 'POST'])
def uploads():
    return render_template('upload.html')

# Handle file upload
@app.route('/admin_upload', methods=['POST'])
def admin_upload():
    title = request.form['title']
    date = request.form['date']  # Get the date from the form
    upload_date = datetime.strptime(date, '%Y-%m-%d').date()

    files = request.files.getlist('images')  # Handle multiple files

    if files:
        uploaded_files = []
        for file in files:
            if file:
                filename = file.filename
                
                # Read file data
                file_data = file.read()
                
                # Save details to the database
                new_file = File(filename=filename, title=title, date=upload_date, image_data=file_data)
                db.session.add(new_file)
                uploaded_files.append(new_file)
                
                # Save the file to the uploads directory
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.seek(0)  # Reset file pointer
                file.save(filepath)

        # Commit changes to the database
        db.session.commit()

        return render_template("admindashboard.html",user=User)
    else:
        return "No files selected", 400

# Serve an image by ID
@app.route('/image/<int:file_id>')
def serve_image(file_id):
    file = File.query.get_or_404(file_id)
    return send_file(
        io.BytesIO(file.image_data),
        mimetype='image/jpeg',  # Adjust if using other formats
        as_attachment=False,
        download_name=file.filename
    )

@app.route('/remove_image/<int:file_id>', methods=['POST'])
def remove_image(file_id):
    token = session.get('token')

    if not token:
        return jsonify({'message': 'Unauthorized access. Please login again.'}), 401

    decoded_token = decode_jwt(token)
    print(decoded_token)
    if not decoded_token:  # If the token is invalid or expired
        return jsonify({'message': 'Invalid token. Please login again.'}), 401

    if decoded_token.get('role') != 1:  # Check if user is not an admin
        return jsonify({'message': 'Permission denied. Admins only.'}), 403

    # (Existing logic to remove the file)
    file = File.query.get_or_404(file_id)
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        db.session.delete(file)
        db.session.commit()
        return redirect(f'/filter_image?year={file.date.year}&month={file.date.month}')
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to remove image: {str(e)}'}), 400


# Filter images by year and month
from collections import defaultdict


from flask import jsonify, session
import jwt



from flask import session, jsonify
import jwt

@app.route('/filter_image', methods=['GET', 'POST'])
def filter_image():
    token = session.get('token')

    if token:
        # Decode the token to get the user id
        decoded_token = decode_jwt(token)
    try:
        is_admin = decoded_token.get('role') == 1  # Assuming role=1 indicates admin
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token expired. Please login again.'}), 401
    except jwt.InvalidTokenError as e:
        return jsonify({'message': f'Invalid token: {str(e)}. Please login again.'}), 401

    # Get the distinct years and months from the database
    distinct_years = db.session.query(db.extract('year', File.date)).distinct().all()
    distinct_months = db.session.query(db.extract('month', File.date)).distinct().all()

    year = request.form.get('year') if request.method == 'POST' else request.args.get('year')
    month = request.form.get('month') if request.method == 'POST' else request.args.get('month')

    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return jsonify({'message': 'Invalid year or month. Please provide valid values.'}), 400

        # Query files matching the selected year and month
        files = File.query.filter(
            db.extract('year', File.date) == year,
            db.extract('month', File.date) == month
        ).all()

        # Group files by their title
        categorized_files = defaultdict(list)
        for file in files:
            categorized_files[file.title].append(file)

        return render_template(
            'display.html', 
            categorized_files=categorized_files, 
            year=year, 
            month=month, 
            is_admin=is_admin,
            distinct_years=distinct_years,
            distinct_months=distinct_months
        )
    else:
        return render_template('select.html', distinct_years=distinct_years, distinct_months=distinct_months)


# Add custom filter for month conversion
@app.template_filter('to_month_name')
def to_month_name(month):
    months = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    return months[month - 1]



    
@app.route('/view_images', methods=['GET'])
def view_images():
    year = request.args.get('year')
    month = request.args.get('month')

    if year and month:
        # Query files based on year and month
        files = File.query.filter(
            db.extract('year', File.date) == int(year),
            db.extract('month', File.date) == int(month)
        ).all()

        # Group files by their title
        categorized_files = defaultdict(list)
        for file in files:
            categorized_files[file.title].append(file)

        # Render the user-specific page
        return render_template('display.html', categorized_files=categorized_files, year=year, month=month)
    else:
        return render_template('select.html')

import zipfile
from flask import send_file

@app.route('/download_all/<string:title>/<int:year>/<int:month>', methods=['GET'])
def download_all(title, year, month):
    # Query the database for the files
    files = File.query.filter(
        File.title == title,
        db.extract('year', File.date) == year,
        db.extract('month', File.date) == month
    ).all()

    if not files:
        return "No files found", 404  # Return 404 if no files are found

    # Call the function to create the zip and send it as a response
    return create_zip_and_send_file(files, title, year, month)


def create_zip_and_send_file(files, title, year, month):
    # Create a ZIP archive in memory
    zip_stream = io.BytesIO()
    with zipfile.ZipFile(zip_stream, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            # Assuming 'file.image_data' holds the binary data of the file
            zipf.writestr(file.filename, file.image_data)
    
    # Move the cursor back to the start of the BytesIO stream before sending
    zip_stream.seek(0)

    # Send the zip file as an attachment for download
    return send_file(
        zip_stream,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"{title}_{year}_{month}.zip"
    )
    
    
    

@app.route('/logout2', methods=['GET','POST'])
def logout2():
    session.pop('token', None)  # Remove the token from session
    return redirect(url_for('index'))  # Redirect to the index page


@app.route('/todays-birthday', methods=['GET'])
@admin_required
def todays_birthday():
    today = datetime.today().date()

    # Query users whose birthday matches today's date
    users_today_birthday = User.query.filter(
        db.extract('month', User.birthday) == today.month,
        db.extract('day', User.birthday) == today.day
    ).all()

    # Pass the list of users to the template
    return render_template('todays_birthday.html', users=users_today_birthday)
from flask import flash, redirect, url_for, render_template
from datetime import datetime
from flask_mail import Message

@app.route('/send_birthday_emails', methods=['POST'])
@admin_required
def send_birthday_emails():
    today = datetime.today().date()
    users_with_birthday_today = User.query.filter(
        db.extract('month', User.birthday) == today.month,
        db.extract('day', User.birthday) == today.day
    ).all()

    if not users_with_birthday_today:
        flash("No birthdays today!", "info")
        return redirect(url_for('admindashboard'))  # Redirect back to the dashboard

    for user in users_with_birthday_today:
        # Render the HTML email content
        html_content = render_template('birthday_email.html', user=user)

        # Create and send the email
        msg = Message(
            subject=f"🎉 Happy Birthday, {user.name}! 🎂",
            sender=app.config['MAIL_USERNAME'],
            recipients=[user.email],
            html=html_content
        )
        mail.send(msg)

    flash("Birthday emails sent successfully!", "success")
    return redirect(url_for('admin_dashboard'))  # Redirect with flash message

@app.route('/update_remarks', methods=['POST'])
def update_remarks():
    issue_id = request.form.get('issue_id')
    remarks = request.form.get('remarks')
    
    issue = Issuues.query.get(issue_id)  # Use the corrected model name 'Issue'
    if issue:
        issue.remarks = remarks
        db.session.commit()
    return redirect(url_for('get_issue',remarks=remarks))  # Redirect to the page showing the issues

@app.route('/update_assigned_to', methods=['POST'])
def update_assigned_to():
    issue_id = request.form.get('issue_id')
    assigned_to = request.form.get('assigned_to')  # Corrected to 'assigned_to'
    
    # Ensure you are querying the correct model 'Issuues'
    issue = Issuues.query.get(issue_id)  
    if issue:
        issue.assigned_to = assigned_to  # Update assigned_to
        db.session.commit()
    return redirect(url_for('get_issue'))  # Redirect to the page showing the issues
@app.route('/update_issue_status', methods=['POST'])
@admin_required
def update_issue_status():
    issue_id = request.form['issue_id']
    new_status = request.form['status']
    remarks = request.form.get('remarks', '')  # Get the remarks if any, otherwise empty string
    print("remarks is:", remarks)
    issue = Issuues.query.get(issue_id)
    if issue:
        old_status = issue.status
        issue.status = new_status
        issue.remarks=remarks
        db.session.commit()
  
        # Add history entry with status and remarks
        history_entry = IssueHistory(issue_id=issue.id, status=new_status, remarks=remarks)
        db.session.add(history_entry)
        db.session.commit()

        flash(f"Issue status updated to '{new_status}'", "success")
    else:
        flash("Issue not found","danger")
    
    return redirect(url_for('get_issue'))




@app.route('/change', methods=['GET', 'POST'])
def change_password():
    # Get the token from the session
    token = session.get('token')

    if not token:
        flash("You need to log in to change your password.", "danger")
        return redirect(url_for('admin_login'))

    try:
        # Decode the token to get user ID and role
        decoded_token = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = decoded_token['user_id']
    except jwt.ExpiredSignatureError:
        flash("Session expired. Please log in again.", "danger")
        return redirect(url_for('admin_login'))
    except jwt.InvalidTokenError:
        flash("Invalid token. Please log in again.", "danger")
        return redirect(url_for('admin_login'))

    # Get the current user based on the decoded user ID
    user = User.query.get(user_id)

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("Passwords do not match. Please try again.", "danger")
            return redirect(url_for('change_password'))

        # Update the password (hash the password in production)
        user.password = new_password
        db.session.commit()

        flash("Password updated successfully!", "success")
        return render_template('dashboard.html',user=user)

    return render_template('change.html', user=user)


@app.route('/fetch_issue_details/<int:id>', methods=['GET'])
def fetch_issue_details(id):
    try:
        issue = Issuues.query.filter_by(id=id).first() 
        print("issue",issue)
        if issue:
            return jsonify({
                'success': True,
                'issue': {
                    'date_raised': issue.date_raised,
                    'due_date': issue.due_date
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Issue not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500




if __name__ == "__main__":
    app.run(debug=True)



@app.route('/history')
def history():
    token = session.get('user_token')
    if not token:
        flash("Please log in to view your history.", "warning")
        return redirect(url_for('login'))

    decoded_token = decode_jwt(token)
    if not decoded_token:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for('login'))

    user_id = decoded_token.get('user_id')
    if not user_id:
        flash("Invalid session data. Please log in again.", "warning")
        return redirect(url_for('login'))

    # Retrieve the user
    user = User.query.filter_by(id=user_id).first()
    if not user:
        flash("User not found. Please log in again.", "warning")
        return redirect(url_for('login'))

    # Fetch all issues raised by the user
    all_user_issues = Issuues.query.filter_by(id=user.id).order_by(Issuues.date_raised.desc()).all()

    # Retrieve filter parameters
    status_filter = request.args.get('status', 'All')
    start_date = request.args.get('start_date', None)
    end_date = request.args.get('end_date', None)
    due_start_date = request.args.get('due_start_date', None)  # Filter for due_date range start
    due_end_date = request.args.get('due_end_date', None)      # Filter for due_date range end

    # Filter issues based on the filters
    user_issues = all_user_issues
    if status_filter != 'All':
        user_issues = [issue for issue in user_issues if issue.status == status_filter]
    if start_date:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        user_issues = [issue for issue in user_issues if issue.date_raised >= start_date_obj]
    if end_date:
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        user_issues = [issue for issue in user_issues if issue.date_raised <= end_date_obj]
    if due_start_date:
        due_start_date_obj = datetime.strptime(due_start_date, "%Y-%m-%d")
        user_issues = [issue for issue in user_issues if issue.due_date >= due_start_date_obj]
    if due_end_date:
        due_end_date_obj = datetime.strptime(due_end_date, "%Y-%m-%d")
        user_issues = [issue for issue in user_issues if issue.due_date <= due_end_date_obj]

    # Fetch all issue histories related to these issues
    issue_ids = [issue.id for issue in user_issues]
    issue_history = IssueHistory.query.filter(IssueHistory.issue_id.in_(issue_ids)).order_by(IssueHistory.timestamp.desc()).all()

    # Organize issue history by issue_id for easy access
    issue_history_dict = {}
    for history in issue_history:
        if history.issue_id not in issue_history_dict:
            issue_history_dict[history.issue_id] = []
        issue_history_dict[history.issue_id].append(history)

    # Calculate stats
    total_tickets = len(all_user_issues)
    in_progress_count = sum(1 for issue in all_user_issues if issue.status == "In Progress")
    in_queued_count = sum(1 for issue in all_user_issues if issue.status == "In Queued")
    rejected_count = sum(1 for issue in all_user_issues if issue.status == "Rejected")
    on_hold_count = sum(1 for issue in all_user_issues if issue.status == "On Hold")
    completed_count = sum(1 for issue in all_user_issues if issue.status == "Completed")
    submitted_count = sum(1 for issue in all_user_issues if issue.status == "Submitted")

    # Now make sure we pass the `date_raised` and `due_date` to the template
    issues_data = [{
        "id": issue.id,
        "email": issue.email,
        "problem": issue.problem,
        "status": issue.status,
        "remarks": issue.remarks,
        "date_raised": issue.date_raised,  # Added date_raised
        "due_date": issue.due_date,        # Added due_date
        "status_remarks": issue.status_remarks or 'No remarks for status'
    } for issue in user_issues]

    # Render the template with the issue history data and other required data
    return render_template(
        'history.html',
        issues=issues_data,             # Pass the new list with date_raised and due_date
        issue_history=issue_history_dict,
        total_tickets=total_tickets,
        in_progress_count=in_progress_count,
        in_queued_count=in_queued_count,
        rejected_count=rejected_count,
        on_hold_count=on_hold_count,
        completed_count=completed_count,
        submitted_count=submitted_count,
        current_filter=status_filter,
        start_date=start_date,
        end_date=end_date,
        due_start_date=due_start_date,
        due_end_date=due_end_date
    )
