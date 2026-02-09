import streamlit as st
from src.api_client import BackendAPIClient
from datetime import datetime, timedelta

def show_token_input_page():
    """
    Display page for Calendar Service login
    """
    st.title("Kết nối Calendar Service")
    
    api_client = BackendAPIClient()
    
    # Check current token status
    try:
        status = api_client.check_token_status()
        
        if status.get("has_token"):
            st.success("Bạn đã kết nối với Calendar Service")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Trạng thái", "Hợp lệ" if status.get("is_valid") else "Hết hạn")
            with col2:
                if status.get("expires_at"):
                    expires = datetime.fromisoformat(status["expires_at"].replace("Z", ""))
                    st.metric("Hết hạn lúc", expires.strftime("%Y-%m-%d %H:%M"))
            
            if status.get("calendar_user_email"):
                st.info(f"Calendar Email: {status['calendar_user_email']}")
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Làm mới Token", use_container_width=True):
                    with st.spinner("Đang làm mới..."):
                        try:
                            result = api_client.refresh_token()
                            st.success("Đã làm mới token!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Lỗi: {str(e)}")
            
            with col2:
                if st.button("Ngắt kết nối", use_container_width=True, type="secondary"):
                    try:
                        api_client.delete_token()
                        st.success("Đã ngắt kết nối!")
                        st.session_state.token_connected = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Lỗi: {str(e)}")
            
            st.divider()
            
            # Mark as connected
            st.session_state.token_connected = True
            return  # Don't show login form if already connected
    
    except Exception as e:
        st.warning(f"Không thể kiểm tra token: {str(e)}")
    
    # Calendar Service Login Form
    st.subheader("Đăng nhập Calendar Service")
    
    st.info("""
    **Hướng dẫn:**
    1. Nhập thông tin đăng nhập Calendar Service của bạn
    2. Hệ thống sẽ tự động lấy và lưu tokens
    3. Tokens sẽ được tự động làm mới khi hết hạn
    """)
    
    # Login method selector
    login_method = st.radio(
        "Chọn phương thức:",
        ["Đăng nhập Calendar Service", "Nhập token thủ công"],
        horizontal=True,
        help="Khuyến nghị: Đăng nhập tự động để hệ thống quản lý tokens"
    )
    
    if login_method == "Đăng nhập Calendar Service":
        # Auto login form
        with st.form("calendar_login_form"):
            st.caption("**Calendar Service Credentials**")
            
            calendar_email = st.text_input(
                "Email *",
                placeholder="user@example.com",
                help="Email bạn dùng để đăng nhập Calendar Service"
            )
            
            calendar_password = st.text_input(
                "Password *",
                type="password",
                placeholder="Mật khẩu Calendar Service",
                help="Mật khẩu sẽ được mã hóa và không lưu trữ"
            )
            
            submitted = st.form_submit_button("🔐 Đăng nhập & Kết nối", use_container_width=True)
            
            if submitted:
                if not calendar_email or not calendar_password:
                    st.error("❌ Vui lòng nhập đầy đủ thông tin")
                else:
                    try:
                        with st.spinner("Đang kết nối với Calendar Service..."):
                            # Call backend to login to Calendar Service
                            result = api_client.login_to_calendar_service(
                                email=calendar_email,
                                password=calendar_password
                            )
                            
                            st.success("Đã kết nối thành công với Calendar Service!")
                            st.balloons()
                            
                            # Mark as connected
                            st.session_state.token_connected = True
                            
                            # Show token info
                            with st.expander("Token Info"):
                                st.json({
                                    "email": result.get("calendar_user_email"),
                                    "expires_at": result.get("expires_at"),
                                    "is_active": result.get("is_active")
                                })
                            
                            # Redirect to chat after 2 seconds
                            st.info("Chuyển đến trang chat trong 2 giây...")
                            import time
                            time.sleep(2)
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"❌ Đăng nhập thất bại: {str(e)}")
                        
                        with st.expander("Chi tiết lỗi"):
                            st.code(str(e))
                            st.caption("""
                            **Có thể do:**
                            - Sai email hoặc mật khẩu
                            - Calendar Service không hoạt động
                            - Lỗi kết nối mạng
                            """)
    
    else:
        # Manual token input form
        with st.form("manual_token_form"):
            st.caption("**Nhập Token Thủ Công**")
            
            with st.expander("Cách lấy tokens", expanded=False):
                st.code("""
# Gọi API login của Calendar Service:
curl -X POST http://localhost:8000/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'

# Response:
{
  "access_token": "eyJhbGc...",
  "expires_in": 1800,
  "refresh_token": "abc123...",
  "token_type": "bearer"
}
                """)
            
            access_token = st.text_area(
                "Access Token *",
                height=100,
                placeholder="eyJhbGc...",
                help="Copy từ response của Calendar Service"
            )
            
            refresh_token = st.text_area(
                "Refresh Token *",
                height=100,
                placeholder="abc123...",
                help="Copy từ response của Calendar Service"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                expires_in_seconds = st.number_input(
                    "Expires In (seconds) *",
                    min_value=60,
                    max_value=604800,  # 7 days
                    value=1800,  # 30 minutes default
                    help="expires_in từ response"
                )
            
            with col2:
                calendar_email = st.text_input(
                    "Calendar Email",
                    placeholder="user@example.com",
                    help="Email trên Calendar Service (tùy chọn)"
                )
            
            notes = st.text_area(
                "Ghi chú",
                placeholder="VD: Token từ production, token test...",
                help="Ghi chú để nhớ token này (tùy chọn)"
            )
            
            submitted = st.form_submit_button("💾 Lưu Tokens", use_container_width=True)
            
            if submitted:
                if not access_token or not refresh_token:
                    st.error("❌ Vui lòng nhập đầy đủ Access Token và Refresh Token")
                else:
                    try:
                        with st.spinner("Đang lưu tokens..."):
                            api_client.save_calendar_token(
                                access_token=access_token.strip(),
                                refresh_token=refresh_token.strip(),
                                expires_in=expires_in_seconds,
                                calendar_user_email=calendar_email.strip() if calendar_email else None,
                                notes=notes.strip() if notes else None
                            )
                            
                            st.success("Đã lưu tokens thành công!")
                            st.balloons()
                            
                            # Mark as connected
                            st.session_state.token_connected = True
                            
                            # Redirect to chat
                            st.info("Chuyển đến trang chat trong 2 giây...")
                            import time
                            time.sleep(2)
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"❌ Lỗi khi lưu tokens: {str(e)}")


def check_token_connected():
    """
    Check if user has valid token
    
    Returns:
        True if user has valid token, False otherwise
    """
    return st.session_state.get("token_connected", False)