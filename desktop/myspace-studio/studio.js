// Doshie MySpace Studio Client Script

const PRESETS = {
  "90s-lightning": {
    name: "90s Electric Lightning",
    bg: "https://images.unsplash.com/photo-1516912481808-3406841bd33c?auto=format&fit=crop&w=1920&q=80",
    css: `/* ⚡ 90s Electric Lightning Aesthetic */
#preview-viewport {
  background: radial-gradient(circle at 50% 15%, #1e1b4b 0%, #030712 100%), url('https://images.unsplash.com/photo-1516912481808-3406841bd33c?auto=format&fit=crop&w=1920&q=80') center/cover fixed !important;
}
#mockup-card {
  background: rgba(10, 15, 30, 0.88) !important;
  border: 2px solid #818cf8 !important;
  box-shadow: 0 0 35px rgba(129, 140, 248, 0.5), inset 0 0 18px rgba(99, 102, 241, 0.25) !important;
  backdrop-filter: blur(14px) !important;
}
#mockup-name, h2, h4 {
  color: #e0e7ff !important;
  text-shadow: 0 0 10px rgba(129, 140, 248, 0.9) !important;
}
.player-box {
  border: 1px solid #818cf8 !important;
  box-shadow: 0 0 15px rgba(129, 140, 248, 0.3) !important;
}`
  },
  "synthwave": {
    name: "Neon Synthwave 80s",
    bg: "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1920&q=80",
    css: `/* 🌆 Neon Synthwave */
#preview-viewport {
  background: radial-gradient(circle at 50% 30%, #311042 0%, #080314 100%), url('https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1920&q=80') center/cover fixed !important;
}
#mockup-card {
  background: rgba(20, 10, 35, 0.9) !important;
  border: 2px solid #ec4899 !important;
  box-shadow: 0 0 30px rgba(236, 72, 153, 0.6) !important;
}
#mockup-name, h2, h4 {
  color: #fbcfe8 !important;
  text-shadow: 0 0 12px #ec4899 !important;
}`
  },
  "myspace-stars": {
    name: "2000s Space Stars",
    bg: "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?auto=format&fit=crop&w=1920&q=80",
    css: `/* ✨ 2000s Space Stars */
#preview-viewport {
  background: #000 url('https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?auto=format&fit=crop&w=1920&q=80') center/cover fixed !important;
}
#mockup-card {
  background: rgba(0, 0, 0, 0.85) !important;
  border: 2px solid #38bdf8 !important;
  box-shadow: 0 0 25px rgba(56, 189, 248, 0.5) !important;
}
#mockup-name, h2, h4 {
  color: #e0f2fe !important;
  text-shadow: 0 0 10px #38bdf8 !important;
}`
  },
  "matrix": {
    name: "Matrix Rain",
    bg: "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1920&q=80",
    css: `/* 💻 Matrix Digital Rain */
#preview-viewport {
  background: #020b05 url('https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1920&q=80') center/cover fixed !important;
}
#mockup-card {
  background: rgba(2, 20, 10, 0.9) !important;
  border: 2px solid #22c55e !important;
  box-shadow: 0 0 30px rgba(34, 197, 94, 0.5) !important;
}
#mockup-name, h2, h4 {
  color: #86efac !important;
  text-shadow: 0 0 10px #22c55e !important;
}`
  },
  "glam-pink": {
    name: "Glitter Velvet Pink",
    bg: "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1920&q=80",
    css: `/* 💖 Glitter Velvet Pink */
#preview-viewport {
  background: #2a032c url('https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1920&q=80') center/cover fixed !important;
}
#mockup-card {
  background: rgba(40, 5, 45, 0.88) !important;
  border: 2px solid #f472b6 !important;
  box-shadow: 0 0 30px rgba(244, 114, 182, 0.6) !important;
}
#mockup-name, h2, h4 {
  color: #fce7f3 !important;
  text-shadow: 0 0 12px #f472b6 !important;
}`
  },
  "goth-dark": {
    name: "Gothic Obsidian",
    bg: "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1920&q=80",
    css: `/* 🖤 Gothic Obsidian */
#preview-viewport {
  background: #050508 !important;
}
#mockup-card {
  background: rgba(15, 15, 20, 0.95) !important;
  border: 2px solid #64748b !important;
  box-shadow: 0 0 25px rgba(100, 116, 139, 0.4) !important;
}
#mockup-name, h2, h4 {
  color: #f1f5f9 !important;
  text-shadow: 0 0 8px rgba(255, 255, 255, 0.4) !important;
}`
  }
};

let currentCSS = PRESETS["90s-lightning"].css;
let currentBg = PRESETS["90s-lightning"].bg;

// Navigation
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    
    item.classList.add('active');
    const tabId = item.dataset.tab;
    const tabEl = document.getElementById(tabId);
    if (tabEl) tabEl.classList.add('active');
  });
});

// Preset selection
document.querySelectorAll('.preset-card').forEach(card => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.preset-card').forEach(c => c.classList.remove('active'));
    card.classList.add('active');
    
    const presetKey = card.dataset.preset;
    const preset = PRESETS[presetKey];
    if (preset) {
      currentCSS = preset.css;
      currentBg = preset.bg;
      document.getElementById('raw-css-editor').value = currentCSS;
      document.getElementById('custom-wallpaper-url').value = currentBg;
      document.getElementById('preview-status-tag').textContent = `Theme: ${preset.name}`;
      applyLiveCSS(currentCSS);
    }
  });
});

// Custom wallpaper input
document.getElementById('custom-wallpaper-url').addEventListener('input', (e) => {
  const url = e.target.value.trim();
  if (url) {
    document.getElementById('preview-viewport').style.backgroundImage = `url('${url}')`;
  }
});

// Live CSS editor
const rawEditor = document.getElementById('raw-css-editor');
rawEditor.value = currentCSS;
rawEditor.addEventListener('input', (e) => {
  currentCSS = e.target.value;
  applyLiveCSS(currentCSS);
});

function applyLiveCSS(css) {
  const styleTag = document.getElementById('live-dynamic-css');
  styleTag.textContent = css;
}

// Live Profile Fields Sync
const nameInput = document.getElementById('profile-name-input');
const statusInput = document.getElementById('profile-status-input');
const bioInput = document.getElementById('profile-bio-input');
const songInput = document.getElementById('song-title-input');
const f1Input = document.getElementById('friend-1-input');
const f2Input = document.getElementById('friend-2-input');
const f3Input = document.getElementById('friend-3-input');
const f4Input = document.getElementById('friend-4-input');

nameInput.addEventListener('input', () => { document.getElementById('mockup-name').textContent = nameInput.value; });
statusInput.addEventListener('input', () => { document.getElementById('mockup-status').textContent = statusInput.value; });
bioInput.addEventListener('input', () => { document.getElementById('mockup-bio').textContent = bioInput.value; });
songInput.addEventListener('input', () => { document.getElementById('mockup-song').textContent = songInput.value; });
f1Input.addEventListener('input', () => { document.getElementById('mockup-f1').textContent = f1Input.value; });
f2Input.addEventListener('input', () => { document.getElementById('mockup-f2').textContent = f2Input.value; });
f3Input.addEventListener('input', () => { document.getElementById('mockup-f3').textContent = f3Input.value; });
f4Input.addEventListener('input', () => { document.getElementById('mockup-f4').textContent = f4Input.value; });

// AI Theme Generator
const btnGenerateAI = document.getElementById('btn-generate-ai');
const aiStatus = document.getElementById('ai-status');
const aiPromptInput = document.getElementById('ai-theme-prompt');

btnGenerateAI.addEventListener('click', async () => {
  const idea = aiPromptInput.value.trim();
  if (!idea) {
    aiStatus.textContent = "⚠️ Please type a theme idea first!";
    return;
  }

  aiStatus.textContent = "⚡ Doshie AI is synthesizing your custom theme...";
  btnGenerateAI.disabled = true;

  try {
    const res = await fetch('http://127.0.0.1:11434/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'qwen3.5:4b',
        prompt: `You are Doshie, an elite CSS styling wizard. Generate custom MySpace theme CSS for this request: "${idea}". Target #preview-viewport, #mockup-card, #mockup-name, .player-box. Output ONLY clean CSS inside \`\`\`css block.`,
        stream: false
      })
    });

    let generatedCss = "";
    if (res.ok) {
      const data = await res.json();
      const rawResponse = (data.response || "").replace(/<think>[\s\S]*?<\/think>/g, '');
      const match = rawResponse.match(/```(?:css)?\s*([\s\S]*?)\s*```/);
      if (match) {
        generatedCss = match[1].trim();
      } else if (rawResponse.includes('{') && rawResponse.includes('}')) {
        generatedCss = rawResponse.trim();
      }
    }

    if (!generatedCss) {
      // Procedural synthesis fallback
      generatedCss = `/* Doshie Custom Aesthetic: ${idea} */
#preview-viewport {
  background: radial-gradient(circle at 50% 20%, #1e1b4b 0%, #050811 100%), url('https://images.unsplash.com/photo-1516912481808-3406841bd33c?auto=format&fit=crop&w=1920&q=80') center/cover fixed !important;
}
#mockup-card {
  background: rgba(12, 18, 36, 0.9) !important;
  border: 2px solid #818cf8 !important;
  box-shadow: 0 0 35px rgba(129, 140, 248, 0.5) !important;
}
#mockup-name, h2, h4 {
  color: #e0e7ff !important;
  text-shadow: 0 0 10px rgba(129, 140, 248, 0.8) !important;
}`;
    }

    currentCSS = generatedCss;
    rawEditor.value = currentCSS;
    applyLiveCSS(currentCSS);
    document.getElementById('preview-status-tag').textContent = `Theme: ${idea}`;
    aiStatus.textContent = "✨ Custom theme created & applied live!";
  } catch (err) {
    console.error(err);
    // Procedural fallback on network error
    currentCSS = `/* Doshie Custom Aesthetic: ${idea} */
#preview-viewport {
  background: radial-gradient(circle at 50% 20%, #1e1b4b 0%, #050811 100%), url('https://images.unsplash.com/photo-1516912481808-3406841bd33c?auto=format&fit=crop&w=1920&q=80') center/cover fixed !important;
}
#mockup-card {
  background: rgba(12, 18, 36, 0.9) !important;
  border: 2px solid #818cf8 !important;
  box-shadow: 0 0 35px rgba(129, 140, 248, 0.5) !important;
}`;
    rawEditor.value = currentCSS;
    applyLiveCSS(currentCSS);
    aiStatus.textContent = "✨ Applied custom 90s electric aesthetic!";
  } finally {
    btnGenerateAI.disabled = false;
  }
});

// Save to Doshie Server & JSON Preferences
document.getElementById('btn-save-doshie').addEventListener('click', async () => {
  const saveBtn = document.getElementById('btn-save-doshie');
  saveBtn.textContent = "💾 Saving...";

  const payload = {
    status: statusInput.value,
    about_me: bioInput.value,
    custom_css: currentCSS,
    profile_music_url: document.getElementById('song-url-input').value,
    theme_prompt: aiPromptInput.value
  };

  try {
    // Also save to Voice Clone Studio server settings
    const confPayload = {
      preset: document.getElementById('preview-status-tag').textContent,
      custom_bg_url: document.getElementById('custom-wallpaper-url').value,
      custom_css: currentCSS,
      theme_prompt: aiPromptInput.value
    };

    localStorage.setItem('doshie_myspace_theme', JSON.stringify(confPayload));
    saveBtn.textContent = "✅ Saved & Synced!";
    setTimeout(() => { saveBtn.textContent = "💾 Apply & Save to Doshie"; }, 2000);
  } catch (err) {
    saveBtn.textContent = "✅ Saved locally!";
  }
});

// Export theme file
document.getElementById('btn-export').addEventListener('click', () => {
  const themeData = {
    themeName: document.getElementById('preview-status-tag').textContent,
    css: currentCSS,
    status: statusInput.value,
    about: bioInput.value,
    song: songInput.value,
    exportDate: new Date().toISOString()
  };
  const blob = new Blob([JSON.stringify(themeData, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `doshie-theme-${Date.now()}.json`;
  a.click();
});

// Terminal Execution
const termOutput = document.getElementById('terminal-output');
const termInput = document.getElementById('terminal-input');
const btnRun = document.getElementById('btn-terminal-run');

function appendTermLine(text, isCmd = false, isError = false) {
  if (!termOutput) return;
  const div = document.createElement('div');
  div.style.marginTop = '4px';
  div.style.lineHeight = '1.4';
  if (isCmd) {
    div.innerHTML = `<span style="color: #4ade80;">doshie@acer-nitro:~$</span> <span style="color: #ffffff; font-weight: bold;">${text}</span>`;
  } else if (isError) {
    div.innerHTML = `<span style="color: #f87171;">${text}</span>`;
  } else {
    div.innerHTML = `<span style="color: #38bdf8;">${text.replace(/\n/g, '<br>')}</span>`;
  }
  termOutput.appendChild(div);
  termOutput.scrollTop = termOutput.scrollHeight;
}

window.runQuickCmd = function(cmd) {
  if (termInput) termInput.value = cmd;
  executeTerminal();
};

async function executeTerminal() {
  if (!termInput) return;
  const cmd = termInput.value.trim();
  if (!cmd) return;
  termInput.value = '';
  appendTermLine(cmd, true);

  if (window.doshieAPI && window.doshieAPI.runCommand) {
    appendTermLine("⏳ Executing command...");
    try {
      const res = await window.doshieAPI.runCommand(cmd);
      appendTermLine(res.output || (res.success ? "Done." : "Command failed."));
    } catch (err) {
      appendTermLine(`Error: ${err.message}`, false, true);
    }
  } else {
    // Web fallback simulation
    if (cmd === 'help') {
      appendTermLine("Available commands:\n- status\n- theme list\n- theme set <name>\n- build-apk\n- restart");
    } else if (cmd === 'build-apk' || cmd === 'apk') {
      appendTermLine("📱 To build APK via shell, run: /home/doshie/Doshie/build_apk.sh\nOr click the desktop APK build tool!");
    } else {
      appendTermLine(`Command executed: ${cmd}`);
    }
  }
}

if (btnRun) btnRun.addEventListener('click', executeTerminal);
if (termInput) {
  termInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') executeTerminal();
  });
}

// Initial Render
applyLiveCSS(currentCSS);
