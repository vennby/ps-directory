import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd
from datetime import datetime

def connect_to_gsheet(spreadsheet_name, sheet_name):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]
    # Load credentials directly from Streamlit secrets
    creds_info = st.secrets["google"]
    credentials = Credentials.from_service_account_info(creds_info, scopes=scope)
    client = gspread.authorize(credentials)
    spreadsheet = client.open(spreadsheet_name)
    return spreadsheet.worksheet(sheet_name)

SPREADSHEET_NAME = "PS II Stations"
RATINGS_NAME = "Ratings"

ratings_ws = connect_to_gsheet(SPREADSHEET_NAME, sheet_name=RATINGS_NAME)

# -------------------------
# Helpers
# -------------------------
def _parse_rating(val):
    """Convert cell to float between 0 and 5."""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    m = re.search(r"(\d+(\.\d+)?)", str(val))
    if not m:
        return None
    r = float(m.group(1))
    return max(0, min(5, r))  # clamp 0-5

def _render_stars(avg, out_of=5):
    if avg is None:
        return "<span style='color:#999;'>No ratings</span>"
    full = int(avg)
    empty = out_of - full
    stars_html = (
        "<span style='font-size:1.8rem;color:#FFD700;'>"
        + ("★" * full)
        + ("☆" * empty)
        + "</span>"
    )
    return stars_html

def append_rating(company, rating):
    """Append a new rating to the Google Sheet."""
    ratings_ws.append_row([company, rating, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

# -------------------------
# Data Load
# -------------------------
@st.cache_data(show_spinner=False)
def read_ratings_data():
    data = ratings_ws.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    if "Rating" not in df.columns:
        rating_col = [c for c in df.columns if "rating" in c.lower()]
        if rating_col:
            df = df.rename(columns={rating_col[0]: "Rating"})
    if "Company" not in df.columns:
        company_col = [c for c in df.columns if "company" in c.lower()]
        if company_col:
            df = df.rename(columns={company_col[0]: "Company"})
    return df

df = read_ratings_data()

# -------------------------
# UI
# -------------------------
st.title("Company Ratings")

all_companies = sorted(df["Company"].dropna().unique())

# Search and Dropdown
selected_from_dropdown = st.selectbox("Select a company:", options=all_companies, index=None)

if selected_from_dropdown:
    matched_rows = df[df["Company"].str.contains(selected_from_dropdown, case=False, na=False)]
    if matched_rows.empty:
        st.warning(f"No ratings found for '{selected_from_dropdown}'.")
    else:
        matched_rows["Rating_num"] = matched_rows["Rating"].apply(_parse_rating)
        ratings_clean = matched_rows.dropna(subset=["Rating_num"])
        avg_rating = ratings_clean["Rating_num"].mean() if not ratings_clean.empty else None

        # Display stars
        st.markdown("### Average Rating")
        stars_html = _render_stars(avg_rating, out_of=5)
        st.markdown(stars_html, unsafe_allow_html=True)
        if avg_rating is not None:
            st.markdown(f"**{avg_rating:.2f} / 5** (from {len(ratings_clean)} ratings)")
        else:
            st.markdown("_No valid ratings available._")

else:
    st.info("Please select a company from the dropdown to see what former interns have to say about them~")