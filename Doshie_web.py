from datetime import timedelta
from urllib.parse import urlsplit

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template_string,
    request,
    send_file,
    send_from_directory,
    session,
)
from werkzeug.middleware.proxy_fix import ProxyFix
import errno
import json
import fcntl
import os
import pty
import re
import secrets
import select
import signal
import subprocess
import sys
import threading
import time

sys.path.insert(0, "/data/data/com.termux/files/home/Doshie")
import Doshie_memory
import Doshie_agents
import Doshie_news
import Doshie_profile_avatar
import Doshie_profile_lock
import Doshie_profile_preferences
import Doshie_search
import Doshie_settings
import Doshie_history
import Doshie_health_access
import Doshie_invites
import Doshie_recovery
import Doshie_roles
import Doshie_summary
import Doshie_voice_proxy
import Doshie_spotify
import Doshie_messaging
import Doshie_permissions
import Doshie_equipment_health
import Doshie_chat_attachments
import Doshie_media
from Doshie_router import route_tool

app = Flask(__name__)


@app.after_request
def force_download_headers(response):
    if request.path.startswith('/static/downloads/') and request.path.lower().endswith(('.apk', '.exe')):
        response.headers['Content-Disposition'] = 'attachment; filename="' + os.path.basename(request.path) + '"'
        response.headers['Cache-Control'] = 'no-store'
    return response
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1
)
app.secret_key = Doshie_profile_lock.get_session_secret()
app.config.update(
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,
    SESSION_COOKIE_NAME="Doshie_session",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    TRUSTED_HOSTS=[
        "Doshie-home.duckdns.org",
        "hermes-duran-tecra-a60-m.tail50b4c5.ts.net",
        "127.0.0.1",
        "localhost",
        "100.113.75.55",
    ],
)
app.permanent_session_lifetime = timedelta(hours=8)
INSTANCE_ID = secrets.token_urlsafe(8)

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, interactive-widget=resizes-content">
<meta name="theme-color" content="#5c8f73">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Doshie">
<link rel="manifest" href="/static/manifest.webmanifest">
<link rel="icon" href="/static/Doshie-icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/static/Doshie-192.png">
<link rel="stylesheet" href="/static/Doshie-app.css?v=57">
<title>Doshie</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #101412;
    color: #f1f5f3;
    font-family: Arial, sans-serif;
    height: 100vh;
}

.app {
    max-width: 760px;
    height: 100vh;
    margin: auto;
    display: flex;
    flex-direction: column;
}

.header {
    padding: 18px;
    text-align: center;
    background: #17201c;
    border-bottom: 1px solid #2b3932;
}

.header h1 {
    margin: 0;
    font-size: 24px;
}

.header small {
    color: #9eb2a7;
}

.tools {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding: 10px;
    background: #131a17;
}

.tool {
    border: 1px solid #34473e;
    background: #1d2923;
    color: white;
    padding: 10px 14px;
    border-radius: 18px;
    white-space: nowrap;
    font-size: 14px;
}

#messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
}

.message {
    max-width: 85%;
    padding: 11px 14px;
    margin: 8px 0;
    border-radius: 16px;
    line-height: 1.4;
    white-space: pre-wrap;
}

.user {
    background: #2d493c;
    margin-left: auto;
    border-bottom-right-radius: 5px;
}

.Doshie {
    background: #222b27;
    margin-right: auto;
    border-bottom-left-radius: 5px;
}

.input-area {
    display: flex;
    gap: 8px;
    padding: 12px;
    background: #17201c;
    padding-bottom: max(12px, env(safe-area-inset-bottom));
}

#input {
    flex: 1;
    border: 1px solid #3b4b43;
    border-radius: 22px;
    padding: 12px 16px;
    background: #202824;
    color: white;
    font-size: 16px;
    outline: none;
}

.send {
    border: 0;
    border-radius: 22px;
    padding: 0 18px;
    background: #3c7258;
    color: white;
    font-size: 16px;
}

#status {
    font-size: 12px;
    color: #8fa197;
    padding: 0 16px 6px;
    background: #17201c;
}

/* Modern responsive shell. Existing feature panels and routes stay intact. */
:root {
    color-scheme: light dark;
    --page: #f7f7f5;
    --surface: #ffffff;
    --surface-soft: #f1f1ee;
    --surface-hover: #e9e9e5;
    --text: #202123;
    --muted: #6b6c70;
    --line: #deded9;
    --accent: #5c8f73;
    --accent-strong: #47735c;
    --user: #e3f1e9;
    --shadow: 0 12px 36px rgba(20, 28, 24, .10);
}

@media (prefers-color-scheme: dark) {
    :root {
        --page: #181a19;
        --surface: #212422;
        --surface-soft: #292c2a;
        --surface-hover: #323633;
        --text: #f2f4f2;
        --muted: #a7ada9;
        --line: #3a3e3b;
        --accent: #68a985;
        --accent-strong: #7ab894;
        --user: #294338;
        --shadow: 0 14px 40px rgba(0, 0, 0, .28);
    }
}

html, body { height: 100%; }
body {
    background: var(--page);
    color: var(--text);
    font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    overflow: hidden;
}
button, input, select, textarea { font: inherit; }
button { cursor: pointer; }

.sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 30;
    width: 264px;
    padding: 16px 12px;
    background: var(--surface-soft);
    border-right: 1px solid var(--line);
    display: flex;
    flex-direction: column;
    gap: 14px;
    transition: transform .22s ease;
}
.sidebar-brand { display:flex; align-items:center; gap:10px; padding:6px 8px; font-weight:700; }
.brand-mark { display:grid; place-items:center; width:34px; height:34px; border-radius:10px; background:var(--surface); box-shadow:var(--shadow); }
.sidebar .new-chat { width:100%; padding:11px 12px; border:1px solid var(--line); border-radius:12px; background:var(--surface); color:var(--text); text-align:left; }
.sidebar-label { padding: 0 8px; color:var(--muted); font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:.06em; }
.side-actions { display:grid; gap:4px; overflow:auto; }
.side-action { border:0; border-radius:9px; padding:9px 10px; background:transparent; color:var(--text); text-align:left; }
.side-action:hover, .sidebar .new-chat:hover { background:var(--surface-hover); }
.sidebar-foot { margin-top:auto; padding:10px 8px; color:var(--muted); font-size:12px; }
.mobile-scrim { display:none; position:fixed; inset:0; z-index:25; background:rgba(0,0,0,.42); }

.app {
    max-width: none;
    height: 100dvh;
    margin: 0 0 0 264px;
    background: var(--surface);
    transition: margin .22s ease;
}
.header {
    min-height: 64px;
    padding: 10px 18px;
    background: color-mix(in srgb, var(--surface) 92%, transparent);
    backdrop-filter: blur(14px);
    border-bottom: 1px solid var(--line);
    display:flex;
    align-items:center;
    gap:12px;
    text-align:left;
}
.header h1 { font-size:16px; font-weight:650; flex:1; }
.header small { color:var(--muted); font-size:12px; }
.menu-button { display:none; width:38px; height:38px; border:0; border-radius:10px; background:transparent; color:var(--text); font-size:20px; }
.menu-button:hover { background:var(--surface-soft); }

#dashboard {
    padding: 9px 20px !important;
    background: var(--surface) !important;
    border-bottom: 1px solid var(--line) !important;
    color: var(--muted);
    text-align:center;
}
.tools {
    gap: 7px;
    padding: 9px max(16px, calc((100% - 820px) / 2));
    background: var(--surface);
    border-bottom: 1px solid var(--line);
    scrollbar-width:none;
}
.tools::-webkit-scrollbar { display:none; }
.tool {
    border: 1px solid var(--line);
    background: var(--surface-soft);
    color: var(--text);
    padding: 8px 12px;
    border-radius: 999px;
    font-size: 13px;
    transition: background .15s, transform .15s;
}
.tool:hover { background:var(--surface-hover); transform:translateY(-1px); }

#messages {
    padding: 28px max(20px, calc((100% - 820px) / 2)) 150px;
    scroll-behavior:smooth;
}
.message {
    width: fit-content;
    max-width: min(78%, 700px);
    padding: 13px 16px;
    margin: 12px 0;
    border-radius: 18px;
    line-height: 1.55;
    font-size: 15px;
    box-shadow: 0 1px 1px rgba(0,0,0,.03);
}
.user { background:var(--user); border-bottom-right-radius:5px; }
.Doshie { background:var(--surface-soft); border:1px solid var(--line); border-bottom-left-radius:5px; }
#status { position:absolute; left:calc(264px + max(20px, (100% - 264px - 820px)/2)); bottom:104px; z-index:4; padding:0; background:transparent; color:var(--muted); }
.input-area {
    position:absolute;
    z-index:5;
    left:calc(264px + max(16px, (100% - 264px - 820px)/2));
    right:max(16px, calc((100% - 264px - 820px)/2));
    bottom:max(18px, env(safe-area-inset-bottom));
    padding:9px;
    background:var(--surface);
    border:1px solid var(--line);
    border-radius:24px;
    box-shadow:var(--shadow);
}
#input { border:0; background:transparent; color:var(--text); padding:10px 12px; }
#input::placeholder { color:var(--muted); }
.send { min-width:72px; min-height:42px; padding:0 16px; border-radius:16px; background:var(--accent); font-weight:650; }
.send:hover { background:var(--accent-strong); }

.app > [id$="Panel"] {
    position:absolute;
    z-index:15;
    top:76px;
    bottom:92px;
    left:calc(264px + max(16px, (100% - 264px - 900px)/2));
    right:max(16px, calc((100% - 264px - 900px)/2));
    overflow:auto;
    padding:22px !important;
    background:var(--surface) !important;
    border:1px solid var(--line) !important;
    border-radius:18px;
    box-shadow:var(--shadow);
}
.app > [id$="Panel"] input, .app > [id$="Panel"] textarea, .app > [id$="Panel"] select,
.app > div:not(.header):not(.tools):not(#messages):not(.input-area) input,
.app > div:not(.header):not(.tools):not(#messages):not(.input-area) textarea,
.app > div:not(.header):not(.tools):not(#messages):not(.input-area) select {
    border:1px solid var(--line); border-radius:9px; background:var(--surface-soft); color:var(--text);
}

@media (max-width: 800px) {
    .sidebar { transform:translateX(-100%); box-shadow:var(--shadow); }
    body.sidebar-open .sidebar { transform:translateX(0); }
    body.sidebar-open .mobile-scrim { display:block; }
    .app { margin-left:0; }
    .menu-button { display:inline-grid; place-items:center; }
    .header { padding-inline:12px; }
    .header small { max-width:145px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    #messages { padding:20px 14px 140px; }
    .message { max-width:88%; }
    #status { left:20px; bottom:96px; }
    .input-area { left:10px; right:10px; bottom:max(10px, env(safe-area-inset-bottom)); }
    .app > [id$="Panel"] { left:10px; right:10px; top:70px; bottom:84px; padding:16px !important; }
    #dashboard { text-align:left; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
}

.credential-field { display:flex; align-items:center; gap:6px; width:100%; }
.credential-field input { flex:1; min-width:0; }
.credential-field button { width:44px; min-width:44px; height:44px; padding:0; border:1px solid var(--line); border-radius:10px; background:var(--surface-soft); color:var(--text); }

.thinking-buddy {
    position:absolute;
    z-index:7;
    left:20px;
    top:-42px;
    height:42px;
    display:flex;
    align-items:flex-end;
    gap:5px;
    padding:0 7px 0 0;
    border:0;
    background:transparent;
    color:var(--muted);
    font-size:11px;
    transform:translateY(1px);
}
.thinking-buddy img {
    width:40px;
    height:40px;
    object-fit:cover;
    border-radius:13px;
    filter:drop-shadow(0 4px 4px rgba(0,0,0,.35));
    transform-origin:center bottom;
}
.thinking-buddy span { padding-bottom:4px; }
.thinking-buddy.thinking img { animation:buddy-think .55s ease-in-out infinite alternate; }
.thinking-buddy.happy img { animation:buddy-happy .38s ease-in-out 3 alternate; }
@keyframes buddy-think { to { transform:translateY(-6px) rotate(3deg); } }
@keyframes buddy-happy { to { transform:translateY(-8px) rotate(-5deg); } }

.child-mode .sidebar,
.child-mode .tools,
.child-mode #dashboard,
.child-mode .display-controls,
.child-mode .install-app,
.child-mode #profileSwitcher,
.child-mode .settings-header-button,
.child-mode .builder-side-action,
.child-mode .builder-launch { display:none !important; }
.child-mode .app { margin-left:0 !important; }
.child-mode .menu-button { display:none !important; }
.child-mode .header { justify-content:center; }
.child-mode .header h1 { flex:0 1 auto; }
.child-mode .mobile-nav button:not([data-app-view="chat"]):not(#voiceDockButton) {
    display:none !important;
}
.child-mode .mobile-nav { justify-content:center; gap:26px; }

@media (max-width:800px) {
    .header {
        min-height:calc(64px + env(safe-area-inset-top));
        padding-top:max(10px,env(safe-area-inset-top));
        padding-left:max(12px,env(safe-area-inset-left));
        padding-right:max(12px,env(safe-area-inset-right));
        gap:7px;
    }
    .header .display-control span { display:none; }
    .header .display-control { width:36px; min-width:36px; padding:0; }
    #messages { padding-bottom:calc(158px + env(safe-area-inset-bottom)); }
    .message { max-width:min(92%,680px); overflow-wrap:anywhere; }
    .input-area {
        left:max(8px,env(safe-area-inset-left));
        right:max(8px,env(safe-area-inset-right));
        bottom:max(10px,env(safe-area-inset-bottom));
    }
}
@media (max-width:520px) {
    .header .display-controls { display:none; }
    .header h1 { font-size:15px; }
    .header small { max-width:92px; }
    .message { max-width:95%; }
    .thinking-buddy { left:14px; }
}
@media (prefers-reduced-motion:reduce) {
    .thinking-buddy img { animation:none !important; }
}
</style>
</head>

<body>

<div id="splash" class="app-launch-splash" aria-live="polite">
    <div class="splash-card">
        <div class="splash-mark">🦖</div>
        <strong>Doshie</strong>
        <span id="splashText">Connecting to your private assistant...</span>
    </div>
</div>

<section id="accountChooser" class="account-chooser" hidden
         aria-labelledby="accountChooserTitle">
    <div class="account-chooser-card">
        <div class="account-chooser-brand">🦖</div>
        <h1 id="accountChooserTitle">Who’s using Doshie?</h1>
        <p>Choose your private account to continue.</p>
        <div id="accountGrid" class="account-grid"></div>
        <form id="publicSignInPanel" class="invite-access-panel"
              onsubmit="signInPublicAccount(event)" hidden>
            <strong>Family sign in</strong>
            <p>Enter your Doshie username and private password or PIN.</p>
            <input id="publicSignInUsername" type="text"
                   name="Doshie-login-name" autocomplete="new-password" autocapitalize="none"
                   placeholder="Username" maxlength="80" required>
            <input id="publicSignInCredential" type="password"
                   autocomplete="current-password"
                   placeholder="Password or PIN" maxlength="64" required>
            <button type="submit" class="tool">Sign in</button>
            <div id="publicSignInStatus" role="status"></div>
        </form>
        <form id="inviteAccessPanel" class="invite-access-panel"
              onsubmit="claimFamilyInvite(event)" hidden>
            <strong>Have an invitation?</strong>
            <p>Enter the private invitation code sent by Hermes or Aeriel.</p>
            <input id="familyInviteToken" type="password"
                   autocomplete="one-time-code"
                   placeholder="Invitation code" required>
            <button type="submit" class="tool">Use invitation</button>
            <div id="familyInviteClaimStatus" role="status"></div>
        </form>
        <small>Accounts, chats, and photos stay private on this TECRA.</small>
    </div>
</section>

<aside class="sidebar" aria-label="Doshie navigation">
    <div class="sidebar-brand">
        <span class="brand-mark">🦖</span><span class="side-text">Doshie</span>
    </div>
    <button class="new-chat" onclick="newChat(); closeSidebar()">
        <span class="side-icon">＋</span><span class="side-text">New chat</span>
    </button>
    <button class="new-chat install-app" data-install-app hidden
            onclick="installDoshieApp()">
        <span class="side-icon">⬇</span><span class="side-text">Install app</span>
    </button>
    <div class="sidebar-label side-text">Spaces</div>
    <nav class="side-actions">
        <button class="side-action active" data-side-view="chat"
                onclick="openChatSpace('main'); closeSidebar()">
            <span class="side-icon">💬</span><span class="side-text">Chat</span>
        </button>
        <button id="hermesWorkspaceButton" class="side-action" hidden
                onclick="openHermesWorkspace(); closeSidebar()">
            <span class="side-icon">🧠</span><span class="side-text">Hermes AI</span>
        </button>
        <button class="side-action" data-side-view="mansion"
                onclick="openChatSpace('mansion'); closeSidebar()">
            <span class="side-icon">🏰</span><span class="side-text">Mansion Doshie</span>
        </button>
        <button class="side-action" data-side-view="search"
                onclick="openSearchHub(); closeSidebar()">
            <span class="side-icon">🔎</span><span class="side-text">Search Hub</span>
        </button>
        <button class="side-action" data-side-view="watch"
                onclick="openWatchMode(); closeSidebar()">
            <span class="side-icon">⌚</span><span class="side-text">Watch</span>
        </button>
        <button class="side-action" data-side-view="family"
                onclick="openAppView('family'); closeSidebar()">
            <span class="side-icon">👥</span><span class="side-text">Peer Chat</span>
        </button>
        <button class="side-action" onclick="openTechDashboard(); closeSidebar()">
            <span class="side-icon">💻</span><span class="side-text">Technology</span>
        </button>
        <button class="side-action" onclick="openAiTutorial(); closeSidebar()">
            <span class="side-icon">📘</span><span class="side-text">AI Tutorial</span>
        </button>
        <button class="side-action builder-side-action" onclick="openBuilderPanel(); closeSidebar()">
            <span class="side-icon">🧩</span><span class="side-text">Build an app</span>
        </button>
        <button class="side-action" onclick="quick('Open Media Studio. I want to generate an AI picture or video.'); closeSidebar()">
            <span class="side-icon">✦</span><span class="side-text">Media Studio</span>
        </button>
        <button class="side-action" onclick="quick('Open the AI Growth Core dashboard and show shared memory, model routing, tools, and approval permissions.'); closeSidebar()">
            <span class="side-icon">◎</span><span class="side-text">Growth Core</span>
        </button>
        <button class="side-action" onclick="openGamingDashboard(); closeSidebar()">
            <span class="side-icon">🎮</span><span class="side-text">Gaming</span>
        </button>
        <button class="side-action" onclick="openSpotify(); closeSidebar()">
            <span class="side-icon">🎵</span><span class="side-text">Spotify</span>
        </button>
        <button class="side-action" onclick="focusNewsBanner(); closeSidebar()">
            <span class="side-icon">📰</span><span class="side-text">News</span>
        </button>
        <button id="adminControlButton" class="side-action" hidden
                onclick="openAdminControl(); closeSidebar()">
            <span class="side-icon">🛡️</span><span class="side-text">Admin Control</span>
        </button>
        <button class="side-action" onclick="openProfileCustomizer(); closeSidebar()">
            <span class="side-icon">🎨</span><span class="side-text">Customize</span>
        </button>
        <button class="side-action" onclick="toggleSettings(); closeSidebar()">
            <span class="side-icon">⚙️</span><span class="side-text">Settings</span>
        </button>
        <button class="side-action" onclick="quick('Weather'); closeSidebar()">
            <span class="side-icon">🌦️</span><span class="side-text">Weather</span>
        </button>
        <button class="side-action" onclick="signOutProfile()">
            <span class="side-icon">👥</span><span class="side-text">Switch account</span>
        </button>
    </nav>
    <div class="sidebar-foot side-text">Private · Runs on your TECRA</div>
</aside>
<div class="mobile-scrim" onclick="closeSidebar()"></div>

<div class="app">

    <section id="newsBanner" class="news-banner" aria-label="News updates">
        <button id="newsTopicButton" class="news-topic" data-short-label="EL PASO"
                onclick="cycleNewsTopic()" aria-label="Change news topic">
            LOCAL · EL PASO
        </button>
        <div id="newsMarquee" class="news-marquee">
            <div id="newsTrack" class="news-marquee-track">
                <a id="newsHeadline" class="news-headline" href="#"
                   target="_blank" rel="noopener noreferrer">
                    Loading local news…
                </a>
                <span class="news-separator" aria-hidden="true">•</span>
                <span id="newsSource" class="news-source"></span>
            </div>
        </div>
        <button class="news-control" onclick="stepNews(-1)"
                aria-label="Previous headline">‹</button>
        <button id="newsPauseButton" class="news-control"
                onclick="toggleNewsPause()" aria-label="Pause headlines">Ⅱ</button>
        <button class="news-control" onclick="stepNews(1)"
                aria-label="Next headline">›</button>
        <button class="news-control news-refresh" onclick="loadNews(true)"
                aria-label="Refresh news">↻</button>
    </section>

    <div class="header">
        <button id="sidebarToggle" class="menu-button" onclick="toggleSidebar()"
            aria-label="Collapse sidebar" title="Collapse sidebar">☰</button>
        <h1 id="appRoomTitle">🦖 Doshie</h1>
        <div class="display-controls">
            <button id="phonePreviewButton"
                    class="display-control"
                    onclick="togglePhonePreview()"
                    aria-label="Toggle phone preview"
                    title="Phone preview">📱</button>
            <button id="fullscreenButton"
                    class="display-control"
                    onclick="toggleDoshieFullscreen()"
                    aria-label="Toggle fullscreen"
                    title="Fullscreen">⛶</button>
            <button id="designControlButton"
                    class="display-control design-control-button"
                    onclick="openProfileCustomizer()"
                    aria-label="Open full app and website design control"
                    title="Full design control">🎛️<span>Control</span></button>
            <button id="settingsHeaderButton"
                    class="display-control settings-header-button"
                    onclick="toggleSettings()"
                    aria-label="Open settings"
                    title="Settings">⚙️<span>Settings</span></button>
        </div>
        <button class="install-app"
                data-install-app
                hidden
                onclick="installDoshieApp()">Install</button>
        <label id="profileSwitcher" class="profile-chip" title="Administrator profile switcher">
            <span class="profile-mini-avatar" aria-hidden="true">
                <img id="activeProfileAvatar" alt="" hidden>
                <span id="activeProfileInitials">H</span>
            </span>
            <select id="activeProfile"
                    aria-label="Who is talking"
                    onchange="switchProfile()">
                <option value="Hermes">Hermes</option>
            </select>
        </label>
        <small id="connectionStatus">🟡 Doshie is waking up...</small>
    </div>

    <div id="dashboard" style="
        padding:10px 14px;
        background:#131a17;
        border-bottom:1px solid #2b3932;
        font-size:13px;
        line-height:1.6;
    ">
        Loading Doshie status...
    </div>

    <div class="tools">
        <button class="tool" onclick="quick('Weather')">🌦️ Weather</button>
        <button class="tool" onclick="quick('/battery')">🔋 Battery</button>
        <button class="tool" onclick="quick('/status')">📱 Status</button>
        <button class="tool" onclick="quick('/memories')">🧠 Memories</button>
        <button class="tool" onclick="enableMicrophone()">🎙️ Voice</button>
        <button class="tool" onclick="openFamily()">👨‍👩‍👧‍👦 Family</button>
        <button class="tool" onclick="openFamilyDashboard()">🏠 Family Dashboard</button>
        <button class="tool" onclick="openShopping()">🛒 Shopping</button>
        <button class="tool" onclick="openReminders()">⏰ Reminders</button>
        <button class="tool" onclick="createBackup()">💾 Backup</button>
        <button class="tool" onclick="openOrganizer()">📝 Organizer</button>
        <button class="tool" onclick="openTechDashboard()">💻 Tech</button>
        <button class="tool" onclick="openAiTutorial()">📘 AI Tutorial</button>
        <button class="tool builder-launch" onclick="openBuilderPanel()">🧩 Build an app</button>
        <button class="tool" onclick="quick('Open Media Studio. I want to generate an AI picture or video.')">✦ Media Studio</button>
        <button class="tool" onclick="quick('Open the AI Growth Core dashboard and show shared memory, model routing, tools, and approval permissions.')">◎ Growth Core</button>
        <button class="tool" onclick="openGamingDashboard()">🎮 Gaming</button>
        <button class="tool" onclick="toggleSettings()">⚙️ Settings</button>
        <button class="tool" onclick="newChat()">➕ New Chat</button>
        <button class="tool" onclick="clearChat()">🗑️ Clear Chat</button>
    </div>

    <div id="gamingPanel" style="
        display:none;
        padding:14px;
        background:#17201c;
        border-bottom:1px solid #2b3932;
    ">
        <h3 style="margin-top:0;">🎮 Doshie Gaming</h3>

        <div id="gamingDashboardContent">
            Loading gaming status...
        </div>

        <div style="
            margin-top:12px;
            display:flex;
            flex-wrap:wrap;
            gap:8px;
        ">
            <button class="tool"
                    onclick="quick('Help me optimize my gaming settings')">
                ⚡ Optimize
            </button>

            <button class="tool"
                    onclick="quick('Check my gaming performance')">
                📊 Performance
            </button>

            <button class="tool"
                    onclick="quick('Help me troubleshoot gaming hardware')">
                🛠️ Hardware
            </button>

            <button class="tool"
                    onclick="openGamingDashboard()">
                🔄 Refresh
            </button>

            <button class="tool"
                    onclick="closeGamingDashboard()">
                Close
            </button>
        </div>
    </div>

    <div id="aiTutorialPanel" style="
        display:none;
        padding:14px;
        background:#17201c;
        border-bottom:1px solid #2b3932;
    ">
        <div class="panel-heading">
            <strong>📘 Doshie Mini AI Tutorial</strong>
            <button type="button" class="panel-close"
                    onclick="closeAiTutorial()" aria-label="Close tutorial">✕</button>
        </div>
        <div style="color:var(--muted);margin:4px 0 12px;">
            Five tiny lessons. Learn one idea, try it immediately, keep moving.
        </div>
        <div id="aiTutorialProgress" style="font-size:13px;margin-bottom:8px;"></div>
        <div style="height:6px;background:#202824;border-radius:999px;overflow:hidden;margin-bottom:14px;">
            <div id="aiTutorialProgressBar" style="height:100%;width:20%;background:var(--accent,#6ad39a);"></div>
        </div>
        <div id="aiTutorialLesson" style="padding:14px;background:#202824;border-radius:12px;line-height:1.55;"></div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;">
            <button class="tool" onclick="aiTutorialPrevious()">← Previous</button>
            <button class="tool" onclick="aiTutorialTry()">🧪 Try this</button>
            <button class="tool" onclick="aiTutorialNext()">Next →</button>
            <button class="tool" onclick="aiTutorialReset()">↺ Reset</button>
        </div>
    </div>

    <div id="techPanel" style="
        display:none;
        padding:14px;
        background:#17201c;
        border-bottom:1px solid #2b3932;
    ">
        <h3 style="margin-top:0;">💻 Doshie Tech</h3>

        <div id="techDashboardContent">
            Loading tech status...
        </div>

        <button class="tool"
                style="margin-top:10px;"
                onclick="openTechDashboard()">
            🔄 Refresh
        </button>

        <button class="tool"
                style="margin-top:10px;"
                onclick="closeTechDashboard()">
            Close
        </button>
    </div>

    <div id="hermesPanel" class="hermes-workspace" style="display:none;">
        <div class="panel-heading">
            <div>
                <strong>🧠 Hermes AI</strong>
                <small>Your portable technical partner · administrator only</small>
            </div>
            <button type="button" class="panel-close"
                    onclick="closeHermesWorkspace()" aria-label="Close Hermes AI">✕</button>
        </div>
        <div id="hermesMessages" class="hermes-messages" aria-live="polite">
            <div class="hermes-empty">Opening your private Hermes workspace…</div>
        </div>
        <div id="hermesStatus" class="hermes-status" aria-live="polite"></div>
        <form class="hermes-composer" onsubmit="sendHermesMessage(event)">
            <button type="button" class="tool" onclick="startHermesVoice()"
                    aria-label="Talk to Hermes">🎙️</button>
            <textarea id="hermesInput" rows="2" maxlength="4000"
                      placeholder="Ask Hermes to inspect, explain, plan, or propose a change…"></textarea>
            <button type="submit" class="send">Send</button>
            <button type="button" class="tool" onclick="clearHermesHistory()">Clear</button>
        </form>
        <small class="permission-note">
            Hermes may inspect and advise. File or AI changes still follow your approval policy.
        </small>
    </div>

    <script>
    function hermesMessage(role, content) {
        const item = document.createElement("div");
        item.className = "hermes-message " + (role === "user" ? "user" : "assistant");
        const label = document.createElement("small");
        label.textContent = role === "user" ? activeProfile : "Hermes AI";
        const body = document.createElement("div");
        body.textContent = content;
        item.append(label, body);
        return item;
    }

    function renderHermesHistory(messages) {
        const list = document.getElementById("hermesMessages");
        list.replaceChildren();
        if (!messages.length) {
            const empty = document.createElement("div");
            empty.className = "hermes-empty";
            empty.textContent = "Hermes is ready. Ask for help with Doshie, coding, equipment, or planning.";
            list.append(empty);
            return;
        }
        messages.forEach(message => {
            list.append(hermesMessage(message.role, message.content));
        });
        list.scrollTop = list.scrollHeight;
    }

    async function hermesApi(path, options = {}) {
        const config = Object.assign({}, options);
        config.headers = Object.assign(
            {"Content-Type": "application/json"},
            options.headers || {}
        );
        const response = await fetch(path, config);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Hermes AI is unavailable.");
        return data;
    }

    async function loadHermesHistory() {
        const status = document.getElementById("hermesStatus");
        try {
            const data = await hermesApi(
                "/hermes-ai/history?profile=" + encodeURIComponent(activeProfile)
            );
            renderHermesHistory(data.messages || []);
            status.textContent = "";
        } catch (error) {
            status.textContent = error.message;
        }
    }

    function openHermesWorkspace() {
        const record = typeof profileRecord === "function"
            ? profileRecord(activeProfile) : null;
        if (!record || !record.is_admin) {
            statusBox.textContent = "Administrator access is required for Hermes AI.";
            return;
        }
        if (window.showChatHome) window.showChatHome();
        const panel = document.getElementById("hermesPanel");
        panel.style.display = "flex";
        closeSidebar();
        loadHermesHistory();
        document.getElementById("hermesInput").focus({preventScroll: true});
    }

    function closeHermesWorkspace() {
        document.getElementById("hermesPanel").style.display = "none";
        if (window.showChatHome) window.showChatHome();
    }

    async function sendHermesMessage(event) {
        event.preventDefault();
        const input = document.getElementById("hermesInput");
        const status = document.getElementById("hermesStatus");
        const message = input.value.trim();
        if (!message) return;
        const list = document.getElementById("hermesMessages");
        const empty = list.querySelector(".hermes-empty");
        if (empty) empty.remove();
        list.append(hermesMessage("user", message));
        list.scrollTop = list.scrollHeight;
        input.value = "";
        status.textContent = "Hermes is thinking…";
        try {
            const data = await hermesApi("/hermes-ai/chat", {
                method: "POST",
                body: JSON.stringify({profile: activeProfile, message})
            });
            list.append(hermesMessage("assistant", data.reply));
            list.scrollTop = list.scrollHeight;
            status.textContent = "";
            if (DoshieSettings.speak_replies && typeof speakDoshieReply === "function") {
                speakDoshieReply(data.reply);
            }
        } catch (error) {
            status.textContent = error.message;
        }
    }

    async function clearHermesHistory() {
        const status = document.getElementById("hermesStatus");
        try {
            await hermesApi("/hermes-ai/history", {
                method: "DELETE",
                body: JSON.stringify({profile: activeProfile})
            });
            renderHermesHistory([]);
            status.textContent = "Hermes history cleared.";
        } catch (error) {
            status.textContent = error.message;
        }
    }

    function DoshieNativeSpeechPlugin() {
        const capacitor = window.Capacitor;
        if (!capacitor) return null;
        if (capacitor.Plugins?.DoshieSpeech) {
            return capacitor.Plugins.DoshieSpeech;
        }
        return typeof capacitor.registerPlugin === "function"
            ? capacitor.registerPlugin("DoshieSpeech")
            : null;
    }

    async function startHermesVoice() {
        const status = document.getElementById("hermesStatus");
        const nativeSpeech = DoshieNativeSpeechPlugin();
        if (nativeSpeech) {
            status.textContent = "Listening through Android…";
            try {
                const result = await nativeSpeech.startListening({
                    language: navigator.language || "en-US"
                });
                document.getElementById("hermesInput").value =
                    String(result?.text || "").trim();
                status.textContent = "Voice captured. Tap Send when ready.";
            } catch (error) {
                status.textContent = String(
                    error?.message || error || "Hermes could not hear that clearly."
                );
            }
            return;
        }
        const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!Recognition) {
            status.textContent = "Voice input is unavailable on this device.";
            return;
        }
        const recognition = new Recognition();
        recognition.lang = navigator.language || "en-US";
        recognition.interimResults = false;
        status.textContent = "Listening…";
        recognition.onresult = event => {
            document.getElementById("hermesInput").value =
                event.results[0][0].transcript;
            status.textContent = "Voice captured. Tap Send when ready.";
        };
        recognition.onerror = () => {
            status.textContent = "Hermes could not hear that clearly.";
        };
        recognition.start();
    }
    </script>

    <div id="builderPanel" class="builder-panel" style="display:none;">
        <div class="panel-heading">
            <strong>🧩 Build with Doshie</strong>
            <button type="button" class="panel-close" onclick="closeBuilderPanel()">✕</button>
        </div>
        <p class="builder-subtitle">Describe an app or code change. Doshie will plan it, show the files it wants to change, test the result, and wait for your approval.</p>
        <label class="settings-field" for="builderGoal">
            <span>What should Doshie build?</span>
            <textarea id="builderGoal" rows="4" maxlength="4000" placeholder="Example: Build a family messenger with dark-red MySpace styling and a collapsible mobile chat bar."></textarea>
        </label>
        <div class="builder-options">
            <label><input type="checkbox" id="builderPreview" checked> Show a live preview</label>
            <label><input type="checkbox" id="builderTests" checked> Run tests and repair errors</label>
            <label><input type="checkbox" id="builderBackup" checked> Create a backup first</label>
        </div>
        <div class="admin-actions">
            <button class="tool" type="button" onclick="sendBuilderRequest()">Start build conversation</button>
            <button class="tool" type="button" onclick="closeBuilderPanel()">Close</button>
        </div>
        <small class="permission-note">Approval lock: Doshie proposes changes first. Nothing is written, installed, or restarted without your approval.</small>
        <div class="permission-queue-head">
            <strong>Admin approval queue</strong>
            <div class="admin-actions">
                <button class="tool" type="button" onclick="requestRegressionCheck()">Request full test</button>
                <button class="tool" type="button" onclick="loadPermissionRequests()">Refresh</button>
            </div>
        </div>
        <div id="permissionRequestList" class="permission-request-list">No requests yet.</div>
        <div id="permissionRequestStatus" class="permission-request-status" aria-live="polite"></div>
    </div>
    <script>
    function openBuilderPanel() {
        const record = typeof profileRecord === "function" ? profileRecord(activeProfile) : null;
        if (!record || !record.is_admin) {
            statusBox.textContent = "Administrator access is required for Build with Doshie.";
            return;
        }
        const panel = document.getElementById("builderPanel");
        if (panel) panel.style.display = "block";
        loadPermissionRequests();
        const goal = document.getElementById("builderGoal");
        if (goal) goal.focus();
    }
    function closeBuilderPanel() {
        const panel = document.getElementById("builderPanel");
        if (panel) panel.style.display = "none";
    }
    function sendBuilderRequest() {
        const goal = (document.getElementById("builderGoal")?.value || "").trim();
        if (!goal) { document.getElementById("builderGoal")?.focus(); return; }
        const preview = document.getElementById("builderPreview")?.checked;
        const tests = document.getElementById("builderTests")?.checked;
        const backup = document.getElementById("builderBackup")?.checked;
        const request = "[CODING BUILDER MODE] " + goal +
            "\\n\\nWork in approval stages. " +
            (backup ? "Create a backup proposal first. " : "") +
            "Inspect approved source files, then use propose_code_edit to place every exact change in my admin approval queue. Never claim a proposal was applied. " +
            (tests ? "Run tests and repair failures. " : "") +
            (preview ? "Open or describe a live preview when ready. " : "") +
            "Do not use root, delete files, install packages, or restart services without my approval.";
        closeBuilderPanel();
        if (typeof quick === "function") quick(request);
        else {
            const input = document.getElementById("messageInput") || document.querySelector("#input");
            if (input) { input.value = request; input.focus(); }
        }
    }

    async function permissionApi(path, options = {}) {
        const config = Object.assign({}, options);
        config.headers = Object.assign(
            {"Content-Type": "application/json"},
            options.headers || {}
        );
        const response = await fetch(path, config);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Approval request failed.");
        return data;
    }

    function permissionActionButton(label, handler) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "tool";
        button.textContent = label;
        button.addEventListener("click", handler);
        return button;
    }

    function renderPermissionRequests(records) {
        const list = document.getElementById("permissionRequestList");
        list.replaceChildren();
        if (!records.length) {
            list.textContent = "No approval requests yet.";
            return;
        }
        records.forEach(record => {
            const card = document.createElement("article");
            card.className = "permission-request-card";
            const heading = document.createElement("strong");
            heading.textContent = record.summary || record.action;
            const meta = document.createElement("small");
            meta.textContent = [
                record.status,
                record.requested_by,
                record.target
            ].filter(Boolean).join(" · ");
            card.append(heading, meta);
            if (record.action === "exact_replace") {
                const details = document.createElement("details");
                const summary = document.createElement("summary");
                summary.textContent = "Review exact change";
                const code = document.createElement("pre");
                code.textContent =
                    "CURRENT\\n" + (record.old_text || "") +
                    "\\n\\nPROPOSED\\n" + (record.new_text || "");
                details.append(summary, code);
                card.append(details);
            }
            const actions = document.createElement("div");
            actions.className = "admin-actions";
            if (record.status === "pending") {
                actions.append(
                    permissionActionButton("Approve", () => reviewPermissionRequest(record.id, "approve")),
                    permissionActionButton("Reject", () => reviewPermissionRequest(record.id, "reject"))
                );
            }
            if (record.status === "completed" && record.backup) {
                actions.append(
                    permissionActionButton("Rollback", () => rollbackPermissionRequest(record.id))
                );
            }
            card.append(actions);
            list.append(card);
        });
    }

    async function loadPermissionRequests() {
        const status = document.getElementById("permissionRequestStatus");
        try {
            const data = await permissionApi(
                "/permission-requests?profile=" + encodeURIComponent(activeProfile)
            );
            renderPermissionRequests(data.requests || []);
            status.textContent = "";
        } catch (error) {
            status.textContent = error.message;
        }
    }

    async function reviewPermissionRequest(id, decision) {
        const status = document.getElementById("permissionRequestStatus");
        status.textContent = decision === "approve" ? "Verifying approved action..." : "Rejecting request...";
        try {
            const data = await permissionApi(
                "/permission-requests/" + encodeURIComponent(id) + "/review",
                {method: "POST", body: JSON.stringify({profile: activeProfile, decision})}
            );
            status.textContent = "Request " + data.request.status + ".";
            await loadPermissionRequests();
        } catch (error) {
            status.textContent = error.message;
        }
    }

    async function rollbackPermissionRequest(id) {
        const status = document.getElementById("permissionRequestStatus");
        status.textContent = "Restoring the verified backup...";
        try {
            await permissionApi(
                "/permission-requests/" + encodeURIComponent(id) + "/rollback",
                {method: "POST", body: JSON.stringify({profile: activeProfile})}
            );
            status.textContent = "Rollback completed.";
            await loadPermissionRequests();
        } catch (error) {
            status.textContent = error.message;
        }
    }

    async function requestRegressionCheck() {
        const status = document.getElementById("permissionRequestStatus");
        try {
            await permissionApi(
                "/permission-requests/regression",
                {method: "POST", body: JSON.stringify({profile: activeProfile})}
            );
            status.textContent = "Regression check added for approval.";
            await loadPermissionRequests();
        } catch (error) {
            status.textContent = error.message;
        }
    }
    </script>

    <div id="adminPanel" style="display:none;">
        <div class="panel-heading">
            <strong>🛡️ Doshie Admin Control Center</strong>
            <button type="button" class="panel-close" onclick="closeAdminControl()">✕</button>
        </div>
        <div class="admin-control-grid">
            <section class="admin-card admin-card-wide">
                <small>LIVE STATUS</small>
                <h2>Doshie command center</h2>
                <p id="adminControlSummary">Checking Doshie...</p>
                <button class="tool" onclick="refreshAdminControl()">Refresh status</button>
            </section>
            <section class="admin-card">
                <small>REPLY SPEED</small>
                <strong id="adminReplySpeed">No messages measured yet</strong>
                <span id="adminReplyDetail">Send a message to begin measuring.</span>
            </section>
            <section class="admin-card">
                <small>AI MODEL</small>
                <strong id="adminModelName">Checking...</strong>
                <span id="adminModelDetail">Local model health</span>
            </section>
            <section class="admin-card admin-card-wide">
                <label class="settings-field" for="adminBrainMode">
                    <span>Default brain for this device</span>
                    <select id="adminBrainMode" onchange="setAdminBrainMode()">
                        <option value="auto">Auto router</option>
                        <option value="fast">Fast</option>
                        <option value="balanced">Balanced</option>
                        <option value="coding">Coding</option>
                        <option value="advanced">Advanced</option>
                        <option value="vision" data-admin-only="true">Vision</option>
                    </select>
                </label>
                <small>Fast is best for everyday replies. Advanced is slower.</small>
            </section>
            <section class="admin-card admin-card-wide">
                <small>SYSTEM CHECKS</small>
                <div id="adminHealthChecks" class="admin-health-list">Loading checks...</div>
            </section>
            <section class="admin-card admin-card-wide">
                <small>EQUIPMENT HEALTH</small>
                <strong id="equipmentHealthSummary">Checking this Doshie host...</strong>
                <div id="equipmentHealthDetails" class="admin-health-list"></div>
                <div id="equipmentHealthAlerts" class="permission-request-status"></div>
            </section>
            <section class="admin-card admin-card-wide">
                <small>CONTROLS</small>
                <div class="admin-actions">
                    <button class="tool" onclick="talkToDoshieFromControl()">💬 Talk to Doshie</button>
                    <button class="tool" onclick="openProfileCustomizer()">Customize design</button>
                    <button class="tool" onclick="toggleSettings()">All settings</button>
                    <button class="tool" onclick="createBackup()">Create backup</button>
                    <button class="tool" onclick="restartDoshieService()">Restart Doshie</button>
                </div>
            </section>
            <section class="admin-card admin-card-wide terminal-card">
                <div class="terminal-heading">
                    <div>
                        <small>USER-LEVEL TERMINAL</small>
                        <h2>Tecra command deck</h2>
                        <p>Customize Doshie colors, interface code, model behavior, backups, and services as your normal Linux user.</p>
                    </div>
                    <span class="terminal-user-badge">USER ONLY</span>
                </div>
                <div class="terminal-hints">
                    <button type="button" class="tool" onclick="setAdminTerminalCommand('cd /home/hermes-duran/Doshie && code static/Doshie-app.css')">Open theme CSS</button>
                    <button type="button" class="tool" onclick="setAdminTerminalCommand('cd /home/hermes-duran/Doshie && code static/Doshie-app.js')">Open interface JS</button>
                    <button type="button" class="tool" onclick="setAdminTerminalCommand('cd /home/hermes-duran/Doshie && git status --short')">Check changes</button>
                    <button type="button" class="tool" onclick="setAdminTerminalCommand('cd /home/hermes-duran/Doshie && scripts/backup-Doshie-now')">Create backup</button>
                </div>
                <pre id="adminTerminalOutput" class="admin-terminal-output">Terminal closed. Open it to control Tecra as your user.</pre>
                <div class="admin-terminal-input-row">
                    <input id="adminTerminalInput" placeholder="Type a command, e.g. code static/Doshie-app.css" autocomplete="off">
                    <button type="button" class="tool" onclick="startAdminTerminal()">Open</button>
                    <button type="button" class="tool" onclick="sendAdminTerminalInput()">Run</button>
                    <button type="button" class="tool" onclick="stopAdminTerminal()">Close</button>
                </div>
                <small class="permission-note">Full user-level shell. It does not automatically run as root. If you type <code>sudo</code>, Linux asks for your password.</small>
            </section>
            <section class="admin-card admin-card-wide agent-foundry-card">
                <div class="agent-foundry-heading">
                    <div>
                        <small>AGENT FOUNDRY</small>
                        <h2>Build Doshie specialists</h2>
                        <p>Create focused local AIs with separate brains, memory boundaries, and approved capabilities.</p>
                    </div>
                    <button class="tool agent-new-button" onclick="openAgentEditor()">＋ New AI</button>
                </div>
                <div class="agent-safety-lock">
                    <span>🔐 Hermes approval lock</span>
                    <small>Every agent can propose actions. None receives shell, root, or unattended control.</small>
                </div>
                <div id="agentFoundryStatus" class="admin-path-status"></div>
                <div id="agentList" class="agent-list">
                    <span class="agent-empty">Loading Agent Foundry...</span>
                </div>

                <form id="agentEditor" class="agent-editor" hidden onsubmit="saveAgent(event)">
                    <input id="agentId" type="hidden">
                    <div class="agent-editor-title">
                        <strong id="agentEditorTitle">Create a new AI</strong>
                        <button type="button" class="panel-close" onclick="closeAgentEditor()">✕</button>
                    </div>
                    <div class="agent-form-grid">
                        <label class="settings-field">
                            <span>AI name</span>
                            <input id="agentName" maxlength="48" required placeholder="Example: Neon Architect">
                        </label>
                        <label class="settings-field">
                            <span>Identity color</span>
                            <input id="agentAccent" type="color" value="#35f2d0">
                        </label>
                        <label class="settings-field agent-field-wide">
                            <span>Main responsibility</span>
                            <input id="agentPurpose" maxlength="240" required
                                   placeholder="Designs and checks Doshie interfaces">
                        </label>
                        <label class="settings-field">
                            <span>Brain</span>
                            <select id="agentBrain">
                                <option value="auto">Auto router</option>
                                <option value="fast">Fast · everyday</option>
                                <option value="balanced">Balanced · planning</option>
                                <option value="coding">Coder · software</option>
                                <option value="advanced">Advanced · deep work</option>
                                <option value="vision" data-admin-only="true">Vision · photos</option>
                            </select>
                        </label>
                        <label class="settings-field">
                            <span>Memory boundary</span>
                            <select id="agentMemory">
                                <option value="none">None · clean session</option>
                                <option value="private">Hermes private only</option>
                                <option value="shared">Shared family only</option>
                                <option value="all">Private + shared</option>
                            </select>
                        </label>
                        <label class="settings-field agent-field-wide">
                            <span>Personality and operating rules</span>
                            <textarea id="agentInstructions" maxlength="4000"
                                      placeholder="How should this AI think, speak, and solve problems?"></textarea>
                        </label>
                    </div>
                    <fieldset class="agent-capabilities">
                        <legend>Approved capability requests</legend>
                        <label><input type="checkbox" value="memory_read"> Read allowed memory</label>
                        <label><input type="checkbox" value="memory_write"> Propose new memory</label>
                        <label><input type="checkbox" value="service_health"> Check system health</label>
                        <label><input type="checkbox" value="project_read"> Read project files</label>
                        <label><input type="checkbox" value="code_proposals"> Propose code changes</label>
                        <label><input type="checkbox" value="web_research"> Research the web</label>
                    </fieldset>
                    <label class="settings-toggle agent-enabled-toggle">
                        <span>Agent enabled</span>
                        <input id="agentEnabled" type="checkbox" checked>
                    </label>
                    <div class="admin-actions">
                        <button class="tool" type="submit">Save AI</button>
                        <button class="tool" type="button" onclick="closeAgentEditor()">Cancel</button>
                    </div>
                </form>

                <div id="agentTestConsole" class="agent-test-console" hidden>
                    <div class="agent-editor-title">
                        <strong id="agentTestTitle">Test agent</strong>
                        <button type="button" class="panel-close" onclick="closeAgentTest()">✕</button>
                    </div>
                    <textarea id="agentTestMessage" maxlength="2000"
                              placeholder="Ask this specialist something..."></textarea>
                    <div class="admin-actions">
                        <button class="tool" onclick="runAgentTest()">Run protected test</button>
                    </div>
                    <pre id="agentTestReply" class="agent-test-reply">Ready.</pre>
                </div>
            </section>
            <section class="admin-card admin-card-wide">
                <small>MOVE TO A BIGGER HOME</small>
                <p>Create a verified package with profiles, memories, settings, and customization.</p>
                <button class="tool" onclick="createMigrationPackage()">Create migration package</button>
                <div id="migrationStatus" class="admin-path-status"></div>
            </section>
        </div>
    </div>

    <div id="settingsPanel" style="
        display:none;
        padding:14px;
        background:#17201c;
        border-bottom:1px solid #2b3932;
    ">
        <div class="panel-heading">
            <strong>⚙️ Settings</strong>
            <button type="button"
                    class="panel-close"
                    onclick="closeSettings()"
                    aria-label="Close settings">✕</button>
        </div>

        <div class="settings-stack">
            <details class="settings-group" open>
                <summary>General</summary>
                <div class="settings-body">
                    <label class="settings-toggle">
                        <span>Automatic memory</span>
                        <input type="checkbox" id="autoMemory">
                    </label>
                    <label class="settings-toggle">
                        <span>Speak Doshie's replies</span>
                        <input type="checkbox" id="speakReplies">
                    </label>
                    <label class="settings-field" for="DoshieMode">
                        <span>Doshie mode</span>
                        <select id="DoshieMode"
                                onchange="applyDoshieMode()">
                            <option value="family">🏠 Family</option>
                            <option value="normal">🦖 Normal</option>
                            <option value="tech">💻 Tech</option>
                            <option value="gaming">🎮 Gaming</option>
                        </select>
                    </label>
                    <label class="settings-field" for="weatherLocation">
                        <span>Weather location</span>
                        <input id="weatherLocation" placeholder="El Paso">
                    </label>
                    <small class="permission-note">
                        Weather uses this saved city. Doshie does not read your
                        device location unless you explicitly approve a future location feature.
                    </small>
                    <section id="familyInviteAdmin" class="family-invite-admin" hidden>
                        <h4>Family invitations</h4>
                        <p class="permission-note">
                            Create a one-time, seven-day invitation for a protected
                            family account. Only administrators can use this section.
                        </p>
                        <label class="settings-field" for="familyInviteTarget">
                            <span>Family account</span>
                            <select id="familyInviteTarget"></select>
                        </label>
                        <button type="button" class="tool"
                                onclick="createFamilyInvite()">Create invitation</button>
                        <textarea id="familyInviteUrl" readonly
                                  placeholder="The secure invitation link appears here."></textarea>
                        <button type="button" class="tool"
                                onclick="copyFamilyInvite()">Copy link</button>
                        <div id="familyInviteAdminStatus" role="status"></div>
                        <div id="familyInviteList"></div>
                    </section>
                </div>
            </details>

            <details class="settings-group">
                <summary>Account &amp; privacy</summary>
                <div class="settings-body">
                    <small style="color:var(--muted);">
                        Choose a photo and use no password, a PIN, or a regular password.
                    </small>
                    <label class="settings-field" for="profileLockTarget">
                        <span>Account</span>
                        <select id="profileLockTarget"
                                onchange="refreshProfileLockControls()"></select>
                    </label>
                    <div class="profile-photo-editor">
                        <div class="profile-photo-preview" aria-hidden="true">
                            <img id="profilePhotoPreview" alt="" hidden>
                            <span id="profilePhotoInitials">Y</span>
                        </div>
                        <div class="profile-photo-tools">
                            <strong>Profile photo</strong>
                            <div>
                                <label class="tool profile-photo-picker">
                                    📷 Choose photo
                                    <input id="profilePhotoInput" type="file"
                                           accept="image/png,image/jpeg,image/webp"
                                           onchange="uploadProfileAvatar(event)">
                                </label>
                                <button type="button" class="tool"
                                        onclick="removeProfileAvatar()">Remove</button>
                            </div>
                        </div>
                    </div>
                    <div id="profilePhotoStatus" class="profile-photo-status"
                         aria-live="polite"></div>
                    <small class="permission-note">
                        Doshie cannot open a live camera by itself. A camera or
                        photo library opens only after you tap Choose photo and approve it.
                    </small>
                    <label class="settings-field" for="profileSecurityType">
                        <span>Sign-in protection</span>
                        <select id="profileSecurityType"
                                onchange="updateProfileSecurityFields()">
                            <option value="none">No password</option>
                            <option value="pin">PIN (4–8 digits)</option>
                            <option value="password">Password</option>
                        </select>
                    </label>
                    <div id="profileLockStatus" class="profile-lock-status"
                         aria-live="polite">Choose a profile.</div>
                    <label class="settings-field" for="profileCurrentPin">
                        <span id="profileCurrentCredentialLabel">Current sign-in (if requested)</span>
                        <span class="credential-field"><input id="profileCurrentPin" type="password"
                               maxlength="64"
                               autocomplete="current-password"><button type="button" onclick="toggleCredentialField('profileCurrentPin',this)" aria-label="Show current sign-in">👁</button></span>
                    </label>
                    <label class="settings-field" for="profileNewPin">
                        <span id="profileNewCredentialLabel">New sign-in</span>
                        <span class="credential-field"><input id="profileNewPin" type="password"
                               maxlength="64" autocomplete="new-password"><button type="button" onclick="toggleCredentialField('profileNewPin',this)" aria-label="Show new sign-in">👁</button></span>
                    </label>
                    <label class="settings-field" for="profileConfirmPin">
                        <span id="profileConfirmCredentialLabel">Confirm new sign-in</span>
                        <span class="credential-field"><input id="profileConfirmPin" type="password"
                               maxlength="64"
                               autocomplete="new-password"><button type="button" onclick="toggleCredentialField('profileConfirmPin',this)" aria-label="Show confirmation">👁</button></span>
                    </label>
                    <div class="profile-lock-actions">
                        <button type="button" class="tool"
                                onclick="saveProfileSecurity()">🔐 Save account security</button>
                        <button type="button" class="tool profile-session-toggle"
                                onclick="unlockProfileInside()">🔓 Unlock access</button>
                        <button type="button" class="tool profile-session-toggle"
                                onclick="lockProfileNow()">🔒 Lock now</button>
                        <button type="button" class="tool"
                                onclick="removeProfileProtection()">Remove protection</button>
                    </div>
                    <small style="color:var(--muted);">
                        Passwords and PINs are stored only as one-way hashes on the TECRA.
                    </small>
                    <hr>
                    <h4>Forgot sign-in recovery</h4>
                    <small id="profileRecoveryCurrent" class="permission-note">
                        Add an email address, phone number, or both.
                    </small>
                    <label class="settings-field" for="profileRecoveryEmail">
                        <span>Recovery email</span>
                        <input id="profileRecoveryEmail" type="email"
                               autocomplete="email" placeholder="name@example.com">
                    </label>
                    <label class="settings-field" for="profileRecoveryPhone">
                        <span>Recovery phone</span>
                        <input id="profileRecoveryPhone" type="tel"
                               autocomplete="tel" placeholder="+1 555 123 4567">
                    </label>
                    <button type="button" class="tool"
                            onclick="saveProfileRecovery()">Save recovery methods</button>
                    <div id="profileRecoveryStatus" role="status"></div>
                </div>
            </details>

            <details class="settings-group"
                     ontoggle="if (this.open) refreshHealthSyncControls()">
                <summary>Health sync</summary>
                <div class="settings-body">
                    <p class="customizer-intro">
                        Samsung Health data can be shared through an Android Health Connect bridge.
                        Access is off by default and belongs to the signed-in account only.
                    </p>
                    <label class="settings-field" for="healthSyncEnabled">
                        <span>Allow Health sync</span>
                        <input id="healthSyncEnabled" type="checkbox">
                    </label>
                    <div class="profile-lock-actions" id="healthPermissionChoices">
                        <label><input type="checkbox" data-health-permission value="activity"> Activity</label>
                        <label><input type="checkbox" data-health-permission value="heart"> Heart</label>
                        <label><input type="checkbox" data-health-permission value="sleep"> Sleep</label>
                        <label><input type="checkbox" data-health-permission value="workouts"> Workouts</label>
                        <label><input type="checkbox" data-health-permission value="body"> Body</label>
                        <label><input type="checkbox" data-health-permission value="nutrition"> Nutrition</label>
                        <label><input type="checkbox" data-health-permission value="medications"> Medications</label>
                    </div>
                    <button type="button" class="tool" onclick="saveHealthSyncControls()">
                        🫀 Save Health permissions
                    </button>
                    <div id="healthSyncStatus" class="profile-lock-status" aria-live="polite"></div>
                    <small class="permission-note">
                        Sync requires this account to be unlocked, explicit consent to be enabled,
                        and an online connection. Doshie never grants Health access to another profile.
                    </small>
                </div>
            </details>

            <details id="profileCustomizeGroup" class="settings-group" open>
                <summary>Full app &amp; website design control</summary>
                <div class="settings-body profile-customizer">
                    <p class="customizer-intro">
                        Personalize <strong id="customizingProfileName">this account</strong>.
                        Changes stay private on the TECRA.
                    </p>
                    <label class="settings-field" for="profileStatus">
                        <span>Status</span>
                        <input id="profileStatus" maxlength="80"
                               placeholder="What are you up to?">
                    </label>
                    <label class="settings-field" for="profileAbout">
                        <span>About Me</span>
                        <textarea id="profileAbout" maxlength="240" rows="3"
                                  placeholder="A few things Doshie should show on your profile."></textarea>
                    </label>
                    <label class="settings-field" for="profileInterests">
                        <span>Interests &amp; favorites</span>
                        <textarea id="profileInterests" maxlength="240" rows="2"
                                  placeholder="Games, music, teams, hobbies, creators…"></textarea>
                    </label>
                    <label class="settings-field" for="profileMusicUrl">
                        <span>Profile music link</span>
                        <input id="profileMusicUrl" type="url" maxlength="500"
                               placeholder="https://open.spotify.com/...">
                        <small>HTTPS link only. Music opens after the user taps it.</small>
                    </label>
                    <fieldset class="accent-picker">
                        <legend>Accent color</legend>
                        <div class="accent-options" id="profileAccentOptions">
                            <button type="button" data-accent="mint" title="Mint"
                                    onclick="chooseProfileAccent('mint')"></button>
                            <button type="button" data-accent="forest" title="Forest"
                                    onclick="chooseProfileAccent('forest')"></button>
                            <button type="button" data-accent="teal" title="Teal"
                                    onclick="chooseProfileAccent('teal')"></button>
                            <button type="button" data-accent="blue" title="Blue"
                                    onclick="chooseProfileAccent('blue')"></button>
                            <button type="button" data-accent="purple" title="Purple"
                                    onclick="chooseProfileAccent('purple')"></button>
                            <button type="button" data-accent="rose" title="Rose"
                                    onclick="chooseProfileAccent('rose')"></button>
                            <button type="button" data-accent="orange" title="Orange"
                                    onclick="chooseProfileAccent('orange')"></button>
                            <button type="button" data-accent="amber" title="Amber"
                                    onclick="chooseProfileAccent('amber')"></button>
                        </div>
                    </fieldset>
                    <label class="settings-field" for="profileTheme">
                        <span>Theme</span>
                        <select id="profileTheme" onchange="renderProfilePreview()">
                            <option value="forest">🌲 Forest</option>
                            <option value="midnight">🌙 Midnight</option>
                            <option value="jungle">🌿 Jungle</option>
                            <option value="sunset">🌅 Sunset</option>
                            <option value="stars">✨ Stars</option>
                            <option value="tron">◈ Tron Grid</option>
                        </select>
                    </label>
                    <div id="tronThemeControls" class="tron-controls" hidden>
                        <strong>Tron interface controls</strong>
                        <label class="settings-field" for="profileCustomColor">
                            <span>Neon color</span>
                            <input id="profileCustomColor" type="color" value="#31f6ff"
                                   oninput="renderProfilePreview()">
                        </label>
                        <label class="settings-field" for="profileFontFamily">
                            <span>Font</span>
                            <select id="profileFontFamily" onchange="renderProfilePreview()">
                                <option value="tech">Tech</option>
                                <option value="system">System</option>
                                <option value="mono">Monospace</option>
                                <option value="compact">Compact</option>
                                <option value="classic">Classic</option>
                            </select>
                        </label>
                        <label class="settings-field" for="profileFontSize">
                            <span>Text size <output id="profileFontSizeValue">100%</output></span>
                            <input id="profileFontSize" type="range"
                                   min="85" max="130" step="15" value="100"
                                   oninput="renderProfilePreview()">
                        </label>
                    </div>
                    <label class="settings-field" for="profileNewsTopic">
                        <span>News topic</span>
                        <select id="profileNewsTopic">
                            <option value="local">Local · El Paso</option>
                            <option value="national">National</option>
                            <option value="tech">Technology</option>
                            <option value="gaming">Gaming</option>
                            <option value="family">Family</option>
                        </select>
                    </label>
                    <label class="settings-toggle">
                        <span>Show the news banner</span>
                        <input type="checkbox" id="profileNewsVisible">
                    </label>
                    <label class="settings-field" for="profileAutoLock">
                        <span>Lock protected account after</span>
                        <select id="profileAutoLock">
                            <option value="5">5 minutes</option>
                            <option value="15">15 minutes</option>
                            <option value="30">30 minutes</option>
                            <option value="60">1 hour</option>
                            <option value="0">When the app closes</option>
                        </select>
                    </label>
                    <label class="settings-toggle">
                        <span>Lock when app closes</span>
                        <input type="checkbox" id="profileLockOnClose">
                    </label>
                    <div id="adminCssControls" class="admin-css-controls" hidden>
                        <div class="full-control-heading">
                            <div>
                                <strong>Full website CSS control</strong>
                                <small>Change backgrounds, panels, buttons, spacing, fonts, and glow.</small>
                            </div>
                            <button type="button" class="tool"
                                    onclick="openAdminControl()">Open command deck</button>
                        </div>
                        <div class="theme-preset-actions">
                            <button type="button" class="tool"
                                    onclick="applyAdminThemePreset('dark-red')">Dark red MySpace</button>
                            <button type="button" class="tool"
                                    onclick="applyAdminThemePreset('deep-red')">Deep red minimal</button>
                        </div>
                        <label class="settings-field" for="profileCustomCss">
                            <span>Custom CSS <small>Admin only · MySpace mode</small></span>
                            <textarea id="profileCustomCss" rows="9" maxlength="12000"
                                      spellcheck="false"
                                      placeholder="/* Change Doshie directly, like a MySpace profile */"
                                      oninput="previewAdminCustomCss()"></textarea>
                        </label>
                        <div class="customizer-actions">
                            <button type="button" class="tool"
                                    onclick="resetAdminCustomCss()">Reset CSS</button>
                        </div>
                        <small>Your CSS previews immediately. Save profile style to keep it.</small>
                    </div>
                    <div id="profileStylePreview" class="profile-style-preview">
                        <strong id="profilePreviewName">Profile</strong>
                        <span id="profilePreviewStatus">Your status appears here.</span>
                        <p id="profilePreviewAbout">Your About Me appears here.</p>
                        <p id="profilePreviewInterests">Your interests appear here.</p>
                        <a id="profilePreviewMusic" href="#" target="_blank"
                           rel="noopener" hidden>🎵 Open profile music</a>
                    </div>
                    <div class="customizer-actions">
                        <button type="button" class="tool"
                                onclick="restoreProfileDefaults()">Restore defaults</button>
                        <button type="button" class="tool"
                                onclick="saveProfilePreferences()">Save profile style</button>
                    </div>
                    <div id="profilePreferenceStatus" class="profile-photo-status"
                         aria-live="polite"></div>
                </div>
            </details>

            <details class="settings-group">
                <summary>Voice</summary>
                <div class="settings-body">
                    <label class="settings-field" for="voiceIdentity">
                        <span>Voice identity</span>
                        <select id="voiceIdentity"
                                onchange="applyVoiceIdentity()">
                            <option value="hermes">🧠 Hermes — Private local voice</option>
                            <option value="Doshie">🦖 Doshie — Friendly device voice</option>
                            <option value="device">📱 Custom device voice</option>
                        </select>
                        <small>Choose the personality first; fine-tune the engine, voice, speed, and pitch below.</small>
                    </label>
                    <label class="settings-field" for="voiceEngine">
                        <span>Voice engine</span>
                        <select id="voiceEngine"
                                onchange="updateVoiceControls()">
                            <option value="clone">🎙️ Hermes — Private Clone</option>
                            <option value="device">📱 Device Voice</option>
                        </select>
                    </label>
                    <label class="settings-field" for="voiceSelect">
                        <span>Device voice fallback</span>
                        <select id="voiceSelect"></select>
                    </label>
                    <label class="settings-field" for="voicePreset">
                        <span>Voice preset</span>
                        <select id="voicePreset"
                                onchange="applyVoicePreset()">
                            <option value="custom">Custom</option>
                            <option value="calm">🌿 Calm</option>
                            <option value="tech">💻 Tech</option>
                            <option value="dino">🦖 Dino</option>
                        </select>
                    </label>
                    <label class="settings-field" for="voiceRate">
                        <span>Speech rate</span>
                        <input id="voiceRate" type="range"
                               min="0.5" max="1.5" step="0.1" value="1.0">
                    </label>
                    <label class="settings-field" for="voicePitch">
                        <span>Pitch</span>
                        <input id="voicePitch" type="range"
                               min="0.5" max="1.5" step="0.1" value="1.0">
                    </label>
                    <div class="voice-settings-actions">
                        <button type="button" class="tool"
                                onclick="enableMicrophone()">🎙 Enable microphone</button>
                        <button type="button" class="tool"
                                onclick="testVoice()">▶ Test voice</button>
                        <button type="button" class="tool"
                                onclick="stopDoshieVoice()">⏹ Stop voice</button>
                    </div>
                    <div id="microphoneStatus" class="profile-photo-status"
                         aria-live="polite">Tap Enable microphone once on each device.</div>
                    <small style="color:var(--muted);">
                        The private clone runs on the TECRA. Microphone input
                        uses this device's browser; Ctrl+Space also starts or stops listening.
                    </small>
                </div>
            </details>

            <details class="settings-group">
                <summary>App maintenance</summary>
                <div class="settings-body">
                    <small style="color:var(--muted);">
                        Refresh reloads the screen. Clear cache downloads the
                        newest interface. Restart safely restarts Doshie's web
                        service. Your memories, profiles, and voice stay safe.
                    </small>
                    <div class="maintenance-actions">
                        <button type="button" class="tool"
                                onclick="refreshDoshieApp()">
                            ↻ Refresh app
                        </button>
                        <button type="button" class="tool"
                                onclick="clearDoshieCache()">
                            🧹 Clear cache
                        </button>
                        <button type="button"
                                class="tool maintenance-restart"
                                onclick="restartDoshieApp()">
                            🔄 Restart Doshie
                        </button>
                    </div>
                </div>
            </details>
        </div>

        <div class="settings-actions">
            <button class="tool" onclick="saveSettings()">Save</button>
            <button class="tool" onclick="closeSettings()">Close</button>
        </div>
    </div>

    <div id="spotifyPanel" style="
        display:none;
        padding:14px;
        background:#17201c;
        border-bottom:1px solid #2b3932;
        overflow:auto;
    ">
        <div class="panel-heading">
            <strong>🎵 Spotify</strong>
            <button type="button"
                    class="panel-close"
                    onclick="closeSpotify()"
                    aria-label="Close Spotify">✕</button>
        </div>

        <div id="spotifyStatusText" class="spotify-status">
            Checking Spotify...
        </div>

        <section id="spotifySetupSection">
            <p style="margin-top:0;">
                <strong>Connect in four steps</strong><br>
                This is a one-time setup for this Doshie profile.
            </p>
            <ol class="spotify-setup-steps">
                <li>
                    <a class="tool spotify-dashboard-link"
                       href="https://developer.spotify.com/dashboard"
                       target="_blank" rel="noopener">
                        Open Spotify Dashboard
                    </a>
                    and choose <strong>Create app</strong>.
                </li>
                <li>
                    Name it <strong>Doshie</strong>. If Spotify asks which
                    product you will use, choose <strong>Web API</strong>.
                </li>
                <li>
                    In the app settings, add this exact
                    <strong>Redirect URI</strong>, then save:
                    <div class="spotify-copy-row">
                        <code id="spotifyCallbackUri"></code>
                        <button type="button" class="tool"
                                onclick="copySpotifyCallback()">
                            Copy URI
                        </button>
                    </div>
                </li>
                <li>
                    Copy the app's <strong>Client ID</strong>—not the
                    Client Secret—and paste it below.
                </li>
            </ol>
            <label class="settings-field" for="spotifyClientId">
                <span>Spotify Client ID</span>
                <input id="spotifyClientId"
                       autocomplete="off"
                       placeholder="Paste the Client ID">
            </label>
            <button class="tool spotify-connect-button"
                    id="spotifyConnectButton"
                    onclick="saveAndConnectSpotify()">
                Save &amp; Connect Spotify
            </button>
            <small style="display:block;margin-top:10px;color:var(--muted);">
                Doshie uses Spotify's PKCE sign-in. Your Spotify password and
                Client Secret are never requested or stored.
            </small>
        </section>

        <section id="spotifyPlayerSection" hidden>
            <div class="spotify-player-card">
                <img id="spotifyAlbumArt" class="spotify-art"
                     src="/static/Doshie-icon.svg" alt="Current album art">
                <div class="spotify-track-copy">
                    <div class="spotify-state-row">
                        <span id="spotifyPlaybackState"
                              class="spotify-playback-state">Not playing</span>
                        <small id="spotifyDeviceName">No active player</small>
                    </div>
                    <strong id="spotifyTrackName">Nothing playing</strong>
                    <span id="spotifyArtistName">Open Spotify on a device</span>
                    <div class="spotify-progress-row">
                        <progress id="spotifyProgress" class="spotify-progress"
                                  max="1" value="0"></progress>
                        <small id="spotifyTime">0:00 / 0:00</small>
                    </div>
                </div>
            </div>

            <div class="spotify-controls" aria-label="Spotify controls">
                <button class="spotify-control" onclick="spotifyControl('previous')"
                        aria-label="Previous track">⏮</button>
                <button id="spotifyPlayPauseButton"
                        class="spotify-control spotify-main-control"
                        onclick="spotifyTogglePlayback()" aria-label="Play">▶</button>
                <button class="spotify-control" onclick="spotifyControl('next')"
                        aria-label="Next track">⏭</button>
                <button class="spotify-control" onclick="loadSpotifyNowPlaying(true)"
                        aria-label="Refresh player">↻</button>
            </div>

            <div class="spotify-search">
                <input id="spotifySearchInput"
                       placeholder="Song, artist, or album"
                       onkeydown="if(event.key === 'Enter') searchSpotify()">
                <button class="tool" onclick="searchSpotify()">Search</button>
            </div>
            <div id="spotifySearchResults" class="spotify-list"></div>

            <div style="display:flex;align-items:center;justify-content:space-between;margin:16px 0 8px;">
                <strong>My playlists</strong>
                <button class="tool" onclick="loadSpotifyPlaylists()">Refresh</button>
            </div>
            <div id="spotifyPlaylistList" class="spotify-list"></div>

            <button class="tool"
                    style="margin-top:18px;"
                    onclick="disconnectSpotify()">
                Disconnect this profile
            </button>
        </section>
    </div>

    <div id="remindersPanel" style="
        display:none;
        padding:14px;
        background:#17201c;
        border-bottom:1px solid #2b3932;
    ">
        <h3 style="margin-top:0;">⏰ Reminders</h3>

        <div style="
            padding:10px;
            margin-bottom:12px;
            background:#202824;
            border-radius:10px;
        ">
            <input
                id="newReminderText"
                placeholder="Reminder..."
                style="width:100%;padding:8px;margin-bottom:8px;"
            >

            <input
                id="newReminderDate"
                type="date"
                style="padding:8px;margin-bottom:8px;"
            >

            <select id="newReminderFamily"
                    style="padding:8px;margin-bottom:8px;">
                <option value="">Unassigned</option>
            </select>

            <button class="tool" onclick="createReminder()">
                ➕ Add Reminder
            </button>
        </div>

        <div id="remindersList">Loading...</div>

        <button class="tool" onclick="closeReminders()">
            Close
        </button>
    </div>

    <div id="shoppingPanel" style="
        display:none;
        padding:14px;
        background:#17201c;
        border-bottom:1px solid #2b3932;
    ">
        <h3 style="margin-top:0;">🛒 Family Shopping</h3>

        <select id="shoppingFamilyFilter"
                onchange="openShopping()"
                style="padding:8px;margin-bottom:10px;">
            <option value="">Everyone</option>
        </select>

        <div style="
            padding:10px;
            margin-bottom:12px;
            background:#202824;
            border-radius:10px;
        ">
            <input
                id="newShoppingItem"
                placeholder="Item"
                style="width:100%;padding:8px;margin-bottom:8px;"
            >

            <input
                id="newShoppingQuantity"
                placeholder="Quantity, optional"
                style="width:100%;padding:8px;margin-bottom:8px;"
            >


            <select id="newShoppingCategory"
                    style="padding:8px;margin-bottom:8px;">
                <option>Groceries</option>
                <option>Pets</option>
                <option>Household</option>
                <option>School</option>
                <option>Tech</option>
                <option selected>Other</option>
            </select>

            <button class="tool" onclick="createShoppingItem()">
                ➕ Add Item
            </button>
        </div>

        <div id="shoppingList">Loading...</div>

        <button class="tool" onclick="closeShopping()">
            Close
        </button>
    </div>

    <div id="familyDashboardPanel" style="
        display:none;
        padding:14px;
        background:#17201c;
        border-bottom:1px solid #2b3932;
    ">
        <h3 style="margin-top:0;">🏠 Family Dashboard</h3>

        <div id="familyTodayBox" style="
            padding:12px;
            margin-bottom:14px;
            background:#202824;
            border-radius:12px;
        ">
            Loading today's family plan...
        </div>

        <div id="familyDashboardList">Loading...</div>

        <button class="tool" onclick="closeFamilyDashboard()">
            Close
        </button>
    </div>

    <div id="familyPanel" style="
        display:none;
        padding:14px;
        background:#17201c;
        border-bottom:1px solid #2b3932;
    ">
        <h3 style="margin-top:0;">👨‍👩‍👧‍👦 Family</h3>

        <div style="
            padding:10px;
            margin-bottom:12px;
            background:#202824;
            border-radius:10px;
        ">
            <input
                id="newFamilyName"
                placeholder="Name"
                style="width:100%;padding:8px;margin-bottom:8px;"
            >

            <input
                id="newFamilyRole"
                placeholder="Role, e.g. wife, son, daughter"
                style="width:100%;padding:8px;margin-bottom:8px;"
            >

            <input
                id="newFamilyNotes"
                placeholder="Optional notes"
                style="width:100%;padding:8px;margin-bottom:8px;"
            >

            <button class="tool" onclick="createFamilyMember()">
                ➕ Add Family Member
            </button>
        </div>

        <div id="familyList">Loading...</div>

        <button class="tool" onclick="closeFamily()">
            Close
        </button>
    </div>

    <div id="organizerPanel" style="
        display:none;
        padding:14px;
        background:#17201c;
        border-bottom:1px solid #2b3932;
    ">
        <h3 style="margin-top:0;">📝 Organizer</h3>

        <div style="
            display:flex;
            flex-wrap:wrap;
            gap:8px;
            margin-bottom:12px;
        ">
            <button class="tool" onclick="setOrganizerTag('all')">All</button>
            <button class="tool" onclick="setOrganizerTag('Tech')">Tech</button>
            <button class="tool" onclick="setOrganizerTag('Home')">Home</button>
            <button class="tool" onclick="setOrganizerTag('School')">School</button>
            <button class="tool" onclick="setOrganizerTag('Gaming')">Gaming</button>
            <button class="tool" onclick="setOrganizerTag('Personal')">Personal</button>
            <button class="tool" onclick="setOrganizerTag('General')">General</button>
        </div>

        <div style="margin-bottom:16px;">
            <h4>✅ Tasks</h4>

            <div style="
                padding:10px;
                margin-bottom:12px;
                background:#202824;
                border-radius:10px;
            ">
                <input
                    id="newTaskText"
                    placeholder="New task..."
                    style="
                        width:100%;
                        padding:8px;
                        margin-bottom:8px;
                    "
                >

                <div style="
                    display:flex;
                    flex-wrap:wrap;
                    gap:8px;
                ">
                    <select id="newTaskPriority" style="padding:8px;">
                        <option>Low</option>
                        <option selected>Normal</option>
                        <option>High</option>
                    </select>

                    <input
                        id="newTaskDue"
                        type="date"
                        style="padding:8px;"
                    >

                    <select id="newTaskTag" style="padding:8px;">
                        <option>General</option>
                        <option>Tech</option>
                        <option>Home</option>
                        <option>School</option>
                        <option>Gaming</option>
                        <option>Personal</option>
                    </select>


                    <select id="newTaskFamily" style="padding:8px;">
                        <option value="">Unassigned</option>
                    </select>

                    <button class="tool" onclick="createTask()">
                        ➕ Add Task
                    </button>
                </div>
            </div>

            <div id="taskList">Loading...</div>
        </div>

        <div>
            <h4>🗒️ Notes</h4>

            <div style="
                padding:10px;
                margin-bottom:12px;
                background:#202824;
                border-radius:10px;
            ">
                <textarea
                    id="newNoteText"
                    placeholder="New note..."
                    rows="3"
                    style="
                        width:100%;
                        padding:8px;
                        margin-bottom:8px;
                        resize:vertical;
                    "
                ></textarea>

                <select id="newNoteTag" style="padding:8px;margin-bottom:8px;">
                    <option>General</option>
                    <option>Tech</option>
                    <option>Home</option>
                    <option>School</option>
                    <option>Gaming</option>
                    <option>Personal</option>
                </select>

                <button class="tool" onclick="createNote()">
                    ➕ Add Note
                </button>
            </div>

            <div id="noteList">Loading...</div>
        </div>

        <button class="tool" onclick="closeOrganizer()">Close</button>
    </div>

    <div id="taskAlert" style="
        display:none;
        margin:10px 14px;
        padding:12px;
        background:#2a2118;
        border:1px solid #5a4732;
        border-radius:12px;
    ">
        <div id="taskAlertText"></div>

        <button class="tool"
                style="margin-top:8px;"
                onclick="openOrganizer('all')">
            View Tasks
        </button>
    </div>

    <div class="quick-add-card" style="
        padding:10px 14px;
        background:#17201c;
        border-bottom:1px solid #2b3932;
    ">
        <div style="
            display:flex;
            gap:8px;
            flex-wrap:wrap;
        ">
            <input
                id="quickShoppingItem"
                placeholder="Quick add shopping item..."
                style="
                    flex:1;
                    min-width:180px;
                    padding:8px;
                "
            >

            <select id="quickShoppingCategory"
                    style="padding:8px;">
                <option>Groceries</option>
                <option>Pets</option>
                <option>Household</option>
                <option>School</option>
                <option>Tech</option>
                <option>Other</option>
            </select>

            <button class="tool" onclick="quickAddShopping()">
                🛒 Add
            </button>
        </div>
    </div>

    <div class="quick-add-card" style="
        padding:10px 14px;
        background:#17201c;
        border-bottom:1px solid #2b3932;
    ">
        <div style="
            display:flex;
            gap:8px;
            flex-wrap:wrap;
        ">
            <input
                id="quickTaskText"
                placeholder="Quick family task..."
                style="
                    flex:1;
                    min-width:180px;
                    padding:8px;
                "
            >

            <select id="quickTaskFamily"
                    style="padding:8px;">
                <option value="">Unassigned</option>
            </select>

            <button class="tool" onclick="quickAddTask()">
                ✅ Add
            </button>
        </div>
    </div>

    <div id="watchPanel" class="watch-mode-panel" style="display:none;">
        <div class="watch-shell">
            <header class="watch-topline">
                <span id="watchTime">--:--</span>
                <button onclick="showChatHome()" aria-label="Close watch mode">✕</button>
            </header>
            <div class="watch-identity">
                <span class="watch-dino" aria-hidden="true">🦖</span>
                <div>
                    <strong>Doshie</strong>
                    <small id="watchProfileName">Hermes</small>
                </div>
            </div>
            <div id="watchReply" class="watch-reply" aria-live="polite">
                Ready for a quick question.
            </div>
            <button id="watchTalkButton" class="watch-talk"
                    onclick="enableWatchMicrophone()">
                🎙️ <span>Talk</span>
            </button>
            <div class="watch-quick-actions">
                <button onclick="watchAsk('What is on my schedule today?')">Today</button>
                <button onclick="watchAsk('Show my current tasks')">Tasks</button>
                <button onclick="watchAsk('What is the weather?')">Weather</button>
            </div>
            <form class="watch-form" onsubmit="submitWatchText(event)">
                <input id="watchInput" maxlength="500"
                       placeholder="Ask Doshie…" aria-label="Watch message">
                <button type="submit" aria-label="Send">➤</button>
            </form>
            <small class="watch-note">
                Watch mode uses the same private TECRA brain and account lock.
            </small>
        </div>
    </div>

    <div id="searchPanel" class="search-hub-panel" style="display:none;">
        <header class="feature-panel-header">
            <div>
                <small>PRIVATE SEARCH WORKSPACE</small>
                <h2>🔎 Doshie Search Hub</h2>
            </div>
            <button class="tool" onclick="showChatHome()">Close</button>
        </header>
        <div class="search-mode-tabs" role="tablist" aria-label="Search type">
            <button id="webSearchTab" class="active" type="button"
                    onclick="setSearchMode('web')">🌐 Web</button>
            <button id="deviceSearchTab" type="button"
                    onclick="setSearchMode('device')">📁 TECRA Explorer</button>
        </div>
        <form class="search-hub-form" onsubmit="runSearchHub(event)">
            <span aria-hidden="true">🔎</span>
            <input id="searchHubInput" type="search" maxlength="180"
                   autocomplete="off" placeholder="Search the web…"
                   aria-label="Search">
            <button type="submit">Search</button>
        </form>
        <div id="searchProviderLinks" class="search-provider-links">
            <a id="searchGoogleLink" href="https://www.google.com/"
               target="_blank" rel="noopener noreferrer">Google</a>
            <a id="searchDuckLink" href="https://duckduckgo.com/"
               target="_blank" rel="noopener noreferrer">DuckDuckGo</a>
            <a id="searchBingLink" href="https://www.bing.com/"
               target="_blank" rel="noopener noreferrer">Bing</a>
        </div>
        <p id="searchPrivacyNote" class="search-privacy-note">
            Results appear inside Doshie through Bing. Provider buttons open a new tab.
        </p>
        <div id="searchHubStatus" class="search-hub-status"
             aria-live="polite">Enter a search above.</div>
        <div id="searchHubResults" class="search-results"></div>
    </div>

    <div id="messages">
        <div class="message Doshie">
            Hi Hermes. What can I help with?
        </div>
    </div>

    <div id="status"></div>

    <div class="input-area" id="composer">
        <button id="thinkingBuddy" class="thinking-buddy" type="button"
                onclick="document.getElementById('input').focus()"
                aria-label="Doshie buddy is ready" title="Doshie buddy">
            <img src="/static/Doshie-avatar.png" alt="">
            <span>Ready</span>
        </button>
        <button id="composerMoreButton"
                class="composer-more"
                type="button"
                onclick="toggleComposerTools()"
                aria-expanded="false"
                aria-label="Show chat controls"
                title="Chat controls">⋯</button>
        <select id="chatMode" class="chat-mode"
                aria-label="Doshie chat mode"
                onchange="saveChatMode()">
            <option value="general">💬 General</option>
            <option value="tech">💻 Tech</option>
            <option value="ai_tutor">🧠 AI Tutor</option>
            <option value="coding">⌨️ Coding</option>
            <option value="gaming">🎮 Gaming</option>
        </select>
        <select id="brainMode" class="brain-mode"
                aria-label="Doshie brain" onchange="saveBrainMode()">
            <option value="auto">🧠 Auto</option>
            <option value="fast" data-admin-only="true">⚡ Fast</option>
            <option value="balanced">⚖️ Balanced</option>
            <option value="coding" data-admin-only="true">⌨️ Coding</option>
            <option value="advanced" data-admin-only="true">🚀 Advanced</option>
            <option value="vision" data-admin-only="true">👁 Vision</option>
        </select>
        <details class="chat-options">
            <summary aria-label="Customize chat appearance">Aa</summary>
            <div class="chat-options-menu">
                <strong>Chat appearance</strong>
                <label>Text size
                    <select id="chatTextSize" onchange="saveChatAppearance()">
                        <option value="small">Small</option>
                        <option value="normal" selected>Normal</option>
                        <option value="large">Large</option>
                    </select>
                </label>
                <label>Bubble width
                    <select id="chatBubbleWidth" onchange="saveChatAppearance()">
                        <option value="comfortable">Comfortable</option>
                        <option value="wide" selected>Wide</option>
                        <option value="full">Extra wide</option>
                    </select>
                </label>
                <label>Spacing
                    <select id="chatSpacing" onchange="saveChatAppearance()">
                        <option value="compact">Compact</option>
                        <option value="normal" selected>Normal</option>
                        <option value="roomy">Roomy</option>
                    </select>
                </label>
            </div>
        </details>
        <button class="composer-attach" type="button"
                onclick="openChatAttachmentPicker('file')"
                aria-label="Attach a file" title="Attach file">📎</button>
        <button class="composer-camera" type="button"
                onclick="openChatAttachmentPicker('camera')"
                aria-label="Take or add a photo" title="Camera or photo">📷</button>
        <input id="chatFileInput" type="file" hidden multiple
               accept=".png,.jpg,.jpeg,.webp,.gif,.pdf,.txt,.md,.csv,.json,.py,.js,.css,.html"
               onchange="uploadChatAttachments(event)">
        <input id="chatCameraInput" type="file" hidden
               accept="image/*" capture="environment"
               onchange="uploadChatAttachments(event)">
        <div id="chatAttachmentTray" class="chat-attachment-tray"
             aria-live="polite" hidden></div>
        <button id="voiceButton" class="composer-voice"
                onclick="enableMicrophone()" aria-pressed="false"
                aria-label="Talk to Doshie"
                title="Tap to talk; tap again to stop">
            <span aria-hidden="true">🎙️</span><span class="mic-label">Talk</span>
        </button>
        <input
            id="input"
            placeholder="Message Doshie..."
            autocomplete="off"
        >
        <button class="send" onclick="send()" aria-label="Send message">Send</button>
        <button id="stopThinkingButton"
                class="stop-thinking"
                onclick="stopThinking()"
                aria-label="Stop Doshie thinking"
                hidden>■ Stop</button>
        <button id="composerCollapseButton"
                class="composer-collapse"
                type="button"
                onclick="toggleComposerMinimized()"
                aria-label="Minimize chat box"
                title="Minimize chat box">—</button>
    </div>

    <nav class="mobile-nav" aria-label="Doshie app navigation">
        <button class="active" data-app-view="chat" onclick="openAppView('chat')">💬<span>Chat</span></button>
        <button data-app-view="family" onclick="openAppView('family')">🏠<span>Family</span></button>
        <button id="voiceDockButton" class="voice-dock" onclick="enableMicrophone()"
                aria-pressed="false" aria-label="Talk to Doshie">🎙️</button>
        <button data-app-view="organizer" onclick="openAppView('organizer')">✅<span>Tasks</span></button>
        <button onclick="toggleSidebar()">☰<span>More</span></button>
    </nav>

</div>

<div id="profileUnlockModal" class="profile-lock-modal" hidden
     role="dialog" aria-modal="true" aria-labelledby="profileUnlockTitle">
    <form class="profile-lock-card" onsubmit="submitProfileUnlock(event)">
        <button type="button" class="profile-lock-close"
                onclick="closeProfileUnlock(false)"
                aria-label="Cancel profile unlock">✕</button>
        <div class="profile-lock-mark">🔒</div>
        <h2 id="profileUnlockTitle">Unlock profile</h2>
        <p id="profileUnlockHelp">
            Enter this account's sign-in to continue.
        </p>
        <input id="profileUnlockCredential" type="password"
               maxlength="64" autocomplete="current-password"
               aria-label="Account sign-in" placeholder="PIN or password">
        <div id="profileUnlockError" class="profile-lock-error"
             aria-live="polite"></div>
        <div class="profile-lock-modal-actions">
            <button type="button" class="tool"
                    onclick="closeProfileUnlock(false)">Cancel</button>
            <button type="submit" class="tool">Unlock</button>
        </div>
    </form>
</div>

<script>
const input = document.getElementById("input");
const messages = document.getElementById("messages");
const statusBox = document.getElementById("status");
const activeProfileSelect = document.getElementById("activeProfile");
let activeProfile =
    localStorage.getItem("Doshie_active_profile") || "Hermes";
let activeChatSpace =
    localStorage.getItem("Doshie_chat_space") === "mansion"
        ? "mansion"
        : "main";
let searchMode = "web";
let voiceDestination = "chat";
let profileCatalog = [];
let pendingUnlockProfile = "";
let profileUnlockResolver = null;
let chosenProfileAccent = "mint";
let newsItems = [];
let newsIndex = 0;
let newsPaused = false;
let loadedNewsTopic = "";
let profileAutoLockTimer = null;
let profileAutoLockBusy = false;

const PROFILE_ACCENTS = {
    mint: "#83d69b", forest: "#5f9d76", teal: "#62b9ad",
    blue: "#6f9ed6", purple: "#9b78c6", rose: "#ce7893",
    orange: "#dc8b61", amber: "#dfb45f"
};
const PROFILE_FONTS = {
    system: "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    tech: "'Trebuchet MS', 'Segoe UI', sans-serif",
    mono: "ui-monospace, 'Cascadia Code', 'SFMono-Regular', Consolas, monospace",
    compact: "'Arial Narrow', 'Roboto Condensed', Arial, sans-serif",
    classic: "Georgia, 'Times New Roman', serif"
};
const PROFILE_DEFAULTS = {
    status: "", about_me: "", interests: "", profile_music_url: "", custom_css: "", accent: "mint", accent_hex: "#83d69b",
    theme: "forest", custom_color: "#31f6ff", font_family: "tech",
    font_size: 100, auto_lock_minutes: 5, lock_on_close: true,
    news_topic: "local", news_visible: true
};
const NEWS_TOPICS = ["local", "national", "tech", "gaming", "family"];

function profileRecord(name) {
    return profileCatalog.find(
        item => item.name.toLowerCase() === String(name || "").toLowerCase()
    );
}

function setAvatarDisplay(image, initials, profile) {
    if (!image || !initials) return;
    initials.textContent = (profile && profile.initials) || "Y";
    if (profile && profile.avatar_url) {
        image.src = profile.avatar_url;
        image.hidden = false;
        initials.hidden = true;
    } else {
        image.removeAttribute("src");
        image.hidden = true;
        initials.hidden = false;
    }
}


function profileSecurityLabel(profile) {
    if (!profile || !profile.locked) return "No password";
    return profile.auth_type === "password" ? "Password" : "PIN";
}


function profilePreferences(record) {
    const saved = record && record.preferences ? record.preferences : {};
    const preferences = Object.assign({}, PROFILE_DEFAULTS, saved);
    preferences.accent_hex =
        PROFILE_ACCENTS[preferences.accent] || PROFILE_DEFAULTS.accent_hex;
    return preferences;
}


function updateNewsMotionMetrics() {
    const marquee = document.getElementById("newsMarquee");
    const track = document.getElementById("newsTrack");
    if (!marquee || !track) return;
    const travel = Math.max(240, marquee.clientWidth);
    const distance = travel + Math.max(240, track.scrollWidth);
    const duration = Math.max(14, Math.min(40, distance / 55));
    track.style.setProperty("--news-travel", travel + "px");
    track.style.setProperty("--news-duration", duration.toFixed(1) + "s");
}


function renderNewsHeadline() {
    const headline = document.getElementById("newsHeadline");
    const source = document.getElementById("newsSource");
    if (!headline || !source) return;

    if (!newsItems.length) {
        headline.textContent = "News is temporarily unavailable.";
        headline.removeAttribute("href");
        source.textContent = "";
        window.requestAnimationFrame(updateNewsMotionMetrics);
        return;
    }

    newsIndex = ((newsIndex % newsItems.length) + newsItems.length) % newsItems.length;
    const item = newsItems[newsIndex];
    headline.textContent = item.title || "Open headline";
    headline.href = item.url;
    source.textContent = item.source || "";
    window.requestAnimationFrame(updateNewsMotionMetrics);
}


function startNewsRotation() {
    const track = document.getElementById("newsTrack");
    if (!track) return;
    if (track.dataset.motionReady !== "yes") {
        track.dataset.motionReady = "yes";
        track.addEventListener("animationiteration", () => {
            if (newsPaused || newsItems.length < 2) return;
            newsIndex = (newsIndex + 1) % newsItems.length;
            renderNewsHeadline();
        });
        window.addEventListener("resize", updateNewsMotionMetrics, {passive: true});
    }
    track.style.animation = "none";
    void track.offsetWidth;
    track.style.animation = "";
    updateNewsMotionMetrics();
}


async function loadNews(force = false) {
    const record = profileRecord(activeProfile);
    const preferences = profilePreferences(record);
    const topic = preferences.news_topic || "local";
    const banner = document.getElementById("newsBanner");
    if (!banner || !preferences.news_visible) return;

    const topicButton = document.getElementById("newsTopicButton");
    topicButton.textContent =
        topic === "local" ? "LOCAL · EL PASO" : topic.toUpperCase();
    topicButton.dataset.shortLabel =
        topic === "local" ? "EL PASO" : topic.toUpperCase().slice(0, 8);
    try {
        const response = await fetch(
            "/news?topic=" + encodeURIComponent(topic) +
            (force ? "&refresh=1" : "")
        );
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "News unavailable.");
        newsItems = Array.isArray(data.items) ? data.items : [];
        newsIndex = 0;
        loadedNewsTopic = topic;
        renderNewsHeadline();
        startNewsRotation();
    } catch (error) {
        newsItems = [];
        renderNewsHeadline();
    }
}


function cycleNewsTopic() {
    const record = profileRecord(activeProfile);
    if (!record) return;
    const preferences = profilePreferences(record);
    const index = NEWS_TOPICS.indexOf(preferences.news_topic);
    preferences.news_topic = NEWS_TOPICS[(index + 1) % NEWS_TOPICS.length];
    record.preferences = preferences;
    loadedNewsTopic = "";
    applyProfileExperience(record);
}


function stepNews(direction) {
    if (!newsItems.length) return;
    newsIndex = (newsIndex + direction + newsItems.length) % newsItems.length;
    renderNewsHeadline();
    startNewsRotation();
}


function toggleNewsPause() {
    newsPaused = !newsPaused;
    const banner = document.getElementById("newsBanner");
    const button = document.getElementById("newsPauseButton");
    if (banner) banner.classList.toggle("news-paused", newsPaused);
    button.textContent = newsPaused ? "▶" : "Ⅱ";
    button.setAttribute(
        "aria-label",
        newsPaused ? "Resume headlines" : "Pause headlines"
    );
}


function focusNewsBanner() {
    const banner = document.getElementById("newsBanner");
    if (!banner) return;
    banner.hidden = false;
    banner.scrollIntoView({behavior: "smooth", block: "start"});
    banner.classList.add("news-highlight");
    window.setTimeout(() => banner.classList.remove("news-highlight"), 1200);
    if (!newsItems.length) loadNews();
}


function renderAccountChooser() {
    const grid = document.getElementById("accountGrid");
    if (!grid) return;
    grid.innerHTML = "";

    profileCatalog.forEach(profile => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "account-card";
        button.addEventListener("click", () => signIntoProfile(profile.name));

        const avatar = document.createElement("span");
        avatar.className = "account-avatar";
        const image = document.createElement("img");
        image.alt = "";
        const initials = document.createElement("span");
        avatar.append(image, initials);
        setAvatarDisplay(image, initials, profile);

        const name = document.createElement("strong");
        name.textContent = profile.name;
        const role = document.createElement("span");
        role.className = "account-role";
        role.textContent = profile.role || "Family";
        const preferences = profilePreferences(profile);
        const profileStatus = document.createElement("span");
        profileStatus.className = "account-status";
        profileStatus.textContent = preferences.status || "Available";
        const security = document.createElement("span");
        security.className = "account-security";
        security.textContent =
            (profile.locked && !profile.unlocked ? "🔒 " : "") +
            profileSecurityLabel(profile);

        button.append(avatar, name, role, profileStatus, security);
        grid.appendChild(button);
    });
}


function clearProfileAutoLock() {
    if (profileAutoLockTimer) window.clearTimeout(profileAutoLockTimer);
    profileAutoLockTimer = null;
}


function armProfileAutoLock() {
    clearProfileAutoLock();
    const record = profileRecord(activeProfile);
    if (
        !record || !record.locked || !record.unlocked ||
        sessionStorage.getItem("Doshie_signed_in_profile") !== record.name
    ) return;

    const minutes = Number(profilePreferences(record).auto_lock_minutes);
    if (!minutes) return;
    profileAutoLockTimer = window.setTimeout(
        () => autoLockActiveProfile("inactivity"),
        minutes * 60 * 1000
    );
}


async function autoLockActiveProfile(reason = "inactivity") {
    if (profileAutoLockBusy) return;
    const record = profileRecord(activeProfile);
    if (!record || !record.locked || !record.unlocked) return;

    profileAutoLockBusy = true;
    clearProfileAutoLock();
    try {
        await profileLockApi("/profile-lock/lock", {profile: record.name});
        record.unlocked = false;
        bringLockedProfileForward(
            record.name,
            reason === "inactivity"
                ? "Account locked after inactivity."
                : "Account locked."
        );
    } catch (error) {
        statusBox.textContent = error.message;
        armProfileAutoLock();
    } finally {
        profileAutoLockBusy = false;
    }
}


function setAdminCustomCss(css) {
    let style = document.getElementById("adminCustomCss");
    if (!style) {
        style = document.createElement("style");
        style.id = "adminCustomCss";
        document.head.appendChild(style);
    }
    style.textContent = String(css || "");
}

function previewAdminCustomCss() {
    const field = document.getElementById("profileCustomCss");
    if (field && !field.disabled) setAdminCustomCss(field.value);
}

function resetAdminCustomCss() {
    const field = document.getElementById("profileCustomCss");
    if (!field || field.disabled) return;
    field.value = "";
    setAdminCustomCss("");
}

function applyAdminThemePreset(name) {
    const field = document.getElementById("profileCustomCss");
    if (!field || field.disabled) return;
    const presets = {
        "dark-red": `
:root {
  --profile-accent: #ff294d;
  --page: #060204;
  --surface: #120509;
  --surface-soft: #1d080e;
  --surface-hover: #310c16;
  --text: #fff4f6;
  --muted: #c9a7af;
  --line: #7a101f;
}
body { background: #060204 !important; }
.header, .sidebar, .input-area, .settings-group > summary {
  background: linear-gradient(180deg, #21070d, #0c0306) !important;
}
.message, .admin-card, .settings-body {
  border-color: #7a101f !important;
  box-shadow: 0 0 16px rgba(180, 12, 38, .24);
}
`,
        "deep-red": `
:root {
  --profile-accent: #c81432;
  --page: #040102;
  --surface: #0d0305;
  --surface-soft: #160509;
  --surface-hover: #260810;
  --text: #fbeff2;
  --muted: #b58f98;
  --line: #5e0b18;
}
body, .app { background: #040102 !important; }
button, input, select, textarea { border-color: #5e0b18 !important; }
`
    };
    field.value = presets[name] || "";
    previewAdminCustomCss();
    document.getElementById("profilePreferenceStatus").textContent =
        "Preset previewed. Tap Save profile style to keep it.";
}

function applyProfileExperience(record) {
    if (!record) return;
    const preferences = profilePreferences(record);
    const adminRecord = profileCatalog.find(item => item.is_admin);
    const adminPreferences = adminRecord ? profilePreferences(adminRecord) : null;
    setAdminCustomCss(adminPreferences ? adminPreferences.custom_css : "");
    document.body.dataset.profileTheme = preferences.theme;
    document.documentElement.style.setProperty(
        "--profile-accent",
        preferences.accent_hex
    );
    const tronTheme = preferences.theme === "tron";
    document.documentElement.style.setProperty(
        "--profile-font-family",
        tronTheme
            ? (PROFILE_FONTS[preferences.font_family] || PROFILE_FONTS.tech)
            : PROFILE_FONTS.system
    );
    document.documentElement.style.setProperty(
        "--profile-font-scale",
        tronTheme ? String(preferences.font_size / 100) : "1"
    );
    document.body.classList.toggle("tron-interface", tronTheme);
    const themeMeta = document.querySelector('meta[name="theme-color"]');
    if (themeMeta) themeMeta.content = preferences.accent_hex;

    const banner = document.getElementById("newsBanner");
    document.body.classList.toggle("news-hidden", !preferences.news_visible);
    if (banner) banner.hidden = !preferences.news_visible;
    if (preferences.news_visible && loadedNewsTopic !== preferences.news_topic) {
        loadNews();
    }
    armProfileAutoLock();
}


function showAccountChooser() {
    const usernameField = document.getElementById("publicSignInUsername");
    if (usernameField) usernameField.value = "";
    renderAccountChooser();
    document.getElementById("accountChooser").hidden = false;
    setProfileInteraction(false);
    closeSidebar();
}


function hideAccountChooser() {
    document.getElementById("accountChooser").hidden = true;
}


function setProfileInteraction(enabled) {
    input.disabled = !enabled;
    document.querySelectorAll(".send, .composer-voice").forEach(button => {
        button.disabled = !enabled;
    });
}

function showLockedProfileState(profile) {
    messages.innerHTML = "";
    addMessage(
        profile.split(" ")[0] +
        "'s account is locked. Sign in to view private chats and memories.",
        "Doshie"
    );
    setProfileInteraction(false);
}

function bringLockedProfileForward(profile, message) {
    const record = profileRecord(profile);
    if (!record || !record.locked || record.unlocked) return;
    sessionStorage.removeItem("Doshie_signed_in_profile");
    showLockedProfileState(record.name);
    showAccountChooser();
    renderProfileSelectors();
    if (message) statusBox.textContent = message;
    const chooser = document.getElementById("accountChooser");
    if (chooser) chooser.scrollIntoView({behavior: "smooth", block: "start"});
}

function renderProfileSelectors() {
    const lockTarget = document.getElementById("profileLockTarget");
    const inviteTarget = document.getElementById("familyInviteTarget");
    const lockTargetValue =
        lockTarget && lockTarget.value ? lockTarget.value : activeProfile;
    activeProfileSelect.innerHTML = "";
    if (lockTarget) lockTarget.innerHTML = "";
    if (inviteTarget) inviteTarget.innerHTML = "";

    profileCatalog.forEach(profile => {
        const marker = profile.locked
            ? (profile.unlocked ? "🔓 " : "🔒 ")
            : "";
        const label = marker + profile.name.split(" ")[0];
        const option = document.createElement("option");
        option.value = profile.name;
        option.textContent = label;
        option.title = profile.name + " — " + profile.role;
        activeProfileSelect.appendChild(option);

        if (lockTarget) {
            const lockOption = option.cloneNode(true);
            lockTarget.appendChild(lockOption);
        }
        if (inviteTarget && profile.name !== activeProfile) {
            const inviteOption = option.cloneNode(true);
            inviteTarget.appendChild(inviteOption);
        }
    });

    activeProfileSelect.value = activeProfile;
    if (lockTarget) {
        lockTarget.value = profileRecord(lockTargetValue)
            ? lockTargetValue
            : activeProfile;
    }
    const selected = profileRecord(activeProfile);
    document.body.classList.toggle(
        "child-mode", Boolean(selected && selected.is_child)
    );
    const profileSwitcher = document.getElementById("profileSwitcher");
    if (profileSwitcher) {
        profileSwitcher.hidden = !Boolean(selected && selected.is_admin);
    }
    const adminControlButton = document.getElementById("adminControlButton");
    if (adminControlButton) {
        adminControlButton.hidden = !Boolean(selected && selected.is_admin);
    }
    const hermesWorkspaceButton = document.getElementById("hermesWorkspaceButton");
    if (hermesWorkspaceButton) {
        hermesWorkspaceButton.hidden = !Boolean(selected && selected.is_admin);
    }
    document.querySelectorAll(".builder-side-action, .builder-launch").forEach(button => {
        button.hidden = !Boolean(selected && selected.is_admin);
    });
    const inviteAdmin = document.getElementById("familyInviteAdmin");
    if (inviteAdmin) {
        inviteAdmin.hidden = !Boolean(selected && selected.is_admin);
    }
    loadChatPreferences();
    setAvatarDisplay(
        document.getElementById("activeProfileAvatar"),
        document.getElementById("activeProfileInitials"),
        selected
    );
    renderAccountChooser();
    refreshProfileLockControls();
}

function toggleSidebar() {
    if (document.body.classList.contains("control-app")) {
        document.body.classList.toggle("sidebar-open");
        return;
    }
    if (window.matchMedia("(min-width: 900px)").matches) {
        const collapsed = !document.body.classList.contains("sidebar-collapsed");
        document.body.classList.toggle("sidebar-collapsed", collapsed);
        localStorage.setItem("Doshie_sidebar_collapsed", String(collapsed));
        syncSidebarToggleLabel();
        return;
    }
    document.body.classList.toggle("sidebar-open");
}

function closeSidebar() {
    document.body.classList.remove("sidebar-open");
}

function syncSidebarToggleLabel() {
    const button = document.getElementById("sidebarToggle");
    if (!button) return;
    const collapsed = document.body.classList.contains("sidebar-collapsed");
    const label = collapsed ? "Expand sidebar" : "Collapse sidebar";
    button.setAttribute("aria-label", label);
    button.title = label;
}

const savedSidebarCollapsed = localStorage.getItem("Doshie_sidebar_collapsed");
if (savedSidebarCollapsed !== "false") {
    document.body.classList.add("sidebar-collapsed");
}
syncSidebarToggleLabel();

async function profileLockApi(path, payload) {
    const response = await fetch(path, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload || {})
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const error = new Error(data.error || "Profile lock request failed.");
        error.status = response.status;
        error.retryAfter = data.retry_after;
        throw error;
    }
    return data;
}

function openProfileUnlock(profile) {
    const record = profileRecord(profile);
    if (!record || !record.locked || record.unlocked) {
        return Promise.resolve(true);
    }

    if (profileUnlockResolver) closeProfileUnlock(false);
    pendingUnlockProfile = record.name;
    document.getElementById("profileUnlockTitle").textContent =
        "Unlock " + record.name.split(" ")[0];
    const credentialInput =
        document.getElementById("profileUnlockCredential");
    const isPin = record.auth_type !== "password";
    document.getElementById("profileUnlockHelp").textContent =
        "Enter " + record.name.split(" ")[0] + "'s " +
        (isPin ? "private PIN." : "private password.");
    credentialInput.inputMode = isPin ? "numeric" : "text";
    credentialInput.maxLength = isPin ? 8 : 64;
    credentialInput.placeholder = isPin ? "PIN" : "Password";
    credentialInput.value = "";
    document.getElementById("profileUnlockError").textContent = "";
    document.getElementById("profileUnlockModal").hidden = false;

    return new Promise(resolve => {
        profileUnlockResolver = resolve;
        setTimeout(() => {
            document.getElementById("profileUnlockCredential").focus();
        }, 0);
    });
}

function closeProfileUnlock(result) {
    const resolver = profileUnlockResolver;
    profileUnlockResolver = null;
    pendingUnlockProfile = "";
    document.getElementById("profileUnlockModal").hidden = true;
    document.getElementById("profileUnlockCredential").value = "";
    document.getElementById("profileUnlockError").textContent = "";
    if (resolver) resolver(Boolean(result));
}

async function submitProfileUnlock(event) {
    event.preventDefault();
    const errorBox = document.getElementById("profileUnlockError");
    const credential =
        document.getElementById("profileUnlockCredential").value;
    errorBox.textContent = "";

    try {
        await profileLockApi("/profile-lock/unlock", {
            profile: pendingUnlockProfile,
            credential
        });
        const record = profileRecord(pendingUnlockProfile);
        if (record) record.unlocked = true;
        setProfileInteraction(true);
        renderProfileSelectors();
        closeProfileUnlock(true);
    } catch (error) {
        errorBox.textContent = error.retryAfter
            ? error.message + " Try again in " + error.retryAfter + " seconds."
            : error.message;
        document.getElementById("profileUnlockCredential").select();
    }
}

let DoshieSettings = {
    auto_memory: true,
    speak_replies: false,
    default_weather_location: "El Paso"
};
let conversationEpoch = 0;
const activeChatRequests = new Set();
let pendingChatAttachments = [];


function activeProfileFirstName() {
    return (activeProfile || "Hermes").split(" ")[0];
}


function setSideView(view) {
    document.querySelectorAll("[data-side-view]").forEach(button => {
        button.classList.toggle("active", button.dataset.sideView === view);
    });
}


function syncRoomHeader() {
    const mansion = activeChatSpace === "mansion";
    document.getElementById("appRoomTitle").textContent =
        mansion ? "🏰 Mansion Doshie" : "🦖 Doshie";
    input.placeholder = mansion
        ? "Build Doshie's final home…"
        : "Message Doshie…";
    setSideView(mansion ? "mansion" : "chat");
}


function renderMansionRoomBanner() {
    const banner = document.createElement("section");
    banner.className = "mansion-room-banner";
    banner.innerHTML = `
        <small>PRIVATE BUILD ROOM</small>
        <h2>🏰 Mansion Doshie</h2>
        <p>Our dedicated workspace for building Doshie's final home.</p>
        <div class="mansion-roadmap">
            <button data-mansion-area="brain">🧠 Brain</button>
            <button data-mansion-area="desktop">🖥️ Desktop</button>
            <button data-mansion-area="watch">⌚ Watch</button>
            <button data-mansion-area="home">🏠 Smart home</button>
            <button data-mansion-area="security">🛡️ Security</button>
            <button data-mansion-area="backup">💾 Backups</button>
        </div>
    `;
    banner.querySelectorAll("[data-mansion-area]").forEach(button => {
        button.addEventListener("click", () => {
            mansionPrompt(button.dataset.mansionArea);
        });
    });
    messages.appendChild(banner);
}


function mansionPrompt(area) {
    const prompts = {
        brain: "Help me plan the next dependable brain upgrade for Doshie.",
        desktop: "Help me build Doshie's final desktop application.",
        watch: "Help me build Doshie's Wear OS watch application.",
        home: "Help me plan Doshie's safe smart-home integration.",
        security: "Review Mansion Doshie's security and permission boundaries.",
        backup: "Review Doshie's backup, recovery, and rollback plan."
    };
    input.value = prompts[area] || "";
    input.focus({preventScroll: true});
}


async function openChatSpace(space) {
    activeChatSpace = space === "mansion" ? "mansion" : "main";
    localStorage.setItem("Doshie_chat_space", activeChatSpace);
    conversationEpoch += 1;
    activeChatRequests.forEach(controller => controller.abort());
    if (window.showChatHome) window.showChatHome();
    syncRoomHeader();
    await loadProfileHistory();
}


function showProfileGreeting() {
    messages.innerHTML = "";
    if (activeChatSpace === "mansion") {
        renderMansionRoomBanner();
        addMessage(
            "Welcome home, " + activeProfileFirstName() +
            ". This conversation stays separate from your regular Doshie chat.",
            "Doshie"
        );
        return;
    }
    addMessage(
        "Hi " + activeProfileFirstName() + ". What can I help with?",
        "Doshie"
    );
}


async function loadProfileHistory() {
    try {
        const response = await fetch(
            "/chat-history?profile=" +
            encodeURIComponent(activeProfile) +
            "&space=" + encodeURIComponent(activeChatSpace)
        );
        const data = await response.json();

        if (response.status === 423) {
            showLockedProfileState(activeProfile);
            return false;
        }
        if (!response.ok || !Array.isArray(data.history)) {
            throw new Error("Could not load profile history.");
        }

        setProfileInteraction(true);
        messages.innerHTML = "";
        if (activeChatSpace === "mansion" && data.history.length) {
            renderMansionRoomBanner();
        }
        if (!data.history.length) {
            showProfileGreeting();
            return true;
        }

        data.history.forEach(item => {
            if (item.role === "user") addMessage(item.content, "user");
            if (item.role === "assistant") addMessage(item.content, "Doshie");
        });
        return true;
    } catch (error) {
        setProfileInteraction(true);
        showProfileGreeting();
        return false;
    }
}


async function signInPublicAccount(event) {
    event.preventDefault();
    const username = document.getElementById("publicSignInUsername").value.trim();
    const credential = document.getElementById("publicSignInCredential").value;
    const status = document.getElementById("publicSignInStatus");
    if (!username || !credential) return;
    status.textContent = "Signing in securely...";
    try {
        const response = await fetch("/family-login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({username, credential})
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const error = new Error(data.error || "Sign in failed.");
            error.retryAfter = data.retry_after;
            throw error;
        }
        await refreshProfileCatalog();
        status.textContent = "Signed in. Loading your private account...";
        await signIntoProfile(data.profile);
    } catch (error) {
        status.textContent = error.retryAfter
            ? error.message + " Try again in " + error.retryAfter + " seconds."
            : error.message;
        document.getElementById("publicSignInCredential").select();
    }
}


async function claimFamilyInvite(event, suppliedToken = "") {
    if (event) event.preventDefault();
    const input = document.getElementById("familyInviteToken");
    const status = document.getElementById("familyInviteClaimStatus");
    const token = String(suppliedToken || (input ? input.value : "")).trim();
    if (!token) return;

    status.textContent = "Checking invitation...";
    try {
        const response = await fetch("/family-invites/claim", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({token})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Invitation failed.");
        window.history.replaceState({}, "", window.location.pathname);
        await refreshProfileCatalog();
        status.textContent = "Invitation accepted. Sign in to continue.";
        await signIntoProfile(data.profile);
    } catch (error) {
        status.textContent = error.message;
        if (input) input.select();
    }
}


async function createFamilyInvite() {
    const target = document.getElementById("familyInviteTarget").value;
    const status = document.getElementById("familyInviteAdminStatus");
    const output = document.getElementById("familyInviteUrl");
    if (!target) {
        status.textContent = "Choose a family account.";
        return;
    }
    status.textContent = "Creating secure invitation...";
    try {
        const response = await fetch("/family-invites", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                profile: activeProfile,
                target_profile: target
            })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not create invitation.");
        output.value = data.url;
        status.textContent =
            "One-time invitation created. It expires in seven days.";
        output.focus();
        output.select();
    } catch (error) {
        status.textContent = error.message;
    }
}


async function copyFamilyInvite() {
    const output = document.getElementById("familyInviteUrl");
    const status = document.getElementById("familyInviteAdminStatus");
    if (!output.value) {
        status.textContent = "Create an invitation first.";
        return;
    }
    try {
        await navigator.clipboard.writeText(output.value);
        status.textContent = "Invitation link copied.";
    } catch (error) {
        output.focus();
        output.select();
        status.textContent = "Press Ctrl+C to copy the selected link.";
    }
}


async function refreshProfileCatalog() {
    const response = await fetch("/profiles");
    const profiles = await response.json();
    if (!response.ok || !Array.isArray(profiles)) {
        throw new Error("Could not load profiles.");
    }
    profileCatalog = profiles;
    const publicSignInPanel = document.getElementById("publicSignInPanel");
    const invitePanel = document.getElementById("inviteAccessPanel");
    if (publicSignInPanel) publicSignInPanel.hidden = profiles.length !== 0;
    if (invitePanel) invitePanel.hidden = profiles.length !== 0;
    if (!profiles.length) {
        renderAccountChooser();
        return profiles;
    }
    if (!profileRecord(activeProfile)) activeProfile = profiles[0].name;
    renderProfileSelectors();
    return profiles;
}


async function loadProfiles() {
    try {
        const invitation = new URLSearchParams(window.location.search).get("invite");
        if (invitation) {
            await claimFamilyInvite(null, invitation);
            return;
        }
        await refreshProfileCatalog();
        const signedIn =
            sessionStorage.getItem("Doshie_signed_in_profile") || "";
        const signedInRecord = profileRecord(signedIn);
        if (!signedInRecord) {
            sessionStorage.removeItem("Doshie_signed_in_profile");
            showAccountChooser();
            return;
        }

        activeProfile = signedInRecord.name;
        renderProfileSelectors();
        if (signedInRecord.locked && !signedInRecord.unlocked) {
            sessionStorage.removeItem("Doshie_signed_in_profile");
            showAccountChooser();
            return;
        }

        localStorage.setItem("Doshie_active_profile", activeProfile);
        hideAccountChooser();
        applyProfileExperience(signedInRecord);
        syncRoomHeader();
        await loadProfileHistory();
    } catch (error) {
        sessionStorage.removeItem("Doshie_signed_in_profile");
        showAccountChooser();
    }
}


async function signIntoProfile(profileName) {
    const record = profileRecord(profileName);
    if (!record) return false;

    if (record.locked && !record.unlocked) {
        const unlocked = await openProfileUnlock(record.name);
        if (!unlocked) {
            renderProfileSelectors();
            return false;
        }
        record.unlocked = true;
    }

    const previousName =
        sessionStorage.getItem("Doshie_signed_in_profile") || "";
    const previous = profileRecord(previousName);
    if (
        previous &&
        previous.name !== record.name &&
        previous.locked &&
        previous.unlocked
    ) {
        try {
            await profileLockApi("/profile-lock/lock", {
                profile: previous.name
            });
            previous.unlocked = false;
        } catch (error) {
            statusBox.textContent = error.message;
            return false;
        }
    }

    conversationEpoch += 1;
    activeChatRequests.forEach(controller => controller.abort());
    activeProfile = record.name;
    localStorage.setItem("Doshie_active_profile", activeProfile);
    sessionStorage.setItem("Doshie_signed_in_profile", activeProfile);
    renderProfileSelectors();
    hideAccountChooser();
    closeSidebar();
    applyProfileExperience(record);
    if (window.showChatHome) window.showChatHome();
    syncRoomHeader();
    await loadProfileHistory();
    await openRequestedStartView();
    return true;
}


async function signOutProfile() {
    const record = profileRecord(activeProfile);
    try {
        if (record && record.locked && record.unlocked) {
            await profileLockApi("/profile-lock/lock", {
                profile: record.name
            });
            record.unlocked = false;
        }
    } catch (error) {
        statusBox.textContent = error.message;
        return;
    }

    conversationEpoch += 1;
    activeChatRequests.forEach(controller => controller.abort());
    clearProfileAutoLock();
    sessionStorage.removeItem("Doshie_signed_in_profile");
    messages.innerHTML = "";
    showAccountChooser();
    statusBox.textContent = "Choose an account to continue.";
}


async function switchProfile() {
    const previousProfile = activeProfile;
    const requestedProfile = activeProfileSelect.value || "Hermes";
    const signedIn = await signIntoProfile(requestedProfile);
    if (!signedIn) {
        activeProfileSelect.value = previousProfile;
        return;
    }

    statusBox.textContent =
        "Signed in as " + activeProfileFirstName() + ".";
    setTimeout(() => {
        if (statusBox.textContent.startsWith("Signed in as")) {
            statusBox.textContent = "";
        }
    }, 1500);
}


function isDirectGifUrl(value) {
    try {
        const url = new URL(value);
        return (
            (url.protocol === "https:" || url.protocol === "http:") &&
            /\\.gif$/i.test(url.pathname)
        );
    } catch (error) {
        return false;
    }
}


function splitMessageGifs(value) {
    let visibleText = String(value || "");
    const gifs = [];

    visibleText = visibleText.replace(
        /!\\[[^\\]]*\\]\\((https?:\\/\\/[^\\s)]+)\\)/gi,
        (full, url) => {
            if (!isDirectGifUrl(url)) return full;
            gifs.push(url);
            return "";
        }
    );

    visibleText = visibleText.replace(
        /https?:\\/\\/[^\\s<>()]+/gi,
        rawUrl => {
            const url = rawUrl.replace(/[.,!?;:]+$/, "");
            if (!isDirectGifUrl(url)) return rawUrl;
            gifs.push(url);
            return rawUrl.slice(url.length);
        }
    );

    return {
        text: visibleText.replace(/\\n{3,}/g, "\\n\\n").trim(),
        gifs: [...new Set(gifs)]
    };
}


function appendLinkedText(container, value) {
    const text = String(value || "");
    const pattern = /https?:\\/\\/[^\\s<>()]+/gi;
    let cursor = 0;
    let match;

    while ((match = pattern.exec(text)) !== null) {
        if (match.index > cursor) {
            container.appendChild(
                document.createTextNode(text.slice(cursor, match.index))
            );
        }
        let url = match[0];
        while (url && ".,!?;:)>]}".includes(url.slice(-1))) {
            url = url.slice(0, -1);
        }
        const anchor = document.createElement("a");
        anchor.className = "chat-link";
        anchor.href = url;
        anchor.target = "_blank";
        anchor.rel = "noopener noreferrer";
        anchor.textContent = url;
        container.appendChild(anchor);
        if (url.length < match[0].length) {
            container.appendChild(
                document.createTextNode(match[0].slice(url.length))
            );
        }
        cursor = match.index + match[0].length;
    }

    if (cursor < text.length) {
        container.appendChild(document.createTextNode(text.slice(cursor)));
    }
}


function isLookupRequest(value) {
    return /\b(search|look up|lookup|find online|where (?:can|do) i (?:find|buy)|latest|news about)\b/i
        .test(String(value || ""));
}


function addLookupLinks(container, query, sources) {
    const rows = Array.isArray(sources) ? sources : [];
    const links = [];
    rows.forEach(source => {
        if (!source || !source.url) return;
        try {
            const url = new URL(source.url);
            if (!["http:", "https:"].includes(url.protocol)) return;
            links.push({
                label: String(source.title || source.source || url.hostname),
                url: url.href
            });
        } catch (error) {
            // Ignore unsafe or incomplete source URLs.
        }
    });

    if (!links.length && isLookupRequest(query)) {
        const encoded = encodeURIComponent(String(query || "").slice(0, 500));
        links.push(
            {label: "Google", url: "https://www.google.com/search?q=" + encoded},
            {label: "DuckDuckGo", url: "https://duckduckgo.com/?q=" + encoded}
        );
    }
    if (!links.length) return;

    const row = document.createElement("div");
    row.className = "message-links";
    const label = document.createElement("span");
    label.textContent = rows.length ? "Sources" : "Search links";
    row.appendChild(label);
    links.slice(0, 5).forEach(item => {
        const anchor = document.createElement("a");
        anchor.href = item.url;
        anchor.target = "_blank";
        anchor.rel = "noopener noreferrer";
        anchor.textContent = item.label;
        row.appendChild(anchor);
    });
    container.appendChild(row);
}


function speakableReply(value) {
    return String(value || "")
        .replace(/!\\[[^\\]]*\\]\\(https?:\\/\\/[^\\s)]+\\)/gi, "")
        .replace(/https?:\\/\\/[^\\s<>()]+/gi, "")
        .replace(/\\s{2,}/g, " ")
        .trim();
}


function appendMarkdown(container, value) {
    let html = String(value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    html = html.replace(/^###\\s+(.+)$/gm, '<h3>$1</h3>').replace(/^##\\s+(.+)$/gm, '<h2>$1</h2>').replace(/^#\\s+(.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^[-*]\\s+(.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\\/li>)/gs, '<ul class=\"message-list\">$1</ul>');
    html = html.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>').replace(/(^|[^*])\\*([^*]+)\\*/g, '$1<em>$2</em>');
    html = html.replace(/```[a-zA-Z0-9_-]*\\n?([\\s\\S]*?)```/g, '<pre class=\"message-code-block\"><code>$1</code></pre>');
    html = html.split('\\n').map(line => line.match(/^<(h[23]|ul|pre)/) ? line : (line ? '<p>' + line + '</p>' : '<br>')).join('');
    container.innerHTML = html;
}


function addMessage(text, who) {
    const div = document.createElement("div");
    div.className = "message " + who;

    if (who === "Doshie") {
        const content = splitMessageGifs(text);

        if (content.text) {
            const copy = document.createElement("span");
            copy.className = "message-text";
            appendMarkdown(copy, content.text);
            div.appendChild(copy);
        }

        content.gifs.forEach(url => {
            const gif = document.createElement("img");
            gif.className = "chat-gif";
            gif.src = url;
            gif.alt = "Animated GIF";
            gif.loading = "lazy";
            div.appendChild(gif);
        });

        if (!content.text && !content.gifs.length) {
            div.textContent = text;
        }
    } else {
        div.textContent = text;
    }

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
}


const CHAT_MODES = new Set([
    "general", "tech", "ai_tutor", "coding", "gaming"
]);
const ADMIN_BRAIN_MODES = new Set([
    "auto", "fast", "balanced", "coding", "advanced", "vision"
]);
const MEMBER_BRAIN_MODES = new Set(["auto", "balanced"]);
const CHAT_TEXT_SIZES = new Set(["small", "normal", "large"]);
const CHAT_BUBBLE_WIDTHS = new Set(["comfortable", "wide", "full"]);
const CHAT_SPACINGS = new Set(["compact", "normal", "roomy"]);


function chatPreferenceKey(name) {
    return "Doshie-chat-" + String(activeProfile || "Hermes").toLowerCase()
        .replace(/[^a-z0-9]+/g, "-");
}


function loadChatPreferences() {
    let saved = {};
    try {
        saved = JSON.parse(localStorage.getItem(chatPreferenceKey()) || "{}");
    } catch (error) {
        saved = {};
    }

    const mode = CHAT_MODES.has(saved.mode) ? saved.mode : "general";
    const record = profileRecord(activeProfile);
    const isAdmin = Boolean(record && record.is_admin);
    const allowedBrains = isAdmin ? ADMIN_BRAIN_MODES : MEMBER_BRAIN_MODES;
    const brain = allowedBrains.has(saved.brain) ? saved.brain : "auto";
    const brainSelect = document.getElementById("brainMode");
    brainSelect.querySelectorAll("[data-admin-only]").forEach(option => {
        option.hidden = !isAdmin;
        option.disabled = !isAdmin;
    });
    brainSelect.value = brain;
    const textSize = CHAT_TEXT_SIZES.has(saved.textSize)
        ? saved.textSize : "normal";
    const bubbleWidth = CHAT_BUBBLE_WIDTHS.has(saved.bubbleWidth)
        ? saved.bubbleWidth : "wide";
    const spacing = CHAT_SPACINGS.has(saved.spacing)
        ? saved.spacing : "normal";

    document.getElementById("chatMode").value = mode;
    document.getElementById("chatTextSize").value = textSize;
    document.getElementById("chatBubbleWidth").value = bubbleWidth;
    document.getElementById("chatSpacing").value = spacing;
    document.body.dataset.chatTextSize = textSize;
    document.body.dataset.chatBubbleWidth = bubbleWidth;
    document.body.dataset.chatSpacing = spacing;
}


function saveChatPreferences() {
    const preferences = {
        mode: document.getElementById("chatMode").value,
        brain: document.getElementById("brainMode").value,
        textSize: document.getElementById("chatTextSize").value,
        bubbleWidth: document.getElementById("chatBubbleWidth").value,
        spacing: document.getElementById("chatSpacing").value
    };
    localStorage.setItem(chatPreferenceKey(), JSON.stringify(preferences));
    loadChatPreferences();
}


function saveChatMode() {
    saveChatPreferences();
    const selected = document.getElementById("chatMode");
    statusBox.textContent =
        selected.options[selected.selectedIndex].text + " mode selected.";
    window.setTimeout(() => {
        if (statusBox.textContent.endsWith("mode selected.")) {
            statusBox.textContent = "";
        }
    }, 1400);
}


function saveBrainMode() {
    saveChatPreferences();
    const selected = document.getElementById("brainMode");
    statusBox.textContent =
        selected.options[selected.selectedIndex].text + " brain selected.";
    window.setTimeout(() => {
        if (statusBox.textContent.endsWith("brain selected.")) {
            statusBox.textContent = "";
        }
    }, 1400);
}


function saveChatAppearance() {
    saveChatPreferences();
}


function openChatAttachmentPicker(kind) {
    const input = document.getElementById(
        kind === "camera" ? "chatCameraInput" : "chatFileInput"
    );
    if (input) input.click();
}


function attachmentUrl(item, download=false) {
    const separator = String(item.url || "").includes("?") ? "&" : "?";
    return String(item.url || "") + (download ? separator + "download=1" : "");
}


function appendAttachmentCards(parent, items) {
    if (!parent || !Array.isArray(items) || !items.length) return;
    const list = document.createElement("div");
    list.className = "message-attachments";
    items.forEach(item => {
        const card = document.createElement("a");
        card.className = "message-attachment";
        card.href = attachmentUrl(item, item.kind !== "image");
        card.target = "_blank";
        card.rel = "noopener";
        if (item.kind === "image") {
            const image = document.createElement("img");
            image.src = attachmentUrl(item);
            image.alt = item.name || "Attached photo";
            image.loading = "lazy";
            card.appendChild(image);
        }
        const label = document.createElement("span");
        label.textContent = (item.kind === "image" ? "📷 " : "📄 ")
            + (item.name || "Attachment");
        card.appendChild(label);
        list.appendChild(card);
    });
    parent.appendChild(list);
}


function renderChatAttachmentTray() {
    const tray = document.getElementById("chatAttachmentTray");
    if (!tray) return;
    tray.innerHTML = "";
    pendingChatAttachments.forEach((item, index) => {
        const chip = document.createElement("span");
        chip.className = "chat-attachment-chip";
        const label = document.createElement("span");
        label.textContent = (item.kind === "image" ? "📷 " : "📄 ") + item.name;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.textContent = "×";
        remove.setAttribute("aria-label", "Remove " + item.name);
        remove.onclick = () => {
            pendingChatAttachments.splice(index, 1);
            renderChatAttachmentTray();
        };
        chip.append(label, remove);
        tray.appendChild(chip);
    });
    tray.hidden = pendingChatAttachments.length === 0;
}


async function uploadChatAttachments(event) {
    const inputElement = event.target;
    const files = Array.from(inputElement.files || []);
    inputElement.value = "";
    const available = Math.max(0, 5 - pendingChatAttachments.length);
    if (!files.length || !available) {
        statusBox.textContent = available ? "" : "You can attach up to five items.";
        return;
    }

    statusBox.textContent = "Adding attachment…";
    for (const file of files.slice(0, available)) {
        const form = new FormData();
        form.append("profile", activeProfile);
        form.append("attachment", file, file.name);
        try {
            const response = await fetch(
                "/chat-attachment?profile=" + encodeURIComponent(activeProfile),
                {method: "POST", body: form}
            );
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.error || "Upload failed.");
            pendingChatAttachments.push(data.attachment);
            renderChatAttachmentTray();
        } catch (error) {
            statusBox.textContent = error.message;
            return;
        }
    }
    statusBox.textContent = pendingChatAttachments.length
        ? "Attachment ready. Add a message or tap Send."
        : "";
}


function setThinkingBuddy(state = "idle") {
    const buddy = document.getElementById("thinkingBuddy");
    if (!buddy) return;
    buddy.classList.toggle("thinking", state === "thinking");
    buddy.classList.toggle("happy", state === "happy");
    const label = buddy.querySelector("span");
    if (label) label.textContent = state === "thinking"
        ? "Thinking…" : (state === "happy" ? "Got it!" : "Ready");
    buddy.setAttribute(
        "aria-label",
        "Doshie buddy is " + (state === "thinking" ? "thinking" : "ready")
    );
    if (state === "happy") {
        window.setTimeout(() => {
            if (activeChatRequests.size === 0) setThinkingBuddy("idle");
        }, 1300);
    }
}


async function sendText(text) {

    if (!text.trim() && pendingChatAttachments.length === 0) return;

    const requestEpoch = conversationEpoch;
    const requestProfile = activeProfile;
    const requestSpace = activeChatSpace;
    const requestAttachments = pendingChatAttachments.splice(0);
    renderChatAttachmentTray();
    const controller = new AbortController();
    activeChatRequests.add(controller);
    updateStopThinkingButton();
    const userElement = addMessage(
        text || "Shared attachment" + (requestAttachments.length > 1 ? "s" : ""),
        "user"
    );
    appendAttachmentCards(userElement, requestAttachments);
    statusBox.textContent = "Doshie is thinking...";
    const replyStartedAt = performance.now();

    try {

        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            signal: controller.signal,
            body: JSON.stringify({
                message: text,
                profile: requestProfile,
                space: requestSpace,
                chat_mode: document.getElementById("chatMode").value,
                brain_mode: document.getElementById("brainMode").value,
                attachments: requestAttachments.map(item => item.id)
            })
        });

        const data = await response.json();
        recordReplyMetric(performance.now() - replyStartedAt);

        if (
            requestEpoch !== conversationEpoch ||
            requestProfile !== activeProfile ||
            requestSpace !== activeChatSpace ||
            data.discarded
        ) {
            return;
        }

        const reply = data.reply || data.error || "No response.";

        const replyElement = addMessage(reply, "Doshie");
        if (response.ok) {
            addLookupLinks(replyElement, text, data.sources);
        }

        if (response.ok && DoshieSettings.speak_replies) {
            const spokenReply = speakableReply(reply);
            if (spokenReply) speakDoshieReply(spokenReply);
        }

    } catch (error) {

        if (error.name === "AbortError" || requestEpoch !== conversationEpoch) {
            return;
        }

        addMessage(
            "I couldn't reach Doshie's local server.",
            "Doshie"
        );

    } finally {
        activeChatRequests.delete(controller);
        updateStopThinkingButton();
        if (requestEpoch === conversationEpoch) {
            statusBox.textContent = "";
        }
    }
}



function updateStopThinkingButton() {
    const button = document.getElementById("stopThinkingButton");
    const sendButton = document.querySelector("#composer > .send");
    const thinking = activeChatRequests.size > 0;
    if (button) button.hidden = !thinking;
    if (sendButton) sendButton.hidden = thinking;
    setThinkingBuddy(thinking ? "thinking" : "happy");
}


function stopThinking() {
    if (activeChatRequests.size === 0) return;

    conversationEpoch += 1;
    activeChatRequests.forEach(controller => controller.abort());
    activeChatRequests.clear();
    updateStopThinkingButton();
    statusBox.textContent = "Stopped. Your conversation is still here.";

    window.setTimeout(() => {
        if (activeChatRequests.size === 0) {
            statusBox.textContent = "";
        }
    }, 1800);
}

function send() {

    const text = input.value.trim();

    if (!text && pendingChatAttachments.length === 0) return;

    input.value = "";
    sendText(text);
}


function quick(command) {
    sendText(command);
}


if (input) {
    const quickTaskInput =
    document.getElementById("quickTaskText");

if (quickTaskInput) {
    quickTaskInput.addEventListener(
        "keydown",
        function(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                quickAddTask();
            }
        }
    );
}


const quickShoppingInput =
    document.getElementById("quickShoppingItem");

if (quickShoppingInput) {
    quickShoppingInput.addEventListener(
        "keydown",
        function(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                quickAddShopping();
            }
        }
    );
}


input.addEventListener("keydown", function(event) {

        if (event.key === "Enter") {
            event.preventDefault();
            send();
        }

    });
}


async function checkHealth() {
    const status = document.getElementById("connectionStatus");
    const splash = document.getElementById("splash");
    const splashText = document.getElementById("splashText");

    try {
        const response = await fetch("/health", {
            cache: "no-store"
        });

        const data = await response.json();

        if (data.online === true) {
            status.textContent = "🟢 Doshie Online";

            if (splashText) {
                splashText.textContent = "Doshie is ready.";
            }

            if (splash) {
                splash.style.transition = "opacity 0.35s ease";
                splash.style.opacity = "0";

                setTimeout(() => {
                    splash.style.display = "none";
                }, 350);
            }

            return;
        }

        status.textContent = "🟡 Doshie is waking up...";

        if (splashText) {
            splashText.textContent = "Loading local AI...";
        }

    } catch (error) {
        status.textContent = "🔴 Doshie Offline";

        if (splashText) {
            splashText.textContent = "Waiting for Doshie...";
        }
    }
}


checkHealth();
setInterval(checkHealth, 5000);

// Never leave the public app trapped behind a startup splash if one request is slow.
setTimeout(() => {
    const splash = document.getElementById("splash");
    if (splash && splash.style.display !== "none") {
        splash.style.opacity = "0";
        splash.style.display = "none";
        if (typeof showAccountChooser === "function") showAccountChooser();
    }
}, 8000);

async function loadTaskAlert() {
    const banner = document.getElementById("taskAlert");
    const textBox = document.getElementById("taskAlertText");

    try {
        const response = await fetch("/dashboard", {
            cache: "no-store"
        });

        const data = await response.json();
        const tasks = data.tasks || {};

        const overdue = tasks.overdue || 0;
        const today = tasks.due_today || 0;
        const tomorrow = tasks.due_tomorrow || 0;

        const parts = [];

        if (overdue > 0) {
            parts.push("⚠️ " + overdue + " overdue");
        }

        if (today > 0) {
            parts.push("📅 " + today + " due today");
        }

        if (tomorrow > 0) {
            parts.push("🌅 " + tomorrow + " due tomorrow");
        }

        if (parts.length === 0) {
            banner.style.display = "none";
            return;
        }

        textBox.textContent = parts.join(" • ");
        banner.style.display = "block";

    } catch (error) {
        banner.style.display = "none";
    }
}


loadTaskAlert();
setInterval(loadTaskAlert, 60000);


async function openTodayRoutines() {
    try {
        const response = await fetch("/routines/today");
        const routines = await response.json();

        if (!routines.length) {
            addMessage(
                "No recurring family routines are due today.",
                "Doshie"
            );
            return;
        }

        const reply = routines.map(item => {
            const state = item.done_today ? "✅" : "⬜";

            return state + " " + item.routine +
                (item.assigned_name
                    ? " → " + item.assigned_name
                    : "");
        }).join(" | ");

        addMessage(
            "Today's routines: " + reply,
            "Doshie"
        );

    } catch (error) {
        addMessage(
            "I couldn't load today's routines.",
            "Doshie"
        );
    }
}


async function setDoshieMode(mode, preset) {
    try {
        const response = await fetch("/settings", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                mode: mode,
                voice_preset: preset
            })
        });

        if (!response.ok) {
            throw new Error("Mode change failed.");
        }

        DoshieSettings.mode = mode;
        DoshieSettings.voice_preset = preset;

        const modeSelect =
            document.getElementById("DoshieMode");

        const presetSelect =
            document.getElementById("voicePreset");

        if (modeSelect) {
            modeSelect.value = mode;
        }

        if (presetSelect) {
            presetSelect.value = preset;
        }

        statusBox.textContent =
            "Doshie mode: " + mode.toUpperCase();

        setTimeout(() => {
            statusBox.textContent = "";
        }, 1600);

    } catch (error) {
        statusBox.textContent =
            "Could not change Doshie mode.";
    }
}


async function openGamingDashboard() {
    await setDoshieMode("gaming", "dino");

    const panel =
        document.getElementById("gamingPanel");

    const box =
        document.getElementById(
            "gamingDashboardContent"
        );

    panel.style.display = "block";
    box.textContent = "Loading gaming status...";

    try {
        const response =
            await fetch("/gaming-dashboard");

        const data = await response.json();

        box.innerHTML = "";

        const rows = [
            ["🧠 Local AI",
             data.ai_online
                ? "Online ✅"
                : "Offline ❌"],

            ["🔋 Battery",
             data.battery || "Unknown"],

            ["📱 Device",
             data.status || "Unknown"],

            ["💾 Storage Used",
             data.storage_used_gb + " GB"],

            ["📦 Storage Free",
             data.storage_free_gb + " GB"]
        ];

        rows.forEach(([name, value]) => {
            const row =
                document.createElement("div");

            row.style.padding = "8px";
            row.style.marginBottom = "6px";
            row.style.background = "#202824";
            row.style.borderRadius = "8px";

            row.textContent =
                name + ": " + value;

            box.appendChild(row);
        });

    } catch (error) {
        box.textContent =
            "Could not load Gaming Dashboard.";
    }
}


function closeGamingDashboard() {
    document.getElementById(
        "gamingPanel"
    ).style.display = "none";
}


const AI_TUTORIAL_LESSONS = [
    {
        title: "1. What is AI?",
        icon: "🧠",
        body: "AI is software that finds patterns in information and uses those patterns to produce useful output. A language model predicts and assembles words based on context. It can be helpful without being all-knowing.",
        tryPrompt: "Teach me what an AI language model is in simple terms, then quiz me with one question."
    },
    {
        title: "2. Give better prompts",
        icon: "🎯",
        body: "A useful prompt usually has four ingredients: goal, context, constraints, and desired format. Instead of 'help with my PC', try 'My game stutters after 20 minutes. Give me a safe step-by-step troubleshooting checklist.'",
        tryPrompt: "Show me how to turn a vague request into a strong AI prompt using one example from computer troubleshooting."
    },
    {
        title: "3. AI can make mistakes",
        icon: "🔎",
        body: "AI can sound confident and still be wrong. For important facts, ask for evidence, dates, calculations, or a way to verify the answer. Treat confidence as presentation, not proof.",
        tryPrompt: "Give me a short example of an AI answer that sounds confident but needs verification, and show me how to check it."
    },
    {
        title: "4. Memory, privacy, and permissions",
        icon: "🔐",
        body: "Good personal AI should remember only what is useful and allowed. Sensitive features should be opt-in. In Doshie, profile locks, per-user permissions, and online/offline rules form the fence around private data.",
        tryPrompt: "Explain Doshie's privacy idea: opt-in permissions, profile locks, and online-only syncing, using a simple example."
    },
    {
        title: "5. Build with AI, don't just ask it",
        icon: "🛠️",
        body: "The strongest workflow is a loop: describe the goal, make a small change, test it, inspect the result, then improve it. That turns AI from an answer machine into a workshop partner.",
        tryPrompt: "Give me a tiny beginner AI project I can build with Doshie, with exactly three steps."
    }
];
let aiTutorialIndex = 0;

function aiTutorialStorageKey() {
    return "Doshie-ai-tutorial-" + String(activeProfile || "Hermes").toLowerCase();
}

function renderAiTutorial() {
    const panel = document.getElementById("aiTutorialPanel");
    const lessonBox = document.getElementById("aiTutorialLesson");
    if (!panel || !lessonBox) return;
    aiTutorialIndex = Math.max(0, Math.min(AI_TUTORIAL_LESSONS.length - 1, aiTutorialIndex));
    const lesson = AI_TUTORIAL_LESSONS[aiTutorialIndex];
    lessonBox.innerHTML =
        `<div style="font-size:20px;font-weight:700;margin-bottom:8px;">${lesson.icon} ${lesson.title}</div>` +
        `<div>${lesson.body}</div>`;
    document.getElementById("aiTutorialProgress").textContent =
        `Lesson ${aiTutorialIndex + 1} of ${AI_TUTORIAL_LESSONS.length}`;
    document.getElementById("aiTutorialProgressBar").style.width =
        `${((aiTutorialIndex + 1) / AI_TUTORIAL_LESSONS.length) * 100}%`;
    localStorage.setItem(aiTutorialStorageKey(), String(aiTutorialIndex));
}

function openAiTutorial() {
    const saved = parseInt(localStorage.getItem(aiTutorialStorageKey()) || "0", 10);
    aiTutorialIndex = Number.isFinite(saved) ? saved : 0;
    document.getElementById("aiTutorialPanel").style.display = "block";
    renderAiTutorial();
}

function closeAiTutorial() {
    document.getElementById("aiTutorialPanel").style.display = "none";
}

function aiTutorialPrevious() {
    aiTutorialIndex = Math.max(0, aiTutorialIndex - 1);
    renderAiTutorial();
}

function aiTutorialNext() {
    aiTutorialIndex = Math.min(AI_TUTORIAL_LESSONS.length - 1, aiTutorialIndex + 1);
    renderAiTutorial();
}

function aiTutorialTry() {
    const lesson = AI_TUTORIAL_LESSONS[aiTutorialIndex];
    closeAiTutorial();
    quick(lesson.tryPrompt);
}

function aiTutorialReset() {
    aiTutorialIndex = 0;
    localStorage.removeItem(aiTutorialStorageKey());
    renderAiTutorial();
}


async function openTechDashboard() {
    await setDoshieMode("tech", "tech");

    const panel =
        document.getElementById("techPanel");

    const box =
        document.getElementById(
            "techDashboardContent"
        );

    panel.style.display = "block";
    box.textContent = "Loading tech status...";

    try {
        const response =
            await fetch("/tech-dashboard");

        const data = await response.json();

        box.innerHTML = "";

        const rows = [
            ["🧠 Local AI",
             data.ai_online ? "Online ✅" : "Offline ❌"],

            ["🖥️ Architecture",
             data.architecture || "Unknown"],

            ["⚙️ CPU Load",
             data.load_average || "Unknown"],

            ["🧮 Memory Total",
             data.memory_total || "Unknown"],

            ["🟢 Memory Available",
             data.memory_available || "Unknown"],

            ["💾 Storage",
             data.storage_used_gb + " GB used / " +
             data.storage_total_gb + " GB"],

            ["📦 Free Storage",
             data.storage_free_gb + " GB"]
        ];

        rows.forEach(([name, value]) => {
            const row =
                document.createElement("div");

            row.style.padding = "8px";
            row.style.marginBottom = "6px";
            row.style.background = "#202824";
            row.style.borderRadius = "8px";

            row.textContent =
                name + ": " + value;

            box.appendChild(row);
        });

    } catch (error) {
        box.textContent =
            "Could not load Tech Dashboard.";
    }
}


function closeTechDashboard() {
    document.getElementById(
        "techPanel"
    ).style.display = "none";
}


async function loadDashboard() {
    const box = document.getElementById("dashboard");

    try {
        const response = await fetch("/dashboard");
        const data = await response.json();

        box.innerHTML =
            "🌦️ " + data.weather +
            "<br>🧠 Auto Memory: " +
            (data.auto_memory ? "ON" : "OFF") +
            " | 🔊 Speak: " +
            (data.speak_replies ? "ON" : "OFF") +
            "<br>" +
            `<button class="tool" onclick="openOrganizer('overdue')">⚠️ Overdue: ${data.tasks.overdue}</button>
            <button class="tool" onclick="openOrganizer('today')">📅 Today: ${data.tasks.due_today}</button>
            <button class="tool" onclick="openOrganizer('tomorrow')">🌅 Tomorrow: ${data.tasks.due_tomorrow}</button>
            <button class="tool" onclick="openTodayRoutines()">🔁 Routines Today: ${data.tasks.routines_today || 0}</button>
            <button class="tool" onclick="openOrganizer('high')">🔥 High: ${data.tasks.high_priority}</button>`;

    } catch (error) {
        box.textContent = "Doshie status unavailable.";
    }
}


loadDashboard();
setInterval(loadDashboard, 300000);

loadQuickTaskFamily();


async function loadReminderFamilyOptions() {
    const select =
        document.getElementById("newReminderFamily");

    if (!select) return;

    try {
        const response = await fetch("/family");
        const family = await response.json();

        select.innerHTML = "";

        const empty = document.createElement("option");
        empty.value = "";
        empty.textContent = "Unassigned";
        select.appendChild(empty);

        family.forEach(member => {
            const option = document.createElement("option");

            option.value = member.id;
            option.textContent =
                member.name + " (" + member.role + ")";

            select.appendChild(option);
        });

    } catch (error) {
        console.log("Could not load reminder family options.");
    }
}


async function openReminders() {
    loadReminderFamilyOptions();
    const panel = document.getElementById("remindersPanel");
    const list = document.getElementById("remindersList");

    panel.style.display = "block";
    list.innerHTML = "Loading...";

    try {
        const response = await fetch("/reminders");
        const reminders = await response.json();

        const familyResponse = await fetch("/family");
        const family = await familyResponse.json();

        list.innerHTML = "";

        if (!reminders.length) {
            list.innerHTML = "<p>No reminders yet.</p>";
            return;
        }

        reminders.forEach(item => {
            const row = document.createElement("div");

            row.style.padding = "10px";
            row.style.marginBottom = "8px";
            row.style.background = "#202824";
            row.style.borderRadius = "10px";

            const done = document.createElement("button");
            done.className = "tool";
            done.textContent = item.done ? "✅" : "⏰";

            done.onclick = async () => {
                if (!item.done) {
                    await fetch(
                        "/reminders/" + item.id + "/done",
                        { method: "POST" }
                    );
                }

                openReminders();
            };

            const label = document.createElement("span");

            let assignedName = "";

            if (item.assigned_to) {
                const member = family.find(
                    person =>
                        Number(person.id) ===
                        Number(item.assigned_to)
                );

                if (member) {
                    assignedName = member.name;
                }
            }

            label.textContent =
                " " + item.reminder +
                (item.due_date
                    ? " • Due " + item.due_date
                    : "") +
                (assignedName
                    ? " • 👤 " + assignedName
                    : "");

            if (item.done) {
                label.style.textDecoration = "line-through";
                label.style.opacity = "0.6";
            }

            const del = document.createElement("button");
            del.className = "tool";
            del.textContent = "🗑️";
            del.style.marginLeft = "8px";

            del.onclick = async () => {
                await fetch(
                    "/reminders/" + item.id,
                    { method: "DELETE" }
                );

                openReminders();
            };

            row.appendChild(done);
            row.appendChild(label);
            row.appendChild(del);

            list.appendChild(row);
        });

    } catch (error) {
        list.innerHTML = "Could not load reminders.";
    }
}


function closeReminders() {
    document.getElementById(
        "remindersPanel"
    ).style.display = "none";
}


async function createReminder() {
    const reminder =
        document.getElementById(
            "newReminderText"
        ).value.trim();

    const dueDate =
        document.getElementById(
            "newReminderDate"
        ).value;

    const assignedTo =
        document.getElementById(
            "newReminderFamily"
        ).value;

    if (!reminder) {
        statusBox.textContent =
            "Enter a reminder first.";
        return;
    }

    try {
        const response = await fetch("/reminders", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                reminder: reminder,
                due_date: dueDate,
                assigned_to: assignedTo || null
            })
        });

        if (!response.ok) {
            throw new Error("Reminder creation failed.");
        }

        document.getElementById(
            "newReminderText"
        ).value = "";

        document.getElementById(
            "newReminderDate"
        ).value = "";

        openReminders();

    } catch (error) {
        statusBox.textContent =
            "Could not add reminder.";
    }
}


async function loadShoppingFamilyFilter() {
    const select =
        document.getElementById("shoppingFamilyFilter");

    if (!select) return;

    const current = select.value;

    try {
        const response = await fetch("/family");
        const family = await response.json();

        select.innerHTML = "";

        const all = document.createElement("option");
        all.value = "";
        all.textContent = "Everyone";
        select.appendChild(all);

        family.forEach(member => {
            const option = document.createElement("option");

            option.value = member.name;
            option.textContent =
                member.name + " (" + member.role + ")";

            select.appendChild(option);
        });

        select.value = current;

    } catch (error) {
        console.log("Could not load shopping family filter.");
    }
}


async function loadQuickTaskFamily() {
    const select =
        document.getElementById("quickTaskFamily");

    if (!select) return;

    try {
        const response = await fetch("/family");
        const family = await response.json();

        select.innerHTML = "";

        const empty = document.createElement("option");
        empty.value = "";
        empty.textContent = "Unassigned";
        select.appendChild(empty);

        family.forEach(member => {
            const option = document.createElement("option");

            option.value = member.id;
            option.textContent =
                member.name + " (" + member.role + ")";

            select.appendChild(option);
        });

    } catch (error) {
        console.log("Could not load quick task family.");
    }
}


async function quickAddTask() {
    const task =
        document.getElementById(
            "quickTaskText"
        ).value.trim();

    const assignedTo =
        document.getElementById(
            "quickTaskFamily"
        ).value;

    if (!task) {
        statusBox.textContent =
            "Enter a task first.";
        return;
    }

    try {
        const response = await fetch("/tasks", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                task: task,
                priority: "Normal",
                due_date: "",
                tag: "Home",
                assigned_to: assignedTo || null
            })
        });

        if (!response.ok) {
            throw new Error("Quick task failed.");
        }

        document.getElementById(
            "quickTaskText"
        ).value = "";

        statusBox.textContent =
            "Family task added. ✅";

        setTimeout(() => {
            statusBox.textContent = "";
        }, 1600);

        if (typeof loadDashboard === "function") {
            loadDashboard();
        }

    } catch (error) {
        statusBox.textContent =
            "Could not add family task.";
    }
}


async function quickAddShopping() {
    const item =
        document.getElementById(
            "quickShoppingItem"
        ).value.trim();

    const category =
        document.getElementById(
            "quickShoppingCategory"
        ).value;

    if (!item) {
        statusBox.textContent =
            "Enter a shopping item first.";
        return;
    }

    try {
        const response = await fetch("/shopping", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                item: item,
                category: category
            })
        });

        if (!response.ok) {
            throw new Error("Quick add failed.");
        }

        document.getElementById(
            "quickShoppingItem"
        ).value = "";

        statusBox.textContent =
            "Added to shopping list. 🛒";

        setTimeout(() => {
            statusBox.textContent = "";
        }, 1600);

    } catch (error) {
        statusBox.textContent =
            "Could not add shopping item.";
    }
}


async function openShopping() {
    await loadShoppingFamilyFilter();
    const panel = document.getElementById("shoppingPanel");
    const list = document.getElementById("shoppingList");

    panel.style.display = "block";
    list.innerHTML = "Loading...";

    try {
        const response = await fetch("/shopping");
        let items = await response.json();

        const filter =
            document.getElementById(
                "shoppingFamilyFilter"
            ).value;

        if (filter) {
            items = items.filter(item =>
                (item.added_by || "") === filter
            );
        }

        list.innerHTML = "";

        if (!items.length) {
            list.innerHTML = "<p>The shopping list is empty.</p>";
            return;
        }

        const grouped = {};

        items.forEach(item => {
            const category = item.category || "Other";

            if (!grouped[category]) {
                grouped[category] = [];
            }

            grouped[category].push(item);
        });

        const preferredOrder = [
            "Groceries",
            "Pets",
            "Household",
            "School",
            "Tech",
            "Other"
        ];

        preferredOrder.forEach(category => {
            const categoryItems = grouped[category];

            if (!categoryItems || !categoryItems.length) {
                return;
            }

            const section = document.createElement("div");
            section.style.marginBottom = "16px";

            const heading = document.createElement("div");
            heading.style.fontWeight = "bold";
            heading.style.marginBottom = "8px";

            let icon = "📦";

            if (category === "Groceries") icon = "🥦";
            if (category === "Pets") icon = "🐾";
            if (category === "Household") icon = "🏠";
            if (category === "School") icon = "🎒";
            if (category === "Tech") icon = "💻";

            heading.textContent =
                icon + " " + category +
                " (" + categoryItems.length + ")";

            section.appendChild(heading);

            categoryItems.forEach(item => {
                const row = document.createElement("div");

                row.style.padding = "10px";
                row.style.marginBottom = "8px";
                row.style.background = "#202824";
                row.style.borderRadius = "10px";

                const toggle = document.createElement("button");
                toggle.className = "tool";
                toggle.textContent = item.bought ? "✅" : "⬜";

                toggle.onclick = async () => {
                    await fetch("/shopping/" + item.id, {
                        method: "PUT",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            bought: !item.bought
                        })
                    });

                    openShopping();
                };

                const label = document.createElement("span");

                label.textContent =
                    " " + item.item +
                    (item.quantity
                        ? " x" + item.quantity
                        : "") +
                    (item.added_by
                        ? " • 👤 " + item.added_by
                        : " • 👤 Unassigned");

                if (item.bought) {
                    label.style.textDecoration = "line-through";
                    label.style.opacity = "0.6";
                }

                const del = document.createElement("button");
                del.className = "tool";
                del.textContent = "🗑️";
                del.style.marginLeft = "8px";

                del.onclick = async () => {
                    await fetch("/shopping/" + item.id, {
                        method: "DELETE"
                    });

                    openShopping();
                };

                row.appendChild(toggle);
                row.appendChild(label);
                row.appendChild(del);

                section.appendChild(row);
            });

            list.appendChild(section);
        });

    } catch (error) {
        list.innerHTML = "Could not load shopping list.";
    }
}


function closeShopping() {
    document.getElementById("shoppingPanel").style.display = "none";
}


async function createShoppingItem() {
    const item =
        document.getElementById("newShoppingItem").value.trim();

    const quantity =
        document.getElementById("newShoppingQuantity").value.trim();

    const category =
        document.getElementById("newShoppingCategory").value;

    if (!item) {
        statusBox.textContent = "Enter an item first.";
        return;
    }

    try {
        const response = await fetch("/shopping", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                item: item,
                quantity: quantity,
                category: category
            })
        });

        if (!response.ok) {
            throw new Error("Shopping item failed.");
        }

        document.getElementById("newShoppingItem").value = "";
        document.getElementById("newShoppingQuantity").value = "";

        openShopping();

    } catch (error) {
        statusBox.textContent = "Could not add shopping item.";
    }
}


async function loadFamilyToday() {
    const box = document.getElementById("familyTodayBox");

    if (!box) return;

    box.innerHTML = "Loading today's family plan...";

    try {
        const response = await fetch("/family-today");
        const data = await response.json();

        box.innerHTML = "";

        const title = document.createElement("div");
        title.style.fontWeight = "bold";
        title.style.marginBottom = "8px";
        title.textContent = "☀️ Today • " + data.weekday;

        box.appendChild(title);

        const items = [
            ...data.tasks,
            ...data.reminders,
            ...data.routines
        ];

        if (!items.length) {
            const empty = document.createElement("div");
            empty.textContent = "✅ Nothing due for the family today.";
            empty.style.color = "#9eb2a7";
            box.appendChild(empty);
            return;
        }

        items.forEach(item => {
            const row = document.createElement("div");

            row.style.display = "flex";
            row.style.alignItems = "center";
            row.style.gap = "8px";
            row.style.padding = "6px 0";

            const done = document.createElement("button");
            done.className = "tool";
            done.textContent = "⬜";

            const label = document.createElement("span");

            let icon = "⬜";

            if (item.type === "reminder") {
                icon = "⏰";
            }

            if (item.type === "routine") {
                icon = "🔁";
            }

            label.textContent =
                icon + " " + item.text +
                (item.assigned_name
                    ? " → " + item.assigned_name
                    : " → Unassigned");

            done.onclick = async () => {
                try {
                    if (item.type === "task") {
                        await fetch(
                            "/tasks/" + item.id + "/done",
                            { method: "POST" }
                        );
                    }

                    if (item.type === "reminder") {
                        await fetch(
                            "/reminders/" + item.id + "/done",
                            { method: "POST" }
                        );
                    }

                    if (item.type === "routine") {
                        await fetch(
                            "/routines/" + item.id + "/done-today",
                            { method: "POST" }
                        );
                    }

                    await loadFamilyToday();

                    if (typeof loadDashboard === "function") {
                        loadDashboard();
                    }

                } catch (error) {
                    statusBox.textContent =
                        "Could not complete that item.";
                }
            };

            row.appendChild(done);
            row.appendChild(label);

            box.appendChild(row);
        });

    } catch (error) {
        box.textContent =
            "Could not load today's family plan.";
    }
}


async function openFamilyDashboard() {
    loadFamilyToday();
    const panel =
        document.getElementById("familyDashboardPanel");

    const list =
        document.getElementById("familyDashboardList");

    panel.style.display = "block";
    list.innerHTML = "Loading...";

    try {
        const response = await fetch("/family-dashboard");
        const data = await response.json();

        list.innerHTML = "";

        data.members.forEach(member => {
            const card = document.createElement("div");

            card.style.padding = "12px";
            card.style.marginBottom = "12px";
            card.style.background = "#202824";
            card.style.borderRadius = "12px";

            const title = document.createElement("div");
            title.style.fontWeight = "bold";
            title.style.marginBottom = "8px";
            title.textContent =
                "👤 " + member.name +
                " (" + member.role + ")" +
                " • " + member.open_tasks.length +
                " open";

            card.appendChild(title);

            if (!member.open_tasks.length) {
                const empty = document.createElement("div");
                empty.textContent = "✅ No open chores.";
                empty.style.color = "#9eb2a7";
                card.appendChild(empty);
            } else {
                member.open_tasks.forEach(task => {
                    const row = document.createElement("div");

                    row.style.padding = "6px 0";

                    row.textContent =
                        "⬜ " + task.task +
                        " • " + task.priority +
                        (task.due_date
                            ? " • Due " + task.due_date
                            : "");

                    card.appendChild(row);
                });
            }

            if (member.routines && member.routines.length) {
                const routineTitle = document.createElement("div");

                routineTitle.textContent = "🔁 Routines";
                routineTitle.style.fontWeight = "bold";
                routineTitle.style.marginTop = "10px";
                routineTitle.style.marginBottom = "4px";

                card.appendChild(routineTitle);

                member.routines.forEach(routine => {
                    const row = document.createElement("div");

                    row.style.padding = "5px 0";
                    row.style.color = "#9eb2a7";

                    row.textContent =
                        "🔁 " + routine.routine +
                        (routine.weekday
                            ? " • Every " + routine.weekday
                            : "");

                    card.appendChild(row);
                });
            }

            list.appendChild(card);
        });

        if (data.unassigned && data.unassigned.length) {
            const card = document.createElement("div");

            card.style.padding = "12px";
            card.style.marginBottom = "12px";
            card.style.background = "#202824";
            card.style.borderRadius = "12px";

            const title = document.createElement("div");
            title.style.fontWeight = "bold";
            title.style.marginBottom = "8px";
            title.textContent =
                "👤 Unassigned • " +
                data.unassigned.length +
                " open";

            card.appendChild(title);

            data.unassigned.forEach(task => {
                const row = document.createElement("div");

                row.style.padding = "6px 0";

                row.textContent =
                    "⬜ " + task.task +
                    " • " + task.priority +
                    (task.due_date
                        ? " • Due " + task.due_date
                        : "");

                card.appendChild(row);
            });

            list.appendChild(card);
        }

    } catch (error) {
        list.innerHTML =
            "Could not load the Family Dashboard.";
    }
}


function closeFamilyDashboard() {
    document.getElementById(
        "familyDashboardPanel"
    ).style.display = "none";
}


async function openFamily() {
    const panel = document.getElementById("familyPanel");
    const list = document.getElementById("familyList");

    panel.style.display = "block";
    list.innerHTML = "Loading...";

    try {
        const response = await fetch("/family");
        const family = await response.json();

        list.innerHTML = "";

        if (!family.length) {
            list.innerHTML = "<p>No family members saved yet.</p>";
            return;
        }

        family.forEach(member => {
            const card = document.createElement("div");

            card.style.padding = "10px";
            card.style.marginBottom = "10px";
            card.style.background = "#202824";
            card.style.borderRadius = "10px";

            const name = document.createElement("input");
            name.value = member.name;
            name.style.width = "100%";
            name.style.padding = "8px";
            name.style.marginBottom = "8px";

            const role = document.createElement("input");
            role.value = member.role;
            role.style.width = "100%";
            role.style.padding = "8px";
            role.style.marginBottom = "8px";

            const notes = document.createElement("input");
            notes.value = member.notes || "";
            notes.placeholder = "Notes";
            notes.style.width = "100%";
            notes.style.padding = "8px";
            notes.style.marginBottom = "8px";

            const save = document.createElement("button");
            save.className = "tool";
            save.textContent = "💾 Save";

            save.onclick = async () => {
                await fetch("/family/" + member.id, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        name: name.value,
                        role: role.value,
                        notes: notes.value
                    })
                });

                statusBox.textContent = "Family member updated.";

                setTimeout(() => {
                    statusBox.textContent = "";
                }, 1200);

                openFamily();
            };

            const del = document.createElement("button");
            del.className = "tool";
            del.textContent = "🗑️ Remove";
            del.style.marginLeft = "8px";

            del.onclick = async () => {
                await fetch("/family/" + member.id, {
                    method: "DELETE"
                });

                openFamily();
            };

            card.appendChild(name);
            card.appendChild(role);
            card.appendChild(notes);
            card.appendChild(save);
            card.appendChild(del);

            list.appendChild(card);
        });

    } catch (error) {
        list.innerHTML = "Could not load family members.";
    }
}


function closeFamily() {
    document.getElementById("familyPanel").style.display = "none";
}


async function createFamilyMember() {
    const name =
        document.getElementById("newFamilyName").value.trim();

    const role =
        document.getElementById("newFamilyRole").value.trim();

    const notes =
        document.getElementById("newFamilyNotes").value.trim();

    if (!name) {
        statusBox.textContent = "Enter a name first.";
        return;
    }

    try {
        const response = await fetch("/family", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name: name,
                role: role || "Family",
                notes: notes
            })
        });

        if (!response.ok) {
            throw new Error("Could not add family member.");
        }

        document.getElementById("newFamilyName").value = "";
        document.getElementById("newFamilyRole").value = "";
        document.getElementById("newFamilyNotes").value = "";

        openFamily();

    } catch (error) {
        statusBox.textContent = "Could not add family member.";
    }
}


async function createBackup() {
    statusBox.textContent = "Creating Doshie backup...";

    try {
        const response = await fetch("/backup", {
            method: "POST"
        });

        const data = await response.json();

        statusBox.textContent =
            data.reply || "Backup finished.";

        setTimeout(() => {
            statusBox.textContent = "";
        }, 4000);

    } catch (error) {
        statusBox.textContent = "Backup failed.";
    }
}


async function createNote() {
    const input = document.getElementById("newNoteText");
    const note = input.value.trim();
    const tag = document.getElementById("newNoteTag").value;

    if (!note) {
        statusBox.textContent = "Enter a note first.";
        return;
    }

    try {
        const response = await fetch("/notes", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                note: note,
                tag: tag
            })
        });

        if (!response.ok) {
            throw new Error("Note creation failed.");
        }

        input.value = "";

        statusBox.textContent = "Note added.";

        setTimeout(() => {
            statusBox.textContent = "";
        }, 1200);

        openOrganizer();

    } catch (error) {
        statusBox.textContent = "Could not add note.";
    }
}


async function createTask() {
    const task = document.getElementById("newTaskText").value.trim();
    const priority =
        document.getElementById("newTaskPriority").value;
    const due =
        document.getElementById("newTaskDue").value;

    const tag =
        document.getElementById("newTaskTag").value;

    const assignedTo =
        document.getElementById("newTaskFamily").value;

    if (!task) {
        statusBox.textContent = "Enter a task first.";
        return;
    }

    try {
        const response = await fetch("/tasks", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                task: task,
                priority: priority,
                due_date: due,
                tag: tag,
                assigned_to: assignedTo || null
            })
        });

        if (!response.ok) {
            throw new Error("Task creation failed.");
        }

        document.getElementById("newTaskText").value = "";
        document.getElementById("newTaskDue").value = "";
        document.getElementById("newTaskPriority").value = "Normal";
        document.getElementById("newTaskTag").value = "General";

        statusBox.textContent = "Task added.";

        setTimeout(() => {
            statusBox.textContent = "";
        }, 1200);

        openOrganizer();

        if (typeof loadDashboard === "function") {
            loadDashboard();
        }

        if (typeof loadTaskAlert === "function") {
            loadTaskAlert();
        }

    } catch (error) {
        statusBox.textContent = "Could not add task.";
    }
}


let organizerTag = "all";


function setOrganizerTag(tag) {
    organizerTag = tag;
    openOrganizer();
}


async function loadTaskFamilyOptions() {
    const select = document.getElementById("newTaskFamily");

    if (!select) return;

    try {
        const response = await fetch("/family");
        const family = await response.json();

        select.innerHTML = "";

        const empty = document.createElement("option");
        empty.value = "";
        empty.textContent = "Unassigned";
        select.appendChild(empty);

        family.forEach(member => {
            const option = document.createElement("option");
            option.value = member.id;
            option.textContent =
                member.name + " (" + member.role + ")";
            select.appendChild(option);
        });

    } catch (error) {
        console.log("Could not load family options.");
    }
}


async function openOrganizer(filter = 'all') {
    loadTaskFamilyOptions();
    const panel = document.getElementById("organizerPanel");
    const taskList = document.getElementById("taskList");
    const noteList = document.getElementById("noteList");

    panel.style.display = "block";

    try {
        const taskResponse = await fetch("/tasks");
        let tasks = await taskResponse.json();

        const familyResponse = await fetch("/family");
        const familyMembers = await familyResponse.json();

        if (organizerTag !== "all") {
            tasks = tasks.filter(item =>
                (item.tag || "General") === organizerTag
            );
        }

        const today = new Date().toISOString().slice(0, 10);

        if (filter === "overdue") {
            tasks = tasks.filter(item =>
                !item.done &&
                item.due_date &&
                item.due_date < today
            );
        }

        if (filter === "today") {
            tasks = tasks.filter(item =>
                !item.done &&
                item.due_date === today
            );
        }

        if (filter === "tomorrow") {
            const tomorrowDate = new Date();
            tomorrowDate.setDate(
                tomorrowDate.getDate() + 1
            );

            const tomorrow =
                tomorrowDate.toISOString().slice(0, 10);

            tasks = tasks.filter(item =>
                !item.done &&
                item.due_date === tomorrow
            );
        }

        if (filter === "high") {
            tasks = tasks.filter(item =>
                !item.done &&
                item.priority === "High"
            );
        }

        taskList.innerHTML = "";

        if (!tasks.length) {
            taskList.innerHTML = "<p>No tasks yet.</p>";
        } else {
            tasks.forEach(item => {
                const row = document.createElement("div");

                row.style.padding = "10px";
                row.style.marginBottom = "10px";
                row.style.background = "#202824";
                row.style.borderRadius = "10px";

                const input = document.createElement("input");
                input.value = item.task;
                input.style.width = "100%";
                input.style.padding = "8px";
                input.style.marginBottom = "8px";

                const priority = document.createElement("select");
                priority.style.padding = "8px";
                priority.style.marginRight = "8px";

                ["Low", "Normal", "High"].forEach(value => {
                    const option = document.createElement("option");
                    option.value = value;
                    option.textContent = value;

                    if (item.priority === value) {
                        option.selected = true;
                    }

                    priority.appendChild(option);
                });

                const due = document.createElement("input");
                due.type = "date";
                due.value = item.due_date || "";
                due.style.padding = "8px";
                due.style.marginRight = "8px";

                const done = document.createElement("button");
                done.className = "tool";
                done.textContent = item.done ? "↩️ Reopen" : "✅ Done";

                done.onclick = async () => {
                    await fetch("/tasks/" + item.id, {
                        method: "PUT",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({
                            done: !item.done
                        })
                    });

                    openOrganizer();
                };

                const save = document.createElement("button");
                save.className = "tool";
                save.textContent = "💾 Save";
                save.style.marginLeft = "8px";

                save.onclick = async () => {
                    await fetch("/tasks/" + item.id, {
                        method: "PUT",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({
                            task: input.value,
                            priority: priority.value,
                            due_date: due.value
                        })
                    });

                    statusBox.textContent = "Task updated.";
                    setTimeout(() => statusBox.textContent = "", 1200);
                };

                const del = document.createElement("button");
                del.className = "tool";
                del.textContent = "🗑️ Delete";
                del.style.marginLeft = "8px";

                del.onclick = async () => {
                    await fetch("/tasks/" + item.id, {
                        method: "DELETE"
                    });

                    openOrganizer();
                };

                const controls = document.createElement("div");
                controls.style.display = "flex";
                controls.style.flexWrap = "wrap";
                controls.style.gap = "8px";

                controls.appendChild(priority);
                controls.appendChild(due);
                controls.appendChild(done);
                controls.appendChild(save);
                controls.appendChild(del);

                const familySelect = document.createElement("select");
                familySelect.style.padding = "8px";
                familySelect.style.marginBottom = "8px";

                const unassigned = document.createElement("option");
                unassigned.value = "";
                unassigned.textContent = "👤 Unassigned";
                familySelect.appendChild(unassigned);

                familyMembers.forEach(member => {
                    const option = document.createElement("option");

                    option.value = member.id;
                    option.textContent =
                        "👤 " + member.name + " (" + member.role + ")";

                    if (
                        item.assigned_to &&
                        Number(item.assigned_to) === Number(member.id)
                    ) {
                        option.selected = true;
                    }

                    familySelect.appendChild(option);
                });

                familySelect.onchange = async () => {
                    await fetch("/tasks/" + item.id, {
                        method: "PUT",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            assigned_to:
                                familySelect.value || null
                        })
                    });

                    statusBox.textContent = "Task reassigned.";

                    setTimeout(() => {
                        statusBox.textContent = "";
                    }, 1200);

                    openOrganizer();
                };

                const familyLabel = document.createElement("div");
                familyLabel.textContent =
                    item.assigned_name
                    ? "👤 " + item.assigned_name
                    : "👤 Unassigned";

                familyLabel.style.fontSize = "12px";
                familyLabel.style.color = "#9eb2a7";
                familyLabel.style.marginBottom = "6px";

                const tagLabel = document.createElement("div");
                tagLabel.textContent = "🏷️ " + (item.tag || "General");
                tagLabel.style.fontSize = "12px";
                tagLabel.style.color = "#9eb2a7";
                tagLabel.style.marginBottom = "8px";

                row.appendChild(input);
                row.appendChild(familySelect);
                row.appendChild(familyLabel);
                row.appendChild(tagLabel);
                row.appendChild(controls);

                taskList.appendChild(row);
            });
        }

        const noteResponse = await fetch("/notes");
        let notes = await noteResponse.json();

        if (organizerTag !== "all") {
            notes = notes.filter(item =>
                (item.tag || "General") === organizerTag
            );
        }

        noteList.innerHTML = "";

        if (!notes.length) {
            noteList.innerHTML = "<p>No notes yet.</p>";
        } else {
            notes.forEach(item => {
                const row = document.createElement("div");

                row.style.padding = "10px";
                row.style.marginBottom = "10px";
                row.style.background = "#202824";
                row.style.borderRadius = "10px";

                const input = document.createElement("input");
                input.value = item.note;
                input.style.width = "100%";
                input.style.padding = "8px";
                input.style.marginBottom = "8px";

                const save = document.createElement("button");
                save.className = "tool";
                save.textContent = "💾 Save";

                save.onclick = async () => {
                    await fetch("/notes/" + item.id, {
                        method: "PUT",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({
                            note: input.value
                        })
                    });

                    statusBox.textContent = "Note updated.";
                    setTimeout(() => statusBox.textContent = "", 1200);
                };

                const del = document.createElement("button");
                del.className = "tool";
                del.textContent = "🗑️ Delete";
                del.style.marginLeft = "8px";

                del.onclick = async () => {
                    await fetch("/notes/" + item.id, {
                        method: "DELETE"
                    });

                    openOrganizer();
                };

                const tagLabel = document.createElement("div");
                tagLabel.textContent = "🏷️ " + (item.tag || "General");
                tagLabel.style.fontSize = "12px";
                tagLabel.style.color = "#9eb2a7";
                tagLabel.style.marginBottom = "8px";

                row.appendChild(input);
                row.appendChild(tagLabel);
                row.appendChild(save);
                row.appendChild(del);

                noteList.appendChild(row);
            });
        }

    } catch (error) {
        taskList.innerHTML = "Could not load tasks.";
        noteList.innerHTML = "Could not load notes.";
    }
}


function closeOrganizer() {
    document.getElementById("organizerPanel").style.display = "none";
}


let availableVoices = [];
let activeVoiceAudio = null;
let activeVoiceUrl = null;
let voiceRequestToken = 0;


function scoreVoice(voice) {
    const name = voice.name.toLowerCase();
    const language = voice.lang.toLowerCase();
    let score = 0;

    if (language === "en-us") score += 8;
    else if (language.startsWith("en")) score += 4;
    if (/natural|neural|enhanced/.test(name)) score += 8;
    if (/google|samsung|microsoft/.test(name)) score += 5;
    if (voice.localService) score += 1;

    return score;
}


function loadVoices() {
    availableVoices = window.speechSynthesis.getVoices();

    const select = document.getElementById("voiceSelect");
    if (!select) return;

    const savedUri = localStorage.getItem("Doshie_voice_uri");
    let selectedIndex = 0;
    let selectedScore = -1;
    select.innerHTML = "";

    availableVoices.forEach((voice, index) => {
        const option = document.createElement("option");
        option.value = index;
        option.textContent = voice.name + " (" + voice.lang + ")";
        select.appendChild(option);

        if (savedUri && voice.voiceURI === savedUri) {
            selectedIndex = index;
        } else if (!savedUri && scoreVoice(voice) > selectedScore) {
            selectedIndex = index;
            selectedScore = scoreVoice(voice);
        }
    });

    select.value = String(selectedIndex);
    select.onchange = () => {
        const voice = availableVoices[parseInt(select.value)];
        if (voice) localStorage.setItem("Doshie_voice_uri", voice.voiceURI);
    };
}


if ("speechSynthesis" in window) {
    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;
}


function cleanSpeechText(text) {
    return String(text || "")
        .replace(
            /!\\[[^\\]]*(?:gif|animated)[^\\]]*\\]\\([^)]*\\)/gi,
            " "
        )
        .replace(
            /!\\[[^\\]]*\\]\\(https?:\\/\\/[^\\s)]+\\.gif(?:\\?[^\\s)]*)?\\)/gi,
            " "
        )
        .replace(
            /https?:\\/\\/[^\\s]+\\.gif(?:\\?[^\\s]*)?/gi,
            " "
        )
        .replace(/\\b(?:gif|giphy|tenor)\\b\\s*:*/gi, " ")
        .replace(/https?:\\/\\/\\S+/g, " link ")
        .replace(/[*_#>|]/g, " ")
        .replace(/\\s+/g, " ")
        .trim();
}


function selectedDoshieVoice() {
    const select = document.getElementById("voiceSelect");
    if (!select || !availableVoices.length) return null;

    return availableVoices[parseInt(select.value)] || null;
}


function updateVoiceControls() {
    const engine = document.getElementById("voiceEngine");
    const voiceSelect = document.getElementById("voiceSelect");
    const pitch = document.getElementById("voicePitch");
    const usesClone = !engine || engine.value === "clone";

    if (voiceSelect) voiceSelect.disabled = usesClone;
    if (pitch) pitch.disabled = usesClone;
}


function speakWithDeviceVoice(cleanText) {
    if (!("speechSynthesis" in window)) {
        throw new Error("Device speech is not available.");
    }

    const speech = new SpeechSynthesisUtterance(cleanText);
    const voice = selectedDoshieVoice();

    if (voice) {
        speech.voice = voice;
        speech.lang = voice.lang;
    } else {
        speech.lang = "en-US";
    }

    speech.rate = Number(DoshieSettings.voice_rate ?? 1.0);
    speech.pitch = Number(DoshieSettings.voice_pitch ?? 0.95);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(speech);
}


function splitSpeechChunks(text, maxLength = 140) {
    let remaining = String(text || "").trim();
    const chunks = [];

    while (remaining.length > maxLength) {
        let cut = -1;

        [". ", "? ", "! "].forEach(mark => {
            cut = Math.max(cut, remaining.lastIndexOf(mark, maxLength - 1) + 1);
        });

        if (cut < Math.floor(maxLength * 0.55)) {
            cut = remaining.lastIndexOf(" ", maxLength);
        }
        if (cut <= 0) cut = maxLength;

        chunks.push(remaining.slice(0, cut).trim());
        remaining = remaining.slice(cut).trim();
    }

    if (remaining) chunks.push(remaining);
    return chunks;
}


async function fetchCloneSpeech(text) {
    const response = await fetch("/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
    });

    if (!response.ok) {
        throw new Error("Cloned voice is not ready.");
    }
    return response.blob();
}


function queuedCloneSpeech(text) {
    return fetchCloneSpeech(text).then(
        blob => ({ blob }),
        error => ({ error })
    );
}


function playCloneSpeech(audioBlob, requestToken) {
    return new Promise((resolve, reject) => {
        if (requestToken !== voiceRequestToken) {
            resolve();
            return;
        }

        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        let finished = false;

        activeVoiceAudio = audio;
        activeVoiceUrl = audioUrl;
        audio.playbackRate = Math.min(
            1.25,
            Math.max(0.75, Number(DoshieSettings.voice_rate ?? 1.0))
        );

        const finish = error => {
            if (finished) return;
            finished = true;
            clearInterval(cancelCheck);
            if (activeVoiceAudio === audio) activeVoiceAudio = null;
            if (activeVoiceUrl === audioUrl) activeVoiceUrl = null;
            URL.revokeObjectURL(audioUrl);
            if (error) reject(error);
            else resolve();
        };

        const cancelCheck = setInterval(() => {
            if (requestToken !== voiceRequestToken) {
                audio.pause();
                finish();
            }
        }, 100);

        audio.addEventListener("ended", () => finish(), { once: true });
        audio.addEventListener(
            "error",
            () => finish(new Error("Voice playback failed.")),
            { once: true }
        );
        audio.play().catch(finish);
    });
}


async function speakDoshieReply(text) {
    const cleanText = cleanSpeechText(text).slice(0, 700);
    if (!cleanText) return;

    stopDoshieVoice();
    const requestToken = voiceRequestToken;
    const engine = document.getElementById("voiceEngine");
    const useClone = (engine?.value || DoshieSettings.voice_engine || "clone") === "clone";

    if (useClone) {
        try {
            const chunks = splitSpeechChunks(cleanText);
            let pending = queuedCloneSpeech(chunks[0]);

            for (let index = 0; index < chunks.length; index += 1) {
                const result = await pending;
                if (requestToken !== voiceRequestToken) return;
                if (result.error) throw result.error;

                pending = index + 1 < chunks.length
                    ? queuedCloneSpeech(chunks[index + 1])
                    : null;
                await playCloneSpeech(result.blob, requestToken);
            }
            return;
        } catch (error) {
            if (requestToken !== voiceRequestToken) return;
            stopDoshieVoice();
            statusBox.textContent =
                "Using the device voice while Hermes voice is unavailable.";
            setTimeout(() => {
                if (statusBox.textContent.includes("device voice")) {
                    statusBox.textContent = "";
                }
            }, 2500);
        }
    }

    try {
        speakWithDeviceVoice(cleanText);
    } catch (error) {
        statusBox.textContent = "Voice playback is not available on this device.";
    }
}


function stopDoshieVoice() {
    voiceRequestToken += 1;

    if (activeVoiceAudio) {
        activeVoiceAudio.pause();
        activeVoiceAudio.currentTime = 0;
        activeVoiceAudio = null;
    }

    if (activeVoiceUrl) {
        URL.revokeObjectURL(activeVoiceUrl);
        activeVoiceUrl = null;
    }

    if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
    }
}


function applyDoshieMode() {
    const mode =
        document.getElementById("DoshieMode").value;

    const preset =
        document.getElementById("voicePreset");

    if (mode === "family") {
        preset.value = "calm";
    }

    if (mode === "tech") {
        preset.value = "tech";
    }

    if (mode === "gaming") {
        preset.value = "dino";
    }

    if (mode === "normal") {
        preset.value = "custom";
    }

    applyVoicePreset();
}


function applyVoiceIdentity() {
    const identity = document.getElementById("voiceIdentity")?.value || "hermes";
    const engine = document.getElementById("voiceEngine");
    const preset = document.getElementById("voicePreset");
    const rate = document.getElementById("voiceRate");
    const pitch = document.getElementById("voicePitch");

    if (identity === "hermes") {
        engine.value = "clone";
        preset.value = "calm";
        rate.value = 0.9;
        pitch.value = 0.9;
    } else if (identity === "Doshie") {
        engine.value = "device";
        preset.value = "dino";
        rate.value = 0.95;
        pitch.value = 1.08;
    } else {
        engine.value = "device";
        preset.value = "custom";
    }

    updateVoiceControls();
}


function applyVoicePreset() {
    const preset =
        document.getElementById("voicePreset").value;

    const rate =
        document.getElementById("voiceRate");

    const pitch =
        document.getElementById("voicePitch");

    if (preset === "calm") {
        rate.value = 0.92;
        pitch.value = 1.0;
    }

    if (preset === "tech") {
        rate.value = 1.0;
        pitch.value = 1.0;
    }

    if (preset === "dino") {
        rate.value = 0.95;
        pitch.value = 1.08;
    }
}


function testVoice() {
    DoshieSettings.voice_identity =
        document.getElementById("voiceIdentity")?.value || "hermes";
    DoshieSettings.voice_engine =
        document.getElementById("voiceEngine").value;
    DoshieSettings.voice_rate = parseFloat(
        document.getElementById("voiceRate").value
    );
    DoshieSettings.voice_pitch = parseFloat(
        document.getElementById("voicePitch").value
    );

    statusBox.textContent = DoshieSettings.voice_engine === "clone"
        ? "Preparing Hermes voice..."
        : "Playing the device voice...";

    speakDoshieReply(
        "Hello Hermes. This is Doshie, speaking with your private local voice."
    ).finally(() => {
        setTimeout(() => {
            if (statusBox.textContent.includes("voice")) {
                statusBox.textContent = "";
            }
        }, 1500);
    });
}


let spotifyRefreshTimer = null;
let spotifyIsPlaying = false;
let spotifyNowPlayingBusy = false;
let spotifyControlBusy = false;


async function spotifyApi(path, options = {}) {
    const method = options.method || "GET";
    const url = new URL(path, window.location.origin);
    url.searchParams.set("profile", activeProfile);

    const fetchOptions = { method };
    if (method !== "GET") {
        fetchOptions.headers = { "Content-Type": "application/json" };
        fetchOptions.body = JSON.stringify({
            ...(options.body || {}),
            profile: activeProfile
        });
    }

    const response = await fetch(url.pathname + url.search, fetchOptions);
    let data = {};
    try {
        data = await response.json();
    } catch (error) {
        data = {};
    }
    if (!response.ok) {
        throw new Error(data.error || "Spotify request failed.");
    }
    return data;
}


function closeSpotify() {
    if (spotifyRefreshTimer) {
        clearInterval(spotifyRefreshTimer);
        spotifyRefreshTimer = null;
    }
    const panel = document.getElementById("spotifyPanel");
    panel.style.display = "none";
    if (window.showChatHome) window.showChatHome();
}


async function openSpotify() {
    if (window.showChatHome) window.showChatHome();
    document.getElementById("spotifyPanel").style.display = "block";
    await loadSpotifyStatus();
}


function setSpotifyStatus(message) {
    document.getElementById("spotifyStatusText").textContent = message;
}


async function copySpotifyCallback() {
    const callback = document.getElementById("spotifyCallbackUri");
    const uri = callback.textContent.trim();
    if (!uri) {
        setSpotifyStatus("The Redirect URI is not ready yet.");
        return;
    }

    try {
        await navigator.clipboard.writeText(uri);
        setSpotifyStatus("Redirect URI copied. Paste it into Spotify.");
    } catch (error) {
        setSpotifyStatus(
            "Press and hold the Redirect URI, then choose Copy."
        );
    }
}


async function loadSpotifyStatus() {
    const setup = document.getElementById("spotifySetupSection");
    const player = document.getElementById("spotifyPlayerSection");
    const connectButton = document.getElementById("spotifyConnectButton");

    try {
        const data = await spotifyApi("/spotify/status");
        document.getElementById("spotifyCallbackUri").textContent =
            data.callback_uri || "";
        document.getElementById("spotifyClientId").value =
            data.client_id || "";

        setup.hidden = !!data.connected;
        player.hidden = !data.connected;
        connectButton.disabled = !data.callback_supported;

        if (!data.callback_supported) {
            setSpotifyStatus(
                "Setup must be opened on the TECRA at " +
                "http://127.0.0.1:5000."
            );
        } else if (!data.configured) {
            setSpotifyStatus(
                "Add the Client ID from your Spotify developer app."
            );
        } else if (!data.connected) {
            setSpotifyStatus(
                "Ready to connect " + activeProfileFirstName() + "'s Spotify."
            );
        } else {
            const accountName = data.account?.name || "Spotify";
            setSpotifyStatus(
                "Connected as " + accountName + " for " +
                activeProfileFirstName() + "."
            );
            await Promise.all([
                loadSpotifyNowPlaying(),
                loadSpotifyPlaylists()
            ]);
        }

        if (spotifyRefreshTimer) clearInterval(spotifyRefreshTimer);
        if (data.connected) {
            spotifyRefreshTimer = setInterval(
                loadSpotifyNowPlaying,
                15000
            );
        }
    } catch (error) {
        setup.hidden = false;
        player.hidden = true;
        setSpotifyStatus(error.message);
    }
}


async function saveAndConnectSpotify() {
    const clientId =
        document.getElementById("spotifyClientId").value.trim();
    if (!clientId) {
        setSpotifyStatus("Paste the Spotify Client ID first.");
        document.getElementById("spotifyClientId").focus();
        return;
    }

    try {
        setSpotifyStatus("Saving the Client ID privately...");
        await spotifyApi("/spotify/config", {
            method: "POST",
            body: { client_id: clientId }
        });
        setSpotifyStatus("Opening Spotify sign-in...");
        const data = await spotifyApi("/spotify/connect", {
            method: "POST"
        });
        window.location.assign(data.authorize_url);
    } catch (error) {
        setSpotifyStatus(error.message);
    }
}


async function saveSpotifyClientId() {
    const clientId =
        document.getElementById("spotifyClientId").value.trim();
    try {
        await spotifyApi("/spotify/config", {
            method: "POST",
            body: { client_id: clientId }
        });
        setSpotifyStatus("Spotify Client ID saved privately.");
        await loadSpotifyStatus();
    } catch (error) {
        setSpotifyStatus(error.message);
    }
}


async function connectSpotify() {
    try {
        setSpotifyStatus("Opening Spotify authorization...");
        const data = await spotifyApi("/spotify/connect", {
            method: "POST"
        });
        window.location.assign(data.authorize_url);
    } catch (error) {
        setSpotifyStatus(error.message);
    }
}


async function disconnectSpotify() {
    const confirmed = window.confirm(
        "Disconnect Spotify from " + activeProfileFirstName() + "'s profile?"
    );
    if (!confirmed) return;

    try {
        await spotifyApi("/spotify/disconnect", { method: "POST" });
        await loadSpotifyStatus();
    } catch (error) {
        setSpotifyStatus(error.message);
    }
}


function spotifySafeImage(value) {
    try {
        const url = new URL(value);
        return url.protocol === "https:" ? url.href : "/static/Doshie-icon.svg";
    } catch (error) {
        return "/static/Doshie-icon.svg";
    }
}


function formatSpotifyTime(milliseconds) {
    const seconds = Math.max(0, Math.floor(Number(milliseconds || 0) / 1000));
    return Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0");
}


function updateSpotifyPlaybackButton() {
    const button = document.getElementById("spotifyPlayPauseButton");
    if (!button) return;
    button.textContent = spotifyIsPlaying ? "⏸" : "▶";
    button.setAttribute("aria-label", spotifyIsPlaying ? "Pause" : "Play");
}


async function loadSpotifyNowPlaying() {
    if (spotifyNowPlayingBusy) return;
    spotifyNowPlayingBusy = true;
    try {
        const data = await spotifyApi("/spotify/now-playing");
        const track = data.track || {};
        const art = document.getElementById("spotifyAlbumArt");
        const title = document.getElementById("spotifyTrackName");
        const artist = document.getElementById("spotifyArtistName");
        const device = document.getElementById("spotifyDeviceName");
        const state = document.getElementById("spotifyPlaybackState");
        const progress = document.getElementById("spotifyProgress");
        const timeCopy = document.getElementById("spotifyTime");

        if (!data.active) {
            spotifyIsPlaying = false;
            art.src = "/static/Doshie-icon.svg";
            title.textContent = "Nothing playing";
            artist.textContent = "Open Spotify on a device";
            state.textContent = "Not playing";
            device.textContent = "No active player";
            progress.max = 1;
            progress.value = 0;
            timeCopy.textContent = "0:00 / 0:00";
            updateSpotifyPlaybackButton();
            return;
        }

        spotifyIsPlaying = !!data.is_playing;
        const duration = Math.max(1, Number(track.duration_ms || 1));
        const position = Math.min(duration, Number(data.progress_ms || 0));
        art.src = spotifySafeImage(track.image);
        art.onerror = () => { art.src = "/static/Doshie-icon.svg"; };
        title.textContent = track.name || "Unknown track";
        artist.textContent =
            [track.artists, track.album].filter(Boolean).join(" · ") || "Spotify";
        state.textContent = spotifyIsPlaying ? "Playing" : "Paused";
        device.textContent = data.device?.name || "Spotify device";
        progress.max = duration;
        progress.value = position;
        timeCopy.textContent =
            formatSpotifyTime(position) + " / " + formatSpotifyTime(duration);
        updateSpotifyPlaybackButton();
    } catch (error) {
        setSpotifyStatus(error.message);
    } finally {
        spotifyNowPlayingBusy = false;
    }
}


function spotifyTogglePlayback() {
    return spotifyControl(spotifyIsPlaying ? "pause" : "play");
}


async function spotifyControl(
    action,
    uri = "",
    contextUri = ""
) {
    if (spotifyControlBusy) return;
    spotifyControlBusy = true;
    document.querySelectorAll(".spotify-control").forEach(button => {
        button.disabled = true;
    });
    if (action === "play") spotifyIsPlaying = true;
    if (action === "pause") spotifyIsPlaying = false;
    updateSpotifyPlaybackButton();

    try {
        await spotifyApi("/spotify/control", {
            method: "POST",
            body: {
                action,
                uri,
                context_uri: contextUri
            }
        });
        const labels = {
            play: "Playing", pause: "Paused",
            next: "Skipping…", previous: "Going back…"
        };
        setSpotifyStatus(labels[action] || "Spotify updated.");
        window.setTimeout(loadSpotifyNowPlaying, 500);
    } catch (error) {
        setSpotifyStatus(error.message);
        window.setTimeout(loadSpotifyNowPlaying, 100);
    } finally {
        spotifyControlBusy = false;
        document.querySelectorAll(".spotify-control").forEach(button => {
            button.disabled = false;
        });
    }
}


function spotifyItemCard(item, playlist = false) {
    const row = document.createElement("div");
    row.className = "spotify-item";

    const image = document.createElement("img");
    image.src = spotifySafeImage(item.image);
    image.alt = "";

    const copy = document.createElement("div");
    copy.className = "spotify-item-copy";

    const title = document.createElement("strong");
    title.textContent = item.name || "Untitled";

    const detail = document.createElement("span");
    detail.textContent = playlist
        ? ((item.owner || "Spotify") +
            (item.total ? " · " + item.total + " items" : ""))
        : ([item.artists, item.album].filter(Boolean).join(" · "));

    const play = document.createElement("button");
    play.className = "tool";
    play.textContent = "Play";
    play.addEventListener("click", () => {
        if (playlist) {
            spotifyControl("play", "", item.uri || "");
        } else {
            spotifyControl("play", item.uri || "");
        }
    });

    copy.append(title, detail);
    row.append(image, copy, play);
    return row;
}


async function searchSpotify() {
    const query =
        document.getElementById("spotifySearchInput").value.trim();
    const list = document.getElementById("spotifySearchResults");
    if (!query) {
        setSpotifyStatus("Enter a song, artist, or album.");
        return;
    }

    list.textContent = "Searching...";
    try {
        const data = await spotifyApi(
            "/spotify/search?q=" + encodeURIComponent(query)
        );
        list.replaceChildren();
        if (!data.length) {
            list.textContent = "No matching songs found.";
            return;
        }
        data.forEach(item => {
            list.appendChild(spotifyItemCard(item));
        });
    } catch (error) {
        list.textContent = "";
        setSpotifyStatus(error.message);
    }
}


async function loadSpotifyPlaylists() {
    const list = document.getElementById("spotifyPlaylistList");
    list.textContent = "Loading playlists...";
    try {
        const data = await spotifyApi("/spotify/playlists");
        list.replaceChildren();
        if (!data.length) {
            list.textContent = "No playlists found.";
            return;
        }
        data.forEach(item => {
            list.appendChild(spotifyItemCard(item, true));
        });
    } catch (error) {
        list.textContent = "";
        setSpotifyStatus(error.message);
    }
}


const adminReplyMetrics = [];

function recordReplyMetric(milliseconds) {
    const value = Math.max(0, Number(milliseconds) || 0);
    adminReplyMetrics.push(value);
    if (adminReplyMetrics.length > 20) adminReplyMetrics.shift();
    const speed = document.getElementById("adminReplySpeed");
    const detail = document.getElementById("adminReplyDetail");
    if (!speed || !detail) return;
    const average = adminReplyMetrics.reduce((sum, item) => sum + item, 0)
        / adminReplyMetrics.length;
    speed.textContent = (value / 1000).toFixed(1) + " seconds";
    detail.textContent = "Latest reply · " + (average / 1000).toFixed(1)
        + "s average across " + adminReplyMetrics.length + " message(s).";
}

function closeAdminControl() {
    const panel = document.getElementById("adminPanel");
    if (panel) panel.style.display = "none";
    if (window.showChatHome) window.showChatHome();
}

function openAdminControl() {
    const record = profileRecord(activeProfile);
    if (!record || !record.is_admin) {
        if (statusBox) statusBox.textContent = "Administrator access is required.";
        return;
    }
    const panel = document.getElementById("adminPanel");
    if (!panel) {
        window.location.href = "/control";
        return;
    }
    if (window.showChatHome) window.showChatHome();
    panel.style.display = "block";
    const adminBrain = document.getElementById("adminBrainMode");
    const chatBrain = document.getElementById("brainMode");
    if (adminBrain && chatBrain) adminBrain.value = chatBrain.value;
    refreshAdminControl();
    loadEquipmentHealth();
    loadAgentFoundry();
}


function talkToDoshieFromControl() {
    const panel = document.getElementById("adminPanel");
    if (panel) panel.style.display = "none";
    if (window.showChatHome) window.showChatHome();
    const chatInput = document.getElementById("input");
    if (chatInput) chatInput.focus({preventScroll: true});
}


function equipmentHealthRow(labelText, valueText, needsAttention = false) {
    const row = document.createElement("div");
    row.className = "admin-health-row";
    row.classList.toggle("needs-attention", needsAttention);
    const label = document.createElement("span");
    const value = document.createElement("strong");
    label.textContent = labelText;
    value.textContent = valueText;
    row.append(label, value);
    return row;
}


async function loadEquipmentHealth() {
    const summary = document.getElementById("equipmentHealthSummary");
    const details = document.getElementById("equipmentHealthDetails");
    const alerts = document.getElementById("equipmentHealthAlerts");
    if (!summary || !details || !alerts) return;
    try {
        const response = await fetch(
            "/equipment-health?profile=" + encodeURIComponent(activeProfile)
        );
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Health check failed.");
        const equipment = data.equipment || {};
        summary.textContent = equipment.hostname + " · "
            + equipment.os + " " + equipment.os_release
            + " · " + (equipment.overall === "healthy" ? "Healthy" : "Needs attention");
        details.replaceChildren(
            equipmentHealthRow(
                "CPU",
                equipment.cpu.percent + "% · " + equipment.cpu.logical_cores + " logical cores",
                equipment.cpu.state !== "healthy"
            ),
            equipmentHealthRow(
                "Memory",
                equipment.memory.used_gb + " / " + equipment.memory.total_gb + " GB",
                equipment.memory.state !== "healthy"
            ),
            equipmentHealthRow(
                "Storage",
                equipment.disk.free_gb + " GB free · " + equipment.disk.percent + "% used",
                equipment.disk.state !== "healthy"
            ),
            equipmentHealthRow(
                "Temperature",
                equipment.temperature_c == null ? "Not reported" : equipment.temperature_c + "°C",
                equipment.temperature_c != null && equipment.temperature_c >= 85
            ),
            equipmentHealthRow(
                "Battery",
                equipment.battery
                    ? equipment.battery.percent + "% · " + (equipment.battery.plugged_in ? "Plugged in" : "On battery")
                    : "Not reported"
            )
        );
        alerts.textContent = (equipment.alerts || []).join(" ") || "No equipment alerts.";
    } catch (error) {
        summary.textContent = "Could not inspect equipment.";
        details.replaceChildren();
        alerts.textContent = error.message;
    }
}


function setAdminBrainMode() {
    const adminBrain = document.getElementById("adminBrainMode");
    const chatBrain = document.getElementById("brainMode");
    if (!adminBrain || !chatBrain) return;
    chatBrain.value = adminBrain.value;
    saveBrainMode();
}

async function refreshAdminControl() {
    const summary = document.getElementById("adminControlSummary");
    const checks = document.getElementById("adminHealthChecks");
    try {
        const response = await fetch("/health");
        const data = await response.json();
        summary.textContent = data.online
            ? "All core systems are ready."
            : "Doshie is running with one or more degraded checks.";
        document.getElementById("adminModelName").textContent =
            data.model || "Local model";
        const brains = data.brain_models || {};
        document.getElementById("adminModelDetail").textContent =
            "Fast: " + (brains.fast || "automatic")
            + " · Coding: " + (brains.coding || "automatic")
            + " · Advanced: " + (brains.advanced || "automatic");
        checks.replaceChildren();
        Object.entries(data.checks || {}).forEach(([name, ready]) => {
            const row = document.createElement("div");
            row.className = "admin-health-row";
            const label = document.createElement("span");
            const state = document.createElement("strong");
            label.textContent = name.replaceAll("_", " ");
            state.textContent = ready ? "Ready" : "Needs attention";
            row.classList.toggle("needs-attention", !ready);
            row.append(label, state);
            checks.appendChild(row);
        });
    } catch (error) {
        summary.textContent = "Could not load system health.";
        checks.textContent = error.message;
    }
}

async function createMigrationPackage() {
    const status = document.getElementById("migrationStatus");
    status.textContent = "Creating and verifying migration package...";
    try {
        const response = await fetch("/admin/migration", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({profile: activeProfile})
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Migration failed.");
        status.textContent = "Ready: " + data.archive;
    } catch (error) {
        status.textContent = error.message;
    }
}


let adminAgents = [];
let activeAgentTestId = "";

function agentApiProfile() {
    return encodeURIComponent(activeProfile || "Hermes");
}

async function loadAgentFoundry() {
    const list = document.getElementById("agentList");
    const status = document.getElementById("agentFoundryStatus");
    if (!list) return;
    try {
        const response = await fetch("/admin/agents?profile=" + agentApiProfile());
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Could not load Agent Foundry.");
        adminAgents = Array.isArray(data.agents) ? data.agents : [];
        status.textContent = adminAgents.length
            ? adminAgents.length + " local specialist(s) configured."
            : "No specialists yet. Create the first one.";
        renderAgentList();
    } catch (error) {
        status.textContent = error.message;
        list.replaceChildren();
    }
}

function agentCapabilityLabel(value) {
    const labels = {
        memory_read: "Memory read",
        memory_write: "Memory proposal",
        service_health: "System health",
        project_read: "Project reader",
        code_proposals: "Code proposals",
        web_research: "Web research"
    };
    return labels[value] || value;
}

function renderAgentList() {
    const list = document.getElementById("agentList");
    list.replaceChildren();
    if (!adminAgents.length) {
        const empty = document.createElement("span");
        empty.className = "agent-empty";
        empty.textContent = "Your specialist AIs will appear here.";
        list.appendChild(empty);
        return;
    }

    adminAgents.forEach(agent => {
        const card = document.createElement("article");
        card.className = "agent-tile";
        card.style.setProperty("--agent-accent", agent.accent || "#35f2d0");
        card.classList.toggle("agent-disabled", !agent.enabled);

        const identity = document.createElement("div");
        identity.className = "agent-identity";
        const light = document.createElement("span");
        light.className = "agent-light";
        const copy = document.createElement("div");
        const name = document.createElement("strong");
        name.textContent = agent.name;
        const purpose = document.createElement("p");
        purpose.textContent = agent.purpose;
        copy.append(name, purpose);
        identity.append(light, copy);

        const badges = document.createElement("div");
        badges.className = "agent-badges";
        [
            (agent.model_mode || "auto") + " brain",
            (agent.memory_scope || "none") + " memory",
            agent.enabled ? "online" : "paused"
        ].forEach(value => {
            const badge = document.createElement("span");
            badge.textContent = value;
            badges.appendChild(badge);
        });
        (agent.capabilities || []).forEach(value => {
            const badge = document.createElement("span");
            badge.textContent = agentCapabilityLabel(value);
            badges.appendChild(badge);
        });

        const actions = document.createElement("div");
        actions.className = "admin-actions";
        const test = document.createElement("button");
        test.type = "button";
        test.className = "tool";
        test.textContent = "Test";
        test.disabled = !agent.enabled;
        test.addEventListener("click", () => openAgentTest(agent.id));
        const edit = document.createElement("button");
        edit.type = "button";
        edit.className = "tool";
        edit.textContent = "Edit";
        edit.addEventListener("click", () => openAgentEditor(agent.id));
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "tool agent-delete-button";
        remove.textContent = "Delete";
        remove.addEventListener("click", () => deleteAgent(agent.id));
        actions.append(test, edit, remove);

        card.append(identity, badges, actions);
        list.appendChild(card);
    });
}

function openAgentEditor(agentId = "") {
    const form = document.getElementById("agentEditor");
    const agent = adminAgents.find(item => item.id === agentId);
    document.getElementById("agentEditorTitle").textContent =
        agent ? "Edit " + agent.name : "Create a new AI";
    document.getElementById("agentId").value = agent?.id || "";
    document.getElementById("agentName").value = agent?.name || "";
    document.getElementById("agentPurpose").value = agent?.purpose || "";
    document.getElementById("agentBrain").value = agent?.model_mode || "auto";
    document.getElementById("agentMemory").value = agent?.memory_scope || "none";
    document.getElementById("agentAccent").value = agent?.accent || "#35f2d0";
    document.getElementById("agentInstructions").value = agent?.instructions || "";
    document.getElementById("agentEnabled").checked = agent?.enabled ?? true;
    const selected = new Set(agent?.capabilities || []);
    form.querySelectorAll(".agent-capabilities input").forEach(input => {
        input.checked = selected.has(input.value);
    });
    form.hidden = false;
    closeAgentTest();
    form.scrollIntoView({behavior: "smooth", block: "nearest"});
    document.getElementById("agentName").focus({preventScroll: true});
}

function closeAgentEditor() {
    document.getElementById("agentEditor").hidden = true;
}

async function saveAgent(event) {
    event.preventDefault();
    const status = document.getElementById("agentFoundryStatus");
    const capabilities = Array.from(
        document.querySelectorAll(".agent-capabilities input:checked"),
        input => input.value
    );
    const payload = {
        profile: activeProfile,
        id: document.getElementById("agentId").value,
        name: document.getElementById("agentName").value,
        purpose: document.getElementById("agentPurpose").value,
        model_mode: document.getElementById("agentBrain").value,
        memory_scope: document.getElementById("agentMemory").value,
        accent: document.getElementById("agentAccent").value,
        instructions: document.getElementById("agentInstructions").value,
        enabled: document.getElementById("agentEnabled").checked,
        capabilities
    };
    status.textContent = "Saving protected agent definition...";
    try {
        const response = await fetch("/admin/agents", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Could not save this AI.");
        closeAgentEditor();
        status.textContent = data.agent.name + " is ready.";
        await loadAgentFoundry();
    } catch (error) {
        status.textContent = error.message;
    }
}

async function deleteAgent(agentId) {
    const agent = adminAgents.find(item => item.id === agentId);
    if (!agent || !window.confirm("Delete " + agent.name + "? This cannot be undone.")) return;
    const status = document.getElementById("agentFoundryStatus");
    try {
        const response = await fetch("/admin/agents/" + encodeURIComponent(agentId), {
            method: "DELETE",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({profile: activeProfile})
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Could not delete this AI.");
        status.textContent = agent.name + " was removed.";
        await loadAgentFoundry();
    } catch (error) {
        status.textContent = error.message;
    }
}

function openAgentTest(agentId) {
    const agent = adminAgents.find(item => item.id === agentId);
    if (!agent) return;
    activeAgentTestId = agent.id;
    document.getElementById("agentTestTitle").textContent = "Protected test · " + agent.name;
    document.getElementById("agentTestReply").textContent =
        "This test may answer and propose work, but cannot change the computer.";
    document.getElementById("agentTestMessage").value = "";
    document.getElementById("agentTestConsole").hidden = false;
    closeAgentEditor();
    document.getElementById("agentTestConsole").scrollIntoView({
        behavior: "smooth",
        block: "nearest"
    });
    document.getElementById("agentTestMessage").focus({preventScroll: true});
}

function closeAgentTest() {
    activeAgentTestId = "";
    document.getElementById("agentTestConsole").hidden = true;
}

async function runAgentTest() {
    const message = document.getElementById("agentTestMessage").value.trim();
    const reply = document.getElementById("agentTestReply");
    if (!activeAgentTestId || !message) {
        reply.textContent = "Type a test request first.";
        return;
    }
    reply.textContent = "Thinking locally on Tecra...";
    const started = performance.now();
    try {
        const response = await fetch(
            "/admin/agents/" + encodeURIComponent(activeAgentTestId) + "/test",
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({profile: activeProfile, message})
            }
        );
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Agent test failed.");
        reply.textContent = data.reply;
        recordReplyMetric(performance.now() - started);
    } catch (error) {
        reply.textContent = error.message;
    }
}

function composerElement() {
    return document.getElementById("composer");
}

function setComposerToolsOpen(open) {
    const composer = composerElement();
    const button = document.getElementById("composerMoreButton");
    if (!composer || !button) return;
    composer.classList.toggle("composer-tools-open", !!open);
    button.setAttribute("aria-expanded", open ? "true" : "false");
    button.setAttribute(
        "aria-label",
        open ? "Hide chat controls" : "Show chat controls"
    );
}

function toggleComposerTools() {
    const composer = composerElement();
    if (!composer) return;
    if (composer.classList.contains("composer-minimized")) {
        setComposerMinimized(false);
    }
    setComposerToolsOpen(
        !composer.classList.contains("composer-tools-open")
    );
}

function setComposerMinimized(minimized) {
    const composer = composerElement();
    const button = document.getElementById("composerCollapseButton");
    if (!composer || !button) return;
    composer.classList.toggle("composer-minimized", !!minimized);
    if (minimized) setComposerToolsOpen(false);
    button.textContent = minimized ? "💬" : "—";
    button.setAttribute(
        "aria-label",
        minimized ? "Open chat box" : "Minimize chat box"
    );
    button.title = minimized ? "Open chat box" : "Minimize chat box";
    if (!minimized) {
        window.setTimeout(() => {
            document.getElementById("input")?.focus({preventScroll: true});
            keepLatestMessageVisible();
        }, 80);
    }
}

function toggleComposerMinimized() {
    const composer = composerElement();
    if (!composer) return;
    setComposerMinimized(
        !composer.classList.contains("composer-minimized")
    );
}

function keepLatestMessageVisible() {
    const messages = document.getElementById("messages");
    if (!messages) return;
    messages.scrollTop = messages.scrollHeight;
}

function syncMobileVisualViewport() {
    const viewport = window.visualViewport;
    const height = viewport ? viewport.height : window.innerHeight;
    document.documentElement.style.setProperty(
        "--Doshie-visual-height",
        Math.max(320, Math.round(height)) + "px"
    );
    const keyboardOpen = !!viewport && (
        window.innerHeight - viewport.height > 120
    );
    document.body.classList.toggle("keyboard-open", keyboardOpen);
    if (keyboardOpen && document.activeElement?.id === "input") {
        window.setTimeout(keepLatestMessageVisible, 40);
    }
}

function installMobileComposerControls() {
    const input = document.getElementById("input");
    if (!input) return;
    input.addEventListener("focus", () => {
        setComposerMinimized(false);
        syncMobileVisualViewport();
        window.setTimeout(keepLatestMessageVisible, 120);
    });
    document.addEventListener("pointerdown", event => {
        const composer = composerElement();
        if (
            composer?.classList.contains("composer-tools-open") &&
            !composer.contains(event.target)
        ) {
            setComposerToolsOpen(false);
        }
    });
    window.addEventListener("resize", syncMobileVisualViewport);
    window.visualViewport?.addEventListener(
        "resize",
        syncMobileVisualViewport
    );
    window.visualViewport?.addEventListener(
        "scroll",
        syncMobileVisualViewport
    );
    syncMobileVisualViewport();
}

installMobileComposerControls();

let adminTerminalSession = "";
let adminTerminalPollTimer = 0;

function setAdminTerminalCommand(command) {
    const field = document.getElementById("adminTerminalInput");
    if (!field) return;
    field.value = command;
    field.focus();
}

async function startAdminTerminal() {
    const output = document.getElementById("adminTerminalOutput");
    if (!output) return;
    if (adminTerminalSession) {
        await pollAdminTerminal();
        return;
    }
    output.textContent = "Opening user-level terminal...";
    try {
        const response = await fetch("/admin/terminal/start", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({profile: activeProfile, cwd: "/home/hermes-duran/Doshie"}),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not open terminal.");
        adminTerminalSession = data.session_id;
        output.textContent = data.message + "\\n$ cd " + data.cwd + "\\n";
        await pollAdminTerminal();
    } catch (error) {
        output.textContent = "Terminal error: " + error.message;
    }
}

async function pollAdminTerminal() {
    if (!adminTerminalSession) return;
    try {
        const response = await fetch(
            "/admin/terminal/output?profile=" + encodeURIComponent(activeProfile) +
            "&session_id=" + encodeURIComponent(adminTerminalSession)
        );
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Terminal unavailable.");
        const output = document.getElementById("adminTerminalOutput");
        if (output && data.output) {
            output.textContent += data.output;
            output.scrollTop = output.scrollHeight;
        }
        if (data.alive) {
            adminTerminalPollTimer = window.setTimeout(pollAdminTerminal, 700);
        } else {
            adminTerminalSession = "";
        }
    } catch (error) {
        const output = document.getElementById("adminTerminalOutput");
        if (output) output.textContent += "\\n[terminal disconnected: " + error.message + "]\\n";
        adminTerminalSession = "";
    }
}

async function sendAdminTerminalInput() {
    const field = document.getElementById("adminTerminalInput");
    if (!field) return;
    if (!adminTerminalSession) {
        await startAdminTerminal();
        if (!adminTerminalSession) return;
    }
    const input = field.value;
    if (!input) return;
    try {
        const response = await fetch("/admin/terminal/input", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                profile: activeProfile,
                session_id: adminTerminalSession,
                input: input + "\\n",
            }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not send command.");
        field.value = "";
        await pollAdminTerminal();
    } catch (error) {
        const output = document.getElementById("adminTerminalOutput");
        if (output) output.textContent += "\\n[input error: " + error.message + "]\\n";
    }
}

async function stopAdminTerminal() {
    if (!adminTerminalSession) return;
    window.clearTimeout(adminTerminalPollTimer);
    try {
        await fetch("/admin/terminal/stop", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({profile: activeProfile, session_id: adminTerminalSession}),
        });
    } finally {
        adminTerminalSession = "";
        const output = document.getElementById("adminTerminalOutput");
        if (output) output.textContent = "Terminal closed.";
    }
}

document.getElementById("adminTerminalInput")?.addEventListener("keydown", event => {
    if (event.key === "Enter") {
        event.preventDefault();
        sendAdminTerminalInput();
    }
});

async function loadSettings() {
    try {
        const response = await fetch("/settings");
        const data = await response.json();

        DoshieSettings = data;

        document.getElementById("autoMemory").checked =
            !!data.auto_memory;

        document.getElementById("speakReplies").checked =
            !!data.speak_replies;

        document.getElementById("voiceIdentity").value =
            data.voice_identity || "hermes";

        document.getElementById("voiceEngine").value =
            data.voice_engine || "clone";

        document.getElementById("voiceRate").value =
            data.voice_rate ?? 0.9;

        document.getElementById("voicePitch").value =
            data.voice_pitch ?? 0.9;


        document.getElementById("voicePreset").value =
            data.voice_preset || "custom";


        document.getElementById("DoshieMode").value =
            data.mode || "family";

        document.getElementById("weatherLocation").value =
            data.default_weather_location || "El Paso";

        updateVoiceControls();

    } catch (error) {
        console.log("Could not load settings.");
    }
}


function closeSettings() {
    const panel = document.getElementById("settingsPanel");
    panel.style.display = "none";
    panel.querySelectorAll("details").forEach(group => {
        group.open = false;
    });
    if (window.showChatHome) window.showChatHome();
}


function installSettingsAccordion() {
    document.querySelectorAll("#settingsPanel details").forEach(group => {
        group.addEventListener("toggle", () => {
            if (!group.open) return;
            document.querySelectorAll("#settingsPanel details").forEach(other => {
                if (other !== group) other.open = false;
            });
        });
    });
}


function toggleSettings() {
    const panel = document.getElementById("settingsPanel");
    const opening = window.getComputedStyle(panel).display === "none";

    if (!opening) {
        closeSettings();
        return;
    }

    if (window.showChatHome) window.showChatHome();
    panel.style.display = "block";
    refreshProfileLockControls();
}


function updateSettingsAvatar(profile) {
    setAvatarDisplay(
        document.getElementById("profilePhotoPreview"),
        document.getElementById("profilePhotoInitials"),
        profile
    );
}


function updateProfileSecurityFields() {
    const typeSelect = document.getElementById("profileSecurityType");
    if (!typeSelect) return;
    const kind = typeSelect.value || "none";
    const isNone = kind === "none";
    const isPin = kind === "pin";
    const target = document.getElementById("profileLockTarget");
    const record = profileRecord(target ? target.value : activeProfile);
    const currentKind =
        record && record.auth_type === "password" ? "password" : "PIN";

    document.getElementById("profileCurrentCredentialLabel").textContent =
        "Current " + currentKind + " (if requested)";
    document.getElementById("profileNewCredentialLabel").textContent =
        isPin ? "New PIN" : "New password";
    document.getElementById("profileConfirmCredentialLabel").textContent =
        isPin ? "Confirm new PIN" : "Confirm new password";

    const current = document.getElementById("profileCurrentPin");
    const next = document.getElementById("profileNewPin");
    const confirm = document.getElementById("profileConfirmPin");
    current.inputMode = currentKind === "PIN" ? "numeric" : "text";
    current.placeholder = currentKind;
    [next, confirm].forEach(field => {
        field.disabled = isNone;
        field.inputMode = isPin ? "numeric" : "text";
        field.maxLength = isPin ? 8 : 64;
    });
    next.placeholder = isNone
        ? "No sign-in required"
        : (isPin ? "4–8 digits" : "8–64 characters");
}


async function ensureProfileUnlocked(record) {
    if (!record || !record.locked || record.unlocked) return true;
    const unlocked = await openProfileUnlock(record.name);
    if (unlocked) record.unlocked = true;
    return unlocked;
}


function squareAvatarBlob(file) {
    if (!file || !String(file.type).startsWith("image/")) {
        return Promise.reject(new Error("Choose a PNG, JPEG, or WebP photo."));
    }
    if (file.size > 15 * 1024 * 1024) {
        return Promise.reject(new Error("Choose a photo under 15 MB."));
    }

    return new Promise((resolve, reject) => {
        const objectUrl = URL.createObjectURL(file);
        const image = new Image();
        image.onload = () => {
            const canvas = document.createElement("canvas");
            canvas.width = 256;
            canvas.height = 256;
            const context = canvas.getContext("2d", {alpha: false});
            const sourceSize = Math.min(image.naturalWidth, image.naturalHeight);
            const sourceX = (image.naturalWidth - sourceSize) / 2;
            const sourceY = (image.naturalHeight - sourceSize) / 2;
            context.drawImage(
                image,
                sourceX,
                sourceY,
                sourceSize,
                sourceSize,
                0,
                0,
                256,
                256
            );
            URL.revokeObjectURL(objectUrl);
            canvas.toBlob(blob => {
                if (blob) resolve(blob);
                else reject(new Error("Could not prepare this photo."));
            }, "image/png");
        };
        image.onerror = () => {
            URL.revokeObjectURL(objectUrl);
            reject(new Error("Doshie could not open this photo."));
        };
        image.src = objectUrl;
    });
}


async function uploadProfileAvatar(event) {
    const picker = event.target;
    const status = document.getElementById("profilePhotoStatus");
    const target = document.getElementById("profileLockTarget").value;
    const record = profileRecord(target);
    const file = picker.files && picker.files[0];
    if (!file || !record) return;

    status.textContent = "Preparing your profile photo...";
    try {
        if (!await ensureProfileUnlocked(record)) {
            status.textContent = "Unlock this account to change its photo.";
            return;
        }
        const avatar = await squareAvatarBlob(file);
        const form = new FormData();
        form.append("profile", record.name);
        form.append("avatar", avatar, "profile.png");
        const response = await fetch("/profile-avatar", {
            method: "POST",
            body: form
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Photo upload failed.");
        await refreshProfileCatalog();
        status.textContent = "Profile photo saved.";
    } catch (error) {
        status.textContent = error.message;
    } finally {
        picker.value = "";
    }
}


async function removeProfileAvatar() {
    const status = document.getElementById("profilePhotoStatus");
    const target = document.getElementById("profileLockTarget").value;
    const record = profileRecord(target);
    if (!record || !record.avatar_url) {
        status.textContent = "This account does not have a profile photo.";
        return;
    }
    if (!window.confirm("Remove " + record.name.split(" ")[0] + "'s photo?")) {
        return;
    }

    try {
        if (!await ensureProfileUnlocked(record)) return;
        const response = await fetch("/profile-avatar/remove", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({profile: record.name})
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Could not remove photo.");
        await refreshProfileCatalog();
        status.textContent = "Profile photo removed.";
    } catch (error) {
        status.textContent = error.message;
    }
}


async function refreshHealthSyncControls() {
    const status = document.getElementById("healthSyncStatus");
    const enabled = document.getElementById("healthSyncEnabled");
    if (!status || !enabled) return;
    const record = profileRecord(activeProfile);
    if (!record) return;
    try {
        if (!await ensureProfileUnlocked(record)) {
            status.textContent = "🔒 Unlock this account to view Health permissions.";
            return;
        }
        const online = navigator.onLine ? "true" : "false";
        const response = await fetch(`/health-sync/status?profile=${encodeURIComponent(record.name)}&online=${online}`);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Could not load Health permissions.");
        enabled.checked = !!data.enabled;
        document.querySelectorAll("[data-health-permission]").forEach(box => {
            box.checked = (data.permissions || []).includes(box.value);
            box.disabled = !enabled.checked;
        });
        status.textContent = data.allowed
            ? "🟢 Health sync gate is open for this account."
            : "🔒 Health sync gate is closed: " + (data.reasons || []).join(", ");
    } catch (error) {
        status.textContent = error.message;
    }
}

async function saveHealthSyncControls() {
    const status = document.getElementById("healthSyncStatus");
    const record = profileRecord(activeProfile);
    if (!status || !record) return;
    try {
        if (!await ensureProfileUnlocked(record)) return;
        const enabled = document.getElementById("healthSyncEnabled").checked;
        const permissions = [...document.querySelectorAll("[data-health-permission]:checked")].map(box => box.value);
        const response = await fetch("/health-sync/configure", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({profile: record.name, enabled, permissions})
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Could not save Health permissions.");
        document.querySelectorAll("[data-health-permission]").forEach(box => { box.disabled = !enabled; });
        status.textContent = enabled
            ? "✅ Health consent saved. Online + unlocked rules still apply."
            : "🔒 Health sync disabled for this account.";
    } catch (error) {
        status.textContent = error.message;
    }
}

function refreshProfileLockControls() {
    const target = document.getElementById("profileLockTarget");
    const status = document.getElementById("profileLockStatus");
    const securityType = document.getElementById("profileSecurityType");
    if (!target || !status || !securityType) return;

    const record = profileRecord(target.value || activeProfile);
    if (!record) {
        status.textContent = "Choose an account.";
        return;
    }

    securityType.value = record.locked
        ? (record.auth_type || "pin")
        : "none";
    updateSettingsAvatar(record);
    document.getElementById("profilePhotoStatus").textContent = "";

    if (!record.locked) {
        status.textContent =
            "🔓 " + record.name.split(" ")[0] +
            " signs in without a password.";
    } else if (record.unlocked) {
        status.textContent =
            "🔓 " + profileSecurityLabel(record) +
            " protected and unlocked on this device.";
    } else {
        status.textContent =
            "🔒 " + profileSecurityLabel(record) +
            " protected and locked on this device.";
    }
    updateProfileSecurityFields();
    refreshProfilePreferenceControls(record);
    refreshProfileRecovery();
}


function refreshProfilePreferenceControls(record) {
    const statusInput = document.getElementById("profileStatus");
    if (!statusInput || !record) return;
    const preferences = profilePreferences(record);
    chosenProfileAccent = preferences.accent;

    document.getElementById("customizingProfileName").textContent = record.name;
    statusInput.value = preferences.status;
    document.getElementById("profileAbout").value = preferences.about_me;
    document.getElementById("profileInterests").value =
        preferences.interests || "";
    document.getElementById("profileMusicUrl").value =
        preferences.profile_music_url || "";
    const adminCssControls = document.getElementById("adminCssControls");
    const customCssField = document.getElementById("profileCustomCss");
    const canEditCss = Boolean(record.is_admin);
    adminCssControls.hidden = !canEditCss;
    customCssField.disabled = !canEditCss;
    customCssField.value = canEditCss ? (preferences.custom_css || "") : "";
    document.getElementById("profileTheme").value = preferences.theme;
    document.getElementById("profileCustomColor").value =
        preferences.custom_color;
    document.getElementById("profileFontFamily").value =
        preferences.font_family;
    document.getElementById("profileFontSize").value =
        String(preferences.font_size);
    document.getElementById("profileNewsTopic").value = preferences.news_topic;
    document.getElementById("profileNewsVisible").checked =
        preferences.news_visible;
    document.getElementById("profileAutoLock").value =
        String(preferences.auto_lock_minutes);
    document.getElementById("profileLockOnClose").checked =
        preferences.lock_on_close;
    document.querySelectorAll("#profileAccentOptions [data-accent]").forEach(
        button => button.classList.toggle(
            "selected",
            button.dataset.accent === chosenProfileAccent
        )
    );
    document.getElementById("profilePreferenceStatus").textContent = "";
    renderProfilePreview();
}


function renderProfilePreview() {
    const preview = document.getElementById("profileStylePreview");
    if (!preview) return;
    const target = document.getElementById("profileLockTarget");
    const record = profileRecord(target ? target.value : activeProfile);
    const status = document.getElementById("profileStatus").value.trim();
    const about = document.getElementById("profileAbout").value.trim();
    const interests = document.getElementById("profileInterests").value.trim();
    const musicUrl = document.getElementById("profileMusicUrl").value.trim();
    const theme = document.getElementById("profileTheme").value;
    const tronTheme = theme === "tron";
    const customColor = document.getElementById("profileCustomColor").value;
    const fontFamily = document.getElementById("profileFontFamily").value;
    const fontSize = Number(document.getElementById("profileFontSize").value);

    document.getElementById("tronThemeControls").hidden = !tronTheme;
    document.getElementById("profileFontSizeValue").textContent =
        fontSize + "%";
    preview.dataset.previewTheme = theme;
    preview.style.setProperty(
        "--preview-accent",
        tronTheme
            ? customColor
            : (PROFILE_ACCENTS[chosenProfileAccent] || PROFILE_ACCENTS.mint)
    );
    preview.style.setProperty(
        "--preview-font",
        tronTheme
            ? (PROFILE_FONTS[fontFamily] || PROFILE_FONTS.tech)
            : PROFILE_FONTS.system
    );
    preview.style.setProperty(
        "--preview-font-scale",
        tronTheme ? String(fontSize / 100) : "1"
    );
    document.getElementById("profilePreviewName").textContent =
        record ? record.name : "Profile";
    document.getElementById("profilePreviewStatus").textContent =
        status || "Your status appears here.";
    document.getElementById("profilePreviewAbout").textContent =
        about || "Your About Me appears here.";
    document.getElementById("profilePreviewInterests").textContent =
        interests ? "⭐ " + interests : "Your interests appear here.";
    const musicLink = document.getElementById("profilePreviewMusic");
    musicLink.hidden = !musicUrl;
    musicLink.href = musicUrl || "#";
}


function chooseProfileAccent(accent) {
    if (!PROFILE_ACCENTS[accent]) return;
    chosenProfileAccent = accent;
    document.querySelectorAll("#profileAccentOptions [data-accent]").forEach(
        button => button.classList.toggle(
            "selected",
            button.dataset.accent === accent
        )
    );
    renderProfilePreview();
}


function restoreProfileDefaults() {
    chosenProfileAccent = PROFILE_DEFAULTS.accent;
    document.getElementById("profileStatus").value = PROFILE_DEFAULTS.status;
    document.getElementById("profileAbout").value = PROFILE_DEFAULTS.about_me;
    document.getElementById("profileInterests").value = PROFILE_DEFAULTS.interests;
    document.getElementById("profileMusicUrl").value =
        PROFILE_DEFAULTS.profile_music_url;
    document.getElementById("profileTheme").value = PROFILE_DEFAULTS.theme;
    document.getElementById("profileCustomColor").value = PROFILE_DEFAULTS.custom_color;
    document.getElementById("profileFontFamily").value = PROFILE_DEFAULTS.font_family;
    document.getElementById("profileFontSize").value = String(PROFILE_DEFAULTS.font_size);
    document.getElementById("profileNewsTopic").value = PROFILE_DEFAULTS.news_topic;
    document.getElementById("profileNewsVisible").checked = PROFILE_DEFAULTS.news_visible;
    document.getElementById("profileAutoLock").value = String(PROFILE_DEFAULTS.auto_lock_minutes);
    document.getElementById("profileLockOnClose").checked = PROFILE_DEFAULTS.lock_on_close;
    const cssField = document.getElementById("profileCustomCss");
    if (cssField && !cssField.disabled) {
        cssField.value = "";
        setAdminCustomCss("");
    }
    document.querySelectorAll("#profileAccentOptions [data-accent]").forEach(
        button => button.classList.toggle(
            "selected",
            button.dataset.accent === chosenProfileAccent
        )
    );
    document.getElementById("profilePreferenceStatus").textContent =
        "Defaults are previewed. Save to keep them.";
    renderProfilePreview();
}


async function saveProfilePreferences() {
    const target = document.getElementById("profileLockTarget").value;
    const record = profileRecord(target);
    const status = document.getElementById("profilePreferenceStatus");
    if (!record) return;

    if (!await ensureProfileUnlocked(record)) {
        status.textContent = "Unlock this account to customize it.";
        return;
    }

    const preferences = {
        status: document.getElementById("profileStatus").value,
        about_me: document.getElementById("profileAbout").value,
        interests: document.getElementById("profileInterests").value,
        profile_music_url: document.getElementById("profileMusicUrl").value,
        custom_css: record.is_admin
            ? document.getElementById("profileCustomCss").value
            : "",
        accent: chosenProfileAccent,
        theme: document.getElementById("profileTheme").value,
        custom_color: document.getElementById("profileCustomColor").value,
        font_family: document.getElementById("profileFontFamily").value,
        font_size: Number(document.getElementById("profileFontSize").value),
        news_topic: document.getElementById("profileNewsTopic").value,
        news_visible: document.getElementById("profileNewsVisible").checked,
        auto_lock_minutes:
            Number(document.getElementById("profileAutoLock").value),
        lock_on_close:
            document.getElementById("profileLockOnClose").checked
    };

    status.textContent = "Saving profile...";
    try {
        const response = await fetch("/profile-preferences", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({profile: target, preferences})
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || "Could not save profile.");
        }
        record.preferences = data.preferences;
        if (target === activeProfile) {
            loadedNewsTopic = "";
            applyProfileExperience(record);
        }
        renderAccountChooser();
        refreshProfilePreferenceControls(record);
        status.textContent = "Profile style and auto-lock saved.";
    } catch (error) {
        status.textContent = error.message;
    }
}


function openProfileCustomizer() {
    const panel = document.getElementById("settingsPanel");
    if (window.getComputedStyle(panel).display === "none") toggleSettings();
    document.querySelectorAll("#settingsPanel details").forEach(details => {
        details.open = false;
    });
    const target = document.getElementById("profileLockTarget");
    target.value = activeProfile;
    refreshProfileLockControls();
    const group = document.getElementById("profileCustomizeGroup");
    group.open = true;
    group.scrollIntoView({behavior: "smooth", block: "start"});
}


function toggleCredentialField(id, button) {
    const field = document.getElementById(id);
    if (!field) return;
    const visible = field.type === "text";
    field.type = visible ? "password" : "text";
    button.textContent = visible ? "👁" : "🙈";
    button.setAttribute("aria-pressed", String(!visible));
    button.setAttribute("aria-label", visible ? "Show sign-in value" : "Hide sign-in value");
    field.focus();
}


function clearProfileCredentialFields() {
    ["profileCurrentPin", "profileNewPin", "profileConfirmPin"].forEach(id => {
        document.getElementById(id).value = "";
    });
}


async function refreshProfileRecovery() {
    const target = document.getElementById("profileLockTarget")?.value;
    const current = document.getElementById("profileRecoveryCurrent");
    if (!target || !current) return;
    try {
        const response = await fetch(
            "/recovery/profile?profile=" + encodeURIComponent(target),
            {cache: "no-store"}
        );
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Recovery is unavailable.");
        const contact = data.contact || {};
        const methods = [];
        if (contact.has_email) methods.push("Email " + contact.email_masked);
        if (contact.has_phone) methods.push("Text " + contact.phone_masked);
        current.textContent = methods.length
            ? "Current: " + methods.join(" · ") + ". Blank fields keep these values."
            : "Add an email address, phone number, or both.";
        const delivery = data.delivery || {};
        if (!delivery.email_ready && !delivery.sms_ready) {
            current.textContent += " Owner delivery setup is still required.";
        }
    } catch (error) {
        current.textContent = error.message;
    }
}


async function saveProfileRecovery() {
    const target = document.getElementById("profileLockTarget")?.value;
    const status = document.getElementById("profileRecoveryStatus");
    if (!target || !status) return;
    status.textContent = "Saving recovery methods…";
    try {
        const response = await fetch("/recovery/profile", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                profile: target,
                email: document.getElementById("profileRecoveryEmail").value,
                phone: document.getElementById("profileRecoveryPhone").value
            })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Recovery could not be saved.");
        document.getElementById("profileRecoveryEmail").value = "";
        document.getElementById("profileRecoveryPhone").value = "";
        status.textContent = "Recovery methods saved.";
        await refreshProfileRecovery();
    } catch (error) {
        status.textContent = error.message;
    }
}


async function saveProfileSecurity() {
    const target = document.getElementById("profileLockTarget").value;
    const authType = document.getElementById("profileSecurityType").value;
    const current = document.getElementById("profileCurrentPin").value;
    const credential = document.getElementById("profileNewPin").value;
    const confirmation = document.getElementById("profileConfirmPin").value;
    const status = document.getElementById("profileLockStatus");
    const record = profileRecord(target);

    if (authType === "none") {
        if (!record || !record.locked) {
            status.textContent = "This account already uses no password.";
            return;
        }
        if (!window.confirm("Remove sign-in protection from this account?")) {
            return;
        }
        try {
            await profileLockApi("/profile-lock/remove", {
                profile: target,
                current_credential: current
            });
            clearProfileCredentialFields();
            await refreshProfileCatalog();
            status.textContent = "Sign-in protection removed.";
        } catch (error) {
            status.textContent = error.message;
        }
        return;
    }

    if (authType === "pin" && !/^\\d{4,8}$/.test(credential)) {
        status.textContent = "PIN must be 4–8 digits.";
        return;
    }
    if (
        authType === "password" &&
        (credential.length < 8 || credential.length > 64)
    ) {
        status.textContent = "Password must be 8–64 characters.";
        return;
    }
    if (credential !== confirmation) {
        status.textContent = "The new sign-ins do not match.";
        return;
    }

    status.textContent = "Saving account security...";
    try {
        await profileLockApi("/profile-lock/configure", {
            profile: target,
            auth_type: authType,
            current_credential: current,
            credential
        });
        clearProfileCredentialFields();
        await refreshProfileCatalog();
        status.textContent =
            "🔐 " + (authType === "pin" ? "PIN" : "Password") +
            " saved. This device remains unlocked for now.";
    } catch (error) {
        status.textContent = error.message;
    }
}


async function unlockProfileInside() {
    const target = document.getElementById("profileLockTarget").value;
    const record = profileRecord(target);
    const status = document.getElementById("profileLockStatus");

    if (!record) return;
    if (!record.locked) {
        status.textContent = "This account has no sign-in protection.";
        return;
    }
    if (record.unlocked) {
        status.textContent = target.split(" ")[0] + " is already unlocked here.";
        return;
    }

    const unlocked = await openProfileUnlock(record.name);
    if (!unlocked) {
        status.textContent = "Unlock canceled.";
        return;
    }
    record.unlocked = true;
    if (target === activeProfile) {
        sessionStorage.setItem("Doshie_signed_in_profile", target);
        setProfileInteraction(true);
        hideAccountChooser();
        await loadProfileHistory();
    }
    renderProfileSelectors();
    armProfileAutoLock();
    status.textContent = "🔓 " + target.split(" ")[0] + " is unlocked on this device.";
}


async function lockProfileNow() {
    const target = document.getElementById("profileLockTarget").value;
    const record = profileRecord(target);
    const status = document.getElementById("profileLockStatus");

    if (!record || !record.locked) {
        status.textContent =
            "Choose PIN or password protection before locking this account.";
        return;
    }

    try {
        await profileLockApi("/profile-lock/lock", {profile: target});
        record.unlocked = false;
        renderProfileSelectors();
        status.textContent =
            "🔒 " + target.split(" ")[0] + " is locked on this device.";
        if (target === activeProfile) {
            bringLockedProfileForward(
                target,
                "🔒 " + target.split(" ")[0] + " is locked on this device."
            );
        }
    } catch (error) {
        status.textContent = error.message;
    }
}


async function removeProfileProtection() {
    const target = document.getElementById("profileLockTarget").value;
    const current = document.getElementById("profileCurrentPin").value;
    const record = profileRecord(target);
    const status = document.getElementById("profileLockStatus");

    if (!record || !record.locked) {
        status.textContent = "This account already uses no password.";
        return;
    }
    if (!window.confirm(
        "Remove " + target.split(" ")[0] + "'s sign-in protection?"
    )) {
        return;
    }

    status.textContent = "Removing sign-in protection...";
    try {
        await profileLockApi("/profile-lock/remove", {
            profile: target,
            current_credential: current
        });
        clearProfileCredentialFields();
        await refreshProfileCatalog();
        status.textContent = "Sign-in protection removed.";
        if (target === activeProfile) await loadProfileHistory();
    } catch (error) {
        status.textContent = error.message;
    }
}

let DoshieRestarting = false;


function DoshiePause(milliseconds) {
    return new Promise(resolve => window.setTimeout(resolve, milliseconds));
}


function refreshDoshieApp() {
    statusBox.textContent = "Refreshing Doshie...";
    window.setTimeout(() => window.location.reload(), 120);
}


async function clearDoshieCache() {
    const confirmed = window.confirm(
        "Clear only Doshie's downloaded app cache? " +
        "Memories, profiles, settings, Spotify, and voice stay safe."
    );
    if (!confirmed) return;

    statusBox.textContent = "Clearing Doshie's app cache...";
    try {
        if ("caches" in window) {
            const keys = await window.caches.keys();
            await Promise.all(
                keys.map(key => window.caches.delete(key))
            );
        }

        if ("serviceWorker" in navigator) {
            const registration =
                await navigator.serviceWorker.getRegistration();
            if (registration) await registration.update();
        }

        statusBox.textContent =
            "Cache cleared. Loading the newest Doshie interface...";
        await DoshiePause(350);
        window.location.replace("/?fresh=" + Date.now());
    } catch (error) {
        statusBox.textContent =
            "I could not clear the cache. Try Refresh app instead.";
    }
}


async function restartDoshieApp() {
    if (DoshieRestarting) return;

    const confirmed = window.confirm(
        "Restart Doshie's web service now? This takes about 5–10 seconds. " +
        "Memories, profiles, and the voice recording stay safe."
    );
    if (!confirmed) return;

    DoshieRestarting = true;
    closeSettings();
    statusBox.textContent = "Restarting Doshie...";
    let previousInstance = "";
    let sawOffline = false;

    try {
        const response = await fetch("/system/restart", {
            method: "POST",
            headers: { "X-Doshie-Action": "restart" }
        });
        const data = await response.json();
        if (!response.ok) {
            statusBox.textContent =
                data.error || "Doshie could not restart.";
            DoshieRestarting = false;
            return;
        }
        previousInstance = data.instance || "";
    } catch (error) {
        statusBox.textContent =
            "Restart request sent. Waiting for Doshie...";
    }

    await DoshiePause(1000);
    for (let attempt = 0; attempt < 40; attempt += 1) {
        try {
            const response = await fetch(
                "/live?restart_check=" + Date.now(),
                { cache: "no-store" }
            );
            if (!response.ok) throw new Error("Doshie is restarting.");
            const data = await response.json();
            const newInstance =
                previousInstance && data.instance !== previousInstance;
            if (newInstance || (!previousInstance && sawOffline)) {
                statusBox.textContent = "Doshie is back online.";
                await DoshiePause(400);
                window.location.replace("/");
                return;
            }
        } catch (error) {
            sawOffline = true;
        }
        await DoshiePause(750);
    }

    statusBox.textContent =
        "Doshie is taking longer to restart. Try Refresh app in a moment.";
    DoshieRestarting = false;
}


async function saveSettings() {
    const payload = {
        auto_memory:
            document.getElementById("autoMemory").checked,

        speak_replies:
            document.getElementById("speakReplies").checked,

        voice_identity:
            document.getElementById("voiceIdentity").value,

        voice_engine:
            document.getElementById("voiceEngine").value,

        voice_rate:
            parseFloat(document.getElementById("voiceRate").value),

        voice_pitch:
            parseFloat(document.getElementById("voicePitch").value),

        voice_preset:
            document.getElementById("voicePreset").value,

        mode:
            document.getElementById("DoshieMode").value,

        default_weather_location:
            document.getElementById("weatherLocation").value.trim()
    };

    try {
        const response = await fetch("/settings", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        DoshieSettings = await response.json();

        closeSettings();
        statusBox.textContent = "Settings saved.";

        setTimeout(() => {
            statusBox.textContent = "";
        }, 1500);

    } catch (error) {
        statusBox.textContent = "Could not save settings.";
    }
}


function extractSharedWebUrl(explicitUrl, sharedText) {
    const candidates = [];
    const direct = String(explicitUrl || "").trim();
    if (direct) candidates.push(direct);

    const text = String(sharedText || "");
    ["https://", "http://"].forEach(prefix => {
        const start = text.indexOf(prefix);
        if (start < 0) return;

        let end = text.length;
        [" ", "\\n", "\\t"].forEach(separator => {
            const found = text.indexOf(separator, start);
            if (found >= 0 && found < end) end = found;
        });
        candidates.push(text.slice(start, end));
    });

    for (let candidate of candidates) {
        while (
            candidate &&
            ".,!?;:)>]}".includes(candidate.slice(-1))
        ) {
            candidate = candidate.slice(0, -1);
        }

        try {
            const parsed = new URL(candidate);
            if (parsed.protocol === "https:" || parsed.protocol === "http:") {
                return parsed.href;
            }
        } catch (error) {
            // Keep checking the remaining shared fields.
        }
    }
    return "";
}


function setSearchMode(mode) {
    searchMode = mode === "device" ? "device" : "web";
    document.getElementById("webSearchTab").classList.toggle(
        "active", searchMode === "web"
    );
    document.getElementById("deviceSearchTab").classList.toggle(
        "active", searchMode === "device"
    );
    const field = document.getElementById("searchHubInput");
    const providers = document.getElementById("searchProviderLinks");
    const note = document.getElementById("searchPrivacyNote");
    field.placeholder = searchMode === "web"
        ? "Search the web…"
        : "Find a file or folder by name…";
    field.maxLength = searchMode === "web" ? 180 : 100;
    providers.hidden = searchMode !== "web";
    note.textContent = searchMode === "web"
        ? "Results appear inside Doshie through Bing. Provider buttons open a new tab."
        : "Owner-only filename search. Hidden, credential, certificate, and database files are excluded.";
    document.getElementById("searchHubStatus").textContent =
        searchMode === "web"
            ? "Enter a web search above."
            : "Explorer checks approved TECRA folders only.";
    document.getElementById("searchHubResults").innerHTML = "";
    field.focus({preventScroll: true});
}


function updateSearchProviderLinks(query) {
    const encoded = encodeURIComponent(query);
    document.getElementById("searchGoogleLink").href =
        "https://www.google.com/search?q=" + encoded;
    document.getElementById("searchDuckLink").href =
        "https://duckduckgo.com/?q=" + encoded;
    document.getElementById("searchBingLink").href =
        "https://www.bing.com/search?q=" + encoded;
}


function openSearchHub() {
    if (window.showChatHome) window.showChatHome();
    document.getElementById("searchPanel").style.display = "block";
    document.body.classList.add("app-panel-open");
    setSideView("search");
    setSearchMode(searchMode);
}


function formatSearchFileSize(bytes) {
    const value = Number(bytes || 0);
    if (value < 1024) return value + " B";
    if (value < 1024 * 1024) return Math.round(value / 1024) + " KB";
    if (value < 1024 * 1024 * 1024) {
        return (value / (1024 * 1024)).toFixed(1) + " MB";
    }
    return (value / (1024 * 1024 * 1024)).toFixed(1) + " GB";
}


function renderWebSearchResults(data) {
    const container = document.getElementById("searchHubResults");
    container.innerHTML = "";
    (data.results || []).forEach((item, index) => {
        const article = document.createElement("article");
        article.className = "web-result-card";
        const count = document.createElement("span");
        count.className = "search-result-number";
        count.textContent = String(index + 1).padStart(2, "0");
        const body = document.createElement("div");
        const domain = document.createElement("small");
        domain.textContent = item.domain || "Web result";
        const link = document.createElement("a");
        link.href = item.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = item.title || item.url;
        body.append(domain, link);
        if (item.snippet) {
            const snippet = document.createElement("p");
            snippet.textContent = item.snippet;
            body.appendChild(snippet);
        }
        article.append(count, body);
        container.appendChild(article);
    });
}


function renderDeviceSearchResults(data) {
    const container = document.getElementById("searchHubResults");
    container.innerHTML = "";
    (data.results || []).forEach(item => {
        const article = document.createElement("article");
        article.className = "device-result-card";
        const icon = document.createElement("span");
        icon.className = "device-result-icon";
        icon.textContent = item.type === "folder" ? "📁" : "📄";
        const body = document.createElement("div");
        const title = document.createElement("strong");
        title.textContent = item.name;
        const location = document.createElement("span");
        location.textContent =
            item.location + " › " + item.relative_path;
        body.append(title, location);
        if (item.type === "file") {
            const size = document.createElement("small");
            size.textContent = formatSearchFileSize(item.size);
            body.appendChild(size);
        }
        article.append(icon, body);
        container.appendChild(article);
    });
}


async function runSearchHub(event) {
    if (event) event.preventDefault();
    const field = document.getElementById("searchHubInput");
    const status = document.getElementById("searchHubStatus");
    const container = document.getElementById("searchHubResults");
    const query = field.value.trim();
    if (query.length < 2) {
        status.textContent = "Enter at least two characters.";
        field.focus();
        return;
    }

    if (searchMode === "device" && activeProfile.toLowerCase() !== "hermes") {
        status.textContent =
            "TECRA Explorer is available only inside Hermes's owner account.";
        container.innerHTML = "";
        return;
    }

    if (searchMode === "web") updateSearchProviderLinks(query);
    status.textContent = searchMode === "web"
        ? "Searching the web…"
        : "Searching approved TECRA folders…";
    container.innerHTML = "";

    const endpoint = searchMode === "web"
        ? "/search/web"
        : "/search/device";
    const params = new URLSearchParams({
        q: query,
        profile: activeProfile
    });

    try {
        const response = await fetch(endpoint + "?" + params.toString());
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || "Search could not be completed.");
        }
        if (searchMode === "web") {
            renderWebSearchResults(data);
        } else {
            renderDeviceSearchResults(data);
        }
        const count = Array.isArray(data.results) ? data.results.length : 0;
        status.textContent = count
            ? count + (count === 1 ? " result" : " results")
            : "No matching results. Try a different search.";
    } catch (error) {
        status.textContent = error.message;
    }
}


function updateWatchClock() {
    const clock = document.getElementById("watchTime");
    if (!clock) return;
    clock.textContent = new Intl.DateTimeFormat([], {
        hour: "numeric",
        minute: "2-digit"
    }).format(new Date());
}


function openWatchMode() {
    if (window.showChatHome) window.showChatHome();
    document.getElementById("watchPanel").style.display = "block";
    document.body.classList.add("app-panel-open");
    document.getElementById("watchProfileName").textContent = activeProfile;
    setSideView("watch");
    updateWatchClock();
    if (!window.DoshieWatchClock) {
        window.DoshieWatchClock = window.setInterval(updateWatchClock, 30000);
    }
}


async function watchAsk(value) {
    const text = String(value || "").trim();
    const replyBox = document.getElementById("watchReply");
    if (!text) return;
    replyBox.textContent = "Doshie is thinking…";
    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                message: text,
                profile: activeProfile,
                space: "watch"
            })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || "Doshie could not answer.");
        }
        const reply = data.reply || "No response.";
        replyBox.textContent = reply;
        if (DoshieSettings.speak_replies) {
            const spoken = speakableReply(reply);
            if (spoken) speakDoshieReply(spoken);
        }
    } catch (error) {
        replyBox.textContent = error.message;
    }
}


function submitWatchText(event) {
    event.preventDefault();
    const field = document.getElementById("watchInput");
    const text = field.value.trim();
    if (!text) return;
    field.value = "";
    watchAsk(text);
}


function prepareSharedItem() {
    if (window.location.pathname !== "/share-target") return;

    const params = new URLSearchParams(window.location.search);
    const title = String(params.get("title") || "").trim().slice(0, 240);
    const sharedText = String(params.get("text") || "").trim().slice(0, 5000);
    const sharedUrl = extractSharedWebUrl(
        params.get("url"),
        sharedText
    );
    const context = sharedUrl
        ? sharedText.replace(sharedUrl, "").trim()
        : sharedText;

    const lines = [
        sharedUrl
            ? "Help me with this shared link."
            : "Help me with this shared item."
    ];
    if (title && title !== context) lines.push("Title: " + title);
    if (context) lines.push(context);
    if (sharedUrl) lines.push(sharedUrl);

    input.value = lines.join(" — ").slice(0, 7800);
    statusBox.textContent =
        "Shared with Doshie. Review it, then tap Send.";
    input.focus({ preventScroll: true });
    input.setSelectionRange(input.value.length, input.value.length);
    window.history.replaceState({}, "", "/");
}


async function openRequestedStartView() {
    const chooser = document.getElementById("accountChooser");
    if (!chooser.hidden) return;
    if (window.location.pathname === "/control") {
        openAdminControl();
    } else if (window.location.pathname === "/watch") {
        openWatchMode();
    } else if (window.location.pathname === "/search") {
        openSearchHub();
    } else if (window.location.pathname === "/mansion") {
        await openChatSpace("mansion");
    }
}


loadSettings();
let loadedAppVersion = "";
async function checkForAppUpdate() {
    try {
        const response = await fetch("/app-version?now=" + Date.now(), {
            cache: "no-store"
        });
        if (!response.ok) return;
        const data = await response.json();
        const next = String(data.version || "");
        if (!loadedAppVersion) loadedAppVersion = next;
        else if (next && next !== loadedAppVersion) {
            window.location.reload();
        }
    } catch (error) {
        // Stay usable offline and retry on the next interval.
    }
}
checkForAppUpdate();
window.setInterval(checkForAppUpdate, 30000);
document.addEventListener("visibilitychange", () => {
    if (!document.hidden) checkForAppUpdate();
});

loadProfiles().then(openRequestedStartView);
prepareSharedItem();

const spotifyReturnStatus =
    new URLSearchParams(window.location.search).get("spotify");
if (spotifyReturnStatus) {
    window.setTimeout(async () => {
        await openSpotify();
        if (spotifyReturnStatus === "connected") {
            setSpotifyStatus("Spotify connected successfully.");
            await loadSpotifyStatus();
        } else if (spotifyReturnStatus === "denied") {
            setSpotifyStatus("Spotify connection was canceled.");
        } else {
            setSpotifyStatus("Spotify could not be connected. Please try again.");
        }
    }, 600);
    window.history.replaceState({}, "", window.location.pathname);
}


async function newChat() {
    conversationEpoch += 1;
    activeChatRequests.forEach(controller => controller.abort());

    try {
        const response = await fetch("/new-chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                profile: activeProfile,
                space: activeChatSpace
            })
        });
        if (!response.ok) {
            throw new Error("Could not start a new chat.");
        }

        localStorage.removeItem("Doshie_chat_history");
        messages.innerHTML = "";
        if (activeChatSpace === "mansion") renderMansionRoomBanner();

        addMessage(
            activeChatSpace === "mansion"
                ? "A fresh Mansion Doshie build conversation is ready. " +
                  "The project room stays separate and long-term memories remain available."
                : "New conversation for " + activeProfileFirstName() +
                  ". Long-term memories are still available.",
            "Doshie"
        );

        statusBox.textContent = "New chat started.";

        setTimeout(() => {
            statusBox.textContent = "";
        }, 1500);

    } catch (error) {
        statusBox.textContent = "Could not start a new chat.";
    }
}


function clearChat() {
    localStorage.removeItem("Doshie_chat_history");

    messages.innerHTML = "";

    addMessage(
        "Chat cleared. Long-term memories are still safe.",
        "Doshie"
    );
}


let activeRecognition = null;


function setVoiceListening(active) {
    document.body.classList.toggle("voice-listening", active);
    ["voiceButton", "voiceDockButton", "watchTalkButton"].forEach(id => {
        const button = document.getElementById(id);
        if (!button) return;
        button.setAttribute("aria-pressed", String(active));
        button.setAttribute(
            "aria-label",
            active ? "Stop listening" : "Talk to Doshie"
        );
    });
    const label = document.querySelector("#voiceButton .mic-label");
    const watchLabel = document.querySelector("#watchTalkButton span");
    if (label) label.textContent = active ? "Stop" : "Talk";
    if (watchLabel) watchLabel.textContent = active ? "Stop" : "Talk";
    if (voiceDestination === "watch") {
        if (active) {
            document.getElementById("watchReply").textContent =
                "Listening… Speak now.";
        }
    } else {
        statusBox.textContent = active
            ? "Listening… Speak now. Tap Stop when finished."
            : "";
    }
}


function enableMicrophone() {
    return enableMicrophoneFor("chat");
}


function enableWatchMicrophone() {
    return enableMicrophoneFor("watch");
}


async function enableMicrophoneFor(destination = "chat") {
    voiceDestination = destination === "watch" ? "watch" : "chat";
    const microphoneStatus = document.getElementById("microphoneStatus");
    if (!window.isSecureContext) {
        const message = "Open Doshie with the secure shared link to use the microphone.";
        if (microphoneStatus) microphoneStatus.textContent = message;
        addMessage(message, "Doshie");
        return;
    }

    if (sessionStorage.getItem("Doshie_microphone_consent") !== "yes") {
        const approved = window.confirm(
            "Doshie will listen only after you tap Allow in the browser. " +
            "Audio is used to turn this spoken message into text. Continue?"
        );
        if (!approved) {
            if (microphoneStatus) microphoneStatus.textContent =
                "Microphone stays off until you choose Enable microphone.";
            return;
        }
        sessionStorage.setItem("Doshie_microphone_consent", "yes");
    }

    if (microphoneStatus) microphoneStatus.textContent =
        DoshieNativeSpeechPlugin()
            ? "Waiting for Android's microphone permission…"
            : "Waiting for the browser's microphone prompt…";
    try {
        if (DoshieNativeSpeechPlugin()) {
            if (microphoneStatus) microphoneStatus.textContent =
                "Android microphone ready. Doshie is listening.";
            return voice();
        }
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            const stream = await navigator.mediaDevices.getUserMedia({audio: true});
            stream.getTracks().forEach(track => track.stop());
        }
        if (microphoneStatus) microphoneStatus.textContent =
            "Microphone ready. Doshie is listening.";
        voice();
    } catch (error) {
        sessionStorage.removeItem("Doshie_microphone_consent");
        const message =
            "Microphone access is blocked. Allow it in this site's browser permissions.";
        if (microphoneStatus) microphoneStatus.textContent = message;
        addMessage(message, "Doshie");
    }
}


async function voice() {
    const nativeSpeech = DoshieNativeSpeechPlugin();
    if (nativeSpeech) {
        if (activeRecognition) {
            activeRecognition.cancelled = true;
            await nativeSpeech.stopListening().catch(() => {});
            return;
        }

        const session = {native: true, cancelled: false};
        activeRecognition = session;
        setVoiceListening(true);
        try {
            const result = await nativeSpeech.startListening({
                language:
                    (DoshieSettings.voice_language || "en") + "-" +
                    (DoshieSettings.voice_region || "US")
            });
            const transcript = String(result?.text || "").trim();
            if (transcript) {
                if (voiceDestination === "watch") {
                    document.getElementById("watchInput").value = "";
                    watchAsk(transcript);
                } else {
                    input.value = "";
                    sendText(transcript);
                }
            }
        } catch (error) {
            if (!session.cancelled) {
                addMessage(
                    String(error?.message || error || "The microphone stopped."),
                    "Doshie"
                );
            }
        } finally {
            if (activeRecognition === session) activeRecognition = null;
            setVoiceListening(false);
        }
        return;
    }

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        addMessage(
            "Voice input is not supported by this browser. Try Chrome or Samsung Internet.",
            "Doshie"
        );
        return;
    }

    if (activeRecognition) {
        activeRecognition.stop();
        return;
    }

    const recognition = new SpeechRecognition();
    activeRecognition = recognition;
    recognition.lang =
        (DoshieSettings.voice_language || "en") + "-" +
        (DoshieSettings.voice_region || "US");
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    let finalText = "";
    setVoiceListening(true);

    recognition.onresult = function(event) {
        let preview = "";

        for (let index = event.resultIndex; index < event.results.length; index++) {
            const transcript = event.results[index][0].transcript;
            preview += transcript;

            if (event.results[index].isFinal) {
                finalText += transcript;
            }
        }

        const heard = (finalText + " " + preview).trim();
        const destinationField = voiceDestination === "watch"
            ? document.getElementById("watchInput")
            : input;
        if (heard) destinationField.value = heard;
        if (voiceDestination === "watch") {
            document.getElementById("watchReply").textContent = heard
                ? "Listening: " + heard
                : "Listening…";
        } else {
            statusBox.textContent = heard
                ? "Listening: " + heard
                : "Listening…";
        }
    };

    recognition.onerror = function(event) {
        if (event.error === "not-allowed") {
            addMessage(
                "Please allow microphone access, then tap the mic again.",
                "Doshie"
            );
        } else if (event.error === "no-speech") {
            addMessage(
                "I didn't hear anything. Tap Talk and try again.",
                "Doshie"
            );
        } else if (event.error !== "aborted") {
            addMessage(
                "The microphone stopped. Check the browser permission and try again.",
                "Doshie"
            );
        }
    };

    recognition.onend = function() {
        activeRecognition = null;
        setVoiceListening(false);

        if (finalText.trim()) {
            const transcript = finalText.trim();
            if (voiceDestination === "watch") {
                document.getElementById("watchInput").value = "";
                watchAsk(transcript);
            } else {
                input.value = "";
                sendText(transcript);
            }
        } else if (voiceDestination === "watch") {
            document.getElementById("watchInput").focus({preventScroll: true});
        } else {
            input.focus({preventScroll: true});
        }
    };

    try {
        recognition.start();
    } catch (error) {
        activeRecognition = null;
        setVoiceListening(false);
    }
}


["pointerdown", "keydown", "touchstart"].forEach(eventName => {
    window.addEventListener(eventName, armProfileAutoLock, {passive: true});
});

window.addEventListener("keydown", event => {
    if (event.ctrlKey && event.code === "Space") {
        event.preventDefault();
        enableMicrophone();
    }
});

window.addEventListener("pagehide", () => {
    const record = profileRecord(activeProfile);
    if (
        !record || !record.locked || !record.unlocked ||
        !profilePreferences(record).lock_on_close
    ) return;
    fetch("/profile-lock/lock", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({profile: record.name}),
        keepalive: true
    });
});

["profileStatus", "profileAbout", "profileInterests", "profileMusicUrl"].forEach(id => {
    const field = document.getElementById(id);
    if (field) field.addEventListener("input", renderProfilePreview);
});
installSettingsAccordion();

</script>
<script src="/static/Doshie-app.js?v=21"></script>

</body>
</html>
"""

history = Doshie_history.load_history("Hermes")
Doshie_settings.load_settings()
history_lock = threading.RLock()
history_generation = 0
profile_histories = {}
profile_generations = {}

terminal_sessions = {}
terminal_sessions_lock = threading.RLock()
TERMINAL_IDLE_SECONDS = 30 * 60
TERMINAL_MAX_SESSIONS = 2


def _terminal_stop_locked(session_id):
    item = terminal_sessions.pop(session_id, None)
    if not item:
        return
    try:
        os.killpg(os.getpgid(item["pid"]), signal.SIGTERM)
    except (OSError, ProcessLookupError):
        pass
    try:
        os.close(item["fd"])
    except OSError:
        pass


def _terminal_cleanup_locked():
    cutoff = time.time() - TERMINAL_IDLE_SECONDS
    for session_id, item in list(terminal_sessions.items()):
        if item.get("last_activity", 0) < cutoff:
            _terminal_stop_locked(session_id)


def _terminal_read_locked(item, max_bytes=16000):
    chunks = []
    total = 0
    while total < max_bytes:
        try:
            readable, _, _ = select.select([item["fd"]], [], [], 0)
        except (OSError, ValueError):
            break
        if not readable:
            break
        try:
            data = os.read(item["fd"], min(65536, max_bytes - total))
        except OSError as error:
            if error.errno == errno.EIO:
                item["closed"] = True
            break
        if not data:
            item["closed"] = True
            break
        chunks.append(data)
        total += len(data)
    return b"".join(chunks).decode("utf-8", "replace")


def _terminal_get_locked(session_id, profile):
    item = terminal_sessions.get(str(session_id or ""))
    if not item or item.get("profile", "").casefold() != profile.casefold():
        return None
    return item


TERMINAL_MUTATION_PATTERN = re.compile(
    r"(^|[\\s;&|])(sudo|rm|mv|cp|touch|mkdir|rmdir|chmod|chown|tee|truncate|dd|npm\\s+(install|i)|pip(?:3)?\\s+install|systemctl|service|git\\s+(commit|reset|checkout|clean|restore|rebase|merge|cherry-pick)|sed\\s+-i|perl\\s+-i|python(?:3)?\\s+-c|node\\s+-e)\\b",
    re.IGNORECASE,
)


def _terminal_command_requires_approval(command):
    return bool(
        TERMINAL_MUTATION_PATTERN.search(command)
        or re.search(r">>|(^|[^>])>(?!>)", command)
    )


def _terminal_start(profile, cwd=None, mode="direct"):
    with terminal_sessions_lock:
        _terminal_cleanup_locked()
        if len(terminal_sessions) >= TERMINAL_MAX_SESSIONS:
            raise ValueError("The user-level terminal is busy. Close an existing session first.")
        clean_cwd = os.path.realpath(os.path.expanduser(str(cwd or app.root_path)))
        if not os.path.isdir(clean_cwd):
            raise ValueError("That working directory does not exist.")
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(clean_cwd)
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env["PYTHONUNBUFFERED"] = "1"
            os.execvpe("/bin/bash", ["bash", "-l"], env)
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        session_id = secrets.token_urlsafe(24)
        terminal_sessions[session_id] = {
            "id": session_id,
            "profile": profile,
            "mode": mode if mode in {"direct", "maintenance"} else "direct",
            "pid": pid,
            "fd": fd,
            "cwd": clean_cwd,
            "created": time.time(),
            "last_activity": time.time(),
            "closed": False,
        }
        return session_id, clean_cwd


def profile_catalog():
    profiles = [{
        "id": "owner",
        "name": "Hermes",
        "role": "Owner Administrator",
        "access_role": "owner",
        "is_admin": True,
        "is_child": False,
    }]
    seen = {"hermes"}

    for member_id, name, role, _notes in Doshie_memory.get_family_members():
        clean = " ".join((name or "").split()).strip()
        if not clean or clean.casefold() in seen:
            continue
        seen.add(clean.casefold())
        flags = Doshie_roles.role_flags(clean, role)
        display_role = {
            "admin": "Administrator",
            "child": "Child / Kids mode",
            "family": role or "Family",
        }.get(flags["access_role"], role or "Family")
        profiles.append({
            "id": f"family-{member_id}",
            "name": clean,
            "role": display_role,
            **flags,
        })

    for profile in profiles:
        parts = profile["name"].split()
        profile["initials"] = "".join(
            part[0].upper() for part in parts[:2] if part
        ) or "Y"
        version = Doshie_profile_avatar.avatar_version(profile["name"])
        profile["avatar_url"] = (
            f"/profile-avatar/{profile['id']}?v={version}"
            if version else None
        )
        profile["preferences"] = (
            Doshie_profile_preferences.get_preferences(profile["name"])
        )
    return profiles


def resolve_profile(value):
    requested = " ".join(str(value or "Hermes").split()).strip()
    for item in profile_catalog():
        if item["name"].casefold() == requested.casefold():
            return item["name"]
    # Some installed clients display the owner as "Hermes Duran" while
    # the local owner profile key is "Hermes". This exact alias keeps the
    # terminal and chat compatible without affecting family profiles.
    if requested.casefold() == "hermes duran":
        owner = next(
            (item for item in profile_catalog()
             if item["name"].casefold() == "hermes"),
            None,
        )
        return owner["name"] if owner else None
    return None


def resolve_profile_id(value):
    requested = str(value or "").strip().casefold()
    for item in profile_catalog():
        if item["id"].casefold() == requested:
            return item
    return None


PROFILE_UNLOCK_SECONDS = 8 * 60 * 60
PROFILE_ATTEMPT_WINDOW = 5 * 60
PROFILE_ATTEMPT_LIMIT = 5
PROFILE_BLOCK_SECONDS = 5 * 60
profile_unlock_attempts = {}
profile_unlock_attempts_lock = threading.RLock()


def _profile_session_key(profile):
    return Doshie_profile_lock.profile_key(profile)


def _profile_session_unlocked(profile):
    if not Doshie_profile_lock.is_locked(profile):
        return True

    unlocks = session.get("profile_unlocks", {})
    expires_at = unlocks.get(_profile_session_key(profile), 0)
    try:
        valid = float(expires_at) > time.time()
    except (TypeError, ValueError):
        valid = False

    if not valid and _profile_session_key(profile) in unlocks:
        updated = dict(unlocks)
        updated.pop(_profile_session_key(profile), None)
        session["profile_unlocks"] = updated
        session.modified = True
    return valid


def _remember_profile_unlock(profile):
    unlocks = dict(session.get("profile_unlocks", {}))
    preferences = Doshie_profile_preferences.get_preferences(profile)
    minutes = preferences.get("auto_lock_minutes", 5)
    unlock_seconds = (
        PROFILE_UNLOCK_SECONDS if minutes == 0 else minutes * 60
    )
    unlocks[_profile_session_key(profile)] = time.time() + unlock_seconds
    session["profile_unlocks"] = unlocks
    session.permanent = True
    session.modified = True


def _forget_profile_unlock(profile):
    unlocks = dict(session.get("profile_unlocks", {}))
    unlocks.pop(_profile_session_key(profile), None)
    session["profile_unlocks"] = unlocks
    session.modified = True


def _profile_attempt_key(profile):
    forwarded = request.headers.get("X-Forwarded-For", "")
    client = forwarded.split(",", 1)[0].strip() or request.remote_addr or "local"
    return client, _profile_session_key(profile)


def _profile_retry_after(profile):
    now = time.time()
    key = _profile_attempt_key(profile)
    with profile_unlock_attempts_lock:
        record = profile_unlock_attempts.get(key)
        if not record:
            return 0
        blocked_until = float(record.get("blocked_until") or 0)
        if blocked_until > now:
            return max(1, int(blocked_until - now) + 1)
        if now - float(record.get("started_at") or now) > PROFILE_ATTEMPT_WINDOW:
            profile_unlock_attempts.pop(key, None)
    return 0


def _record_profile_failure(profile):
    now = time.time()
    key = _profile_attempt_key(profile)
    with profile_unlock_attempts_lock:
        record = profile_unlock_attempts.get(key)
        if (
            not record
            or now - float(record.get("started_at") or now)
            > PROFILE_ATTEMPT_WINDOW
        ):
            record = {"count": 0, "started_at": now, "blocked_until": 0}
        record["count"] += 1
        if record["count"] >= PROFILE_ATTEMPT_LIMIT:
            record["blocked_until"] = now + PROFILE_BLOCK_SECONDS
        profile_unlock_attempts[key] = record
    return _profile_retry_after(profile)


def _clear_profile_failures(profile):
    with profile_unlock_attempts_lock:
        profile_unlock_attempts.pop(_profile_attempt_key(profile), None)


PROFILE_PROTECTED_ENDPOINTS = {
    "chat_history_get",
    "profile_preferences_get",
    "profile_preferences_save",
    "spotify_status",
    "spotify_config",
    "spotify_connect",
    "spotify_disconnect",
    "spotify_search",
    "spotify_playlists",
    "spotify_now_playing",
    "spotify_control",
    "web_search_get",
    "device_search_get",
    "health_sync_status",
    "health_sync_configure",
    "health_sync_authorize",
    "new_chat",
    "chat_attachment_upload",
    "chat_attachment_get",
    "chat",
}


def _request_profile_from_request():
    data = request.get_json(silent=True)
    values = data if isinstance(data, dict) else {}
    requested = values.get("profile") or request.args.get("profile", "Hermes")
    return resolve_profile(requested)


def _profile_locked_response(profile):
    auth_type = Doshie_profile_lock.status(profile)["auth_type"]
    return jsonify({
        "error": "This account is locked.",
        "code": "profile_locked",
        "profile": profile,
        "locked": True,
        "auth_type": auth_type,
        "needs_credential": True,
        "needs_pin": auth_type == "pin",
    }), 423


PUBLIC_FUNNEL_PORT = 8443
WEBSITE_HOSTS = {
    "Doshie-home.duckdns.org",
    "hermes-duran-tecra-a60-m.tail50b4c5.ts.net",
}
PUBLIC_OPEN_ENDPOINTS = {
    "home", "static", "service_worker", "login_page",
    "profiles_get", "family_invite_claim", "family_login", "app_version", "android_asset_links",
    "recovery_request", "recovery_verify", "recovery_reset",
}
WEBSITE_LOGIN_OPEN_ENDPOINTS = {
    "static", "service_worker", "login_page", "app_version", "android_asset_links",
    "family_invite_claim", "family_login",
    "recovery_request", "recovery_verify", "recovery_reset",
}
WEBSITE_PAGE_ENDPOINTS = {
    "canonical_home", "tech_preview", "home", "share_target",
}


def _website_request_host():
    forwarded = request.headers.get("X-Forwarded-Host", "")
    host = (forwarded or request.host or "").split(",", 1)[0].strip().lower()
    return host.split(":", 1)[0], host


def _is_public_funnel_request():
    hostname, host = _website_request_host()
    return (
        hostname in WEBSITE_HOSTS
        or host.endswith(f":{PUBLIC_FUNNEL_PORT}")
    )


def _public_authorized_profile():
    value = str(session.get("public_profile") or "").strip()
    expires = float(session.get("public_profile_expires") or 0)
    if not value or expires <= time.time():
        session.pop("public_profile", None)
        session.pop("public_profile_expires", None)
        return None
    return resolve_profile(value)


@app.before_request
def enforce_website_login():
    if not _is_public_funnel_request():
        return None
    if request.method == "OPTIONS":
        return None

    endpoint = request.endpoint or ""
    if endpoint in WEBSITE_LOGIN_OPEN_ENDPOINTS:
        public_download_page = (
            endpoint == "static"
            and request.path == "/static/downloads/index.html"
        )
        if (
            endpoint != "static"
            or not request.path.lower().endswith(".html")
            or public_download_page
        ):
            return None

    if _public_authorized_profile() is not None:
        return None

    if endpoint in WEBSITE_PAGE_ENDPOINTS:
        return redirect("/login", code=302)

    return jsonify({
        "error": "Sign in is required.",
        "code": "login_required",
    }), 401


@app.before_request
def enforce_website_origin():
    if not _is_public_funnel_request():
        return None
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None

    origin = str(request.headers.get("Origin") or "").strip()
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or parsed.hostname not in WEBSITE_HOSTS:
        return jsonify({
            "error": "The request origin is not allowed.",
            "code": "origin_forbidden",
        }), 403
    return None


@app.before_request
def enforce_public_invitation():
    if not _is_public_funnel_request():
        return None
    if request.endpoint in PUBLIC_OPEN_ENDPOINTS:
        return None
    authorized = _public_authorized_profile()
    if authorized is None:
        return jsonify({
            "error": "A family invitation is required.",
            "code": "invite_required",
        }), 401
    data = request.get_json(silent=True)
    values = data if isinstance(data, dict) else {}
    requested_value = values.get("profile") or request.args.get("profile")
    requested = resolve_profile(requested_value) if requested_value else None
    if requested_value and requested is None:
        return jsonify({
            "error": "Choose a valid account.",
            "code": "profile_forbidden",
        }), 403
    if requested is not None and requested.casefold() != authorized.casefold():
        return jsonify({
            "error": "This invitation belongs to a different account.",
            "code": "profile_forbidden",
        }), 403
    return None


@app.after_request
def add_website_security_headers(response):
    if not _is_public_funnel_request():
        return response

    response.headers.setdefault(
        "Strict-Transport-Security",
        "max-age=31536000",
    )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault(
        "Referrer-Policy",
        "strict-origin-when-cross-origin",
    )
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(self), microphone=(self), "
        "geolocation=(), payment=(), usb=()",
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "base-uri 'self'; object-src 'none'; "
        "frame-ancestors 'self'; form-action 'self'; "
        "img-src 'self' data: blob:; "
        "media-src 'self' blob:; "
        "connect-src 'self'; frame-src 'self'; "
        "worker-src 'self' blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'",
    )
    if response.mimetype == "text/html":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.before_request
def enforce_profile_lock():
    if request.endpoint not in PROFILE_PROTECTED_ENDPOINTS:
        return None

    profile = _request_profile_from_request()
    if profile is None:
        return None

    try:
        if not _profile_session_unlocked(profile):
            return _profile_locked_response(profile)
    except Doshie_profile_lock.ProfileLockError:
        return jsonify({
            "error": "Doshie's profile security needs repair.",
            "code": "profile_lock_unavailable",
        }), 503
    return None


CHAT_SPACES = {"main", "mansion", "watch"}
CHAT_MODE_CONTEXTS = {
    "general": "",
    "tech": (
        "TECH MODE: Act as a dependable technology specialist. Diagnose from "
        "evidence, explain commands plainly, protect existing data, and verify fixes."
    ),
    "ai_tutor": (
        "AI TUTOR MODE: Teach artificial intelligence step by step with accurate "
        "definitions, practical examples, short exercises, and no invented claims."
    ),
    "coding": (
        "CODING MODE: Act as a patient senior programming teacher. Prefer secure, "
        "small, testable code; explain the plan; check syntax and edge cases. "
        "Write polished American English with complete sentences, correct grammar, "
        "clear headings, and concise step-by-step explanations. Never output broken "
        "fragments, filler, or rushed shorthand. Before sending, silently proofread "
        "the entire response."
    ),
    "gaming": (
        "GAMING MODE: Help with game design, gameplay systems, performance, engines, "
        "and code. Explain game loops, components, testing, and player experience."
    ),
}


def normalize_chat_mode(value):
    mode = str(value or "general").strip().casefold()
    return mode if mode in CHAT_MODE_CONTEXTS else "general"


ADMIN_BRAIN_MODES = {"auto", "fast", "balanced", "coding", "advanced", "vision"}
MEMBER_BRAIN_MODES = {"auto", "balanced"}


def normalize_brain_mode(value, profile):
    requested = str(value or "auto").strip().casefold()
    record = next(
        (
            item for item in profile_catalog()
            if item["name"].casefold() == str(profile).casefold()
        ),
        None,
    )
    allowed = ADMIN_BRAIN_MODES if record and record.get("is_admin") else MEMBER_BRAIN_MODES
    return requested if requested in allowed else "auto"


def combined_chat_context(space, mode):
    return "\n\n".join(
        item for item in (
            chat_space_context(space),
            CHAT_MODE_CONTEXTS[normalize_chat_mode(mode)],
        ) if item
    )


def normalize_chat_space(value):
    space = str(value or "main").strip().casefold()
    return space if space in CHAT_SPACES else None


def conversation_storage_profile(profile, space="main"):
    if space == "mansion":
        return f"{profile} Mansion Doshie"
    if space == "watch":
        return f"{profile} Watch Doshie"
    return profile


def chat_space_context(space):
    if space == "mansion":
        return (
            "You are in Mansion Doshie, a dedicated engineering room for "
            "building Doshie's dependable final home. Keep plans practical, "
            "family-first, private, testable, reversible, and organized."
        )
    if space == "watch":
        return (
            "You are answering from Doshie Watch mode. Be concise, useful, "
            "and easy to read aloud or scan on a tiny screen."
        )
    return ""


def conversation_snapshot(profile, space="main"):
    global history, history_generation
    storage_profile = conversation_storage_profile(profile, space)
    with history_lock:
        if storage_profile.casefold() == "hermes":
            return list(history), history_generation

        if storage_profile not in profile_histories:
            profile_histories[storage_profile] = (
                Doshie_history.load_history(storage_profile)
            )
            profile_generations[storage_profile] = 0

        return (
            list(profile_histories[storage_profile]),
            profile_generations.get(storage_profile, 0)
        )


def append_conversation(
    profile, user_text, reply, request_generation, space="main"
):
    global history, history_generation
    storage_profile = conversation_storage_profile(profile, space)

    with history_lock:
        if storage_profile.casefold() == "hermes":
            if request_generation != history_generation:
                return False
            current = list(history)
        else:
            if request_generation != profile_generations.get(storage_profile, 0):
                return False
            current = list(profile_histories.get(storage_profile, []))

        current.extend([
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": reply},
        ])

        if len(current) > 4:
            older_messages = current[:-4]
            Doshie_summary.append_entries(older_messages, storage_profile)
            current = current[-4:]

        Doshie_history.save_history(current, storage_profile)

        if storage_profile.casefold() == "hermes":
            history = current
        else:
            profile_histories[storage_profile] = current
        return True


def reset_chat_history(profile="Hermes", space="main"):
    global history, history_generation
    profile = profile or "Hermes"
    storage_profile = conversation_storage_profile(profile, space)

    with history_lock:
        if storage_profile.casefold() == "hermes":
            history = []
            history_generation += 1
        else:
            profile_histories[storage_profile] = []
            profile_generations[storage_profile] = (
                profile_generations.get(storage_profile, 0) + 1
            )

        Doshie_history.clear_history(storage_profile)
        Doshie_summary.clear_summary(storage_profile)


@app.route("/login", methods=["GET"])
def login_page():
    authorized = _public_authorized_profile()
    if authorized is not None:
        record = next(
            item for item in profile_catalog() if item["name"] == authorized
        )
        return redirect("/tech" if record["is_admin"] else "/control", code=302)
    response = send_from_directory(
        "/home/hermes-duran/Doshie/static", "login.html"
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/logout", methods=["POST"])
def website_logout():
    session.clear()
    response = jsonify({"ok": True})
    response.headers["Clear-Site-Data"] = '"cache"'
    return response


@app.route("/tech")
def tech_preview():
    authorized = _public_authorized_profile()
    if _is_public_funnel_request() and authorized:
        record = next(
            item for item in profile_catalog() if item["name"] == authorized
        )
        if not record["is_admin"]:
            return redirect("/control", code=302)
    response = send_from_directory(
        "/home/hermes-duran/Doshie/static", "tech-shell.html"
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    if request.args.get("reset-cache") == "1":
        response.headers["Clear-Site-Data"] = '"cache"'
    return response

@app.route("/")
def canonical_home():
    authorized = _public_authorized_profile()
    if _is_public_funnel_request() and authorized:
        record = next(
            item for item in profile_catalog() if item["name"] == authorized
        )
        if not record["is_admin"]:
            return redirect("/control", code=302)
    return tech_preview()


@app.route("/control")
@app.route("/mansion")
@app.route("/search")
@app.route("/watch")
def home():
    if request.path == "/control":
        return redirect("/tech?panel=control&refresh=" + str(int(time.time())))
    page = HTML
    if request.path == "/control":
        page = page.replace(
            "/static/manifest.webmanifest",
            "/static/tecra-control.webmanifest",
            1,
        ).replace("<title>Doshie</title>", "<title>Doshie Control</title>", 1).replace(
            "<body>", "<body class=\"control-app\">", 1
        )
    return render_template_string(page)


@app.route("/share-target", methods=["GET"])
def share_target():
    return render_template_string(HTML)


@app.route("/.well-known/assetlinks.json", methods=["GET"])
def android_asset_links():
    response = jsonify([{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": "org.Doshie.assistant",
            "sha256_cert_fingerprints": [
                "0F:A0:DB:CA:B8:83:CD:D1:8A:04:87:AB:44:5E:C1:75:4A:09:06:E4:7B:72:D3:CA:F3:C4:26:F4:93:72:BC:77"
            ],
        },
    }])
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


@app.route("/app-version", methods=["GET"])
def app_version():
    watched = [
        __file__,
        os.path.join(app.root_path, "static", "tech-shell.html"),
        os.path.join(app.root_path, "static", "login.html"),
        os.path.join(app.root_path, "static", "Doshie-app.css"),
    ]
    version = max(
        (os.stat(path).st_mtime_ns for path in watched if os.path.exists(path)),
        default=0,
    )
    manifest_path = os.path.join(app.root_path, "static", "downloads", "latest.json")
    releases = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as manifest_file:
                manifest = json.load(manifest_file)
            for platform in ("windows", "linux", "android"):
                release = manifest.get(platform)
                if isinstance(release, dict) and release.get("file"):
                    releases[platform] = {
                        **release,
                        "url": "/static/downloads/" + str(release["file"]),
                        "version": str(manifest.get("version", "")),
                    }
        except (OSError, ValueError, TypeError):
            releases = {}
    response = jsonify({"version": str(version), "releases": releases, "source": "Doshie main home"})
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/service-worker.js", methods=["GET"])
def service_worker():
    response = send_from_directory(
        os.path.join(app.root_path, "static"),
        "service-worker.js"
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.route("/live", methods=["GET"])
def live():
    return jsonify({
        "live": True,
        "status": "running",
        "instance": INSTANCE_ID,
    })


def _terminate_for_restart():
    os.kill(os.getpid(), signal.SIGTERM)


@app.route("/system/restart", methods=["POST"])
def restart_service():
    if request.headers.get("X-Doshie-Action") != "restart":
        return jsonify({"error": "Restart confirmation is required."}), 403

    timer = threading.Timer(0.75, _terminate_for_restart)
    timer.daemon = True
    timer.start()
    return jsonify({
        "restarting": True,
        "instance": INSTANCE_ID,
    }), 202


@app.route("/health", methods=["GET"])
def health():
    model_online = False
    database_ok = False
    recall_ready = callable(getattr(Doshie_memory, "smart_recall", None))
    history_ok = Doshie_history.history_file_valid()
    settings_ok = Doshie_settings.settings_file_valid()
    profile_security_ok = Doshie_profile_lock.data_file_valid()
    profile_photos_ok = Doshie_profile_avatar.data_directory_valid()
    profile_preferences_ok = Doshie_profile_preferences.data_file_valid()
    news_service_ok = Doshie_news.service_ready()
    search_service_ok = Doshie_search.service_ready()
    voice_status = Doshie_voice_proxy.status()
    voice_service_ok = bool(voice_status.get("online"))
    try:
        Doshie_chat_attachments.ROOT.mkdir(parents=True, exist_ok=True)
        attachments_ok = os.access(Doshie_chat_attachments.ROOT, os.W_OK)
    except OSError:
        attachments_ok = False
    permission_queue_ok = callable(getattr(Doshie_permissions, "list_requests", None))

    try:
        model_online = bool(Doshie_memory.server_ready())
    except Exception:
        app.logger.exception("Doshie model health check failed")

    try:
        database_ok = Doshie_memory.database_ready()
    except Exception:
        app.logger.exception("Doshie database health check failed")

    ready = (
        model_online
        and database_ok
        and recall_ready
        and history_ok
        and settings_ok
        and profile_security_ok
        and profile_photos_ok
        and profile_preferences_ok
        and news_service_ok
        and search_service_ok
    )
    response = jsonify({
        "online": ready,
        "status": "online" if ready else "degraded",
        "checks": {
            "model": model_online,
            "database": database_ok,
            "memory_recall": recall_ready,
            "chat_history": history_ok,
            "settings": settings_ok,
            "profile_security": profile_security_ok,
            "profile_photos": profile_photos_ok,
            "profile_preferences": profile_preferences_ok,
            "news_service": news_service_ok,
            "search_service": search_service_ok,
            "voice_service": voice_service_ok,
            "attachments": attachments_ok,
            "approval_queue": permission_queue_ok,
            "web_service": True
        },
        "voice": voice_status,
        "instance": INSTANCE_ID,
        "model": Doshie_memory.MODEL,
        "brain_models": Doshie_memory.BRAIN_MODELS,
        "context_size": Doshie_memory.CONTEXT_SIZE
    })
    return response, 200 if ready else 503


@app.route("/dashboard", methods=["GET"])
def dashboard():
    settings = Doshie_settings.load_settings()

    battery = Doshie_memory.get_battery_status()
    status = Doshie_memory.get_device_status()

    weather_location = settings.get(
        "default_weather_location",
        "El Paso"
    )

    weather = Doshie_memory.get_weather(weather_location)

    task_summary = Doshie_memory.get_task_summary()

    return jsonify({
        "battery": battery,
        "status": status,
        "weather": weather,
        "auto_memory": settings.get("auto_memory", True),
        "speak_replies": settings.get("speak_replies", False),
        "tasks": task_summary
    })


def _require_invite_admin(profile):
    resolved = resolve_profile(profile)
    record = next(
        (
            item for item in profile_catalog()
            if resolved and item["name"].casefold() == resolved.casefold()
        ),
        None,
    )
    if not record or not record.get("is_admin"):
        return None, (jsonify({"error": "Administrator access required."}), 403)
    if not _profile_session_unlocked(resolved):
        return None, _profile_locked_response(resolved)
    return resolved, None


@app.route("/media-studio/status", methods=["GET"])
def media_studio_status():
    _admin, error = _require_invite_admin(request.args.get("profile"))
    if error:
        return error
    return jsonify(Doshie_media.status())


@app.route("/media-studio/generate", methods=["POST"])
def media_studio_generate():
    data = request.get_json(silent=True) or {}
    admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error
    kind = str(data.get("kind") or "image").strip().casefold()
    try:
        if kind == "image":
            media = Doshie_media.generate_image(
                admin,
                data.get("prompt"),
                size=data.get("size") or "512x512",
                quality=data.get("quality") or "medium",
            )
        elif kind == "video":
            media = Doshie_media.start_video(
                data.get("prompt"),
                size=data.get("size") or "1280x720",
                seconds=data.get("seconds") or 8,
            )
        else:
            return jsonify({"error": "Choose image or video generation."}), 400
    except Doshie_media.MediaError as exc:
        return jsonify({"error": str(exc)}), 502
    if media.get("filename"):
        media["url"] = f"/generated-media/{media['filename']}?profile={admin}"
    return jsonify({"media": media})


@app.route("/media-studio/video/<job_id>", methods=["GET"])
def media_studio_video(job_id):
    admin, error = _require_invite_admin(request.args.get("profile"))
    if error:
        return error
    try:
        media = Doshie_media.poll_video(admin, job_id)
    except Doshie_media.MediaError as exc:
        return jsonify({"error": str(exc)}), 502
    if media.get("filename"):
        media["url"] = f"/generated-media/{media['filename']}?profile={admin}"
    return jsonify({"media": media})


@app.route("/generated-media/<filename>", methods=["GET"])
def generated_media(filename):
    admin, error = _require_invite_admin(request.args.get("profile"))
    if error:
        return error
    try:
        target = Doshie_media.media_path(admin, filename)
    except Doshie_media.MediaError as exc:
        return jsonify({"error": str(exc)}), 404
    return send_file(target, conditional=True)


def _builder_project_directory(name):
    clean = str(name or "").strip().casefold()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,59}", clean):
        raise ValueError("Use a short project name with letters, numbers, or hyphens.")
    root = os.path.realpath(os.path.join(os.path.expanduser("~"), "Doshie", "projects"))
    directory = os.path.realpath(os.path.join(root, clean))
    if os.path.commonpath([root, directory]) != root:
        raise ValueError("Project path is invalid.")
    return clean, root, directory


@app.route("/builder-projects", methods=["GET"])
def builder_projects():
    _admin, error = _require_invite_admin(request.args.get("profile"))
    if error:
        return error
    root = os.path.join(os.path.expanduser("~"), "Doshie", "projects")
    os.makedirs(root, exist_ok=True)
    projects = []
    for name in sorted(os.listdir(root)):
        try:
            clean, _root, directory = _builder_project_directory(name)
        except ValueError:
            continue
        if os.path.isdir(directory):
            files = []
            for current, directories, names in os.walk(directory):
                directories[:] = [item for item in directories if not item.startswith(".")]
                for filename in names:
                    relative = os.path.relpath(os.path.join(current, filename), directory)
                    files.append(relative.replace(os.sep, "/"))
            projects.append({
                "name": clean,
                "files": sorted(files)[:200],
                "preview_ready": os.path.isfile(os.path.join(directory, "index.html")),
            })
    return jsonify({"projects": projects})


@app.route("/builder-preview/<project>/", defaults={"asset": "index.html"})
@app.route("/builder-preview/<project>/<path:asset>")
def builder_preview(project, asset):
    _admin, error = _require_invite_admin(request.args.get("profile"))
    if error:
        return error
    try:
        _clean, _root, directory = _builder_project_directory(project)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not os.path.isdir(directory):
        return jsonify({"error": "That Builder project does not exist."}), 404
    return send_from_directory(directory, asset)


@app.route("/memory-center", methods=["GET", "POST"])
def memory_center():
    data = request.get_json(silent=True) if request.method == "POST" else request.args
    data = data if isinstance(data, dict) else request.args
    admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error
    try:
        message = ""
        backup = ""
        if request.method == "POST":
            action = str(data.get("action") or "").strip().casefold()
            if action == "add":
                message = Doshie_memory.add_memory(
                    str(data.get("memory") or "")[:4000],
                    category=data.get("category") or "General",
                    importance=data.get("importance") or "Normal",
                    profile=admin,
                    scope=data.get("scope") or "private",
                )
            elif action == "update":
                message = Doshie_memory.update_memory_record(
                    admin,
                    data.get("id"),
                    data.get("memory"),
                    category=data.get("category") or "General",
                    importance=data.get("importance") or "Normal",
                    scope=data.get("scope") or "private",
                )
            elif action == "set_active":
                message = Doshie_memory.set_memory_active(
                    admin, data.get("id"), bool(data.get("active"))
                )
            elif action == "backup":
                backup = Doshie_memory.create_memory_backup()
                message = "Verified private memory backup created."
            else:
                return jsonify({"error": "Choose a valid memory action."}), 400
        records = Doshie_memory.memory_center_records(
            admin,
            include_inactive=str(data.get("include_inactive", "1")) != "0",
        )
        return jsonify({
            "profile": admin,
            "memories": records,
            "message": message,
            "backup": backup,
        })
    except (ValueError, TypeError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/equipment-health", methods=["GET"])
def equipment_health():
    _admin, error = _require_invite_admin(request.args.get("profile"))
    if error:
        return error
    return jsonify({"equipment": Doshie_equipment_health.snapshot()})


@app.route("/permission-requests", methods=["GET"])
def permission_requests_list():
    admin, error = _require_invite_admin(request.args.get("profile"))
    if error:
        return error
    return jsonify({"requests": Doshie_permissions.list_requests()})


@app.route("/permission-requests/regression", methods=["POST"])
def permission_requests_regression():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error
    try:
        record = Doshie_permissions.create_regression_request(
            admin,
            data.get("summary") or "Run the full Doshie regression suite.",
        )
        return jsonify({"request": record}), 201
    except Doshie_permissions.PermissionRequestError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/permission-requests/<request_id>/review", methods=["POST"])
def permission_request_review(request_id):
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error
    decision = str(data.get("decision") or "").strip().lower()
    try:
        record = Doshie_permissions.review(
            request_id,
            admin,
            decision,
        )
        return jsonify({"request": record})
    except Doshie_permissions.PermissionRequestError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/permission-requests/<request_id>/rollback", methods=["POST"])
def permission_request_rollback(request_id):
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error
    try:
        record = Doshie_permissions.rollback(request_id, admin)
        return jsonify({"request": record})
    except Doshie_permissions.PermissionRequestError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/family-profiles", methods=["POST"])
def family_profile_create():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error

    name = " ".join(str(data.get("name") or "").split()).strip()[:80]
    auth_type = str(data.get("auth_type") or "pin").strip().casefold()
    credential = data.get("credential")
    if not name:
        return jsonify({"error": "Enter the person's name."}), 400
    if resolve_profile(name):
        return jsonify({"error": "That person already has a profile."}), 409

    try:
        Doshie_profile_lock.validate_credential(credential, auth_type)
        Doshie_memory.add_family_member(name, "Family", "Invited by Hermes")
        profile = resolve_profile(name)
        if not profile:
            raise ValueError("The family profile could not be created.")
        Doshie_profile_lock.set_credential(profile, credential, auth_type)
        token, record = Doshie_invites.create(profile, admin)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Doshie_profile_lock.ProfileLockError:
        return jsonify({"error": "Profile security needs repair."}), 503

    public_url = f"{request.host_url.rstrip('/')}/login?invite={token}"
    return jsonify({
        "ok": True,
        "profile": profile,
        "invite": record,
        "token": token,
        "url": public_url,
    }), 201


@app.route("/family-invites", methods=["GET", "POST"])
def family_invites():
    data = request.get_json(silent=True) if request.method == "POST" else request.args
    data = data if isinstance(data, dict) else request.args
    admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error

    if request.method == "GET":
        return jsonify({"invites": Doshie_invites.list_records()})

    target = resolve_profile(data.get("target_profile"))
    if target is None:
        return jsonify({"error": "Choose a valid family account."}), 400
    if not Doshie_profile_lock.is_locked(target):
        return jsonify({
            "error": "Set a PIN or password on this account before inviting it."
        }), 400
    token, record = Doshie_invites.create(target, admin)
    public_url = f"{request.host_url.rstrip('/')}/login?invite={token}"
    return jsonify({"invite": record, "token": token, "url": public_url}), 201


@app.route("/family-invites/<invite_id>", methods=["DELETE"])
def family_invite_revoke(invite_id):
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    _admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error
    return jsonify({"invite": Doshie_invites.revoke(invite_id)})


def _require_owner_session():
    actor = _public_authorized_profile()
    if not actor or actor.casefold() != "hermes":
        return None, (jsonify({"error": "Verified owner sign-in required."}), 403)
    if not _profile_session_unlocked(actor):
        return None, _profile_locked_response(actor)
    return actor, None


@app.route("/admin/profile-roles", methods=["GET", "POST"])
def admin_profile_roles():
    _owner, error = _require_owner_session()
    if error:
        return error
    data = request.get_json(silent=True) if request.method == "POST" else {}
    data = data if isinstance(data, dict) else {}
    if request.method == "POST":
        target = resolve_profile(data.get("target_profile"))
        if not target:
            return jsonify({"error": "Choose a valid family profile."}), 400
        try:
            Doshie_roles.set_role(target, data.get("access_role"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    return jsonify({
        "profiles": [{
            "name": item["name"],
            "role": item["role"],
            "access_role": item["access_role"],
            "is_admin": item["is_admin"],
            "is_child": item["is_child"],
        } for item in profile_catalog()]
    })


@app.route("/family-profiles/<path:profile_name>", methods=["DELETE"])
def family_profile_delete(profile_name):
    _owner, error = _require_owner_session()
    if error:
        return error
    target = resolve_profile(profile_name)
    if not target:
        return jsonify({"error": "That family account was not found."}), 404
    if target.casefold() == "hermes":
        return jsonify({"error": "The owner account cannot be removed."}), 400
    member = next(
        (
            item for item in Doshie_memory.get_family_members()
            if str(item[1] or "").strip().casefold() == target.casefold()
        ),
        None,
    )
    if not member:
        return jsonify({"error": "That family account was not found."}), 404
    Doshie_invites.revoke_profile(target)
    Doshie_profile_lock.remove_pin(target)
    Doshie_profile_preferences.remove_preferences(target)
    Doshie_profile_avatar.remove_avatar(target)
    Doshie_roles.remove_role(target)
    Doshie_memory.remove_family_member(member[0])
    return jsonify({
        "ok": True,
        "removed": target,
        "message": "Account access removed. Existing chat files remain archived.",
    })


RECOVERY_GENERIC_MESSAGE = (
    "If that account and recovery method are configured, "
    "a six-digit code is on the way."
)


@app.route("/recovery/request", methods=["POST"])
def recovery_request():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    profile = resolve_profile(data.get("username"))
    method = str(data.get("method") or "").strip().casefold()
    if profile and method in {"email", "sms"}:
        try:
            Doshie_recovery.request_code(profile, method)
        except Exception:
            app.logger.warning("A recovery message could not be delivered.")
    return jsonify({
        "ok": True,
        "message": RECOVERY_GENERIC_MESSAGE,
    }), 202


@app.route("/recovery/verify", methods=["POST"])
def recovery_verify():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    profile = resolve_profile(data.get("username"))
    token = (
        Doshie_recovery.verify_code(profile, data.get("code"))
        if profile else None
    )
    if not token:
        return jsonify({
            "error": "The recovery code is incorrect or expired."
        }), 400
    return jsonify({"ok": True, "reset_token": token})


@app.route("/recovery/reset", methods=["POST"])
def recovery_reset():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    profile = resolve_profile(data.get("username"))
    auth_type = str(data.get("auth_type") or "pin").casefold()
    credential = data.get("credential")
    try:
        Doshie_profile_lock.validate_credential(credential, auth_type)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    if not profile or not Doshie_recovery.consume_reset_token(
        profile, data.get("reset_token")
    ):
        return jsonify({
            "error": "The recovery session is incorrect or expired."
        }), 400
    result = Doshie_profile_lock.set_credential(
        profile, credential, auth_type
    )
    session.clear()
    session["public_profile"] = profile
    session["public_profile_expires"] = time.time() + 8 * 60 * 60
    _remember_profile_unlock(profile)
    session.permanent = True
    session.modified = True
    result["unlocked"] = True
    record = next(item for item in profile_catalog() if item["name"] == profile)
    return jsonify({
        "ok": True,
        "profile": profile,
        "security": result,
        "is_admin": record["is_admin"],
        "is_child": record["is_child"],
    })


@app.route("/family-login", methods=["POST"])
def family_login():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    username = " ".join(str(data.get("username") or "").split()).strip()[:80]
    credential = data.get("credential")
    profile = resolve_profile(username) if username else None
    attempt_profile = profile or username or "unknown-family-account"

    retry_after = _profile_retry_after(attempt_profile)
    if retry_after:
        return jsonify({
            "error": "Too many incorrect sign-in attempts.",
            "retry_after": retry_after,
        }), 429

    valid = bool(
        profile
        and Doshie_profile_lock.is_locked(profile)
        and Doshie_profile_lock.verify_credential(profile, credential)
    )
    if not valid:
        return _credential_failure_response(attempt_profile)

    _clear_profile_failures(profile)
    session.clear()
    session["public_profile"] = profile
    session["public_profile_expires"] = time.time() + 8 * 60 * 60
    _remember_profile_unlock(profile)
    session.permanent = True
    session.modified = True
    record = next(item for item in profile_catalog() if item["name"] == profile)
    return jsonify({
        "ok": True,
        "profile": profile,
        "is_admin": record["is_admin"],
        "is_child": record["is_child"],
    })


@app.route("/family-invites/claim", methods=["POST"])
def family_invite_claim():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    try:
        profile = Doshie_invites.claim(data.get("token"))
    except ValueError as error:
        return jsonify({"error": str(error), "code": "invalid_invite"}), 400
    session.clear()
    session["public_profile"] = profile
    session["public_profile_expires"] = time.time() + 8 * 60 * 60
    _remember_profile_unlock(profile)
    session.permanent = True
    session.modified = True
    record = next(item for item in profile_catalog() if item["name"] == profile)
    return jsonify({
        "ok": True,
        "profile": profile,
        "is_admin": record["is_admin"],
        "is_child": record["is_child"],
    })


def _recovery_settings_profile(value=None):
    authorized = _public_authorized_profile()
    if not authorized:
        return None
    requested = resolve_profile(value) if value else authorized
    if (
        not requested
        or requested.casefold() != authorized.casefold()
    ):
        return None
    return requested


@app.route("/recovery/profile", methods=["GET", "POST"])
def recovery_profile_settings():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    profile = _recovery_settings_profile(
        data.get("profile") or request.args.get("profile")
    )
    if not profile:
        return jsonify({"error": "Recovery profile is not allowed."}), 403
    if request.method == "GET":
        return jsonify({
            "contact": Doshie_recovery.get_profile_contact(profile),
            "delivery": Doshie_recovery.delivery_status(),
        })
    try:
        contact = Doshie_recovery.save_profile_contact(
            profile,
            email=data.get("email", ""),
            phone=data.get("phone", ""),
        )
        return jsonify({
            "contact": contact,
            "delivery": Doshie_recovery.delivery_status(),
        })
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Doshie_recovery.RecoveryError:
        return jsonify({"error": "Recovery settings need repair."}), 503


@app.route("/recovery/delivery", methods=["GET", "POST"])
def recovery_delivery_settings():
    authorized = _public_authorized_profile()
    if not authorized or authorized.casefold() != "hermes":
        return jsonify({
            "error": "Only authenticated Hermes can configure recovery delivery."
        }), 403
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    if request.method == "GET":
        return jsonify({"delivery": Doshie_recovery.delivery_status()})
    try:
        delivery = Doshie_recovery.save_delivery_settings(data)
        return jsonify({"delivery": delivery})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Doshie_recovery.RecoveryError:
        return jsonify({"error": "Recovery settings need repair."}), 503


@app.route("/profiles", methods=["GET"])
def profiles_get():
    try:
        profiles = []
        authorized = (
            _public_authorized_profile()
            if _is_public_funnel_request()
            else None
        )
        if _is_public_funnel_request() and authorized is None:
            return jsonify([])
        for item in profile_catalog():
            if authorized and item["name"].casefold() != authorized.casefold():
                continue
            profile = dict(item)
            security = Doshie_profile_lock.status(item["name"])
            profile["locked"] = security["locked"]
            profile["auth_type"] = security["auth_type"]
            profile["unlocked"] = _profile_session_unlocked(item["name"])
            profiles.append(profile)
        return jsonify(profiles)
    except (
        Doshie_profile_lock.ProfileLockError,
        Doshie_profile_preferences.ProfilePreferencesError,
    ):
        return jsonify({
            "error": "Doshie's profile data needs repair.",
            "code": "profile_data_unavailable",
        }), 503


@app.route("/news", methods=["GET"])
def news_get():
    topic = request.args.get("topic", "local")
    force = request.args.get("refresh", "").casefold() in {"1", "true", "yes"}
    try:
        return jsonify(Doshie_news.get_headlines(topic, force=force))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.route("/search/web", methods=["GET"])
def web_search_get():
    try:
        return jsonify(Doshie_search.web_search(request.args.get("q", "")))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 502


@app.route("/search/device", methods=["GET"])
def device_search_get():
    profile = resolve_profile(request.args.get("profile", "Hermes"))
    if profile is None:
        return jsonify({"error": "Unknown profile."}), 400
    if profile.casefold() != "hermes":
        return jsonify({
            "error": "TECRA Explorer is available only to Hermes."
        }), 403
    try:
        return jsonify(Doshie_search.device_search(request.args.get("q", "")))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.route("/profile-preferences", methods=["GET"])
def profile_preferences_get():
    profile = resolve_profile(request.args.get("profile", ""))
    if profile is None:
        return jsonify({"error": "Unknown profile."}), 400
    try:
        return jsonify({
            "profile": profile,
            "preferences": Doshie_profile_preferences.get_preferences(profile),
        })
    except Doshie_profile_preferences.ProfilePreferencesError:
        return jsonify({"error": "Profile customization needs repair."}), 503


@app.route("/profile-preferences", methods=["POST"])
def profile_preferences_save():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send valid profile preferences."}), 400
    profile = resolve_profile(data.get("profile", ""))
    if profile is None:
        return jsonify({"error": "Unknown profile."}), 400
    preference_updates = data.get("preferences", {})
    if (
        isinstance(preference_updates, dict)
        and preference_updates.get("custom_css")
        and profile.casefold() != "hermes"
    ):
        return jsonify({"error": "Only the administrator can save custom CSS."}), 403
    try:
        preferences = Doshie_profile_preferences.save_preferences(
            profile,
            data.get("preferences", {}),
        )
        if Doshie_profile_lock.is_locked(profile):
            _remember_profile_unlock(profile)
        return jsonify({"profile": profile, "preferences": preferences})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except (
        Doshie_profile_lock.ProfileLockError,
        Doshie_profile_preferences.ProfilePreferencesError,
    ):
        return jsonify({"error": "Profile customization needs repair."}), 503


@app.route("/profile-avatar/<profile_id>", methods=["GET"])
def profile_avatar_get(profile_id):
    profile = resolve_profile_id(profile_id)
    if profile is None:
        return jsonify({"error": "Unknown profile."}), 404
    path = Doshie_profile_avatar.avatar_path(profile["name"])
    if path is None:
        return jsonify({"error": "No profile photo."}), 404

    response = send_file(path, mimetype="image/png", conditional=True)
    response.headers["Cache-Control"] = "private, max-age=3600"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _avatar_request_profile(value):
    profile = resolve_profile(value)
    if profile is None:
        return None, (jsonify({"error": "Unknown profile."}), 400)
    try:
        if not _profile_session_unlocked(profile):
            return None, _profile_locked_response(profile)
    except Doshie_profile_lock.ProfileLockError:
        return None, (
            jsonify({"error": "Doshie's profile security needs repair."}),
            503,
        )
    return profile, None


@app.route("/profile-avatar", methods=["POST"])
def profile_avatar_upload():
    profile, error = _avatar_request_profile(request.form.get("profile", ""))
    if error:
        return error
    upload = request.files.get("avatar")
    if upload is None:
        return jsonify({"error": "Choose a profile photo first."}), 400

    try:
        data = upload.stream.read(Doshie_profile_avatar.MAX_AVATAR_BYTES + 1)
        Doshie_profile_avatar.save_avatar(profile, data)
        item = next(
            value for value in profile_catalog()
            if value["name"].casefold() == profile.casefold()
        )
        return jsonify({
            "profile": profile,
            "avatar_url": item["avatar_url"],
        })
    except (Doshie_profile_avatar.ProfileAvatarError, OSError) as error:
        return jsonify({"error": str(error)}), 400


@app.route("/profile-avatar/remove", methods=["POST"])
def profile_avatar_remove():
    data = request.get_json(silent=True) or {}
    profile, error = _avatar_request_profile(data.get("profile", ""))
    if error:
        return error
    try:
        removed = Doshie_profile_avatar.remove_avatar(profile)
        return jsonify({
            "profile": profile,
            "removed": removed,
            "avatar_url": None,
        })
    except OSError:
        return jsonify({"error": "Could not remove this profile photo."}), 500


def _profile_lock_request():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, None, (
            jsonify({"error": "A JSON request is required."}),
            400,
        )
    profile = resolve_profile(data.get("profile", ""))
    if profile is None:
        return None, None, (
            jsonify({"error": "Unknown profile."}),
            400,
        )
    return data, profile, None


def _credential_failure_response(profile):
    retry_after = _record_profile_failure(profile)
    if retry_after:
        return jsonify({
            "error": "Too many incorrect sign-in attempts.",
            "retry_after": retry_after,
        }), 429
    return jsonify({"error": "Incorrect sign-in credential."}), 401


@app.route("/profile-lock/unlock", methods=["POST"])
def profile_lock_unlock():
    data, profile, error = _profile_lock_request()
    if error:
        return error

    retry_after = _profile_retry_after(profile)
    if retry_after:
        return jsonify({
            "error": "Too many incorrect sign-in attempts.",
            "retry_after": retry_after,
        }), 429

    try:
        security = Doshie_profile_lock.status(profile)
        if not security["locked"]:
            _remember_profile_unlock(profile)
            return jsonify({
                "profile": profile,
                "locked": False,
                "auth_type": "none",
                "unlocked": True,
            })

        credential = data.get("credential", data.get("pin"))
        if not Doshie_profile_lock.verify_credential(profile, credential):
            return _credential_failure_response(profile)

        _clear_profile_failures(profile)
        _remember_profile_unlock(profile)
        return jsonify({
            "profile": profile,
            "locked": True,
            "auth_type": security["auth_type"],
            "unlocked": True,
        })
    except Doshie_profile_lock.ProfileLockError:
        return jsonify({
            "error": "Doshie's profile security needs repair."
        }), 503


@app.route("/profile-lock/configure", methods=["POST"])
def profile_lock_configure():
    data, profile, error = _profile_lock_request()
    if error:
        return error

    try:
        already_locked = Doshie_profile_lock.is_locked(profile)
        if already_locked and not _profile_session_unlocked(profile):
            retry_after = _profile_retry_after(profile)
            if retry_after:
                return jsonify({
                    "error": "Too many incorrect sign-in attempts.",
                    "retry_after": retry_after,
                }), 429
            current = data.get(
                "current_credential",
                data.get("current_pin"),
            )
            if not Doshie_profile_lock.verify_credential(profile, current):
                return _credential_failure_response(profile)
            _clear_profile_failures(profile)

        auth_type = str(data.get("auth_type") or "pin").casefold()
        credential = data.get("credential", data.get("pin"))
        result = Doshie_profile_lock.set_credential(
            profile,
            credential,
            auth_type,
        )
        _remember_profile_unlock(profile)
        result["unlocked"] = True
        return jsonify(result)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Doshie_profile_lock.ProfileLockError:
        return jsonify({
            "error": "Doshie's profile security needs repair."
        }), 503


@app.route("/profile-lock/lock", methods=["POST"])
def profile_lock_now():
    _data, profile, error = _profile_lock_request()
    if error:
        return error

    try:
        if not Doshie_profile_lock.is_locked(profile):
            return jsonify({
                "error": "Set a PIN or password before locking this profile."
            }), 400
        _forget_profile_unlock(profile)
        return jsonify({
            "profile": profile,
            "locked": True,
            "unlocked": False,
        })
    except Doshie_profile_lock.ProfileLockError:
        return jsonify({
            "error": "Doshie's profile security needs repair."
        }), 503


@app.route("/profile-lock/remove", methods=["POST"])
def profile_lock_remove():
    data, profile, error = _profile_lock_request()
    if error:
        return error

    try:
        if not Doshie_profile_lock.is_locked(profile):
            return jsonify({
                "profile": profile,
                "locked": False,
                "unlocked": True,
            })

        if not _profile_session_unlocked(profile):
            retry_after = _profile_retry_after(profile)
            if retry_after:
                return jsonify({
                    "error": "Too many incorrect sign-in attempts.",
                    "retry_after": retry_after,
                }), 429
            current = data.get(
                "current_credential",
                data.get("current_pin"),
            )
            if not Doshie_profile_lock.verify_credential(profile, current):
                return _credential_failure_response(profile)
            _clear_profile_failures(profile)

        Doshie_profile_lock.remove_pin(profile)
        _forget_profile_unlock(profile)
        return jsonify({
            "profile": profile,
            "locked": False,
            "unlocked": True,
        })
    except Doshie_profile_lock.ProfileLockError:
        return jsonify({
            "error": "Doshie's profile security needs repair."
        }), 503


def _health_request_online(value):
    if isinstance(value, bool):
        return value
    return str(value or "").strip().casefold() in {"1", "true", "yes", "online"}


@app.route("/health-sync/status", methods=["GET"])
def health_sync_status():
    profile = resolve_profile(request.args.get("profile", "Hermes"))
    if profile is None:
        return jsonify({"error": "Unknown profile."}), 400
    online = _health_request_online(request.args.get("online", "false"))
    result = Doshie_health_access.authorize(
        profile, online=online, unlocked=_profile_session_unlocked(profile)
    )
    result["available_permissions"] = list(Doshie_health_access.PERMISSIONS)
    result["source"] = "Android Health Connect bridge"
    return jsonify(result)


@app.route("/health-sync/configure", methods=["POST"])
def health_sync_configure():
    data = request.get_json(silent=True) or {}
    profile = resolve_profile(data.get("profile", ""))
    if profile is None:
        return jsonify({"error": "Unknown profile."}), 400
    try:
        policy = Doshie_health_access.set_policy(
            profile,
            enabled=bool(data.get("enabled", False)),
            permissions=data.get("permissions", []),
        )
        return jsonify(policy)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.route("/health-sync/authorize", methods=["POST"])
def health_sync_authorize():
    data = request.get_json(silent=True) or {}
    profile = resolve_profile(data.get("profile", ""))
    if profile is None:
        return jsonify({"error": "Unknown profile."}), 400
    categories = data.get("categories", [])
    result = Doshie_health_access.authorize(
        profile,
        online=_health_request_online(data.get("online", False)),
        unlocked=_profile_session_unlocked(profile),
    )
    requested = {str(item).strip().casefold() for item in categories}
    permitted = set(result.get("permissions", []))
    missing = sorted(requested - permitted)
    if missing:
        result["allowed"] = False
        result["reasons"] = list(result.get("reasons", [])) + ["permission_not_granted"]
        result["missing_permissions"] = missing
    Doshie_health_access.record_sync_access(profile, categories, result["allowed"])
    return jsonify(result), 200 if result["allowed"] else 403


@app.route("/chat-history", methods=["GET"])
def chat_history_get():
    profile = resolve_profile(request.args.get("profile", "Hermes"))
    if profile is None:
        return jsonify({"error": "Unknown profile."}), 400
    space = normalize_chat_space(request.args.get("space", "main"))
    if space is None:
        return jsonify({"error": "Unknown chat space."}), 400

    current, _generation = conversation_snapshot(profile, space)
    return jsonify({
        "profile": profile,
        "space": space,
        "history": current,
    })


@app.route("/settings", methods=["GET"])
def settings_get():
    return jsonify(Doshie_settings.load_settings())


@app.route("/voice-status", methods=["GET"])
def voice_status():
    return jsonify(Doshie_voice_proxy.status())


def _spotify_request_profile(data=None):
    values = data if isinstance(data, dict) else {}
    requested = values.get("profile") or request.args.get("profile", "Hermes")
    profile = resolve_profile(requested)
    if profile is None:
        raise ValueError("Unknown profile.")
    return profile


def _spotify_callback_uri():
    configured = os.environ.get("Doshie_SPOTIFY_REDIRECT_URI", "").strip()
    if configured:
        return configured
    forwarded_proto = request.headers.get(
        "X-Forwarded-Proto",
        ""
    ).split(",", 1)[0].strip().casefold()
    scheme = "https" if forwarded_proto == "https" else request.scheme
    return f"{scheme}://{request.host}/spotify/callback"


def _spotify_error(error):
    status = error.status if error.status in {400, 401, 403, 429} else 502
    return jsonify({"error": str(error)}), status


@app.route("/spotify/status", methods=["GET"])
def spotify_status():
    try:
        profile = _spotify_request_profile()
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    callback_uri = _spotify_callback_uri()
    payload = Doshie_spotify.status(profile)
    payload.update({
        "callback_uri": callback_uri,
        "callback_supported": Doshie_spotify.redirect_uri_supported(callback_uri),
        "local_setup_uri": "http://127.0.0.1:5000/spotify/callback",
    })
    return jsonify(payload)


@app.route("/spotify/config", methods=["POST"])
def spotify_config():
    data = request.json or {}
    try:
        Doshie_spotify.save_client_id(data.get("client_id"))
        profile = _spotify_request_profile(data)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    payload = Doshie_spotify.status(profile)
    payload["callback_uri"] = _spotify_callback_uri()
    return jsonify(payload)


@app.route("/spotify/connect", methods=["POST"])
def spotify_connect():
    data = request.json or {}
    try:
        profile = _spotify_request_profile(data)
        authorize_url = Doshie_spotify.begin_authorization(
            profile,
            _spotify_callback_uri(),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Doshie_spotify.SpotifyError as error:
        return _spotify_error(error)

    return jsonify({"authorize_url": authorize_url})


@app.route("/spotify/callback", methods=["GET"])
def spotify_callback():
    if request.args.get("error"):
        return redirect("/?spotify=denied")

    try:
        Doshie_spotify.complete_authorization(
            request.args.get("state"),
            request.args.get("code"),
        )
    except Doshie_spotify.SpotifyError:
        app.logger.exception("Spotify authorization failed")
        return redirect("/?spotify=error")

    return redirect("/?spotify=connected")


@app.route("/spotify/disconnect", methods=["POST"])
def spotify_disconnect():
    data = request.json or {}
    try:
        profile = _spotify_request_profile(data)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    Doshie_spotify.disconnect(profile)
    return jsonify({"connected": False, "profile": profile})


@app.route("/spotify/search", methods=["GET"])
def spotify_search():
    try:
        profile = _spotify_request_profile()
        results = Doshie_spotify.search_tracks(
            profile,
            request.args.get("q", ""),
            limit=5,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Doshie_spotify.SpotifyError as error:
        return _spotify_error(error)

    return jsonify(results)


@app.route("/spotify/playlists", methods=["GET"])
def spotify_playlists():
    try:
        profile = _spotify_request_profile()
        results = Doshie_spotify.playlists(profile, limit=10)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Doshie_spotify.SpotifyError as error:
        return _spotify_error(error)

    return jsonify(results)


@app.route("/spotify/now-playing", methods=["GET"])
def spotify_now_playing():
    try:
        profile = _spotify_request_profile()
        result = Doshie_spotify.now_playing(profile)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Doshie_spotify.SpotifyError as error:
        return _spotify_error(error)

    return jsonify(result)


@app.route("/spotify/control", methods=["POST"])
def spotify_control():
    data = request.json or {}
    try:
        profile = _spotify_request_profile(data)
        Doshie_spotify.control(
            profile,
            data.get("action"),
            uri=data.get("uri"),
            context_uri=data.get("context_uri"),
            device_id=data.get("device_id"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Doshie_spotify.SpotifyError as error:
        return _spotify_error(error)

    return jsonify({"ok": True})


@app.route("/speak", methods=["POST"])
def speak():
    data = request.json or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify({"error": "Text is required."}), 400

    try:
        audio = Doshie_voice_proxy.synthesize(text)
    except ValueError:
        return jsonify({"error": "Text is required."}), 400
    except Doshie_voice_proxy.VoiceUnavailable as error:
        return jsonify({"error": str(error)}), 503

    return Response(
        audio,
        mimetype="audio/wav",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": "inline; filename=Doshie-voice.wav",
            "X-Doshie-Voice": "Hermes",
        },
    )


@app.route("/settings", methods=["POST"])
def settings_post():
    data = request.json or {}
    settings = Doshie_settings.load_settings()

    if "auto_memory" in data:
        settings["auto_memory"] = bool(data["auto_memory"])

    if "speak_replies" in data:
        settings["speak_replies"] = bool(data["speak_replies"])

    if "voice_identity" in data:
        identity = str(data["voice_identity"]).strip()
        if identity in ("hermes", "Doshie", "device"):
            settings["voice_identity"] = identity

    if "voice_engine" in data:
        engine = str(data["voice_engine"]).strip()
        if engine in ("clone", "device"):
            settings["voice_engine"] = engine

    if "voice_rate" in data:
        try:
            settings["voice_rate"] = max(
                0.5,
                min(2.0, float(data["voice_rate"]))
            )
        except (TypeError, ValueError):
            pass

    if "voice_pitch" in data:
        try:
            settings["voice_pitch"] = max(
                0.5,
                min(2.0, float(data["voice_pitch"]))
            )
        except (TypeError, ValueError):
            pass


    if "voice_preset" in data:
        preset = str(data["voice_preset"]).strip()

        if preset in ("custom", "calm", "tech", "dino"):
            settings["voice_preset"] = preset


    if "mode" in data:
        mode = str(data["mode"]).strip()

        if mode in ("family", "normal", "tech", "gaming"):
            settings["mode"] = mode

    if "default_weather_location" in data:
        location = str(data["default_weather_location"]).strip()
        if location:
            settings["default_weather_location"] = location

    Doshie_settings.save_settings(settings)
    return jsonify(settings)


@app.route("/new-chat", methods=["POST"])
def new_chat():
    data = request.get_json(silent=True) or {}
    profile = resolve_profile(data.get("profile", "Hermes"))
    if profile is None:
        return jsonify({"error": "Unknown profile."}), 400
    space = normalize_chat_space(data.get("space", "main"))
    if space is None:
        return jsonify({"error": "Unknown chat space."}), 400

    reset_chat_history(profile, space)

    return jsonify({"ok": True, "profile": profile, "space": space})


@app.route("/notes", methods=["POST"])
def notes_create():
    data = request.json or {}

    note = str(data.get("note", "")).strip()
    tag = str(data.get("tag", "General")).strip() or "General"

    if not note:
        return jsonify({"error": "Note cannot be empty."}), 400

    conn = Doshie_memory.connect_db()
    conn.execute(
        "INSERT INTO notes (note, tag) VALUES (?, ?)",
        (note, tag)
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/notes", methods=["GET"])
def notes_get():
    rows = Doshie_memory.get_notes()

    return jsonify([
        {
            "id": note_id,
            "note": note,
            "tag": tag or "General"
        }
        for note_id, note, tag in rows
    ])


@app.route("/tasks", methods=["POST"])
def tasks_create():
    data = request.json or {}

    task = str(data.get("task", "")).strip()
    priority = str(data.get("priority", "Normal")).strip()
    due_date = str(data.get("due_date", "")).strip() or None
    tag = str(data.get("tag", "General")).strip() or "General"

    assigned_to = data.get("assigned_to")

    try:
        assigned_to = int(assigned_to) if assigned_to else None
    except (TypeError, ValueError):
        assigned_to = None

    if not task:
        return jsonify({"error": "Task cannot be empty."}), 400

    if priority not in ("Low", "Normal", "High"):
        priority = "Normal"

    conn = Doshie_memory.connect_db()

    conn.execute(
        """
        INSERT INTO tasks (
            task,
            done,
            priority,
            due_date,
            tag,
            assigned_to
        )
        VALUES (?, 0, ?, ?, ?, ?)
        """,
        (task, priority, due_date, tag, assigned_to)
    )

    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/tasks", methods=["GET"])
def tasks_get():
    rows = Doshie_memory.get_tasks()

    conn = Doshie_memory.connect_db()

    results = []

    for task_id, task, done, priority, due_date, tag, assigned_to in rows:
        assigned_name = ""

        if assigned_to:
            member = conn.execute(
                """
                SELECT name
                FROM family_members
                WHERE id = ?
                """,
                (assigned_to,)
            ).fetchone()

            if member:
                assigned_name = member[0]

        results.append({
            "id": task_id,
            "task": task,
            "done": bool(done),
            "priority": priority or "Normal",
            "due_date": due_date or "",
            "tag": tag or "General",
            "assigned_to": assigned_to,
            "assigned_name": assigned_name
        })

    conn.close()

    return jsonify(results)


@app.route("/tasks/<int:task_id>/done", methods=["POST"])
def tasks_done(task_id):
    reply = Doshie_memory.complete_task(task_id)
    return jsonify({"reply": reply})


@app.route("/notes/<int:note_id>", methods=["PUT"])
def notes_update(note_id):
    data = request.json or {}
    value = str(data.get("note", "")).strip()

    if not value:
        return jsonify({"error": "Note cannot be empty."}), 400

    conn = Doshie_memory.connect_db()
    conn.execute(
        "UPDATE notes SET note = ? WHERE id = ?",
        (value, note_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/notes/<int:note_id>", methods=["DELETE"])
def notes_delete(note_id):
    conn = Doshie_memory.connect_db()
    conn.execute(
        "DELETE FROM notes WHERE id = ?",
        (note_id,)
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def tasks_update(task_id):
    data = request.json or {}
    updates = []
    values = []

    if "task" in data:
        value = str(data["task"]).strip()
        if not value:
            return jsonify({"error": "Task cannot be empty."}), 400
        updates.append("task = ?")
        values.append(value)

    if "done" in data:
        updates.append("done = ?")
        values.append(1 if data["done"] else 0)

    if "priority" in data:
        priority = str(data.get("priority", "Normal")).strip().title()
        if priority not in ("Low", "Normal", "High"):
            return jsonify({"error": "Invalid priority."}), 400
        updates.append("priority = ?")
        values.append(priority)

    if "due_date" in data:
        due_date = str(data.get("due_date", "")).strip() or None
        updates.append("due_date = ?")
        values.append(due_date)

    if "tag" in data:
        tag = str(data.get("tag", "General")).strip() or "General"
        updates.append("tag = ?")
        values.append(tag)

    if "assigned_to" in data:
        assigned_to = data.get("assigned_to")

        try:
            assigned_to = int(assigned_to) if assigned_to else None
        except (TypeError, ValueError):
            assigned_to = None

        updates.append("assigned_to = ?")
        values.append(assigned_to)

    conn = Doshie_memory.connect_db()
    exists = conn.execute(
        "SELECT 1 FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    if not exists:
        conn.close()
        return jsonify({"error": "Task not found."}), 404

    if updates:
        values.append(task_id)
        conn.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
            values
        )

    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def tasks_delete(task_id):
    conn = Doshie_memory.connect_db()
    conn.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/family", methods=["GET"])
def family_get():
    rows = Doshie_memory.get_family_members()

    return jsonify([
        {
            "id": member_id,
            "name": name,
            "role": role or "Family",
            "notes": notes or ""
        }
        for member_id, name, role, notes in rows
    ])


@app.route("/family", methods=["POST"])
def family_create():
    data = request.json or {}

    name = str(data.get("name", "")).strip()
    role = str(data.get("role", "Family")).strip()
    notes = str(data.get("notes", "")).strip() or None

    if not name:
        return jsonify({"error": "Name is required."}), 400

    reply = Doshie_memory.add_family_member(
        name,
        role or "Family",
        notes
    )

    return jsonify({"reply": reply})


@app.route("/family/<int:member_id>", methods=["PUT"])
def family_update(member_id):
    data = request.json or {}

    reply = Doshie_memory.update_family_member(
        member_id,
        data.get("name"),
        data.get("role"),
        data.get("notes")
    )

    return jsonify({"reply": reply})


@app.route("/family/<int:member_id>", methods=["DELETE"])
def family_delete(member_id):
    reply = Doshie_memory.remove_family_member(member_id)
    return jsonify({"reply": reply})


@app.route("/shopping", methods=["GET"])
def shopping_get():
    rows = Doshie_memory.get_shopping_items()

    return jsonify([
        {
            "id": item_id,
            "item": item,
            "quantity": quantity or "",
            "bought": bool(bought),
            "added_by": added_by or "",
            "category": category or "Other"
        }
        for item_id, item, quantity, bought, added_by, category in rows
    ])


@app.route("/shopping", methods=["POST"])
def shopping_create():
    data = request.json or {}

    item = str(data.get("item", "")).strip()
    quantity = str(data.get("quantity", "")).strip() or None
    added_by = str(data.get("added_by", "")).strip() or None
    category = str(data.get("category", "Other")).strip() or "Other"

    if not item:
        return jsonify({"error": "Item is required."}), 400

    reply = Doshie_memory.add_shopping_item(
        item,
        quantity,
        added_by,
        category
    )

    return jsonify({"reply": reply})


@app.route("/shopping/<int:item_id>", methods=["PUT"])
def shopping_update(item_id):
    data = request.json or {}

    bought = bool(data.get("bought", False))

    reply = Doshie_memory.set_shopping_bought(
        item_id,
        bought
    )

    return jsonify({"reply": reply})


@app.route("/shopping/<int:item_id>", methods=["DELETE"])
def shopping_delete(item_id):
    reply = Doshie_memory.delete_shopping_item(item_id)
    return jsonify({"reply": reply})


@app.route("/admin/terminal/start", methods=["POST"])
def admin_terminal_start():
    data = request.get_json(silent=True) or {}
    profile, error = _require_invite_admin(data.get("profile"))
    if error:
        return error
    mode = "maintenance" if data.get("mode") == "maintenance" else "direct"
    try:
        session_id, cwd = _terminal_start(profile, data.get("cwd") or app.root_path, mode)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except OSError:
        app.logger.exception("Could not start user-level terminal")
        return jsonify({"error": "Could not start the user-level terminal."}), 500
    return jsonify({
        "session_id": session_id,
        "cwd": cwd,
        "user": os.environ.get("USER", "hermes-duran"),
        "root": False,
        "mode": mode,
        "approval_required": mode == "maintenance",
        "message": "User-level terminal opened. sudo remains an explicit choice.",
    }), 201


@app.route("/admin/terminal/output", methods=["GET"])
def admin_terminal_output():
    profile, error = _require_invite_admin(request.args.get("profile"))
    if error:
        return error
    session_id = request.args.get("session_id")
    with terminal_sessions_lock:
        item = _terminal_get_locked(session_id, profile)
        if not item:
            return jsonify({"error": "Terminal session not found."}), 404
        item["last_activity"] = time.time()
        output = _terminal_read_locked(item)
        cwd = item["cwd"]
        alive = not item.get("closed")
        if alive:
            try:
                os.kill(item["pid"], 0)
            except OSError:
                alive = False
        if not alive:
            _terminal_stop_locked(session_id)
    return jsonify({"output": output, "alive": alive, "cwd": cwd})


@app.route("/admin/terminal/input", methods=["POST"])
def admin_terminal_input():
    data = request.get_json(silent=True) or {}
    profile, error = _require_invite_admin(data.get("profile"))
    if error:
        return error
    command = data.get("input", "")
    if not isinstance(command, str):
        return jsonify({"error": "Terminal input must be text."}), 400
    if len(command) > 12000:
        return jsonify({"error": "Keep terminal input under 12,000 characters."}), 413
    approved = bool(data.get("approved", False))
    with terminal_sessions_lock:
        item = _terminal_get_locked(data.get("session_id"), profile)
        if not item:
            return jsonify({"error": "Terminal session not found."}), 404
        if item.get("mode") == "maintenance" and not approved and _terminal_command_requires_approval(command):
            return jsonify({
                "error": "Hermes maintenance mode paused this command until you approve it.",
                "approval_required": True,
            }), 409
        try:
            os.write(item["fd"], command.encode("utf-8"))
        except OSError:
            _terminal_stop_locked(data.get("session_id"))
            return jsonify({"error": "Terminal session closed."}), 410
        item["last_activity"] = time.time()
    return jsonify({"ok": True})


@app.route("/admin/terminal/stop", methods=["POST"])
def admin_terminal_stop():
    data = request.get_json(silent=True) or {}
    profile, error = _require_invite_admin(data.get("profile"))
    if error:
        return error
    with terminal_sessions_lock:
        item = _terminal_get_locked(data.get("session_id"), profile)
        if item:
            _terminal_stop_locked(data.get("session_id"))
    return jsonify({"stopped": True})


def _enabled_hermes_agent():
    agent = Doshie_agents.get_agent_by_name("Hermes")
    if not agent or not agent.get("enabled", True):
        return None
    return agent


@app.route("/hermes-ai/history", methods=["GET", "DELETE"])
def hermes_ai_history():
    data = request.get_json(silent=True) if request.method == "DELETE" else request.args
    data = data if isinstance(data, dict) else request.args
    _admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error
    agent = _enabled_hermes_agent()
    if not agent:
        return jsonify({"error": "Hermes AI is unavailable or disabled."}), 404
    conversation = "Agent " + agent["id"]
    with history_lock:
        if request.method == "DELETE":
            Doshie_history.clear_history(conversation)
            return jsonify({"cleared": True})
        messages = Doshie_history.load_history(conversation)
    return jsonify({
        "messages": messages,
        "agent": {"id": agent["id"], "name": agent["name"]},
    })


@app.route("/hermes-ai/chat", methods=["POST"])
def hermes_ai_chat():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error
    agent = _enabled_hermes_agent()
    if not agent:
        return jsonify({"error": "Hermes AI is unavailable or disabled."}), 404
    message = str(data.get("message") or "").strip()
    if len(message) > 4000:
        return jsonify({"error": "Keep the message under 4,000 characters."}), 413

    attachment_ids = data.get("attachments", [])
    if not isinstance(attachment_ids, list) or len(attachment_ids) > 5:
        return jsonify({"error": "Choose up to five valid attachments."}), 400
    try:
        attachment_context, attachment_items = Doshie_chat_attachments.prompt_context(
            admin, attachment_ids
        )
        image_payloads = Doshie_chat_attachments.image_payloads(
            admin, attachment_ids
        )
    except Doshie_chat_attachments.AttachmentError:
        return jsonify({"error": "One of those attachments is unavailable."}), 400
    if not message and not attachment_items:
        return jsonify({"error": "Type a message or attach a file for Hermes first."}), 400

    model_message = message
    if attachment_context:
        model_message = ((message + "\n\n") if message else "") + (
            "USER ATTACHMENTS:\n" + attachment_context
        )

    conversation = "Agent " + agent["id"]
    with history_lock:
        recent = Doshie_history.load_history(conversation)
    # Vision requests must stay small enough for the local model's context window.
    # Keep the saved history intact, but omit it while an image is being inspected.
    model_recent = [] if image_payloads else recent[-6:]
    diagnostic_intent = bool(re.search(
        r"\b(diagnos\w*|troubleshoot\w*|run\s+(?:python\s+)?checks?|inspect\s+Doshie|check\s+Doshie)\b",
        message,
        re.IGNORECASE,
    ))
    if diagnostic_intent and not image_payloads:
        try:
            existing = next(
                (
                    item for item in Doshie_permissions.list_requests(100)
                    if item.get("action") == "run_regression"
                    and item.get("status") == "pending"
                ),
                None,
            )
            diagnostic = existing or Doshie_permissions.create_regression_request(
                admin,
                "Hermes diagnosis: run Doshie Python compile and regression checks",
            )
            request_label = str(diagnostic.get("id") or "")[:8]
            state = "already waiting" if existing else "now waiting"
            reply = (
                "Yes. I can diagnose Doshie and inspect its project code. "
                f"Python diagnostic request {request_label} is {state} for your approval. "
                "Open Growth Core, review the exact request, and press Approve to run it. "
                "I will not run tests or change files before you approve them."
            )
        except Exception:
            app.logger.exception("Hermes could not queue diagnostics")
            return jsonify({"error": "Hermes could not queue diagnostics right now."}), 503
    else:
        try:
            reply = Doshie_memory.ask_Doshie(
                model_recent,
                model_message,
                raise_on_error=True,
                profile=admin,
                conversation_profile=conversation,
                system_context=(
                    "You are Hermes AI in your dedicated workspace. "
                    "You can inspect the current Doshie source files with read-only project tools. "
                    "You can prepare exact code changes with propose_code_edit; that tool places "
                    "the change in the administrator approval queue and never writes directly. "
                    "When the user asks whether you can make changes, answer clearly: yes, you "
                    "can inspect and prepare an exact proposal, but you never apply changes "
                    "without the user's approval. When a specific change is requested, gather "
                    "the minimum evidence needed and propose the change instead of giving a "
                    "generic technician checklist. Never refer the user to a support team. "
                    "Never say you lack access to Doshie code or internal systems; use your "
                    "approved project tools when evidence is needed. Never claim an edit was "
                    "applied before tool confirmation. Do not call consult_hermes_ai because "
                    "you are already Hermes.\n"
                    + Doshie_agents.agent_system_context(agent)
                ),
                brain_mode=agent.get("model_mode", "auto"),
                memory_scope=agent.get("memory_scope", "none"),
                images=image_payloads,
            )
        except Exception:
            app.logger.exception("Hermes AI workspace request failed")
            return jsonify({"error": "Hermes could not answer right now."}), 503

    updated = recent + [
        {"role": "user", "content": message or "Shared an attachment."},
        {"role": "assistant", "content": reply},
    ]
    with history_lock:
        Doshie_history.save_history(updated, conversation)
    return jsonify({
        "reply": reply,
        "agent": {"id": agent["id"], "name": agent["name"]},
        "attachments": attachment_items,
    })


@app.route("/admin/agents", methods=["GET", "POST"])
def admin_agents_collection():
    data = request.get_json(silent=True) if request.method == "POST" else request.args
    data = data if isinstance(data, dict) else request.args
    _admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error

    if request.method == "GET":
        return jsonify({
            "agents": Doshie_agents.list_agents(),
            "model_modes": Doshie_agents.MODEL_MODES,
            "memory_scopes": Doshie_agents.MEMORY_SCOPES,
            "capabilities": Doshie_agents.CAPABILITIES,
            "approval_required": True,
        })

    try:
        agent = Doshie_agents.save_agent(data)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except OSError:
        app.logger.exception("Could not save Doshie agent")
        return jsonify({"error": "Could not securely save this AI."}), 500
    return jsonify({"agent": agent}), 201


@app.route("/admin/agents/<agent_id>", methods=["DELETE"])
def admin_agent_delete(agent_id):
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    _admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error
    if not Doshie_agents.delete_agent(agent_id):
        return jsonify({"error": "That AI was not found."}), 404
    return jsonify({"deleted": True, "id": agent_id})


@app.route("/admin/agents/<agent_id>/test", methods=["POST"])
def admin_agent_test(agent_id):
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error

    agent = Doshie_agents.get_agent(agent_id)
    if not agent:
        return jsonify({"error": "That AI was not found."}), 404
    if not agent.get("enabled", True):
        return jsonify({"error": "Enable this AI before testing it."}), 409

    message = str(data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Type a test request first."}), 400
    if len(message) > 2000:
        return jsonify({"error": "Keep the test under 2,000 characters."}), 413

    model_name = Doshie_memory.choose_brain_model(
        message + " " + agent.get("purpose", ""),
        brain_mode=agent.get("model_mode", "auto"),
    )
    try:
        reply = Doshie_memory.ask_Doshie(
            [],
            message,
            raise_on_error=True,
            profile=admin,
            conversation_profile="Agent " + agent["id"],
            system_context=Doshie_agents.agent_system_context(agent),
            brain_mode=agent.get("model_mode", "auto"),
            memory_scope=agent.get("memory_scope", "none"),
        )
    except Exception:
        app.logger.exception("Doshie agent test failed")
        return jsonify({"error": "The local agent could not answer right now."}), 503

    return jsonify({
        "reply": reply,
        "agent": {
            "id": agent["id"],
            "name": agent["name"],
            "approval_required": True,
        },
        "model": model_name,
    })


@app.route("/admin/migration", methods=["POST"])
def admin_migration_create():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    _admin, error = _require_invite_admin(data.get("profile"))
    if error:
        return error

    script = os.path.join(app.root_path, "scripts", "backup-Doshie-now")
    try:
        completed = subprocess.run(
            [script],
            cwd=app.root_path,
            capture_output=True,
            text=True,
            timeout=180,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        app.logger.exception("Doshie migration package failed")
        return jsonify({"error": "Could not create the migration package."}), 500

    archive = ""
    for line in completed.stdout.splitlines():
        candidate = line.strip()
        if candidate.endswith(".tar.gz"):
            archive = candidate
            break
    if not archive or not os.path.isfile(archive):
        return jsonify({"error": "Migration package verification failed."}), 500
    checksum = archive + ".sha256"
    if not os.path.isfile(checksum):
        return jsonify({"error": "Migration checksum is missing."}), 500
    return jsonify({
        "archive": archive,
        "checksum": checksum,
        "verified": True,
    })


@app.route("/backup", methods=["POST"])
def backup_create():
    reply = Doshie_memory.create_backup()
    return jsonify({"reply": reply})


@app.route("/family-dashboard", methods=["GET"])
def family_dashboard():
    conn = Doshie_memory.connect_db()

    members = conn.execute(
        """
        SELECT id, name, role
        FROM family_members
        ORDER BY id
        """
    ).fetchall()

    results = []

    for member_id, name, role in members:
        tasks = conn.execute(
            """
            SELECT id, task, done, priority, due_date
            FROM tasks
            WHERE assigned_to = ?
              AND done = 0
            ORDER BY due_date, id
            """,
            (member_id,)
        ).fetchall()

        routines = conn.execute(
            """
            SELECT id, routine, weekday, active
            FROM routines
            WHERE assigned_to = ?
              AND active = 1
            ORDER BY weekday, id
            """,
            (member_id,)
        ).fetchall()

        results.append({
            "id": member_id,
            "name": name,
            "role": role or "Family",
            "open_tasks": [
                {
                    "id": task_id,
                    "task": task,
                    "priority": priority or "Normal",
                    "due_date": due_date or ""
                }
                for task_id, task, done, priority, due_date in tasks
            ],
            "routines": [
                {
                    "id": routine_id,
                    "routine": routine,
                    "weekday": weekday or "",
                    "active": bool(active)
                }
                for routine_id, routine, weekday, active in routines
            ]
        })

    unassigned = conn.execute(
        """
        SELECT id, task, priority, due_date
        FROM tasks
        WHERE assigned_to IS NULL
          AND done = 0
        ORDER BY due_date, id
        """
    ).fetchall()

    conn.close()

    return jsonify({
        "members": results,
        "unassigned": [
            {
                "id": task_id,
                "task": task,
                "priority": priority or "Normal",
                "due_date": due_date or ""
            }
            for task_id, task, priority, due_date in unassigned
        ]
    })


@app.route("/reminders", methods=["GET"])
def reminders_get():
    rows = Doshie_memory.get_reminders()

    return jsonify([
        {
            "id": reminder_id,
            "reminder": reminder,
            "due_date": due_date or "",
            "assigned_to": assigned_to,
            "done": bool(done)
        }
        for reminder_id, reminder, due_date, assigned_to, done in rows
    ])


@app.route("/reminders", methods=["POST"])
def reminders_create():
    data = request.json or {}

    reminder = str(data.get("reminder", "")).strip()
    due_date = str(data.get("due_date", "")).strip() or None

    assigned_to = data.get("assigned_to")

    try:
        assigned_to = int(assigned_to) if assigned_to else None
    except (TypeError, ValueError):
        assigned_to = None

    if not reminder:
        return jsonify({"error": "Reminder is required."}), 400

    reply = Doshie_memory.add_reminder(
        reminder,
        due_date=due_date,
        assigned_to=assigned_to
    )

    return jsonify({"reply": reply})


@app.route("/reminders/<int:reminder_id>/done", methods=["POST"])
def reminders_done(reminder_id):
    reply = Doshie_memory.complete_reminder(reminder_id)
    return jsonify({"reply": reply})


@app.route("/reminders/<int:reminder_id>", methods=["DELETE"])
def reminders_delete(reminder_id):
    conn = Doshie_memory.connect_db()

    conn.execute(
        "DELETE FROM reminders WHERE id = ?",
        (reminder_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/routines/today", methods=["GET"])
def routines_today():
    from datetime import date

    weekday = date.today().strftime("%A")

    conn = Doshie_memory.connect_db()

    rows = conn.execute(
        """
        SELECT id, routine, weekday, assigned_to
        FROM routines
        WHERE active = 1
          AND lower(weekday) = lower(?)
        ORDER BY id
        """,
        (weekday,)
    ).fetchall()

    results = []

    for routine_id, routine, routine_day, assigned_to in rows:
        assigned_name = ""

        if assigned_to:
            member = conn.execute(
                """
                SELECT name
                FROM family_members
                WHERE id = ?
                """,
                (assigned_to,)
            ).fetchone()

            if member:
                assigned_name = member[0]

        done_today = False

        completion = conn.execute(
            """
            SELECT 1
            FROM routine_completions
            WHERE routine_id = ?
              AND completed_date = ?
            """,
            (
                routine_id,
                date.today().isoformat()
            )
        ).fetchone()

        if completion:
            done_today = True

        results.append({
            "id": routine_id,
            "routine": routine,
            "weekday": routine_day,
            "assigned_name": assigned_name,
            "done_today": done_today
        })

    conn.close()

    return jsonify(results)


@app.route("/routines/<int:routine_id>/done-today", methods=["POST"])
def routine_done_today_route(routine_id):
    reply = Doshie_memory.complete_routine_for_today(routine_id)
    return jsonify({"reply": reply})


@app.route("/family-today", methods=["GET"])
def family_today():
    from datetime import date

    today = date.today()
    today_iso = today.isoformat()
    weekday = today.strftime("%A")

    conn = Doshie_memory.connect_db()

    members = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT id, name FROM family_members"
        ).fetchall()
    }

    tasks = conn.execute(
        """
        SELECT id, task, assigned_to, priority
        FROM tasks
        WHERE done = 0
          AND due_date = ?
        ORDER BY assigned_to, id
        """,
        (today_iso,)
    ).fetchall()

    reminders = conn.execute(
        """
        SELECT id, reminder, assigned_to
        FROM reminders
        WHERE done = 0
          AND due_date = ?
        ORDER BY assigned_to, id
        """,
        (today_iso,)
    ).fetchall()

    routines = conn.execute(
        """
        SELECT r.id, r.routine, r.assigned_to
        FROM routines r
        WHERE r.active = 1
          AND lower(r.weekday) = lower(?)
          AND NOT EXISTS (
              SELECT 1
              FROM routine_completions rc
              WHERE rc.routine_id = r.id
                AND rc.completed_date = ?
          )
        ORDER BY r.assigned_to, r.id
        """,
        (weekday, today_iso)
    ).fetchall()

    conn.close()

    return jsonify({
        "date": today_iso,
        "weekday": weekday,
        "tasks": [
            {
                "type": "task",
                "id": item_id,
                "text": task,
                "assigned_name": members.get(assigned_to, ""),
                "priority": priority or "Normal"
            }
            for item_id, task, assigned_to, priority in tasks
        ],
        "reminders": [
            {
                "type": "reminder",
                "id": reminder_id,
                "text": reminder,
                "assigned_name": members.get(assigned_to, "")
            }
            for reminder_id, reminder, assigned_to in reminders
        ],
        "routines": [
            {
                "type": "routine",
                "id": routine_id,
                "text": routine,
                "assigned_name": members.get(assigned_to, "")
            }
            for routine_id, routine, assigned_to in routines
        ]
    })


@app.route("/gaming-dashboard", methods=["GET"])
def gaming_dashboard():
    import os
    import shutil

    total, used, free = shutil.disk_usage(
        os.path.expanduser("~")
    )

    battery = Doshie_memory.get_battery_status()
    status = Doshie_memory.get_device_status()
    ai_online = Doshie_memory.server_ready()

    return jsonify({
        "battery": battery,
        "status": status,
        "ai_online": ai_online,
        "storage_total_gb":
            round(total / (1024 ** 3), 1),
        "storage_used_gb":
            round(used / (1024 ** 3), 1),
        "storage_free_gb":
            round(free / (1024 ** 3), 1)
    })


@app.route("/tech-dashboard", methods=["GET"])
def tech_dashboard():
    import os
    import shutil
    import subprocess

    # Storage
    total, used, free = shutil.disk_usage(os.path.expanduser("~"))

    # Memory
    mem_total = None
    mem_available = None

    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            info = {}

            for line in f:
                key, value = line.split(":", 1)
                info[key] = value.strip()

        mem_total = info.get("MemTotal", "")
        mem_available = info.get("MemAvailable", "")

    except Exception:
        pass

    # Local AI status
    ai_online = Doshie_memory.server_ready()

    # CPU load
    load_average = ""

    try:
        with open("/proc/loadavg", "r", encoding="utf-8") as f:
            load_average = f.read().strip().split()[0]
    except Exception:
        pass

    # Architecture
    architecture = ""

    try:
        architecture = subprocess.check_output(
            ["uname", "-m"],
            text=True,
            timeout=3
        ).strip()
    except Exception:
        pass

    return jsonify({
        "architecture": architecture,
        "load_average": load_average,
        "memory_total": mem_total,
        "memory_available": mem_available,
        "storage_total_gb": round(total / (1024 ** 3), 1),
        "storage_used_gb": round(used / (1024 ** 3), 1),
        "storage_free_gb": round(free / (1024 ** 3), 1),
        "ai_online": ai_online
    })


def _messaging_profile_request(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    requested = payload.get("profile") or request.args.get("profile", "Hermes")
    profile = resolve_profile(requested)
    if profile is None:
        return None, (jsonify({"error": "Unknown profile."}), 400)
    try:
        if not _profile_session_unlocked(profile):
            return None, _profile_locked_response(profile)
    except Doshie_profile_lock.ProfileLockError:
        return None, (jsonify({
            "error": "Doshie's profile security needs repair.",
            "code": "profile_data_unavailable",
        }), 503)
    Doshie_messaging.touch_presence(profile)
    return profile, None


@app.route("/messaging/people", methods=["GET"])
def messaging_people():
    profile, error = _messaging_profile_request()
    if error:
        return error
    return jsonify({
        "profile": profile,
        "people": Doshie_messaging.people(profile_catalog(), profile),
    })


@app.route("/messaging/presence", methods=["GET", "POST"])
def messaging_presence():
    payload = request.get_json(silent=True) if request.method == "POST" else {}
    profile, error = _messaging_profile_request(payload)
    if error:
        return error
    return jsonify({"ok": True, "profile": profile, "online": True})


@app.route("/messaging/conversations", methods=["GET"])
def messaging_conversations_get():
    profile, error = _messaging_profile_request()
    if error:
        return error
    return jsonify({
        "profile": profile,
        "conversations": Doshie_messaging.list_conversations(profile),
    })


@app.route("/messaging/conversations", methods=["POST"])
def messaging_conversations_create():
    data = request.get_json(silent=True) or {}
    profile, error = _messaging_profile_request(data)
    if error:
        return error
    members = data.get("members", [])
    if isinstance(members, str):
        members = [members]
    if not isinstance(members, list):
        return jsonify({"error": "Members must be a list."}), 400
    resolved_members = []
    for value in members:
        member = resolve_profile(value)
        if member is None:
            return jsonify({"error": "Choose valid family profiles."}), 400
        resolved_members.append(member)
    try:
        conversation_id = Doshie_messaging.create_conversation(
            profile,
            resolved_members,
            title=data.get("title", ""),
            kind=data.get("kind", "direct"),
        )
    except (PermissionError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({
        "ok": True,
        "conversation_id": conversation_id,
        "conversations": Doshie_messaging.list_conversations(profile),
    }), 201


@app.route("/messaging/conversations/<conversation_id>/messages", methods=["GET"])
def messaging_messages_get(conversation_id):
    profile, error = _messaging_profile_request()
    if error:
        return error
    try:
        messages = Doshie_messaging.get_messages(
            conversation_id,
            profile,
            after_id=request.args.get("after_id", 0),
            limit=request.args.get("limit", 100),
        )
    except PermissionError:
        return jsonify({"error": "Conversation access denied."}), 403
    return jsonify({
        "profile": profile,
        "conversation_id": conversation_id,
        "messages": messages,
    })


@app.route("/messaging/conversations/<conversation_id>/messages", methods=["POST"])
def messaging_messages_post(conversation_id):
    data = request.get_json(silent=True) or {}
    profile, error = _messaging_profile_request(data)
    if error:
        return error
    try:
        message = Doshie_messaging.send_message(
            conversation_id, profile, data.get("body", data.get("message", ""))
        )
    except PermissionError:
        return jsonify({"error": "Conversation access denied."}), 403
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "message": message}), 201


@app.route("/messaging/conversations/<conversation_id>/read", methods=["POST"])
def messaging_messages_read(conversation_id):
    data = request.get_json(silent=True) or {}
    profile, error = _messaging_profile_request(data)
    if error:
        return error
    try:
        result = Doshie_messaging.mark_read(
            conversation_id, profile, data.get("message_id")
        )
    except PermissionError:
        return jsonify({"error": "Conversation access denied."}), 403
    return jsonify({"ok": True, **result})


@app.route("/messaging/typing", methods=["POST"])
def messaging_typing_post():
    data = request.get_json(silent=True) or {}
    profile, error = _messaging_profile_request(data)
    if error:
        return error
    conversation_id = str(data.get("conversation_id", "")).strip()
    try:
        users = Doshie_messaging.set_typing(
            conversation_id,
            profile,
            bool(data.get("typing")),
        )
    except PermissionError:
        return jsonify({"error": "Conversation access denied."}), 403
    return jsonify({
        "ok": True,
        "conversation_id": conversation_id,
        "typing": users,
    })


@app.route("/messaging/conversations/<conversation_id>/typing", methods=["GET"])
def messaging_typing_get(conversation_id):
    profile, error = _messaging_profile_request()
    if error:
        return error
    try:
        users = Doshie_messaging.get_typing_users(conversation_id, profile)
    except PermissionError:
        return jsonify({"error": "Conversation access denied."}), 403
    return jsonify({
        "conversation_id": conversation_id,
        "typing": users,
    })


@app.route("/chat-attachment", methods=["POST"])
def chat_attachment_upload():
    profile = resolve_profile(request.form.get("profile", ""))
    if profile is None:
        return jsonify({"error": "Choose a valid profile first."}), 400
    upload = request.files.get("attachment")
    if upload is None:
        return jsonify({"error": "Choose a file or photo first."}), 400
    try:
        data = upload.stream.read(Doshie_chat_attachments.MAX_BYTES + 1)
        item = Doshie_chat_attachments.save_attachment(
            profile, upload.filename, data
        )
        item["url"] = (
            f"/chat-attachment/{item['id']}?profile={profile}"
        )
        return jsonify({"attachment": item})
    except Doshie_chat_attachments.AttachmentError as error:
        return jsonify({"error": str(error)}), 400
    except OSError:
        return jsonify({"error": "Could not store that attachment."}), 500


@app.route("/chat-attachment/<attachment_id>", methods=["GET"])
def chat_attachment_get(attachment_id):
    profile = resolve_profile(request.args.get("profile", ""))
    if profile is None:
        return jsonify({"error": "Choose a valid profile first."}), 400
    try:
        metadata, path = Doshie_chat_attachments.get_attachment(
            profile, attachment_id
        )
    except Doshie_chat_attachments.AttachmentError:
        return jsonify({"error": "Attachment not found."}), 404
    response = send_file(
        path,
        mimetype=metadata["mime"],
        as_attachment=request.args.get("download") == "1",
        download_name=metadata["name"],
        conditional=True,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/chat", methods=["POST"])
def chat():
    try:
        return _chat_impl()
    except Exception:
        app.logger.exception("Unhandled exception in Doshie chat")
        return jsonify({
            "reply": "Doshie ran into a problem while answering. Please try again.",
            "error": "chat_failed"
        }), 500


def _chat_impl():
    global history

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "reply": "Send a valid text message.",
            "error": "invalid_request"
        }), 400

    raw_text = data.get("message", "")
    if not isinstance(raw_text, str):
        return jsonify({
            "reply": "Message must be text.",
            "error": "invalid_request"
        }), 400

    text = raw_text.strip()
    settings = Doshie_settings.load_settings()
    profile = resolve_profile(data.get("profile", "Hermes"))

    if profile is None:
        return jsonify({
            "reply": "Choose a valid family profile first.",
            "error": "invalid_profile"
        }), 400

    attachment_ids = data.get("attachments", [])
    if not isinstance(attachment_ids, list) or len(attachment_ids) > 5:
        return jsonify({
            "reply": "Choose up to five valid attachments.",
            "error": "invalid_attachments"
        }), 400
    try:
        attachment_context, attachment_items = (
            Doshie_chat_attachments.prompt_context(
                profile, attachment_ids
            )
        )
        image_payloads = Doshie_chat_attachments.image_payloads(
            profile, attachment_ids
        )
    except Doshie_chat_attachments.AttachmentError:
        return jsonify({
            "reply": "One of those attachments is unavailable.",
            "error": "invalid_attachment"
        }), 400

    space = normalize_chat_space(data.get("space", "main"))
    chat_mode = normalize_chat_mode(data.get("chat_mode", "general"))
    brain_mode = normalize_brain_mode(data.get("brain_mode", "auto"), profile)
    incognito = bool(data.get("incognito", False))
    ephemeral_history = []
    if incognito:
        raw_ephemeral = data.get("ephemeral_history", [])
        if not isinstance(raw_ephemeral, list):
            return jsonify({
                "reply": "Incognito history must be a message list.",
                "error": "invalid_incognito_history"
            }), 400
        for item in raw_ephemeral[-8:]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip().casefold()
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                ephemeral_history.append({
                    "role": role,
                    "content": content[:4000],
                })
    if space is None:
        return jsonify({
            "reply": "Choose a valid Doshie room.",
            "error": "invalid_space"
        }), 400

    if not text and not attachment_items:
        return jsonify({"reply": "Say something or attach a file first."})

    if len(text) > 8000:
        return jsonify({
            "reply": "That message is too long. Keep it under 8,000 characters.",
            "error": "message_too_long"
        }), 413

    if text.startswith("/note "):
        return jsonify({
            "reply": Doshie_memory.add_note(text[len("/note "):])
        })

    if text == "/notes":
        rows = Doshie_memory.get_notes()

        if not rows:
            reply = "No saved notes."
        else:
            reply = " | ".join(
                f"{note_id}: {note}"
                for note_id, note, *_ in rows
            )

        return jsonify({"reply": reply})

    if text.startswith("/task "):
        return jsonify({
            "reply": Doshie_memory.add_task(text[len("/task "):])
        })

    if text == "/tasks":
        rows = Doshie_memory.get_tasks()

        if not rows:
            reply = "No tasks."
        else:
            reply = " | ".join(
                (
                    f"{task_id}: {'✅' if done else '⬜'} {task} "
                    f"[{priority or 'Normal'}"
                    + (f", due {due_date}" if due_date else "")
                    + "]"
                )
                for (
                    task_id,
                    task,
                    done,
                    priority,
                    due_date,
                    _tag,
                    _assigned_to,
                ) in rows
            )

        return jsonify({"reply": reply})

    if text.startswith("/done "):
        return jsonify({
            "reply": Doshie_memory.complete_task(text[len("/done "):])
        })

    if text.startswith("/remember-shared "):
        reply = Doshie_memory.add_memory(
            text[len("/remember-shared "):],
            profile=profile,
            scope="shared"
        )
        reset_chat_history(profile, space)
        return jsonify({"reply": reply, "memory": "shared"})

    if text.startswith("/remember "):
        reply = Doshie_memory.add_memory(
            text[len("/remember "):],
            profile=profile
        )
        reset_chat_history(profile, space)
        return jsonify({"reply": reply, "memory": "saved"})

    if text == "/memories":
        memories = Doshie_memory.get_memories(profile=profile)

        if not memories:
            reply = "No saved memories."
        else:
            reply = "\n".join(
                f"#{row[0]} [{row[2]} | {row[3]}] {row[1]}"
                for row in memories
            )

        return jsonify({"reply": reply})

    if text.startswith("/memories "):
        memory_filter = text[len("/memories "):].strip()

        if memory_filter.lower() == "inactive":
            memories = [
                row for row in Doshie_memory.get_memories(
                    include_inactive=True,
                    profile=profile
                )
                if row[6] == 0
            ]

        elif memory_filter.lower() in {"high", "normal", "low"}:
            memories = Doshie_memory.get_memories(
                importance=memory_filter.title(),
                profile=profile
            )

        else:
            memories = Doshie_memory.get_memories(
                category=memory_filter.title(),
                profile=profile
            )

        reply = Doshie_memory.format_memory_rows(memories)
        return jsonify({"reply": reply})

    if text.startswith("/find-memory "):
        query = text[len("/find-memory "):].strip()

        if not query:
            return jsonify({
                "reply": "Usage: /find-memory <search>"
            })

        memories = Doshie_memory.smart_recall(
            query,
            limit=10,
            profile=profile
        )

        return jsonify({
            "reply": Doshie_memory.format_memory_rows(memories)
        })

    if text.startswith("/forget "):
        memory_id = text[len("/forget "):].strip()

        try:
            memory_id = int(memory_id)
        except ValueError:
            return jsonify({
                "reply": "Usage: /forget <id>"
            })

        conn = Doshie_memory.connect_db()

        cur = conn.execute(
            """
            UPDATE memories
            SET active = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND active = 1
              AND LOWER(profile) = LOWER(?)
            """,
            (memory_id, profile)
        )

        conn.commit()
        conn.close()

        if cur.rowcount:
            reply = f"Memory #{memory_id} deactivated. 🧠"
        else:
            reply = "Memory not found or already inactive."

        reset_chat_history(profile, space)
        return jsonify({"reply": reply})

    if text.startswith("/restore-memory "):
        memory_id = text[len("/restore-memory "):].strip()

        reply = Doshie_memory.restore_memory(
            memory_id,
            profile=profile
        )

        reset_chat_history(profile, space)
        return jsonify({"reply": reply})

    if text == "/battery":
        return jsonify({
            "reply": Doshie_memory.get_battery_status()
        })

    if text == "/status":
        return jsonify({
            "reply": Doshie_memory.get_device_status()
        })

    if text == "/weather":
        return jsonify({
            "reply": Doshie_memory.get_weather(
                settings.get("default_weather_location", "El Paso")
            )
        })

    model_text = text
    if attachment_context:
        model_text = (
            (text + "\n\n") if text else ""
        ) + "USER ATTACHMENTS:\n" + attachment_context

    handled, tool_reply = route_tool(
        text,
        settings.get("default_weather_location", "El Paso"),
        profile=profile
    )

    if handled:
        return jsonify({
            "reply": tool_reply
        })

    if not incognito and settings.get("auto_memory", True):
        saved = Doshie_memory.auto_remember(text, profile=profile)
    else:
        saved = False

    if saved == "updated":
        reset_chat_history(profile, space)

    if incognito:
        current_history = ephemeral_history
        request_generation = None
    else:
        current_history, request_generation = conversation_snapshot(
            profile,
            space,
        )

    try:
        reply = Doshie_memory.ask_Doshie(
            current_history,
            model_text,
            raise_on_error=True,
            profile=profile,
            conversation_profile=(
                f"{profile} Incognito"
                if incognito
                else conversation_storage_profile(profile, space)
            ),
            system_context=combined_chat_context(space, chat_mode),
            brain_mode=brain_mode,
            memory_scope="none" if incognito else "all",
            images=image_payloads,
        )
    except Exception:
        app.logger.exception("Doshie could not complete a chat request")
        return jsonify({
            "reply": "Doshie's local AI could not answer right now.",
            "error": "chat_unavailable"
        }), 503

    if not incognito and not append_conversation(
        profile,
        text or "Shared an attachment.",
        reply,
        request_generation,
        space=space,
    ):
        return jsonify({"reply": "", "discarded": True}), 409

    return jsonify({
        "reply": reply,
        "memory": saved,
        "profile": profile,
        "space": space,
        "attachments": attachment_items,
        "incognito": incognito,
    })


def stop_owned_model(process):
    if process is None or process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=10)
    except Exception:
        process.kill()
        process.wait(timeout=5)

    try:
        with open(Doshie_memory.MODEL_PID_PATH, encoding="utf-8") as handle:
            recorded_pid = int(handle.read().strip())
        if recorded_pid == process.pid:
            os.unlink(Doshie_memory.MODEL_PID_PATH)
    except (FileNotFoundError, OSError, TypeError, ValueError):
        pass


if __name__ == "__main__":
    Doshie_memory.connect_db().close()
    owned_model = None

    def request_shutdown(_signal_number, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    try:
        owned_model = Doshie_memory.start_server()
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=False
        )
    finally:
        stop_owned_model(owned_model)
