import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, auth, firestore, exceptions
from streamlit_option_menu import option_menu
import Bug_Report, About_Us, Account_Settings
from firebase_admin._auth_utils import EmailAlreadyExistsError
import os
from google.cloud import storage
from google.oauth2 import service_account
import pandas as pd
import io

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "firebase-adminsdk-fbsvc@foodshare-ee612.iam.gserviceaccount.com.json"
credentials_dict = dict(st.secrets["gcp_service_account"])
service_account_credentials = service_account.Credentials.from_service_account_info(credentials_dict)

def initialize_firebase():
    if not firebase_admin._apps:
        firebase_creds_dict = dict(st.secrets["gcp_service_account"])   
        cred = credentials.Certificate(firebase_creds_dict)
        firebase_admin.initialize_app(cred)
    return firebase_admin.get_app()
app = initialize_firebase()

def show_main():
    st.set_page_config(
        page_title="Login / Sign Up",
        layout="centered",
    )

    if not firebase_admin._apps:
        firebase_creds_dict = dict(st.secrets["gcp_service_account"])   
        cred = credentials.Certificate(firebase_creds_dict)
        firebase_admin.initialize_app(cred)

db = firestore.client()

def show_main():
    st.title("Thank you for choosing food share")
    st.subheader("Note: if you are logging in, just use your email and the custom password you used to sign up.")

    choice = st.selectbox("Login/Signup", ["Login", "Signup"])

    if choice == "Login":
        email = st.text_input("Custom Email Address", key="login_email")
        password = st.text_input("Custom Password", type="password", key="login_password")

        if st.button("Login"):
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                try:
                    user_record = auth.get_user_by_email(email)
                except Exception as auth_err:
                    st.error("Login failed. Email not found in Authentication records.")
                    return

                login_success = False
                logged_in_uid = user_record.uid
                logged_in_username = None
                logged_in_email = None
                logged_in_password = None

                try:
                    user_docs = db.collection("users").where("email", "==", email).limit(1).get()
                    if len(user_docs) > 0:
                        user_snapshot = user_docs[0]
                        user_data = user_snapshot.to_dict()
                        if user_data and user_data.get("password") == password:
                            login_success = True
                            logged_in_username = user_data.get("username")
                            logged_in_email = user_data.get("email")
                            logged_in_password = user_data.get("password")
                        else:
                            st.error("Login failed. Incorrect password.")
                    else:
                        st.error("Login failed. Account record not found in database.")
                except Exception as db_err:
                    print(f"Database error details: {db_err}")
                    st.error("A database connectivity error occurred. Please try again.")

                if login_success:
                    st.session_state.uid = logged_in_uid
                    st.session_state.username = logged_in_username
                    st.session_state.email = logged_in_email
                    st.session_state.password = logged_in_password
                    st.success("Login successful!")
                    st.switch_page("pages/Home_Page.py")
    else:
        email = st.text_input("Custom Email Address", key="signup_email")
        password = st.text_input("Custom Password", type="password", key="signup_password")
        username = st.text_input("Enter your custom username", key="signup_username")

        storage_client = storage.Client(credentials=service_account_credentials, project="foodshare-ee612")
        BUCKET_NAME = "foodshare"
        def upload_to_gcs(bucket_name, folder_name, streamlit_file, file_name):
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(folder_name + "/" + file_name + ".png")
            blob.upload_from_file(streamlit_file)

        picture_uploader = st.file_uploader("Upload a profile picture", type=["jpg", "jpeg", "png"], key="signup_pic")
        if picture_uploader is not None:
            picture_uploader.seek(0)
            st.image(picture_uploader, caption="Uploaded Profile Picture", width=110)

        if st.button("Create my Foodshare account"):
            if not email or not password or not username:
                st.error("All fields are required.")
                return
            try:
                if picture_uploader is not None:
                    with st.spinner("Uploading..."):
                        upload_to_gcs(BUCKET_NAME, folder_name="profile_pictures", streamlit_file=picture_uploader, file_name=username)
                user = auth.create_user(email=email, password=password, uid=username)
                db.collection("users").document(username).set({
                    "email": email,
                    "username": username,
                    "password": password,
                })
                st.session_state.uid = username
                st.session_state.username = username
                st.session_state.email = email
                st.session_state.password = password
                st.success("Account created successfully!")
                st.markdown(f"Your unique password is: **{password}**. Please remember this for future logins.")
                st.switch_page("pages/Home_Page.py")
            except Exception as e:
                error_code = getattr(e, 'code', None)
                if 'EMAIL_EXISTS' in str(e):
                    st.warning('An account with this email already exists. Please sign in.')
                elif error_code in ['UID_ALREADY_EXISTS', 'DUPLICATE_LOCAL_ID'] or "uid already exists" in str(e).lower():
                    st.warning('This username is already taken. Please choose another one.')
                else:
                    st.error(f"An error occurred: {e}")
                return

def show_bug_report():
    Bug_Report.app()

def show_about_us():
    About_Us.app()

def main():
    with st.sidebar:
        selected = option_menu(
            menu_title="Main Menu",
            options=["Login / Sign Up", "Bug Report or Suggestion", "About Us"],
            icons=["key", "bug", "info-circle"],
            default_index=0,
            key="menu_selection",
            styles={
                "container": {"padding": "5!important", "background-color": "black"},
                "icon": {"color": "white", "font-size": "23px"},
                "nav-link": {"color": "white", "font-size": "20px", "text-align": "left", "margin": "0px", "--hover-color": "blue"},
                "nav-link-selected": {"background-color": "#02ab21"},
            }
        )
    
    if selected == "Login / Sign Up":
        show_main()
    elif selected == "Bug Report or Suggestion":
        show_bug_report()
    elif selected == "About Us":
        show_about_us()

if __name__ == "__main__":
    main()