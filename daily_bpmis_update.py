# BPMIS PERMIT MANAGEMENT - FIXED FOR YOUR TABLE STRUCTURE
import requests
import pandas as pd
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import arcpy

def update_bpmis_permits():
    """
    FIXED BPMIS SCRIPT: Based on your actual table structure
    Table fields: plot_no, registered_usage, districtname, district, application_group,
    name_of_project, building_type, date_of_submission, date_of_issuance, date_of_expiry,
    date_of_response, plot_size, approval_status
    """
    
    # Configuration
    API_BASE_URL = "https://api.intellex.dev/traffic/pt/"
    API_ENDPOINT_ID = "2d9f2d69-1388-4e03-9cc8-b10e4a904a6b"
    API_KEY = "apk_91a9a659-ac15-4580-b199-d7829355a96a"
    GDB_PATH = r"C:\City of Kigali\CoK_EGDB.sde"
    TABLE_PATH = f"{GDB_PATH}\\BPMIS_Current"
    
    print("=" * 60)
    print(" BPMIS PERMIT MANAGEMENT - FIXED VERSION")
    print("=" * 60)
    print(" Target: BPMIS_Current table")
    print("Plot field: plot_no (lowercase)")
    print(" Status field: approval_status")
    print(" Date field: date_of_response")
    print(" Statuses: Permitted → Approved, Canceled → Rejected")
    print("=" * 60)
    
    try:
        # Step 1: Fetch API data
        print("\n🔄 STEP 1: Fetching API data...")
        df_api = fetch_api_data(API_BASE_URL, API_ENDPOINT_ID, API_KEY)
        
        if df_api is None or df_api.empty:
            print(" No API data received!")
            return False
        
        # Step 2: Filter for target statuses
        print("\n🔄 STEP 2: Filtering statuses...")
        df_filtered = filter_target_statuses(df_api)
        
        if df_filtered.empty:
            print("❌ No Permitted/Canceled records found!")
            return False
        
        # Step 3: Map to your table structure
        print("\n🔄 STEP 3: Mapping to table structure...")
        df_mapped = map_to_table_structure(df_filtered)
        
        # Step 4: Fill missing values
        print("\n🔄 STEP 4: Filling missing values...")
        df_clean = fill_missing_values(df_mapped)
        
        # Step 5: Remove expired permits
        print("\n🔄 STEP 5: Removing expired permits...")
        remove_expired_permits(TABLE_PATH)
        
        # Step 6: Upsert data
        print("\n🔄 STEP 6: Upserting data...")
        success = upsert_data_fixed(df_clean, TABLE_PATH)
        
        if success:
            print("\n" + "=" * 60)
            print("✅ SUCCESS: BPMIS permits updated successfully!")
            show_final_results(TABLE_PATH)
            print("=" * 60)
            return True
        else:
            print("\n❌ FAILED: Could not update permits!")
            return False
            
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def fetch_api_data(base_url, endpoint_id, api_key):
    """Fetch permit data from API for last 6 months"""
    try:
        # Calculate date range (last 6 months)
        today = date.today()
        end_date = today.strftime("%Y-%m-%d")
        start_date = (today - relativedelta(months=6)).strftime("%Y-%m-%d")
        
        # Build request
        url = f"{base_url}{endpoint_id}?startDate={start_date}&endDate={end_date}"
        headers = {"api-key": api_key}
        
        print(f"   📅 Date range: {start_date} to {end_date}")
        print(f"   🌐 Requesting API...")
        
        # Make API call
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        df = pd.DataFrame(data)
        
        print(f"   ✅ Received {len(df):,} records from API")
        
        # Show available fields for debugging
        print(f"   📋 API fields available: {list(df.columns)[:10]}...")
        
        # Convert date fields
        if 'date_of_response' in df.columns:
            df['date_of_response'] = pd.to_datetime(df['date_of_response'], errors='coerce').dt.date
            print(f"   📅 Converted date_of_response field")
        
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"   ❌ API request failed: {e}")
        return None
    except Exception as e:
        print(f"   ❌ API processing error: {e}")
        return None

def filter_target_statuses(df):
    """Filter for Permitted and Canceled records only"""
    try:
        if 'Application_Status' not in df.columns:
            print("   ❌ Application_Status column not found!")
            # Show available columns
            print(f"   📋 Available columns: {list(df.columns)}")
            return pd.DataFrame()
        
        # Show all available statuses
        all_statuses = df['Application_Status'].value_counts()
        print("   📊 Available statuses in API:")
        for status, count in all_statuses.items():
            print(f"      {status}: {count:,}")
        
        # Filter for target statuses
        target_statuses = ['Permitted', 'Canceled']
        df_filtered = df[df['Application_Status'].isin(target_statuses)].copy()
        
        print(f"   ✅ Filtered to {len(df_filtered):,} target records:")
        if not df_filtered.empty:
            filtered_counts = df_filtered['Application_Status'].value_counts()
            for status, count in filtered_counts.items():
                print(f"      {status}: {count:,}")
        
        return df_filtered
        
    except Exception as e:
        print(f"   ❌ Filter error: {e}")
        return pd.DataFrame()

def map_to_table_structure(df):
    """Map API fields to your specific table structure"""
    try:
        print("   🔄 Mapping fields to table structure...")
        df_mapped = df.copy()
        
        # STEP 1: Map status values (API → Table)
        status_mapping = {
            'Permitted': 'Approved',
            'Canceled': 'Rejected'
        }
        
        if 'Application_Status' in df_mapped.columns:
            print("   📋 Status mapping:")
            original_counts = df_mapped['Application_Status'].value_counts()
            for api_status, count in original_counts.items():
                table_status = status_mapping.get(api_status, api_status)
                print(f"      {api_status} → {table_status}: {count:,}")
            
            # Create new approval_status field
            df_mapped['approval_status'] = df_mapped['Application_Status'].map(status_mapping).fillna(df_mapped['Application_Status'])
        
        # STEP 2: Map field names to match your table structure exactly
        field_mapping = {
            # Try common plot number field variations
            'Plot_No': 'plot_no',
            'plot_number': 'plot_no',
            'PlotNo': 'plot_no',
            'PlotNumber': 'plot_no',
            'parcel_no': 'plot_no',
            'parcel_number': 'plot_no',
            
            # Other field mappings based on your table
            'Registered_Usage': 'registered_usage',
            'DistrictName': 'districtname',
            'District': 'district',
            'Application_group': 'application_group',
            'Name_Of_Project': 'name_of_project',
            'Building_Type': 'building_type',
            'date_of_submission': 'date_of_submission',
            'Date_of_Issuance': 'date_of_issuance',
            'date_of_expiry': 'date_of_expiry',
            'Plot_size': 'plot_size'
        }
        
        # Apply field mappings only if source field exists
        mapped_count = 0
        for api_field, table_field in field_mapping.items():
            if api_field in df_mapped.columns:
                df_mapped = df_mapped.rename(columns={api_field: table_field})
                print(f"      {api_field} → {table_field}")
                mapped_count += 1
        
        # Ensure plot_no field exists - try to find it with different approaches
        if 'plot_no' not in df_mapped.columns:
            # Look for any field that might contain plot numbers
            plot_candidates = []
            for col in df_mapped.columns:
                col_lower = col.lower()
                if any(keyword in col_lower for keyword in ['plot', 'parcel', 'lot', 'number', 'no']):
                    plot_candidates.append(col)
            
            if plot_candidates:
                # Use the first candidate and rename it
                first_candidate = plot_candidates[0]
                df_mapped = df_mapped.rename(columns={first_candidate: 'plot_no'})
                print(f"   🎯 Using {first_candidate} as plot_no field")
            else:
                print("   ⚠️ WARNING: No plot number field found in API data!")
                # Create a dummy plot_no field with sequential numbers
                df_mapped['plot_no'] = [f"API_{i+1:06d}" for i in range(len(df_mapped))]
                print("   ⚠️ Created dummy plot_no field with sequential numbers")
        
        print(f"   ✅ Mapped {mapped_count} fields successfully")
        
        # Show final field mapping
        final_fields = [col for col in df_mapped.columns if col in [
            'plot_no', 'registered_usage', 'districtname', 'district', 'application_group',
            'name_of_project', 'building_type', 'date_of_submission', 'date_of_issuance',
            'date_of_expiry', 'date_of_response', 'plot_size', 'approval_status'
        ]]
        print(f"   📋 Final mapped fields for table: {final_fields}")
        
        return df_mapped
        
    except Exception as e:
        print(f"   ❌ Mapping error: {e}")
        return df

def fill_missing_values(df):
    """Fill null values with smart defaults"""
    try:
        print(f"   🔧 Processing {len(df):,} records for null values...")
        df_filled = df.copy()
        original_nulls = df_filled.isnull().sum().sum()
        
        # Smart defaults based on approval status
        for idx, row in df_filled.iterrows():
            status = str(row.get('approval_status', '')).lower()
            
            # Fill essential fields
            if pd.isna(row.get('plot_size')) or row.get('plot_size') == 0:
                df_filled.at[idx, 'plot_size'] = 150.0 if status == 'rejected' else 100.0
            
            if pd.isna(row.get('registered_usage')) or str(row.get('registered_usage')).strip() in ['', 'nan', 'None']:
                df_filled.at[idx, 'registered_usage'] = 'Residential'
            
            if pd.isna(row.get('building_type')) or str(row.get('building_type')).strip() in ['', 'nan', 'None']:
                df_filled.at[idx, 'building_type'] = 'Rejected Project' if status == 'rejected' else 'Residential'
            
            if pd.isna(row.get('district')) or str(row.get('district')).strip() in ['', 'nan', 'None']:
                df_filled.at[idx, 'district'] = 'Kigali'
            
            if pd.isna(row.get('districtname')) or str(row.get('districtname')).strip() in ['', 'nan', 'None']:
                df_filled.at[idx, 'districtname'] = 'Kigali'
        
        # Final cleanup with global defaults
        global_defaults = {
            'plot_size': 100.0,
            'registered_usage': 'Residential',
            'building_type': 'Residential',
            'district': 'Kigali',
            'districtname': 'Kigali',
            'application_group': 'Building Permit',
            'name_of_project': 'Residential Project'
        }
        
        for col, default_val in global_defaults.items():
            if col in df_filled.columns:
                df_filled[col] = df_filled[col].fillna(default_val)
                if isinstance(default_val, str):
                    df_filled[col] = df_filled[col].replace(['', 'nan', 'None'], default_val)
        
        final_nulls = df_filled.isnull().sum().sum()
        filled_count = original_nulls - final_nulls
        
        print(f"   ✅ Filled {filled_count:,} null values")
        print(f"   📊 Null count: {original_nulls:,} → {final_nulls:,}")
        
        return df_filled
        
    except Exception as e:
        print(f"   ❌ Fill nulls error: {e}")
        return df

def remove_expired_permits(table_path):
    """Remove approved permits older than 2 years"""
    try:
        if not arcpy.Exists(table_path):
            print("   ⚠️ Table does not exist, skipping cleanup")
            return
        
        # Calculate 2-year cutoff date
        cutoff_date = date.today() - timedelta(days=730)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        print(f"   📅 Removing Approved permits before {cutoff_date}")
        
        # Count before cleanup
        initial_count = int(str(arcpy.GetCount_management(table_path)))
        
        # Remove expired approved records using your actual field names
        where_clause = f"date_of_response < date '{cutoff_str}' AND approval_status = 'Approved'"
        
        expired_count = 0
        try:
            with arcpy.da.UpdateCursor(table_path, ['date_of_response', 'approval_status'], where_clause) as cursor:
                for row in cursor:
                    cursor.deleteRow()
                    expired_count += 1
        except Exception as e:
            print(f"   ⚠️ Cleanup query failed: {e}")
            return
        
        final_count = int(str(arcpy.GetCount_management(table_path)))
        
        print(f"   ✅ Removed {expired_count:,} expired permits")
        print(f"   📊 Record count: {initial_count:,} → {final_count:,}")
        
    except Exception as e:
        print(f"   ❌ Cleanup error: {e}")

def upsert_data_fixed(df, table_path):
    """Upsert data using your exact table structure"""
    try:
        if not arcpy.Exists(table_path):
            print(f"   ❌ Table not found: {table_path}")
            return False
        
        print(f"   🔄 Upserting {len(df):,} records...")
        
        # Define fields that exist in your table
        table_fields = [
            'plot_no', 'registered_usage', 'districtname', 'district', 'application_group',
            'name_of_project', 'building_type', 'date_of_submission', 'date_of_issuance',
            'date_of_expiry', 'date_of_response', 'plot_size', 'approval_status'
        ]
        
        # Find common fields between DataFrame and table
        df_fields = df.columns.tolist()
        common_fields = [f for f in table_fields if f in df_fields]
        
        if 'plot_no' not in common_fields:
            print("   ❌ plot_no field is missing from DataFrame!")
            return False
        
        print(f"   📋 Using {len(common_fields)} common fields: {common_fields}")
        
        # STEP 1: Remove duplicates from API data
        print("   🧹 Step 1: Removing API duplicates...")
        original_count = len(df)
        
        if 'date_of_response' in df.columns:
            df_clean = df.sort_values('date_of_response', ascending=False).drop_duplicates(subset=['plot_no'], keep='first')
        else:
            df_clean = df.drop_duplicates(subset=['plot_no'], keep='first')
        
        removed_dupes = original_count - len(df_clean)
        print(f"   ✅ Removed {removed_dupes} API duplicates ({original_count} → {len(df_clean)})")
        
        # Get API plot numbers
        api_plots = set()
        for plot in df_clean['plot_no'].dropna():
            plot_str = str(plot).strip().upper()
            if plot_str and plot_str != 'NAN':
                api_plots.add(plot_str)
        
        print(f"   📊 API contains {len(api_plots)} unique plot numbers")
        
        # STEP 2: Get current table count
        initial_count = int(str(arcpy.GetCount_management(table_path)))
        print(f"   📊 Current table has {initial_count:,} records")
        
        # STEP 3: Remove existing matching plots
        print("   🗑️  Step 3: Removing existing plots...")
        removed_count = 0
        
        try:
            with arcpy.da.UpdateCursor(table_path, ['plot_no']) as cursor:
                for row in cursor:
                    if row[0] is not None:
                        existing_plot = str(row[0]).strip().upper()
                        if existing_plot in api_plots:
                            cursor.deleteRow()
                            removed_count += 1
        except Exception as e:
            print(f"   ⚠️ Error removing existing plots: {e}")
        
        print(f"   ✅ Removed {removed_count:,} existing plots")
        
        # STEP 4: Insert fresh data
        print("   📥 Step 4: Inserting fresh data...")
        insert_count = 0
        error_count = 0
        
        try:
            with arcpy.da.InsertCursor(table_path, common_fields) as cursor:
                for _, row in df_clean.iterrows():
                    try:
                        values = []
                        for field in common_fields:
                            value = row[field] if field in row else None
                            
                            # Handle null values
                            if pd.isna(value):
                                value = None
                            # Handle date fields
                            elif field in ['date_of_submission', 'date_of_issuance', 'date_of_expiry', 'date_of_response'] and value is not None:
                                if hasattr(value, 'strftime'):
                                    value = value.strftime('%Y-%m-%d')
                                else:
                                    value = str(value)
                            
                            values.append(value)
                        
                        cursor.insertRow(values)
                        insert_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        if error_count <= 3:
                            plot_no = row.get('plot_no', 'Unknown')
                            print(f"      ⚠️ Insert error for Plot {plot_no}: {str(e)[:100]}")
        
        except Exception as e:
            print(f"   ❌ Insert cursor error: {e}")
            return False
        
        # Final verification
        final_count = int(str(arcpy.GetCount_management(table_path)))
        
        print(f"   ✅ Upsert completed:")
        print(f"      • Initial records: {initial_count:,}")
        print(f"      • Removed existing: {removed_count:,}")
        print(f"      • Inserted new: {insert_count:,}")
        print(f"      • Insert errors: {error_count:,}")
        print(f"      • Final records: {final_count:,}")
        
        return insert_count > 0
        
    except Exception as e:
        print(f"   ❌ Upsert error: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_final_results(table_path):
    """Display final results summary"""
    try:
        if not arcpy.Exists(table_path):
            print("❌ Final table not found")
            return
        
        # Total count
        total_count = int(str(arcpy.GetCount_management(table_path)))
        print(f"📊 BPMIS_Current total records: {total_count:,}")
        
        # Status breakdown
        try:
            status_counts = {}
            with arcpy.da.SearchCursor(table_path, ['approval_status']) as cursor:
                for row in cursor:
                    if row[0]:
                        status = str(row[0])
                        status_counts[status] = status_counts.get(status, 0) + 1
            
            print("📋 Status breakdown:")
            for status, count in sorted(status_counts.items()):
                percentage = (count / total_count * 100) if total_count > 0 else 0
                print(f"   • {status}: {count:,} ({percentage:.1f}%)")
            
            # Recent records count (last 30 days)
            recent_date = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
            recent_count = 0
            with arcpy.da.SearchCursor(table_path, ['date_of_response'], f"date_of_response >= date '{recent_date}'") as cursor:
                for row in cursor:
                    recent_count += 1
            print(f"📅 Recent records (last 30 days): {recent_count:,}")
                
        except Exception as e:
            print(f"⚠️ Could not generate detailed breakdown: {e}")
            
    except Exception as e:
        print(f"❌ Results display error: {e}")

# Main execution
if __name__ == "__main__":
    print("🚀 Starting BPMIS Permit Management...")
    success = update_bpmis_permits()
    
    if success:
        print("🎉 BPMIS update completed successfully!")
    else:
        print("💥 BPMIS update failed!")
    
    print("🏁 Script finished.")
