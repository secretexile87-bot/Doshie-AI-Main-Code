"""Autonomous Background Task Agent Engine for Doshie.

Manages asynchronous background agents working on complex goals,
executing multi-step reasoning, invoking capability-gated tools,
logging step-by-step progress, and reporting back structured results.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time
import urllib.request
import uuid

import Doshie_agents
import Doshie_memory
import Doshie_tool_agent


DATA_DIR = Path(__file__).resolve().parent / "data"
TASKS_FILE = DATA_DIR / "agent_tasks.json"
_lock = threading.RLock()
_active_threads: dict[str, threading.Thread] = {}
_cancel_events: dict[str, threading.Event] = {}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_tasks_unlocked() -> list[dict]:
    try:
        if not TASKS_FILE.exists():
            return []
        data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("tasks"), list):
            return data["tasks"]
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_tasks_unlocked(tasks: list[dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": _now(),
        "tasks": tasks,
    }
    tmp_path = DATA_DIR / f".agent_tasks_{uuid.uuid4().hex[:8]}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, TASKS_FILE)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def list_tasks(limit: int = 50) -> list[dict]:
    with _lock:
        tasks = _load_tasks_unlocked()
        tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
        return tasks[:limit]


def get_task(task_id: str) -> dict | None:
    wanted = str(task_id or "").strip()
    with _lock:
        for t in _load_tasks_unlocked():
            if t.get("id") == wanted:
                return dict(t)
    return None


def cancel_task(task_id: str) -> bool:
    wanted = str(task_id or "").strip()
    with _lock:
        event = _cancel_events.get(wanted)
        if event:
            event.set()
        tasks = _load_tasks_unlocked()
        found = False
        for t in tasks:
            if t.get("id") == wanted and t.get("status") in ("queued", "running"):
                t["status"] = "cancelled"
                t["completed_at"] = _now()
                found = True
                break
        if found:
            _save_tasks_unlocked(tasks)
        return found


def clear_completed_tasks() -> int:
    with _lock:
        tasks = _load_tasks_unlocked()
        kept = [t for t in tasks if t.get("status") in ("queued", "running")]
        cleared_count = len(tasks) - len(kept)
        _save_tasks_unlocked(kept)
        return cleared_count


def _update_task(task_id: str, updates: dict):
    with _lock:
        tasks = _load_tasks_unlocked()
        for t in tasks:
            if t.get("id") == task_id:
                t.update(updates)
                break
        _save_tasks_unlocked(tasks)


def _append_task_step(task_id: str, step: dict):
    with _lock:
        tasks = _load_tasks_unlocked()
        for t in tasks:
            if t.get("id") == task_id:
                steps = t.setdefault("steps", [])
                steps.append(step)
                break
        _save_tasks_unlocked(tasks)


def _task_worker(task_id: str, agent: dict, goal: str, profile: str, context: str, cancel_event: threading.Event):
    _update_task(task_id, {"status": "running", "started_at": _now(), "progress": 10})
    
    agent_capabilities = agent.get("capabilities", [])
    model_name = Doshie_memory.choose_brain_model(
        goal + " " + agent.get("purpose", ""),
        brain_mode=agent.get("model_mode", "balanced")
    )
    
    system_prompt = (
        f"{Doshie_agents.agent_system_context(agent)}\n\n"
        "AUTONOMOUS TASK DIRECTIVE:\n"
        "You are operating as an autonomous background specialist. Your objective is to achieve the user's goal.\n"
        "You have access to approved capabilities and function tools.\n"
        "Use your tools iteratively to gather facts, inspect systems, search the web, read/write memory, or prepare proposals.\n"
        "When you have completed your work or gathered sufficient evidence, provide a thorough, structured, and actionable final report.\n"
        "Be clear, direct, and factual. Always present your findings clearly to the user."
    )
    
    user_content = f"OBJECTIVE / GOAL:\n{goal}"
    if context:
        user_content += f"\n\nADDITIONAL CONTEXT:\n{context}"
        
    working_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
    
    max_steps = 7
    step_count = 0
    final_result = ""
    error_msg = ""
    
    try:
        for i in range(1, max_steps + 1):
            if cancel_event.is_set():
                _update_task(task_id, {"status": "cancelled", "completed_at": _now()})
                return
                
            step_count = i
            progress = min(15 + int((i / max_steps) * 75), 90)
            _update_task(task_id, {"progress": progress})
            
            # Filter tools according to agent capabilities
            allowed_tool_names = set()
            for cap in agent_capabilities:
                for tname in Doshie_tool_agent.CAPABILITY_TOOL_MAP.get(cap, []):
                    allowed_tool_names.add(tname)
            allowed_tools = [t for t in Doshie_tool_agent.TOOLS if t["function"]["name"] in allowed_tool_names]
            
            request_body = {
                "model": model_name,
                "messages": working_messages,
                "temperature": 0.3,
                "max_tokens": 500,
                "reasoning_effort": "none",
                "think": False,
                "keep_alive": "5m"
            }
            if allowed_tools:
                request_body["tools"] = allowed_tools
                
            payload = json.dumps(request_body).encode("utf-8")
            url = Doshie_memory.URL
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
            except Exception as net_err:
                error_msg = f"Model request failed: {net_err}"
                break
                
            choice = resp_data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = str(message.get("content") or "").strip()
            tool_calls = message.get("tool_calls") or []
            
            # Record reasoning if available
            thinking = str(message.get("thinking") or "").strip()
            
            if not tool_calls:
                # Finished!
                final_result = content or "Task completed successfully with no additional output."
                _append_task_step(task_id, {
                    "step": step_count,
                    "type": "final_answer",
                    "thought": thinking,
                    "output": final_result,
                    "timestamp": _now(),
                })
                break
                
            # Has tool calls
            working_messages.append(message)
            step_record = {
                "step": step_count,
                "type": "tool_execution",
                "thought": thinking or content,
                "tool_calls": [],
                "timestamp": _now(),
            }
            
            for call in tool_calls:
                func = call.get("function") or {}
                fname = str(func.get("name") or "")
                raw_args = func.get("arguments") or {}
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args = {}
                    
                can_propose = profile.casefold() in {"hermes", "admin", "owner", "aeriel duran"}
                try:
                    tool_out = Doshie_tool_agent.execute_tool(
                        fname,
                        args,
                        actor_profile=profile,
                        can_propose_changes=can_propose
                    )
                    content_str = json.dumps({"ok": True, "result": tool_out}, ensure_ascii=False)
                    step_record["tool_calls"].append({
                        "tool": fname,
                        "arguments": args,
                        "result": tool_out,
                        "ok": True
                    })
                except Exception as ex:
                    content_str = json.dumps({"ok": False, "error": str(ex)})
                    step_record["tool_calls"].append({
                        "tool": fname,
                        "arguments": args,
                        "error": str(ex),
                        "ok": False
                    })
                    
                working_messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "content": content_str
                })
                
            _append_task_step(task_id, step_record)
            time.sleep(0.2)
            
        if not final_result and not error_msg:
            final_result = "Reached maximum execution steps. Summary of progress recorded in logs."
            
        if error_msg:
            _update_task(task_id, {
                "status": "failed",
                "error": error_msg,
                "completed_at": _now(),
                "progress": 100,
            })
        else:
            _update_task(task_id, {
                "status": "completed",
                "result": final_result,
                "completed_at": _now(),
                "progress": 100,
            })
            
    except Exception as exc:
        _update_task(task_id, {
            "status": "failed",
            "error": str(exc),
            "completed_at": _now(),
            "progress": 100,
        })
    finally:
        _active_threads.pop(task_id, None)
        _cancel_events.pop(task_id, None)


def dispatch_task(agent_id_or_name: str, goal: str, profile: str = "Hermes", context: str = "") -> dict:
    clean_goal = " ".join(str(goal or "").split()).strip()
    if not clean_goal:
        raise ValueError("Describe the goal for this agent task.")
        
    agent = Doshie_agents.get_agent(agent_id_or_name)
    if not agent:
        agent = Doshie_agents.get_agent_by_name(agent_id_or_name)
    if not agent:
        raise ValueError(f"Agent '{agent_id_or_name}' not found.")
    if not agent.get("enabled", True):
        raise ValueError(f"Agent '{agent.get('name')}' is currently disabled.")
        
    task_id = f"task-{uuid.uuid4().hex[:10]}"
    task_record = {
        "id": task_id,
        "agent_id": agent["id"],
        "agent_name": agent["name"],
        "agent_accent": agent.get("accent", "#35f2d0"),
        "agent_purpose": agent.get("purpose", ""),
        "goal": clean_goal,
        "profile": profile,
        "status": "queued",
        "progress": 0,
        "created_at": _now(),
        "started_at": None,
        "completed_at": None,
        "steps": [],
        "result": None,
        "error": None,
    }
    
    with _lock:
        tasks = _load_tasks_unlocked()
        tasks.insert(0, task_record)
        _save_tasks_unlocked(tasks)
        
    cancel_event = threading.Event()
    _cancel_events[task_id] = cancel_event
    
    thread = threading.Thread(
        target=_task_worker,
        args=(task_id, agent, clean_goal, profile, context, cancel_event),
        name=f"AgentTask-{task_id}",
        daemon=True
    )
    _active_threads[task_id] = thread
    thread.start()
    
    return task_record
