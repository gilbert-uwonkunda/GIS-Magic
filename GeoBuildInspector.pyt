import arcpy
import sys
import os
from datetime import datetime

# Define input parameters
Parcels_Name = arcpy.GetParameterAsText(0)  # Input Parcels Feature Class
Zoning_Layer = arcpy.GetParameterAsText(1)  # Input Zoning Feature Class
Detected_Constructions = arcpy.GetParameterAsText(2)  # Input Detected Constructions Feature Class
BPMIS_Data = arcpy.GetParameterAsText(3)  # Input BPMIS Table/Feature Class
Output_Geodatabase = arcpy.GetParameterAsText(4)  # Output Geodatabase
Image_Acquisition_Date = arcpy.GetParameterAsText(5)  # Image acquisition date (text)

# Validate image acquisition date format (optional but recommended)
def validate_date_format(date_string):
    """Validate date format and return standardized format"""
    try:
        if not date_string.strip():
            return datetime.now().strftime("%Y-%m-%d")
        
        # Try different date formats
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y%m%d"):
            try:
                parsed_date = datetime.strptime(date_string.strip(), fmt)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # If no format matches, return as-is with warning
        arcpy.AddWarning(f"Date format not recognized: {date_string}. Using as provided.")
        return date_string.strip()
    except:
        return datetime.now().strftime("%Y-%m-%d")

# Validate and format the acquisition date
acquisition_date = validate_date_format(Image_Acquisition_Date)

# Define output variables with dynamic naming
year_suffix = acquisition_date.replace("-", "_")
ParcelZoning = os.path.join(Output_Geodatabase, "ParcelZoning_Temp")
ParcelZoning_Final = os.path.join(Output_Geodatabase, f"ParcelZoning_Final_{year_suffix}")
New_Constructions = os.path.join(Output_Geodatabase, f"New_Constructions_{year_suffix}")
Parcel_Zoning_Statistics = os.path.join(Output_Geodatabase, "ParcelZoning_Statistics_Temp")
Construction_Statistics = os.path.join(Output_Geodatabase, "Construction_Statistics_Temp")
New_Houses = os.path.join(Output_Geodatabase, f"New_Houses_{year_suffix}")

def cleanup_temp_data():
    """Clean up temporary datasets"""
    temp_datasets = [
        ParcelZoning,
        Parcel_Zoning_Statistics,
        Construction_Statistics,
        "ParcelZoning_Layer",
        "New_Constructions_Layer",
        "New_Houses_Layer"
    ]
    
    for dataset in temp_datasets:
        try:
            if arcpy.Exists(dataset):
                arcpy.management.Delete(dataset)
        except:
            pass

def validate_inputs():
    """Validate all input parameters"""
    arcpy.AddMessage("Validating input parameters...")
    
    if not arcpy.Exists(Parcels_Name):
        arcpy.AddError(f"Input parcels layer does not exist: {Parcels_Name}")
        return False
    
    if not arcpy.Exists(Zoning_Layer):
        arcpy.AddError(f"Input zoning layer does not exist: {Zoning_Layer}")
        return False
    
    if not arcpy.Exists(Detected_Constructions):
        arcpy.AddError(f"Input detected constructions layer does not exist: {Detected_Constructions}")
        return False
    
    if not arcpy.Exists(BPMIS_Data):
        arcpy.AddError(f"Input BPMIS data does not exist: {BPMIS_Data}")
        return False
    
    if not arcpy.Exists(Output_Geodatabase):
        arcpy.AddError(f"Output geodatabase does not exist: {Output_Geodatabase}")
        return False
    
    # Check if required fields exist
    parcel_fields = [f.name.lower() for f in arcpy.ListFields(Parcels_Name)]
    if 'upi' not in parcel_fields:
        arcpy.AddError("'upi' field not found in parcels layer")
        return False
    
    bpmis_fields = [f.name.lower() for f in arcpy.ListFields(BPMIS_Data)]
    if 'plot_no' not in bpmis_fields:
        arcpy.AddError("'Plot_No' field not found in BPMIS data")
        return False
    
    arcpy.AddMessage("Input validation completed successfully.")
    return True

def get_dominant_area_features(input_layer, group_field, temp_stats_table):
    """
    Get features with dominant (maximum) area for each group
    Returns the feature class with only dominant area features
    """
    arcpy.AddMessage(f"Calculating dominant areas for {input_layer}...")
    
    # Calculate statistics to find maximum area for each group
    arcpy.analysis.Statistics(
        in_table=input_layer,
        out_table=temp_stats_table,
        statistics_fields="Shape_Area MAX",
        case_field=group_field
    )
    
    # Join the statistics back to the original layer
    arcpy.management.JoinField(
        in_data=input_layer,
        in_field=group_field,
        join_table=temp_stats_table,
        join_field=group_field,
        fields="MAX_Shape_Area"
    )
    
    # Create a feature layer and select features with maximum area
    layer_name = f"{os.path.basename(input_layer)}_Layer"
    arcpy.management.MakeFeatureLayer(input_layer, layer_name)
    
    # Select features where Shape_Area equals MAX_Shape_Area (dominant area)
    where_clause = "Shape_Area >= MAX_Shape_Area"
    arcpy.management.SelectLayerByAttribute(layer_name, "NEW_SELECTION", where_clause)
    
    selected_count = int(arcpy.management.GetCount(layer_name)[0])
    arcpy.AddMessage(f"Selected {selected_count} features with dominant area.")
    
    if selected_count == 0:
        arcpy.AddError(f"No features selected with dominant area criteria for {input_layer}")
        return None, layer_name
    
    return selected_count, layer_name

try:
    # Validate inputs first
    if not validate_inputs():
        sys.exit("Input validation failed")
    
    arcpy.AddMessage(f"Starting construction analysis for acquisition date: {acquisition_date}")
    
    ##############################################################################
    # PART A: Process Parcels & Zoning - Get Dominant Zoning per Parcel
    ##############################################################################
    arcpy.AddMessage("=" * 60)
    arcpy.AddMessage("PART A: Processing Parcels and Zoning Intersection")
    arcpy.AddMessage("=" * 60)
    
    # Intersect parcels with zoning
    arcpy.AddMessage("Performing intersection between Parcels and Zoning...")
    arcpy.analysis.Intersect(
        in_features=[Parcels_Name, Zoning_Layer],
        out_feature_class=ParcelZoning,
        join_attributes="ALL",
        cluster_tolerance="",
        output_type="INPUT"
    )
    arcpy.AddMessage("Intersection completed successfully.")
    
    # Get features with dominant area (one zoning per parcel)
    parcel_desc = arcpy.Describe(Parcels_Name)
    parcel_oid_field = f"FID_{parcel_desc.baseName}" if parcel_desc.baseName else "FID_Parcels"
    
    selected_count, parcel_layer = get_dominant_area_features(
        ParcelZoning, 
        parcel_oid_field, 
        Parcel_Zoning_Statistics
    )
    
    if selected_count is None:
        raise Exception("Failed to identify dominant zoning areas for parcels")
    
    # Export the dominant zoning parcels
    arcpy.conversion.ExportFeatures(parcel_layer, ParcelZoning_Final)
    arcpy.AddMessage(f"Exported {selected_count} parcels with dominant zoning to {ParcelZoning_Final}")
    
    ##############################################################################
    # PART B: Process New Constructions - Get Dominant Parcel per Construction
    ##############################################################################
    arcpy.AddMessage("=" * 60)
    arcpy.AddMessage("PART B: Processing New Constructions")
    arcpy.AddMessage("=" * 60)
    
    # Intersect detected constructions with final parcel-zoning data
    arcpy.AddMessage("Intersecting detected constructions with parcel-zoning data...")
    arcpy.analysis.Intersect(
        in_features=[Detected_Constructions, ParcelZoning_Final],
        out_feature_class=New_Constructions,
        join_attributes="ALL",
        cluster_tolerance="",
        output_type="INPUT"
    )
    arcpy.AddMessage("Construction-parcel intersection completed.")
    
    # Get constructions with dominant parcel area
    construction_desc = arcpy.Describe(Detected_Constructions)
    construction_oid_field = f"FID_{construction_desc.baseName}" if construction_desc.baseName else "FID_Detected_Constructions"
    
    selected_count, construction_layer = get_dominant_area_features(
        New_Constructions,
        construction_oid_field,
        Construction_Statistics
    )
    
    if selected_count is None:
        raise Exception("Failed to identify dominant parcel areas for constructions")
    
    # Export the final constructions with dominant parcel assignment
    arcpy.conversion.ExportFeatures(construction_layer, New_Houses)
    arcpy.AddMessage(f"Exported {selected_count} constructions with dominant parcel assignment to {New_Houses}")
    
    ##############################################################################
    # PART C: Add and Configure Fields
    ##############################################################################
    arcpy.AddMessage("=" * 60)
    arcpy.AddMessage("PART C: Adding and Configuring Fields")
    arcpy.AddMessage("=" * 60)
    
    # Define fields to add - keeping original field names
    fields_to_add = [
        {
            "field_name": "status_t", 
            "field_type": "TEXT", 
            "field_length": 250, 
            "field_alias": "Status",
            "default_value": "New House"
        },
        {
            "field_name": "year_t", 
            "field_type": "TEXT", 
            "field_length": 50, 
            "field_alias": "Year",
            "default_value": acquisition_date
        },
        {
            "field_name": "legal_t", 
            "field_type": "TEXT", 
            "field_length": 250, 
            "field_alias": "Legality Status",
            "default_value": "Unknown"
        }
    ]
    
    # Add fields
    for field in fields_to_add:
        try:
            arcpy.management.AddField(
                in_table=New_Houses,
                field_name=field["field_name"],
                field_type=field["field_type"],
                field_precision="",
                field_scale="",
                field_length=field.get("field_length", ""),
                field_alias=field["field_alias"]
            )
            arcpy.AddMessage(f"Added field: {field['field_name']}")
        except Exception as e:
            if "already exists" in str(e).lower():
                arcpy.AddWarning(f"Field {field['field_name']} already exists, skipping...")
            else:
                raise e
    
    ##############################################################################
    # PART D: Join with BPMIS Data
    ##############################################################################
    arcpy.AddMessage("=" * 60)
    arcpy.AddMessage("PART D: Joining with BPMIS Data")
    arcpy.AddMessage("=" * 60)
    
    # Get BPMIS fields (exclude system fields)
    bpmis_fields = [f.name for f in arcpy.ListFields(BPMIS_Data) 
                    if f.type not in ('OID', 'Geometry') and 
                    f.name.lower() not in ('shape', 'shape_length', 'shape_area', 'objectid')]
    
    # Ensure Plot_No is in the join fields
    if "Plot_No" not in bpmis_fields:
        bpmis_fields.append("Plot_No")
    
    arcpy.AddMessage(f"Joining BPMIS fields: {', '.join(bpmis_fields)}")
    
    # Perform the join
    arcpy.management.JoinField(
        in_data=New_Houses,
        in_field="upi",
        join_table=BPMIS_Data,
        join_field="Plot_No",
        fields=bpmis_fields
    )
    arcpy.AddMessage("BPMIS data join completed.")
    
    ##############################################################################
    # PART E: Calculate Legal Status and Populate Fields
    ##############################################################################
    arcpy.AddMessage("=" * 60)
    arcpy.AddMessage("PART E: Calculating Legal Status and Populating Fields")
    arcpy.AddMessage("=" * 60)
    
    # Create feature layer for calculations
    arcpy.management.MakeFeatureLayer(New_Houses, "New_Houses_Layer")
    
    # Calculate legal status based on Plot_No availability
    arcpy.AddMessage("Calculating legal status...")
    
    # Mark as Legal where Plot_No is NOT NULL
    legal_where_clause = "Plot_No IS NOT NULL"
    arcpy.management.SelectLayerByAttribute("New_Houses_Layer", "NEW_SELECTION", legal_where_clause)
    legal_count = int(arcpy.management.GetCount("New_Houses_Layer")[0])
    if legal_count > 0:
        arcpy.management.CalculateField(
            "New_Houses_Layer", 
            "legal_t", 
            "'Legal'", 
            "PYTHON3"
        )
        arcpy.AddMessage(f"Marked {legal_count} constructions as Legal")
    
    # Mark as Illegal where Plot_No IS NULL
    illegal_where_clause = "Plot_No IS NULL"
    arcpy.management.SelectLayerByAttribute("New_Houses_Layer", "NEW_SELECTION", illegal_where_clause)
    illegal_count = int(arcpy.management.GetCount("New_Houses_Layer")[0])
    if illegal_count > 0:
        arcpy.management.CalculateField(
            "New_Houses_Layer", 
            "legal_t", 
            "'Illegal'", 
            "PYTHON3"
        )
        arcpy.AddMessage(f"Marked {illegal_count} constructions as Illegal")
    
    # Clear selection and populate other fields
    arcpy.management.SelectLayerByAttribute("New_Houses_Layer", "CLEAR_SELECTION")
    
    # Populate status field
    arcpy.management.CalculateField(
        "New_Houses_Layer", 
        "status_t", 
        "'New House'", 
        "PYTHON3"
    )
    
    # Populate year field with acquisition date
    arcpy.management.CalculateField(
        "New_Houses_Layer", 
        "year_t", 
        f"'{acquisition_date}'", 
        "PYTHON3"
    )
    
    ##############################################################################
    # PART F: Final Summary and Cleanup
    ##############################################################################
    arcpy.AddMessage("=" * 60)
    arcpy.AddMessage("PART F: Final Summary")
    arcpy.AddMessage("=" * 60)
    
    # Get final counts
    total_constructions = int(arcpy.management.GetCount(New_Houses)[0])
    
    arcpy.AddMessage(f"Analysis completed successfully!")
    arcpy.AddMessage(f"Total constructions processed: {total_constructions}")
    arcpy.AddMessage(f"Legal constructions: {legal_count}")
    arcpy.AddMessage(f"Illegal constructions: {illegal_count}")
    arcpy.AddMessage(f"Image acquisition date: {acquisition_date}")
    arcpy.AddMessage(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    arcpy.AddMessage(f"Output feature class: {New_Houses}")
    
    # Clean up temporary data
    cleanup_temp_data()
    arcpy.AddMessage("Temporary data cleaned up successfully.")
    
except Exception as e:
    arcpy.AddError(f"An error occurred: {str(e)}")
    # Clean up on error
    cleanup_temp_data()
    sys.exit(f"Script failed with error: {str(e)}")

finally:
    # Final cleanup attempt
    try:
        cleanup_temp_data()
    except:
        pass
