import streamlit as st
import pandas as pd
import re
from io import StringIO

# Page config
st.set_page_config(
    page_title="CNC Email Consolidator",
    page_icon="🌿",
    layout="wide"
)

# --- AUTHENTICATION ---
# Replace with your organization's domain
AUTHORIZED_DOMAIN = "@yourdomain.org"  # Change this!

def check_authentication():
    """Check if user is from authorized organization"""
    try:
        user_info = st.context.headers.get("X-Forwarded-Email", "")
        if user_info and user_info.endswith(AUTHORIZED_DOMAIN):
            return True, user_info
    except:
        pass
    return False, None

# Simple password protection (until you set up proper auth)
def simple_auth():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔐 CNC Email Consolidator - Login")
        password = st.text_input("Enter access password:", type="password")
        if st.button("Login"):
            if password == "cnc2026":  # Change this password!
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Incorrect password")
        st.stop()

# --- HELPER FUNCTIONS ---
def extract_sheet_id_and_gid(url):
    """Extract spreadsheet ID and sheet GID from Google Sheets URL"""
    pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)(?:/.*?gid=([0-9]+))?'
    match = re.search(pattern, url)
    if match:
        sheet_id = match.group(1)
        gid = match.group(2) if match.group(2) else '0'
        return sheet_id, gid
    return None, None

def convert_to_csv_url(sheet_url):
    """Convert Google Sheets URL to CSV export URL"""
    sheet_id, gid = extract_sheet_id_and_gid(sheet_url)
    if sheet_id:
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return None

def load_google_sheet(url):
    """Load data from Google Sheets URL"""
    csv_url = convert_to_csv_url(url)
    if csv_url:
        try:
            df = pd.read_csv(csv_url)
            return df
        except Exception as e:
            st.error(f"❌ Error loading Google Sheet: {str(e)}")
            st.info("💡 Make sure the sheet is set to 'Anyone with the link can view'")
            return None
    else:
        st.error("❌ Invalid Google Sheets URL")
        return None

def clean_email(email):
    """Clean and validate email"""
    if pd.isna(email):
        return None
    email = str(email).strip().lower()
    if '@' in email:
        return email
    return None

def process_dataframes(dfs):
    """Combine and deduplicate dataframes"""
    if not dfs:
        return None
    
    # Combine all dataframes
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Clean emails
    combined_df['Email'] = combined_df['Email'].apply(clean_email)
    
    # Remove rows with no email
    combined_df = combined_df[combined_df['Email'].notna()]
    
    # Remove duplicates based on email (keep first occurrence)
    unique_df = combined_df.drop_duplicates(subset=['Email'], keep='first')
    
    return unique_df

# --- MAIN APP ---
def main():
    simple_auth()  # Enable authentication
    
    st.title("🌿 City Nature Challenge - Email Consolidator")
    st.markdown("Upload CSV files or paste Google Sheets links to extract consolidated email lists")
    
    # Initialize session state
    if 'dataframes' not in st.session_state:
        st.session_state.dataframes = []
    
    # Create tabs for different input methods
    tab1, tab2 = st.tabs(["📤 Upload CSV Files", "🔗 Google Sheets Links"])
    
    # --- TAB 1: CSV Upload ---
    with tab1:
        st.subheader("Upload CSV Files")
        uploaded_files = st.file_uploader(
            "Choose CSV file(s)",
            type=['csv'],
            accept_multiple_files=True,
            help="You can upload multiple CSV files at once"
        )
        
        if uploaded_files:
            temp_dfs = []
            for file in uploaded_files:
                try:
                    df = pd.read_csv(file)
                    temp_dfs.append(df)
                    st.success(f"✅ Loaded: {file.name} ({len(df)} rows)")
                except Exception as e:
                    st.error(f"❌ Error reading {file.name}: {str(e)}")
            
            if temp_dfs and st.button("Add CSV Files to Processing Queue", key="add_csv"):
                st.session_state.dataframes.extend(temp_dfs)
                st.success(f"✅ Added {len(temp_dfs)} file(s) to queue!")
    
    # --- TAB 2: Google Sheets ---
    with tab2:
        st.subheader("Google Sheets URLs")
        st.info("📝 Make sure sheets are set to 'Anyone with the link can view'")
        
        # Input for multiple URLs
        sheet_urls_input = st.text_area(
            "Paste Google Sheets URLs (one per line)",
            height=150,
            placeholder="https://docs.google.com/spreadsheets/d/...\nhttps://docs.google.com/spreadsheets/d/..."
        )
        
        if st.button("Add Google Sheets to Processing Queue", key="add_sheets"):
            urls = [url.strip() for url in sheet_urls_input.split('\n') if url.strip()]
            if urls:
                for url in urls:
                    df = load_google_sheet(url)
                    if df is not None:
                        st.session_state.dataframes.append(df)
                        st.success(f"✅ Loaded sheet ({len(df)} rows)")
                st.success(f"✅ Added {len(urls)} sheet(s) to queue!")
            else:
                st.warning("⚠️ Please paste at least one URL")
    
    # --- PROCESSING SECTION ---
    st.divider()
    
    if st.session_state.dataframes:
        st.subheader(f"📊 Data Queue: {len(st.session_state.dataframes)} file(s) loaded")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🚀 Process & Extract Emails", type="primary", use_container_width=True):
                with st.spinner("Processing..."):
                    result_df = process_dataframes(st.session_state.dataframes)
                    
                    if result_df is not None and not result_df.empty:
                        st.session_state.result_df = result_df
                        st.success(f"✅ Found {len(result_df)} unique emails!")
                    else:
                        st.error("❌ No valid data found")
        
        with col2:
            if st.button("🗑️ Clear Queue", use_container_width=True):
                st.session_state.dataframes = []
                if 'result_df' in st.session_state:
                    del st.session_state.result_df
                st.rerun()
    
    # --- RESULTS SECTION ---
    if 'result_df' in st.session_state:
        st.divider()
        st.subheader("📋 Results")
        
        result_df = st.session_state.result_df
        
        # Sorting options
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            # Determine available columns for sorting
            available_cols = result_df.columns.tolist()
            sort_column = st.selectbox("Sort by:", available_cols, index=0 if 'Country/Region Name' in available_cols else 0)
        
        with col2:
            sort_order = st.radio("Order:", ["Ascending", "Descending"], horizontal=True)
        
        with col3:
            # Filter by country (if column exists)
            if 'Country/Region Name' in result_df.columns:
                countries = ['All'] + sorted(result_df['Country/Region Name'].dropna().unique().tolist())
                selected_country = st.selectbox("Filter by Country:", countries)
            else:
                selected_country = 'All'
        
        # Apply filters and sorting
        display_df = result_df.copy()
        
        if selected_country != 'All':
            display_df = display_df[display_df['Country/Region Name'] == selected_country]
        
        display_df = display_df.sort_values(
            by=sort_column,
            ascending=(sort_order == "Ascending")
        )
        
        # Display statistics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Unique Emails", len(display_df))
        col2.metric("Total Countries", display_df['Country/Region Name'].nunique() if 'Country/Region Name' in display_df.columns else "N/A")
        col3.metric("New Organizers", len(display_df[display_df.get('Are you a new or returning organizer for the 2026 City Nature Challenge?', '') == 'I am a new organizer']) if 'Are you a new or returning organizer for the 2026 City Nature Challenge?' in display_df.columns else "N/A")
        
        # Select columns to display
        display_columns = []
        available_display_cols = ['Full Name', 'Email', 'Country/Region Name', 'City Name', 'iNaturalist Username', 'Organization (if applicable)']
        
        for col in available_display_cols:
            if col in display_df.columns:
                display_columns.append(col)
        
        # Display dataframe
        st.dataframe(
            display_df[display_columns] if display_columns else display_df,
            use_container_width=True,
            height=400
        )
        
        # Download buttons
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            # Download full data
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Full Data (CSV)",
                data=csv,
                file_name="cnc_email_list_full.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Download emails only
            email_only_df = display_df[['Full Name', 'Email'] if 'Full Name' in display_df.columns else ['Email']]
            csv_emails = email_only_df.to_csv(index=False)
            st.download_button(
                label="📧 Download Emails Only (CSV)",
                data=csv_emails,
                file_name="cnc_emails_only.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    else:
        st.info("👆 Upload files or add Google Sheets links above to get started")

if __name__ == "__main__":
    main()
