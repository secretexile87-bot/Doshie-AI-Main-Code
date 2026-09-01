(() => {
    "use strict";

    const panels = Array.from(
        document.querySelectorAll('.app > [id$="Panel"]')
    );
    let deferredInstallPrompt = null;

    function setInstallVisible(visible) {
        document.querySelectorAll("[data-install-app]").forEach(button => {
            button.hidden = !visible;
        });
    }

    function setActiveView(view) {
        document.querySelectorAll("[data-app-view]").forEach(button => {
            button.classList.toggle(
                "active",
                button.dataset.appView === view
            );
        });
    }

    function syncPanelState() {
        const panelOpen = panels.some(panel => {
            return window.getComputedStyle(panel).display !== "none";
        });
        document.body.classList.toggle("app-panel-open", panelOpen);
        if (!panelOpen) setActiveView("chat");
    }
    window.showChatHome = function() {
        panels.forEach(panel => {
            panel.style.display = "none";
        });
        closeSidebar();
        syncPanelState();
        setActiveView("chat");
        if (typeof window.syncRoomHeader === "function") {
            window.syncRoomHeader();
        }
        const chatInput = document.getElementById("input");
        if (chatInput) chatInput.focus({ preventScroll: true });
    };

    window.openAppView = function(view) {
        if (view === "chat") {
            window.showChatHome();
            return;
        }

        panels.forEach(panel => {
            panel.style.display = "none";
        });
        closeSidebar();

        const actions = {
            family: () => window.openPeerChat(),
            organizer: () => openOrganizer("all")
        };
        if (actions[view]) actions[view]();
        setActiveView(view);
        if (typeof window.setSideView === "function") {
            window.setSideView(view);
        }
        window.setTimeout(syncPanelState, 0);
    };
    panels.forEach(panel => {
        new MutationObserver(syncPanelState).observe(panel, {
            attributes: true,
            attributeFilter: ["style", "class"]
        });
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") window.showChatHome();
    });

    window.addEventListener("beforeinstallprompt", event => {
        event.preventDefault();
        deferredInstallPrompt = event;
        setInstallVisible(true);
    });

    window.installDoshieApp = async function() {
        if (deferredInstallPrompt) {
            deferredInstallPrompt.prompt();
            await deferredInstallPrompt.userChoice;
            deferredInstallPrompt = null;
            setInstallVisible(false);
            return;
        }
        const appleMobile = /iPhone|iPad|iPod/i.test(navigator.userAgent);
        window.alert(
            appleMobile
                ? "To install Doshie: tap Share, then Add to Home Screen."
                : "To install Doshie: open your browser menu and choose Install app or Add to Home screen."
        );
    };

    window.addEventListener("appinstalled", () => {
        deferredInstallPrompt = null;
        setInstallVisible(false);
    });
    const standalone =
        window.matchMedia("(display-mode: standalone)").matches ||
        window.navigator.standalone === true;

    document.body.classList.toggle("standalone-app", standalone);
    setInstallVisible(!standalone);
    setActiveView("chat");
    syncPanelState();

    if ("serviceWorker" in navigator) {
        const hadControllerAtLoad = Boolean(navigator.serviceWorker.controller);
        let reloadingForUpdate = false;

        navigator.serviceWorker.addEventListener("controllerchange", () => {
            if (!hadControllerAtLoad || reloadingForUpdate) return;
            reloadingForUpdate = true;
            window.location.reload();
        });

        window.addEventListener("load", async () => {
            try {
                const registration = await navigator.serviceWorker.register(
                    "/service-worker.js",
                    { scope: "/" }
                );
                await registration.update();
            } catch (error) {
                console.log("Doshie app install support is unavailable.", error);
            }
        });
    }

    const displayPreferenceKey = "Doshie-display-mode";

    function applyPhonePreview(enabled) {
        document.body.classList.toggle("phone-preview", enabled);
        const button = document.getElementById("phonePreviewButton");
        if (button) {
            button.classList.toggle("active", enabled);
            button.setAttribute("aria-pressed", String(enabled));
        }
    }

    window.togglePhonePreview = function() {
        const enabled = !document.body.classList.contains("phone-preview");
        applyPhonePreview(enabled);
    };

    window.toggleDoshieFullscreen = async function() {
        try {
            if (!document.fullscreenElement) {
                await document.documentElement.requestFullscreen();
            } else {
                await document.exitFullscreen();
            }
        } catch (error) {
            console.log("Fullscreen is unavailable.", error);
        }
    };

    document.addEventListener("fullscreenchange", () => {
        const button = document.getElementById("fullscreenButton");
        if (button) {
            button.classList.toggle(
                "active",
                Boolean(document.fullscreenElement)
            );
        }
    });

    localStorage.removeItem(displayPreferenceKey);
    applyPhonePreview(false);

    const peerState = {
        panel: null,
        profile: "",
        tab: "chats",
        conversations: [],
        people: [],
        conversationId: "",
        conversationTitle: "",
        afterId: 0,
        heartbeat: null,
        inboxPoll: null,
        poll: null,
        typingTimer: null,
        typingActive: false,
        unreadCount: 0
    };

    function peerProfile() {
        const selector = document.getElementById("activeProfile");
        return selector ? selector.value : "Hermes";
    }

    function peerEscape(value) {
        return String(value ?? "").replace(/[&<>"']/g, character => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;",
            '"': "&quot;", "'": "&#039;"
        }[character]));
    }

    async function peerRequest(url, options = {}) {
        const response = await fetch(url, options);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || "Messaging is unavailable.");
        }
        return data;
    }

    function ensurePeerPanel() {
        if (peerState.panel) return peerState.panel;
        const panel = document.createElement("section");
        panel.id = "peerChatPanel";
        panel.className = "peer-chat-panel";
        panel.style.display = "none";
        panel.innerHTML = `
            <header class="peer-chat-header">
                <div>
                    <small>PRIVATE MESSAGING</small>
                    <h2>💬 Peer Chat</h2>
                    <p>Message family members through Doshie.</p>
                </div>
                <div class="peer-header-actions">
                    <span id="peerNotificationBadge" class="peer-header-badge" hidden>0</span>
                    <button type="button" class="tool" id="peerNewGroup">＋ Group</button>
                    <button type="button" class="panel-close" id="peerClose">✕</button>
                </div>
            </header>
            <div class="peer-chat-layout">
                <aside class="peer-inbox">
                    <div class="peer-tabs">
                        <button type="button" data-peer-tab="chats" class="active">Chats</button>
                        <button type="button" data-peer-tab="people">People</button>
                    </div>
                    <div id="peerList" class="peer-list"></div>
                </aside>
                <section class="peer-thread">
                    <header id="peerThreadHeader" class="peer-thread-header">
                        <strong>Select a conversation</strong>
                        <small>Choose a person to start messaging.</small>
                    </header>
                    <div id="peerMessages" class="peer-messages">
                        <div class="peer-empty">Your private conversations will appear here.</div>
                    </div>
                    <form id="peerComposer" class="peer-composer">
                        <input id="peerInput" maxlength="8000" autocomplete="off"
                               placeholder="Message a family member…" disabled>
                        <button class="send" type="submit" disabled>Send</button>
                    </form>
                </section>
            </div>
        `;
        document.querySelector(".app").appendChild(panel);
        panels.push(panel);
        peerState.panel = panel;

        panel.querySelector("#peerClose").addEventListener("click", () => {
            window.showChatHome();
        });
        panel.querySelectorAll("[data-peer-tab]").forEach(button => {
            button.addEventListener("click", () => {
                peerState.tab = button.dataset.peerTab;
                panel.querySelectorAll("[data-peer-tab]").forEach(item => {
                    item.classList.toggle("active", item === button);
                });
                renderPeerList();
            });
        });
        panel.querySelector("#peerList").addEventListener("click", event => {
            const conversation = event.target.closest("[data-peer-conversation]");
            if (conversation) {
                selectPeerConversation(
                    conversation.dataset.peerConversation,
                    conversation.dataset.peerTitle || "Conversation"
                );
                return;
            }
            const person = event.target.closest("[data-peer-person]");
            if (person) createPeerDirect(person.dataset.peerPerson);
        });
        panel.querySelector("#peerNewGroup").addEventListener("click", createPeerGroup);
        panel.querySelector("#peerComposer").addEventListener("submit", sendPeerMessage);
        panel.querySelector("#peerInput").addEventListener("input", handlePeerInput);
        panel.querySelector("#peerInput").addEventListener("blur", () => {
            setPeerTyping(false).catch(() => {});
        });
        return panel;
    }

    function renderPeerList() {
        const list = peerState.panel && peerState.panel.querySelector("#peerList");
        if (!list) return;
        if (peerState.tab === "people") {
            const people = peerState.people.filter(item => !item.self);
            list.innerHTML = people.length ? people.map(item => `
                <button type="button" class="peer-list-row" data-peer-person="${peerEscape(item.name)}">
                    <span class="peer-avatar ${item.online ? "online" : ""}">${peerEscape(item.initials)}</span>
                    <span class="peer-list-copy"><strong>${peerEscape(item.name)}</strong>
                    <small>${item.online ? "Online" : "Offline"} · ${peerEscape(item.role)}</small></span>
                    <span class="peer-start">＋</span>
                </button>
            `).join("") : '<div class="peer-empty">No other family profiles are available yet.</div>';
            return;
        }
        list.innerHTML = peerState.conversations.length ? peerState.conversations.map(item => {
            const last = item.last_message ? item.last_message.body : "Start a conversation";
            return `
                <button type="button" class="peer-list-row ${item.id === peerState.conversationId ? "active" : ""}"
                        data-peer-conversation="${peerEscape(item.id)}"
                        data-peer-title="${peerEscape(item.title)}">
                    <span class="peer-avatar">${peerEscape((item.title || "D").slice(0, 2).toUpperCase())}</span>
                    <span class="peer-list-copy"><strong>${peerEscape(item.title)}</strong>
                    <small>${peerEscape(last.slice(0, 72))}</small></span>
                    ${item.unread_count ? `<b class="peer-unread">${item.unread_count}</b>` : ""}
                </button>
            `;
        }).join("") : '<div class="peer-empty">No chats yet. Open People and choose someone.</div>';
    }

    function renderPeerThreadHeader() {
        const header = peerState.panel && peerState.panel.querySelector("#peerThreadHeader");
        const input = peerState.panel && peerState.panel.querySelector("#peerInput");
        const send = peerState.panel && peerState.panel.querySelector(".peer-composer .send");
        if (!header) return;
        if (!peerState.conversationId) {
            header.innerHTML = `<strong>Select a conversation</strong><small>Choose a person to start messaging.</small><small id="peerTypingStatus" class="peer-typing-status" aria-live="polite"></small>`;
            if (input) input.disabled = true;
            if (send) send.disabled = true;
            return;
        }
        header.innerHTML = `<strong>${peerEscape(peerState.conversationTitle)}</strong>
            <small>Private Doshie conversation · messages sync automatically</small>
            <small id="peerTypingStatus" class="peer-typing-status" aria-live="polite"></small>`;
        if (input) input.disabled = false;
        if (send) send.disabled = false;
    }

    function renderPeerMessages(items) {
        const box = peerState.panel && peerState.panel.querySelector("#peerMessages");
        if (!box) return;
        if (!items.length) {
            box.innerHTML = '<div class="peer-empty">No messages yet. Say hello.</div>';
            return;
        }
        box.innerHTML = items.map(item => {
            const outgoing = item.sender_profile.toLowerCase() === peerState.profile.toLowerCase();
            const stamp = new Date(item.created_at).toLocaleTimeString([], {
                hour: "numeric", minute: "2-digit"
            });
            return `<article class="peer-bubble ${outgoing ? "outgoing" : "incoming"}">
                <p>${peerEscape(item.body).replace(/\\n/g, "<br>")}</p>
                <small>${peerEscape(outgoing ? "You · " + stamp : item.sender_profile + " · " + stamp)}</small>
            </article>`;
        }).join("");
        box.scrollTop = box.scrollHeight;
    }

    function updatePeerNotificationBadge(count) {
        const total = Math.max(0, Number(count) || 0);
        document.querySelectorAll(
            '[data-side-view="family"], [data-app-view="family"]'
        ).forEach(button => {
            let badge = button.querySelector(".peer-notification-badge");
            if (total && !badge) {
                badge = document.createElement("span");
                badge.className = "peer-notification-badge";
                button.appendChild(badge);
            }
            if (badge) {
                badge.textContent = total > 99 ? "99+" : String(total);
                badge.hidden = !total;
            }
        });
        const headerBadge = peerState.panel &&
            peerState.panel.querySelector("#peerNotificationBadge");
        if (headerBadge) {
            headerBadge.textContent = total > 99 ? "99+" : String(total);
            headerBadge.hidden = !total;
        }
    }

    function renderPeerTyping(users) {
        const status = peerState.panel &&
            peerState.panel.querySelector("#peerTypingStatus");
        if (!status) return;
        const names = Array.isArray(users) ? users : [];
        status.textContent = names.length
            ? (names.length === 1
                ? names[0] + " is typing…"
                : names.join(", ") + " are typing…")
            : "";
    }

    async function setPeerTyping(typing) {
        if (!peerState.conversationId || !peerState.profile) return;
        peerState.typingActive = Boolean(typing);
        await peerRequest("/messaging/typing", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                profile: peerState.profile,
                conversation_id: peerState.conversationId,
                typing: peerState.typingActive
            })
        });
    }

    function handlePeerInput() {
        const input = peerState.panel && peerState.panel.querySelector("#peerInput");
        if (!input) return;
        window.clearTimeout(peerState.typingTimer);
        if (!input.value.trim()) {
            setPeerTyping(false).catch(() => {});
            return;
        }
        setPeerTyping(true).catch(() => {});
        peerState.typingTimer = window.setTimeout(() => {
            setPeerTyping(false).catch(() => {});
        }, 1800);
    }

    async function loadPeerTyping() {
        if (!peerState.conversationId || !peerState.profile) return;
        const data = await peerRequest(
            "/messaging/conversations/" +
            encodeURIComponent(peerState.conversationId) +
            "/typing?profile=" + encodeURIComponent(peerState.profile)
        );
        renderPeerTyping(data.typing);
    }

    async function refreshPeerInbox() {
        if (!peerState.profile) return;
        const data = await peerRequest(
            "/messaging/conversations?profile=" +
            encodeURIComponent(peerState.profile)
        );
        peerState.conversations = Array.isArray(data.conversations)
            ? data.conversations : [];
        peerState.unreadCount = peerState.conversations.reduce(
            (total, item) => total + (Number(item.unread_count) || 0), 0
        );
        updatePeerNotificationBadge(peerState.unreadCount);
        renderPeerList();
    }

    async function loadPeerMessages(reset = false) {
        if (!peerState.conversationId) return;
        if (reset) peerState.afterId = 0;
        const query = "?profile=" + encodeURIComponent(peerState.profile) +
            "&after_id=" + encodeURIComponent(peerState.afterId);
        const data = await peerRequest(
            "/messaging/conversations/" + encodeURIComponent(peerState.conversationId) +
            "/messages" + query
        );
        const box = peerState.panel.querySelector("#peerMessages");
        if (reset) box.innerHTML = "";
        const old = peerState.messages || [];
        const incoming = Array.isArray(data.messages) ? data.messages : [];
        const merged = reset ? incoming : old.concat(incoming);
        peerState.messages = merged.filter((item, index, array) =>
            index === array.findIndex(candidate => candidate.id === item.id)
        );
        if (incoming.length) {
            peerState.afterId = incoming[incoming.length - 1].id;
            await peerRequest(
                "/messaging/conversations/" + encodeURIComponent(peerState.conversationId) + "/read",
                {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        profile: peerState.profile,
                        message_id: peerState.afterId
                    })
                }
            ).catch(() => {});
        }
        renderPeerMessages(peerState.messages);
    }

    async function loadPeerInbox() {
        peerState.profile = peerProfile();
        const [people, conversations] = await Promise.all([
            peerRequest("/messaging/people?profile=" + encodeURIComponent(peerState.profile)),
            peerRequest("/messaging/conversations?profile=" + encodeURIComponent(peerState.profile))
        ]);
        peerState.people = Array.isArray(people.people) ? people.people : [];
        peerState.conversations = Array.isArray(conversations.conversations)
            ? conversations.conversations : [];
        peerState.unreadCount = peerState.conversations.reduce(
            (total, item) => total + (Number(item.unread_count) || 0), 0
        );
        updatePeerNotificationBadge(peerState.unreadCount);
        renderPeerList();
        renderPeerThreadHeader();
        if (!peerState.conversationId && peerState.conversations.length) {
            const first = peerState.conversations[0];
            await selectPeerConversation(first.id, first.title);
        }
    }

    async function selectPeerConversation(id, title) {
        setPeerTyping(false).catch(() => {});
        window.clearTimeout(peerState.typingTimer);
        peerState.conversationId = id;
        peerState.conversationTitle = title;
        peerState.messages = [];
        peerState.afterId = 0;
        renderPeerList();
        renderPeerThreadHeader();
        try {
            await loadPeerMessages(true);
            if (peerState.poll) window.clearInterval(peerState.poll);
            peerState.poll = window.setInterval(() => {
                loadPeerMessages(false).catch(() => {});
                loadPeerTyping().catch(() => {});
            }, 2500);
            loadPeerTyping().catch(() => {});
        } catch (error) {
            const box = peerState.panel.querySelector("#peerMessages");
            box.innerHTML = `<div class="peer-empty">${peerEscape(error.message)}</div>`;
        }
    }

    async function createPeerDirect(name) {
        try {
            const data = await peerRequest("/messaging/conversations", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({profile: peerState.profile, members: [name], kind: "direct"})
            });
            peerState.conversations = data.conversations || [];
            peerState.tab = "chats";
            peerState.panel.querySelector("[data-peer-tab='chats']").click();
            const conversation = peerState.conversations.find(
                item => item.id === data.conversation_id
            );
            await selectPeerConversation(data.conversation_id, conversation?.title || name);
        } catch (error) {
            const box = peerState.panel.querySelector("#peerMessages");
            box.innerHTML = `<div class="peer-empty">${peerEscape(error.message)}</div>`;
        }
    }

    async function createPeerGroup() {
        const options = peerState.people.filter(item => !item.self).map(item => item.name);
        if (!options.length) return;
        const names = window.prompt("Enter family names separated by commas:\n" + options.join(", "));
        if (!names) return;
        const selected = names.split(",").map(item => item.trim()).filter(item =>
            options.some(option => option.toLowerCase() === item.toLowerCase())
        );
        if (!selected.length) return;
        const title = window.prompt("Name this group:", "Family group") || "Family group";
        try {
            const data = await peerRequest("/messaging/conversations", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    profile: peerState.profile, members: selected,
                    title, kind: "group"
                })
            });
            peerState.conversations = data.conversations || [];
            peerState.tab = "chats";
            peerState.panel.querySelector("[data-peer-tab='chats']").click();
            await selectPeerConversation(data.conversation_id, title);
        } catch (error) {
            window.alert(error.message);
        }
    }

    async function sendPeerMessage(event) {
        event.preventDefault();
        const input = peerState.panel.querySelector("#peerInput");
        const text = input.value.trim();
        if (!text || !peerState.conversationId) return;
        input.disabled = true;
        window.clearTimeout(peerState.typingTimer);
        setPeerTyping(false).catch(() => {});
        try {
            await peerRequest(
                "/messaging/conversations/" + encodeURIComponent(peerState.conversationId) + "/messages",
                {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({profile: peerState.profile, body: text})
                }
            );
            input.value = "";
            await loadPeerMessages(false);
            const data = await peerRequest(
                "/messaging/conversations?profile=" + encodeURIComponent(peerState.profile)
            );
            peerState.conversations = data.conversations || peerState.conversations;
            renderPeerList();
        } catch (error) {
            const box = peerState.panel.querySelector("#peerMessages");
            box.innerHTML = `<div class="peer-empty">${peerEscape(error.message)}</div>`;
        } finally {
            input.disabled = false;
            input.focus({preventScroll: true});
        }
    }

    window.openPeerChat = async function() {
        const panel = ensurePeerPanel();
        panels.forEach(item => {
            item.style.display = "none";
        });
        panel.style.display = "block";
        closeSidebar();
        setActiveView("family");
        if (typeof window.setSideView === "function") window.setSideView("family");
        renderPeerThreadHeader();
        try {
            await loadPeerInbox();
        } catch (error) {
            panel.querySelector("#peerList").innerHTML =
                `<div class="peer-empty">${peerEscape(error.message)}</div>`;
        }
        if (!peerState.heartbeat) {
            peerState.heartbeat = window.setInterval(() => {
                peerRequest("/messaging/presence", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({profile: peerProfile()})
                }).catch(() => {});
            }, 30000);
        }
        if (!peerState.inboxPoll) {
            peerState.inboxPoll = window.setInterval(() => {
                refreshPeerInbox().catch(() => {});
            }, 5000);
        }
        window.setTimeout(syncPanelState, 0);
    };

})();
