const express = require('express');
const bodyParser = require('body-parser');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const path = require('path');
const fs = require('fs');

const PORT = process.env.WHATSAPP_SERVICE_PORT || 3002;
const SESSION_DIR = path.join(__dirname, '.wwebjs_auth');

let client = null;

const createClient = () =>
  new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    },
  });

const wireClientEvents = (c) => {
  c.on('qr', (qr) => {
    qrcode.generate(qr, { small: true });
    console.log('Scan this QR to log in the admin WhatsApp account.');
  });

  c.on('ready', () => {
    console.log('WhatsApp service is ready (logged in).');
  });

  c.on('auth_failure', (msg) => {
    console.error('WhatsApp auth failure:', msg);
  });

  c.on('disconnected', (reason) => {
    console.error('WhatsApp client disconnected:', reason);
    initClient(true);
  });
};

const initClient = (recreate = false) => {
  try {
    if (client && recreate) {
      client.destroy();
    }
  } catch (e) {
    console.error('Error destroying existing client:', e);
  }

  client = createClient();
  wireClientEvents(client);
  client.initialize();
};

initClient();

const app = express();
app.use(bodyParser.json());

const normalizeNumber = (number) => {
  if (!number) return null;
  const cleaned = number.replace(/[^\d+]/g, '');
  if (!cleaned) return null;
  // WhatsApp Web.js expects the country code and the @c.us suffix
  const withPlus = cleaned.startsWith('+') ? cleaned : `+${cleaned}`;
  return `${withPlus.replace(/\+/g, '')}@c.us`;
};

const mimeFromExt = (ext) => {
  const lower = ext.toLowerCase();
  if (lower === '.pdf') return 'application/pdf';
  if (lower === '.mp3') return 'audio/mpeg';
  if (lower === '.wav') return 'audio/wav';
  if (lower === '.m4a') return 'audio/m4a';
  return 'application/octet-stream';
};

app.post('/send', async (req, res) => {
  const { to, message } = req.body || {};
  if (!to || !message) {
    return res.status(400).json({ error: 'Both "to" and "message" are required.' });
  }

  if (!client) {
    return res.status(503).json({ error: 'WhatsApp client not initialized.' });
  }

  const waId = normalizeNumber(to);
  if (!waId) {
    return res.status(400).json({ error: 'Invalid phone number format.' });
  }

  try {
    await client.sendMessage(waId, message);
    return res.json({ status: 'sent' });
  } catch (err) {
    console.error('Error sending WhatsApp message:', err);
    return res.status(500).json({ error: 'Failed to send message.' });
  }
});

app.post('/send-media', async (req, res) => {
  const { to, files = [], caption = '' } = req.body || {};
  if (!to || !Array.isArray(files) || files.length === 0) {
    return res.status(400).json({ error: '"to" and non-empty "files" array are required.' });
  }

  if (!client) {
    return res.status(503).json({ error: 'WhatsApp client not initialized.' });
  }

  const waId = normalizeNumber(to);
  if (!waId) {
    return res.status(400).json({ error: 'Invalid phone number format.' });
  }

  try {
    // Send caption first (if provided)
    if (caption) {
      await client.sendMessage(waId, caption);
    }

    for (const filePath of files) {
      const abs = path.resolve(filePath);
      if (!fs.existsSync(abs)) {
        return res.status(400).json({ error: `File not found: ${abs}` });
      }
      const data = fs.readFileSync(abs, { encoding: 'base64' });
      const ext = path.extname(abs);
      const mime = mimeFromExt(ext);
      const filename = path.basename(abs);
      const media = new MessageMedia(mime, data, filename);
      await client.sendMessage(waId, media, { sendMediaAsDocument: true });
    }

    return res.json({ status: 'sent' });
  } catch (err) {
    console.error('Error sending WhatsApp media:', err);
    return res.status(500).json({ error: 'Failed to send media.' });
  }
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.post('/reset-session', async (req, res) => {
  try {
    if (client) {
      await client.destroy();
      client = null;
    }
  } catch (e) {
    console.error('Error destroying client on reset:', e);
  }

  try {
    if (fs.existsSync(SESSION_DIR)) {
      fs.rmSync(SESSION_DIR, { recursive: true, force: true });
      console.log('Cleared WhatsApp session store to force a new QR.');
    }
  } catch (e) {
    console.error('Error clearing session directory:', e);
  }

  initClient(true);
  res.json({ status: 'reset', message: 'Session cleared. Watch terminal for new QR.' });
});

const server = app.listen(PORT, () => {
  console.log(`WhatsApp service listening on http://localhost:${PORT}`);
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`Port ${PORT} is already in use. Stop the other process or set WHATSAPP_SERVICE_PORT.`);
  } else {
    console.error('Server error:', err);
  }
  process.exit(1);
});

