import streamlit as st
from src.api_client import BackendAPIClient

def show_auth_page():
    """
    Display webapp authentication page (Login/Register)
    This is called by app.py when user is not authenticated.
    """
    # Initialize API client
    api_client = BackendAPIClient()
    
    # Check backend health
    if not api_client.health_check():
        st.error("⚠️ Cannot connect to backend server. Please check if the server is running.")
        st.code("docker-compose up -d")
        st.stop()
    
    st.title("📆 Calendar AI Assistant")
    st.caption("Trợ lý AI quản lý lịch trình cá nhân thông minh")
    
    # Tabs for Login and Register
    tab1, tab2 = st.tabs(["Đăng nhập", "Đăng ký"])
    
    with tab1:
        with st.form("login_form"):
            st.subheader("Đăng nhập Webapp")
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            
            submitted = st.form_submit_button("Đăng nhập", use_container_width=True)
            
            if submitted:
                if not email or not password:
                    st.error("Vui lòng nhập đầy đủ thông tin")
                else:
                    try:
                        with st.spinner("Đang đăng nhập..."):
                            token = api_client.login(email, password)
                            
                            # Save token to session
                            st.session_state.auth_token = token
                            st.session_state.authenticated = True
                            
                            st.success("✅ Đăng nhập thành công!")
                            st.info("Tiếp theo: Kết nối với Calendar Service...")
                            import time
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Đăng nhập thất bại: {str(e)}")
    
    with tab2:
        with st.form("register_form"):
            st.subheader("Đăng ký tài khoản mới")
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Password", type="password", key="register_password")
            password_confirm = st.text_input("Xác nhận Password", type="password", key="register_password_confirm")
            
            submitted = st.form_submit_button("Đăng ký", use_container_width=True)
            
            if submitted:
                if not email or not password or not password_confirm:
                    st.error("Vui lòng nhập đầy đủ thông tin")
                elif password != password_confirm:
                    st.error("Mật khẩu xác nhận không khớp")
                elif len(password) < 8:
                    st.error("Mật khẩu phải có ít nhất 8 ký tự")
                else:
                    try:
                        with st.spinner("Đang đăng ký..."):
                            api_client.register(email, password)
                            st.success("✅ Đăng ký thành công! Vui lòng đăng nhập.")
                    except Exception as e:
                        st.error(f"❌ Đăng ký thất bại: {str(e)}")


def check_webapp_authentication():
    """
    Check if user is authenticated to webapp
    
    Returns:
        True if authenticated, False otherwise
    """
    return st.session_state.get("authenticated", False)


def logout():
    """
    Logout user from both webapp and Calendar Service
    """
    st.session_state.authenticated = False
    st.session_state.auth_token = None
    st.session_state.token_connected = False
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.rerun()