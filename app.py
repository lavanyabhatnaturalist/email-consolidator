import streamlit as st
import pandas as pd
import re

# Minimal page config
st.set_page_config(page_title="CNC 2026 Email Consolidator", layout="wide")

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

def load_google_sheet_individual(url):
    """Load individual registration data"""
    csv_url = convert_to_csv_url(url)
    if csv_url:
        try:
            df = pd.read_csv(csv_url)
            return df
        except Exception as e:
            return None
    return None

def load_google_sheet_city(url):
    """Load city registration data and extract organizer info"""
    csv_url = convert_to_csv_url(url)
    if csv_url:
        try:
            df = pd.read_csv(csv_url)
            # Skip first row (headers are malformed)
            df = df.iloc[1:].reset_index(drop=True)
            
            # Extract organizer data from multiple columns
            organizers = []
            organizer_cols = [
                ('Unnamed: 9', 'Unnamed: 10'),   # Organizer 1
                ('Unnamed: 11', 'Unnamed: 12'),  # Organizer 2
                ('Unnamed: 13', 'Unnamed: 14'),  # Organizer 3
                ('Unnamed: 15', 'Unnamed: 16'),  # Organizer 4
                ('Unnamed: 17', 'Unnamed: 18'),  # Organizer 5
                ('Unnamed: 19', 'Unnamed: 20'),  # Organizer 6
                ('Unnamed: 21', 'Unnamed: 22'),  # Organizer 7
            ]
            
            for _, row in df.iterrows():
                city_name = row['Unnamed: 1']
                country = row['If you have changes, additions, or edits to other columns, please leave a comment in the cell where you would like a change and our team can make that change for you. Thank you, The CNC Global Organizing Team.']
                
                for name_col, email_col in organizer_cols:
                    name = row.get(name_col)
                    email = row.get(email_col)
                    
                    if pd.notna(email) and '@' in str(email):
                        organizers.append({
                            'Full Name': name if pd.notna(name) else 'Unknown',
                            'Email': email,
                            'Country': country if pd.notna(country) else 'Unknown',
                            'City Name: This is the name of the nearest or largest metropolitan area anchoring your project (it may be a large city or a small rural town). If multiple cities are listed, please separate each city with a semi colon (;). Example: Minneapolis; St. Paul': city_name if pd.notna(city_name) else 'Unknown'
                        })
            
            return pd.DataFrame(organizers)
        except Exception as e:
            st.error(f"Error loading City sheet: {e}")
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

def process_dataframes(df_individual, df_city):
    """Combine and clean dataframes with proper source tracking"""
    if df_individual is None and df_city is None:
        return None
    
    # Track which emails appear in which sheets
    individual_emails = set()
    city_emails = set()
    
    if df_individual is not None:
        df_individual['Email_clean'] = df_individual['Email'].apply(clean_email)
        individual_emails = set(df_individual['Email_clean'].dropna())
    
    if df_city is not None:
        df_city['Email_clean'] = df_city['Email'].apply(clean_email)
        city_emails = set(df_city['Email_clean'].dropna())
    
    # Determine source for each email
    emails_in_both = individual_emails & city_emails
    
    # Add source column to each dataframe
    if df_individual is not None:
        df_individual['Source'] = df_individual['Email_clean'].apply(
            lambda x: 'Both Sheets' if x in emails_in_both else 'Individual Registration'
        )
    
    if df_city is not None:
        df_city['Source'] = df_city['Email_clean'].apply(
            lambda x: 'Both Sheets' if x in emails_in_both else 'City Registration'
        )
    
    # Combine dataframes
    dfs = []
    if df_individual is not None:
        dfs.append(df_individual)
    if df_city is not None:
        dfs.append(df_city)
    
    if not dfs:
        return None
    
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Clean and filter
    combined_df = combined_df[combined_df['Email_clean'].notna()]
    
    # Detect country column
    country_cols = [c for c in combined_df.columns if "Country" in c]
    if country_cols:
        combined_df['Country'] = combined_df[country_cols[0]]
    else:
        combined_df['Country'] = "Unknown"
    
    # Deduplicate by email, keeping first occurrence (preserves "Both Sheets" when applicable)
    # Sort by Source first so "Both Sheets" comes first
    combined_df['Source_priority'] = combined_df['Source'].apply(lambda x: 0 if x == 'Both Sheets' else 1)
    combined_df = combined_df.sort_values('Source_priority')
    unique_df = combined_df.drop_duplicates(subset=['Email_clean'], keep='first')
    
    # Final sort by Country then Full Name
    unique_df = unique_df.sort_values(by=['Country', 'Full Name'], ascending=[True, True])
    
    # Drop helper columns
    unique_df = unique_df.drop(['Email_clean', 'Source_priority'], axis=1)
    
    return unique_df

# --- MAIN APP ---
def main():
    # Title and Load Button side by side
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("CNC 2026 Email Consolidator")
    with col2:
        st.write("")  # Spacing
        load_button = st.button("Load Data", type="primary", use_container_width=True)
    
    # Fixed Google Sheets URLs
    INDIVIDUAL_URL = "https://docs.google.com/spreadsheets/d/1_Sz7pJgOHwzkhepIYS05Z-azYylI0lpjzdisFwcEo6U/edit?gid=1692911100#gid=1692911100"
    CITY_URL = "https://docs.google.com/spreadsheets/d/1mWFNjaYJ-CAM63jJiKlnRAVC7sdzekHFajzTIGR56Mk/edit?gid=1473544593#gid=1473544593"
    
    # Initialize session state
    if 'result_df' not in st.session_state:
        st.session_state.result_df = None
    
    # Load data when button clicked
    if load_button:
        with st.spinner("Loading..."):
            df_individual = load_google_sheet_individual(INDIVIDUAL_URL)
            df_city = load_google_sheet_city(CITY_URL)
            
            if df_individual is not None or df_city is not None:
                result_df = process_dataframes(df_individual, df_city)
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
           total_countries = (result_df['Country'].nunique()if selected_country == 'All'else 1)
           st.metric("Countries Selected", total_countries)
    
        # Apply filter
        display_df = result_df.copy()
        if selected_country != 'All':
            display_df = display_df[display_df['Country'] == selected_country]
        
        # Display columns: Name, Email, Source, Country only (NO INDEX)
        display_columns = ['Full Name', 'Email', 'Source', 'Country']
        display_columns = [col for col in display_columns if col in display_df.columns]
        
        # Show table WITHOUT index column
        st.dataframe(
            display_df[display_columns].reset_index(drop=True), 
            use_container_width=True, 
            height=400,
            hide_index=True  # This removes the serial number column
        )
        
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
