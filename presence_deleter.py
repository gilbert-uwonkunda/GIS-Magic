#!/usr/bin/env python3
"""
Simple Presence Layer Deleter
Updated for E:\HealthGIS_Automation folder structure
"""

import sys
import datetime
from arcgis.gis import GIS
from arcgis.features import FeatureLayer

def log_message(message):
    """Simple logging function"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    
    # Also write to log file
    try:
        with open("E:/Scripts/HealthGIS_Automation/logs/presence_deletion.log", "a", encoding="utf-8") as log_file:
            log_file.write(log_entry + "\n")
    except:
        pass  # Continue even if logging fails

def main():
    """Main deletion function"""
    log_message("=== PRESENCE LAYER DELETION STARTED ===")
    
    try:
        # 1. Connect to ArcGIS Enterprise portal
        log_message("Connecting to portal...")
        gis = GIS("https://esrirw.rw/portal", "gilbertu@esri_rw", "BeatitG@#1996!!")
        log_message("Connected to portal successfully.")

        # 2. Access feature layer
        layer_url = "https://esrirw.rw/server/rest/services/Hosted/presence_0a7705de1c85423ba8ff60c0ad728abb/FeatureServer/0"
        fl = FeatureLayer(layer_url)
        log_message(f"Accessing layer: {layer_url}")

        # 3. Query all features (OBJECTIDs)
        log_message("Querying features...")
        result = fl.query(where="1=1", out_fields="objectid", return_geometry=False)
        object_ids = [str(feature.attributes["objectid"]) for feature in result.features]

        # 4. Perform deletion
        if object_ids:
            log_message(f"Found {len(object_ids)} features. Starting deletion...")

            # Delete in batches to avoid timeouts for large datasets
            batch_size = 10000
            total_deleted = 0
            
            for i in range(0, len(object_ids), batch_size):
                batch_num = i // batch_size + 1
                batch = object_ids[i:i + batch_size]
                
                log_message(f"Processing batch {batch_num} ({len(batch)} features)...")
                
                delete_result = fl.edit_features(deletes=",".join(batch))

                # Check deletion results
                if "deleteResults" in delete_result:
                    success_count = sum(1 for r in delete_result["deleteResults"] if r.get("success"))
                    total_deleted += success_count
                    log_message(f"Batch {batch_num}: Successfully deleted {success_count} features.")
                else:
                    log_message(f"Batch {batch_num}: Unexpected response: {delete_result}")
            
            log_message(f"DELETION COMPLETED: {total_deleted} out of {len(object_ids)} features deleted")
        else:
            log_message("No features found to delete.")
        
        log_message("=== PRESENCE LAYER DELETION FINISHED SUCCESSFULLY ===")
        return True

    except Exception as e:
        error_msg = f"Error occurred: {str(e)}"
        log_message(error_msg)
        log_message("=== PRESENCE LAYER DELETION FAILED ===")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)