#!/usr/bin/env python3
"""Doshie Core API bridge for the new command center."""
from flask import Flask, jsonify
from doshie_core import snapshot, ollama_status, gpu_status

app = Flask(__name__)

@app.route("/api/core/status")
def status():
    return jsonify(snapshot())

@app.route("/api/core/models")
def models():
    return jsonify(ollama_status())

@app.route("/api/core/gpu")
def gpu():
    return jsonify({"gpu": gpu_status()})

@app.route("/health")
def health():
    return jsonify({"ok": True, "service": "Doshie Core API"})
