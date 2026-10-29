/**
 * doshie_whatsapp.js - Doshie WhatsApp Bridge
 *
 * Runs WhatsApp Web via whatsapp-web.js and exposes a local HTTP API
 * so Doshie (Python) can send messages, receive messages, and route
 * incoming messages to Aeriel for AI replies.
 *
 * First run: shows a QR code to scan with your WhatsApp phone.
 * After that: session is saved and auto-reconnects.
 *
 * API endpoints (default port 5099):
 *   GET  /status          — connection status
 *   POST /send            — send a message { to, message }
 *   GET  /messages        — get recent received messages
 *   POST /clear           — clear the message queue
 *   GET  /contacts        — list all WhatsApp contacts
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const http = require('http');

const PORT = process.env.DOSHIE_WA_PORT || 5099;
const DOSHIE_API = process.env.DOSHIE_API || 'http://127.0.0.1:5000';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let waStatus = 'initializing';   // initializing | qr_pending | ready | disconnected
let qrCode = null;
let pairingCode = null;
const messageQueue = [];          // Incoming messages waiting for Doshie to read
const MAX_QUEUE = 200;

// ---------------------------------------------------------------------------
// WhatsApp Client
// ---------------------------------------------------------------------------
const client = new Client({
  authStrategy: new LocalAuth({
    dataPath: __dirname + '/wa_session'
  }),
  pairWithPhoneNumber: '19153296410',
  webVersionCache: {
    type: 'remote',
    remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.3000.1052198210-alpha.html',
  },
  puppeteer: {
    executablePath: '/usr/bin/google-chrome',
    headless: true,
    protocolTimeout: 0,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--no-first-run',
      '--no-default-browser-check',
    ],
  },
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
});

client.on('code', (code) => {
  pairingCode = code;
  console.log(`\n🔑 WhatsApp Pairing Code: ${code}\n`);
});

client.on('loading_screen', (percent, message) => {
  console.log(`⏳ Loading WhatsApp: ${percent}% - ${message || ''}`);
});

client.on('auth_failure', (msg) => {
  console.error('❌ WhatsApp auth failure:', msg);
});

client.on('qr', (qr) => {
  waStatus = 'qr_pending';
  qrCode = qr;
  console.log('\n🔗 Scan this QR code with WhatsApp on your phone:\n');
  qrcode.generate(qr, { small: true });
  console.log('\nOr open Doshie and go to Settings → WhatsApp to scan.\n');
});

client.on('authenticated', () => {
  console.log('✅ WhatsApp authenticated.');
  waStatus = 'authenticated';
  qrCode = null;
});

client.on('ready', () => {
  console.log('✅ WhatsApp ready! Doshie is connected.');
  waStatus = 'ready';
  qrCode = null;
});

client.on('disconnected', (reason) => {
  console.log('❌ WhatsApp disconnected:', reason);
  waStatus = 'disconnected';
  qrCode = null;
  // Auto-reconnect after 10s
  setTimeout(() => {
    console.log('🔄 Reconnecting WhatsApp...');
    client.initialize().catch(console.error);
  }, 10000);
});

// Unhandled error protection
process.on('unhandledRejection', (reason) => {
  console.warn('⚠️ WhatsApp Rejection:', reason && reason.message ? reason.message : reason);
});
process.on('uncaughtException', (err) => {
  console.error('⚠️ WhatsApp Exception:', err && err.message ? err.message : err);
});

// Incoming messages → queue for Doshie + auto-route to AI
client.on('message', async (msg) => {
  try {
    if (msg.isStatus) return;

    let contactName = msg.from;
    try {
      const contact = await msg.getContact();
      if (contact) {
        contactName = contact.pushname || contact.name || msg.from;
      }
    } catch (_) {}

    let isGroup = typeof msg.from === 'string' && msg.from.endsWith('@g.us');
    let groupName = null;
    try {
      const chat = await msg.getChat();
      if (chat) {
        isGroup = Boolean(chat.isGroup);
        groupName = chat.isGroup ? chat.name : null;
      }
    } catch (_) {}

    const entry = {
      id: (msg.id && msg.id._serialized) || String(Date.now()),
      from: msg.from,
      from_name: contactName,
      to: msg.to,
      body: msg.body || '',
      timestamp: msg.timestamp || Math.floor(Date.now() / 1000),
      is_group: isGroup,
      group_name: groupName,
      has_media: Boolean(msg.hasMedia),
      received_at: new Date().toISOString(),
    };

    // Add to queue
    messageQueue.unshift(entry);
    if (messageQueue.length > MAX_QUEUE) messageQueue.pop();

    console.log(`📩 WhatsApp from ${entry.from_name}: ${entry.body.slice(0, 80)}`);

    // Forward to Doshie for AI routing (non-blocking)
    forwardToDoshie(entry).catch(() => {});
  } catch (err) {
    console.error('Error processing WhatsApp message:', err && err.message ? err.message : err);
  }
});

// ---------------------------------------------------------------------------
// Forward incoming message to Doshie for AI reply decision
// ---------------------------------------------------------------------------
async function forwardToDoshie(entry) {
  const payload = JSON.stringify({
    source: 'whatsapp',
    from: entry.from_name,
    phone: entry.from,
    message: entry.body,
    is_group: entry.is_group,
    group_name: entry.group_name,
    timestamp: entry.timestamp,
  });

  return new Promise((resolve) => {
    try {
      const req = http.request(
        `${DOSHIE_API}/api/whatsapp/incoming`,
        { method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) } },
        (res) => { res.resume(); resolve(); }
      );
      req.on('error', resolve);
      req.setTimeout(3000, () => { req.destroy(); resolve(); });
      req.write(payload);
      req.end();
    } catch { resolve(); }
  });
}

// ---------------------------------------------------------------------------
// HTTP API for Doshie (Python) to call
// ---------------------------------------------------------------------------
const api = express();
api.use(express.json());

// Status
api.get('/status', (req, res) => {
  res.json({
    status: waStatus,
    qr_available: !!qrCode,
    qr: qrCode,
    pairing_code: pairingCode,
    queue_size: messageQueue.length,
  });
});

// Info about the logged-in user
api.get('/info', (req, res) => {
  if (waStatus !== 'ready') return res.status(503).json({ ok: false, error: 'Not ready.' });
  res.json({
    ok: true,
    info: client.info || null,
  });
});

// Send a message
api.post('/send', async (req, res) => {
  const { to, message, reply_to } = req.body || {};
  if (!to || !message) return res.status(400).json({ ok: false, error: 'to and message required.' });
  if (waStatus !== 'ready') return res.status(503).json({ ok: false, error: `WhatsApp not ready (status: ${waStatus}).` });

  try {
    let clean = String(to).replace(/\D/g, '');
    let targetChatId = null;

    // Check if sending to self
    if (client.info && client.info.wid) {
      const myNumber = client.info.wid.user;
      if (clean === myNumber || to === client.info.wid._serialized) {
        targetChatId = client.info.wid._serialized;
      }
    }

    if (!targetChatId) {
      if (String(to).endsWith('@g.us')) {
        targetChatId = to;
      } else {
        // Resolve WhatsApp ID
        try {
          const numberId = await client.getNumberId(clean);
          if (numberId) {
            targetChatId = numberId._serialized;
          }
        } catch (_) {}

        if (!targetChatId) {
          targetChatId = clean + '@c.us';
        }
      }
    }

    console.log(`📤 Sending message to ${targetChatId}: ${message.slice(0, 60)}...`);
    const sentMsg = await client.sendMessage(targetChatId, message);
    const msgId = (sentMsg && sentMsg.id && sentMsg.id._serialized) ? sentMsg.id._serialized : 'sent';
    res.json({ ok: true, message_id: msgId, to: targetChatId });
  } catch (err) {
    console.error('Send error:', err);
    res.status(500).json({ ok: false, error: err.message || String(err) });
  }
});

// Get queued incoming messages
api.get('/messages', (req, res) => {
  const limit = Math.min(parseInt(req.query.limit || '50'), MAX_QUEUE);
  res.json({ ok: true, messages: messageQueue.slice(0, limit) });
});

// Clear message queue
api.post('/clear', (req, res) => {
  messageQueue.length = 0;
  res.json({ ok: true });
});

// List contacts
api.get('/contacts', async (req, res) => {
  if (waStatus !== 'ready') return res.status(503).json({ ok: false, error: 'Not ready.' });
  try {
    const contacts = await client.getContacts();
    const list = contacts
      .filter(c => c.isMyContact && c.number)
      .map(c => ({ name: c.pushname || c.name || c.number, number: c.number, id: c.id._serialized }))
      .sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    res.json({ ok: true, contacts: list });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// QR code endpoint (returns QR as JSON for Doshie UI)
api.get('/qr', (req, res) => {
  if (qrCode) return res.json({ ok: true, qr: qrCode, status: waStatus });
  res.json({ ok: false, qr: null, status: waStatus });
});

// Request pairing code with phone number
api.post('/pair', async (req, res) => {
  const { phone } = req.body || {};
  if (!phone) return res.status(400).json({ ok: false, error: 'Phone number is required.' });
  try {
    const cleanNumber = String(phone).replace(/\D/g, '');
    const code = await client.requestPairingCode(cleanNumber);
    console.log(`\n🔑 PAIRING CODE for ${cleanNumber}: ${code}\n`);
    res.json({ ok: true, phone: cleanNumber, code: code });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message || String(err) });
  }
});

api.listen(PORT, '127.0.0.1', () => {
  console.log(`🚀 Doshie WhatsApp Bridge listening on http://127.0.0.1:${PORT}`);
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
console.log('🟡 Starting WhatsApp client...');
client.initialize().catch((err) => {
  console.error('Failed to initialize WhatsApp client:', err);
  process.exit(1);
});

process.on('SIGINT', async () => {
  console.log('\n🛑 Shutting down WhatsApp bridge...');
  await client.destroy();
  process.exit(0);
});
