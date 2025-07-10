import arcpy
import psycopg2
from datetime import datetime

# Lais db to staging feature class
egdb_fc = r"C:\City of Kigali\Automation\Automation.gdb\parcels_nla_live"

source_ref = arcpy.SpatialReference()
source_ref.loadFromString(
    "PROJCS['ITRF_2005_TM',GEOGCS['GCS_ITRF_2005',DATUM['D_ITRF_2005'," +
    "SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0]," +
    "UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator']," +
    "PARAMETER['False_Easting',500000.0],PARAMETER['False_Northing',5000000.0]," +
    "PARAMETER['Central_Meridian',30.0],PARAMETER['Scale_Factor',0.9999]," +
    "PARAMETER['Latitude_Of_Origin',0.0],UNIT['Meter',1.0]]"
)
target_ref = arcpy.SpatialReference(32636)

conn_params = {
    "host": "10.10.87.93",              # <--- Fill in your LAIS host
    "port": "5432",
    "database": "lais",
    "user": "kigali_city",
    "password": "Lands@Kigali2025!"
}

# === Get today's date ===
today = datetime.now().strftime('%Y-%m-%d')
print(f"📅 Fetching approvals for: {today}")

# === SQL to pull ONLY today's approved parcels ===
sql = """
SELECT
    upi, receive_date, status, approval_date, transaction_type_name,
    province, district, sector, cell, village, village_code, area,
    existing_land_use, lat, long, ownership, planned_land_use,
    sale_price,
    sde.st_astext(shape) AS wkt_geom,
    last_refreshed_on
FROM rra.kigali_parcel_changes_vw
WHERE DATE(approval_date) = %s
"""

# === Step 1: Connect and Fetch ===
print("🔌 Connecting to LAIS...")
conn = psycopg2.connect(**conn_params)
cur = conn.cursor()

# Execute with today's date as parameter (safer than string concatenation)
cur.execute(sql, (today,))
rows = cur.fetchall()

print(f"📦 Retrieved {len(rows)} records approved on {today}")

# If no records for today, exit early
if len(rows) == 0:
    print("ℹ️ No approvals found for today. Exiting.")
    cur.close()
    conn.close()
    exit()

# === Step 2: Expected Fields (input side) ===
expected_fields = [
    'upi', 'receive_date', 'status', 'approval_date', 'transaction_type_name',
    'province', 'district', 'sector', 'cell', 'village', 'village_code', 'area',
    'existing_land_use', 'lat', 'long', 'ownership', 'planned_land_use',
    'sale_price', 'SHAPE@', 'last_refreshed_on'
]

# === Step 3: Resolve Actual EGDB Field Names ===
fc_fields = [f.name for f in arcpy.ListFields(egdb_fc)]
resolved_fields = []
resolved_indices = []

for i, fname in enumerate(expected_fields):
    if fname == "SHAPE@" or fname in fc_fields:
        resolved_fields.append(fname)
        resolved_indices.append(i)
    else:
        # Try matching schema-qualified fields like bpmis.sde.parcels_nla_live.area
        fq_match = next((f for f in fc_fields if f.lower().endswith("." + fname.lower())), None)
        if fq_match:
            resolved_fields.append(fq_match)
            resolved_indices.append(i)

print("🧾 Resolved insert fields:", resolved_fields)

# === Step 4: Clear existing staging data ===
print("🧹 Clearing existing staging data...")
arcpy.management.TruncateTable(egdb_fc)

# === Step 5: Insert Today's Approved Records into EGDB ===
print(f"🚀 Inserting {len(rows)} approved records into staging...")

success = 0
failures = 0
failed_upis = []

with arcpy.da.InsertCursor(egdb_fc, resolved_fields) as cursor:
    for row in rows:
        try:
            wkt_geom = row[18]  # WKT geometry column
            geom = arcpy.FromWKT(wkt_geom, source_ref)
            projected_geom = geom.projectAs(target_ref)
            
            insert_values = []
            for idx in resolved_indices:
                field_name = expected_fields[idx]
                value = row[idx]
                
                # Handle sale_price casting
                if field_name == "sale_price":
                    if value is None or value == '':
                        insert_values.append(None)
                    else:
                        insert_values.append(float(value))
                elif field_name == "SHAPE@":
                    insert_values.append(projected_geom)
                else:
                    insert_values.append(value)
            
            cursor.insertRow(insert_values)
            success += 1
            
        except Exception as e:
            upi = row[0] if len(row) > 0 else "Unknown"
            print(f"⚠️ Failed to insert UPI {upi}: {e}")
            failed_upis.append(upi)
            failures += 1

# === Cleanup ===
cur.close()
conn.close()

# === Final Report ===
print(f"\n✅ Daily Approval Sync Complete!")
print(f"   📅 Date: {today}")
print(f"   📥 Successfully inserted: {success} records")
print(f"   ⚠️ Failed insertions: {failures} records")
print(f"   🎯 Staging table now contains today's approved transactions")

if failed_upis:
    print(f"\n❌ Failed UPIs: {', '.join(failed_upis[:10])}")
    if len(failed_upis) > 10:
        print(f"   ... and {len(failed_upis) - 10} more")

# === Next Step Guidance ===
if success > 0:
    print(f"\n🔄 Ready for next step:")
    print(f"   Run your sync script to push these {success} approved transactions to live database")
else:
    print(f"\n💤 No data to sync today")