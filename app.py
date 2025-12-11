import os
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from dotenv import load_dotenv
from database import db, UserPreference, Newsletter, User, AdminConfig
from news_fetcher import fetch_news
from summarizer import summarize_articles, generate_overall_summary
from pdf_generator import generate_pdf
from audio_generator import generate_audio
from email_sender import send_newsletter_email, create_newsletter_email_body, is_smtp_configured
from datetime import datetime
import re

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///newsletter.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    # Attempt to add prompt column if database was created before prompt existed
    try:
        db.session.execute('ALTER TABLE user_preferences ADD COLUMN prompt TEXT DEFAULT ""')
        db.session.commit()
    except Exception:
        db.session.rollback()

def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_whatsapp(number):
    """Validate WhatsApp number format."""
    cleaned = re.sub(r'[^\d+]', '', number)
    return len(cleaned) >= 10 and len(cleaned) <= 15

def sanitize_input(text):
    """Sanitize user input to prevent XSS."""
    if not text:
        return ''
    return text.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def build_public_url(path):
    """Create a full URL for static files based on the current request host."""
    base = request.host_url.rstrip('/')
    clean_path = path.lstrip('/')
    return f"{base}/{clean_path}"

def send_whatsapp_via_service(phone_number, message):
    """Send WhatsApp text message through the local WhatsApp service."""
    service_url = 'http://localhost:3002/send'
    try:
        resp = requests.post(service_url, json={'to': phone_number, 'message': message}, timeout=5)
        resp.raise_for_status()
        return True, None
    except Exception as exc:
        return False, str(exc)

def send_whatsapp_media_via_service(phone_number, file_paths, caption=''):
    """Send media files (PDF/audio) via WhatsApp service."""
    service_url = 'http://localhost:3002/send-media'
    try:
        resp = requests.post(service_url, json={
            'to': phone_number,
            'files': file_paths,
            'caption': caption
        }, timeout=15)
        resp.raise_for_status()
        return True, None
    except Exception as exc:
        return False, str(exc)

def send_newsletter_to_user(newsletter, user):
    """Send newsletter to a single user via email and WhatsApp."""
    successes = []
    errors = []

    if is_smtp_configured():
        try:
            email_body = create_newsletter_email_body(
                newsletter.title,
                newsletter.overall_summary or '',
                len(newsletter.topics.split(','))
            )
            send_newsletter_email(
                user.email,
                newsletter.title,
                email_body,
                newsletter.pdf_path,
                newsletter.audio_path
            )
            successes.append('email')
        except Exception as exc:
            errors.append(f'Email to {user.email} failed: {exc}')
    else:
        errors.append('SMTP not configured')

    pdf_link = build_public_url(newsletter.pdf_path) if newsletter.pdf_path else ''
    audio_link = build_public_url(newsletter.audio_path) if newsletter.audio_path else ''
    message_parts = [
        f"{newsletter.title}",
        newsletter.overall_summary or 'Here is your personalized newsletter.',
    ]
    if pdf_link:
        message_parts.append(f"PDF: {pdf_link}")
    if audio_link:
        message_parts.append(f"Audio: {audio_link}")
    message_parts.append("Sent via Newsletter Bot.")
    whatsapp_message = "\n\n".join(message_parts)

    ok, err = send_whatsapp_via_service(user.whatsapp_number, whatsapp_message)
    if ok:
        successes.append('whatsapp')
    else:
        errors.append(f'WhatsApp to {user.whatsapp_number} failed: {err}')

    # Send media (PDF and audio) as documents if available
    media_files = []
    if newsletter.pdf_path and os.path.exists(newsletter.pdf_path):
        media_files.append(os.path.abspath(newsletter.pdf_path))
    if newsletter.audio_path and os.path.exists(newsletter.audio_path):
        media_files.append(os.path.abspath(newsletter.audio_path))

    if media_files:
        ok_media, err_media = send_whatsapp_media_via_service(
            user.whatsapp_number,
            media_files,
            caption=newsletter.title
        )
        if ok_media:
            successes.append('whatsapp-media')
        else:
            errors.append(f'WhatsApp media to {user.whatsapp_number} failed: {err_media}')

    return successes, errors

@app.route('/')
def index():
    preferences = UserPreference.query.first()
    newsletters = Newsletter.query.order_by(Newsletter.created_at.desc()).limit(10).all()
    users = User.query.filter_by(is_active=True).all()
    return render_template('index.html', preferences=preferences, newsletters=newsletters, users=users)

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    pref = UserPreference.query.first()
    
    if request.method == 'POST':
        topics = sanitize_input(request.form.get('topics', ''))
        prompt_text = sanitize_input(request.form.get('prompt', ''))
        primary_color = request.form.get('primary_color', '#1a73e8')
        secondary_color = request.form.get('secondary_color', '#4285f4')
        font_style = request.form.get('font_style', 'modern')
        
        if pref:
            pref.topics = topics
            pref.prompt = prompt_text
            pref.primary_color = primary_color
            pref.secondary_color = secondary_color
            pref.font_style = font_style
        else:
            pref = UserPreference(
                topics=topics,
                prompt=prompt_text,
                primary_color=primary_color,
                secondary_color=secondary_color,
                font_style=font_style
            )
            db.session.add(pref)
        
        db.session.commit()
        flash('Preferences saved successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('preferences.html', preferences=pref)

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'POST':
        name = sanitize_input(request.form.get('name', '').strip())
        email = request.form.get('email', '').strip().lower()
        whatsapp = request.form.get('whatsapp', '').strip()
        topics = sanitize_input(request.form.get('topics', '').strip())
        primary_color = request.form.get('primary_color', '#1a73e8')
        secondary_color = request.form.get('secondary_color', '#4285f4')
        font_style = request.form.get('font_style', 'modern')
        
        if not name or len(name) < 2:
            flash('Please enter a valid name.', 'error')
            return redirect(url_for('subscribe'))
        
        if not validate_email(email):
            flash('Please enter a valid email address.', 'error')
            return redirect(url_for('subscribe'))
        
        if not validate_whatsapp(whatsapp):
            flash('Please enter a valid WhatsApp number with country code (e.g., +1234567890).', 'error')
            return redirect(url_for('subscribe'))
        
        if not topics:
            flash('Please enter at least one topic of interest.', 'error')
            return redirect(url_for('subscribe'))
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            existing_user.name = name
            existing_user.whatsapp_number = whatsapp
            existing_user.topics = topics
            existing_user.primary_color = primary_color
            existing_user.secondary_color = secondary_color
            existing_user.font_style = font_style
            existing_user.is_active = True
            flash('Your subscription has been updated!', 'success')
        else:
            user = User(
                name=name,
                email=email,
                whatsapp_number=whatsapp,
                topics=topics,
                primary_color=primary_color,
                secondary_color=secondary_color,
                font_style=font_style
            )
            db.session.add(user)
            flash('You have been subscribed successfully!', 'success')
        
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('subscribe.html')

@app.route('/users')
def list_users():
    users = User.query.filter_by(is_active=True).all()
    return render_template('users.html', users=users)

@app.route('/generate', methods=['POST'])
def generate_newsletter():
    pref = UserPreference.query.first()
    
    if not pref or not pref.topics:
        flash('Please set your preferences first!', 'error')
        return redirect(url_for('preferences'))
    
    try:
        topics = [t.strip() for t in pref.topics.split(',')]
        prompt_text = getattr(pref, 'prompt', '') or ''
        articles = fetch_news(topics)
        
        if not articles:
            flash('No news articles found for your topics. Try different keywords.', 'warning')
            return redirect(url_for('index'))
        
        summarized = summarize_articles(articles, prompt=prompt_text)
        overall_summary = generate_overall_summary(summarized, prompt=prompt_text)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f'newsletter_{timestamp}.pdf'
        audio_filename = f'newsletter_{timestamp}.mp3'
        
        pdf_path = os.path.join('static', 'newsletters', pdf_filename)
        audio_path = os.path.join('static', 'newsletters', audio_filename)
        
        os.makedirs(os.path.join('static', 'newsletters'), exist_ok=True)
        
        generate_pdf(
            summarized,
            pdf_path,
            primary_color=pref.primary_color,
            secondary_color=pref.secondary_color,
            font_style=pref.font_style,
            overall_summary=overall_summary
        )
        
        generate_audio(summarized, audio_path, overall_summary)
        
        newsletter = Newsletter(
            title=f"Newsletter - {datetime.now().strftime('%B %d, %Y')}",
            topics=pref.topics,
            overall_summary=overall_summary,
            pdf_path=pdf_path,
            audio_path=audio_path
        )
        db.session.add(newsletter)
        db.session.commit()
        
        # Auto-send to all active users (email + WhatsApp)
        successes = []
        errors = []
        active_users = User.query.filter_by(is_active=True).all()
        for u in active_users:
            s, e = send_newsletter_to_user(newsletter, u)
            successes.extend(s)
            errors.extend(e)
        
        if successes:
            flash(f'Newsletter generated and sent via: {", ".join(set(successes))}', 'success')
        else:
            flash('Newsletter generated, but sending failed. Check configuration.', 'error')
        for msg in errors:
            flash(msg, 'error')

        return redirect(url_for('view_newsletter', newsletter_id=newsletter.id))
        
    except Exception as e:
        flash(f'Error generating newsletter: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/generate-for-user/<int:user_id>', methods=['POST'])
def generate_for_user(user_id):
    user = User.query.get_or_404(user_id)
    
    try:
        topics = [t.strip() for t in user.topics.split(',')]
        pref_prompt = getattr(UserPreference.query.first(), 'prompt', '') if UserPreference.query.first() else ''
        articles = fetch_news(topics)
        
        if not articles:
            flash(f'No news articles found for {user.name}\'s topics.', 'warning')
            return redirect(url_for('list_users'))
        
        summarized = summarize_articles(articles, prompt=pref_prompt)
        overall_summary = generate_overall_summary(summarized, prompt=pref_prompt)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f'newsletter_{user.id}_{timestamp}.pdf'
        audio_filename = f'newsletter_{user.id}_{timestamp}.mp3'
        
        pdf_path = os.path.join('static', 'newsletters', pdf_filename)
        audio_path = os.path.join('static', 'newsletters', audio_filename)
        
        os.makedirs(os.path.join('static', 'newsletters'), exist_ok=True)
        
        generate_pdf(
            summarized,
            pdf_path,
            primary_color=user.primary_color,
            secondary_color=user.secondary_color,
            font_style=user.font_style,
            overall_summary=overall_summary
        )
        
        generate_audio(summarized, audio_path, overall_summary)
        
        newsletter = Newsletter(
            title=f"Newsletter for {user.name} - {datetime.now().strftime('%B %d, %Y')}",
            topics=user.topics,
            overall_summary=overall_summary,
            pdf_path=pdf_path,
            audio_path=audio_path
        )
        db.session.add(newsletter)
        db.session.commit()
        
        successes, errors = send_newsletter_to_user(newsletter, user)
        if successes:
            flash(f'Newsletter generated and sent to {user.name} via: {", ".join(successes)}', 'success')
        else:
            flash(f'Newsletter generated for {user.name}, but sending failed.', 'error')
        for msg in errors:
            flash(msg, 'error')
        return redirect(url_for('view_newsletter', newsletter_id=newsletter.id))
        
    except Exception as e:
        flash(f'Error generating newsletter: {str(e)}', 'error')
        return redirect(url_for('list_users'))

@app.route('/send-newsletter/<int:newsletter_id>/<int:user_id>', methods=['POST'])
def send_newsletter(newsletter_id, user_id):
    newsletter = Newsletter.query.get_or_404(newsletter_id)
    user = User.query.get_or_404(user_id)
    
    send_email = request.form.get('send_email') == 'on'
    send_whatsapp = request.form.get('send_whatsapp') == 'on'
    
    errors = []
    successes = []
    
    if send_email:
        try:
            email_body = create_newsletter_email_body(
                newsletter.title,
                newsletter.overall_summary or '',
                len(newsletter.topics.split(','))
            )
            send_newsletter_email(
                user.email,
                newsletter.title,
                email_body,
                newsletter.pdf_path,
                newsletter.audio_path
            )
            successes.append('Email sent successfully!')
        except Exception as e:
            errors.append(f'Email failed: {str(e)}')
    
    if send_whatsapp:
        pdf_link = build_public_url(newsletter.pdf_path) if newsletter.pdf_path else ''
        audio_link = build_public_url(newsletter.audio_path) if newsletter.audio_path else ''
        message_parts = [
            f"{newsletter.title}",
            newsletter.overall_summary or 'Here is your personalized newsletter.',
        ]
        if pdf_link:
            message_parts.append(f"PDF: {pdf_link}")
        if audio_link:
            message_parts.append(f"Audio: {audio_link}")
        message_parts.append("Sent via Newsletter Bot.")
        whatsapp_message = "\n\n".join(message_parts)

        ok, err = send_whatsapp_via_service(user.whatsapp_number, whatsapp_message)
        if ok:
            successes.append('WhatsApp message sent (via admin session).')
        else:
            errors.append(f'WhatsApp failed: {err}')
    
    for msg in successes:
        flash(msg, 'success')
    for msg in errors:
        flash(msg, 'error')
    
    return redirect(url_for('view_newsletter', newsletter_id=newsletter_id))

@app.route('/newsletter/<int:newsletter_id>')
def view_newsletter(newsletter_id):
    newsletter = Newsletter.query.get_or_404(newsletter_id)
    users = User.query.filter_by(is_active=True).all()
    smtp_configured = is_smtp_configured()
    return render_template('newsletter.html', newsletter=newsletter, users=users, smtp_configured=smtp_configured)

@app.route('/download/pdf/<int:newsletter_id>')
def download_pdf(newsletter_id):
    newsletter = Newsletter.query.get_or_404(newsletter_id)
    return send_file(newsletter.pdf_path, as_attachment=True)

@app.route('/download/audio/<int:newsletter_id>')
def download_audio(newsletter_id):
    newsletter = Newsletter.query.get_or_404(newsletter_id)
    return send_file(newsletter.audio_path, as_attachment=True)

@app.route('/admin')
def admin():
    config = AdminConfig.query.first()
    users = User.query.all()
    newsletters = Newsletter.query.order_by(Newsletter.created_at.desc()).limit(20).all()
    
    smtp_configured = bool(os.environ.get('SMTP_EMAIL') and os.environ.get('SMTP_PASSWORD'))
    
    return render_template('admin.html', 
                          config=config, 
                          users=users, 
                          newsletters=newsletters,
                          smtp_configured=smtp_configured)

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    flash(f'User {user.name} has been deactivated.', 'success')
    return redirect(url_for('admin'))

@app.route('/api/preview-news', methods=['POST'])
def preview_news():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    
    topics = data.get('topics', '')
    if not topics or not isinstance(topics, str):
        return jsonify({'error': 'No topics provided or invalid format'}), 400
    
    topic_list = [t.strip() for t in topics.split(',') if t.strip()]
    if not topic_list:
        return jsonify({'error': 'No valid topics found'}), 400
    
    try:
        articles = fetch_news(topic_list, limit=3)
        return jsonify({'articles': articles})
    except Exception as e:
        return jsonify({'error': f'Failed to fetch news: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
