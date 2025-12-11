Personal Newsletter Generator
Overview
A Flask-based web application that generates personalized news newsletters in PDF and audio format based on user preferences. Features subscriber management, email delivery via SMTP, and WhatsApp integration.

Features
User subscription with email and WhatsApp number
User preference management (topics, colors, font styles)
News fetching from RSS feeds (BBC, NYT) with article images
AI-powered content summarization using Groq (free)
Overall AI summary of all news articles
Custom PDF generation with links and images using ReportLab
Text-to-speech audio using gTTS
Email delivery via SMTP
WhatsApp delivery support (via WhatsApp Web.js)
Admin panel for managing subscribers and newsletters
Project Structure
/
├── app.py              # Main Flask application with all routes
├── database.py         # SQLite database models (User, Newsletter, etc.)
├── news_fetcher.py     # RSS feed parsing with image extraction
├── summarizer.py       # Groq AI integration for summarization
├── pdf_generator.py    # PDF creation with links, images, overall summary
├── audio_generator.py  # Text-to-speech with gTTS
├── email_sender.py     # SMTP email delivery with attachments
├── templates/          # Jinja2 HTML templates
│   ├── base.html       # Base layout with navigation
│   ├── index.html      # Home page
│   ├── preferences.html # Preference settings
│   ├── subscribe.html  # User subscription form
│   ├── users.html      # Subscriber list
│   ├── newsletter.html # Newsletter view with send options
│   └── admin.html      # Admin panel
├── static/
│   ├── css/style.css
│   └── newsletters/    # Generated PDF and audio files
└── instance/
    └── newsletter.db   # SQLite database

Running the Application
The app runs on port 5000 with Flask's development server.

Environment Variables
SESSION_SECRET - Flask session secret key
GROQ_API_KEY - Groq API key for free AI summarization (https://console.groq.com)
SMTP_HOST - SMTP server hostname (default: smtp.gmail.com)
SMTP_PORT - SMTP port (default: 587)
SMTP_EMAIL - Email address for sending newsletters
SMTP_PASSWORD - SMTP password or app password
Recent Changes
December 11, 2025: Added subscriber management with email/WhatsApp
December 11, 2025: Added article links and images to PDF
December 11, 2025: Added AI-powered overall summary
December 11, 2025: Added email delivery via SMTP
December 11, 2025: Added admin panel for subscriber management
December 11, 2025: Initial project setup with core features