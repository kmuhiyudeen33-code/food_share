import firebase_admin
import streamlit as st
import json
from firebase_admin import firestore, credentials, auth, exceptions

def app():
    st.set_page_config(
        page_title="Report a Bug / Suggestion",
        layout="wide",
    )

    if not firebase_admin._apps:
        firebase_creds_dict = dict(st.secrets["gcp_service_account"])   
        cred = credentials.Certificate(firebase_creds_dict)
        firebase_admin.initialize_app(cred)
    
    if 'db' not in st.session_state:
        st.session_state.db = ''

    db=firestore.client()
    st.session_state.db=db

    st.title("NeighborFood Share - Bug Report / Suggestion Page")
    st.write("If you encounter any bugs or issues while using the NeighborFood Share app, please report them here. Your feedback is valuable in helping us improve the app and provide a better experience for all users.")
    st.write("Our Email is: kmuhiyudeen33@gmail.com")

    st.link_button("Click here to email us", "mailto:kmuhiyudeen33@gmail.com")
    
if __name__ == "__main__":
    app()