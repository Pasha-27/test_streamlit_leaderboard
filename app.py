import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Page configuration
st.set_page_config(
    page_title="Points Table Dashboard",
    page_icon="🏆",
    layout="wide"
)

st.title("🏆 Points Table Dashboard")

# Function to load data from specific worksheet
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_points_data(worksheet_option="first"):
    """
    Load data from Google Sheets - specific worksheet
    
    Args:
        worksheet_option: "first", "by_name", or "by_index"
    """
    try:
        # Get credentials from Streamlit secrets
        SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
        SHEET_ID = st.secrets["sheet_id"]
        
        # Define scope
        SCOPE = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        
        # Authorize and connect
        creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPE)
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        sheet = client.open_by_key(SHEET_ID)
        
        # Choose worksheet method
        if worksheet_option == "first":
            # Method 1: Get first worksheet
            worksheet = sheet.worksheets()[0]
        elif worksheet_option == "by_name":
            # Method 2: Get by specific name (change "Sheet1" to your actual sheet name)
            worksheet = sheet.worksheet("Sheet1")
        elif worksheet_option == "by_index":
            # Method 3: Get by index (0 = first, 1 = second, 2 = third)
            worksheet = sheet.worksheets()[0]  # First worksheet
        else:
            # Default: use sheet1 property
            worksheet = sheet.sheet1
        
        # Get all data
        data = worksheet.get_all_records()
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Clean and process data for points table
        if not df.empty:
            # Identify POD and Points columns (adjust based on your sheet structure)
            pod_col = None
            points_col = None
            
            # Look for POD column
            for col in df.columns:
                if any(keyword in str(col).lower() for keyword in ['pod', 'team', 'player', 'name']):
                    pod_col = col
                    break
            
            # Look for Points column
            for col in df.columns:
                if any(keyword in str(col).lower() for keyword in ['point', 'score', 'total']):
                    points_col = col
                    break
            
            # If specific columns not found, use first two columns
            if pod_col is None:
                pod_col = df.columns[0]
            if points_col is None and len(df.columns) > 1:
                points_col = df.columns[1]
            
            # Create clean dataframe
            if pod_col and points_col:
                clean_df = pd.DataFrame({
                    'POD Number': df[pod_col],
                    'Total Points': pd.to_numeric(df[points_col], errors='coerce')
                })
                
                # Remove rows with NaN points
                clean_df = clean_df.dropna(subset=['Total Points'])
                
                # Sort by points (descending) and add rank
                clean_df = clean_df.sort_values('Total Points', ascending=False).reset_index(drop=True)
                clean_df['Rank'] = range(1, len(clean_df) + 1)
                
                # Reorder columns
                clean_df = clean_df[['Rank', 'POD Number', 'Total Points']]
                
                return clean_df, worksheet.title  # Return data and worksheet name
        
        return pd.DataFrame(), "Unknown"
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame(), "Error"

# Sidebar for worksheet selection (optional)
st.sidebar.header("📊 Worksheet Settings")

# Show available worksheets (for debugging/info)
if st.sidebar.button("Show Available Worksheets"):
    try:
        SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
        SHEET_ID = st.secrets["sheet_id"]
        SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        
        creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)
        
        worksheets = sheet.worksheets()
        st.sidebar.write("**Available worksheets:**")
        for i, ws in enumerate(worksheets):
            st.sidebar.write(f"{i+1}. {ws.title}")
            
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

# Load data from first worksheet
df, worksheet_name = load_points_data("first")

# Show which worksheet is being used
st.info(f"📋 Using data from worksheet: **{worksheet_name}**")

# Refresh button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# Display the data
if not df.empty:
    # Show statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total PODs", len(df))
    
    with col2:
        st.metric("Total Points", f"{df['Total Points'].sum():,.0f}")
    
    with col3:
        st.metric("Average Points", f"{df['Total Points'].mean():.1f}")
    
    # Display points table
    st.subheader("🏆 Points Table")
    
    # Style the table
    def highlight_top_3(row):
        if row['Rank'] == 1:
            return ['background-color: #FFD700'] * len(row)  # Gold
        elif row['Rank'] == 2:
            return ['background-color: #C0C0C0'] * len(row)  # Silver
        elif row['Rank'] == 3:
            return ['background-color: #CD7F32'] * len(row)  # Bronze
        else:
            return [''] * len(row)
    
    # Apply styling and display
    styled_df = df.style.apply(highlight_top_3, axis=1)
    st.dataframe(styled_df, use_container_width=True)
    
    # Show raw data
    with st.expander("📋 Raw Data"):
        st.dataframe(df)
        
        # Download option
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="points_table.csv",
            mime="text/csv"
        )

else:
    st.warning("No data available. Check your Google Sheet connection.")

# Advanced worksheet selection (if you want to let users choose)
st.markdown("---")
st.subheader("🔧 Advanced Options")

with st.expander("Worksheet Selection Options"):
    st.markdown("""
    **Current setup:** Using the first worksheet automatically.
    
    **To change which worksheet to use, modify the code:**
    
    ```python
    # Option 1: Use first worksheet (current)
    worksheet = sheet.worksheets()[0]
    
    # Option 2: Use specific worksheet by name
    worksheet = sheet.worksheet("Your Sheet Name")
    
    # Option 3: Use worksheet by index
    worksheet = sheet.worksheets()[1]  # Second worksheet
    worksheet = sheet.worksheets()[2]  # Third worksheet
    ```
    """)
