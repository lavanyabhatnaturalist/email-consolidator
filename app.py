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
    if not dfs:
        return None

    combined_df = pd.concat(dfs, ignore_index=True)

    # Clean emails
    combined_df['Email'] = combined_df['Email'].apply(clean_email)
    combined_df = combined_df[combined_df['Email'].notna()]

    # 🔹 Detect country column automatically
    country_cols = [c for c in combined_df.columns if "Country" in c]

    if country_cols:
        combined_df['Country'] = combined_df[country_cols[0]]
    else:
        combined_df['Country'] = "Unknown"

    # Deduplicate by email
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
        # --- RESULTS SECTION ---
        # --- RESULTS SECTION ---
    if 'result_df' in st.session_state:
        st.divider()
        st.subheader("📋 Results")
        
        result_df = st.session_state.result_df
        
        # EXACT column name from your sheets
        COUNTRY_COL = 'Country'

        
        # Verify column exists
        if COUNTRY_COL not in result_df.columns:
            st.error(f"⚠️ Country column not found! Available columns:")
            st.write(result_df.columns.tolist())
        
        # Sorting options
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            available_cols = result_df.columns.tolist()
            # Set default to country column
            default_index = available_cols.index(COUNTRY_COL) if COUNTRY_COL in available_cols else 0
            sort_column = st.selectbox("Sort by:", available_cols, index=default_index)
        
        with col2:
            sort_order = st.radio("Order:", ["Ascending", "Descending"], horizontal=True)
        
        with col3:
            if COUNTRY_COL in result_df.columns:
                countries = ['All'] + sorted(result_df[COUNTRY_COL].dropna().unique().tolist())
                selected_country = st.selectbox("Filter by Country:", countries)
            else:
                selected_country = 'All'
        
        # Apply filters and sorting
        display_df = result_df.copy()
        
        if selected_country != 'All' and COUNTRY_COL in display_df.columns:
            display_df = display_df[display_df[COUNTRY_COL] == selected_country]
        
        # Sort the dataframe
        display_df = display_df.sort_values(
            by=sort_column,
            ascending=(sort_order == "Ascending")
        )
        
        # Display statistics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Unique Emails", len(display_df))
        col2.metric("Total Countries", display_df[COUNTRY_COL].nunique() if COUNTRY_COL in display_df.columns else "N/A")
        
        # Count new organizers
        new_org_col = 'Are you a new or returning organizer for the 2026 City Nature Challenge?'
        if new_org_col in result_df.columns:
            new_count = len(display_df[display_df[new_org_col] == 'I am a new organizer'])
            col3.metric("New Organizers", new_count)
        else:
            col3.metric("New Organizers", "N/A")
        
        # Select EXACT columns to display (in order you want)
        display_columns = [
    'Full Name',
    'Email',
    'Country',
    'City Name: This is the name of the nearest or largest metropolitan area anchoring your project (it may be a large city or a small rural town). If multiple cities are listed, please separate each city with a semi colon (;). Example: Minneapolis; St. Paul',
    'iNaturalist Username',
]

        
        # Only keep columns that exist in the dataframe
        display_columns = [col for col in display_columns if col in result_df.columns]
        
        # Display dataframe
        st.dataframe(
            display_df[display_columns],
            use_container_width=True,
            height=400
        )
        
        # Copy emails section
        st.divider()
        st.subheader("📧 Copy Emails for Gmail")
        
        # Prepare email lists
        all_emails = display_df['Email'].dropna().tolist()
        all_emails_string = '; '.join(all_emails)
        all_emails_comma = ', '.join(all_emails)
        
        # With names
        if 'Full Name' in display_df.columns:
            emails_with_names = []
            for _, row in display_df.iterrows():
                if pd.notna(row['Email']) and pd.notna(row['Full Name']):
                    emails_with_names.append(f"{row['Full Name']} <{row['Email']}>")
            emails_with_names_string = '; '.join(emails_with_names)
        else:
            emails_with_names_string = all_emails_string
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Emails Only (Semicolon)**")
            st.code(all_emails_string, language=None)
            st.caption(f"📋 {len(all_emails)} emails • Ready for Gmail BCC")
            
        with col2:
            st.markdown("**With Names**")
            st.code(emails_with_names_string, language=None)
            st.caption(f"📋 Format: Name <email>")
        
        with col3:
            st.markdown("**Comma Separated**")
            st.code(all_emails_comma, language=None)
            st.caption(f"📋 Alternative format")
        
        st.info("💡 **Tip:** Click inside any box above, press Ctrl+A (Cmd+A on Mac) to select all, then Ctrl+C (Cmd+C) to copy")
        
        st.divider()
        
        # Download buttons
        st.subheader("📥 Download Options")
        col1, col2 = st.columns(2)
        
        with col1:
            csv = display_df[display_columns].to_csv(index=False)
            filename = f"cnc_emails_{selected_country.lower().replace(' ', '_').replace('/', '_')}.csv" if selected_country != 'All' else "cnc_emails_all.csv"
            st.download_button(
                label="📥 Download Full Data",
                data=csv,
                file_name=filename,
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            plain_emails = '\n'.join(all_emails)
            filename_txt = f"cnc_emails_{selected_country.lower().replace(' ', '_').replace('/', '_')}.txt" if selected_country != 'All' else "cnc_emails.txt"
            st.download_button(
                label="📄 Plain Email List",
                data=plain_emails,
                file_name=filename_txt,
                mime="text/plain",  
                use_container_width=True
            )
    
    else:
        st.info("👆 Click 'Load Latest Registration Data' to get started")

if __name__ == "__main__":
    main()
