import firebase_admin
import streamlit as st
import json
from firebase_admin import firestore, credentials, auth, exceptions

def app():
    st.set_page_config(
        page_title="About Us",
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

    st.title("NeighborFood Share - About Us Page")
    st.write("This app was made by Khwaja Kosgi for the Congressional App Challenge." )
    st.write("The purpose of this app is to help people in need and to reduce food wastage. We hope you find it useful and enjoy using it!")
    st.write("We were motivated to create this app because of the Congressional App Challenge.")