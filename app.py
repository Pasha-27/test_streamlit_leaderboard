import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Page configuration
st.set_page_config(
    page_title="Sample Dashboard",
    page_icon="📊",
    layout="wide"
)

# Title
st.title("📊 Sample Google Sheets Dashboard")
st.markdown("---")

# Function to load data from Google Sheets
@st.cache_data(ttl=300)  # Cache data for 5 minutes
def load_data_from_sheets():
    """
    Load data from Google Sheets
    """
    try:
        # Get credentials from Streamlit secrets
        SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
        SHEET_ID = st.secrets["sheet_id"]
        
        # Define the scope
        SCOPE = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        
        # Authorize and connect
        creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        sheet = client.open_by_key(SHEET_ID).sheet1  # Use first sheet
        
        # Get all data as records (list of dictionaries)
        data = sheet.get_all_records()
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Sidebar
st.sidebar.header("Controls")

# Refresh button
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📋 Data from Google Sheets")
    
    # Load and display data
    df = load_data_from_sheets()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # Basic statistics
        st.subheader("📈 Basic Statistics")
        st.write(f"**Total rows:** {len(df)}")
        st.write(f"**Total columns:** {len(df.columns)}")
        
        # Show column info
        with st.expander("Column Information"):
            for col in df.columns:
                col_type = df[col].dtype
                non_null_count = df[col].count()
                st.write(f"**{col}:** {col_type} ({non_null_count} non-null values)")
        
    else:
        st.warning("No data available. Please check your Google Sheets connection.")

with col2:
    st.subheader("ℹ️ Information")
    
    if not df.empty:
        # Show sample data
        st.write("**Sample Data:**")
        st.write(df.head(3))
        
        # Show numeric columns if any
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            st.write("**Numeric Columns:**")
            for col in numeric_cols:
                st.write(f"• {col}")
                st.write(f"  Sum: {df[col].sum():,.2f}")
                st.write(f"  Average: {df[col].mean():.2f}")
                st.write("---")

# Additional sections
st.markdown("---")

# Charts section (if numeric data exists)
if not df.empty:
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if numeric_cols:
        st.subheader("📊 Sample Charts")
        
        # Select column for chart
        chart_col = st.selectbox("Select column for chart:", numeric_cols)
        
        if chart_col:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Line Chart**")
                st.line_chart(df[chart_col])
            
            with col2:
                st.write("**Bar Chart**")
                st.bar_chart(df[chart_col])

# Raw data section
with st.expander("🔍 Raw Data (Expandable)"):
    if not df.empty:
        st.write("**Full Dataset:**")
        st.dataframe(df)
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="sheet_data.csv",
            mime="text/csv"
        )
    else:
        st.write("No data to display")

# Connection test section
st.markdown("---")
st.subheader("🔧 Connection Test")

if st.button("Test Google Sheets Connection"):
    with st.spinner("Testing connection..."):
        try:
            SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
            SHEET_ID = st.secrets["sheet_id"]
            SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
            client = gspread.authorize(creds)
            sheet = client.open_by_key(SHEET_ID)
            
            st.success(f"✅ Connection successful!")
            st.info(f"📄 Sheet title: {sheet.title}")
            st.info(f"📊 Available worksheets: {[ws.title for ws in sheet.worksheets()]}")
            
        except Exception as e:
            st.error(f"❌ Connection failed: {str(e)}")

# Footer
st.markdown("---")
st.markdown("*This is a sample Streamlit app connected to Google Sheets. Modify as needed!*")
