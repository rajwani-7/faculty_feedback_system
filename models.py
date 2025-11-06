"""
Database models for Faculty Feedback System
This module defines the database schema and models for the application.
"""

import sqlite3
import bcrypt
from datetime import datetime


class Database:
    """Database connection and initialization class"""
    
    def __init__(self, db_name='database.db'):
        """Initialize database connection"""
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create Student table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Student (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                department TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create Faculty table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Faculty (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                subject TEXT NOT NULL,
                image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create Feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                faculty_id INTEGER NOT NULL,
                performance INTEGER NOT NULL CHECK (performance >= 1 AND performance <= 5),
                knowledge INTEGER NOT NULL CHECK (knowledge >= 1 AND knowledge <= 5),
                teaching_skills INTEGER NOT NULL CHECK (teaching_skills >= 1 AND teaching_skills <= 5),
                communication INTEGER NOT NULL CHECK (communication >= 1 AND communication <= 5),
                behavior INTEGER NOT NULL CHECK (behavior >= 1 AND behavior <= 5),
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES Student (id),
                FOREIGN KEY (faculty_id) REFERENCES Faculty (id)
            )
        ''')
        
        conn.commit()
        conn.close()


class Student:
    """Student model for database operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, name, email, password, department):
        """Create a new student"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Hash password using bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        try:
            cursor.execute('''
                INSERT INTO Student (name, email, password, department)
                VALUES (?, ?, ?, ?)
            ''', (name, email, hashed_password, department))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Email already exists
        finally:
            conn.close()
    
    def authenticate(self, email, password):
        """Authenticate student login"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM Student WHERE email = ?', (email,))
        student = cursor.fetchone()
        conn.close()
        
        if student and bcrypt.checkpw(password.encode('utf-8'), student['password']):
            return dict(student)
        return None
    
    def get_by_id(self, student_id):
        """Get student by ID"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM Student WHERE id = ?', (student_id,))
        student = cursor.fetchone()
        conn.close()
        
        return dict(student) if student else None


class Faculty:
    """Faculty model for database operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, name, department, subject, image=None):
        """Create a new faculty member"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO Faculty (name, department, subject, image)
            VALUES (?, ?, ?, ?)
        ''', (name, department, subject, image))
        conn.commit()
        conn.close()
        return True
    
    def get_all(self):
        """Get all faculty members"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM Faculty ORDER BY name')
        faculty = cursor.fetchall()
        conn.close()
        
        return [dict(f) for f in faculty]
    
    def get_by_id(self, faculty_id):
        """Get faculty by ID"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM Faculty WHERE id = ?', (faculty_id,))
        faculty = cursor.fetchone()
        conn.close()
        
        return dict(faculty) if faculty else None
    
    def get_by_department(self, department):
        """Get faculty by department"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM Faculty WHERE department = ? ORDER BY name', (department,))
        faculty = cursor.fetchall()
        conn.close()
        
        return [dict(f) for f in faculty]

    def update(self, faculty_id, name, department, subject, image=None):
        """Update a faculty member's details"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # This single query handles all cases.
        # If `image` is a new filename, it's updated.
        # If `image` is the old filename (or None), it remains unchanged or is set to None.
        cursor.execute('UPDATE Faculty SET name = ?, department = ?, subject = ?, image = ? WHERE id = ?',
                       (name, department, subject, image, faculty_id))
        conn.commit()
        conn.close()
        return True
    
    def delete(self, faculty_id):
        """Delete faculty member and all associated feedback"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # First delete all feedback for this faculty
            cursor.execute('DELETE FROM Feedback WHERE faculty_id = ?', (faculty_id,))
            # Then delete the faculty
            cursor.execute('DELETE FROM Faculty WHERE id = ?', (faculty_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()


class Feedback:
    """Feedback model for database operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, student_id, faculty_id, performance, knowledge, teaching_skills, communication, behavior, comments):
        """Create new feedback"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO Feedback (student_id, faculty_id, performance, knowledge, teaching_skills, communication, behavior, comments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, faculty_id, performance, knowledge, teaching_skills, communication, behavior, comments))
        conn.commit()
        conn.close()
        return True
    
    def get_by_faculty(self, faculty_id):
        """Get all feedback for a specific faculty"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.*, s.department as student_department
            FROM Feedback f
            JOIN Student s ON f.student_id = s.id
            WHERE f.faculty_id = ?
            ORDER BY f.created_at DESC
        ''', (faculty_id,))
        feedback = cursor.fetchall()
        conn.close()
        
        return [dict(f) for f in feedback]
    
    def get_average_ratings(self, faculty_id):
        """Get average ratings for a faculty"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                AVG(performance) as avg_performance,
                AVG(knowledge) as avg_knowledge,
                AVG(teaching_skills) as avg_teaching_skills,
                AVG(communication) as avg_communication,
                AVG(behavior) as avg_behavior,
                COUNT(*) as total_feedback
            FROM Feedback 
            WHERE faculty_id = ?
        ''', (faculty_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result['total_feedback'] > 0:
            return {
                'avg_performance': round(result['avg_performance'], 2),
                'avg_knowledge': round(result['avg_knowledge'], 2),
                'avg_teaching_skills': round(result['avg_teaching_skills'], 2),
                'avg_communication': round(result['avg_communication'], 2),
                'avg_behavior': round(result['avg_behavior'], 2),
                'total_feedback': result['total_feedback'],
                'overall_average': round((result['avg_performance'] + result['avg_knowledge'] + 
                                        result['avg_teaching_skills'] + result['avg_communication'] + 
                                        result['avg_behavior']) / 5, 2)
            }
        return None
    
    def get_all_averages(self):
        """Get average ratings for all faculty"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                faculty_id,
                AVG(performance) as avg_performance,
                AVG(knowledge) as avg_knowledge,
                AVG(teaching_skills) as avg_teaching_skills,
                AVG(communication) as avg_communication,
                AVG(behavior) as avg_behavior,
                COUNT(*) as total_feedback
            FROM Feedback 
            GROUP BY faculty_id
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        averages = {}
        for result in results:
            faculty_id = result['faculty_id']
            averages[faculty_id] = {
                'avg_performance': round(result['avg_performance'], 2),
                'avg_knowledge': round(result['avg_knowledge'], 2),
                'avg_teaching_skills': round(result['avg_teaching_skills'], 2),
                'avg_communication': round(result['avg_communication'], 2),
                'avg_behavior': round(result['avg_behavior'], 2),
                'total_feedback': result['total_feedback'],
                'overall_average': round((result['avg_performance'] + result['avg_knowledge'] + 
                                        result['avg_teaching_skills'] + result['avg_communication'] + 
                                        result['avg_behavior']) / 5, 2)
            }
        return averages
    
    def has_student_feedback_for_faculty(self, student_id, faculty_id):
        """Check if student has already given feedback for a faculty"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM Feedback 
            WHERE student_id = ? AND faculty_id = ?
        ''', (student_id, faculty_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['count'] > 0
    
    def get_all_feedback_with_details(self):
        """Get all feedback with student and faculty details for admin"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                f.*,
                s.name as student_name,
                s.department as student_department,
                fac.name as faculty_name,
                fac.department as faculty_department,
                fac.subject as faculty_subject
            FROM Feedback f
            JOIN Student s ON f.student_id = s.id
            JOIN Faculty fac ON f.faculty_id = fac.id
            ORDER BY f.created_at DESC
        ''')
        feedback = cursor.fetchall()
        conn.close()
        
        return [dict(f) for f in feedback]


# Initialize database when module is imported
db = Database()
student_model = Student(db)
faculty_model = Faculty(db)
feedback_model = Feedback(db)
