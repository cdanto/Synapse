"""
Enhanced Sidebar Component for Synapse
Better navigation, settings, and user experience
"""

import streamlit as st
import requests
from typing import Dict, Any, Optional
import json

class EnhancedSidebar:
    """Enhanced sidebar with better navigation and settings"""
    
    def __init__(self):
        self.setup_session_state()
    
    def setup_session_state(self):
        """Initialize sidebar session state"""
        if 'sidebar_expanded' not in st.session_state:
            st.session_state.sidebar_expanded = True
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "chat"
        if 'theme_mode' not in st.session_state:
            st.session_state.theme_mode = "light"
        if 'sidebar_width' not in st.session_state:
            st.session_state.sidebar_width = "wide"
    
    def render(self):
        """Render the enhanced sidebar"""
        with st.sidebar:
            self.render_header()
            self.render_navigation()
            self.render_quick_actions()
            self.render_settings()
            self.render_system_status()
            self.render_footer()
    
    def render_header(self):
        """Render sidebar header"""
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h2 style="margin: 0; color: #667eea;">🧠</h2>
            <h3 style="margin: 5px 0; color: #333;">Synapse</h3>
            <p style="margin: 0; font-size: 0.8em; color: #666;">AI Assistant</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
    
    def render_navigation(self):
        """Render main navigation menu"""
        st.markdown("### 🧭 Navigation")
        
        # Main navigation
        if st.button("💬 Chat", key="nav_chat", use_container_width=True):
            st.session_state.current_page = "chat"
            st.rerun()
        
        if st.button("🔍 RAG Search", key="nav_rag", use_container_width=True):
            st.session_state.current_page = "rag"
            st.rerun()
        
        if st.button("📁 Documents", key="nav_docs", use_container_width=True):
            st.session_state.current_page = "documents"
            st.rerun()
        
        if st.button("⚙️ Settings", key="nav_settings", use_container_width=True):
            st.session_state.current_page = "settings"
            st.rerun()
        
        if st.button("📊 Analytics", key="nav_analytics", use_container_width=True):
            st.session_state.current_page = "analytics"
            st.rerun()
        
        st.divider()
    
    def render_quick_actions(self):
        """Render quick action buttons"""
        st.markdown("### ⚡ Quick Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Refresh", key="quick_refresh", use_container_width=True):
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear Chat", key="quick_clear", use_container_width=True):
                if 'chat_history' in st.session_state:
                    st.session_state.chat_history = []
                st.success("Chat cleared!")
                st.rerun()
        
        # File upload quick action
        if st.button("📤 Upload Files", key="quick_upload", use_container_width=True):
            st.session_state.current_page = "upload"
            st.rerun()
        
        # Help quick action
        if st.button("❓ Help", key="quick_help", use_container_width=True):
            self.show_help_modal()
        
        st.divider()
    
    def render_settings(self):
        """Render settings panel"""
        st.markdown("### ⚙️ Settings")
        
        # Theme selector
        theme = st.selectbox(
            "Theme",
            ["light", "dark", "auto"],
            index=["light", "dark", "auto"].index(st.session_state.theme_mode),
            key="theme_selector"
        )
        
        if theme != st.session_state.theme_mode:
            st.session_state.theme_mode = theme
            st.rerun()
        
        # Sidebar width
        sidebar_width = st.selectbox(
            "Sidebar Width",
            ["narrow", "wide"],
            index=["narrow", "wide"].index(st.session_state.sidebar_width),
            key="width_selector"
        )
        
        if sidebar_width != st.session_state.sidebar_width:
            st.session_state.sidebar_width = sidebar_width
            st.rerun()
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh stats", value=False, key="auto_refresh")
        
        # Notifications toggle
        notifications = st.checkbox("Enable notifications", value=True, key="notifications")
        
        st.divider()
    
    def render_system_status(self):
        """Render system status information"""
        st.markdown("### 📊 System Status")
        
        try:
            # Health check
            response = requests.get("http://127.0.0.1:9000/health", timeout=5)
            if response.status_code == 200:
                st.success("🟢 Backend Online")
            else:
                st.error("🔴 Backend Error")
        except:
            st.error("🔴 Backend Offline")
        
        # Memory usage (simulated)
        memory_usage = 45.2  # This would come from actual system monitoring
        st.metric("Memory Usage", f"{memory_usage}%")
        
        # Active connections (simulated)
        active_connections = 1
        st.metric("Active Connections", active_connections)
        
        # Last activity
        if 'chat_history' in st.session_state and st.session_state.chat_history:
            last_message = st.session_state.chat_history[-1]
            st.caption(f"Last activity: {last_message['timestamp']}")
        
        st.divider()
    
    def render_footer(self):
        """Render sidebar footer"""
        st.markdown("""
        <div style="text-align: center; padding: 20px 0; font-size: 0.8em; color: #666;">
            <p>Synapse v1.0</p>
            <p>Powered by AI & RAG</p>
        </div>
        """, unsafe_allow_html=True)
    
    def show_help_modal(self):
        """Show help modal"""
        st.info("""
        **Quick Help:**
        
        **Navigation:**
        - Use the sidebar to switch between different modes
        - Chat: Regular AI conversation
        - RAG: AI responses with document context
        - Documents: Manage your knowledge base
        
        **Commands:**
        - `/help` - Show help
        - `/clear` - Clear chat history
        
        **Tips:**
        - Upload documents first for better RAG responses
        - Use specific questions for accuracy
        - Check system status in the sidebar
        """)
    
    def get_current_page(self) -> str:
        """Get current page from session state"""
        return st.session_state.current_page
    
    def set_current_page(self, page: str):
        """Set current page in session state"""
        st.session_state.current_page = page
    
    def is_page_active(self, page: str) -> bool:
        """Check if a page is currently active"""
        return st.session_state.current_page == page
    
    def get_theme_mode(self) -> str:
        """Get current theme mode"""
        return st.session_state.theme_mode
    
    def get_sidebar_width(self) -> str:
        """Get current sidebar width setting"""
        return st.session_state.sidebar_width

# Usage
def main():
    sidebar = EnhancedSidebar()
    sidebar.render()

if __name__ == "__main__":
    main()
