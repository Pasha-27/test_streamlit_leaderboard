import streamlit as st
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Debug App",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 Debug Mode - Step by Step")

# Step 1: Check if streamlit is working
st.success("✅ Step 1: Streamlit is working!")

# Step 2: Check imports
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    st.success("✅ Step 2: All imports successful!")
except ImportError as e:
    st.error(f"❌ Step 2: Import error: {e}")
    st.stop()

# Step 3: Check if secrets exist
try:
    if "gcp_service_account" in st.secrets:
        st.success("✅ Step 3: GCP service account secrets found!")
    else:
        st.error("❌ Step 3: 'gcp_service_account' not found in secrets")
        st.stop()
    
    if "sheet_id" in st.secrets:
        st.success("✅ Step 3b: Sheet ID found in secrets!")
        st.info(f"Sheet ID (first 10 chars): {str(st.secrets['sheet_id'])[:10]}...")
    else:
        st.error("❌ Step 3b: 'sheet_id' not found in secrets")
        st.stop()
        
except Exception as e:
    st.error(f"❌ Step 3: Error accessing secrets: {e}")
    st.stop()

# Step 4: Check service account credentials structure
try:
    SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
    required_fields = ["type", "project_id", "private_key", "client_email"]
    
    missing_fields = []
    for field in required_fields:
        if field not in SERVICE_ACCOUNT_INFO:
            missing_fields.append(field)
    
    if missing_fields:
        st.error(f"❌ Step 4: Missing required fields in service account: {missing_fields}")
        st.stop()
    else:
        st.success("✅ Step 4: Service account has all required fields!")
        st.info(f"Service account email: {SERVICE_ACCOUNT_INFO['client_email']}")
        
except Exception as e:
    st.error(f"❌ Step 4: Error checking service account structure: {e}")
    st.stop()

# Step 5: Test Google Sheets connection
st.markdown("---")
st.subheader("🔗 Google Sheets Connection Test")

if st.button("Test Connection"):
    try:
        with st.spinner("Testing connection..."):
            # Get credentials
            SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
            SHEET_ID = st.secrets["sheet_id"]
            
            # Define scope
            SCOPE = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly"
            ]
            
            st.info("🔑 Creating credentials...")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
            
            st.info("🔐 Authorizing client...")
            client = gspread.authorize(creds)
            
            st.info("📄 Opening spreadsheet...")
            sheet = client.open_by_key(SHEET_ID)
            
            st.info("📊 Getting worksheet...")
            worksheet = sheet.sheet1  # or sheet.worksheets()[0]
            
            st.info("📋 Reading data...")
            # Try to get just first few rows to test
            data = worksheet.get_all_records(head=5)
            
            st.success("✅ Step 5: Connection successful!")
            st.info(f"📄 Sheet title: {sheet.title}")
            st.info(f"📊 Available worksheets: {[ws.title for ws in sheet.worksheets()]}")
            st.info(f"📋 Sample data rows: {len(data)}")
            
            if data:
                st.write("**Sample data:**")
                df_sample = pd.DataFrame(data)
                st.dataframe(df_sample.head())
            
    except gspread.SpreadsheetNotFound:
        st.error("❌ Spreadsheet not found. Check your sheet_id.")
    except gspread.APIError as e:
        st.error(f"❌ Google Sheets API error: {e}")
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}")
        st.error(f"Error type: {type(e).__name__}")

# Step 6: Debug information
st.markdown("---")
st.subheader("🐛 Debug Information")

with st.expander("Show Debug Info"):
    st.write("**Python version:**")
    import sys
    st.write(sys.version)
    
    st.write("**Installed packages:**")
    try:
        import pkg_resources
        installed_packages = [d for d in pkg_resources.working_set]
        relevant_packages = [str(d) for d in installed_packages if any(pkg in str(d).lower() for pkg in ['streamlit', 'gspread', 'oauth2', 'pandas'])]
        for pkg in relevant_packages:
            st.write(f"- {pkg}")
    except:
        st.write("Could not retrieve package information")
    
    st.write("**Secrets keys available:**")
    st.write(list(st.secrets.keys()))

# Instructions
st.markdown("---")
st.subheader("📋 Next Steps")

st.markdown("""
**If you see errors above:**

1. **Import errors:** Install missing packages:
   ```bash
   pip install streamlit pandas gspread oauth2client
   ```

2. **Secrets errors:** Check your `.streamlit/secrets.toml` file:
   - Make sure it exists in the right location
   - Verify all required fields are present
   - Check for syntax errors (proper quotes, brackets)

3. **Connection errors:** 
   - Verify your Google Sheet is shared with the service account email
   - Check that the sheet_id is correct
   - Ensure Google Sheets API is enabled in Google Cloud Console

4. **API errors:**
   - Enable Google Sheets API and Google Drive API
   - Check service account permissions
   - Verify the sheet exists and is accessible

**Common fixes:**
- Double-check the sheet ID from your Google Sheets URL
- Make sure the service account email has access to the sheet
- Verify your secrets.toml file matches the JSON file exactly
""")

st.markdown("---")
st.info("💡 Once all steps show ✅, your main app should work!")
