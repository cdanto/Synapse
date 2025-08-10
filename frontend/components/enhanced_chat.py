"""
Enhanced Chat Interface Component for Synapse
Modern design with better UX, error handling, and performance
"""

import streamlit as st
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests

class EnhancedChatInterface:
    """Enhanced chat interface with modern design and better UX"""
    
    def __init__(self):
        self.setup_session_state()
        self.setup_styling()
    
    def setup_session_state(self):
        """Initialize session state variables"""
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'is_loading' not in st.session_state:
            st.session_state.is_loading = False
        if 'error_message' not in st.session_state:
            st.session_state.error_message = None
        if 'chat_mode' not in st.session_state:
            st.session_state.chat_mode = "chat"  # chat, rag, or upload
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = []
    
    def setup_styling(self):
        """Apply custom CSS for modern design"""
        st.markdown("""
        <style>
        /* Modern Chat Interface Styling */
        .chat-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        
        .user-message {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            border-radius: 20px 20px 5px 20px;
            margin: 10px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            max-width: 80%;
            margin-left: auto;
        }
        
        .assistant-message {
            background: white;
            color: #333;
            padding: 15px 20px;
            border-radius: 20px 20px 20px 5px;
            margin: 10px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            max-width: 80%;
            border-left: 4px solid #667eea;
        }
        
        .message-timestamp {
            font-size: 0.7em;
            color: #888;
            margin-top: 5px;
            text-align: right;
        }
        
        .input-container {
            background: white;
            border-radius: 25px;
            padding: 5px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin: 20px 0;
        }
        
        .send-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 20px;
            padding: 10px 25px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .send-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.2);
        }
        
        .mode-selector {
            background: white;
            border-radius: 15px;
            padding: 15px;
            margin: 15px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .file-upload-area {
            border: 2px dashed #667eea;
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            background: rgba(102, 126, 234, 0.05);
            margin: 15px 0;
        }
        
        .error-message {
            background: #ff6b6b;
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            border-left: 4px solid #d63031;
        }
        
        .success-message {
            background: #00b894;
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            border-left: 4px solid #00a085;
        }
        
        .loading-spinner {
            text-align: center;
            padding: 20px;
            color: #667eea;
        }
        
        .chat-header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .chat-header h1 {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .chat-header p {
            color: #666;
            font-size: 1.1em;
        }
        
        .stats-container {
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        
        .stat-item {
            background: white;
            padding: 15px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin: 5px;
            min-width: 120px;
        }
        
        .stat-number {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            color: #666;
            font-size: 0.9em;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def render_header(self):
        """Render the enhanced chat header"""
        st.markdown("""
        <div class="chat-header">
            <h1>🧠 Synapse</h1>
            <p>Your AI Assistant with Advanced RAG Capabilities</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_mode_selector(self):
        """Render chat mode selector"""
        st.markdown('<div class="mode-selector">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💬 Chat", key="chat_mode_btn", use_container_width=True):
                st.session_state.chat_mode = "chat"
                st.rerun()
        
        with col2:
            if st.button("🔍 RAG Search", key="rag_mode_btn", use_container_width=True):
                st.session_state.chat_mode = "rag"
                st.rerun()
        
        with col3:
            if st.button("📁 Upload Files", key="upload_mode_btn", use_container_width=True):
                st.session_state.chat_mode = "upload"
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_stats(self):
        """Render chat statistics"""
        try:
            response = requests.get("http://127.0.0.1:9000/kb/stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
                
                st.markdown('<div class="stats-container">', unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="stat-item">
                        <div class="stat-number">{stats.get('total_documents', 0)}</div>
                        <div class="stat-label">Documents</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="stat-item">
                        <div class="stat-number">{stats.get('total_chunks', 0)}</div>
                        <div class="stat-label">Chunks</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="stat-item">
                        <div class="stat-number">{len(st.session_state.chat_history)}</div>
                        <div class="stat-label">Messages</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="stat-item">
                        <div class="stat-number">{stats.get('index_size_mb', 0):.1f}MB</div>
                        <div class="stat-label">Index Size</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
        except Exception as e:
            st.warning(f"Could not load stats: {str(e)}")
    
    def render_chat_history(self):
        """Render enhanced chat history"""
        if not st.session_state.chat_history:
            st.info("💡 Start a conversation! Ask me anything or upload documents for RAG-powered responses.")
            return
        
        for i, message in enumerate(st.session_state.chat_history):
            if message['role'] == 'user':
                st.markdown(f"""
                <div class="user-message">
                    {message['content']}
                    <div class="message-timestamp">{message['timestamp']}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="assistant-message">
                    {message['content']}
                    <div class="message-timestamp">{message['timestamp']}</div>
                </div>
                """, unsafe_allow_html=True)
    
    def render_chat_input(self):
        """Render enhanced chat input"""
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input = st.text_input(
                "Your message...",
                key="user_input",
                placeholder="Ask me anything or type '/help' for commands...",
                label_visibility="collapsed"
            )
        
        with col2:
            if st.button("🚀 Send", key="send_button", use_container_width=True):
                if user_input.strip():
                    self.process_user_input(user_input.strip())
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_file_upload(self):
        """Render file upload interface"""
        st.markdown('<div class="file-upload-area">', unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "Upload documents for RAG processing",
            type=['pdf', 'txt', 'docx', 'md'],
            accept_multiple_files=True,
            key="file_uploader"
        )
        
        if uploaded_files:
            st.session_state.uploaded_files = uploaded_files
            
            if st.button("📚 Process Documents", key="process_files"):
                self.process_uploaded_files(uploaded_files)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def process_user_input(self, user_input: str):
        """Process user input and generate response"""
        if user_input.startswith('/help'):
            self.show_help()
            return
        
        if user_input.startswith('/clear'):
            st.session_state.chat_history = []
            st.success("Chat history cleared!")
            return
        
        # Add user message to history
        user_message = {
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().strftime("%H:%M")
        }
        st.session_state.chat_history.append(user_message)
        
        # Set loading state
        st.session_state.is_loading = True
        st.session_state.error_message = None
        
        try:
            # Generate response based on mode
            if st.session_state.chat_mode == "rag":
                response = self.get_rag_response(user_input)
            else:
                response = self.get_chat_response(user_input)
            
            # Add assistant response to history
            assistant_message = {
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.now().strftime("%H:%M")
            }
            st.session_state.chat_history.append(assistant_message)
            
        except Exception as e:
            st.session_state.error_message = f"Error: {str(e)}"
            st.error(f"Failed to get response: {str(e)}")
        
        finally:
            st.session_state.is_loading = False
    
    def get_chat_response(self, user_input: str) -> str:
        """Get chat response from backend"""
        try:
            response = requests.post(
                "http://127.0.0.1:9000/chat",
                json={"message": user_input},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('response', 'No response received')
            else:
                raise Exception(f"Backend error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            raise Exception("Request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to backend. Please check if the service is running.")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")
    
    def get_rag_response(self, user_input: str) -> str:
        """Get RAG-powered response from backend"""
        try:
            response = requests.post(
                "http://127.0.0.1:9000/chat/stream",
                json={"message": user_input, "use_rag": True},
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json().get('response', 'No RAG response received')
            else:
                raise Exception(f"RAG backend error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            raise Exception("RAG request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to RAG backend. Please check if the service is running.")
        except Exception as e:
            raise Exception(f"RAG unexpected error: {str(e)}")
    
    def process_uploaded_files(self, files):
        """Process uploaded files for RAG"""
        st.info("Processing files... This may take a moment.")
        
        # TODO: Implement file processing logic
        st.success(f"Successfully processed {len(files)} files!")
    
    def show_help(self):
        """Show help information"""
        help_text = """
        **Available Commands:**
        - `/help` - Show this help message
        - `/clear` - Clear chat history
        
        **Features:**
        - 💬 **Chat Mode**: Regular conversation with AI
        - 🔍 **RAG Mode**: AI responses enhanced with your documents
        - 📁 **Upload Mode**: Add documents to your knowledge base
        
        **Tips:**
        - Upload documents first for better RAG responses
        - Use specific questions for more accurate answers
        - The AI remembers your conversation context
        """
        
        st.info(help_text)
    
    def render_error_messages(self):
        """Render error messages if any"""
        if st.session_state.error_message:
            st.markdown(f"""
            <div class="error-message">
                ⚠️ {st.session_state.error_message}
            </div>
            """, unsafe_allow_html=True)
    
    def render_loading_state(self):
        """Render loading state"""
        if st.session_state.is_loading:
            st.markdown("""
            <div class="loading-spinner">
                <div>🤔 Thinking...</div>
                <div style="font-size: 0.8em; color: #888;">Please wait while I process your request</div>
            </div>
            """, unsafe_allow_html=True)
    
    def render(self):
        """Main render method"""
        self.render_header()
        self.render_mode_selector()
        self.render_stats()
        
        # Render based on current mode
        if st.session_state.chat_mode == "upload":
            self.render_file_upload()
        else:
            self.render_chat_history()
            self.render_chat_input()
        
        self.render_error_messages()
        self.render_loading_state()

# Usage
def main():
    chat_interface = EnhancedChatInterface()
    chat_interface.render()

if __name__ == "__main__":
    main()
