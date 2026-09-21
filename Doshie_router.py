import re
import yoshi_memory
import yoshi_spotify


def _route_tool_rules(
    text,
    default_location="El Paso",
    profile="Hermes"
):
    """
    Returns:
        handled: bool
        reply: str | None
    """

    clean = text.strip()
    lower = clean.lower()
    normalized = lower.rstrip(" ?.!")

    # Spotify Premium controls are deterministic and profile-aware.
    spotify_now_phrases = {
        "what's playing",
        "whats playing",
        "what is playing",
        "what's playing on spotify",
        "whats playing on spotify",
        "show what's playing",
        "show whats playing",
    }
    if normalized in spotify_now_phrases:
        try:
            playing = yoshi_spotify.now_playing(profile)
        except yoshi_spotify.SpotifyError as error:
            return True, str(error)
        if not playing.get("active"):
            return True, "Nothing is playing on Spotify right now."
        track = playing.get("track") or {}
        state = "Playing" if playing.get("is_playing") else "Paused"
        device = (playing.get("device") or {}).get("name")
        reply = (
            f"{state}: {track.get('name', 'Unknown track')} by "
            f"{track.get('artists') or 'Unknown artist'}"
        )
        if device:
            reply += f" on {device}"
        return True, reply + "."

    spotify_actions = {
        "pause spotify": "pause",
        "pause music": "pause",
        "pause the music": "pause",
        "resume spotify": "play",
        "resume music": "play",
        "continue music": "play",
        "play music": "play",
        "next song": "next",
        "next track": "next",
        "skip song": "next",
        "skip this song": "next",
        "previous song": "previous",
        "previous track": "previous",
        "go back a song": "previous",
    }
    if normalized in spotify_actions:
        try:
            yoshi_spotify.control(
                profile,
                spotify_actions[normalized]
            )
        except yoshi_spotify.SpotifyError as error:
            return True, str(error)
        labels = {
            "pause": "Spotify paused.",
            "play": "Spotify is playing.",
            "next": "Skipped to the next song.",
            "previous": "Went back to the previous song.",
        }
        return True, labels[spotify_actions[normalized]]

    if normalized in {
        "show my spotify playlists",
        "show my playlists",
        "open my playlists",
        "list my spotify playlists",
    }:
        try:
            items = yoshi_spotify.playlists(profile, limit=10)
        except yoshi_spotify.SpotifyError as error:
            return True, str(error)
        if not items:
            return True, "I couldn't find any Spotify playlists."
        return True, "Your Spotify playlists: " + " | ".join(
            item["name"] for item in items
        )

    playlist_match = re.match(
        r"^(?:play|open)\s+(?:my\s+)?(.+?)\s+playlist"
        r"(?:\s+on spotify)?[?.!]?$",
        clean,
        flags=re.IGNORECASE,
    )
    if playlist_match:
        requested = playlist_match.group(1).strip()
        try:
            items = yoshi_spotify.playlists(profile, limit=10)
            selected = next(
                (
                    item for item in items
                    if requested.casefold() in item["name"].casefold()
                ),
                None,
            )
            if selected is None:
                return True, f"I couldn't find a Spotify playlist named {requested}."
            yoshi_spotify.play_playlist(profile, selected["uri"])
        except yoshi_spotify.SpotifyError as error:
            return True, str(error)
        return True, f"Playing your {selected['name']} playlist."

    spotify_search = re.match(
        r"^(?:search spotify for|find on spotify)\s+(.+?)[?.!]?$",
        clean,
        flags=re.IGNORECASE,
    )
    if spotify_search:
        requested = spotify_search.group(1).strip()
        try:
            items = yoshi_spotify.search_tracks(
                profile,
                requested,
                limit=5,
            )
        except yoshi_spotify.SpotifyError as error:
            return True, str(error)
        if not items:
            return True, f"I couldn't find {requested} on Spotify."
        return True, "Spotify found: " + " | ".join(
            f"{item['name']} by {item['artists']}"
            for item in items
        )

    spotify_play = re.match(
        r"^(?:play|put on)\s+(.+?)\s+on spotify[?.!]?$",
        clean,
        flags=re.IGNORECASE,
    )
    if not spotify_play:
        spotify_play = re.match(
            r"^play\s+(?:the\s+)?song\s+(.+?)[?.!]?$",
            clean,
            flags=re.IGNORECASE,
        )
    if spotify_play:
        requested = spotify_play.group(1).strip()
        try:
            track = yoshi_spotify.search_and_play(profile, requested)
        except yoshi_spotify.SpotifyError as error:
            return True, str(error)
        return True, (
            f"Playing {track['name']} by "
            f"{track['artists']} on Spotify."
        )

    # Reliable saved-item search
    search_prefixes = (
        "find anything i saved about ",
        "do i have anything saved about ",
        "search my saved items for ",
        "search my notes for ",
        "find saved information about ",
    )

    for prefix in search_prefixes:
        if normalized.startswith(prefix):
            query = normalized[len(prefix):].strip()

            if not query:
                return True, "Tell me what you want me to search for."

            results = yoshi_memory.search_saved_items(
                query,
                profile=profile
            )

            if not results:
                return True, f"I couldn't find anything saved about {query}."

            parts = []

            for item in results:
                if item["type"] == "memory":
                    parts.append(
                        f"🧠 Memory #{item['id']}: {item['text']}"
                    )

                elif item["type"] == "note":
                    parts.append(
                        f"📝 Note #{item['id']}: {item['text']}"
                    )

                elif item["type"] == "task":
                    state = "✅" if item.get("done") else "⬜"

                    meta = item.get("priority", "Normal")

                    if item.get("due_date"):
                        meta += f", due {item['due_date']}"

                    parts.append(
                        f"{state} Task #{item['id']}: "
                        f"{item['text']} [{meta}]"
                    )

            return True, " | ".join(parts)
    query = lower.rstrip(" ?.!")

    # Reliable task database queries
    if query in (
        "what's due tomorrow",
        "whats due tomorrow",
        "what is due tomorrow",
        "show what's due tomorrow",
        "show whats due tomorrow",
    ):
        from datetime import date, timedelta

        target = (date.today() + timedelta(days=1)).isoformat()

        conn = yoshi_memory.connect_db()
        rows = conn.execute(
            """
            SELECT id, task, priority, due_date
            FROM tasks
            WHERE done = 0 AND due_date = ?
            ORDER BY
                CASE priority
                    WHEN 'High' THEN 1
                    WHEN 'Normal' THEN 2
                    WHEN 'Low' THEN 3
                    ELSE 4
                END,
                id
            """,
            (target,)
        ).fetchall()
        conn.close()

        if not rows:
            return True, "You have nothing due tomorrow."

        return True, " | ".join(
            f"{task_id}: {task} [{priority or 'Normal'}, due {due_date}]"
            for task_id, task, priority, due_date in rows
        )

    if query in (
        "what do i need to do today",
        "what's due today",
        "whats due today",
        "what is due today",
        "show today's tasks",
        "show todays tasks",
    ):
        from datetime import date

        target = date.today().isoformat()

        conn = yoshi_memory.connect_db()
        rows = conn.execute(
            """
            SELECT id, task, priority, due_date
            FROM tasks
            WHERE done = 0 AND due_date = ?
            ORDER BY
                CASE priority
                    WHEN 'High' THEN 1
                    WHEN 'Normal' THEN 2
                    WHEN 'Low' THEN 3
                    ELSE 4
                END,
                id
            """,
            (target,)
        ).fetchall()
        conn.close()

        if not rows:
            return True, "You have nothing due today."

        return True, " | ".join(
            f"{task_id}: {task} [{priority or 'Normal'}, due {due_date}]"
            for task_id, task, priority, due_date in rows
        )

    if query in (
        "show my high-priority tasks",
        "show my high priority tasks",
        "what are my high-priority tasks",
        "what are my high priority tasks",
    ):
        conn = yoshi_memory.connect_db()

        rows = conn.execute(
            """
            SELECT id, task, due_date
            FROM tasks
            WHERE done = 0 AND priority = 'High'
            ORDER BY
                CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
                due_date,
                id
            """
        ).fetchall()

        conn.close()

        if not rows:
            return True, "You have no open high-priority tasks."

        return True, " | ".join(
            f"{task_id}: {task}" +
            (f" [due {due_date}]" if due_date else "")
            for task_id, task, due_date in rows
        )

    # Smarter natural-language task creation
    task_match = re.match(
        r"add\s+(.+?)\s+to my tasks(?:,\s*(low|normal|high)\s+priority)?(?:,\s*due\s+(.+))?[.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if task_match:
        task_text = task_match.group(1).strip()
        priority = (task_match.group(2) or "Normal").title()
        due_text = (task_match.group(3) or "").strip().lower()

        due_date = None

        if due_text:
            from datetime import date, timedelta

            today = date.today()

            if due_text == "today":
                due_date = today.isoformat()

            elif due_text == "tomorrow":
                due_date = (today + timedelta(days=1)).isoformat()

            else:
                weekdays = {
                    "monday": 0,
                    "tuesday": 1,
                    "wednesday": 2,
                    "thursday": 3,
                    "friday": 4,
                    "saturday": 5,
                    "sunday": 6,
                }

                if due_text in weekdays:
                    days_ahead = (
                        weekdays[due_text] - today.weekday()
                    ) % 7

                    if days_ahead == 0:
                        days_ahead = 7

                    due_date = (
                        today + timedelta(days=days_ahead)
                    ).isoformat()

        conn = yoshi_memory.connect_db()

        conn.execute(
            """
            INSERT INTO tasks (
                task,
                done,
                priority,
                due_date
            )
            VALUES (?, 0, ?, ?)
            """,
            (
                task_text,
                priority,
                due_date
            )
        )

        conn.commit()
        conn.close()

        reply = f"Task added: {task_text}. Priority: {priority}."

        if due_date:
            reply += f" Due: {due_date}."

        return True, reply

    # Notes and tasks

    # Tag-aware task queries
    task_tag_match = re.match(
        r"^(?:show|list|find)\s+my\s+(general|tech|home|school|gaming|personal)\s+tasks[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if task_tag_match:
        tag = task_tag_match.group(1).title()

        rows = [
            row for row in yoshi_memory.get_tasks()
            if (row[5] or "General") == tag
        ]

        if not rows:
            return True, f"You have no {tag} tasks."

        return True, " | ".join(
            (
                f"{task_id}: {'✅' if done else '⬜'} {task} "
                f"[{priority or 'Normal'}"
                + (f", due {due_date}" if due_date else "")
                + f", {task_tag or 'General'}]"
            )
            for task_id, task, done, priority, due_date, task_tag, _assigned_to in rows
        )

    # Tag-aware note queries
    note_tag_match = re.match(
        r"^(?:show|list|find)\s+my\s+(general|tech|home|school|gaming|personal)\s+notes[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if note_tag_match:
        tag = note_tag_match.group(1).title()

        rows = [
            row for row in yoshi_memory.get_notes()
            if (row[2] or "General") == tag
        ]

        if not rows:
            return True, f"You have no {tag} notes."

        return True, " | ".join(
            f"{note_id}: {note} [{note_tag or 'General'}]"
            for note_id, note, note_tag in rows
        )

    # Anything with a specific tag
    tagged_match = re.match(
        r"^(?:what do i have|show me|find anything)\s+tagged\s+(general|tech|home|school|gaming|personal)[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if tagged_match:
        tag = tagged_match.group(1).title()
        parts = []

        for note_id, note, note_tag in yoshi_memory.get_notes():
            if (note_tag or "General") == tag:
                parts.append(
                    f"📝 Note #{note_id}: {note}"
                )

        for (
            task_id,
            task,
            done,
            priority,
            due_date,
            task_tag,
            _assigned_to,
        ) in yoshi_memory.get_tasks():
            if (task_tag or "General") == tag:
                state = "✅" if done else "⬜"

                meta = priority or "Normal"

                if due_date:
                    meta += f", due {due_date}"

                parts.append(
                    f"{state} Task #{task_id}: {task} [{meta}]"
                )

        if not parts:
            return True, f"You have nothing tagged {tag}."

        return True, " | ".join(parts)

    # Normal task creation
    if lower.startswith("add ") and " to my tasks" in lower:
        task = re.sub(
            r"^add\s+|\s+to my tasks[.!]?$",
            "",
            clean,
            flags=re.IGNORECASE
        ).strip()

        return True, yoshi_memory.add_task(task)

    if lower.startswith("add task "):
        task = clean[len("add task "):].strip()
        return True, yoshi_memory.add_task(task)

    # Show all tasks
    if lower.rstrip(" ?.!") in (
        "show my tasks",
        "show tasks",
        "what are my tasks",
        "list my tasks",
    ):
        rows = yoshi_memory.get_tasks()

        if not rows:
            return True, "You have no tasks."

        return True, " | ".join(
            (
                f"{task_id}: {'✅' if done else '⬜'} {task} "
                f"[{priority or 'Normal'}"
                + (f", due {due_date}" if due_date else "")
                + f", {tag or 'General'}]"
            )
            for task_id, task, done, priority, due_date, tag, _assigned_to in rows
        )

    done_match = re.search(
        r"(?:mark|complete)\s+task\s+(\d+)\s*(?:done|complete)?",
        lower
    )

    if done_match:
        return True, yoshi_memory.complete_task(
            done_match.group(1)
        )

    # Notes
    if lower.startswith("save a note "):
        note = clean[len("save a note "):].strip()
        return True, yoshi_memory.add_note(note)

    if lower.startswith("remember a note "):
        note = clean[len("remember a note "):].strip()
        return True, yoshi_memory.add_note(note)

    if lower.startswith("make a note "):
        note = clean[len("make a note "):].strip()
        return True, yoshi_memory.add_note(note)

    if lower.rstrip(" ?.!") in (
        "show my notes",
        "show notes",
        "list my notes",
        "what are my notes",
    ):
        rows = yoshi_memory.get_notes()

        if not rows:
            return True, "You have no saved notes."

        return True, " | ".join(
            f"{note_id}: {note} [{tag or 'General'}]"
            for note_id, note, tag in rows
        )

    # Family
    if lower.rstrip(" ?.!") in (
        "/family",
        "show my family",
        "show family",
        "who is in my family",
        "list my family",
    ):
        rows = yoshi_memory.get_family_members()

        if not rows:
            return True, "No family members are saved yet."

        reply = " | ".join(
            f"{member_id}: {name} [{role}]"
            + (f" - {notes}" if notes else "")
            for member_id, name, role, notes in rows
        )

        return True, reply

    if lower.startswith("/family add "):
        value = clean[len("/family add "):].strip()

        parts = value.split(" ", 1)

        name = parts[0]
        role = parts[1] if len(parts) > 1 else "Family"

        return True, yoshi_memory.add_family_member(name, role)

    if lower.startswith("/family remove "):
        member_id = clean[len("/family remove "):].strip()
        return True, yoshi_memory.remove_family_member(member_id)

    family_match = re.match(
        r"^add\s+(.+?)\s+as\s+(?:my\s+)?(.+?)[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if family_match:
        name = family_match.group(1).strip()
        role = family_match.group(2).strip()

        family_words = (
            "wife", "husband", "son", "daughter",
            "child", "kid", "mother", "father",
            "mom", "dad", "brother", "sister",
            "family"
        )

        if any(word in role.lower() for word in family_words):
            return True, yoshi_memory.add_family_member(name, role)

    # Family shopping list
    shopping_add = re.match(
        r"^add\s+(.+?)\s+to\s+(?:the|my|our)\s+shopping\s+list[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if shopping_add:
        item_text = shopping_add.group(1).strip()

        quantity = None
        item = item_text

        quantity_match = re.match(
            r"^(\d+)\s+(.+)$",
            item_text
        )

        if quantity_match:
            quantity = quantity_match.group(1)
            item = quantity_match.group(2).strip()

        return True, yoshi_memory.add_shopping_item(
            item,
            quantity=quantity
        )

    if lower.rstrip(" ?.!") in (
        "show the shopping list",
        "show my shopping list",
        "show our shopping list",
        "what's on the shopping list",
        "whats on the shopping list",
        "shopping list",
    ):
        rows = yoshi_memory.get_shopping_items()

        if not rows:
            return True, "The shopping list is empty."

        return True, " | ".join(
            (
                f"{item_id}: {'✅' if bought else '⬜'} {item}"
                + (f" x{quantity}" if quantity else "")
                + (f" [{category}]" if category else "")
                + (f" • {added_by}" if added_by else "")
            )
            for item_id, item, quantity, bought, added_by, category in rows
        )

    bought_match = re.match(
        r"^(?:mark|set)\s+shopping\s+item\s+(\d+)\s+(?:bought|done)[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if bought_match:
        return True, yoshi_memory.set_shopping_bought(
            bought_match.group(1),
            True
        )

    # Family task queries
    person_tasks_match = re.match(
        r"^(?:show|list|what are)\s+(.+?)(?:'s|s')\s+(?:tasks|chores)[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if person_tasks_match:
        family_name = person_tasks_match.group(1).strip()

        conn = yoshi_memory.connect_db()

        member = conn.execute(
            """
            SELECT id, name
            FROM family_members
            WHERE lower(name) = lower(?)
            LIMIT 1
            """,
            (family_name,)
        ).fetchone()

        if not member:
            conn.close()
            return True, f"I couldn't find {family_name} in the family list."

        member_id, member_name = member

        rows = conn.execute(
            """
            SELECT id, task, done, priority, due_date
            FROM tasks
            WHERE assigned_to = ?
            ORDER BY done, due_date, id
            """,
            (member_id,)
        ).fetchall()

        conn.close()

        if not rows:
            return True, f"{member_name} has no assigned tasks."

        reply = " | ".join(
            (
                f"{task_id}: {'✅' if done else '⬜'} {task}"
                + f" [{priority or 'Normal'}"
                + (f", due {due_date}" if due_date else "")
                + "]"
            )
            for task_id, task, done, priority, due_date in rows
        )

        return True, f"{member_name}'s tasks: {reply}"

    if lower.rstrip(" ?.!") in (
        "show everyone's chores",
        "show everyones chores",
        "show family chores",
        "show the family chores",
        "show everyone's tasks",
        "show everyones tasks",
    ):
        conn = yoshi_memory.connect_db()

        rows = conn.execute(
            """
            SELECT
                tasks.id,
                tasks.task,
                tasks.done,
                family_members.name
            FROM tasks
            LEFT JOIN family_members
                ON tasks.assigned_to = family_members.id
            WHERE tasks.done = 0
            ORDER BY family_members.name, tasks.id
            """
        ).fetchall()

        conn.close()

        if not rows:
            return True, "There are no open family chores."

        return True, " | ".join(
            f"{'👤 ' + name if name else '👤 Unassigned'}: ⬜ {task}"
            for task_id, task, done, name in rows
        )

    if lower.rstrip(" ?.!") in (
        "what does the family need to do today",
        "what are the family tasks today",
        "what are today's family chores",
        "what are todays family chores",
    ):
        from datetime import date

        today = date.today().isoformat()

        conn = yoshi_memory.connect_db()

        rows = conn.execute(
            """
            SELECT
                tasks.task,
                family_members.name
            FROM tasks
            LEFT JOIN family_members
                ON tasks.assigned_to = family_members.id
            WHERE tasks.done = 0
              AND tasks.due_date = ?
            ORDER BY family_members.name, tasks.id
            """,
            (today,)
        ).fetchall()

        conn.close()

        if not rows:
            return True, "The family has no tasks due today."

        return True, "Today's family tasks: " + " | ".join(
            f"{name or 'Unassigned'}: {task}"
            for task, name in rows
        )

    # Family task assignment
    family_task_match = re.match(
        r"^assign\s+(.+?)\s+to\s+(.+?)[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if family_task_match:
        task_text = family_task_match.group(1).strip()
        family_name = family_task_match.group(2).strip()

        return True, yoshi_memory.assign_task_to_family(
            task_text,
            family_name
        )

    # Family-assigned reminders
    family_reminder_match = re.match(
        r"^remind\s+(.+?)\s+to\s+(.+?)(?:\s+(today|tomorrow))?[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if family_reminder_match:
        family_name = family_reminder_match.group(1).strip()
        reminder_text = family_reminder_match.group(2).strip()
        when = (
            family_reminder_match.group(3).lower()
            if family_reminder_match.group(3)
            else None
        )

        member = yoshi_memory.find_family_member(
            family_name
        )

        if member:
            from datetime import date, timedelta

            due_date = None

            if when == "today":
                due_date = date.today().isoformat()

            elif when == "tomorrow":
                due_date = (
                    date.today() + timedelta(days=1)
                ).isoformat()

            member_id, member_name, role, notes = member

            reply = yoshi_memory.add_reminder(
                reminder_text,
                due_date=due_date,
                assigned_to=member_id
            )

            return True, (
                f"{reply} Assigned to {member_name}."
            )

    # Family reminder queries
    person_reminders_match = re.match(
        r"^(?:show|list)\s+(.+?)(?:'s|s')\s+reminders[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if person_reminders_match:
        family_name = person_reminders_match.group(1).strip()

        member = yoshi_memory.find_family_member(family_name)

        if not member:
            return True, f"I couldn't find {family_name} in the family list."

        member_id, member_name, role, notes = member

        rows = [
            row for row in yoshi_memory.get_reminders()
            if row[3] == member_id
        ]

        if not rows:
            return True, f"{member_name} has no reminders."

        return True, " | ".join(
            (
                f"{reminder_id}: "
                f"{'✅' if done else '⏰'} {reminder}"
                + (f" [Due {due_date}]" if due_date else "")
            )
            for reminder_id, reminder, due_date, assigned_to, done in rows
        )

    tomorrow_reminders_match = re.match(
        r"^what reminders does\s+(.+?)\s+have\s+tomorrow[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if tomorrow_reminders_match:
        from datetime import date, timedelta

        family_name = tomorrow_reminders_match.group(1).strip()

        member = yoshi_memory.find_family_member(family_name)

        if not member:
            return True, f"I couldn't find {family_name} in the family list."

        member_id, member_name, role, notes = member

        tomorrow = (
            date.today() + timedelta(days=1)
        ).isoformat()

        rows = [
            row for row in yoshi_memory.get_reminders()
            if row[3] == member_id
            and row[2] == tomorrow
            and not row[4]
        ]

        if not rows:
            return True, f"{member_name} has no reminders tomorrow."

        return True, (
            f"{member_name}'s reminders tomorrow: "
            + " | ".join(
                f"⏰ {reminder}"
                for reminder_id, reminder, due_date, assigned_to, done in rows
            )
        )

    if lower.rstrip(" ?.!") in (
        "show everyone's reminders",
        "show everyones reminders",
        "show family reminders",
        "list family reminders",
    ):
        members = {
            row[0]: row[1]
            for row in yoshi_memory.get_family_members()
        }

        rows = yoshi_memory.get_reminders()

        if not rows:
            return True, "There are no family reminders."

        return True, " | ".join(
            (
                f"{members.get(assigned_to, 'Unassigned')}: "
                f"{'✅' if done else '⏰'} {reminder}"
                + (f" [Due {due_date}]" if due_date else "")
            )
            for reminder_id, reminder, due_date, assigned_to, done in rows
        )

    # Family reminders
    reminder_match = re.match(
        r"^remind me to\s+(.+?)(?:\s+tomorrow)?[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if reminder_match:
        reminder_text = reminder_match.group(1).strip()
        due_date = None

        if " tomorrow" in lower:
            from datetime import date, timedelta
            due_date = (date.today() + timedelta(days=1)).isoformat()

        return True, yoshi_memory.add_reminder(
            reminder_text,
            due_date=due_date
        )

    if lower.rstrip(" ?.!") in (
        "show reminders",
        "show my reminders",
        "what are my reminders",
        "list reminders",
    ):
        rows = yoshi_memory.get_reminders()

        if not rows:
            return True, "You have no reminders."

        return True, " | ".join(
            (
                f"{reminder_id}: "
                f"{'✅' if done else '⏰'} {reminder}"
                + (f" [Due {due_date}]" if due_date else "")
            )
            for reminder_id, reminder, due_date, assigned_to, done in rows
        )

    # Family-assigned routines
    family_routine_match = re.match(
        r"^(.+?)\s+(.+?)\s+every\s+"
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
        r"[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if family_routine_match:
        family_name = family_routine_match.group(1).strip()
        routine_text = family_routine_match.group(2).strip()
        weekday = family_routine_match.group(3).title()

        family_names = [
            row[1]
            for row in yoshi_memory.get_family_members()
        ]

        matches = [
            name
            for name in family_names
            if name.lower() == family_name.lower()
            or name.lower().startswith(
                family_name.lower() + " "
            )
        ]

        if len(matches) == 1:
            return True, yoshi_memory.add_family_routine(
                routine_text,
                family_name,
                weekday
            )

        if len(matches) > 1:
            return True, (
                f"I found more than one family member named "
                f"{family_name}. Please use the full name."
            )

    # Family routine queries
    person_routines_match = re.match(
        r"^(?:show|list)\s+(.+?)(?:'s|s')\s+routines[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if person_routines_match:
        family_name = person_routines_match.group(1).strip()

        members = yoshi_memory.get_family_members()

        matches = [
            row for row in members
            if row[1].lower() == family_name.lower()
            or row[1].lower().startswith(
                family_name.lower() + " "
            )
        ]

        if not matches:
            return True, f"I couldn't find {family_name} in the family list."

        if len(matches) > 1:
            return True, (
                f"I found more than one family member named "
                f"{family_name}. Please use the full name."
            )

        member_id, member_name, role, notes = matches[0]

        rows = [
            row for row in yoshi_memory.get_routines()
            if row[3] == member_id
        ]

        if not rows:
            return True, f"{member_name} has no recurring routines."

        return True, " | ".join(
            (
                f"{routine_id}: "
                f"{'🔁' if active else '⏸️'} {routine}"
                + (f" [Every {weekday}]" if weekday else "")
            )
            for routine_id, routine, weekday, assigned_to, active in rows
        )

    if lower.rstrip(" ?.!") in (
        "show everyone's routines",
        "show everyones routines",
        "show family routines",
        "list family routines",
    ):
        members = {
            row[0]: row[1]
            for row in yoshi_memory.get_family_members()
        }

        rows = yoshi_memory.get_routines()

        if not rows:
            return True, "There are no recurring family routines."

        parts = []

        for routine_id, routine, weekday, assigned_to, active in rows:
            name = members.get(assigned_to, "Unassigned")

            parts.append(
                f"{name}: "
                f"{'🔁' if active else '⏸️'} {routine}"
                + (f" [Every {weekday}]" if weekday else "")
            )

        return True, " | ".join(parts)

    # Family routines
    routine_match = re.match(
        r"^remind me to\s+(.+?)\s+every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)[?.!]?$",
        clean,
        flags=re.IGNORECASE
    )

    if routine_match:
        routine_text = routine_match.group(1).strip()
        weekday = routine_match.group(2).title()

        return True, yoshi_memory.add_routine(
            routine_text,
            weekday=weekday
        )

    if lower.rstrip(" ?.!") in (
        "show my routines",
        "show routines",
        "list routines",
        "what are my routines",
    ):
        rows = yoshi_memory.get_routines()

        if not rows:
            return True, "You have no recurring routines."

        return True, " | ".join(
            (
                f"{routine_id}: "
                f"{'🔁' if active else '⏸️'} {routine}"
                + (f" [Every {weekday}]" if weekday else "")
            )
            for routine_id, routine, weekday, assigned_to, active in rows
        )

    # Backup
    if lower.rstrip(" ?.!") in (
        "/backup",
        "backup yoshi",
        "make a backup",
        "create a backup",
        "backup yourself",
    ):
        return True, yoshi_memory.create_backup()

    # Clipboard
    clipboard_phrases = (
        "what's on my clipboard",
        "whats on my clipboard",
        "what is on my clipboard",
        "read my clipboard",
        "show my clipboard",
        "clipboard contents",
    )

    if clean == "/clipboard" or any(
        phrase in lower for phrase in clipboard_phrases
    ):
        return True, yoshi_memory.get_clipboard_text()

    # Battery
    battery_phrases = (
        "what's my battery",
        "whats my battery",
        "what is my battery",
        "battery level",
        "battery percentage",
        "am i charging",
        "am i plugged in",
        "how much battery",
    )

    if clean == "/battery" or any(
        phrase in lower for phrase in battery_phrases
    ):
        return True, yoshi_memory.get_battery_status()

    # Full device status
    status_phrases = (
        "how's my phone",
        "hows my phone",
        "how is my phone",
        "device status",
        "phone status",
        "how much storage",
        "how much space",
        "storage left",
        "storage free",
        "is my battery healthy",
        "battery health",
    )

    if clean == "/status" or any(
        phrase in lower for phrase in status_phrases
    ):
        return True, yoshi_memory.get_device_status()

    # Explicit/default weather requests
    if lower in (
        "/weather",
        "weather",
        "weather?",
        "current weather",
        "weather now",
    ):
        return True, yoshi_memory.get_weather("El Paso")

    if lower.startswith("/weather "):
        location = clean[len("/weather "):].strip()
        return True, yoshi_memory.get_weather(location)

    # Tomorrow forecast
    if "tomorrow" in lower and (
        "weather" in lower
        or "forecast" in lower
        or "rain" in lower
        or "temperature" in lower
        or "high" in lower
        or "low" in lower
    ):
        location = default_location

        match = re.search(
            r"\bin\s+(.+?)[?.!]?$",
            clean,
            flags=re.IGNORECASE
        )

        if match:
            location = match.group(1).strip()

        forecast = yoshi_memory.get_forecast(location, 1)
        return True, f"Tomorrow's forecast: {forecast}"

    # Current weather
    weather_phrases = (
        "what's the weather",
        "whats the weather",
        "what is the weather",
        "how's the weather",
        "hows the weather",
        "weather today",
        "weather outside",
    )

    if any(phrase in lower for phrase in weather_phrases):
        location = default_location

        match = re.search(
            r"\bin\s+(.+?)[?.!]?$",
            clean,
            flags=re.IGNORECASE
        )

        if match:
            location = match.group(1).strip()

        return True, yoshi_memory.get_weather(location)

    # News routing
    is_news = (
        normalized in {
            "news", "new", "the news", "headlines", "the headlines",
            "daily news", "local news", "tech news", "gaming news",
            "national news", "world news", "news update", "news updates",
            "latest news", "today's news", "todays news", "news today",
            "show news", "get news", "read news", "check news",
        }
        or bool(re.search(r"\b(?:news|headlines)\b", lower))
        or lower.startswith("news ")
        or lower.endswith(" news")
    )
    if is_news:
        try:
            import Doshie_news
            topic = "local"
            # Check for custom topic queries like "news about tesla" or "news on space"
            custom_match = re.search(r"(?:news|headlines)\s+(?:about|on|regarding|for)\s+(.+)$", clean, re.IGNORECASE)
            if custom_match:
                custom_topic = custom_match.group(1).strip(" ?.!")
                data = Doshie_news.search_news(custom_topic, limit=6)
            else:
                if "tech" in lower or "ai" in lower or "software" in lower:
                    topic = "tech"
                elif "gaming" in lower or "game" in lower or "games" in lower:
                    topic = "gaming"
                elif "national" in lower or "world" in lower or "us" in lower:
                    topic = "national"
                elif "family" in lower or "kids" in lower:
                    topic = "family"
                data = Doshie_news.get_headlines(topic=topic, limit=6)

            items = data.get("items", [])
            if not items:
                return True, "No news headlines are available right now."

            reply_lines = [f"📰 **{data.get('label', 'NEWS HEADLINES')}**\n"]
            for idx, item in enumerate(items[:6], 1):
                title = item.get("title", "")
                source = item.get("source", "")
                url = item.get("url", "")
                if url:
                    reply_lines.append(f"{idx}. [{title}]({url}) · *{source}*")
                else:
                    reply_lines.append(f"{idx}. **{title}** · *{source}*")
            return True, "\n\n".join(reply_lines)
        except Exception as error:
            return True, f"Could not load news: {error}"

    # Web search routing
    search_match = re.match(
        r"^(?:search(?:\s+the)?\s+(?:web|internet)|search\s+online\s+for|search\s+for|look\s+up\s+online|google|find\s+online)\s+(?:for\s+)?(.+?)[?.!]?$",
        clean,
        flags=re.IGNORECASE,
    )
    if not search_match and (lower.startswith("search the web for ") or lower.startswith("search web for ") or lower.startswith("google ")):
        q = re.sub(r"^(?:search\s+(?:the\s+)?web\s+for|google)\s+", "", clean, flags=re.IGNORECASE).strip(" ?.!")
        if q:
            search_match = type("Match", (), {"group": lambda self, n: q})()

    if search_match:
        search_query = search_match.group(1).strip()
        if search_query:
            try:
                import Doshie_search
                import Doshie_profile_preferences
                is_under_18 = Doshie_profile_preferences.is_profile_under_18(profile)
                res = Doshie_search.web_search(search_query, is_under_18=is_under_18)
                results = res.get("results", [])
                if not results:
                    return True, f"I searched the web for '{search_query}' but found no safe results."

                reply_lines = [f"🔍 **Web search results for *{search_query}***\n"]
                for idx, item in enumerate(results[:4], 1):
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    url = item.get("url", "")
                    if url:
                        reply_lines.append(f"{idx}. [{title}]({url})\n   {snippet}")
                    else:
                        reply_lines.append(f"{idx}. **{title}**\n   {snippet}")
                return True, "\n\n".join(reply_lines)
            except Exception as error:
                return True, f"Web search could not be completed: {error}"

    return False, None


# ============================================================
# YOSHI BRAIN v3.3
# AI-assisted tool routing fallback
# ============================================================

def _looks_like_tool_request(text):
    """Avoid an AI routing call for ordinary conversation."""

    lower = (text or "").strip().lower()

    markers = (
        "weather",
        "forecast",
        "temperature",
        "battery",
        "charge",
        "device status",
        "phone status",
        "task",
        "tasks",
        "todo",
        "to-do",
        "note",
        "notes",
        "shopping",
        "grocery",
        "groceries",
        "remind",
        "reminder",
        "saved",
        "find my",
        "add ",
        "show my",
        "what do i need",
        "news",
        "headline",
        "headlines",
        "search",
        "google",
        "web search",
        "search online",
        "look up",
    )

    return any(marker in lower for marker in markers)


def _classify_tool_request(text, default_location):
    """Use the local model only for ambiguous tool-like requests."""

    import json
    import urllib.request

    prompt = f"""
Classify this request for DiYoshi's local tools.

Return ONLY valid JSON.

Allowed intents:
none
battery
device_status
weather
news
web_search
list_tasks
add_task
add_note
shopping_list
add_shopping

JSON format:
{{
  "intent": "none",
  "text": "",
  "location": ""
}}

Rules:
- Use none if normal conversation does not require a local tool.
- news means local or current news headlines. Put the topic or location in text.
- web_search means search the internet or web for info. Put the query in text.
- add_task means create a task.
- add_note means save a note.
- add_shopping means add an item to the shopping list.
- list_tasks means show existing tasks.
- shopping_list means show shopping items.
- weather means current weather.
- Keep extracted text short and preserve the user's meaning.
- If no weather location is supplied, use "{default_location}".

User request:
{text}
""".strip()

    payload = json.dumps({
        "model": yoshi_memory.MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.0,
        "max_tokens": 80
    }).encode("utf-8")

    request = urllib.request.Request(
        yoshi_memory.URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=min(
                yoshi_memory.MODEL_TIMEOUT_SECONDS,
                20
            )
        ) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        answer = (
            data["choices"][0]["message"]["content"]
            .strip()
        )

        if answer.startswith("```"):
            answer = answer.strip("`")
            if answer.lower().startswith("json"):
                answer = answer[4:].strip()

        result = json.loads(answer)

        if not isinstance(result, dict):
            return None

        return result

    except Exception:
        return None


def _execute_ai_tool(result, default_location, profile="Hermes"):
    if not result:
        return False, None

    intent = str(result.get("intent", "none")).strip().lower()
    value = str(result.get("text", "") or "").strip()
    location = str(
        result.get("location", "") or default_location
    ).strip()

    if intent == "battery":
        return True, yoshi_memory.get_battery_status()

    if intent == "device_status":
        return True, yoshi_memory.get_device_status()

    if intent == "weather":
        return True, yoshi_memory.get_weather(
            location or default_location
        )

    if intent == "news":
        try:
            import Doshie_news
            topic = "local"
            if "tech" in value.lower():
                topic = "tech"
            elif "gaming" in value.lower() or "game" in value.lower():
                topic = "gaming"
            elif "national" in value.lower() or "world" in value.lower():
                topic = "national"
            elif "family" in value.lower():
                topic = "family"

            data = Doshie_news.get_headlines(topic=topic, limit=6)
            items = data.get("items", [])
            if not items:
                return True, "No news headlines are available right now."

            reply_lines = [f"📰 **{data.get('label', 'NEWS HEADLINES')}**\n"]
            for idx, item in enumerate(items[:6], 1):
                title = item.get("title", "")
                source = item.get("source", "")
                url = item.get("url", "")
                if url:
                    reply_lines.append(f"{idx}. [{title}]({url}) · *{source}*")
                else:
                    reply_lines.append(f"{idx}. **{title}** · *{source}*")
            return True, "\n\n".join(reply_lines)
        except Exception as error:
            return True, f"Could not load news: {error}"

    if intent == "web_search":
        if not value:
            return True, "What would you like me to search for on the web?"
        try:
            import Doshie_search
            import Doshie_profile_preferences
            is_under_18 = Doshie_profile_preferences.is_profile_under_18(profile)
            res = Doshie_search.web_search(value, is_under_18=is_under_18)
            results = res.get("results", [])
            if not results:
                return True, f"I searched the web for '{value}' but found no safe results."

            reply_lines = [f"🔍 **Web search results for *{value}***\n"]
            for idx, item in enumerate(results[:4], 1):
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                url = item.get("url", "")
                if url:
                    reply_lines.append(f"{idx}. [{title}]({url})\n   {snippet}")
                else:
                    reply_lines.append(f"{idx}. **{title}**\n   {snippet}")
            return True, "\n\n".join(reply_lines)
        except Exception as error:
            return True, f"Web search could not be completed: {error}"

    if intent == "list_tasks":
        rows = yoshi_memory.get_tasks()

        open_rows = [
            row for row in rows
            if not row[2]
        ]

        if not open_rows:
            return True, "You have no open tasks."

        reply = " | ".join(
            f"{row[0]}: {row[1]}"
            + (
                f" [{row[3] or 'Normal'}"
                + (
                    f", due {row[4]}"
                    if row[4]
                    else ""
                )
                + "]"
            )
            for row in open_rows
        )

        return True, reply

    if intent == "add_task":
        if not value:
            return True, "What task would you like me to add?"

        return True, yoshi_memory.add_task(value)

    if intent == "add_note":
        if not value:
            return True, "What would you like me to save as a note?"

        return True, yoshi_memory.add_note(value)

    if intent == "shopping_list":
        rows = yoshi_memory.get_shopping_items()

        if not rows:
            return True, "Your shopping list is empty."

        parts = []

        for row in rows:
            item_id = row[0]
            item = row[1]

            quantity = row[2] if len(row) > 2 else None
            bought = row[3] if len(row) > 3 else 0

            state = "✅" if bought else "⬜"

            label = f"{state} {item_id}: {item}"

            if quantity:
                label += f" ({quantity})"

            parts.append(label)

        return True, " | ".join(parts)

    if intent == "add_shopping":
        if not value:
            return True, "What should I add to the shopping list?"

        try:
            reply = yoshi_memory.add_shopping_item(value)
        except TypeError:
            # Some Yoshi builds have optional shopping arguments.
            reply = yoshi_memory.add_shopping_item(
                value,
                None,
                None
            )

        return True, reply

    return False, None



ALLOWED_TOOL_INTENTS = {
    "battery",
    "device_status",
    "weather",
    "news",
    "web_search",
    "list_tasks",
    "add_task",
    "add_note",
    "shopping_list",
    "add_shopping",
}


def _sanitize_tool_action(action, default_location="El Paso"):
    """Validate one AI-generated tool action before execution."""

    if not isinstance(action, dict):
        return None

    intent = str(
        action.get("intent", "")
    ).strip().lower()

    if intent not in ALLOWED_TOOL_INTENTS:
        return None

    value = action.get("text", "")
    location = action.get("location", "")

    if not isinstance(value, str):
        value = str(value or "")

    if not isinstance(location, str):
        location = str(location or "")

    value = value.strip()[:500]
    location = location.strip()[:120]

    # Write actions require actual content.
    if intent in {
        "add_task",
        "add_note",
        "add_shopping",
    } and not value:
        return None

    # Weather always gets a usable location.
    if intent == "weather" and not location:
        location = default_location

    return {
        "intent": intent,
        "text": value,
        "location": location,
    }


def _sanitize_tool_plan(actions, default_location="El Paso"):
    """Return a safe, deduplicated plan of at most three actions."""

    if not isinstance(actions, list):
        return []

    safe = []
    seen = set()

    for action in actions:
        clean = _sanitize_tool_action(
            action,
            default_location
        )

        if clean is None:
            continue

        signature = (
            clean["intent"],
            clean["text"].lower(),
            clean["location"].lower(),
        )

        if signature in seen:
            continue

        seen.add(signature)
        safe.append(clean)

        if len(safe) >= 3:
            break

    return safe


def _looks_like_multi_tool_request(text):
    """Detect requests that likely need two or more Yoshi tools."""

    lower = (text or "").strip().lower()

    groups = (
        ("weather", "forecast", "temperature"),
        ("task", "tasks", "todo", "to-do", "due"),
        ("shopping", "grocery", "groceries"),
        ("battery", "charge"),
        ("device status", "phone status"),
        ("note", "notes"),
        ("remind", "reminder"),
    )

    hits = 0

    for group in groups:
        if any(word in lower for word in group):
            hits += 1

    connectors = (
        " and ",
        " then ",
        " also ",
        " plus ",
        " along with ",
    )

    return hits >= 2 and any(
        connector in lower
        for connector in connectors
    )


def _plan_multi_tool_request(text, default_location):
    """Ask the local model for a small ordered tool plan."""

    import json
    import urllib.request

    prompt = f"""
You are DiYoshi's tool planner.

Convert the user's request into an ordered list of local tool actions.

Return ONLY valid JSON.

Allowed intents:
battery
device_status
weather
list_tasks
add_task
add_note
shopping_list
add_shopping

Format:
{{
  "actions": [
    {{
      "intent": "weather",
      "text": "",
      "location": "{default_location}"
    }}
  ]
}}

Rules:
- Use at most 3 actions.
- Include only actions actually requested.
- Preserve the order that makes sense.
- For add_task, put the task in "text".
- For add_note, put the note in "text".
- For add_shopping, put the shopping item in "text".
- For weather, extract the requested location.
- If no weather location is supplied, use "{default_location}".
- Do not invent tasks, notes, shopping items, or locations.
- Do not explain anything outside the JSON.

User request:
{text}
""".strip()

    payload = json.dumps({
        "model": yoshi_memory.MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.0,
        "max_tokens": 180
    }).encode("utf-8")

    request = urllib.request.Request(
        yoshi_memory.URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=min(
                yoshi_memory.MODEL_TIMEOUT_SECONDS,
                20
            )
        ) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        answer = (
            data["choices"][0]["message"]["content"]
            .strip()
        )

        if answer.startswith("```"):
            answer = answer.strip("`")

            if answer.lower().startswith("json"):
                answer = answer[4:].strip()

        plan = json.loads(answer)

        if not isinstance(plan, dict):
            return []

        actions = plan.get("actions", [])

        if not isinstance(actions, list):
            return []

        return _sanitize_tool_plan(
            actions,
            default_location
        )

    except Exception:
        return []


def _needs_result_reasoning(text):
    """Only spend another model call when the user asks for judgment."""

    lower = (text or "").strip().lower()

    reasoning_phrases = (
        "what should i do",
        "what should i do first",
        "what do you recommend",
        "recommend",
        "prioritize",
        "priority",
        "help me decide",
        "best thing to do",
        "what makes sense",
        "plan my",
        "plan for me",
        "tell me what to do",
        "which should i",
    )

    return any(
        phrase in lower
        for phrase in reasoning_phrases
    )


def _reason_over_tool_results(user_text, results):
    """Turn real tool outputs into a concise recommendation."""

    if not results:
        return None

    import json
    import urllib.request

    tool_context = "\n".join(
        f"{index}. {result}"
        for index, result in enumerate(
            results,
            start=1
        )
    )

    prompt = f"""
You are DiYoshi, a practical personal AI assistant.

The user asked:
{user_text}

These are REAL results returned by DiYoshi's local tools:
{tool_context}

Give a short, useful answer to the user's request.

Rules:
- Base your recommendation only on the tool results above.
- Do not invent tasks, weather, battery data, dates, or other facts.
- If information is insufficient, say what is missing.
- Prioritize urgent or time-sensitive items when the results support it.
- Keep the answer concise and practical.
- Do not mention internal tool routing or JSON.
""".strip()

    payload = json.dumps({
        "model": yoshi_memory.MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 140
    }).encode("utf-8")

    request = urllib.request.Request(
        yoshi_memory.URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=min(
                yoshi_memory.MODEL_TIMEOUT_SECONDS,
                20
            )
        ) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        answer = (
            data["choices"][0]["message"]["content"]
            .strip()
        )

        return answer or None

    except Exception:
        return None


def _execute_multi_tool_plan(
    actions,
    default_location,
    user_text=""
):
    """Run an ordered plan and optionally reason over its results."""

    if not actions:
        return False, None

    results = []

    for action in actions:
        handled, reply = _execute_ai_tool(
            action,
            default_location
        )

        if handled and reply:
            results.append(str(reply))

    if not results:
        return False, None

    if _needs_result_reasoning(user_text):
        recommendation = _reason_over_tool_results(
            user_text,
            results
        )

        if recommendation:
            return True, recommendation

    if len(results) == 1:
        return True, results[0]

    return True, "\n\n".join(
        f"{index}. {result}"
        for index, result in enumerate(
            results,
            start=1
        )
    )

def route_tool(
    text,
    default_location="El Paso",
    profile="Hermes"
):
    """
    Brain v3.4 router.

    1. Deterministic rules remain fastest.
    2. Multi-tool requests get one planning call.
    3. Single ambiguous tool requests use the v3.3 classifier.
    4. Ordinary conversation bypasses tool routing.
    """

    handled, reply = _route_tool_rules(
        text,
        default_location,
        profile=profile
    )

    if handled:
        return handled, reply

    if _looks_like_multi_tool_request(text):
        actions = _plan_multi_tool_request(
            text,
            default_location
        )

        handled, reply = _execute_multi_tool_plan(
            actions,
            default_location,
            text
        )

        if handled:
            return handled, reply

    if not _looks_like_tool_request(text):
        return False, None

    result = _classify_tool_request(
        text,
        default_location
    )

    safe_result = _sanitize_tool_action(
        result,
        default_location
    )

    if safe_result is None:
        return False, None

    return _execute_ai_tool(
        safe_result,
        default_location
    )

