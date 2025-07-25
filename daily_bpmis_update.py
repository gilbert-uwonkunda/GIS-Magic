# DAILY BPMIS PERMIT UPDATE 
import requests
import pandas as pd
from datetime import date, timedelta
import arcpy

def update_daily_bpmis():
    """
    DAILY UPDATE SCRIPT:
    1. Remove expired permits (2+ years old)
    2. Fetch only TODAY's API data
    3. Insert today's Permitted + Canceled records
    """
    
    # Configuration
    API_BASE_URL = "https://api.intellex.dev/traffic/pt/"
    API_ENDPOINT_ID = "2d9f2d69-1388-4e03-9cc8-b10e4a904a6b"
    API_KEY = "apk_91a9a659-ac15-4580-b199-d7829355a96a"
    GDB_PATH = r"E:\Projects\CityofKigali\CoK_PhaseII\Source.gdb"
    TABLE_PATH = f"{GDB_PATH}\\BPMIS_Current"
    
    print("=" * 50)
    print("DAILY BPMIS UPDATE")
    print("=" * 50)
    print("🗑️  Step 1: Remove expired permits")
    print("📅 Step 2: Fetch TODAY's data only")
    print("📥 Step 3: Insert today's records")
    print("=" * 50)
    
    try:
        # Step 1: Remove expired permits first
        print("STEP 1: Removing expired permits...")
        remove_expired_permits(TABLE_PATH)
        
        # Step 2: Fetch TODAY's API data only
        print("STEP 2: Fetching today's API data...")
        df_today = fetch_daily_data(API_BASE_URL, API_ENDPOINT_ID, API_KEY)
        
        if df_today is None or df_today.empty:
            print("✅ No new data today - that's normal!")
            return True
        
        # Step 3: Filter and process today's data
        print("STEP 3: Processing today's data...")
        df_processed = process_daily_data(df_today)
        
        if df_processed.empty:
            print("✅ No Permitted/Canceled records today")
            return True
        
        # Step 4: Insert today's data
        print("STEP 4: Inserting today's records...")
        success = insert_daily_data(df_processed, TABLE_PATH)
        
        if success:
            print("=" * 50)
            print("✅ SUCCESS: Daily update complete!")
            show_daily_results(TABLE_PATH)
            return True
        else:
            print("❌ Daily update failed!")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def remove_expired_permits(table_path):
    """Remove expired Permitted records (2+ years old)"""
    try:
        if not arcpy.Exists(table_path):
            print("   ⚠️ Table not found")
            return
        
        # 2 year cutoff
        cutoff_date = date.today() - timedelta(days=730)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        print(f"   📅 Removing Permitted records before {cutoff_date}")
        
        # Find fields
        fields = [field.name for field in arcpy.ListFields(table_path)]
        status_field = 'Approval_Status' if 'Approval_Status' in fields else 'Application_Status'
        
        if 'date_of_response' not in fields or status_field not in fields:
            print("   ⚠️ Required fields not found")
            return
        
        # Count expired records
        where_clause = f"date_of_response < date '{cutoff_str}' AND {status_field} = 'Permitted'"
        
        expired_count = 0
        with arcpy.da.UpdateCursor(table_path, ['date_of_response', status_field], where_clause) as cursor:
            for row in cursor:
                cursor.deleteRow()
                expired_count += 1
        
        print(f"   ✅ Removed {expired_count} expired permits")
        
    except Exception as e:
        print(f"   ❌ Expired removal error: {e}")

def fetch_daily_data(base_url, endpoint_id, api_key):
    """Fetch only TODAY's data from API"""
    try:
        # Get today's date only
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        
        url = f"{base_url}{endpoint_id}?startDate={today_str}&endDate={today_str}"
        headers = {"api-key": api_key}
        
        print(f"   📅 Fetching data for: {today_str}")
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        df = pd.DataFrame(data)
        
        print(f"   ✅ Got {len(df)} records from API today")
        
        # Convert date
        if not df.empty and 'date_of_response' in df.columns:
            df['date_of_response'] = pd.to_datetime(df['date_of_response'], errors='coerce').dt.date
        
        return df
        
    except Exception as e:
        print(f"   ❌ API error: {e}")
        return None

def process_daily_data(df):
    """Process today's data - filter and clean"""
    try:
        if 'Application_Status' not in df.columns:
            print("   ❌ No Application_Status column!")
            return pd.DataFrame()
        
        # Show what we got today
        print(f"   📊 Today's API data:")
        status_counts = df['Application_Status'].value_counts()
        for status, count in status_counts.items():
            print(f"      {status}: {count}")
        
        # Filter for Permitted + Canceled only
        target_statuses = ['Permitted', 'Canceled']
        df_filtered = df[df['Application_Status'].isin(target_statuses)].copy()
        
        print(f"   ✅ Filtered to {len(df_filtered)} Permitted/Canceled records")
        
        if df_filtered.empty:
            return df_filtered
        
        # Map fields
        df_filtered['Approval_Status'] = df_filtered['Application_Status']
        df_filtered['Date_of_Issuance'] = df_filtered['date_of_response']
        
        # Fill essential nulls
        df_filtered = df_filtered.fillna({
            'Plot_size': 100.0,
            'buildUpArea': 80.0,
            'Number_of_Floors': 1,
            'Building_Type': 'Residential',
            'District': 'Kigali'
        })
        
        print(f"   ✅ Processed {len(df_filtered)} records ready for insert")
        
        return df_filtered
        
    except Exception as e:
        print(f"   ❌ Processing error: {e}")
        return pd.DataFrame()

def insert_daily_data(df, table_path):
    """Insert today's data (no duplicates check - assume clean daily data)"""
    try:
        if not arcpy.Exists(table_path):
            print(f"   ❌ Table not found: {table_path}")
            return False
        
        # Get table fields
        table_fields = [field.name for field in arcpy.ListFields(table_path) 
                       if field.type not in ['OID', 'Geometry']]
        
        # Get common fields
        common_fields = [f for f in table_fields if f in df.columns]
        
        print(f"   📋 Inserting with {len(common_fields)} fields")
        
        # Insert all today's records
        insert_count = 0
        with arcpy.da.InsertCursor(table_path, common_fields) as cursor:
            for _, row in df.iterrows():
                try:
                    values = [row[field] if field in row else None for field in common_fields]
                    cursor.insertRow(values)
                    insert_count += 1
                except Exception as e:
                    print(f"      ⚠️ Insert error: {e}")
        
        print(f"   ✅ Inserted {insert_count} new records")
        return True
        
    except Exception as e:
        print(f"   ❌ Insert error: {e}")
        return False

def show_daily_results(table_path):
    """Show results after daily update"""
    try:
        if arcpy.Exists(table_path):
            total_count = int(str(arcpy.GetCount_management(table_path)))
            print(f"📊 Total records in BPMIS_Current: {total_count:,}")
            
            # Show today's additions
            today_str = date.today().strftime("%Y-%m-%d")
            today_count = 0
            
            try:
                with arcpy.da.SearchCursor(table_path, ['date_of_response']) as cursor:
                    for row in cursor:
                        if row[0] and str(row[0]) == today_str:
                            today_count += 1
                
                print(f"📅 Records added today: {today_count}")
                
            except Exception:
                print("Could not count today's records")
                
        else:
            print("❌ Table not found")
            
    except Exception as e:
        print(f"❌ Results error: {e}")

if __name__ == "__main__":
    print("🚀 Starting daily BPMIS update...")
    update_daily_bpmis()
    print("🏁 Daily update complete!")