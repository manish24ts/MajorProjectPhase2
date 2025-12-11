from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    whatsapp_number = db.Column(db.String(20), nullable=False)
    topics = db.Column(db.Text, nullable=False)
    primary_color = db.Column(db.String(7), default='#1a73e8')
    secondary_color = db.Column(db.String(7), default='#4285f4')
    font_style = db.Column(db.String(20), default='modern')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserPreference(db.Model):
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    topics = db.Column(db.Text, nullable=False)
    prompt = db.Column(db.Text, default='')
    primary_color = db.Column(db.String(7), default='#1a73e8')
    secondary_color = db.Column(db.String(7), default='#4285f4')
    font_style = db.Column(db.String(20), default='modern')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Newsletter(db.Model):
    __tablename__ = 'newsletters'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    topics = db.Column(db.Text, nullable=False)
    overall_summary = db.Column(db.Text)
    pdf_path = db.Column(db.String(500))
    audio_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AdminConfig(db.Model):
    __tablename__ = 'admin_config'
    
    id = db.Column(db.Integer, primary_key=True)
    whatsapp_connected = db.Column(db.Boolean, default=False)
    smtp_configured = db.Column(db.Boolean, default=False)
    smtp_host = db.Column(db.String(200))
    smtp_port = db.Column(db.Integer, default=587)
    smtp_email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
