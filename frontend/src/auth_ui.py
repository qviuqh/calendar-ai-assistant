import streamlit as st
from src.api_client import BackendAPIClient

def show_auth_page():
    """
    Display authentication page (Login/Register)
    """
    st.title("Calendar AI Assistant")
    
    # Initialize API client
    api_client = BackendAPIClient()
    
    # Check backend health
    if not api_client.health_check():
        st.error("Cannot connect to backend server. Please check if the server is running.")
        st.stop()
    
    # Tabs for Login and Register
    tab1, tab2 = st.tabs(["Đăng nhập", "Đăng ký"])
    
    with tab1:
        with st.form("login_form"):
            st.subheader("Đăng nhập")
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
                            
                            st.success("Đăng nhập thành công!")
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
                            st.success("Đăng ký thành công! Vui lòng đăng nhập.")
                    except Exception as e:
                        st.error(f"Đăng ký thất bại: {str(e)}")

def show_oauth_connect():
    """
    Display OAuth connection page
    """
    st.title("📅 Kết nối Google Calendar")
    
    api_client = BackendAPIClient()
    
    st.info("Để sử dụng Calendar AI Assistant, bạn cần kết nối với Google Calendar của mình.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Kết nối Calendar", use_container_width=True):
            try:
                oauth_url = api_client.get_google_oauth_url()
                st.markdown(f"[Click vào đây để kết nối]({oauth_url})")
                st.info("Sau khi kết nối xong, bạn sẽ được chuyển về trang này.")
            except Exception as e:
                st.error(f"Lỗi: {str(e)}")
    
    with col2:
        if st.button("Bỏ qua (Dùng chế độ Demo)", use_container_width=True):
            st.session_state.oauth_connected = True
            st.rerun()

def check_authentication():
    """
    Check if user is authenticated
    
    Returns:
        True if authenticated, False otherwise
    """
    return st.session_state.get("authenticated", False)

def logout():
    """
    Logout user
    """
    st.session_state.authenticated = False
    st.session_state.auth_token = None
    st.session_state.oauth_connected = False
    st.session_state.messages = []
    st.rerun()