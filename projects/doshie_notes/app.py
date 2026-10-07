#!/usr/bin/env python3
"""Doshie Notes & Files - Local Note-Taking & File Organizer App.
Built autonomously by Doshie & Antigravity.
"""

import os
import sqlite3
import time
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from werkzeug.utils import secure_filename

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "notes.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB file upload limit


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at REAL NOT NULL
            )
        """)


init_db()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Doshie Notes & Files</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090e17;
      --card: #111827;
      --card-hover: #172134;
      --border: #1f293d;
      --accent: #10b981;
      --accent-light: #34d399;
      --accent-glow: rgba(16, 185, 129, 0.2);
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --danger: #ef4444;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Plus Jakarta Sans', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      background: rgba(17, 24, 39, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      padding: 1rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 50;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .brand-icon {
      width: 2.25rem;
      height: 2.25rem;
      background: linear-gradient(135deg, var(--accent), var(--accent-light));
      border-radius: 0.75rem;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.25rem;
      box-shadow: 0 0 15px var(--accent-glow);
    }

    .brand-title {
      font-weight: 700;
      font-size: 1.15rem;
      letter-spacing: -0.01em;
    }

    .brand-subtitle {
      font-size: 0.75rem;
      color: var(--accent-light);
      font-family: 'JetBrains Mono', monospace;
    }

    .controls {
      display: flex;
      gap: 0.75rem;
      align-items: center;
    }

    .search-box {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 0.5rem 0.9rem;
      color: var(--text);
      font-size: 0.875rem;
      outline: none;
      transition: all 0.2s;
      width: 200px;
    }
    .search-box:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-glow);
      width: 260px;
    }

    .btn {
      background: linear-gradient(135deg, var(--accent), #059669);
      color: white;
      border: none;
      padding: 0.5rem 1rem;
      border-radius: 0.75rem;
      font-weight: 600;
      font-size: 0.875rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.2s;
    }
    .btn:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px var(--accent-glow);
    }

    .btn-secondary {
      background: var(--card);
      border: 1px solid var(--border);
      color: var(--text-muted);
    }
    .btn-secondary:hover {
      background: var(--card-hover);
      color: var(--text);
      border-color: var(--accent-light);
    }

    .main-layout {
      display: grid;
      grid-template-columns: 1fr 340px;
      gap: 1.5rem;
      max-width: 1400px;
      margin: 1.5rem auto;
      padding: 0 1.5rem;
      flex: 1;
      width: 100%;
    }

    @media (max-width: 900px) {
      .main-layout { grid-template-columns: 1fr; }
    }

    .notes-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
      align-content: start;
    }

    .note-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 1rem;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      transition: all 0.2s ease;
      cursor: pointer;
      position: relative;
    }
    .note-card:hover {
      border-color: rgba(16, 185, 129, 0.4);
      background: var(--card-hover);
      transform: translateY(-2px);
      box-shadow: 0 8px 20px rgba(0,0,0,0.3);
    }

    .note-title {
      font-weight: 700;
      font-size: 1.05rem;
      color: white;
    }

    .note-body {
      font-size: 0.875rem;
      color: var(--text-muted);
      line-height: 1.5;
      white-space: pre-wrap;
      max-height: 150px;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .note-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: auto;
      padding-top: 0.75rem;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .tag-badge {
      background: rgba(16, 185, 129, 0.15);
      color: var(--accent-light);
      padding: 0.2rem 0.5rem;
      border-radius: 0.5rem;
      font-size: 0.7rem;
      font-weight: 600;
    }

    .files-sidebar {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 1rem;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
      height: fit-content;
      position: sticky;
      top: 5.5rem;
    }

    .sidebar-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .sidebar-title {
      font-weight: 700;
      font-size: 1rem;
    }

    .upload-zone {
      border: 2px dashed var(--border);
      border-radius: 0.75rem;
      padding: 1.5rem;
      text-align: center;
      color: var(--text-muted);
      font-size: 0.85rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .upload-zone:hover {
      border-color: var(--accent);
      background: rgba(16, 185, 129, 0.05);
      color: var(--accent-light);
    }

    .files-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      max-height: 380px;
      overflow-y: auto;
    }

    .file-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.6rem 0.75rem;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border);
      border-radius: 0.6rem;
      font-size: 0.8rem;
    }
    .file-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 180px;
      color: var(--text);
    }

    /* Modal */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.8);
      backdrop-filter: blur(8px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 100;
      padding: 1rem;
    }
    .modal-overlay.open { display: flex; }

    .modal-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 1.25rem;
      width: 100%;
      max-width: 600px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
    }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .input-field, .textarea-field {
      width: 100%;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 0.75rem;
      color: var(--text);
      font-size: 0.95rem;
      outline: none;
      font-family: inherit;
    }
    .input-field:focus, .textarea-field:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-glow);
    }
    .textarea-field { min-height: 180px; resize: vertical; }

    .empty-state {
      text-align: center;
      padding: 4rem 1rem;
      color: var(--text-muted);
      grid-column: 1 / -1;
    }
    .empty-icon { font-size: 3rem; margin-bottom: 0.75rem; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="brand-icon">🦖</div>
      <div>
        <div class="brand-title">Doshie Notes & Files</div>
        <div class="brand-subtitle">Autonomous Local Workspace</div>
      </div>
    </div>
    <div class="controls">
      <input type="text" id="searchInput" class="search-box" placeholder="Search notes & tags..." oninput="filterNotes()">
      <button class="btn" onclick="openNoteModal()">+ New Note</button>
    </div>
  </header>

  <div class="main-layout">
    <div>
      <div id="notesContainer" class="notes-grid">
        <!-- Notes rendered here -->
      </div>
    </div>

    <aside class="files-sidebar">
      <div class="sidebar-header">
        <div class="sidebar-title">📁 File Vault</div>
        <span id="filesCount" style="font-size:0.75rem;color:var(--text-muted);">0 files</span>
      </div>

      <div class="upload-zone" onclick="document.getElementById('fileUploadInput').click()">
        <div>📤 Drop or click to upload file</div>
        <div style="font-size:0.75rem;margin-top:0.35rem;opacity:0.7;">PDF, images, zip, audio up to 50MB</div>
      </div>
      <input type="file" id="fileUploadInput" style="display:none;" onchange="uploadFile(this)">

      <div id="filesList" class="files-list">
        <!-- Files listed here -->
      </div>
    </aside>
  </div>

  <!-- Note Edit/Create Modal -->
  <div id="noteModal" class="modal-overlay">
    <div class="modal-card">
      <div class="modal-header">
        <h3 id="modalTitle" style="font-size:1.1rem;font-weight:700;">Create Note</h3>
        <button class="btn btn-secondary" onclick="closeNoteModal()" style="padding:0.3rem 0.6rem;">✕</button>
      </div>
      <input type="hidden" id="editNoteId">
      <input type="text" id="noteTitleInput" class="input-field" placeholder="Note Title...">
      <input type="text" id="noteTagsInput" class="input-field" placeholder="Tags (comma-separated, e.g. Work, Ideas)">
      <textarea id="noteContentInput" class="textarea-field" placeholder="Write your note in markdown or plain text..."></textarea>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.5rem;">
        <button id="deleteNoteBtn" class="btn btn-secondary" style="color:var(--danger);display:none;" onclick="deleteCurrentNote()">Delete</button>
        <div style="display:flex;gap:0.5rem;margin-left:auto;">
          <button class="btn btn-secondary" onclick="closeNoteModal()">Cancel</button>
          <button class="btn" onclick="saveNote()">Save Note</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    let allNotes = [];

    async function loadNotes() {
      const res = await fetch('/api/notes');
      allNotes = await res.json();
      renderNotes(allNotes);
    }

    async function loadFiles() {
      const res = await fetch('/api/files');
      const files = await res.json();
      document.getElementById('filesCount').innerText = `${files.length} files`;
      const container = document.getElementById('filesList');
      if (files.length === 0) {
        container.innerHTML = '<div style="font-size:0.8rem;color:var(--text-muted);text-align:center;padding:1rem;">No files uploaded yet.</div>';
        return;
      }
      container.innerHTML = files.map(f => `
        <div class="file-item">
          <div class="file-name" title="${f.original_name}">📄 ${f.original_name}</div>
          <div style="display:flex;gap:0.4rem;">
            <a href="/api/files/${f.id}/download" style="color:var(--accent-light);text-decoration:none;font-weight:600;" title="Download">⬇</a>
            <button onclick="deleteFile(${f.id})" style="background:none;border:none;color:var(--danger);cursor:pointer;" title="Delete">✕</button>
          </div>
        </div>
      `).join('');
    }

    function renderNotes(notes) {
      const container = document.getElementById('notesContainer');
      if (!notes || notes.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">📝</div>
            <h3 style="font-size:1.15rem;margin-bottom:0.5rem;">No notes yet</h3>
            <p>Click "+ New Note" above to write your first note or idea!</p>
          </div>
        `;
        return;
      }
      container.innerHTML = notes.map(n => `
        <div class="note-card" onclick="editNote(${n.id})">
          <div class="note-title">${escapeHtml(n.title)}</div>
          <div class="note-body">${escapeHtml(n.content)}</div>
          <div class="note-footer">
            <span>${new Date(n.updated_at * 1000).toLocaleDateString()}</span>
            ${n.tags ? `<span class="tag-badge">${escapeHtml(n.tags)}</span>` : ''}
          </div>
        </div>
      `).join('');
    }

    function filterNotes() {
      const q = document.getElementById('searchInput').value.toLowerCase().trim();
      if (!q) return renderNotes(allNotes);
      const filtered = allNotes.filter(n =>
        n.title.toLowerCase().includes(q) ||
        n.content.toLowerCase().includes(q) ||
        n.tags.toLowerCase().includes(q)
      );
      renderNotes(filtered);
    }

    function openNoteModal() {
      document.getElementById('editNoteId').value = '';
      document.getElementById('noteTitleInput').value = '';
      document.getElementById('noteTagsInput').value = '';
      document.getElementById('noteContentInput').value = '';
      document.getElementById('modalTitle').innerText = 'Create Note';
      document.getElementById('deleteNoteBtn').style.display = 'none';
      document.getElementById('noteModal').classList.add('open');
    }

    function editNote(id) {
      const note = allNotes.find(n => n.id === id);
      if (!note) return;
      document.getElementById('editNoteId').value = note.id;
      document.getElementById('noteTitleInput').value = note.title;
      document.getElementById('noteTagsInput').value = note.tags || '';
      document.getElementById('noteContentInput').value = note.content;
      document.getElementById('modalTitle').innerText = 'Edit Note';
      document.getElementById('deleteNoteBtn').style.display = 'block';
      document.getElementById('noteModal').classList.add('open');
    }

    function closeNoteModal() {
      document.getElementById('noteModal').classList.remove('open');
    }

    async function saveNote() {
      const id = document.getElementById('editNoteId').value;
      const title = document.getElementById('noteTitleInput').value.trim() || 'Untitled Note';
      const tags = document.getElementById('noteTagsInput').value.trim();
      const content = document.getElementById('noteContentInput').value.trim();

      const payload = { title, tags, content };
      if (id) {
        await fetch(`/api/notes/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        await fetch('/api/notes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      closeNoteModal();
      loadNotes();
    }

    async function deleteCurrentNote() {
      const id = document.getElementById('editNoteId').value;
      if (!id || !confirm('Delete this note?')) return;
      await fetch(`/api/notes/${id}`, { method: 'DELETE' });
      closeNoteModal();
      loadNotes();
    }

    async function uploadFile(input) {
      if (!input.files || input.files.length === 0) return;
      const file = input.files[0];
      const formData = new FormData();
      formData.append('file', file);
      await fetch('/api/files/upload', { method: 'POST', body: formData });
      input.value = '';
      loadFiles();
    }

    async function deleteFile(id) {
      if (!confirm('Delete this file?')) return;
      await fetch(`/api/files/${id}`, { method: 'DELETE' });
      loadFiles();
    }

    function escapeHtml(str) {
      return (str || '').replace(/[&<>'"]/g, tag => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
      }[tag] || tag));
    }

    loadNotes();
    loadFiles();
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/notes", methods=["GET"])
def get_notes():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM notes ORDER BY updated_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)


@app.route("/api/notes", methods=["POST"])
def create_note():
    data = request.get_json(force=True, silent=True) or {}
    title = data.get("title", "Untitled Note")
    content = data.get("content", "")
    tags = data.get("tags", "")
    now = time.time()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO notes (title, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (title, content, tags, now, now)
        )
        note_id = cur.lastrowid
        conn.commit()
    return jsonify({"id": note_id, "ok": True}), 201


@app.route("/api/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    data = request.get_json(force=True, silent=True) or {}
    title = data.get("title", "Untitled Note")
    content = data.get("content", "")
    tags = data.get("tags", "")
    now = time.time()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE notes SET title = ?, content = ?, tags = ?, updated_at = ? WHERE id = ?",
            (title, content, tags, now, note_id)
        )
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/files", methods=["GET"])
def get_files():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM files ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)


@app.route("/api/files/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No selected file"}), 400

    orig_name = secure_filename(file.filename) or "uploaded_file"
    stored_name = f"{int(time.time())}_{orig_name}"
    save_path = UPLOADS_DIR / stored_name
    file.save(save_path)
    file_size = os.path.getsize(save_path)

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO files (filename, original_name, size_bytes, created_at) VALUES (?, ?, ?, ?)",
            (stored_name, orig_name, file_size, time.time())
        )
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/files/<int:file_id>/download", methods=["GET"])
def download_file(file_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM files WHERE id = ?", (file_id,))
        row = cur.fetchone()
    if not row:
        return "File not found", 404
    return send_from_directory(
        UPLOADS_DIR,
        row["filename"],
        as_attachment=True,
        download_name=row["original_name"]
    )


@app.route("/api/files/<int:file_id>", methods=["DELETE"])
def delete_file_record(file_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM files WHERE id = ?", (file_id,))
        row = cur.fetchone()
        if row:
            p = UPLOADS_DIR / row["filename"]
            if p.exists():
                p.unlink()
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5088))
    print(f"🚀 Starting Doshie Notes & Files at http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
