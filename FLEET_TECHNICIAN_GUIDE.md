# 🛠️ Doshie Unified Remote Technician & RDP Operations Guide

This master guide combines **Doshie's Autonomous AI Fleet Technician** (code modification, diagnostics, and command execution across all computers) with **Doshie Visual Remote Desktop (RDP & RustDesk)** into one unified remote control system.

---

## 1. The Two Pillars of Doshie Remote Operations

```
┌────────────────────────────────────────────────────────────────────────┐
│                        HERMES (Anywhere on Phone/PC)                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌───────────────────────────────────┐   ┌───────────────────────────────────┐
│     PILLAR 1: VISUAL DESKTOP      │   │    PILLAR 2: AI FLEET TECHNICIAN  │
│          (RDP & RustDesk)         │   │        (Doshie Remote Engine)     │
├───────────────────────────────────┤   ├───────────────────────────────────┤
│ • See the full graphical desktop  │   │ • Doshie reads and edits code     │
│ • Mouse, touch, & window control  │   │ • Executes remote bash/PowerShell │
│ • Connect via Doshie-RDP.apk      │   │ • Works across ALL fleet machines │
│ • 100.109.79.35:3389              │   │ • No GUI needed — works in bg     │
└───────────────────────────────────┘   └───────────────────────────────────┘
```

---

## 2. Pillar 1: Visual Remote Desktop (RDP & RustDesk)

Use this when you want to **see and interact with the full graphical desktop** (launching GUI software, Blender, Steam, Cyberpunk, browser windows) from your phone or another computer.

### Connection Endpoints
* **Tailscale RDP Address**: `100.109.79.35:3389` *(Works from anywhere in the world)*
* **Home LAN RDP Address**: `192.168.1.167:3389` *(Fastest when on home Wi-Fi)*
* **Default Username**: `doshie`
* **RustDesk Direct ID**: `256594765` *(Zero-config peer-to-peer visual remote)*

### How to Connect From Your Devices

#### A. From Your Phone or Tablet (Android - Z Fold8 / Tab A9+)
1. Install **`Doshie-RDP.apk`**:
   * Pinned directly on your Acer Nitro desktop: `/home/doshie/Desktop/Doshie-RDP.apk`
   * Or download directly in your mobile browser at:  
     `http://acer-nitro.tail50b4c5.ts.net:8080/download/rdp`
2. Open the app, tap **Add PC**, and enter:
   * **PC Name**: `100.109.79.35:3389`
   * **User Name**: `doshie`
3. Tap Connect. You will see the entire Linux workstation screen in high definition on your phone.

#### B. From Your Windows PCs (`DuranCyberPwrPC`, `AeRonA1221PC`, laptops)
1. Download the pre-configured `.rdp` file:
   `http://acer-nitro.tail50b4c5.ts.net:8080/download/doshie.rdp`
2. Double-click the file to launch Windows Remote Desktop Connection directly.

#### C. Web Control Panel RDP Management
You can restart RDP or change credentials anytime in the Doshie Web UI:
* Go to: `http://acer-nitro.tail50b4c5.ts.net:8080/su#tab-rdp`
* Options: *Restart RDP*, *Enable RDP*, *Set Credentials*.

---

## 3. Pillar 2: Autonomous AI Fleet Technician (Code & Execution)

Use this when you want Doshie to **act as your systems engineer** across all computers in your network—reading files, patching bugs, deploying scripts, and running tests without having to open an RDP session.

### Your Fleet Computers
* **`acer-nitro`** (Linux Hub • `100.109.79.35`)
* **`DuranCyberPwrPC`** (Windows Desktop • `100.104.3.15`)
* **`vultr`** (Linux Cloud Server • `100.107.47.127`)
* **`hermes-duran-TECRA-A60-M`** (Linux Laptop • `100.113.75.55`)

### What Doshie Can Do Autonomously:
1. **Remote Code Reading**: Reads source code with line numbers from any machine (`remote_view_file`).
2. **Remote Surgical Code Editing**: Replaces and patches code chunks directly on the remote machine (`remote_replace_file_content`).
3. **Remote File Deployment**: Writes new scripts or full code files (`remote_write_file`).
4. **Remote Command Execution**: Runs Linux Bash or Windows PowerShell commands (`remote_run_command`).

### Example Technician Prompts in Doshie Chat:
* *"Doshie, what computers are currently online in my fleet?"*
* *"Inspect the API service on my Vultr server. Read `server.py` and tell me what port it's bound to."*
* *"In `config.json` on DuranCyberPwrPC, update the database host IP to `100.109.79.35`."*
* *"Deploy a backup script to `/home/user/backup.sh` on vultr and run it."*
* *"Restart the systemd service on vultr and verify the health."*

---

## 4. Enabling Remote Access on Your Fleet Machines

### On Linux Machines (`vultr`, laptops):
Run this single command on the machine:
```bash
sudo tailscale up --ssh
```
*(Or add Acer Nitro's public key from `~/.ssh/id_ed25519.pub` to `~/.ssh/authorized_keys`).*

### On Windows Machines (`DuranCyberPwrPC`):
**Option 1 (PowerShell Node Agent)**:
Run [`doshie_node.ps1`](file:///home/doshie/Doshie/doshie_node.ps1) in PowerShell. It listens on port 5055 for authorized commands.

**Option 2 (Windows OpenSSH Server)**:
Open PowerShell as Administrator and run:
```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
```

---

## 5. Summary: When to Use Which

| Task | Best Tool | Why |
| :--- | :--- | :--- |
| **Want to see screen, open GUI apps, check Blender/Steam** | **Visual RDP (`Doshie-RDP.apk`)** | Full graphical touch/mouse desktop stream. |
| **Fix a bug in a remote script** | **Doshie Chat (`remote_replace_file_content`)** | Done in 5 seconds via voice/text prompt. |
| **Check server health or run bash commands** | **Doshie Chat (`remote_run_command`)** | Instant output without opening a desktop stream. |
| **Deploy a new program or tool across PCs** | **Doshie Chat (`remote_write_file`)** | Doshie writes and verifies the file automatically. |
