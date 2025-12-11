Environment setup
=================

1) Make a new file named `.env` in the project root.
2) Put these variables in it and fill in your values:

```
SESSION_SECRET=your-random-secret
GROQ_API_KEY=your-groq-key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=you@example.com
SMTP_PASSWORD=your-smtp-or-app-password
WHATSAPP_SERVICE_URL=http://localhost:3002/send
```

3) Start the app after loading the env (example for bash on Windows with the venv):
```
source .venv/Scripts/activate
export $(grep -v '^#' .env | xargs)  # or set them manually
python app.py
```

Notes
- `SMTP_PORT=587` with STARTTLS is what the app uses by default.
- For Gmail, create an App Password and use it for `SMTP_PASSWORD`.
- `WHATSAPP_SERVICE_URL` points to the local WhatsApp Web.js bridge we added.

