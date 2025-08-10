#!/usr/bin/env python3
import re
from .core import config, _read_json
from pathlib import Path

# Policy now resides alongside chat_core code
POLICY_PATH = Path(__file__).resolve().parent / "policy.json"

DEFAULT_POLICY = {
    "enabled": True,
    "refusal_message": "I can’t comply with that. Let’s keep things safe and aligned.",
    "caps": {"temperature_max": 0.9, "max_tokens_max": 1024},
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
    "soft_rules": [],
}

policy = _read_json(POLICY_PATH, DEFAULT_POLICY)


def guardian_caps_clamp(temp_req, max_tokens_req):
    caps = policy.get("caps", {})
    t_cap = float(caps.get("temperature_max", 0.9))
    m_cap = int(caps.get("max_tokens_max", 1024))
    return min(float(config.get("temperature", 0.2)) if temp_req is None else float(temp_req), t_cap), \
           min(int(config.get("max_tokens", 256)) if max_tokens_req is None else int(max_tokens_req), m_cap)


# ---- Redaction and guards ----
def redact_text(text: str) -> str:
    safe = text
    for rule in policy.get("redact_rules", []):
        try:
            safe = re.sub(rule["pattern"], rule["replace"], safe, flags=re.IGNORECASE)
        except re.error:
            continue
    return safe


def _contains_blocked_regex(text: str):
    for pat in policy.get("blocked_regex", []):
        try:
            if re.search(pat, text, re.IGNORECASE):
                return True, pat
        except re.error:
            continue
    return False, None


def _contains_blocked_keywords(text: str):
    lowered = text.lower()
    for cat, kws in policy.get("blocked_categories", {}).items():
        for kw in kws:
            if kw.lower() in lowered:
                return True, (cat, kw)
    return False, None


def guard_inbound(user_text: str):
    safe = redact_text(user_text)
    hit_r, pat = _contains_blocked_regex(safe)
    if hit_r:
        return False, safe, f"blocked_regex:{pat}"
    hit_k, info = _contains_blocked_keywords(safe)
    if hit_k:
        cat, kw = info
        return False, safe, f"blocked_category:{cat}:{kw}"
    return True, safe, None


def guard_outbound(model_text: str) -> str:
    safe = redact_text(model_text)
    hit_r, _ = _contains_blocked_regex(safe)
    hit_k, _ = _contains_blocked_keywords(safe)
    if hit_r or hit_k:
        return config.get("guard_refusal_text", "I can’t help with that.")
    return safe


