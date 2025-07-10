import arcpy
import os

class ConstructionAnalysisTool:
    """
    ArcGIS Pro Geoprocessing Tool for Construction Analysis
    Analyzes parcels, zoning, and detected constructions to identify legal/illegal buildings
    """
    
    def __init__(self):
        self.label = "Construction Analysis Tool"
        self.description = "Analyzes parcels, zoning, and detected constructions to identify legal/illegal buildings"
        self.category = "Construction Analysis"
        self.canRunInBackground = True
        
    def getParameterInfo(self):
        """Define the tool parameters"""
        
        # Parameter 0: Parcels Layer
        param0 = arcpy.Parameter(
            displayName="Parcels Layer",
            name="parcels_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        param0.filter.list = ["Polygon"]
        
        # Parameter 1: Zoning Layer
        param1 = arcpy.Parameter(
            displayName="Zoning Layer",
            name="zoning_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        param1.filter.list = ["Polygon"]
        
        # Parameter 2: Detected Constructions
        param2 = arcpy.Parameter(
            displayName="Detected Constructions",
            name="detected_constructions",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        param2.filter.list = ["Polygon"]
        
        # Parameter 3: BPMIS Data
        param3 = arcpy.Parameter(
            displayName="BPMIS Data",
            name="bpmis_data",
            datatype="GPTableView",
            parameterType="Required",
            direction="Input"
        )
        
        # Parameter 4: Output Geodatabase
        param4 = arcpy.Parameter(
            displayName="Output Geodatabase",
            name="output_geodatabase",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input"
        )
        param4.filter.list = ["Local Database"]
        
        # Parameter 5: Analysis Year
        param5 = arcpy.Parameter(
            displayName="Analysis Year",
            name="analysis_year",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        param5.value = 2025
        
        # Parameter 6: Final Output Name
        param6 = arcpy.Parameter(
            displayName="Final Output Name",
            name="final_output_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param6.value = "CoK_Constructions"
        
        # Parameter 7: Output Feature Class (derived)
        param7 = arcpy.Parameter(
            displayName="Output Feature Class",
            name="output_feature_class",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output"
        )
        
        return [param0, param1, param2, param3, param4, param5, param6, param7]
    
    def isLicensed(self):
        """Set whether tool is licensed to execute"""
        return True
    
    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal validation"""
        # Update the derived output parameter
        if parameters[4].altered and parameters[6].altered:
            if parameters[4].valueAsText and parameters[6].valueAsText:
                output_gdb = parameters[4].valueAsText
                output_name = parameters[6].valueAsText
                parameters[7].value = os.path.join(output_gdb, output_name)
        return
    
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation"""
        # Validate output name
        if parameters[6].value:
            output_name = parameters[6].valueAsText
            if not output_name.replace("_", "").isalnum():
                parameters[6].setErrorMessage("Output name must contain only letters, numbers, and underscores")
        return
    
    def execute(self, parameters, messages):
        """Execute the tool"""
        try:
            # Get input parameters
            parcels_layer = parameters[0].valueAsText
            zoning_layer = parameters[1].valueAsText
            detected_constructions = parameters[2].valueAsText
            bpmis_data = parameters[3].valueAsText
            output_geodatabase = parameters[4].valueAsText
            analysis_year = parameters[5].value
            final_output_name = parameters[6].valueAsText
            
            # Define intermediate output variables
            parcel_zoning = os.path.join(output_geodatabase, "ParcelZoning")
            parcel_zoning_final = os.path.join(output_geodatabase, "ParcelZoning_Final")
            new_constructions = os.path.join(output_geodatabase, f"New_Constructions_{analysis_year}")
            parcel_zoning_statistics = os.path.join(output_geodatabase, "ParcelZoning_Statistics")
            summary_houses = os.path.join(output_geodatabase, "Summary_Houses")
            final_output = os.path.join(output_geodatabase, final_output_name)
            
            # Set derived output parameter
            parameters[7].value = final_output
            
            arcpy.AddMessage(f"Starting Construction Analysis for year {analysis_year}")
            arcpy.AddMessage(f"Final output will be saved as: {final_output}")
            
            ##############################################################################
            # PART A: Process Parcels & Zoning to create filtered parcels
            ##############################################################################
            arcpy.AddMessage("=" * 60)
            arcpy.AddMessage("PART A: Processing Parcels and Zoning")
            arcpy.AddMessage("=" * 60)
            
            arcpy.AddMessage("Starting intersection between Parcels and Zoning...")
            arcpy.analysis.Intersect(
                in_features=[parcels_layer, zoning_layer],
                out_feature_class=parcel_zoning,
                join_attributes="ALL"
            )
            arcpy.AddMessage("✓ Intersection completed successfully.")
            
            arcpy.AddMessage("Calculating summary statistics on ParcelZoning...")
            arcpy.analysis.Statistics(
                in_table=parcel_zoning,
                out_table=parcel_zoning_statistics,
                statistics_fields="Shape_Area MAX",
                case_field="FID_Parcels"
            )
            arcpy.AddMessage("✓ Summary statistics calculation completed.")
            
            arcpy.AddMessage("Joining summary table with ParcelZoning...")
            arcpy.management.JoinField(
                in_data=parcel_zoning,
                in_field="FID_Parcels",
                join_table=parcel_zoning_statistics,
                join_field="FID_Parcels",
                fields="MAX_Shape_Area"
            )
            arcpy.AddMessage("✓ Join operation completed.")
            
            arcpy.AddMessage("Selecting parcels where Shape_Area >= MAX_Shape_Area...")
            arcpy.management.MakeFeatureLayer(parcel_zoning, "ParcelZoning_Layer")
            oid_field = arcpy.Describe("ParcelZoning_Layer").OIDFieldName
            selected_oids = []
            
            with arcpy.da.SearchCursor("ParcelZoning_Layer", [oid_field, "Shape_Area", "MAX_Shape_Area"]) as cursor:
                for oid, shape_area, max_shape_area in cursor:
                    if shape_area >= max_shape_area:
                        selected_oids.append(oid)
            
            if selected_oids:
                oid_list_str = ",".join(map(str, selected_oids))
                query = f"{oid_field} IN ({oid_list_str})"
                arcpy.management.SelectLayerByAttribute("ParcelZoning_Layer", "NEW_SELECTION", query)
                selected_count = int(arcpy.management.GetCount("ParcelZoning_Layer")[0])
                arcpy.AddMessage(f"✓ Selected {selected_count} parcels with representative geometry.")
                
                arcpy.conversion.ExportFeatures("ParcelZoning_Layer", parcel_zoning_final)
                arcpy.AddMessage("✓ Exported selected parcels to ParcelZoning_Final.")
            else:
                arcpy.AddError("No parcels found where Shape_Area >= MAX_Shape_Area. Please check your data.")
                return
            
            ##############################################################################
            # PART B: Process New Constructions
            ##############################################################################
            arcpy.AddMessage("=" * 60)
            arcpy.AddMessage("PART B: Processing New Constructions")
            arcpy.AddMessage("=" * 60)
            
            arcpy.AddMessage("Intersecting new detected constructions with ParcelZoning_Final...")
            arcpy.analysis.Intersect(
                in_features=[detected_constructions, parcel_zoning_final],
                out_feature_class=new_constructions,
                join_attributes="ALL"
            )
            arcpy.AddMessage("✓ Intersection of detected constructions completed.")
            
            arcpy.AddMessage("Calculating summary statistics for new constructions...")
            arcpy.analysis.Statistics(
                in_table=new_constructions,
                out_table=summary_houses,
                statistics_fields="Shape_Area MAX",
                case_field="FID_Detected_Constructions"
            )
            arcpy.AddMessage("✓ Summary statistics for new constructions completed.")
            
            arcpy.AddMessage("Joining summary statistics with New_Constructions...")
            arcpy.management.JoinField(
                in_data=new_constructions,
                in_field="FID_Detected_Constructions",
                join_table=summary_houses,
                join_field="FID_Detected_Constructions",
                fields="MAX_Shape_Area"
            )
            arcpy.AddMessage("✓ Join operation for new constructions completed.")
            
            arcpy.AddMessage("Creating a feature layer for new constructions...")
            arcpy.management.MakeFeatureLayer(new_constructions, "New_Constructions_layer")
            
            arcpy.AddMessage("Selecting new constructions where Shape_Area >= Max_Shape_Area_1...")
            selection_query = "Shape_Area >= Max_Shape_Area_1"
            arcpy.management.SelectLayerByAttribute("New_Constructions_layer", "NEW_SELECTION", selection_query)
            selected_count = int(arcpy.management.GetCount("New_Constructions_layer")[0])
            arcpy.AddMessage(f"✓ Selected {selected_count} features based on area criteria.")
            
            if selected_count == 0:
                arcpy.AddWarning("No features selected with the condition. Verify the field names and attribute values.")
                return
            
            arcpy.AddMessage(f"Exporting selected features to {final_output_name}...")
            arcpy.conversion.ExportFeatures("New_Constructions_layer", final_output)
            arcpy.AddMessage(f"✓ {final_output_name} exported successfully.")
            
            ##############################################################################
            # PART C: Add and Calculate Fields
            ##############################################################################
            arcpy.AddMessage("=" * 60)
            arcpy.AddMessage("PART C: Adding and Calculating Fields")
            arcpy.AddMessage("=" * 60)
            
            arcpy.AddMessage(f"Adding fields legal_t, status_t, and year_t to {final_output_name}...")
            fields_to_add = [
                {"field_name": "status_t", "field_type": "TEXT", "field_length": 250, "field_alias": "Status"},
                {"field_name": "year_t", "field_type": "LONG", "field_length": 10, "field_alias": "Year"},
                {"field_name": "legal_t", "field_type": "TEXT", "field_length": 250, "field_alias": "Legality Status"},
            ]
            
            for field in fields_to_add:
                arcpy.management.AddField(
                    in_table=final_output,
                    field_name=field["field_name"],
                    field_type=field["field_type"],
                    field_precision="",
                    field_scale="",
                    field_length=field["field_length"],
                    field_alias=field["field_alias"]
                )
                arcpy.AddMessage(f"✓ Field {field['field_name']} added successfully.")
            
            ##############################################################################
            # PART D: Permanently Join All BPMIS Data
            ##############################################################################
            arcpy.AddMessage("=" * 60)
            arcpy.AddMessage("PART D: Joining BPMIS Data")
            arcpy.AddMessage("=" * 60)
            
            arcpy.AddMessage("Performing permanent join with BPMIS Data...")
            bpmis_fields = [f.name for f in arcpy.ListFields(bpmis_data) 
                            if f.type not in ('OID', 'Geometry') and f.name != 'Shape']
            
            if "Plot_No" not in bpmis_fields:
                bpmis_fields.append("Plot_No")
            
            arcpy.management.JoinField(
                in_data=final_output,
                in_field="upi",
                join_table=bpmis_data,
                join_field="Plot_No",
                fields=bpmis_fields
            )
            arcpy.AddMessage(f"✓ Permanent join with BPMIS Data completed. Joined fields: {', '.join(bpmis_fields)}")
            
            field_list = [f.name for f in arcpy.ListFields(final_output)]
            if "Plot_No" not in field_list:
                arcpy.AddWarning("Plot_No field not found in final output - join may have failed.")
            else:
                arcpy.AddMessage("✓ Plot_No field successfully included in output.")
            
            ##############################################################################
            # PART E: Flag Houses as Legal/Illegal and Populate Fields
            ##############################################################################
            arcpy.AddMessage("=" * 60)
            arcpy.AddMessage("PART E: Flagging Legal/Illegal Status and Populating Fields")
            arcpy.AddMessage("=" * 60)
            
            arcpy.management.MakeFeatureLayer(final_output, "Final_Output_layer")
            
            # Flag houses as Illegal where Plot_No is NULL
            arcpy.AddMessage("Marking houses as Illegal where Plot_No is NULL...")
            where_clause_illegal = '"Plot_No" IS NULL'
            arcpy.management.SelectLayerByAttribute("Final_Output_layer", "NEW_SELECTION", where_clause_illegal)
            illegal_count = int(arcpy.management.GetCount("Final_Output_layer")[0])
            if illegal_count > 0:
                arcpy.management.CalculateField("Final_Output_layer", "legal_t", expression='"Illegal"', expression_type="PYTHON3")
                arcpy.AddMessage(f"✓ {illegal_count} houses marked as Illegal.")
            
            # Flag houses as Legal where Plot_No is NOT NULL
            arcpy.AddMessage("Marking houses as Legal where Plot_No is NOT NULL...")
            where_clause_legal = '"Plot_No" IS NOT NULL'
            arcpy.management.SelectLayerByAttribute("Final_Output_layer", "NEW_SELECTION", where_clause_legal)
            legal_count = int(arcpy.management.GetCount("Final_Output_layer")[0])
            if legal_count > 0:
                arcpy.management.CalculateField("Final_Output_layer", "legal_t", expression='"Legal"', expression_type="PYTHON3")
                arcpy.AddMessage(f"✓ {legal_count} houses marked as Legal.")
            
            # Clear selection and populate remaining fields
            arcpy.management.SelectLayerByAttribute("Final_Output_layer", "CLEAR_SELECTION")
            
            arcpy.AddMessage(f"Populating year_t field with {analysis_year}...")
            arcpy.management.CalculateField("Final_Output_layer", "year_t", expression=str(analysis_year), expression_type="PYTHON3")
            arcpy.AddMessage("✓ Year field populated successfully.")
            
            arcpy.AddMessage("Calculating default status_t field value...")
            arcpy.management.CalculateField("Final_Output_layer", "status_t", expression='"New House"', expression_type="PYTHON3")
            arcpy.AddMessage("✓ Status field updated successfully.")
            
            # Final summary
            total_count = int(arcpy.management.GetCount(final_output)[0])
            arcpy.AddMessage("=" * 60)
            arcpy.AddMessage("ANALYSIS COMPLETE!")
            arcpy.AddMessage("=" * 60)
            arcpy.AddMessage(f"Final Output: {final_output}")
            arcpy.AddMessage(f"Total Constructions Analyzed: {total_count}")
            arcpy.AddMessage(f"Legal Constructions: {legal_count}")
            arcpy.AddMessage(f"Illegal Constructions: {illegal_count}")
            arcpy.AddMessage(f"Analysis Year: {analysis_year}")
            arcpy.AddMessage("=" * 60)
            
        except Exception as e:
            arcpy.AddError(f"An error occurred during execution: {str(e)}")
            raise e


class Toolbox:
    """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
    
    def __init__(self):
        self.label = "Construction Analysis Toolbox"
        self.alias = "ConstructionAnalysis"
        self.description = "Tools for analyzing construction legality and zoning compliance"
        
        # List of tool classes associated with this toolbox
        self.tools = [ConstructionAnalysisTool]