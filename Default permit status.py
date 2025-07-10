import arcpy
import datetime
import csv

# Configure default permit status to Parcels
live_fc = r"C:\City of Kigali\Analysis.gdb\CoK_Parcels_live_data"
log_file = r"C:\City of Kigali\null_field_update_log.csv"

# === FIELDS TO UPDATE WITH DEFAULT VALUES ===
field_updates = {
    "uruhushya": "Ntamakuru Ku ruhushya",
    "approval": "Field_Inspection"
}

print("=" * 60)
print("🔧 NULL FIELD UPDATER - CITY OF KIGALI")
print(f"📅 Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# === VERIFY FIELDS EXIST ===
print("\n[INFO] Verifying fields exist in database...")
existing_fields = [f.name.lower() for f in arcpy.ListFields(live_fc)]
fields_to_process = {}

for field_name, default_value in field_updates.items():
    if field_name.lower() in existing_fields:
        # Get the actual field name (case-sensitive)
        actual_field_name = next(f.name for f in arcpy.ListFields(live_fc) if f.name.lower() == field_name.lower())
        fields_to_process[actual_field_name] = default_value
        print(f"   ✅ Found field: {actual_field_name}")
    else:
        print(f"   ❌ Field not found: {field_name}")

if not fields_to_process:
    print("\n[ERROR] No valid fields found to update. Exiting.")
    exit()

# === SET UP LOGGING ===
log = open(log_file, mode='w', newline='', encoding='utf-8')
writer = csv.DictWriter(log, fieldnames=["upi", "field_name", "old_value", "new_value", "timestamp", "action"])
writer.writeheader()

# === ANALYZE NULL VALUES ===
print(f"\n[INFO] Analyzing NULL values in {len(fields_to_process)} fields...")

# Build field list for cursor (UPI + fields to update)
cursor_fields = ["upi"] + list(fields_to_process.keys())
null_counts = {field: 0 for field in fields_to_process.keys()}
total_records = 0

# First pass: count NULL values
with arcpy.da.SearchCursor(live_fc, cursor_fields) as cursor:
    for row in cursor:
        total_records += 1
        for i, field_name in enumerate(fields_to_process.keys(), start=1):
            if row[i] is None or str(row[i]).strip() == "":
                null_counts[field_name] += 1

print(f"\n[ANALYSIS] NULL Value Report:")
print(f"   📊 Total records in database: {total_records:,}")
for field_name, null_count in null_counts.items():
    percentage = (null_count / total_records) * 100 if total_records > 0 else 0
    print(f"   📋 {field_name}: {null_count:,} NULL values ({percentage:.1f}%)")

# === UPDATE NULL VALUES ===
print(f"\n[INFO] Updating NULL values...")
now = datetime.datetime.now().isoformat()
update_counts = {field: 0 for field in fields_to_process.keys()}
total_updates = 0

with arcpy.da.UpdateCursor(live_fc, cursor_fields) as cursor:
    for row in cursor:
        upi = row[0]
        row_updated = False
        
        for i, (field_name, default_value) in enumerate(fields_to_process.items(), start=1):
            current_value = row[i]
            
            # Check if value is NULL or empty
            if current_value is None or str(current_value).strip() == "":
                # Update the value
                row[i] = default_value
                row_updated = True
                update_counts[field_name] += 1
                
                # Log the update
                writer.writerow({
                    "upi": upi,
                    "field_name": field_name,
                    "old_value": "NULL" if current_value is None else f"'{current_value}'",
                    "new_value": default_value,
                    "timestamp": now,
                    "action": "null_value_updated"
                })
        
        # Update the row if any field was changed
        if row_updated:
            cursor.updateRow(row)
            total_updates += 1

# === FINALIZE ===
log.close()

# === FINAL REPORT ===
print(f"\n[SUCCESS] NULL Value Update Complete!")
print(f"   📝 Total records updated: {total_updates:,}")

for field_name, update_count in update_counts.items():
    default_value = fields_to_process[field_name]
    print(f"   🔧 {field_name}: {update_count:,} values updated to '{default_value}'")

print(f"\n[INFO] Detailed log saved to: {log_file}")

# === VERIFICATION ===
print(f"\n[VERIFICATION] Post-update NULL count check...")
verification_null_counts = {field: 0 for field in fields_to_process.keys()}

with arcpy.da.SearchCursor(live_fc, cursor_fields) as cursor:
    for row in cursor:
        for i, field_name in enumerate(fields_to_process.keys(), start=1):
            if row[i] is None or str(row[i]).strip() == "":
                verification_null_counts[field_name] += 1

print(f"   📊 Remaining NULL values:")
for field_name, remaining_nulls in verification_null_counts.items():
    percentage = (remaining_nulls / total_records) * 100 if total_records > 0 else 0
    print(f"   📋 {field_name}: {remaining_nulls:,} NULL values ({percentage:.1f}%)")

if sum(verification_null_counts.values()) == 0:
    print(f"\n🎉 SUCCESS: All NULL values have been updated!")
else:
    print(f"\n⚠️  Note: Some NULL values remain (may be newly added records)")

print(f"\n✅ Script completed successfully!")
print("=" * 60)