# frontend_streamlit/app.py
"""
Synapse - Frontend (fast streaming + proper scrolling)
Left: Compose / RAG / KB
Right: Chat history (streaming), oldest -> newest (like ChatGPT)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict  # noqa: F401 (kept for future typing as needed)

import streamlit as st

# ---------- Imports & wiring ----------
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from frontend.api.backend import BackendClient  # type: ignore  # noqa: E402
from frontend.components.chat_interface import ChatInterface  # type: ignore  # noqa: E402
from frontend.components.sidebar import Sidebar  # type: ignore  # noqa: E402


# ---------- Page config ----------
st.set_page_config(
            page_title="Synapse - Your AI Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Base CSS (sticky compose, dedicated chat pane, buttons) ----------
st.markdown(
    """
    <style>
      .appview-container .main .block-container {
        display: flex; flex-direction: column; min-height: 100vh;
      }
      /* Make the main container fill the viewport height */
      html, body { height: auto; overflow: auto; }
      .appview-container, .appview-container .main, .appview-container .main .block-container {
        height: auto; overflow: visible;
      }
      /* Keep the form sticky at bottom of LEFT column only (best-effort) */
      div[data-testid="stForm"] {
        position: sticky; bottom: 0; z-index: 100;
        background: var(--background-color);
        border-top: 1px solid rgba(49,51,63,.15);
        padding-top: .5rem; padding-bottom: .5rem;
      }
      /* Right chat output scrolls independently (no markdown wrapper) */
      [data-testid="stElementContainer"]:has(> [data-testid="stVerticalBlock"] [data-testid="stChatMessage"]) {
        height: calc(100vh - 220px);
        overflow-y: auto;
        padding: .5rem .25rem;
        scroll-behavior: smooth;
        border: 1px solid rgba(49,51,63,.08);
        border-radius: .5rem;
        background: rgba(0,0,0,0.02);
      }

      /* Left compose pane: natural height, no independent scroll; sticky form */
      #compose-pane {
        height: auto;
        overflow: visible;
        padding: 0;
        border: 0;
        background: transparent;
        display: flex; flex-direction: column; gap: .5rem;
      }
      /* Make the body flow naturally; avoids looking like a second chat box */
      #compose-body { flex: 0 0 auto; overflow: visible; padding-bottom: .5rem; }
      #compose-form { position: sticky; bottom: 0; z-index: 100; background: var(--background-color); border-top: 1px solid rgba(49,51,63,.15); padding-top: .5rem; }
      /* Make chat messages breathe a bit */
      [data-testid="stChatMessageContent"] p { margin-bottom: .5rem; }

      /* (toolbar removed) */
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Sidebar toggle always visible ----------
def _ensure_sidebar_toggle_visible() -> None:
    st.markdown(
        """
        <style>
          [data-testid="collapsedControl"] { display: block !important; visibility: visible !important; opacity: 1 !important; }
          [data-testid="collapsedControl"] button { position: fixed; left: 12px; top: 72px; z-index: 9999; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def _apply_sidebar_force_open_css(force_open: bool) -> None:
    if not force_open:
        return
    st.markdown(
        """
        <style>
          [data-testid="stSidebar"] { transform: none !important; visibility: visible !important; opacity: 1 !important; width: 18rem !important; min-width: 18rem !important; }
          [data-testid="stSidebar"] > div { width: 18rem !important; }
          .appview-container .main .block-container { margin-left: 18rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

_ensure_sidebar_toggle_visible()

# ---------- Session init ----------
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:9000")
if "backend_client" not in st.session_state:
    st.session_state.backend_client = BackendClient(BACKEND_URL)

# Inject base chat CSS once and keep the helper around
CHAT_IFACE_VERSION = "2"
if (
    "chat_interface" not in st.session_state
    or st.session_state.get("_chat_iface_version") != CHAT_IFACE_VERSION
):
    st.session_state.chat_interface = ChatInterface()
    st.session_state._chat_iface_version = CHAT_IFACE_VERSION

if "messages" not in st.session_state:
    # [{'role': 'user'|'assistant', 'content': str, 'sources': list?}, ...]
    st.session_state.messages = []

@st.cache_data(ttl=5.0)
def _get_config_cached(url: str):
    # cache briefly to avoid frequent network calls on every re-run
    try:
        return BackendClient(url).get_config()
    except Exception:
        return {
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 512,
            "auto_rag": False,  # Default to False if backend is unavailable
            "rag_top_k": 4,
            "rag_max_chars": 1200,
        }

st.session_state.config = _get_config_cached(BACKEND_URL)

# ---------- Safe markdown (compat across older ChatInterface instances) ----------
def _safe_markdown_to_html(text: str) -> str:
    try:
        ci = st.session_state.get("chat_interface")
        if ci is not None:
            method = getattr(ci, "markdown_to_html_safe", None)
            if callable(method):
                return method(text)
    except Exception:
        pass
    try:
        from frontend.components.chat_interface import _markdown_to_html_safe as _fallback  # type: ignore
        return _fallback(text)
    except Exception:
        return text

# ---------- Sidebar ----------
def render_sidebar(current_rag_status=None):
    sidebar = Sidebar(st.session_state.backend_client)
    actions = sidebar.render(current_rag_status)

    if actions.get("clear_chat"):
        st.session_state.messages = []
        st.rerun()

    if actions.get("reload_kb"):
        with st.spinner("Reindexing knowledge base…"):
            st.session_state.backend_client.kb_reload()
        st.success("KB reindexed")

    if actions.get("show_kb_stats"):
        try:
            stats = st.session_state.backend_client.get_kb_stats()
            st.json(stats)
        except Exception as e:
            st.error(f"KB stats error: {e}")

# ---------- Chat column (RIGHT) ----------
def render_chat_col(col):
    with col:
        # Open the scrollable pane without markdown wrapper
        scroller = st.container()

        # Render welcome or history first
        if not st.session_state.messages:
            with scroller:
                st.session_state.chat_interface.render_welcome()
        else:
            with scroller:
                st.session_state.chat_interface.render_history(st.session_state.messages)

        # Mount point for streaming, inside scroll area
        stream_mount = scroller.container()

        # Bottom pin-once script targeting the nearest container element
        st.markdown(
            """
            <script>
            (function(){
              try {
                const blocks = window.parent.document.querySelectorAll('[data-testid="stElementContainer"]');
                if (blocks && blocks.length) {
                  const el = blocks[blocks.length-1];
                  el.scrollTop = el.scrollHeight;
                }
              } catch (e) {}
            })();
            </script>
            """,
            unsafe_allow_html=True,
        )
        return stream_mount

# ---------- Compose / RAG / KB column (LEFT) ----------
def render_compose_col(col, chat_pane_ref):
    with col:
        st.markdown("### Compose")
        # Fixed compose wrapper (no independent scroll)
        st.markdown('<div id="compose-pane"><div id="compose-pane-anchor"></div>', unsafe_allow_html=True)

        # RAG toggle defaults to backend setting
        rag_default = bool(st.session_state.config.get("auto_rag", False))
        
        # RAG Global Control Section
        st.markdown("### 🔍 Global RAG Control")
        st.caption("This setting controls RAG behavior for ALL messages in your conversation")
        
        # Clear visual toggle for global RAG setting
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Visual toggle switch with clear labels
            current_rag_status = st.session_state.config.get("auto_rag", False)
            new_rag_status = st.toggle(
                "🔍 **Knowledge Base (RAG) Mode**",
                value=current_rag_status,
                help="When ON: AI searches your documents for ALL messages. When OFF: AI uses general knowledge only for ALL messages.",
                key="global_rag_toggle"
            )
            
            # Show current status with color coding
            if new_rag_status:
                st.success("✅ **RAG ENABLED** - AI will search your documents for ALL messages")
            else:
                st.info("ℹ️ **RAG DISABLED** - AI uses general knowledge only for ALL messages")
        
        with col2:
            # Apply button to save changes
            if st.button("💾 Apply", use_container_width=True, type="primary"):
                try:
                    if new_rag_status != current_rag_status:
                        result = st.session_state.backend_client.set_rag_state({"auto_rag": new_rag_status})
                        st.success(f"✅ RAG {'enabled' if result['auto_rag'] else 'disabled'}")
                        # Refresh config to get updated state
                        st.session_state.config = st.session_state.backend_client.get_config()
                        st.rerun()
                    else:
                        st.info("No changes to apply")
                except Exception as e:
                    st.error(f"Failed to update RAG: {e}")
        
        with col3:
            # Refresh button
            if st.button("🔄 Refresh", use_container_width=True, type="secondary"):
                try:
                    st.session_state.config = st.session_state.backend_client.get_config()
                    st.success("Config refreshed")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to refresh config: {e}")
        
        st.divider()
        
        # RAG behavior explanation
        st.markdown("### 📚 RAG Behavior")
        
        # Show current toggle state (what user sees and will be applied)
        if new_rag_status:
            st.success("🔍 **RAG ENABLED** - AI will search your Knowledge Base for ALL messages")
            st.info("💡 **How it works**: When you send a message, the AI automatically searches through your uploaded documents to find relevant information before responding.")
        else:
            st.info("ℹ️ **RAG DISABLED** - AI responds using general knowledge only for ALL messages")
            st.info("💡 **How it works**: The AI responds based on its general knowledge and conversation history, without searching your documents.")
        
        # Set use_rag to match the current toggle state (what user sees)
        use_rag = new_rag_status

        # Compose form
        st.session_state.setdefault("compose_text", "")
        # Clear the text input on the next run BEFORE the widget is created
        if st.session_state.get("_pending_clear_compose"):
            st.session_state.compose_text = ""
            st.session_state._pending_clear_compose = False

        with st.form("compose_form", clear_on_submit=False):
            st.text_area(
                "Message",
                key="compose_text",
                label_visibility="collapsed",
                height=180,
                placeholder="Type your message…  Shift+Enter for newline.",
            )
            c1, c2 = st.columns(2)
            with c1:
                submitted = st.form_submit_button("Send", use_container_width=True)
            with c2:
                cleared = st.form_submit_button("Clear", use_container_width=True)

        if cleared:
            # Defer clearing the widget value until the next run
            st.session_state._pending_clear_compose = True
            st.rerun()

        # RAG preview (optional)
        rag_preview_box = st.empty()

        def show_rag_preview(q: str):
            try:
                data = st.session_state.backend_client.rag_preview(q)
                
                # Check if RAG is disabled
                if data.get("message") == "RAG is currently disabled":
                    with rag_preview_box.container():
                        with st.expander("RAG preview", expanded=False):
                            st.info("ℹ️ RAG is currently disabled - no preview available")
                    return
                
                # Get chunks from response
                chunks = data.get("chunks", [])
                
                if not chunks:
                    with rag_preview_box.container():
                        with st.expander("RAG preview", expanded=False):
                            st.info("🔍 **No relevant documents found**")
                            st.caption("Try:")
                            st.caption("• Uploading more documents")
                            st.caption("• Using different search terms")
                            st.caption("• Checking if documents are indexed")
                else:
                    # Display found chunks
                    with rag_preview_box.container():
                        with st.expander("RAG preview", expanded=False):
                            st.success(f"🔍 **Found {len(chunks)} relevant document(s)**")
                            for i, chunk in enumerate(chunks, 1):
                                with st.expander(f"📄 {chunk.get('title', 'Unknown')}", expanded=False):
                                    st.caption(f"Source: {chunk.get('doc', 'Unknown')}")
                                    st.code(chunk.get('snippet', ''))
            except Exception as e:
                with rag_preview_box.container():
                    with st.expander("RAG preview", expanded=False):
                        st.warning(f"RAG preview error: {e}")

        # Chat management
        st.divider()
        st.markdown("### Chat Management")
        
        # Clear chat history button
        if st.button("🗑️ Clear Chat History", use_container_width=True, type="secondary"):
            st.session_state.messages = []
            st.rerun()
        
        # KB upload
        st.divider()
        st.markdown("### Knowledge Base")
        uploads = st.file_uploader(
            "Upload files",
            type=["txt","md","markdown","pdf","docx","rtf","html","htm","csv","json","xml","pptx"],
            accept_multiple_files=True,
            key="kb_upload",
        )
        if uploads and st.button("Upload & Reindex KB", use_container_width=True):
            try:
                payload = []
                for f in uploads:
                    payload.append(("files", f.getvalue(), f.type or "application/octet-stream", f.name))
                st.session_state.backend_client.kb_upload(payload)
                with st.spinner("Reindexing…"):
                    st.session_state.backend_client.kb_reload()
                st.success("KB updated")
            except Exception as e:
                st.error(f"Upload failed: {e}")

        # Handle submit
        if not submitted:
            st.markdown('</div>', unsafe_allow_html=True)
            return

        q = (st.session_state.compose_text or "").strip()
        if not q:
            st.warning("Type a message first.")
            return

        if use_rag:
            show_rag_preview(q)
        else:
            rag_preview_box.empty()

        # Append user message once
        st.session_state.messages.append({
            "role": "user",
            "content": q,
            "timestamp": datetime.now().isoformat(),
        })

        # Stream assistant reply into RIGHT chat pane, with THROTTLE
        with chat_pane_ref:
            # open bubble inside the same scrollable div
            with st.chat_message("assistant", avatar="🧠"):
                placeholder = st.empty()
                full = ""
                sources = []

                # Throttle knobs
                last_flush = 0.0
                min_interval = 0.04  # seconds between UI updates
                buffered_chars = 0
                flush_every_chars = 120  # also flush on this many new chars

                try:
                    for event in st.session_state.backend_client.chat_stream(
                        _clean_messages_for_backend(st.session_state.messages),  # Clean messages before sending
                        temperature=st.session_state.config.get("temperature", 0.7),
                        max_tokens=st.session_state.config.get("max_tokens", 512),
                        auto_rag=use_rag,
                    ):
                        if event.get("done"):
                            sources = event.get("sources", [])
                            break
                        delta = event.get("delta", "")
                        if not delta:
                            continue

                        # accumulate and flush by time/size
                        full += delta
                        buffered_chars += len(delta)
                        now = time.time()
                        if (now - last_flush) >= min_interval or buffered_chars >= flush_every_chars:
                            # Use safe HTML markdown (compat helper)
                            placeholder.markdown(
                                _safe_markdown_to_html(full) + " ▋",
                                unsafe_allow_html=True,
                            )
                            last_flush = now
                            buffered_chars = 0

                            # keep view pinned to the bottom of chat pane
                            st.markdown(
                                """
                                <script>
                                  try {
                                    const doc = window.document;
                                    const pdoc = window.parent && window.parent.document ? window.parent.document : doc;
                                    const scroller = pdoc.getElementById('chat-scroll') || doc.getElementById('chat-scroll');
                                    if (scroller) scroller.scrollTop = scroller.scrollHeight;
                                  } catch (e) {}
                                </script>
                                """,
                                unsafe_allow_html=True,
                            )

                except Exception as e:
                    full = f"**Error:** {e}"

                # Final paint
                placeholder.markdown(
                    _safe_markdown_to_html(full),
                    unsafe_allow_html=True,
                )
                if sources:
                    st.session_state.chat_interface.render_sources(sources)

        # Persist assistant turn locally (frontend session)
        st.session_state.messages.append({
            "role": "assistant",
            "content": full,
            "timestamp": datetime.now().isoformat(),
            "sources": sources,
        })

        # Clear input next run
        st.session_state._pending_clear_compose = True
        st.markdown('</div>', unsafe_allow_html=True)
        st.rerun()

def _clean_messages_for_backend(messages: List[Dict]) -> List[Dict[str, str]]:
    """Clean messages to match backend API expectations."""
    cleaned = []
    for msg in messages:
        # Only keep role and content fields for backend API
        cleaned_msg = {
            "role": msg.get("role", ""),
            "content": msg.get("content", "")
        }
        cleaned.append(cleaned_msg)
    return cleaned

# ---------- Page body ----------
def main():
    # Sidebar controls & info
    # Pass current RAG status from toggle to sidebar for consistency
    current_rag_status = st.session_state.get("global_rag_toggle", st.session_state.config.get("auto_rag", False))
    render_sidebar(current_rag_status)

    # Optional sidebar toggle in UI (avoid setting value via Session State and widget simultaneously)
    ctrl_col, _ = st.columns([1, 9])
    with ctrl_col:
        show_sidebar = st.checkbox("Show sidebar", key="ui_show_sidebar", value=True)
    _apply_sidebar_force_open_css(bool(show_sidebar))

    st.title("Synapse")

    # Two columns: left compose (narrower), right chat (wider)
    left, right = st.columns([1.4, 2.6], gap="large")
    chat_pane_ref = render_chat_col(right)  # render history first
    render_compose_col(left, chat_pane_ref=chat_pane_ref)

if __name__ == "__main__":
    main()