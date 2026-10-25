import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, auth, firestore
from streamlit_option_menu import option_menu
import Bug_Report, About_Us, Account_Settings, Claimed
import os
from google.cloud import storage
from google.oauth2 import service_account
import pandas as pd
import io
import uuid

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "firebase-adminsdk-fbsvc@foodshare-ee612.iam.gserviceaccount.com.json"
credentials_dict = dict(st.secrets["gcp_service_account"])
service_account_credentials = service_account.Credentials.from_service_account_info(credentials_dict)
storage_client = storage.Client(credentials=service_account_credentials, project="foodshare-ee612")
BUCKET_NAME = "foodshare"

st.set_page_config(page_title="NeighborFood Share", layout="wide")

@st.cache_resource
def initialize_firebase():
    try:
        firebase_creds_dict = dict(st.secrets["gcp_service_account"])   
        cred = credentials.Certificate(firebase_creds_dict)
        return firebase_admin.initialize_app(cred)
    except ValueError:
        return firebase_admin.get_app()

app = initialize_firebase()

db = firestore.client()

if "Food Items" not in st.session_state:
    st.session_state["Food Items"] = []

def show_home():
    global username
    if "username" in st.session_state and st.session_state.username is not None:
        username = st.session_state.username

    username = st.session_state.get("username", "Anoynomous")
    st.title("FoodShare")
    st.subheader(f"Welcome back, {username}! Share food with your community.")

    if username == "Anoynomous":
        st.switch_page("main.py")
    
    st.sidebar.header("Share Extra Food")
    new_title = st.sidebar.text_input("What food do you have? (e.g., 6 Extra Tomatoes)")
    new_location = st.sidebar.text_input("Your Location/Neighborhood")
    categories = ["Vegetables", "Fruits", "Bakery & Bread", "Canned Goods", "Dairy & Eggs", "Other"]
    new_category = st.sidebar.selectbox("Choose a Category", categories)
    new_desc = st.sidebar.text_area("Details (e.g., Expiration date, pickup notes)")
    food_uploader = st.sidebar.file_uploader("Upload a photo of the food", type=["jpg", "jpeg", "png"], key="food_pic")
    if food_uploader is not None:
        food_uploader.seek(0)
        st.sidebar.image(food_uploader, caption="Uploaded Food Photo", width=110)
    
    if st.sidebar.button("Post Food Listing"):
        if new_title and new_location:
            new_post = db.collection("Food Items").document()
            new_post.set({
                "username": username,
                "title": new_title,
                "location": new_location,
                "category": new_category,
                "description": new_desc,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            if food_uploader is not None:
                food_uploader.seek(0)
                st.image(food_uploader, caption="Uploaded Food Photo", width=60)
                try:
                    def upload_to_gcs(bucket_name, streamlit_file, file_name):
                        bucket = storage_client.bucket(bucket_name)
                        blob = bucket.blob("food_pictures/" + file_name + ".png")
                        blob.upload_from_file(streamlit_file)
                    upload_to_gcs(BUCKET_NAME, food_uploader, new_post.id)

                except Exception as e:
                    st.error(f"An error occurred: {e}")

            st.session_state.title = new_title
            st.session_state.location = new_location
            st.session_state.description = new_desc
            st.session_state.category = new_category
            st.sidebar.success(f"Successfully listed: {new_title}!")
            st.rerun()
        else:
            st.sidebar.error("Please fill out the food title and your location.")

    if "deleting_id" not in st.session_state:
        st.session_state.deleting_id = None

    st.header("Available Food Nearby")
    filter_categories = ["All Categories"] + categories
    selected_filter = st.selectbox("Filter listings by category:", filter_categories)
    
    listings_ref = db.collection("Food Items").order_by("timestamp", direction=firestore.Query.DESCENDING)
    docs = listings_ref.stream()

    display_count = 0

    for doc in docs:
        item = doc.to_dict()
        doc_id = doc.id

        if item.get("status") == "claimed":
            continue

        if selected_filter == "All Categories" or item["category"] == selected_filter:
            display_count += 1

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
                st.markdown(f"### {item['title']}")
                st.markdown(f"**Category:** {item['category']}")
                file_to_view_2 = download_gcs_blob(BUCKET_NAME, f"food_pictures/{doc_id}.png")
                if file_to_view_2[0] is not None:
                    st.image(file_to_view_2[0], width=200)
                st.caption(f"**Location:** {item['location']}")
                st.write(f"**Description:** {item['description']}")
                st.write(f"**Posted by:**")
                posted_by_username = item.get('username', 'Unknown')

                file_to_view = download_gcs_blob(BUCKET_NAME, f"profile_pictures/{posted_by_username}.png")
                if file_to_view[0] is not None:
                    st.image(file_to_view[0], width=60)
                st.write(posted_by_username)

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("Claim", key=f"claim_{doc_id}"):
                        fresh_doc = db.collection("Food Items").document(doc_id).get()
                        if not fresh_doc.exists:
                            st.error("Too late! Someone else just claimed this item.")
                            st.rerun()
                        else:
                            fresh_item = fresh_doc.to_dict()
                            
                            if "claimed_items_list" not in st.session_state:
                                st.session_state.claimed_items_list = []

                            new_claim = {
                                "item_id": doc_id,
                                "title": fresh_item.get('title'),
                                "category": fresh_item.get('category'),
                                "location": fresh_item.get('location'),
                                "description": fresh_item.get('description'),
                                "posted_by": fresh_item.get('username', 'Unknown')
                            }

                            if new_claim not in st.session_state.claimed_items_list:
                                st.session_state.claimed_items_list.append(new_claim)
                            
                            claim_doc_id = doc_id
                            db.collection("Claimed Items").document(claim_doc_id).set({
                                "claimed_by": username,
                                "title": fresh_item.get('title'),
                                "category": fresh_item.get('category'),
                                "location": fresh_item.get('location'),
                                "description": fresh_item.get('description'),
                                "item_id": doc_id,
                                "posted_by": fresh_item.get('username', 'Unknown')
                            })

                            db.collection("Food Items").document(doc_id).delete()
                            st.toast(f"'{fresh_item.get('title')}' successfully claimed!")
                            st.rerun()

                with col2:
                    posted_by = item.get('username', '')
                    if username == posted_by and username != "Anoynomous":
                        if st.button("Delete", key=f"delete_{doc_id}", type="secondary"):
                            st.session_state.deleting_id = doc_id
                            st.rerun()
                    else:
                        st.button("Delete", key=f"delete_disabled_{doc_id}", disabled=True, help="You can only delete your own listings.")

                if st.session_state.deleting_id == doc_id:
                    st.warning("Are you sure you want to delete this listing?")
                    conf_col1, conf_col2 = st.columns(2)
                    with conf_col1:
                        if st.button("Yes, proceed", key=f"confirm_{doc_id}"):
                            db.collection("Food Items").document(doc_id).delete()
                            st.session_state.deleting_id = None
                            st.success("Item deleted successfully!")
                            st.rerun()
                    with conf_col2:
                        if st.button("Cancel", key=f"cancel_{doc_id}"):
                            st.session_state.deleting_id = None
                            st.rerun()

                st.markdown("---")      

    if display_count == 0:
        st.info("No food listings found for this category.")
        return

def show_bug_report():
    Bug_Report.app()

def show_about_us():
    About_Us.app()

def show_account_settings():
    Account_Settings.app()

def show_claimed_items():
    Claimed.app()

def main():
    with st.sidebar:
        selected = option_menu(
            menu_title="Main Menu",
            options=["Home", "Claimed Items", "Account Settings", "Bug Report or Suggestion", "About Us", "Log out"],
            icons=["house", "clipboard-data", "gear", "bug", "info-circle", "arrow-left"],
            default_index=0,
            key="menu_selection",
            styles={
                "container": {"padding": "5!important", "background-color": "black"},
                "icon": {"color": "white", "font-size": "23px"},
                "nav-link": {"color": "white", "font-size": "20px", "text-align": "left", "margin": "0px", "--hover-color": "blue"},
                "nav-link-selected": {"background-color": "#02ab21"},
            }
        )

    current_page = st.session_state.menu_selection

    if selected == "Home":
        show_home()
    elif selected == "Claimed Items":
        show_claimed_items()
    elif selected == "Account Settings":
        show_account_settings()
    elif selected == "Bug Report or Suggestion":
        show_bug_report()
    elif selected == "About Us":
        show_about_us()
    elif selected == "Log out":
        st.session_state.clear()
        st.rerun()



if __name__ == "__main__":
    main()