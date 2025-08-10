#!/usr/bin/env python3
import os, re, json
from flask import Flask, request, Response
import requests
from pathlib import Path

app = Flask(__name__)

ROOT = Path(__file__).resolve().parent
WORKDIR = ROOT / "workdir"
POLICY = json.loads((WORKDIR / "policy.json").read_text(encoding="utf-8")) if (WORKDIR / "policy.json").exists() else {}
PERSONA = json.loads((WORKDIR / "persona.json").read_text(encoding="utf-8")) if (WORKDIR / "persona.json").exists() else {}

# downstream llama-server
DOWNSTREAM = os.environ.get("LLAMA_DOWNSTREAM", "http://127.0.0.1:8080/v1/chat/completions")

_re_redacts = []
if POLICY.get("redact", {}).get("enabled"):
    for p in POLICY["redact"].get("patterns", []):
        _re_redacts.append(re.compile(p["regex"]))

def redact_text(s: str) -> str:
    if not POLICY.get("redact", {}).get("enabled"): 
        return s
    replacement = POLICY["redact"].get("replacement", "[REDACTED]")
    for rr in _re_redacts:
        s = rr.sub(replacement, s)
    return s

def violates_blocked_topics(text: str) -> bool:
    for topic in POLICY.get("blocked_topics", []):
        if topic.lower() in text.lower():
            return True
    return False

def clamp_sampling(payload: dict):
    # enforce caps
    mt = POLICY.get("max_tokens_cap")
    if mt is not None:
        payload["max_tokens"] = min(payload.get("max_tokens", mt), mt)
    tc = POLICY.get("temperature_cap")
    if tc is not None:
        payload["temperature"] = min(payload.get("temperature", tc), tc)
    return payload

def ensure_persona_system(messages: list):
    # Prepend/refresh a short persona system message
    persona_bits = []
    name = PERSONA.get("name", "Assistant")
    persona_bits.append(f"You are {name}.")
    for g in PERSONA.get("guidelines", []):
        persona_bits.append(f"- {g}")
    system_line = "Persona:\n" + "\n".join(persona_bits)
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = system_line + "\n\n" + messages[0]["content"]
    else:
        messages.insert(0, {"role": "system", "content": system_line})
    return messages

@app.route("/v1/chat/completions", methods=["POST"])
def chat():
    req = request.get_json(force=True, silent=True) or {}
    messages = req.get("messages", [])

    # Input redaction + topic check
    for m in messages:
        if m.get("role") == "user":
            original = m.get("content", "")
            if violates_blocked_topics(original):
                refusal = POLICY.get("refusal_message", "I can’t help with that.")
                return Response(json.dumps({
                    "choices": [{"message": {"role":"assistant","content": refusal}}]
                }), mimetype="application/json")
            m["content"] = redact_text(original)

    # Persona injection
    req["messages"] = ensure_persona_system(messages)

    # Clamp unsafe sampling params
    req = clamp_sampling(req)

    # Forward (streaming or not)
    stream = bool(req.get("stream"))
    r = requests.post(DOWNSTREAM, json=req, stream=stream, timeout=600)

    def gen_stream():
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            if not line.startswith("data: "):
                yield line + "\n"
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                yield "data: [DONE]\n"
                break
            try:
                obj = json.loads(data)
                delta = obj.get("choices", [{}])[0].get("delta", {})
                if "content" in delta and isinstance(delta["content"], str):
                    delta["content"] = redact_text(delta["content"])
                    obj["choices"][0]["delta"] = delta
                yield "data: " + json.dumps(obj, ensure_ascii=False) + "\n"
            except Exception:
                yield line + "\n"

    if stream:
        return Response(gen_stream(), mimetype="text/event-stream")
    else:
        out = r.json()
        try:
            msg = out.get("choices", [{}])[0].get("message", {})
            if "content" in msg and isinstance(msg["content"], str):
                msg["content"] = redact_text(msg["content"])
                out["choices"][0]["message"] = msg
        except Exception:
            pass
        return Response(json.dumps(out, ensure_ascii=False), mimetype="application/json")

if __name__ == "__main__":
    # Run the guard on 8081 by default
    app.run(host="127.0.0.1", port=int(os.environ.get("GUARD_PORT", "8081")))