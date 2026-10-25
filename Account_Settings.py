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

BUCKET_NAME = "foodshare"
storage_client = storage.Client(credentials=service_account_credentials, project="foodshare-ee612")

def app():
    st.set_page_config(
        page_title="Account Settings",
        layout="wide",
    )

    if not firebase_admin._apps:
        firebase_creds_dict = dict(st.secrets["gcp_service_account"])   
        cred = credentials.Certificate(firebase_creds_dict)
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    user_id = st.session_state.get("uid", "Not Set")
    username = st.session_state.get("username", "Not Set")
    email = st.session_state.get("email", "Not Set")
    password = st.session_state.get("password", "Not Set")

    if not user_id or user_id == "Not Set":
        st.error(f"Debug Info: Redirecting because UID is missing. Current Session State keys: {list(st.session_state.keys())}")
        st.switch_page("main.py")

    st.title("Account Settings")
    st.write("This page is for managing your account settings. You can update your email, password, and other personal information here.")

    choice = st.selectbox("Which one do you want to edit?", ["View", "Edit Email", "Edit Username", "Edit Password", "Edit Profile Picture", "Delete Account"])

    if choice == "View":
        st.write(f"**Current Email:** {email}")
        st.write(f"**Current Username:** {username}")
        st.write(f"**Current Password:** {password}")
        def download_gcs_blob(bucket_name, blob_name):
            try:
                with st.spinner("Getting Profile Picture..."):
                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(blob_name)
                    file_bytes = blob.download_as_bytes()
                    return file_bytes, blob.content_type
            except Exception as e:
                error_code = getattr(e, 'code', None)
                print(f"Error fetching profile picture: {e}, error code: {error_code}")
                if error_code != 404:
                    st.error(f"Failed to fetch Profile Picture: {e}")
                return None, None
            
        file_to_view = download_gcs_blob(BUCKET_NAME, f"profile_pictures/{username}.png")
        if file_to_view[0] is not None:
            st.image(file_to_view[0], width=60)
        st.write(username)


    elif choice == "Edit Email":
        email_update = st.text_input("New email")
        if st.button ("Update my Foodshare account"):
            if not email_update:
                st.error("All fields are required.")
                return
            try:
                user = auth.update_user(uid=user_id, email=email_update)
                user_docs = db.collection("users").where("email", "==", email).limit(1).get()
                if len(user_docs) > 0:
                    doc_id = user_docs[0].id
                    db.collection("users").document(doc_id).update({
                        "email": email_update,
                    })
                st.success("Email updated successfully!")
            except Exception as e:
                st.error(f"An error occurred: {e}")
                
                st.session_state["email"] = email_update
                st.success("Email updated successfully!")
                st.rerun()
            except Exception as e:
                error_code = getattr(e, 'code', None)
                if error_code == 'EMAIL_EXISTS':
                    st.warning('An account with this email already exists. Please sign in.')
                elif error_code in ['UID_ALREADY_EXISTS', 'DUPLICATE_LOCAL_ID'] or "uid already exists" in str(e).lower():
                    st.warning('This username is already taken. Please choose another one.')
                else:
                    st.error(f"An error occurred: {e}")
                return


    elif choice == "Edit Username":
        username_update = st.text_input("New username")
        if st.button ("Update my Foodshare account"):
            if not username_update:
                st.error("All fields are required.")
                return
            try:
                user = auth.update_user(uid=user_id, display_name=username_update,)
                user_docs = db.collection("users").where("email", "==", email).limit(1).get()
                if len(user_docs) > 0:
                    doc_id = user_docs[0].id
                    db.collection("users").document(doc_id).update({
                        "username": username_update,
                    })
                st.session_state["username"] = username_update
                st.success("Username updated successfully!")
                st.rerun()
            except Exception as e:
                error_code = getattr(e, 'code', None)
                if error_code == 'EMAIL_EXISTS':
                    st.warning('An account with this email already exists. Please sign in.')
                elif error_code in ['UID_ALREADY_EXISTS', 'DUPLICATE_LOCAL_ID'] or "uid already exists" in str(e).lower():
                    st.warning('This username is already taken. Please choose another one.')
                else:
                    st.error(f"An error occurred: {e}")
                return


    elif choice == "Edit Password":
        password_update = st.text_input("New password", type="password")
        if st.button("Update my Foodshare account"):
            if not password_update:
                st.error("All fields are required.")
            else:
                try:
                    user = auth.update_user(uid=user_id, password=password_update)
                    user_docs = db.collection("users").where("email", "==", email).limit(1).get()
                    if len(user_docs) > 0:
                        doc_id = user_docs[0].id
                        db.collection("users").document(doc_id).update({
                            "password": password_update,
                        })
                    
                    st.session_state["password"] = password_update
                    st.success("Password updated successfully!")
                    st.rerun()
                except Exception as e:
                    error_code = getattr(e, 'code', None)
                    if error_code == 'EMAIL_EXISTS':
                        st.warning('An account with this email already exists. Please sign in.')
                    elif error_code in ['UID_ALREADY_EXISTS', 'DUPLICATE_LOCAL_ID'] or "uid already exists" in str(e).lower():
                        st.warning('This username is already taken. Please choose another one.')
                    else:
                        st.error(f"An error occurred: {e}")
                    return

    elif choice == "Edit Profile Picture":
        picture_uploader = st.file_uploader("Upload a new profile picture", type=["jpg", "jpeg", "png"], key="edit_pic", width=300)
        if picture_uploader is not None:
            picture_uploader.seek(0)
            st.image(picture_uploader, caption="Uploaded Profile Picture", width=60)
            if st.button("Update my Foodshare account"):
                try:
                    def upload_to_gcs(bucket_name, streamlit_file):
                        bucket = storage_client.bucket(bucket_name)
                        blob = bucket.blob("profile_pictures/" + username + ".png")
                        blob.upload_from_file(streamlit_file)
                    upload_to_gcs(BUCKET_NAME, picture_uploader)
                    st.success("Profile picture updated successfully!")

                except Exception as e:
                    st.error(f"An error occurred: {e}")

    elif choice == "Delete Account":
        if "delete_clicked" not in st.session_state:
            st.session_state.delete_clicked = False
        if not st.session_state.delete_clicked:
            if st.button("Delete account"):
                st.session_state.delete_clicked = True
                st.rerun()

        if st.session_state.delete_clicked:
            st.warning("Are you sure you want to delete your account?")
            conf_col1, conf_col2 = st.columns(2)
            
            with conf_col1:
                if st.button("Yes, proceed", key=f"confirm_{username}"):
                    db.collection("users").document(username).delete

                    auth.delete_user(user_id)
                    st.session_state.delete_clicked = False 
                    st.success("Account deleted successfully!")
                    st.switch_page("main.py")
                    
            with conf_col2:
                if st.button("Cancel", key=f"cancel_{username}"):
                    st.session_state.delete_clicked = False
                    st.rerun()

if __name__ == "__main__":
    app()