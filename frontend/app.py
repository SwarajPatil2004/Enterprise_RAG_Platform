import streamlit as st
import requests

API = "http://localhost:8000"

def set_token(token: str):
    st.session_state["token"] = token

def auth_headers():
    t = st.session_state.get("token")
    return {"Authorization": f"Bearer {t}"} if t else {}

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
                st.success(f"✅ Logged in as {username}")
                st.rerun()
            else:
                st.error("❌ Login failed")
        except Exception as e:
            st.error(f"Backend not running? {e}")

elif "token" in st.session_state:
    user_tenant = st.session_state.get("tenant", "unknown")
    st.sidebar.success(f"✅ Logged in\nTenant: {user_tenant}")
    
    if page == "📤 Upload":
        st.header("Upload Documents")
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
                sensitive = st.checkbox("🔒 Sensitive (admin-only)")
            
            if st.button("🚀 Ingest URL", type="primary"):
                if title and url:
                    with st.spinner("Extracting text..."):
                        r = requests.post(
                            f"{API}/documents/upload_url",
                            data={
                                "title": title,
                                "url": url, 
                                "roles_allowed": roles,
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
                sensitive = st.checkbox("🔒 Sensitive")
            
            if uploaded_file and title and st.button("🚀 Upload PDF", type="primary"):
                with st.spinner("Processing PDF..."):
                    files = {"file": uploaded_file.getvalue()}
                    data = {
                        "title": title,
                        "roles_allowed": roles,
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
                    st.error(r.json().get("detail", r.text))

    elif page == "💬 Chat":
        st.header("💬 Ask Questions")
        
        # Chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "citations" in message:
                    with st.expander("📚 Citations"):
                        for c in message["citations"]:
                            st.markdown(f"**{c['title']}** (chunk {c['chunk_id']})\n{c['snippet']}")

        # Chat input
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