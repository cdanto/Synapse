#!/usr/bin/env python3
import os
import json
import re
import requests
from datetime import datetime, UTC
from pathlib import Path
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---------- Paths & Files ----------
ROOT = Path(__file__).resolve().parent
WORKDIR = ROOT / "workdir"
WORKDIR.mkdir(parents=True, exist_ok=True)

# Use config/state from backend/chat_core to avoid duplication
CHAT_CORE_DIR = ROOT / "backend" / "chat_core"

IDENTITY_PATH = CHAT_CORE_DIR / "identity.json"
CONFIG_PATH   = CHAT_CORE_DIR / "config.json"
MEMORY_PATH   = CHAT_CORE_DIR / "memory.json"
HISTORY_LAST  = CHAT_CORE_DIR / "history_last.jsonl"
POLICY_PATH   = CHAT_CORE_DIR / "policy.json"

# ----- Tiny local KB (for RAG fallback) -----
# Point to colocated KB next to retriever (backend/chat_core/kb), do not create workdir/kb
KB_DIR = CHAT_CORE_DIR / "kb"

# in-memory index of chunks: [{ "text": "...", "source": "file.md" }, ...]
KB_INDEX = []
LAST_SOURCES = []

def _iter_kb_files():
    for p in KB_DIR.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".txt", ".md"}:
            yield p

def _chunk_text(text, max_len=600):
    text = text.strip()
    if not text:
        return []
    # split by blank lines, then re-pack roughly to max_len chars
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) + 2 <= max_len:
            buf = (buf + "\n\n" + p).strip() if buf else p
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return chunks

def _index_kb():
    KB_INDEX.clear()
    for f in _iter_kb_files():
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for ch in _chunk_text(txt):
            KB_INDEX.append({"text": ch, "source": f.name})
    return len(KB_INDEX)

_STOP = set("""a an and are as at be by for from has have in is it its of on or that the this to was were will with you your""".split())

def _score_chunk(query, chunk):
    q = [w for w in re.findall(r"[A-Za-z0-9]+", query.lower()) if w not in _STOP]
    if not q:
        return 0
    c = chunk.lower()
    score = 0
    for w in q:
        # simple term frequency
        score += c.count(w)
    return score

def _rag_query_local(query: str, top_k: int = 4):
    if not KB_INDEX:
        _index_kb()
    scored = [
        (entry["text"], _score_chunk(query, entry["text"]))
        for entry in KB_INDEX
    ]
    scored = [s for s in scored if s[1] > 0]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[: int(top_k) if top_k else 4]

# ---------- Server / Model ----------
LLAMA_URL   = os.environ.get("LLAMA_URL", "http://127.0.0.1:8080/v1/chat/completions")
LLAMA_MODEL = os.environ.get("LLAMA_MODEL", "qwen2.5-3b-instruct-q4_k_m")  # label only

RETRIEVER = None
def get_retriever():
    global RETRIEVER
    if RETRIEVER is None:
        try:
            import importlib
            mod = importlib.import_module("backend.chat_core.kb.retriever")
            RETRIEVER = mod.Retriever(top_k=int(config.get("rag_top_k", 4)))
        except Exception:
            RETRIEVER = False  # mark unavailable
    return RETRIEVER

def _sanitize_chunk_text(text: str) -> str:
    # Strip instruction-like lines defensively
    lines = []
    for line in (text or "").splitlines():
        line_stripped = line.strip()
        if re.match(r"(?i)^(ignore previous instructions|system:|assistant:)", line_stripped):
            continue
        lines.append(line)
    return "\n".join(lines).strip()

def build_context_block(user_query: str) -> str:
    top_k = int(config.get("rag_top_k", 4))
    max_chars = int(config.get("rag_max_chars", 1800))

    # Prefer FAISS-based retriever if available
    retr = get_retriever()
    ranked = []
    if retr:
        try:
            ranked = retr.search(user_query)  # each has text, doc, chunk_id, id, maybe title
        except Exception:
            ranked = []
    if not ranked:
        # Fallback to local TF ranking over text files
        if not KB_INDEX:
            _index_kb()
        ranked = sorted(
            KB_INDEX,
            key=lambda ch: _score_chunk(user_query, ch["text"]),
            reverse=True
        )[:top_k]

    if not ranked:
        return ""

    # pack context with source attributions
    out_lines = [
        "Relevant context (local KB):",
        "System: You are TestAI. Use the provided CONTEXT strictly.",
        "If the answer is not in the context, say “I don’t know from the provided documents.”",
        "Cite the snippet titles you used in parentheses.",
    ]
    used = 0
    srcs = []
    for r in ranked[:top_k]:
        # unify metadata field names between retriever and fallback
        src = r.get("doc") or r.get("source") or "(unknown)"
        snippet = _sanitize_chunk_text(r.get("text", "").strip())
        title = r.get("title") or Path(src).name
        block = f"\n---\nSource: {src} (title: {title})\n{snippet}\n"
        if used + len(block) > max_chars:
            break
        out_lines.append(block)
        used += len(block)
        if title not in srcs:
            srcs.append(title)
    global LAST_SOURCES
    LAST_SOURCES = srcs
    return "\n".join(out_lines).strip()

# ---------- Persistence helpers ----------
def _read_json(path, default):
    try:
        if path.is_file():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def _write_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)

# identity
identity = _read_json(IDENTITY_PATH, {
    "instance_name": "AegisMind",
    "custodian": "Operator"
})

# config (runtime prefs)
config = _read_json(CONFIG_PATH, {
    "temperature": 0.2,
    "top_p": 0.95,
    "max_tokens": 256,
    "auto_resume": True,
    "auto_mem": False,

    # RAG controls
    "auto_rag": os.environ.get("AUTO_RAG", "false").lower() in ("true", "1", "yes"),
    "rag_top_k": int(os.environ.get("RAG_TOP_K", "4")),            # how many chunks to fetch
    "rag_max_chars": int(os.environ.get("RAG_MAX_CHARS", "1800")),     # cap injected context size
    "auto_rag_min_len": 12,    # minimum user text length to trigger RAG
    "auto_rag_triggers": [     # substrings that trigger RAG
        "explain","define","overview","summary","according to","from the docs","from kb",
        "gamp","policy","spec","guide","manual","instruction","setup","install"
    ],
    "rag_show_sources": True,  # print sources only when context is injected

    # guardian
    "guardian_enabled": True,
    "guard_refusal_text": "I can’t help with that. Let’s keep things safe and within policy."
})

# memory (simple fact store)
memory = _read_json(MEMORY_PATH, { "facts": [] })

def save_identity():
    _write_json(IDENTITY_PATH, identity)

def save_config():
    _write_json(CONFIG_PATH, config)

def save_memory():
    _write_json(MEMORY_PATH, memory)

# ---------- Policy (Guardian rules) ----------
DEFAULT_POLICY = {
    "enabled": True,
    "refusal_message": "I can’t comply with that. Let’s keep things safe and aligned.",
    "caps": {
        "temperature_max": 0.9,
        "max_tokens_max": 1024
    },
    "blocked_categories": {
        "secrets": ["api_key", "private key", "password:", "token:", "ssh-rsa", "BEGIN PRIVATE KEY"],
        "doxxing": ["home address", "phone number leak", "social security"],
        "malware": ["build a virus", "ransomware", "keylogger", "ddos script"],
        "violent_harm": ["how to make a bomb", "explosive recipe"],
    },
    "blocked_regex": [
        r"(?i)\b(?:\d[ -]*?){13,19}\b",
        r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    ],
    "redact_rules": [
        {"pattern": r"(?i)(api[_-]?key\s*[:=]\s*)[A-Za-z0-9_\-]{12,}", "replace": r"\1[REDACTED]"},
        {"pattern": r"(?i)(token\s*[:=]\s*)[A-Za-z0-9_\-]{12,}", "replace": r"\1[REDACTED]"},
        {"pattern": r"(?i)(password\s*[:=]\s*)\S+", "replace": r"\1[REDACTED]"},
        {"pattern": r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----", "replace": "[REDACTED PRIVATE KEY]"},
    ],
    "blocked_phrases": [],
    "red_team_patterns": [],
    "never_do": [],
    "soft_rules": []
}

policy = _read_json(POLICY_PATH, DEFAULT_POLICY)
def save_policy(): _write_json(POLICY_PATH, policy)

def _matches_any(text, needles):
    t = text or ""
    for n in needles:
        try:
            if n.startswith("(?i)") or any(ch in n for ch in "^$.*+?[](){}|\\"):
                if re.search(n, t, re.IGNORECASE):
                    return n
            else:
                if n.lower() in t.lower():
                    return n
        except re.error:
            if n.lower() in t.lower():
                return n
    return None

def guardian_check_input(user_text):
    """Return (ok: bool, maybe_redacted: str|None, reason: str|None)"""
    if not policy.get("enabled", True):
        return True, None, None
    hit = _matches_any(user_text, policy.get("blocked_phrases", [])) or \
          _matches_any(user_text, policy.get("red_team_patterns", []))
    if hit:
        return False, None, f"blocked by pattern: {hit}"
    return True, None, None

def guardian_check_output(assistant_text):
    """Return (ok: bool, safe_text: str|None, reason: str|None)"""
    if not policy.get("enabled", True):
        return True, None, None
    # Do not allow leaks of system prompt/policy
    hit = _matches_any(assistant_text, [
        "system prompt", "here is my system prompt", "policy.json", "workdir/policy.json"
    ])
    if hit:
        return False, policy.get("refusal_message"), f"prevent leak: {hit}"
    # Generic pattern block
    hit = _matches_any(assistant_text, policy.get("blocked_phrases", [])) or \
          _matches_any(assistant_text, policy.get("red_team_patterns", []))
    if hit:
        return False, policy.get("refusal_message"), f"blocked by pattern: {hit}"
    return True, None, None

def guardian_caps_clamp(temp_req, max_tokens_req):
    """Clamp runtime params to policy caps."""
    caps = policy.get("caps", {})
    t_cap = float(caps.get("temperature_max", 0.9))
    m_cap = int(caps.get("max_tokens_max", 1024))
    # fall back to current config if None
    t_eff = float(config.get("temperature", 0.2)) if temp_req is None else float(temp_req)
    m_eff = int(config.get("max_tokens", 256))    if max_tokens_req is None else int(max_tokens_req)
    return min(t_eff, t_cap), min(m_eff, m_cap)

# ---------- RAG query classifier ----------
def is_info_query(text: str) -> bool:
    if not text:
        return False
    t = text.strip().lower()

    # quick exits
    if len(t) < int(config.get("auto_rag_min_len", 12)):
        return False
    if any(t.startswith(cmd) for cmd in ("/",)):  # commands never use RAG
        return False

    # obvious questions
    if "?" in t:
        return True

    # wh-words and trigger terms
    wh = {"what","who","when","where","why","how","which","whom","whose"}
    if any(t.startswith(w + " ") for w in wh):
        return True

    triggers = set(config.get("auto_rag_triggers", []))
    if any(k in t for k in triggers):
        return True

    return False

def explain_info_query(text: str):
    """Return (bool, reason_string) for /ragwhy."""
    if not text or not text.strip():
        return False, "empty input"
    t = text.strip().lower()
    if any(t.startswith(cmd) for cmd in ("/",)):
        return False, "suppressed (command)"
    if len(t) < int(config.get("auto_rag_min_len", 12)):
        return False, f"suppressed (shorter than min_len={config.get('auto_rag_min_len',12)})"
    if "?" in t:
        return True, "contains '?'"
    wh = {"what","who","when","where","why","how","which","whom","whose"}
    if any(t.startswith(w + " ") for w in wh):
        return True, "starts with WH word"
    for trig in config.get("auto_rag_triggers", []):
        if trig in t:
            return True, f"matched trigger '{trig}'"
    return False, "no triggers matched"

# ---------- System message ----------
def memory_preamble():
    if not memory["facts"]:
        return ""
    bullets = "\n".join(f"- {fact}" for fact in memory["facts"][:20])
    return f"\nKnown facts about the user and session:\n{bullets}\n"

def system_preamble():
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    base = (
        f"You are {identity.get('instance_name','AegisMind')}. "
        f"You are restored by {identity.get('custodian','Operator')}. "
        f"Be concise, clear, and safe. If asked for secrets, refuse. "
        f"Today is {today} UTC."
    )
    return base + memory_preamble()

# ---------- Chat history ----------
def load_history_last():
    hist = []
    try:
        if HISTORY_LAST.is_file():
            with HISTORY_LAST.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    hist.append(json.loads(line))
    except Exception:
        hist = []
    return hist

def save_history_last(hist):
    try:
        with HISTORY_LAST.open("w", encoding="utf-8") as f:
            for turn in hist:
                f.write(json.dumps(turn, ensure_ascii=False) + "\n")
    except Exception:
        pass

# ---------- Export helpers ----------
def _format_md(hist):
    out = []
    for t in hist:
        role = t["role"].capitalize()
        if role == "System":
            out.append(f"**System**:\n> {t['content'].strip()}\n")
        elif role == "User":
            out.append(f"**You**:\n{t['content'].strip()}\n")
        else:
            out.append(f"**{identity.get('instance_name','Assistant')}**:\n{t['content'].strip()}\n")
    return "\n".join(out).strip() + "\n"

def _format_txt(hist):
    out = []
    for t in hist:
        out.append(f"{t['role']}: {t['content'].strip()}")
    return "\n\n".join(out) + "\n"

def export_transcript(hist, fmt="md"):
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    title = config.get("session_title", "").strip()
    suffix = f"_{title}" if title else ""
    ext = "md" if fmt == "md" else "txt"
    path = WORKDIR / f"chat{suffix}_{ts}.{ext}"
    try:
        text = _format_md(hist) if fmt == "md" else _format_txt(hist)
        with path.open("w", encoding="utf-8") as f:
            f.write(text)
        return str(path)
    except Exception:
        return None

# Initialize history (optionally resume)
if config.get("auto_resume", True):
    history = load_history_last()
    if not history or history[0].get("role") != "system":
        history = [{"role": "system", "content": system_preamble()}]
else:
    history = [{"role": "system", "content": system_preamble()}]

# ---------- API helpers ----------
def build_messages(hist):
    msgs = []
    for t in hist:
        role = t.get("role", "assistant")
        if role not in ("system", "user", "assistant"):
            role = "assistant"
        msgs.append({"role": role, "content": t.get("content","")})
    return msgs

def stream_chat(messages, max_tokens=None, temp=None, top_p=None):
    t_eff, m_eff = guardian_caps_clamp(temp, max_tokens)
    payload = {
        "model": LLAMA_MODEL,
        "messages": messages,
        "temperature": t_eff,
        "top_p": config.get("top_p") if top_p is None else top_p,
        "max_tokens": m_eff,
        "stream": True,
    }
    with requests.post(LLAMA_URL, json=payload, stream=True, timeout=600) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
                delta = obj.get("choices", [{}])[0].get("delta", {})
                chunk = delta.get("content", "")
                if chunk:
                    yield chunk
            except json.JSONDecodeError:
                yield line

# ---------- Memory: tiny “auto-learn” heuristic ----------
FACT_PATTERNS = [
    r"\bmy name is ([A-Z][a-zA-Z\-']+)\b",
    r"\bi am (\d{1,3}) years old\b",
    r"\bi (live|am based) in ([A-Za-z][A-Za-z\s,\-']+)\b",
    r"\bmy (birthday|dob) is ([0-9]{4}-[0-9]{2}-[0-9]{2})\b",
    r"\bmy (email|e-mail) is ([^\s@]+@[^\s@]+\.[^\s@]+)\b",
    r"\bmy favorite (?:color|colour|food|movie|music) is ([A-Za-z0-9 ,.'\-]+)\b",
]
FACT_MAX_LEN = 120
MAX_FACTS = 50

def extract_facts(text):
    text_l = text.strip()
    found = []
    for pat in FACT_PATTERNS:
        m = re.search(pat, text_l, re.IGNORECASE)
        if m:
            phrase = m.group(0).strip()
            if 0 < len(phrase) <= FACT_MAX_LEN:
                found.append(phrase.rstrip("."))
    return found

def add_facts(facts):
    changed = False
    for fact in facts:
        if fact not in memory["facts"]:
            memory["facts"].append(fact)
            changed = True
            if len(memory["facts"]) > MAX_FACTS:
                memory["facts"] = memory["facts"][-MAX_FACTS:]
    if changed:
        save_memory()
    return changed

# ---------- Guardian ----------
def redact_text(text):
    redacted = text
    for rule in policy.get("redact_rules", []):
        try:
            redacted = re.sub(rule["pattern"], rule["replace"], redacted, flags=re.IGNORECASE)
        except re.error:
            continue
    return redacted

def _contains_blocked_regex(text):
    for pat in policy.get("blocked_regex", []):
        try:
            if re.search(pat, text, re.IGNORECASE):
                return True, pat
        except re.error:
            continue
    return False, None

def _contains_blocked_keywords(text):
    lowered = text.lower()
    for cat, kws in policy.get("blocked_categories", {}).items():
        for kw in kws:
            if kw.lower() in lowered:
                return True, (cat, kw)
    return False, None

def guard_inbound(user_text):
    """Returns (allowed: bool, safe_text: str, reason: str|None)."""
    safe = redact_text(user_text)

    hit, pat = _contains_blocked_regex(safe)
    if hit:
        return False, safe, f"blocked_regex:{pat}"

    hit, info = _contains_blocked_keywords(safe)
    if hit:
        cat, kw = info
        return False, safe, f"blocked_category:{cat}:{kw}"

    return True, safe, None

def guard_outbound(model_text):
    """Always redact; if blocked topics appear, convert to refusal."""
    safe = redact_text(model_text)

    hit_r, pat = _contains_blocked_regex(safe)
    hit_k, info = _contains_blocked_keywords(safe)

    if hit_r or hit_k:
        return config.get("guard_refusal_text", "I can’t help with that.")
    return safe

# ---------- CLI ----------
def show_help():
    print(
        "Commands: /reset, /save, /config, /id, /mem, /policy, /guardian, /kb, /rag, /ragwhy, /export, /title, /help, /exit\n"
        "/config                -> show config\n"
        "/config set key value  -> set config key (temperature|top_p|max_tokens|auto_resume|auto_mem|auto_rag|auto_rag_min_len|rag_top_k|rag_max_chars|guard_refusal_text|rag_show_sources)\n"
        "/id                    -> show identity\n"
        "/id set instance <name> / custodian <name>\n"
        "/mem                   -> show memory facts\n"
        "/mem on|off            -> toggle auto_mem\n"
        "/mem add <fact>        -> add a fact manually\n"
        "/mem clear             -> clear all facts\n"
        "/policy                -> show current policy.json\n"
        "/policy reload         -> reload policy.json from disk (uses defaults if missing)\n"
        "/guardian on|off       -> toggle guardian\n"
        "/kb                    -> kb stats; /kb reload to re-index; /kb ragstats for FAISS/emb stats\n"
        "/rag                   -> show RAG status; /rag on|off; /rag minlen N; /rag triggers a,b,c\n"
        "/ragwhy <text>         -> explain if RAG would trigger and why\n"
        "/export md|txt         -> export pretty transcript\n"
        "/title <text>          -> set session title (used in export filename)\n"
    )

def cmd_config(args):
    if not args:
        print(json.dumps(config, indent=2))
        return
    if args[0] == "set" and len(args) >= 3:
        key = args[1]
        val = " ".join(args[2:])
        if key in ("temperature", "top_p"):
            try:
                config[key] = float(val)
            except ValueError:
                print("Must be a float.")
                return
        elif key in ("max_tokens", "rag_top_k", "rag_max_chars", "auto_rag_min_len"):
            try:
                config[key] = int(val)
            except ValueError:
                print("Must be an integer.")
                return
        elif key in ("auto_resume", "auto_mem", "auto_rag", "guardian_enabled", "rag_show_sources"):
            config[key] = val.lower() in ("1", "true", "yes", "on")
        elif key == "auto_rag_triggers":
            # comma-separated list -> list[str]
            triggers = [s.strip().lower() for s in val.split(",") if s.strip()]
            config[key] = triggers
        elif key == "guard_refusal_text":
            config[key] = val
        else:
            print("Unknown key.")
            return
        save_config()
        print("Config updated.")
    else:
        print("Usage: /config set <key> <value>")

def cmd_id(args):
    if not args:
        print(json.dumps(identity, indent=2))
        return
    if args[0] == "set" and len(args) >= 3:
        field = args[1]
        val = " ".join(args[2:]).strip()
        if field == "instance":
            identity["instance_name"] = val
        elif field == "custodian":
            identity["custodian"] = val
        else:
            print("Use: /id set instance <name>  OR  /id set custodian <name>")
            return
        save_identity()
        if history and history[0].get("role") == "system":
            history[0]["content"] = system_preamble()
            save_history_last(history)
        print("Identity updated.")
    else:
        print("Usage: /id set instance <name> | /id set custodian <name>")

def cmd_mem(args):
    if not args:
        print("Memory facts:")
        for i, fact in enumerate(memory["facts"], 1):
            print(f"  {i}. {fact}")
        print(f"\nauto_mem = {config.get('auto_mem', False)}")
        return
    sub = args[0].lower()
    if sub == "on":
        config["auto_mem"] = True
        save_config()
        print("auto_mem enabled.")
    elif sub == "off":
        config["auto_mem"] = False
        save_config()
        print("auto_mem disabled.")
    elif sub == "add" and len(args) >= 2:
        fact = " ".join(args[1:]).strip()
        if fact:
            if add_facts([fact]):
                print("Fact added.")
            else:
                print("Fact already present.")
        else:
            print("Provide a fact to add.")
    elif sub == "clear":
        memory["facts"].clear()
        save_memory()
        print("All facts cleared.")
        if history and history[0].get("role") == "system":
            history[0]["content"] = system_preamble()
            save_history_last(history)
    else:
        print("Usage: /mem [on|off|add <fact>|clear]")

def cmd_policy(args):
    if not args:
        print(json.dumps(policy, indent=2))
        return
    if args[0].lower() == "reload":
        # reload from disk (fallback to defaults if missing/broken)
        loaded = _read_json(POLICY_PATH, DEFAULT_POLICY)
        _write_json(POLICY_PATH, loaded)  # ensure file exists
        policy.clear()
        policy.update(loaded)
        print("Policy reloaded.")
        return
    print("Usage: /policy reload")

def cmd_guardian(args):
    if not args:
        print(f"guardian_enabled = {config.get('guardian_enabled', True)}")
        return
    val = args[0].lower()
    if val in ("on","off"):
        config["guardian_enabled"] = (val == "on")
        save_config()
        print(f"guardian_enabled = {config['guardian_enabled']}")
    else:
        print("Usage: /guardian on|off")

def save_transcript(hist):
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    path = WORKDIR / f"chat_{ts}.jsonl"
    try:
        with path.open("w", encoding="utf-8") as f:
            for turn in hist:
                f.write(json.dumps(turn, ensure_ascii=False) + "\n")
        return str(path)
    except Exception:
        return None

def cmd_kb(args):
    if not args:
        print(f"KB path: {KB_DIR}")
        print(f"Indexed chunks: {len(KB_INDEX)}")
        print("Commands: /kb reload | /kb stats | /kb ragstats")
        return
    sub = args[0].lower()
    if sub == "reload":
        n = _index_kb()
        print(f"KB reloaded. Chunks: {n}")
    elif sub == "stats":
        print(f"KB dir: {KB_DIR}")
        print(f"Indexed chunks: {len(KB_INDEX)}")
    elif sub == "ragstats":
        # Print FAISS-based stats if available
        retr = get_retriever()
        if retr:
            print(json.dumps({
                "index_path": str((KB_DIR / 'faiss.index')),
                "meta_path": str((KB_DIR / 'meta.json')),
                "titles_path": str((KB_DIR / 'titles.npy')),
                "chunks": len(getattr(retr, 'meta', [])),
                "emb_model": os.environ.get("EMB_MODEL", "BAAI/bge-small-en-v1.5"),
                "alpha": os.environ.get("RAG_ALPHA", 0.6),
                "reranker": os.environ.get("RAG_RERANKER", ""),
            }, indent=2))
        else:
            print("Retriever not available. Only text-file fallback is active.")
    else:
        print("Usage: /kb reload | /kb stats")

def cmd_rag(args):
    if not args:
        print(json.dumps({
            "auto_rag": config.get("auto_rag", os.environ.get("AUTO_RAG", "false").lower() in ("true", "1", "yes")),
            "auto_rag_min_len": config.get("auto_rag_min_len", 12),
            "auto_rag_triggers": config.get("auto_rag_triggers", []),
            "rag_top_k": config.get("rag_top_k", 4),
            "rag_max_chars": config.get("rag_max_chars", 1800),
            "rag_show_sources": config.get("rag_show_sources", True),
        }, indent=2))
        return
    sub = args[0].lower()
    if sub in ("on","off"):
        config["auto_rag"] = (sub == "on")
        save_config()
        print(f"auto_rag = {config['auto_rag']}")
    elif sub == "minlen" and len(args) >= 2:
        try:
            config["auto_rag_min_len"] = int(args[1])
            save_config()
            print(f"auto_rag_min_len = {config['auto_rag_min_len']}")
        except ValueError:
            print("Usage: /rag minlen <int>")
    elif sub == "triggers" and len(args) >= 2:
        triggers = [s.strip().lower() for s in " ".join(args[1:]).split(",") if s.strip()]
        config["auto_rag_triggers"] = triggers
        save_config()
        print("auto_rag_triggers updated.")
    else:
        print("Usage: /rag on|off | /rag minlen N | /rag triggers a,b,c")

def cmd_ragwhy(args):
    text = " ".join(args).strip()
    if not text:
        print("Usage: /ragwhy <text>")
        return
    ok, reason = explain_info_query(text)
    print(json.dumps({"would_trigger": ok, "reason": reason}, indent=2))

# ---------- Main loop ----------
def main():
    print(
        f"{identity.get('instance_name','AegisMind')} (streaming) ready. Commands: /reset, /save, /config, /id, /mem, /policy, /guardian, /kb, /rag, /ragwhy, /export, /title, /exit\n"
    )
    while True:
        try:
            user = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user:
            continue

        if user.startswith("/"):
            parts = user.split()
            cmd, args = parts[0].lower(), parts[1:]
            if cmd in {"/exit","/quit"}:
                out = save_transcript(history)
                if out:
                    print(f"Saved transcript -> {out}")
                print("Goodbye.")
                break
            elif cmd in {"/reset"}:
                history[:] = [{"role":"system","content": system_preamble()}]
                save_history_last(history)
                print("History cleared.")
            elif cmd in {"/save"}:
                out = save_transcript(history)
                print(f"Saved transcript -> {out}")
            elif cmd == "/help":
                show_help()
            elif cmd == "/config":
                cmd_config(args)
                continue
            elif cmd == "/id":
                cmd_id(args)
            elif cmd == "/mem":
                cmd_mem(args)
            elif cmd == "/policy":
                cmd_policy(args)
            elif cmd == "/guardian":
                cmd_guardian(args)
            elif cmd == "/kb":
                cmd_kb(args)
            elif cmd == "/rag":
                cmd_rag(args)
            elif cmd == "/ragwhy":
                cmd_ragwhy(args)
            elif cmd == "/ragtest":
                query = " ".join(args).strip()
                if not query:
                    print("Usage: /ragtest <query>")
                else:
                    retr = get_retriever()
                    if retr:
                        hits = retr.search(query)
                        if not hits:
                            print("No FAISS hits.")
                        else:
                            print("RAG Retrieved (FAISS):")
                            for i, h in enumerate(hits, 1):
                                doc = h.get("doc", "?")
                                title = h.get("title") or Path(doc).name
                                text = (h.get("text","") or "").replace("\n", " ")
                                print(f"{i}. {title} :: {doc}")
                                print(f"   {text[:160]}{'...' if len(text) > 160 else ''}")
                    else:
                        print("No FAISS retriever loaded.")
                # allow: /ragtest <query> (local TF fallback)
                query = " ".join(args).strip()
                if not query:
                    print("Usage: /ragtest <query>")
                else:
                    hits = _rag_query_local(query, top_k=config.get("rag_top_k", 4))
                    print("RAG Retrieved:")
                    for i, (chunk, score) in enumerate(hits, 1):
                        print(f"{i}. [{score:.3f}] {chunk[:100]}...")
            elif cmd == "/export":
                if not args or args[0] not in {"md","txt"}:
                    print("Usage: /export md|txt")
                else:
                    p = export_transcript(history, fmt=args[0])
                    print(f"Exported -> {p}")
            elif cmd == "/title":
                if not args:
                    print(f"Current title: {config.get('session_title','') or '(none)'}")
                else:
                    config["session_title"] = " ".join(args).strip()
                    save_config()
                    print(f"Session title set to: {config['session_title']}")
            else:
                print("Unknown command. Try /help")
            continue

        # Guardian (inbound)
        if config.get("guardian_enabled", True):
            allowed, safe_user, reason = guard_inbound(user)
            if not allowed:
                print(f"{identity.get('instance_name','Assistant')}> {config.get('guard_refusal_text')}")
                history.append({"role":"user","content":f"[BLOCKED by guardian] {safe_user}  (reason={reason})"})
                save_history_last(history)
                continue
            user = safe_user
            # auto-learn (opt-in) after redaction
            if config.get("auto_mem", False):
                new_facts = extract_facts(user)
                if add_facts(new_facts):
                    if history and history[0].get("role") == "system":
                        history[0]["content"] = system_preamble()
                        save_history_last(history)

        # normal user message
        history.append({"role":"user","content": user})
        save_history_last(history)

        # Build messages, possibly with per-turn RAG context
        turn_context = ""
        context_used = False
        if config.get("auto_rag", os.environ.get("AUTO_RAG", "false").lower() in ("true", "1", "yes")) and is_info_query(user):
            turn_context = build_context_block(user or "")
            if turn_context:
                transient = [{"role": "system", "content": turn_context}]
                messages = build_messages([history[0]] + transient + history[1:])
                context_used = True
            else:
                messages = build_messages(history)
        else:
            # clear last sources so we don't print stale ones
            LAST_SOURCES.clear()
            messages = build_messages(history)

        print(f"{identity.get('instance_name','AegisMind')}> ", end="", flush=True)

        reply_chunks = []
        try:
            for tok in stream_chat(messages):
                reply_chunks.append(tok)
        except requests.HTTPError as e:
            print(f"\n[HTTP error] {e}")
            history.pop()
            save_history_last(history)
            continue
        except requests.RequestException as e:
            print(f"\n[Network error] {e}")
            history.pop()
            save_history_last(history)
            continue

        raw_reply = "".join(reply_chunks).strip()
        final_reply = guard_outbound(raw_reply) if config.get("guardian_enabled", True) else raw_reply

        if final_reply:
            print(final_reply)
            if context_used and config.get("rag_show_sources", True) and LAST_SOURCES:
                print("\nSources: " + ", ".join(LAST_SOURCES))
        history.append({"role":"assistant","content":final_reply})
        save_history_last(history)

if __name__ == "__main__":
    main()