"""
Faculty Feedback System - Main Flask Application
This is the main application file containing all routes and business logic.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from werkzeug.utils import secure_filename
from models import student_model, faculty_model, feedback_model
import os

# Configuration for file uploads
UPLOAD_FOLDER = 'static/faculty_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # Change this in production

# Admin credentials (fixed as per requirements)
ADMIN_EMAIL = 'admin@college.com'
ADMIN_PASSWORD = 'admin123'


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    """Decorator to require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin login for admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    """Decorator to require student login for student routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'student':
            flash('Student access required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Student registration page"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        department = request.form.get('department')
        
        # Basic validation
        if not all([name, email, password, department]):
            flash('All fields are required.', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('signup.html')
        
        # Create student
        if student_model.create(name, email, password, department):
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email already exists. Please use a different email.', 'error')
            return render_template('signup.html')
    
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for students and admin"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if admin login
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['user_id'] = 'admin'
            session['user_type'] = 'admin'
            session['user_name'] = 'Admin'
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        # Check student login
        student = student_model.authenticate(email, password)
        if student:
            session['user_id'] = student['id']
            session['user_type'] = 'student'
            session['user_name'] = student['name']
            session['user_department'] = student['department']
            flash('Login successful!', 'success')
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password.', 'error')
            return render_template('login.html')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))


@app.route('/student_dashboard')
@student_required
def student_dashboard():
    """Student dashboard - select faculty to give feedback"""
    # Get all faculty members
    faculty_list = faculty_model.get_all()
    
    # Get faculty by student's department
    student_department = session.get('user_department')
    department_faculty = faculty_model.get_by_department(student_department)
    
    # Get average ratings for all faculty
    averages = feedback_model.get_all_averages()
    
    # Add average ratings to faculty data
    for faculty in faculty_list:
        faculty_id = faculty['id']
        if faculty_id in averages:
            faculty.update(averages[faculty_id])
        else:
            faculty.update({
                'avg_performance': 0,
                'avg_knowledge': 0,
                'avg_teaching_skills': 0,
                'avg_communication': 0,
                'avg_behavior': 0,
                'total_feedback': 0,
                'overall_average': 0
            })
    
    # Add average ratings to department faculty
    for faculty in department_faculty:
        faculty_id = faculty['id']
        if faculty_id in averages:
            faculty.update(averages[faculty_id])
        else:
            faculty.update({
                'avg_performance': 0,
                'avg_knowledge': 0,
                'avg_teaching_skills': 0,
                'avg_communication': 0,
                'avg_behavior': 0,
                'total_feedback': 0,
                'overall_average': 0
            })
    
    return render_template('student_dashboard.html', 
                         faculty_list=faculty_list, 
                         department_faculty=department_faculty,
                         student_department=student_department)


@app.route('/feedback/<int:faculty_id>')
@student_required
def feedback_form(faculty_id):
    """Feedback form for specific faculty"""
    faculty = faculty_model.get_by_id(faculty_id)
    if not faculty:
        flash('Faculty not found.', 'error')
        return redirect(url_for('student_dashboard'))
    
    # Check if student has already given feedback for this faculty
    student_id = session['user_id']
    if feedback_model.has_student_feedback_for_faculty(student_id, faculty_id):
        flash('You have already given feedback for this faculty.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    return render_template('feedback_form.html', faculty=faculty)


@app.route('/submit_feedback/<int:faculty_id>', methods=['POST'])
@student_required
def submit_feedback(faculty_id):
    """Submit feedback for faculty"""
    faculty = faculty_model.get_by_id(faculty_id)
    if not faculty:
        flash('Faculty not found.', 'error')
        return redirect(url_for('student_dashboard'))
    
    # Check if student has already given feedback for this faculty
    student_id = session['user_id']
    if feedback_model.has_student_feedback_for_faculty(student_id, faculty_id):
        flash('You have already given feedback for this faculty.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    # Get form data
    performance = int(request.form.get('performance'))
    knowledge = int(request.form.get('knowledge'))
    teaching_skills = int(request.form.get('teaching_skills'))
    communication = int(request.form.get('communication'))
    behavior = int(request.form.get('behavior'))
    comments = request.form.get('comments', '')
    
    # Validate ratings (1-5)
    ratings = [performance, knowledge, teaching_skills, communication, behavior]
    if not all(1 <= rating <= 5 for rating in ratings):
        flash('All ratings must be between 1 and 5.', 'error')
        return redirect(url_for('feedback_form', faculty_id=faculty_id))
    
    # Submit feedback
    if feedback_model.create(student_id, faculty_id, performance, knowledge, 
                           teaching_skills, communication, behavior, comments):
        flash('Feedback submitted successfully! Thank you for your input.', 'success')
        return redirect(url_for('student_dashboard'))
    else:
        flash('Error submitting feedback. Please try again.', 'error')
        return redirect(url_for('feedback_form', faculty_id=faculty_id))


@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard - view faculty with average ratings"""
    faculty_list = faculty_model.get_all()
    averages = feedback_model.get_all_averages()
    
    # Add average ratings to faculty data
    for faculty in faculty_list:
        faculty_id = faculty['id']
        if faculty_id in averages:
            faculty.update(averages[faculty_id])
        else:
            faculty.update({
                'avg_performance': 0,
                'avg_knowledge': 0,
                'avg_teaching_skills': 0,
                'avg_communication': 0,
                'avg_behavior': 0,
                'total_feedback': 0,
                'overall_average': 0
            })
    
    return render_template('admin_dashboard.html', faculty_list=faculty_list)


@app.route('/add_faculty', methods=['GET', 'POST'])
@admin_required
def add_faculty():
    """Add new faculty member"""
    if request.method == 'POST':
        name = request.form.get('name')
        department = request.form.get('department')
        subject = request.form.get('subject')
        image_file = request.files.get('image')
        
        # Basic validation
        if not all([name, department, subject]):
            flash('All fields are required.', 'error')
            return render_template('add_faculty.html')
        
        image_filename = None
        if image_file and image_file.filename != '':
            if allowed_file(image_file.filename):
                image_filename = secure_filename(image_file.filename)
                # Ensure unique filenames to prevent overwrites
                from datetime import datetime
                now = datetime.now().strftime("%Y%m%d%H%M%S")
                image_filename = f"{now}_{image_filename}"
                image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            else:
                flash('Invalid image format. Please use PNG, JPG, or JPEG.', 'error')
                return render_template('add_faculty.html')

        # Add faculty
        if faculty_model.create(name, department, subject, image_filename):
            flash('Faculty added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Error adding faculty. Please try again.', 'error')
            return render_template('add_faculty.html')
    
    return render_template('add_faculty.html')


@app.route('/view_feedback/<int:faculty_id>')
@admin_required
def view_feedback(faculty_id):
    """View detailed feedback report for a faculty"""
    faculty = faculty_model.get_by_id(faculty_id)
    if not faculty:
        flash('Faculty not found.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Get feedback data
    feedback_list = feedback_model.get_by_faculty(faculty_id)
    averages = feedback_model.get_average_ratings(faculty_id)
    
    return render_template('feedback_report.html', 
                         faculty=faculty, 
                         feedback_list=feedback_list, 
                         averages=averages)


@app.route('/update_faculty/<int:faculty_id>', methods=['POST'])
@admin_required
def update_faculty(faculty_id):
    """Update faculty details"""
    faculty = faculty_model.get_by_id(faculty_id)
    if not faculty:
        return jsonify({'success': False, 'message': 'Faculty not found.'}), 404

    name = request.form.get('name')
    department = request.form.get('department')
    subject = request.form.get('subject')

    if not all([name, department, subject]):
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    image_file = request.files.get('image')
    image_filename = faculty.get('image') # Keep old image by default
    image_updated = False

    if image_file and image_file.filename != '':
        if allowed_file(image_file.filename):
            # Delete old image if it exists
            if faculty.get('image') and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], faculty['image'])):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], faculty['image']))
            
            new_filename = secure_filename(image_file.filename)
            from datetime import datetime
            now = datetime.now().strftime("%Y%m%d%H%M%S")
            image_filename = f"{now}_{new_filename}"
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            image_updated = True
        else:
            return jsonify({'success': False, 'message': 'Invalid image format. Please use PNG, JPG, or JPEG.'}), 400

    # Update faculty in database (image_filename will be new or original)
    faculty_model.update(faculty_id, name, department, subject, image_filename)
    
    # Get updated faculty data to return
    updated_faculty = faculty_model.get_by_id(faculty_id)
    if updated_faculty.get('image'):
        updated_faculty['image_url'] = url_for('static', filename=f'faculty_images/{updated_faculty["image"]}')
    
    return jsonify({'success': True, 'message': 'Faculty updated successfully!', 'faculty': updated_faculty})

@app.route('/delete_faculty/<int:faculty_id>', methods=['POST'])
@admin_required
def delete_faculty(faculty_id):
    """Delete a faculty member and all associated feedback"""
    faculty = faculty_model.get_by_id(faculty_id)
    if not faculty:
        return jsonify({'success': False, 'message': 'Faculty not found.'}), 404

    # Delete associated image file
    image_filename = faculty.get('image')
    if image_filename:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

    # Delete faculty and all associated feedback
    if faculty_model.delete(faculty_id):
        flash(f'Faculty "{faculty["name"]}" and all associated feedback have been deleted.', 'success')
        return jsonify({'success': True, 'message': f'Faculty "{faculty["name"]}" deleted successfully.'})
    else:
        flash('Error deleting faculty. Please try again.', 'error')
        return jsonify({'success': False, 'message': 'Error deleting faculty.'}), 500



@app.route('/all_feedback')
@admin_required
def all_feedback():
    """View all student feedback with details"""
    feedback_list = feedback_model.get_all_feedback_with_details()
    return render_template('all_feedback.html', feedback_list=feedback_list)


# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('index.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('index.html'), 500


if __name__ == '__main__':
    # Create database tables on startup
    from models import db

    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Add some sample faculty data if database is empty
    faculty_list = faculty_model.get_all()
    if not faculty_list:
        sample_faculty = [
            ('Dr. John Smith', 'Computer Science', 'Data Structures'),
            ('Dr. Sarah Johnson', 'Computer Science', 'Algorithms'),
            ('Dr. Michael Brown', 'Mathematics', 'Calculus'),
            ('Dr. Emily Davis', 'Physics', 'Quantum Mechanics'),
            ('Dr. Robert Wilson', 'Computer Science', 'Database Systems')
        ]
        
        for name, department, subject in sample_faculty:
            faculty_model.create(name, department, subject)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
