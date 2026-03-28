import asyncio
import streamlit as st
from app.main import build_feature


st.title("AutoDev")
st.subheader("Autonomous Software Engineering Team")
st.write("An AI-powered software engineering team that designs, builds, reviews, tests, and deploys code end-to-end.")

feature = st.text_area("Describe what you want to build?", placeholder="e.g. Build a SaaS app with auth, payments, and dashboard")

session_id = st.text_input("Session ID (optional)", value="default")

if st.button("Build with AutoDev"):
    if feature:
        with st.spinner("Agents are working on your request..."):
            result = asyncio.run(build_feature(feature, session_id=session_id or "default"))

        st.write("### Result")

        if result:
            st.json(result)
        else:
            st.warning("No result returned")
