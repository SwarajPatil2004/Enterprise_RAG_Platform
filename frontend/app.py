import streamlit as st
import requests
import json
import os
import jwt
import pandas as pd

API = os.getenv("API_URL", "http://localhost:8000")

def set_token(token: str):
    st.session_state["token"] = token

def set_user_info(user_info: dict):
    st.session_state["user_info"] = user_info

def auth_headers():
    t = st.session_state.get("token")
    return {"Authorization": f"Bearer {t}"} if t else {}

def get_user_info():
    """Decode basic user info from token for UI display."""
    if "token" not in st.session_state:
        return None
    try:
        # Decode JWT payload (no signature check for UI validity, avoiding separate secret management in frontend)
        token = st.session_state["token"]
        payload = jwt.decode(token, options={"verify_signature": False})
        return {
            "user_id": payload.get("user_id"),
            "tenant_id": payload.get("tenant_id"),
            "role": payload.get("role"),
            "groups": payload.get("groups", [])
        }
    except:
        return None

st.set_page_config(page_title="Enterprise RAG", layout="wide")
st.title("🏢 Enterprise RAG Platform ($0 Local)")

# Sidebar navigation
page = st.sidebar.selectbox("Navigate", ["🔐 Login", "📤 Upload", "💬 Chat", "📊 Admin"])

if page == "🔐 Login":
    st.header("Login")
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Username", placeholder="t1_admin, t1_member, etc.")
    with col2:
        password = st.text_input("Password", type="password", placeholder="pass")
    
    if st.button("🚀 Login", type="primary"):
        try:
            r = requests.post(f"{API}/auth/login", json={"username": username, "password": password})
            if r.status_code == 200:
                set_token(r.json()["access_token"])
                set_user_info(get_user_info())
                st.success(f"✅ Logged in as {username}")
                st.rerun()
            else:
                st.error(f"❌ Login failed: {r.status_code} - {r.text}")
        except Exception as e:
            st.error(f"❌ Backend not running? {e}")

elif "token" in st.session_state:
    # User is logged in
    user_info = get_user_info()
    if not user_info:
        st.error("Invalid token. Please login again.")
        st.rerun()
    
    st.sidebar.success(f"✅ Logged in")
    st.sidebar.markdown(f"**Tenant:** {user_info['tenant_id']}")
    st.sidebar.markdown(f"**Role:** {user_info['role']}")
    st.sidebar.markdown(f"**Groups:** {', '.join(user_info['groups']) if user_info['groups'] else 'None'}")
    
    if page == "📤 Upload":
        st.header("📤 Upload Documents")
        tab1, tab2 = st.tabs(["🌐 URL", "📄 PDF"])
        
        with tab1:
            st.subheader("Ingest from URL")
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Document Title", key="url_title")
                url = st.text_input("URL", placeholder="https://example.com/article")
            with col2:
                roles = st.text_input("Roles Allowed", value="member", 
                                    help="comma separated: member,admin")
                allowed_users = st.text_input("Allowed Users (user_ids)", value="", 
                                            help="comma separated: 1,2,3")
                allowed_groups = st.text_input("Allowed Groups", value="", 
                                             help="comma separated: hr,finance")
                sensitive = st.checkbox("🔒 Sensitive (admin-only)")
            
            if st.button("🚀 Ingest URL", type="primary"):
                if title and url:
                    with st.spinner("Extracting text..."):
                        r = requests.post(
                            f"{API}/documents/upload_url",
                            params={
                                "title": title,
                                "url": url, 
                                "roles_allowed": roles,
                                "allowed_users": allowed_users,
                                "allowed_groups": allowed_groups,
                                "sensitive": sensitive
                            },
                            headers=auth_headers(),
                        )
                    if r.status_code == 200:
                        st.success(r.json())
                    else:
                        st.error(r.json().get("detail", r.text))

        with tab2:
            st.subheader("Upload PDF")
            uploaded_file = st.file_uploader("Choose PDF", type="pdf")
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Document Title", key="pdf_title")
            with col2:
                roles = st.text_input("Roles Allowed", value="member")
                allowed_users = st.text_input("Allowed Users (user_ids)", value="")
                allowed_groups = st.text_input("Allowed Groups", value="")
                sensitive = st.checkbox("🔒 Sensitive")
            
            if uploaded_file and title and st.button("🚀 Upload PDF", type="primary"):
                with st.spinner("Processing PDF..."):
                    # Fix: Explicitly send filename and MIME type so backend validation passes
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    data = {
                        "title": title,
                        "roles_allowed": roles,
                        "allowed_users": allowed_users,
                        "allowed_groups": allowed_groups,
                        "sensitive": sensitive
                    }
                    r = requests.post(
                        f"{API}/documents/upload_pdf",
                        files=files,
                        data=data,
                        headers=auth_headers()
                    )
                if r.status_code == 200:
                    st.success(r.json())
                else:
                    try:
                        err_msg = r.json().get("detail", r.text)
                    except ValueError:
                        err_msg = r.text or f"Error {r.status_code}"
                    st.error(err_msg)

    elif page == "💬 Chat":
        st.header("💬 Ask Questions")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "citations" in message:
                    with st.expander("📚 Citations"):
                        for c in message["citations"]:
                            st.markdown(f"**{c['title']}** (chunk {c['chunk_id']})\n{c['snippet']}")

        if prompt := st.chat_input("Ask a question about your documents..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Searching secure documents..."):
                    r = requests.post(
                        f"{API}/chat/query",
                        json={"question": prompt},
                        headers=auth_headers()
                    )
                
                if r.status_code == 200:
                    data = r.json()
                    st.markdown(data["answer"])
                    
                    msg = {
                        "role": "assistant", 
                        "content": data["answer"],
                        "citations": data["citations"]
                    }
                    st.session_state.messages.append(msg)
                else:
                    st.error("Chat failed")
                    st.session_state.messages.append({"role": "assistant", "content": "Error"})
            
            st.rerun()

    elif page == "📊 Admin":
        st.header("🔐 Admin Panel")
        
        # Admin-only warning
        if user_info["role"] != "admin":
            st.warning("⚠️ Admin panel visible only for convenience. Backend enforces access.")
        
        tab1, tab2 = st.tabs(["📈 Audit Logs", "⚙️ Settings"])
        
        with tab1:
            st.subheader("📊 Audit Logs (Last 100)")
            
            limit = st.slider("Number of logs", 10, 500, 100)
            refresh = st.button("🔄 Refresh Logs", type="secondary")
            
            if refresh or "audit_data" not in st.session_state:
                try:
                    r = requests.get(
                        f"{API}/admin/audit", 
                        headers=auth_headers(), 
                        params={"limit": limit}
                    )
                    if r.status_code == 200:
                        st.session_state["audit_data"] = r.json()["items"]
                        st.success(f"✅ Loaded {len(st.session_state['audit_data'])} audit records")
                    else:
                        st.error(f"❌ Failed to load audit: {r.status_code} - {r.text}")
                except Exception as e:
                    st.error(f"❌ Network error: {e}")
            
            if "audit_data" in st.session_state and st.session_state["audit_data"]:
                df_data = []
                for audit in st.session_state["audit_data"]:
                    docs = [f"{d['doc_id']}-{d['chunk_id']}" for d in audit["retrieved"]]
                    df_data.append({
                        "ID": audit["audit_id"],
                        "User ID": audit["user_id"],
                        "Question": audit["question"][:100] + "..." if len(audit["question"]) > 100 else audit["question"],
                        "Docs Retrieved": f"{len(audit['retrieved'])} chunks: {', '.join(docs[:3])}",
                        "Timestamp": audit["created_at"][:19]
                    })
                
                st.dataframe(df_data, use_container_width=True, hide_index=True)
                
                # Metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Queries", len(st.session_state["audit_data"]))
                with col2:
                    st.metric("Avg Chunks Retrieved", 
                            sum(len(a["retrieved"]) for a in st.session_state["audit_data"]) / len(st.session_state["audit_data"]))
                with col3:
                    st.metric("Newest", st.session_state["audit_data"][0]["created_at"][:19])
                
                # Download CSV
                csv = pd.DataFrame(df_data).to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"audit_logs_{user_info['tenant_id']}.csv",
                    mime="text/csv"
                )
            else:
                st.info("👈 Click 'Refresh Logs' to load audit data")
        
        with tab2:
            st.subheader("⚙️ Admin Settings")
            st.info("Future: Document management, user groups, retention policies")
    
    # Logout button
    if st.sidebar.button("🚪 Logout"):
        for key in ["token", "user_info", "audit_data", "messages"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

else:
    st.info("👈 Please login to continue")