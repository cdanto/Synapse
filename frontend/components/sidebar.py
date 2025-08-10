# frontend/components/sidebar.py
"""
Sidebar components for Synapse (fast, buffered, and reliable)
"""
from __future__ import annotations

from typing import Any, Dict, List
import os
import streamlit as st


class Sidebar:
    """Main sidebar with controls and settings."""

    def __init__(self, backend_client):
        self.backend_client = backend_client

    # --------------------------------------------------------------------- #
    def render(self, current_rag_status=None) -> Dict[str, Any]:
        """Render the sidebar and return an actions dict for the app to handle."""
        actions: Dict[str, Any] = {}

        with st.sidebar:
            st.markdown(
                """
                <div class="sidebar-header" style="margin-bottom:.5rem">
                  <h2 style="margin:0">🧠 Synapse</h2>
                  <p style="margin:.25rem 0 0;color:#6b7280">Your AI Assistant</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Chat controls
            actions.update(self._chat_controls())

            st.divider()

            # Configuration (buffered via forms, one POST on Apply)
            actions.update(self._config_section(current_rag_status))

            st.divider()

            # Knowledge Base
            actions.update(self._kb_section())

            st.divider()

            # Advanced/debug
            actions.update(self._advanced())

        return actions

    # --------------------------------------------------------------------- #
    def _chat_controls(self) -> Dict[str, Any]:
        actions: Dict[str, Any] = {}
        st.markdown("### 💬 Chat")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑 Clear", use_container_width=True):
                actions["clear_chat"] = True
        with c2:
            if st.button("📋 Copy last", use_container_width=True):
                actions["copy_last"] = True

        c3, c4 = st.columns(2)
        with c3:
            if st.button("💾 Export", use_container_width=True):
                actions["export_chat"] = True
        with c4:
            if st.button("➕ New", use_container_width=True):
                actions["new_chat"] = True

        return actions

    # --------------------------------------------------------------------- #
    def _config_section(self, current_rag_status=None) -> Dict[str, Any]:
        """
        Buffered config editing:
        - fetch once (cached in session)
        - edit in forms
        - send a single POST when "Apply" is pressed
        """
        actions: Dict[str, Any] = {}
        st.markdown("### ⚙️ Configuration")

        # cache config to avoid frequent GETs
        try:
            cfg = st.session_state.get("_cached_config")
            if cfg is None:
                cfg = self.backend_client.get_config()
                st.session_state["_cached_config"] = dict(cfg)  # copy
        except Exception as e:
            st.error(f"Config load failed: {e}")
            return actions

        # form for editing
        with st.form("config_form"):
            st.markdown("**Model Settings**")
            temperature = st.slider(
                "Temperature", min_value=0.0, max_value=2.0, value=float(cfg.get("temperature", 0.7)), step=0.1
            )
            top_p = st.slider("Top-p", min_value=0.0, max_value=1.0, value=float(cfg.get("top_p", 0.95)), step=0.05)
            max_tokens = st.slider(
                "Max tokens", min_value=64, max_value=4096, value=int(cfg.get("max_tokens", 512)), step=64
            )

            st.markdown("**RAG Settings**")
            rag_top_k = st.slider(
                "RAG top-k", min_value=1, max_value=20, value=int(cfg.get("rag_top_k", 4)), step=1
            )
            
            # Show current RAG status from main toggle (not from cached config)
            if current_rag_status is not None:
                # Use the current toggle state from main app
                current_rag = current_rag_status
            else:
                # Fallback to cached config if no toggle state passed
                current_rag = bool(cfg.get("auto_rag", os.environ.get("AUTO_RAG", "false").lower() in ("true", "1", "yes")))
            
            # Visual status indicator (consistent with main Global RAG Control)
            if current_rag:
                st.success("🔍 **RAG: ENABLED** - AI searches your documents for ALL messages")
            else:
                st.info("ℹ️ **RAG: DISABLED** - AI uses general knowledge only for ALL messages")
            
            st.caption("💡 **Control RAG globally** in the main chat area above")

            st.markdown("**System Settings**")
            
            # Guardian Control
            st.markdown("**🛡️ Guardian Settings**")
            guardian_enabled = st.checkbox(
                "Enable Guardian",
                value=bool(cfg.get("guardian_enabled", True)),
                help="Guardian filters content and enforces safety policies"
            )
            
            # Show current Guardian status
            if guardian_enabled:
                st.success("🛡️ **Guardian: ENABLED** - Content filtering and safety policies active")
            else:
                st.warning("⚠️ **Guardian: DISABLED** - No content filtering or safety policies")
            
            system_prompt = st.text_area(
                "System prompt",
                value=cfg.get("system_prompt", ""),
                height=100,
                placeholder="Enter system instructions...",
            )

            # submit button
            if st.form_submit_button("💾 Apply Changes", use_container_width=True):
                try:
                    patch = {
                        "temperature": temperature,
                        "top_p": top_p,
                        "max_tokens": max_tokens,
                        "rag_top_k": rag_top_k,
                        "guardian_enabled": guardian_enabled,
                        "system_prompt": system_prompt,
                    }
                    self.backend_client.update_config(patch)
                    st.session_state["_cached_config"] = patch  # update cache
                    st.success("✅ Configuration updated")
                except Exception as e:
                    st.error(f"Update failed: {e}")

        # Clear Knowledge Base and Chat History options (outside the form)
        st.markdown("**🗑️ System Management**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear Knowledge Base", type="secondary", use_container_width=True):
                try:
                    # Use backend API to clear KB
                    self.backend_client.clear_knowledge_base()
                    st.success("✅ Knowledge Base cleared successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error clearing Knowledge Base: {str(e)}")
        
        with col2:
            if st.button("💬 Clear Chat History", type="secondary", use_container_width=True):
                try:
                    # Use backend API to clear chat history
                    self.backend_client.clear_chat_history()
                    st.success("✅ Chat History cleared successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error clearing Chat History: {str(e)}")

        return actions

    # --------------------------------------------------------------------- #
    def _kb_section(self) -> Dict[str, Any]:
        actions: Dict[str, Any] = {}
        st.markdown("### 📚 Knowledge Base")

        # Stats
        try:
            stats = self.backend_client.get_kb_stats()
            c1, c2, c3 = st.columns(3)
            c1.metric("Documents", stats.get("total_files", stats.get("files", 0)))
            c2.metric("Chunks", stats.get("total_chunks", stats.get("chunks", 0)))
            c3.metric("Updated", stats.get("last_updated", "—"))
        except Exception as e:
            st.warning(f"KB stats unavailable: {e}")

        # Controls
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Reload KB", use_container_width=True):
                try:
                    with st.spinner("Reindexing…"):
                        self.backend_client.kb_reload()
                    st.success("KB reindexed")
                except Exception as e:
                    st.error(f"Reload failed: {e}")
        with c2:
            if st.button("📊 Show stats", use_container_width=True):
                actions["show_kb_stats"] = True

        # Uploads
        st.caption("Upload files")
        up = st.file_uploader(
            "Choose files",
            type=[
                "txt",
                "md",
                "markdown",
                "pdf",
                "docx",
                "rtf",
                "html",
                "htm",
                "csv",
                "json",
                "xml",
                "pptx",
            ],
            accept_multiple_files=True,
            key="kb_upload_sidebar",
        )
        if up and st.button("📤 Upload & Reindex", use_container_width=True):
            try:
                payload: List[tuple] = []
                for f in up:
                    payload.append(
                        (
                            "files",
                            f.getvalue(),
                            f.type or "application/octet-stream",
                            f.name,
                        )
                    )
                self.backend_client.kb_upload(payload)
                with st.spinner("Reindexing…"):
                    self.backend_client.kb_reload()
                st.success("KB updated")
            except Exception as e:
                st.error(f"Upload failed: {e}")

        return actions

    # --------------------------------------------------------------------- #
    def _advanced(self) -> Dict[str, Any]:
        actions: Dict[str, Any] = {}
        with st.expander("🔧 Advanced", expanded=False):
            debug_mode = st.checkbox(
                "Debug mode", value=st.session_state.get("debug_mode", False)
            )
            if debug_mode != st.session_state.get("debug_mode", False):
                st.session_state["debug_mode"] = debug_mode
                actions["debug_mode_changed"] = debug_mode

            st.markdown("**Performance**")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🚀 Optimize model", use_container_width=True):
                    actions["optimize_model"] = True
            with c2:
                if st.button("🧹 Clear cache", use_container_width=True):
                    actions["clear_cache"] = True

            st.markdown("**Reset**")
            c3, c4 = st.columns(2)
            with c3:
                if st.button("🔄 Reset config", use_container_width=True):
                    actions["reset_config"] = True
            with c4:
                if st.button("⚠️ Reset all", use_container_width=True, type="secondary"):
                    actions["reset_all"] = True

        return actions