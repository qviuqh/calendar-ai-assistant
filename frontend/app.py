import streamlit as st
import requests
from htbuilder.units import rem
from htbuilder import div, styles
import datetime
import time
import json
from typing import Generator, Dict, Any
import logging

# Import agent classes
from src.agent_workflow import N8nAgent, DifyAgent

from src.token_ui import show_token_input_page, check_token_connected
from src.auth_ui import show_oauth_connect, show_auth_page

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
N8N_WEBHOOK_URL = st.secrets.get("N8N_WEBHOOK_URL")
DIFY_API_URL = st.secrets.get("DIFY_API_URL")
DIFY_API_KEY = st.secrets.get("DIFY_API_KEY")

# Cấu hình trang
st.set_page_config(page_title="Calendar AI Assistant", page_icon="📆")

# Biến cấu hình
MIN_TIME_BETWEEN_REQUESTS = datetime.timedelta(seconds=1)

# Khởi tạo agents (singleton pattern)
@st.cache_resource
def get_n8n_agent():
    """Initialize n8n agent with caching"""
    return N8nAgent(
        webhook_url=N8N_WEBHOOK_URL,
        timeout=30
    )

@st.cache_resource
def get_dify_agent():
    """Initialize Dify agent with caching"""
    return DifyAgent(
        api_url=DIFY_API_URL,
        api_key=DIFY_API_KEY,
        timeout=60
    )

# Initialize session state
if "current_agent" not in st.session_state:
    st.session_state.current_agent = "n8n"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

if "user_id" not in st.session_state:
    # Generate unique user ID
    st.session_state.user_id = f"user_{datetime.datetime.now().timestamp()}"

# Gợi ý câu hỏi mẫu
SUGGESTIONS = {
    "Lịch trình hôm nay": "Lịch trình hôm nay của tôi như thế nào?",
    "Lịch trình tuần này": "Lịch trình tuần này của tôi như thế nào?",
    "Tạo lịch họp trong ngày mai": "Tạo cho tôi một lịch họp vào ngày mai",
}

show_auth_page()

def stream_n8n_response(message: str) -> Generator[str, None, None]:
    """
    Stream response từ n8n agent
    
    Args:
        message: User message
        
    Yields:
        Response chunks (simulated streaming for n8n)
    """
    try:
        agent = get_n8n_agent()
        
        # Prepare workflow data
        workflow_data = {
            "message": message,
            "user_id": st.session_state.user_id,
        }
        
        # Get response (n8n thường không hỗ trợ streaming natively)
        response = agent.send_request(workflow_data, stream=False)
        result = response.json()
        
        # Debug: Log raw response nếu debug mode bật
        if st.session_state.get('debug_mode', False):
            logger.info(f"n8n raw response: {result}")
        
        # Parse n8n response
        response_text = parse_n8n_response(result)
        
        if not response_text:
            yield "⚠️ n8n trả về response rỗng"
            return
        
        # Simulate streaming effect by yielding line by line or word by word
        # Split by line breaks first to preserve formatting
        lines = response_text.split('\n')
        
        for line_idx, line in enumerate(lines):
            if not line.strip():
                # Empty line, just yield line break
                yield '\n'
                continue
            
            # Split line into words
            words = line.split(' ')
            for word_idx, word in enumerate(words):
                if word_idx == len(words) - 1:
                    # Last word in line
                    yield word
                else:
                    yield f"{word} "
                time.sleep(0.02)  # Small delay for streaming effect
            
            # Add line break if not last line
            if line_idx < len(lines) - 1:
                yield '\n'
                time.sleep(0.05)  # Slightly longer delay for line breaks
                
    except Exception as e:
        logger.error(f"n8n streaming error: {str(e)}")
        yield f"❌ Lỗi kết nối n8n: {str(e)}"


def stream_dify_response(message: str) -> Generator[str, None, None]:
    # sourcery skip: inline-immediately-yielded-variable
    """
    Stream response từ Dify agent
    
    Args:
        message: User message
        
    Yields:
        Response chunks
    """
    try:
        agent = get_dify_agent()
        
        # Get streaming response
        stream = agent.chat(
            query=message,
            user_id=st.session_state.user_id,
            conversation_id=st.session_state.conversation_id,
            streaming=True
        )
        
        for event in stream:
            # Debug log
            if st.session_state.get('debug_mode', False):
                logger.info(f"Dify event: {event}")
            
            # Handle different event formats
            event_type = event.get('type', '')
            
            if not event_type:
                # No type field, try to extract content directly
                content = event.get('content', '') or event.get('answer', '') or event.get('text', '')
                if content:
                    # Fix line breaks
                    content = content.replace('\\n', '\n').replace('\n', '  \n')
                    yield content
                
                # Update conversation ID if present
                if event.get('conversation_id'):
                    st.session_state.conversation_id = event['conversation_id']
                continue
            
            if event_type == 'message':
                content = event.get('content', '') or event.get('answer', '')
                if content:
                    # Fix line breaks
                    content = content.replace('\\n', '\n').replace('\n', '  \n')
                    yield content
                
                # Update conversation ID
                if event.get('conversation_id'):
                    st.session_state.conversation_id = event['conversation_id']
                    
            elif event_type == 'message_end':
                # Save conversation ID for context
                if event.get('conversation_id'):
                    st.session_state.conversation_id = event['conversation_id']
                break
                
            elif event_type == 'error':
                logger.error(f"Dify error: {event.get('message')}")
                yield f"❌ Lỗi từ Dify: {event.get('message')}"
                break
                
    except Exception as e:
        logger.error(f"Dify streaming error: {str(e)}", exc_info=True)
        yield f"❌ Lỗi kết nối Dify: {str(e)}"


def get_ai_response_stream(message: str) -> Generator[str, None, None]:
    """
    Unified function để stream response từ agent hiện tại
    
    Args:
        message: User message
        
    Yields:
        Response chunks
    """
    if st.session_state.current_agent == "n8n":
        yield from stream_n8n_response(message)
    else:
        yield from stream_dify_response(message)


def parse_n8n_response(result: Any) -> str:
    """
    Parse n8n response format để extract text
    
    Args:
        result: Raw response từ n8n
        
    Returns:
        Extracted text string với proper line breaks
    """
    text = ""
    
    if isinstance(result, list) and len(result) > 0:
        # Format: [{'output': 'text'}] hoặc [{'text': 'text'}]
        first_item = result[0]
        if isinstance(first_item, dict):
            text = (
                first_item.get('output', '') or 
                first_item.get('text', '') or 
                first_item.get('content', '') or 
                first_item.get('response', '') or
                str(first_item)
            )
    elif isinstance(result, dict):
        # Format: {'output': 'text'} hoặc {'text': 'text'}
        text = (
            result.get('output', '') or 
            result.get('text', '') or 
            result.get('content', '') or 
            result.get('response', '') or
            result.get('message', '') or
            str(result)
        )
    else:
        text = str(result)
    
    # Fix line breaks: Convert literal \n to actual newlines
    # Then convert to Markdown line breaks (double space + newline)
    text = text.replace('\\n', '\n')  # Convert literal \n to actual newline
    text = text.replace('\n', '  \n')  # Convert to Markdown line break
    
    return text


def test_agent_connection(agent_type: str) -> tuple[bool, str]:
    """
    Test kết nối đến agent
    
    Args:
        agent_type: 'n8n' or 'dify'
        
    Returns:
        Tuple of (is_connected, status_message)
    """
    try:
        if agent_type == "n8n":
            # Simple health check for n8n
            response = requests.get(
                N8N_WEBHOOK_URL.replace("/webhook/calendar-chat", "/healthz"),
                timeout=2
            )
            return True, "✅ n8n connected"
        else:
            # Test Dify connection
            response = requests.get(
                DIFY_API_URL,
                headers={"Authorization": f"Bearer {DIFY_API_KEY}"},
                timeout=2
            )
            return True, "✅ Dify connected"
    except requests.exceptions.Timeout:
        return False, f"⚠️ {agent_type} timeout"
    except Exception as e:
        logger.error(f"{agent_type} connection error: {str(e)}")
        return False, f"❌ {agent_type} offline"


@st.dialog("Thông báo pháp lý")
def show_disclaimer_dialog():
    st.caption("""
        Đây là một sản phẩm DEMO được phát triển nhằm mục đích minh họa khả năng tích hợp AI với lịch trình cá nhân.
        
        **Lưu ý:**
        - Dữ liệu có thể không chính xác 100%
        - Không sử dụng cho mục đích sản xuất thực tế
        - AI có thể đưa ra thông tin không chính xác
    """)


# Header với khoảng trắng
st.html(div(style=styles(font_size=rem(5), line_height=1))["📆"])

# Title row
title_row = st.container(horizontal=False, vertical_alignment="bottom")

with title_row:
    st.title("Calendar AI Assistant", anchor=False, width="stretch")
    st.caption("Trợ lý AI quản lý lịch trình cá nhân thông minh")

# Kiểm tra trạng thái tương tác
user_just_asked_initial_question = (
    "initial_question" in st.session_state and st.session_state.initial_question
)

user_just_clicked_suggestion = (
    "selected_suggestion" in st.session_state and st.session_state.selected_suggestion
)

user_first_interaction = (
    user_just_asked_initial_question or user_just_clicked_suggestion
)

has_message_history = len(st.session_state.messages) > 0

# Sidebar
with st.sidebar:
    st.header("Cấu hình")
    
    # Agent selection
    agent = st.radio(
        "Chọn AI Agent:",
        ["n8n", "dify"],
        key="agent_selector",
        horizontal=True,
        help="n8n: workflow tự build | Dify: low-code platform"
    )
    
    # Nếu đổi agent, reset conversation
    if agent != st.session_state.current_agent:
        st.session_state.current_agent = agent
        st.session_state.messages = []
        st.session_state.conversation_id = None  # Reset conversation for Dify
        st.info(f"Đã chuyển sang {agent.upper()}")
        time.sleep(0.5)
        st.rerun()
    
    st.divider()
    
    # Connection status
    st.subheader("Trạng thái kết nối")
    
    with st.spinner("Đang kiểm tra..."):
        is_connected, status_msg = test_agent_connection(st.session_state.current_agent)
    
    if is_connected:
        st.success(status_msg)
    else:
        st.error(status_msg)
    
    # Show current agent info
    if st.session_state.current_agent == "n8n":
        with st.expander("ℹ️ n8n Info"):
            st.caption(f"**Endpoint:** {N8N_WEBHOOK_URL[:50]}...")
            st.caption(f"**User ID:** {st.session_state.user_id}")
    else:
        with st.expander("ℹ️ Dify Info"):
            st.caption(f"**Endpoint:** {DIFY_API_URL}")
            st.caption(f"**User ID:** {st.session_state.user_id}")
            if st.session_state.conversation_id:
                st.caption(f"**Conversation:** {st.session_state.conversation_id[:20]}...")
    
    st.divider()
    
    # Clear chat button
    if st.button("Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.success("Đã xóa lịch sử chat")
        time.sleep(0.5)
        st.rerun()
    
    st.divider()
    
    # Debug mode
    with st.expander("🔧 Debug"):
        debug_mode = st.checkbox("Show debug info", key="debug_mode")
        
        if debug_mode:
            st.caption("**Session State:**")
            st.json({
                "current_agent": st.session_state.current_agent,
                "user_id": st.session_state.user_id,
                "conversation_id": st.session_state.conversation_id,
                "message_count": len(st.session_state.messages)
            })
            
            st.divider()
            
            # Test n8n
            if st.button("🧪 Test n8n Connection"):
                with st.spinner("Testing n8n..."):
                    try:
                        agent = get_n8n_agent()
                        test_response = agent.send_request(
                            {"message": "test", "user_id": "debug_test"},
                            stream=False
                        )
                        result = test_response.json()
                        st.success("✅ n8n response received")
                        
                        with st.expander("Raw Response"):
                            st.json(result)
                        
                        parsed = parse_n8n_response(result)
                        st.text_area("Parsed text:", parsed, height=150)
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            
            # Test Dify
            if st.button("🧪 Test Dify Connection"):
                with st.spinner("Testing Dify..."):
                    try:
                        agent = get_dify_agent()
                        
                        # Test non-streaming first
                        response = agent.send_request(
                            query="test",
                            user_id="debug_test",
                            response_mode="blocking"
                        )
                        result = response.json()
                        st.success("✅ Dify response received (blocking mode)")
                        
                        with st.expander("Blocking Response"):
                            st.json(result)
                        
                        # Test streaming
                        st.info("Testing streaming mode...")
                        events = []
                        stream = agent.chat(
                            query="Hello, this is a test",
                            user_id="debug_test",
                            streaming=True
                        )
                        
                        for idx, event in enumerate(stream):
                            events.append(event)
                            if idx >= 5:  # Limit to 5 events for debug
                                break
                        
                        st.success(f"✅ Received {len(events)} SSE events")
                        with st.expander("SSE Events"):
                            for i, evt in enumerate(events):
                                st.json({f"Event {i}": evt})
                                
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

# Hiển thị UI khi chưa có câu hỏi
if not user_first_interaction and not has_message_history:
    with st.container():
        st.chat_input(
            "Đặt câu hỏi hoặc yêu cầu liên quan đến lịch trình của bạn",
            key="initial_question"
        )
        
        selected_suggestion = st.pills(
            label="Ví dụ",
            label_visibility="collapsed",
            options=SUGGESTIONS.keys(),
            key="selected_suggestion",
        )
    
    st.button(
        "&nbsp;:small[:gray[:material/balance: Thông báo pháp lý]]",
        type="tertiary",
        on_click=show_disclaimer_dialog,
    )
    
    st.stop()

# Chat input ở cuối khi đã có câu hỏi
user_message = st.chat_input("Đặt câu hỏi tiếp theo...")

if not user_message:
    if user_just_asked_initial_question:
        user_message = st.session_state.initial_question
    if user_just_clicked_suggestion:
        user_message = SUGGESTIONS[st.session_state.selected_suggestion]

# Khởi tạo timestamp cho rate limiting
if "prev_question_timestamp" not in st.session_state:
    st.session_state.prev_question_timestamp = datetime.datetime.fromtimestamp(0)

# Hiển thị lịch sử chat
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Xử lý tin nhắn mới từ user
if user_message:
    # Fix LaTeX trong Markdown
    user_message = user_message.replace("$", r"\$")
    
    # Hiển thị tin nhắn user
    with st.chat_message("user"):
        st.markdown(user_message)
    
    # Thêm user message vào history ngay lập tức
    st.session_state.messages.append({
        "role": "user",
        "content": user_message
    })
    
    # Hiển thị response từ assistant
    with st.chat_message("assistant"):
        # Rate limiting
        question_timestamp = datetime.datetime.now()
        time_diff = question_timestamp - st.session_state.prev_question_timestamp
        st.session_state.prev_question_timestamp = question_timestamp
        
        if time_diff < MIN_TIME_BETWEEN_REQUESTS:
            with st.spinner("Đang chờ..."):
                time.sleep((MIN_TIME_BETWEEN_REQUESTS - time_diff).total_seconds())
        
        # Clean message
        clean_message = user_message.replace("'", "")
        
        # Stream response từ agent
        try:
            with st.spinner(f"{st.session_state.current_agent.upper()} đang suy nghĩ..."):
                # Container để fix ghost message bug
                response_container = st.empty()
                full_response = ""
                
                # Stream response
                for chunk in get_ai_response_stream(clean_message):
                    full_response += chunk
                    response_container.markdown(full_response + "▌")
                
                # Final response without cursor
                response_container.markdown(full_response)
                
                # Thêm assistant response vào history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response
                })
                
        except Exception as e:
            error_msg = f"❌ Lỗi: {str(e)}"
            st.error(error_msg)
            logger.error(f"Error processing message: {str(e)}")
            
            # Thêm error message vào history
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })