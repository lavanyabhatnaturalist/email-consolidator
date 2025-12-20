import streamlit as st
import pandas as pd
import re

# Minimal page config
st.set_page_config(page_title="Email Consolidator", layout="wide")

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

def load_google_sheet(url, sheet_name):
    """Load data from Google Sheets URL"""
    csv_url = convert_to_csv_url(url)
    if csv_url:
        try:
            df = pd.read_csv(csv_url)
            df['Source'] = sheet_name  # Add source column
            return df
        except Exception as e:
            return None
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
    """Combine and clean dataframes"""
    if not dfs:
        return None
    
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Clean emails
    combined_df['Email'] = combined_df['Email'].apply(clean_email)
    combined_df = combined_df[combined_df['Email'].notna()]
    
    # Detect country column
    country_cols = [c for c in combined_df.columns if "Country" in c]
    if country_cols:
        combined_df['Country'] = combined_df[country_cols[0]]
    else:
        combined_df['Country'] = "Unknown"
    
    # Deduplicate by email, sort by Country then Full Name
    unique_df = combined_df.drop_duplicates(subset=['Email'], keep='first')
    unique_df = unique_df.sort_values(by=['Country', 'Full Name'], ascending=[True, True])
    
    return unique_df

# --- MAIN APP ---
def main():
    # Title and Load Button side by side
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Email Consolidator")
    with col2:
        st.write("")  # Spacing
        load_button = st.button("Load Data", type="primary", use_container_width=True)
    
    # Fixed Google Sheets URLs with names
    SHEETS = [
        ("Individual Registration", "https://docs.google.com/spreadsheets/d/1_Sz7pJgOHwzkhepIYS05Z-azYylI0lpjzdisFwcEo6U/edit?gid=1692911100#gid=1692911100"),
        ("City Registration", "https://docs.google.com/spreadsheets/d/1mWFNjaYJ-CAM63jJiKlnRAVC7sdzekHFajzTIGR56Mk/edit?gid=1473544593#gid=1473544593"),
    ]
    
    # Initialize session state
    if 'result_df' not in st.session_state:
        st.session_state.result_df = None
    
    # Load data when button clicked
    if load_button:
        with st.spinner("Loading..."):
            dataframes = []
            for sheet_name, url in SHEETS:
                df = load_google_sheet(url, sheet_name)
                if df is not None:
                    dataframes.append(df)
            
            if dataframes:
                result_df = process_dataframes(dataframes)
                if result_df is not None and not result_df.empty:
                    st.session_state.result_df = result_df
                    st.success(f"✓ Loaded {len(result_df)} unique emails from {result_df['Country'].nunique()} countries")
            else:
                st.error("Failed to load data. Check sheet permissions.")
    
    # Display results if available
    if st.session_state.result_df is not None:
        result_df = st.session_state.result_df
        
        # Filters and metrics in one row
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            countries = ['All'] + sorted(result_df['Country'].dropna().unique().tolist())
            selected_country = st.selectbox("Filter by Country", countries)
        
        with col2:
            total_emails = len(result_df) if selected_country == 'All' else len(result_df[result_df['Country'] == selected_country])
            st.metric("Unique Emails", total_emails)
        
        with col3:
            st.metric("Countries", result_df['Country'].nunique())
        
        # Apply filter
        display_df = result_df.copy()
        if selected_country != 'All':
            display_df = display_df[display_df['Country'] == selected_country]
        
        # Display columns: Name, Email, Source, Country only
        display_columns = ['Full Name', 'Email', 'Source', 'Country']
        display_columns = [col for col in display_columns if col in display_df.columns]
        
        # Show table
        st.dataframe(display_df[display_columns], use_container_width=True, height=400)
        
        # Download section
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        # Prepare data
        all_emails_with_names = []
        for _, row in display_df.iterrows():
            if pd.notna(row['Email']) and pd.notna(row.get('Full Name')):
                all_emails_with_names.append(f"{row['Full Name']} <{row['Email']}>")
        emails_string = '; '.join(all_emails_with_names)
        
        with col1:
            st.text_area("Copy Emails with Names", emails_string, height=100)
        
        with col2:
            csv = display_df[display_columns].to_csv(index=False)
            filename = f"cnc_emails_{selected_country.lower().replace(' ', '_')}.csv" if selected_country != 'All' else "cnc_emails_all.csv"
            st.download_button("Download Full Data (CSV)", csv, filename, "text/csv", use_container_width=True)
        
        with col3:
            plain_text = '\n'.join([f"{row['Full Name']}\t{row['Email']}\t{row['Source']}\t{row['Country']}" 
                                    for _, row in display_df.iterrows() if pd.notna(row['Email'])])
            filename_txt = f"cnc_emails_{selected_country.lower().replace(' ', '_')}.txt" if selected_country != 'All' else "cnc_emails_all.txt"
            st.download_button("Download Plain Text", plain_text, filename_txt, "text/plain", use_container_width=True)

if __name__ == "__main__":
    main()
