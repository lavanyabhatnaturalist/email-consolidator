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
    st.title("🌿 City Nature Challenge - Email Consolidator")
    st.markdown("Extract consolidated email lists from CNC registration forms")
    
    # Initialize session state
    if 'dataframes' not in st.session_state:
        st.session_state.dataframes = []
    
    st.divider()
    
    # --- FIXED GOOGLE SHEETS ---
    st.subheader("📊 CNC Registration Sheets")
    st.info("Click below to load the latest registration data")
    
    # Your fixed Google Sheets URLs - REPLACE THESE!
    FIXED_SHEET_URLS = [
        "https://docs.google.com/spreadsheets/d/1_Sz7pJgOHwzkhepIYS05Z-azYylI0lpjzdisFwcEo6U/edit?gid=1692911100#gid=1692911100",
        "https://docs.google.com/spreadsheets/d/1mWFNjaYJ-CAM63jJiKlnRAVC7sdzekHFajzTIGR56Mk/edit?gid=1473544593#gid=1473544593",
    ]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🔄 Load Latest Registration Data", type="primary", use_container_width=True):
            st.session_state.dataframes = []  # Clear old data
            with st.spinner("Loading registration data..."):
                loaded_count = 0
                for i, url in enumerate(FIXED_SHEET_URLS):
                    df = load_google_sheet(url)
                    if df is not None:
                        st.session_state.dataframes.append(df)
                        loaded_count += 1
                        st.success(f"✅ Loaded Sheet {i+1} ({len(df)} rows)")
                
                if loaded_count > 0:
                    st.success(f"✅ Successfully loaded {loaded_count} sheet(s)!")
                    # Auto-process
                    with st.spinner("Processing..."):
                        result_df = process_dataframes(st.session_state.dataframes)
                        if result_df is not None and not result_df.empty:
                            st.session_state.result_df = result_df
                            st.success(f"✅ Found {len(result_df)} unique emails!")
                else:
                    st.error("❌ Failed to load sheets")
    
    with col2:
        if st.button("🗑️ Clear Data", use_container_width=True):
            st.session_state.dataframes = []
            if 'result_df' in st.session_state:
                del st.session_state.result_df
            st.rerun()
    
    # --- RESULTS SECTION (keep as is, but with country default) ---
    if 'result_df' in st.session_state:
        st.divider()
        st.subheader("📋 Results")
        
        result_df = st.session_state.result_df
        
        # Sorting options with COUNTRY as default
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            available_cols = result_df.columns.tolist()
            # Default to Country/Region Name
            default_sort = 'Country/Region Name' if 'Country/Region Name' in available_cols else available_cols[0]
            default_index = available_cols.index(default_sort) if default_sort in available_cols else 0
            sort_column = st.selectbox("Sort by:", available_cols, index=default_index)
        
        with col2:
            sort_order = st.radio("Order:", ["Ascending", "Descending"], horizontal=True)
        
        with col3:
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
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Full Data (CSV)",
                data=csv,
                file_name="cnc_email_list_full.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
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
        st.info("👆 Click 'Load Latest Registration Data' to get started")

if __name__ == "__main__":
    main()
