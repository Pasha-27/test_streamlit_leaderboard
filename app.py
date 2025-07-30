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
    st.success("✅ Step 2a: gspread imported successfully!")
except ImportError as e:
    st.error(f"❌ Step 2a: gspread import error: {e}")
    st.stop()

try:
    from google.oauth2.service_account import Credentials
    st.success("✅ Step 2b: google-auth imported successfully!")
except ImportError as e:
    st.error(f"❌ Step 2b: google-auth import error: {e}")
    st.info("💡 Using fallback oauth2client...")
    try:
        from oauth2client.service_account import ServiceAccountCredentials
        st.success("✅ Step 2b: oauth2client imported successfully!")
        USE_OAUTH2CLIENT = True
    except ImportError as e2:
        st.error(f"❌ Step 2b: Both auth libraries failed: {e2}")
        st.stop()
else:
    USE_OAUTH2CLIENT = False

# Step 3: Check if secrets exist
try:
    if "gcp_service_account" in st.secrets:
        st.success("✅ Step 3: GCP service account secrets found!")
    else:
        st.error("❌ Step 3: 'gcp_service_account' not found in secrets")
        st.info("💡 Make sure you've added secrets in Streamlit Cloud dashboard")
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
            
            if USE_OAUTH2CLIENT:
                creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
            else:
                creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPE)
            
            st.info("🔐 Authorizing client...")
            client = gspread.authorize(creds)
            
            st.info("📄 Opening spreadsheet...")
            sheet = client.open_by_key(SHEET_ID)
            
            st.info("📊 Getting worksheet...")
            worksheet = sheet.sheet1
            
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
    
    st.write("**Streamlit version:**")
    st.write(st.__version__)
    
    st.write("**Environment:**")
    import os
    st.write(f"Environment: {'Streamlit Cloud' if 'STREAMLIT_SHARING' in os.environ else 'Local'}")
    
    st.write("**Secrets keys available:**")
    st.write(list(st.secrets.keys()))

# Instructions for Streamlit Cloud
st.markdown("---")
st.subheader("☁️ Streamlit Cloud Specific Steps")

st.markdown("""
**If you're still getting import errors on Streamlit Cloud:**

1. **Check your repository structure:**
   ```
   your-repo/
   ├── app.py
   ├── requirements.txt  ← Must be in root folder
   └── README.md
   ```

2. **Verify requirements.txt content** (no extra spaces):
   ```
   streamlit
   pandas
   gspread==5.12.0
   google-auth==2.23.4
   google-auth-oauthlib==1.1.0
   google-auth-httplib2==0.1.1
   ```

3. **Force redeploy:**
   - Go to your Streamlit Cloud dashboard
   - Click "Reboot app" or "Delete and redeploy"
   - Sometimes Streamlit Cloud caches old requirements

4. **Check app logs:**
   - In Streamlit Cloud, click "Manage app"
   - Look at the build logs for any error messages
   - You should see lines like "Installing gspread..."

5. **Add secrets in Streamlit Cloud:**
   - Go to app settings → Secrets
   - Paste your secrets there (not in repository)
""")

st.markdown("---")
st.info("💡 Try rebooting your Streamlit Cloud app after updating requirements.txt!")
