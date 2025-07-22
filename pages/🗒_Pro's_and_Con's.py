import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd

def connect_to_gsheet(spreadsheet_name, sheet_name):
    scope = [
        "https://spreadsheets.google.com/feeds", 
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file", 
        "https://www.googleapis.com/auth/drive"
    ]
    # Load credentials from Streamlit secrets
    creds_info = st.secrets["google"]
    credentials = Credentials.from_service_account_info(creds_info, scopes=scope)
    client = gspread.authorize(credentials)
    spreadsheet = client.open(spreadsheet_name)
    return spreadsheet.worksheet(sheet_name)

SPREADSHEET_NAME = 'PS II Stations'
CONS_NAME = "Con's"
PROS_NAME = "Pro's"

# Worksheets
cons_ws = connect_to_gsheet(SPREADSHEET_NAME, sheet_name=CONS_NAME)
pros_ws = connect_to_gsheet(SPREADSHEET_NAME, sheet_name=PROS_NAME)
# -------------------------
# Helpers
# -------------------------
def _normalize_cols(df, mapping):
    df.columns = df.columns.str.strip()
    df = df.rename(columns=mapping)
    return df

def _try_num(x):
    try:
        return float(x)
    except Exception:
        return float('inf')

# -------------------------
# Data Load (cached)
# -------------------------
@st.cache_data(show_spinner=False)
def read_cons_data():
    data = cons_ws.get_all_records()
    df = pd.DataFrame(data)
    df = _normalize_cols(df, {"Con's": "Cons", "No.": "No"})
    return df

@st.cache_data(show_spinner=False)
def read_pros_data():
    data = pros_ws.get_all_records()
    df = pd.DataFrame(data)
    df = _normalize_cols(df, {"Pro's": "Pros", "No.": "No"})
    return df

cons_df = read_cons_data()
pros_df = read_pros_data()

# -------------------------
# Validate required columns
# -------------------------
cons_required = {'Company', 'No', 'Cons'}
pros_required = {'Company', 'No', 'Pros'}

missing_cons = cons_required - set(cons_df.columns)
missing_pros = pros_required - set(pros_df.columns)

if missing_cons:
    st.error(f"Con's sheet is missing required columns: {', '.join(missing_cons)}")
    st.stop()
if missing_pros:
    st.error(f"Pro's sheet is missing required columns: {', '.join(missing_pros)}")
    st.stop()

st.title("PS Companies Pro's and Con's")

# -------------------------
# Company Selection
# -------------------------
all_companies = sorted(
    pd.unique(
        pd.concat([cons_df['Company'].dropna(), pros_df['Company'].dropna()])
    )
)
selected_company = st.selectbox("Select a company:", options=all_companies, index=None)

# Filter both sheets to selected company
company_cons_df = cons_df[cons_df['Company'] == selected_company].copy()
company_pros_df = pros_df[pros_df['Company'] == selected_company].copy()

if company_cons_df.empty and company_pros_df.empty:
    st.info("Please select a company from the dropdown to see what former interns have to say about them~")
    st.stop()

# -------------------------
# Prepare Grouped Data (using Cons sheet as the driver)
# -------------------------
# If there are no Cons rows but there ARE Pros rows, we fallback to Pros grouping.
if company_cons_df.empty:
    base_df = company_pros_df.copy()
    group_label = "Pros"
else:
    base_df = company_cons_df.copy()
    group_label = "Cons"

base_df['No_str'] = base_df['No'].astype(str)
base_df['No_sort'] = base_df['No'].apply(_try_num)
grouped_base = base_df.sort_values('No_sort').groupby('No_str')
group_keys = list(grouped_base.groups.keys())

# -------------------------
# Carousel State
# -------------------------
if (
    'carousel_idx' not in st.session_state or 
    st.session_state.get('carousel_company') != selected_company or
    st.session_state.get('carousel_group_label') != group_label
):
    st.session_state.carousel_idx = 0
    st.session_state.carousel_company = selected_company
    st.session_state.carousel_group_label = group_label

col_prev, col_pos, col_next = st.columns([1, 3, 1])
with col_prev:
    if st.button("⟵ Prev", use_container_width=True):
        st.session_state.carousel_idx = (st.session_state.carousel_idx - 1) % len(group_keys)
with col_next:
    if st.button("Next ⟶", use_container_width=True):
        st.session_state.carousel_idx = (st.session_state.carousel_idx + 1) % len(group_keys)

# Current group
idx = st.session_state.carousel_idx
current_key = group_keys[idx]

with col_pos:
    st.markdown(
        f"<div style='text-align:center;'>Review {idx+1} of {len(group_keys)}</div>",
        unsafe_allow_html=True
    )

st.divider()

# -------------------------
# Display Pro's ABOVE Con's
# -------------------------
# Normalize No in pros/cons company frames for lookup
for _df in (company_pros_df, company_cons_df):
    if not _df.empty:
        _df['No_str'] = _df['No'].astype(str)

# --- Pro's ---
st.subheader(f"Pro's for {selected_company}")

if company_pros_df.empty:
    st.info("No Pro's sheet data for this company.")
else:
    pros_group = company_pros_df[company_pros_df['No_str'] == current_key].copy()
    pros_group['Pros'] = pros_group['Pros'].astype(str).str.strip()
    pros_group = pros_group[pros_group['Pros'] != ""]
    if pros_group.empty:
        st.info("No pros text in this group.")
    else:
        for _, row in pros_group.iterrows():
            st.markdown(f"- {row['Pros']}")

st.divider()

# --- Con's ---
st.subheader(f"Con's for {selected_company}")

if company_cons_df.empty:
    st.info("No Con's sheet data for this company.")
else:
    cons_group = company_cons_df[company_cons_df['No_str'] == current_key].copy()
    cons_group['Cons'] = cons_group['Cons'].astype(str).str.strip()
    cons_group = cons_group[cons_group['Cons'] != ""]
    if cons_group.empty:
        st.info("No cons text in this group.")
    else:
        for _, row in cons_group.iterrows():
            st.markdown(f"- {row['Cons']}")

st.divider()