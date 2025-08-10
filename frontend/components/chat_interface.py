# frontend/components/chat_interface.py
"""
Chat interface components for Synapse
- Solid ChatGPT-like bubbles using st.chat_message()
- Fast streaming (single placeholder, minimal re-render)
- Safe markdown formatting
- Compact, readable RAG source previews
"""
from __future__ import annotations

from typing import List, Dict, Any, Iterable, Optional, Tuple
from datetime import datetime
import html
import re

import streamlit as st


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def _now_iso() -> str:
    return datetime.now().isoformat()

def _format_rel_time(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt.replace(tzinfo=None) if dt.tzinfo is None else now - dt
        if diff.days > 0:
            return f"{diff.days}d ago"
        secs = diff.seconds
        if secs >= 3600:
            return f"{secs // 3600}h ago"
        if secs >= 60:
            return f"{secs // 60}m ago"
        return "Just now"
    except Exception:
        return "Now"

_md_codeblock = re.compile(r"```(\w+)?\n(.*?)\n```", re.DOTALL)
_md_inlinecode = re.compile(r"`([^`]+)`")
_md_bold = re.compile(r"\*\*(.*?)\*\*")
_md_italic = re.compile(r"(?<!\*)\*(?!\*)(.*?)\*(?<!\*)")

def _markdown_to_html_safe(md: str) -> str:
    """Very light md -> HTML; rely mostly on Streamlit's markdown.
    Here we only ensure weird HTML doesn't escape the box."""
    if not md:
        return ""

    # escape raw HTML to avoid breaking layout
    md = html.escape(md)

    # restore common markdown affordances
    md = _md_codeblock.sub(lambda m: f'<div class="code-block"><code>{m.group(2)}</code></div>', md)
    md = _md_inlinecode.sub(lambda m: f'<code class="inline-code">{m.group(1)}</code>', md)
    md = _md_bold.sub(lambda m: f"<strong>{m.group(1)}</strong>", md)
    md = _md_italic.sub(lambda m: f"<em>{m.group(1)}</em>", md)
    md = md.replace("\n", "<br>")
    return md


# --------------------------------------------------------------------------- #
# Chat UI
# --------------------------------------------------------------------------- #

class ChatInterface:
    """Main chat interface component (stable, streaming-friendly)."""

    def __init__(self, *, inject_css_once: bool = True):
        if inject_css_once and not st.session_state.get("_chat_css_injected"):
            self._inject_base_css()
            st.session_state["_chat_css_injected"] = True

    # ----- CSS -------------------------------------------------------------- #
    @staticmethod
    def _inject_base_css() -> None:
        st.markdown(
            """
            <style>
              /* Keep chat nicely centered and bounded */
              .stChatMessage { max-width: 900px; margin-left: auto; margin-right: auto; }
              /* Make markdown breathe */
              [data-testid="stChatMessageContent"] p { margin-bottom: .5rem; }
              /* Code blocks */
              .code-block {
                  display:block; white-space:pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                  background:#0b1020; color:#e6edf3; border-radius:12px; padding:12px; border:1px solid #1f2a44;
              }
              .inline-code {
                  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                  background:#0b1020; color:#e6edf3; padding:2px 6px; border-radius:6px;
                  border:1px solid #1f2a44;
              }
              /* Source expander polish */
              .lm-source-chip {
                  background:#0969da; color:white; padding:2px 8px; border-radius:999px; font-size:12px; font-weight:600;
              }
              .lm-source-box {
                  border:1px solid rgba(0,0,0,.08); border-radius:10px; padding:10px; background:#f8f9fa;
              }
            </style>
            """,
            unsafe_allow_html=True,
        )

    # ----- Welcome ---------------------------------------------------------- #
    def render_welcome(self) -> None:
        # Intentionally left blank (no welcome banner)
        return

    # ----- History ---------------------------------------------------------- #
    def render_history(self, messages: List[Dict[str, Any]]) -> None:
        """Render full conversation, oldest -> newest (ChatGPT style)."""
        if not messages:
            self.render_welcome()
            return

        # Deduplicate consecutive identical messages (same role and content)
        deduped: List[Dict[str, Any]] = []
        last_key: Optional[Tuple[str, str]] = None
        for m in messages:
            role_m = m.get("role", "assistant")
            content_m = m.get("content", "") or ""
            key = (role_m, content_m)
            if key == last_key:
                continue
            deduped.append(m)
            last_key = key

        for msg in deduped:
            role = msg.get("role", "assistant")
            content = msg.get("content", "")
            ts = _format_rel_time(msg.get("timestamp", _now_iso()))
            avatar = "👤" if role == "user" else "🧠"

            with st.chat_message(role, avatar=avatar):
                # Use Streamlit markdown to keep within the message bubble.
                # We still pre-sanitize to avoid HTML breaking layout.
                st.markdown(_markdown_to_html_safe(content), unsafe_allow_html=True)
                st.caption(ts)
                if role == "assistant" and msg.get("sources"):
                    self.render_sources(msg["sources"])

    # Compatibility: render a single message (API expected by some callers)
    def render_message(self, message: Dict[str, Any], index: int) -> None:
        role = message.get("role", "assistant")
        content = message.get("content", "")
        avatar = "👤" if role == "user" else "🧠"
        with st.chat_message(role, avatar=avatar):
            st.markdown(_markdown_to_html_safe(content), unsafe_allow_html=True)
            if role == "assistant" and message.get("sources"):
                self.render_sources(message["sources"])

    # ----- Streaming -------------------------------------------------------- #
    def stream_assistant_reply(
        self,
        events: Iterable[Dict[str, Any]],
        *,
        show_cursor: bool = True,
        show_sources: bool = True,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Stream tokens as they arrive. Returns (full_text, sources)."""
        full = ""
        sources: List[Dict[str, Any]] = []

        with st.chat_message("assistant", avatar="🧠"):
            placeholder = st.empty()
            for ev in events:
                if ev.get("done"):
                    sources = ev.get("sources", []) or []
                    break
                delta = ev.get("delta", "")
                if not delta:
                    continue
                full += delta
                # Single placeholder update → fast
                cursor = " ▋" if show_cursor else ""
                placeholder.markdown(_markdown_to_html_safe(full) + cursor, unsafe_allow_html=True)

            placeholder.markdown(_markdown_to_html_safe(full), unsafe_allow_html=True)
            if show_sources and sources:
                self.render_sources(sources)

        return full, sources

    # ----- Single turn helpers --------------------------------------------- #
    def render_user_message(self, text: str) -> None:
        with st.chat_message("user", avatar="👤"):
            st.markdown(_markdown_to_html_safe(text), unsafe_allow_html=True)

    # ----- Sources ---------------------------------------------------------- #
    def render_sources(self, sources: List[Dict[str, Any]]) -> None:
        """Compact, readable RAG source list."""
        if not sources:
            return
        with st.expander(f"📚 Sources ({len(sources)})", expanded=False):
            for i, s in enumerate(sources, 1):
                title = s.get("title") or s.get("filename") or s.get("doc") or f"Source {i}"
                score = s.get("relevance_score", s.get("score"))
                page = s.get("page") or s.get("chunk_id")
                snippet = s.get("snippet") or s.get("content") or s.get("text") or ""
                snippet = (snippet or "").strip()
                if len(snippet) > 700:
                    snippet = snippet[:700] + " …"

                # Header line
                header_bits = [f"**{title}**"]
                if isinstance(page, int) or (isinstance(page, str) and page):
                    header_bits.append(f"· p/idx: `{page}`")
                if isinstance(score, (int, float)):
                    header_bits.append(f"· <span class='lm-source-chip'>{score:.3f}</span>")

                st.markdown(" ".join(header_bits), unsafe_allow_html=True)

                # Snippet box
                st.markdown(f"<div class='lm-source-box'><pre>{html.escape(snippet)}</pre></div>", unsafe_allow_html=True)

    # Public alias for downstream code expecting this name
    def markdown_to_html_safe(self, content: str) -> str:
        return _markdown_to_html_safe(content)


# --------------------------------------------------------------------------- #
# Message composer (optional)
# --------------------------------------------------------------------------- #

class MessageComposer:
    """Message input composer with a simple layout and hooks."""

    def __init__(self, key_prefix: str = "composer"):
        self.key_prefix = key_prefix
        self._ensure_state()

    def _ensure_state(self):
        st.session_state.setdefault(f"{self.key_prefix}_text", "")
        st.session_state.setdefault(f"{self.key_prefix}_clear_next", False)

    def render(
        self,
        *,
        height: int = 140,
        on_send: Optional[callable] = None,
        disabled: bool = False,
        rag_checkbox: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Render the composer; returns dict with actions."""
        actions: Dict[str, Any] = {}

        # Clear text once (next run) after send/clear
        if st.session_state.get(f"{self.key_prefix}_clear_next"):
            st.session_state[f"{self.key_prefix}_text"] = ""
            st.session_state[f"{self.key_prefix}_clear_next"] = False

        # RAG per-turn toggle (optional, if upstream provides a default)
        use_rag = True if rag_checkbox is None else bool(rag_checkbox)
        rag_toggle = st.checkbox(
            "Use Knowledge Base (RAG) for this message",
            value=use_rag,
            key=f"{self.key_prefix}_rag_toggle",
        )

        with st.form(f"{self.key_prefix}_form", clear_on_submit=False):
            st.text_area(
                "Message",
                key=f"{self.key_prefix}_text",
                label_visibility="collapsed",
                height=height,
                placeholder="Type your message…  Shift+Enter for newline.",
                disabled=disabled,
            )
            c1, c2 = st.columns(2)
            with c1:
                submitted = st.form_submit_button("Send", use_container_width=True, disabled=disabled)
            with c2:
                cleared = st.form_submit_button("Clear", use_container_width=True, disabled=disabled)

        if cleared:
            st.session_state[f"{self.key_prefix}_clear_next"] = True
            st.rerun()

        if submitted:
            text = (st.session_state.get(f"{self.key_prefix}_text") or "").strip()
            if text:
                actions["sent_text"] = text
                actions["use_rag"] = bool(st.session_state.get(f"{self.key_prefix}_rag_toggle", True))
                st.session_state[f"{self.key_prefix}_clear_next"] = True
                if on_send:
                    on_send(text, actions["use_rag"])

        return actions


# --------------------------------------------------------------------------- #
# Performance metrics (optional)
# --------------------------------------------------------------------------- #

class PerformanceMetrics:
    """Tiny panel for quick perf counters."""

    @staticmethod
    def render(metrics: Dict[str, Any]) -> None:
        if not metrics:
            return
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Response time", f"{metrics.get('response_time', 0):.2f}s")
        with c2:
            st.metric("Tokens/sec", f"{metrics.get('tokens_per_second', 0):.1f}")
        with c3:
            st.metric("Total tokens", metrics.get("total_tokens", 0))
        with c4:
            st.metric("KB sources", metrics.get("kb_sources", 0))