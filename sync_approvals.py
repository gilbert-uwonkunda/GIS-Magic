import arcpy
import os
from datetime import datetime

def run_approval_sync():
    """  Approval Synchronization"""
    
    #  PRODUCTION CONFIGURATION
    sde_path = r"E:\Projects\CityofKigali\CoK_PhaseII\PostgreSQL-10-bpmis(sde).sde"
    feature_class_name = "bpmis.sde.CoK_Parcels_live_data"
    table_gdb_path = r"E:\Projects\CityofKigali\CoK_PhaseII\Source.gdb"
    table_name = "CoK_Permits_Current"
    
    # DATA MAPPINGS
    approval_map = {'Approved': 'Approved', 'Pending': 'Pending', 'Rejected': 'No Permit'}
    uruhushya_map = {'Approved': 'Afite Uruhushya Rwo Kubaka', 'Pending': 'Ategereje Uruhushya', 'Rejected': 'Ntaruhushya yahawe rwo Kubaka'}
    
    try:
        print(f" AI Sync Started: {datetime.now().strftime('%H:%M:%S')}")
        
        # Build lookup from permits table
        permits = {}
        with arcpy.da.SearchCursor(os.path.join(table_gdb_path, table_name), ['plot_no', 'Approval_Status']) as cursor:
            for plot_no, status in cursor:
                if status in approval_map:
                    permits[plot_no] = (approval_map[status], uruhushya_map[status])
        
        # Update live parcels
        updated = 0
        with arcpy.da.UpdateCursor(os.path.join(sde_path, feature_class_name), ['upi', 'approval', 'uruhushya']) as cursor:
            for row in cursor:
                if row[0] in permits:
                    row[1], row[2] = permits[row[0]]
                    cursor.updateRow(row)
                    updated += 1
        
        print(f" Success: {updated} parcels synchronized | {datetime.now().strftime('%H:%M:%S')}")
        return True
        
    except Exception as e:
        print(f" Error: {str(e)}")
        return False

#  ONE-CLICK EXECUTION
if __name__ == "__main__":
    run_approval_sync()