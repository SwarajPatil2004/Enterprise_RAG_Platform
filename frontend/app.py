import streamlit as st
import requests

API = "http://localhost:8000"

def set_token(token: str):
    st.session_state["token"] = token

def auth_headers():
    t = st.session_state.get("token")
    return {"Authorization": f"Bearer {t}"} if t else {}

st.title("Enterprise RAG Platform (Local)")

page = st.sidebar.selectbox("Page", ["Login", "Upload", "Chat"])

if page == "Login":
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
        if r.status_code == 200:
            set_token(r.json()["access_token"])
            st.success("Logged in")
        else:
            st.error("Login failed")

elif page == "Upload":
    st.write("Upload a URL (PDF upload can be added similarly).")
    title = st.text_input("Document title")
    url = st.text_input("URL")
    roles = st.text_input("roles_allowed (comma)", value="member")
    sensitive = st.checkbox("Mark as sensitive")
    if st.button("Ingest URL"):
        r = requests.post(
            f"{API}/documents/upload_url",
            params={"title": title, "url": url, "roles_allowed": roles, "sensitive": sensitive},
            headers=auth_headers(),
        )
        st.write(r.status_code, r.text)

elif page == "Chat":
    q = st.text_input("Ask a question")
    if st.button("Ask"):
        r = requests.post(f"{API}/chat/query", json={"question": q}, headers=auth_headers())
        if r.status_code == 200:
            data = r.json()
            st.subheader("Answer")
            st.write(data["answer"])
            st.subheader("Citations")
            for c in data["citations"]:
                st.write(f"- {c['title']} | chunk {c['chunk_id']} | {c['snippet']}")
        else:
            st.error(r.text)