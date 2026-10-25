import streamlit as st
import firebase_admin
from firebase_admin import firestore
import os
from google.cloud import storage
from google.oauth2 import service_account
import pandas as pd
import io

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "firebase-adminsdk-fbsvc@foodshare-ee612.iam.gserviceaccount.com.json"
credentials_dict = dict(st.secrets["gcp_service_account"])
service_account_credentials = service_account.Credentials.from_service_account_info(credentials_dict)
storage_client = storage.Client(credentials=service_account_credentials, project="foodshare-ee612")
BUCKET_NAME = "foodshare"

def app():
    username = st.session_state.get("username", "Anoynomous") 
    
    st.title("Claimed Items")
    st.write("This page displays all the items that have been claimed by you below.")
    
    db = firestore.client()
    
    try:
        claimed_items_ref = db.collection("Claimed Items").where("claimed_by", "==", username).stream()
        claimed_docs = [(doc.id, doc.to_dict()) for doc in claimed_items_ref]
    except Exception as e:
        st.error(f"Error fetching claimed items: {e}")
        claimed_docs = []
        
    if not claimed_docs:
        st.info("You haven't selected any items to claim yet! Go back to Home to claim items.")
        return

    for doc_id, item in claimed_docs:
        item_id = item.get("item_id")
        title = item.get("title", "No Title")
        category = item.get("category", "No Category")
        location = item.get("location", "No Location")
        description = item.get("description", "No Description")
        posted_by_username = item.get("posted_by", "Unknown")

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

        with st.container():
            st.markdown(f"### {title}")
            st.write(f"**Category:** {category}")
            file_to_view_2 = download_gcs_blob(BUCKET_NAME, f"food_pictures/{doc_id}.png")
            if file_to_view_2[0] is not None:
                st.image(file_to_view_2[0], width=300)
            st.write(f"**Location:** {location}")
            st.write(f"**Description:** {description}")
            st.write(f"**Originally posted by:**")
            st.write(posted_by_username)
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

                file_to_view = download_gcs_blob(BUCKET_NAME, f"profile_pictures/{posted_by_username}.png")
                if file_to_view[0] is not None:
                    st.image(file_to_view[0], width=60)
                st.write(posted_by_username)

            
            if st.button("Unclaim Item", key=f"btn_unclaim_{doc_id}"):
                try:
                    db.collection("Claimed Items").document(doc_id).delete()
                    
                    db.collection("Food Items").document(item_id).set({
                        "username": posted_by_username,
                        "title": title,
                        "category": category,
                        "location": location,
                        "description": description,
                        "timestamp": firestore.SERVER_TIMESTAMP
                    })

                    if "claimed_items_list" in st.session_state:
                        st.session_state.claimed_items_list = [
                            i for i in st.session_state.claimed_items_list 
                            if (isinstance(i, dict) and i.get("item_id") != item_id)
                        ]
                        
                    st.toast(f"Unclaimed: {title}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error returning item: {e}")
                    
            st.markdown("---")
