import arcpy
import os
from datetime import datetime

def run_approval_sync():
    """Enhanced Approval Synchronization with Field Inspection Logic"""
    
    # TEST CONFIGURATION - Using local GDB for testing
    sde_path = r"C:\City of Kigali\CoK_EGDB.sde"
    feature_class_name = "bpmis.sde.CoK_Parcels_live_data"
    table_gdb_path = r"C:\City of Kigali\CoK_EGDB.sde"
    table_name = "BPMIS_Current"
    
    # DATA MAPPINGS
    approval_map = {'Approved': 'Approved', 'Pending': 'Pending', 'Rejected': 'No Permit'}
    uruhushya_map = {'Approved': 'Afite Uruhushya Rwo Kubaka', 'Pending': 'Ategereje Uruhushya', 'Rejected': 'Ntaruhushya yahawe rwo Kubaka'}
    
    # FIELD INSPECTION MAPPINGS (for parcels NOT in BPMIS_Current)
    field_inspection_approval = 'Field_Inspection'
    field_inspection_uruhushya = 'Ntamakuru Ku ruhushya'  # No permit information in Kinyarwanda
    
    try:
        print(f"  Sync Started: {datetime.now().strftime('%H:%M:%S')}")
        
        # STEP 1: Build lookup from permits table (BPMIS_Current)
        print(" Building permit lookup from BPMIS_Current...")
        permits = {}
        permit_count = 0
        
        # Check if table exists
        table_path = os.path.join(table_gdb_path, table_name)
        if not arcpy.Exists(table_path):
            print(f" Error: Table {table_name} not found!")
            return False
        
        # Build permit lookup dictionary
        with arcpy.da.SearchCursor(table_path, ['plot_no', 'Approval_Status']) as cursor:
            for plot_no, status in cursor:
                if plot_no and status in approval_map:  # Only include valid plot numbers and statuses
                    permits[str(plot_no).strip()] = (approval_map[status], uruhushya_map[status])
                    permit_count += 1
        
        print(f" Found {permit_count:,} valid permits in BPMIS_Current")
        
        # STEP 2: Update live parcels with enhanced logic
        print(" Synchronizing parcel statuses...")
        
        # Check if parcel feature class exists
        parcel_path = os.path.join(sde_path, feature_class_name)
        if not arcpy.Exists(parcel_path):
            print(f" Error: Feature class {feature_class_name} not found!")
            return False
        
        # Counters for reporting
        matched_updated = 0
        field_inspection_assigned = 0
        total_parcels = 0
        
        # Update parcels
        with arcpy.da.UpdateCursor(parcel_path, ['upi', 'approval', 'uruhushya']) as cursor:
            for row in cursor:
                total_parcels += 1
                upi = str(row[0]).strip() if row[0] else ""
                
                if upi in permits:
                    # UPI EXISTS in BPMIS_Current - use actual permit status
                    row[1], row[2] = permits[upi]
                    cursor.updateRow(row)
                    matched_updated += 1
                else:
                    # UPI DOES NOT EXIST in BPMIS_Current - needs field inspection
                    row[1] = field_inspection_approval
                    row[2] = field_inspection_uruhushya
                    cursor.updateRow(row)
                    field_inspection_assigned += 1
        
        # STEP 3: Final reporting
        print(f" Synchronization Complete!")
        print(f"    Total parcels processed: {total_parcels:,}")
        print(f"    Matched with permits: {matched_updated:,}")
        print(f"    Assigned Field Inspection: {field_inspection_assigned:,}")
        print(f"    Completed: {datetime.now().strftime('%H:%M:%S')}")
        
        # Show breakdown of matched statuses
        if matched_updated > 0:
            status_breakdown = {}
            with arcpy.da.SearchCursor(parcel_path, ['approval']) as cursor:
                for row in cursor:
                    if row[0]:
                        status = row[0]
                        status_breakdown[status] = status_breakdown.get(status, 0) + 1
            
            print(f" Final status breakdown:")
            for status, count in sorted(status_breakdown.items()):
                percentage = (count / total_parcels * 100) if total_parcels > 0 else 0
                print(f"   • {status}: {count:,} ({percentage:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f" Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# ONE-CLICK EXECUTION
if __name__ == "__main__":
    run_approval_sync()
