import arcpy
import datetime
import csv

# === CONFIG ===
staging_fc = r"C:\City of Kigali\Automation\Automation.gdb\parcels_nla_live"
live_fc = r"C:\City of Kigali\Automation\Automation.gdb\CoK_Parcels_live_data_ExportFeatures"
log_file = r"C:\City of Kigali\parcel_sync_logg.csv"

# === EXCLUDE FIELDS NOT TO SYNC ===
exclude_fields = ["OBJECTID", "GlobalID", "CreationDate", "Creator", "EditDate", "Editor"]

# === GET ALL COMMON FIELDS ===
live_fields = [f.name for f in arcpy.ListFields(live_fc) if f.name not in exclude_fields]
staging_fields = [f.name for f in arcpy.ListFields(staging_fc) if f.name not in exclude_fields]
common_fields = list(set(live_fields) & set(staging_fields))

# Ensure 'upi' is first for key matching
if "upi" not in common_fields:
    raise ValueError("Field 'upi' must be present in both tables")
common_fields.remove("upi")
sync_fields = ["upi"] + sorted(common_fields) + ["SHAPE@"]

# === LOG SETUP ===
log = open(log_file, mode='w', newline='', encoding='utf-8')
writer = csv.DictWriter(log, fieldnames=["action", "upi", "timestamp", "changes_detected"])
writer.writeheader()

# === BUILD LOOKUP FROM LIVE (More efficient) ===
print("🔍 Building lookup index from live data...")
live_dict = {}
with arcpy.da.SearchCursor(live_fc, ["upi"]) as cur:
    for row in cur:
        live_dict[row[0]] = True

print(f"📊 Live database contains {len(live_dict)} parcels")

# === LOAD STAGING DATA ===
print("📥 Loading staging data...")
staging_data = {}
staging_upis = []

with arcpy.da.SearchCursor(staging_fc, sync_fields) as cur:
    for row in cur:
        upi = row[0]
        staging_data[upi] = row
        staging_upis.append(upi)

print(f"📊 Staging contains {len(staging_upis)} transaction records")

# === SEPARATE INSERTS FROM UPDATES ===
inserts = []
updates = []

for upi in staging_upis:
    if upi in live_dict:
        updates.append(upi)
    else:
        inserts.append(upi)

print(f"📋 Analysis: {len(inserts)} new parcels, {len(updates)} updates")

# === PROCESS UPDATES (Efficient approach) ===
now = datetime.datetime.now().isoformat()
update_count = 0

if updates:
    print("📝 Processing updates...")
    # Create a set for O(1) lookup
    updates_set = set(updates)
    
    with arcpy.da.UpdateCursor(live_fc, sync_fields) as update_cursor:
        for live_row in update_cursor:
            upi = live_row[0]
            if upi in updates_set:
                staging_row = staging_data[upi]
                
                # Check if data actually changed before updating
                if live_row[1:] != staging_row[1:]:
                    live_row[1:] = staging_row[1:]
                    update_cursor.updateRow(live_row)
                    
                    writer.writerow({
                        "action": "update", 
                        "upi": upi, 
                        "timestamp": now,
                        "changes_detected": "yes"
                    })
                    update_count += 1
                else:
                    # Log that record was processed but no changes needed
                    writer.writerow({
                        "action": "no_change", 
                        "upi": upi, 
                        "timestamp": now,
                        "changes_detected": "no"
                    })
                
                # Remove from set to avoid reprocessing
                updates_set.remove(upi)
                
                # Early exit if all updates processed
                if not updates_set:
                    break

# === PROCESS INSERTS ===
insert_count = 0

if inserts:
    print("➕ Processing inserts...")
    with arcpy.da.InsertCursor(live_fc, sync_fields) as insert_cursor:
        for upi in inserts:
            staging_row = staging_data[upi]
            insert_cursor.insertRow(staging_row)
            
            writer.writerow({
                "action": "insert", 
                "upi": upi, 
                "timestamp": now,
                "changes_detected": "new_record"
            })
            insert_count += 1

# === FINALIZE ===
log.close()

# === PERFORMANCE SUMMARY ===
total_operations = insert_count + update_count
efficiency_note = ""

if len(staging_upis) > 0:
    change_rate = (total_operations / len(staging_upis)) * 100
    efficiency_note = f" ({change_rate:.1f}% of staging records resulted in database changes)"

print(f"\n✅ Sync complete!")
print(f"   📥 Inserted: {insert_count} new parcels")
print(f"   📝 Updated: {update_count} existing parcels")
print(f"   📊 Total operations: {total_operations}{efficiency_note}")
print(f"   🏦 Live database now contains: {len(live_dict) + insert_count} parcels")
print(f"📄 Log saved to: {log_file}")

# === BASIC SUBDIVISION DETECTION (Optional enhancement) ===
if inserts:
    print(f"\n🔍 Quick subdivision check...")
    potential_subdivisions = 0
    
    for new_upi in inserts:
        # Simple check: if new UPI looks like it came from subdivision
        if (new_upi[-1].isalpha() and new_upi[:-1] in live_dict) or \
           (new_upi.count('-') > 1 and '-'.join(new_upi.split('-')[:-1]) in live_dict):
            potential_subdivisions += 1
    
    if potential_subdivisions > 0:
        print(f"   🔄 Detected {potential_subdivisions} potential subdivision results")
        print(f"   💡 Consider running detailed subdivision analysis for audit purposes")