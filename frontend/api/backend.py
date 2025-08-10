# frontend/api/backend.py
from __future__ import annotations

import json
from typing import Dict, Iterable, List, Optional

import requests


class BackendError(RuntimeError):
    pass


class BackendClient:
    """
    Thin client for your FastAPI backend.

    Expected endpoints:
      - POST /chat/stream         -> text/event-stream (SSE). Body: {"messages":[...], "params": {...}}
      - GET  /config              -> returns current config JSON
      - POST /config              -> accepts partial config JSON to update
      - GET  /rag/preview?q=...   -> returns {"context": "...", "sources":[...]} (optional "preview")
      - POST /kb/reload           -> rebuild KB index
      - GET  /kb/stats            -> KB stats
      - POST /kb/upload           -> multipart file upload
    """

    def __init__(self, base_url: str = "http://127.0.0.1:9000", *, timeout: int = 600, auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth_token = auth_token

    # ---------- helpers ----------
    def _url(self, path: str) -> str:
        path = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{path}"

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.auth_token:
            h["Authorization"] = f"Bearer {self.auth_token}"
        return h

    # ---------- config ----------
    def get_config(self) -> Dict:
        r = requests.get(self._url("/config"), headers=self._headers(), timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError(f"GET /config failed: {r.status_code} {r.text}")
        return r.json()

    def update_config(self, patch: Dict) -> Dict:
        r = requests.post(self._url("/config"), headers={**self._headers(), "Content-Type": "application/json"}, data=json.dumps(patch), timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError(f"POST /config failed: {r.status_code} {r.text}")
        return r.json()

    # ---------- chat (SSE streaming) ----------
    def chat_stream(
        self,
        messages: List[Dict],
        *,
        temperature: float = 0.7,
        top_p: float = 0.95,
        max_tokens: int = 512,
        auto_rag: bool = True,  # Default to True, will be overridden by backend if needed
    ) -> Iterable[Dict]:
        """
        Yields dict events:
           {"delta": "<text>"}  or  {"done": true, "sources": [...]}
        Falls back to non-streaming /chat if /chat/stream not available.
        """
        payload = {
            "messages": messages,
            "temperature": float(temperature),
            "top_p": float(top_p),
            "max_tokens": int(max_tokens),
            "auto_rag": bool(auto_rag),
        }

        # Try SSE first
        try:
            with requests.post(
                self._url("/chat/stream"),
                headers={**self._headers(), "Accept": "text/event-stream", "Content-Type": "application/json"},
                data=json.dumps(payload),
                stream=True,
                timeout=self.timeout,
            ) as r:
                if r.status_code == 404:
                    raise FileNotFoundError  # fall back below
                r.raise_for_status()
                buffer = ""
                for raw in r.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    # SSE: lines like "data: {...}"
                    if raw.startswith("data:"):
                        data = raw[5:].strip()
                        if data == "[DONE]":
                            yield {"done": True, "sources": []}
                            break
                        try:
                            evt = json.loads(data)
                        except json.JSONDecodeError:
                            # tolerate partials (rare)
                            buffer += data
                            try:
                                evt = json.loads(buffer)
                                buffer = ""
                            except json.JSONDecodeError:
                                continue
                        # normalize
                        if "delta" in evt:
                            yield {"delta": evt["delta"]}
                        elif evt.get("done"):
                            yield {"done": True, "sources": evt.get("sources", [])}
                        else:
                            # best-effort
                            if "content" in evt:
                                yield {"delta": evt["content"]}
                return
        except FileNotFoundError:
            pass  # fall back
        except requests.RequestException as e:
            # fall back to non-streaming if server returns JSON error
            pass

        # Fallback: non-streaming /chat
        r = requests.post(
            self._url("/chat"),
            headers={**self._headers(), "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=self.timeout,
        )
        if r.status_code >= 400:
            raise BackendError(f"POST /chat failed: {r.status_code} {r.text}")
        obj = r.json()
        text = obj.get("reply") or obj.get("content") or ""
        sources = obj.get("sources", [])
        # Emit one big delta + done
        if text:
            yield {"delta": text}
        yield {"done": True, "sources": sources}

    # ---------- RAG ----------
    def rag_preview(self, q: str) -> Dict:
        r = requests.get(self._url("/rag/preview"), params={"q": q}, headers=self._headers(), timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError(f"GET /rag/preview failed: {r.status_code} {r.text}")
        return r.json()

    # ---------- KB ----------
    def kb_reload(self) -> Dict:
        r = requests.post(self._url("/kb/reload"), headers=self._headers(), timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError(f"POST /kb/reload failed: {r.status_code} {r.text}")
        return r.json()

    def get_kb_stats(self) -> Dict:
        r = requests.get(self._url("/kb/stats"), headers=self._headers(), timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError(f"GET /kb/stats failed: {r.status_code} {r.text}")
        return r.json()

    def kb_upload(self, files_payload: List[tuple]) -> Dict:
        """
        files_payload format: [("files", bytes, mime, filename), ...]
        Backend should accept "files" as multiple form parts.
        """
        files = []
        try:
            for _field, content, mime, fname in files_payload:
                files.append(("files", (fname, content, mime)))
            r = requests.post(self._url("/kb/upload"), files=files, headers=self._headers(), timeout=self.timeout)
            if r.status_code >= 400:
                raise BackendError(f"POST /kb/upload failed: {r.status_code} {r.text}")
            return r.json()
        finally:
            for _, f in files:
                try:
                    f[0].close()  # content as bytes -> nothing to close, keep safe
                except Exception:
                    pass

    # ---------- RAG Control ----------
    def toggle_rag(self) -> Dict:
        """Toggle RAG on/off and persist to environment"""
        r = requests.post(self._url("/rag/toggle"), headers=self._headers(), timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError(f"POST /rag/toggle failed: {r.status_code} {r.text}")
        return r.json()

    def set_rag_state(self, auto_rag: bool) -> Dict:
        """Set RAG to specific state and persist to environment"""
        payload = {"auto_rag": auto_rag}
        r = requests.post(self._url("/rag/set"), json=payload, headers=self._headers(), timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError(f"POST /rag/set failed: {r.status_code} {r.text}")
        return r.json()

    # ---------- Guardian Control ----------
    def toggle_guardian(self) -> Dict:
        """Toggle Guardian on/off and persist to environment"""
        r = requests.post(self._url("/guardian/toggle"), headers=self._headers(), timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError(f"POST /guardian/toggle failed: {r.status_code} {r.text}")
        return r.json()

    def set_guardian_state(self, guardian_enabled: bool) -> Dict:
        """Set Guardian to specific state and persist to environment"""
        payload = {"guardian_enabled": guardian_enabled}
        r = requests.post(self._url("/guardian/set"), json=payload, headers=self._headers(), timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError(f"POST /guardian/set failed: {r.status_code} {r.text}")
        return r.json()

    def clear_knowledge_base(self) -> Dict:
        """Clear the knowledge base - remove all indexed documents"""
        r = requests.post(self._url("/kb/clear"), headers=self._headers(), timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError(f"POST /kb/clear failed: {r.status_code} {r.text}")
        return r.json()

    def clear_chat_history(self) -> Dict:
        """Clear the chat history - remove conversation context"""
        r = requests.post(self._url("/chat/clear"), headers=self._headers(), timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError(f"POST /chat/clear failed: {r.status_code} {r.text}")
        return r.json()