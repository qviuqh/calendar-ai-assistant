import streamlit as st
from src.api_client import BackendAPIClient
from datetime import datetime, timedelta

def show_token_input_page():
    """
    Display page for user to manually input calendar tokens
    """
    st.title("🔑 Cấu hình Calendar Token")
    
    api_client = BackendAPIClient()
    
    # Check current token status
    try:
        status = api_client.check_token_status()
        
        if status.get("has_token"):
            st.success("✅ Bạn đã có token được lưu")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Trạng thái", "Hợp lệ" if status.get("is_valid") else "Hết hạn")
            with col2:
                if status.get("expires_at"):
                    expires = datetime.fromisoformat(status["expires_at"].replace("Z", ""))
                    st.metric("Hết hạn lúc", expires.strftime("%Y-%m-%d %H:%M"))
            
            if status.get("calendar_user_email"):
                st.info(f"📧 Email: {status['calendar_user_email']}")
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Làm mới Token", use_container_width=True):
                    with st.spinner("Đang làm mới..."):
                        try:
                            result = api_client.refresh_token()
                            st.success("✅ Đã làm mới token!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Lỗi: {str(e)}")
            
            with col2:
                if st.button("🗑️ Xóa Token", use_container_width=True, type="secondary"):
                    try:
                        api_client.delete_token()
                        st.success("✅ Đã xóa token!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Lỗi: {str(e)}")
            
            st.divider()
    
    except Exception as e:
        st.warning(f"Không thể kiểm tra token: {str(e)}")
    
    # Token input form
    st.subheader("📝 Nhập Token Mới")
    
    with st.expander("ℹ️ Hướng dẫn lấy token", expanded=False):
        st.markdown(f"""
        ### Cách lấy Access Token và Refresh Token:
        
        1. Đăng nhập vào Calendar Service của bạn
        2. Vào phần **Settings** → **API Tokens**
        3. Tạo token mới hoặc copy token hiện có
        4. Nhập vào form dưới đây
        
        **Lưu ý:**
        - Access Token có thời hạn ngắn (thường 1-24 giờ)
        - Refresh Token có thời hạn dài (thường 30-90 ngày)
        - Hệ thống sẽ tự động làm mới Access Token khi hết hạn
        """)
    
    with st.form("token_input_form"):
        access_token = st.text_area(
            "Access Token *",
            height=100,
            placeholder="Nhập access token từ calendar service...",
            help="Token này dùng để truy cập API"
        )
        
        refresh_token = st.text_area(
            "Refresh Token *",
            height=100,
            placeholder="Nhập refresh token từ calendar service...",
            help="Token này dùng để lấy access token mới khi hết hạn"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            expires_in_hours = st.number_input(
                "Thời hạn Access Token (giờ) *",
                min_value=1,
                max_value=168,  # 7 days
                value=24,
                help="Số giờ cho đến khi access token hết hạn"
            )
        
        with col2:
            calendar_email = st.text_input(
                "Email trên Calendar Service",
                placeholder="user@example.com",
                help="Email bạn dùng trên calendar service (tùy chọn)"
            )
        
        notes = st.text_area(
            "Ghi chú",
            placeholder="VD: Token từ production server, token test, etc.",
            help="Ghi chú để nhớ token này (tùy chọn)"
        )
        
        submitted = st.form_submit_button("💾 Lưu Token", use_container_width=True)
        
        if submitted:
            if not access_token or not refresh_token:
                st.error("❌ Vui lòng nhập đầy đủ Access Token và Refresh Token")
            else:
                try:
                    with st.spinner("Đang lưu token..."):
                        # Convert hours to seconds
                        expires_in = expires_in_hours * 3600
                        
                        api_client.save_calendar_token(
                            access_token=access_token.strip(),
                            refresh_token=refresh_token.strip(),
                            expires_in=expires_in,
                            calendar_user_email=calendar_email.strip() if calendar_email else None,
                            notes=notes.strip() if notes else None
                        )
                        
                        st.success("✅ Đã lưu token thành công!")
                        st.balloons()
                        
                        # Mark as token connected
                        st.session_state.token_connected = True
                        
                        # Redirect to chat after 2 seconds
                        st.info("Chuyển đến trang chat trong 2 giây...")
                        import time
                        time.sleep(2)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Lỗi khi lưu token: {str(e)}")
    
    # Quick test tokens (for development)
    if st.checkbox("🧪 Developer Mode: Load Test Tokens"):
        st.warning("⚠️ Chỉ dùng cho testing!")
        
        if st.button("Load Demo Tokens"):
            st.code("""
access_token = "demo_access_token_12345"
refresh_token = "demo_refresh_token_67890"
expires_in = 86400  # 24 hours
            """)
            
            st.info("Copy các giá trị trên vào form để test")

def check_token_connected():
    """
    Check if user has valid token
    
    Returns:
        True if user has valid token, False otherwise
    """
    return st.session_state.get("token_connected", False)