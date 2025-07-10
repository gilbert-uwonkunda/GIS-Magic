import arcpy
import os


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Building Construction Analysis"
        self.alias = "BuildingAnalysis"
        
        # List of tool classes associated with this toolbox
        self.tools = [BuildingConstructionAnalysisTool]


class BuildingConstructionAnalysisTool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Building Construction Analysis"
        self.description = "Analyze detected constructions against existing buildings and export results"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        # Input detected constructions layer
        param_detected = arcpy.Parameter(
            displayName="Detected Constructions Layer",
            name="detected_constructions",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        param_detected.filter.list = ["Polygon"]
        
        # Input existing buildings layer
        param_buildings = arcpy.Parameter(
            displayName="Existing Buildings Layer", 
            name="existing_buildings",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        param_buildings.filter.list = ["Polygon"]
        
        # Output geodatabase
        param_output_gdb = arcpy.Parameter(
            displayName="Output Geodatabase",
            name="output_geodatabase",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input"
        )
        param_output_gdb.filter.list = ["Local Database"]
        
        # Output coordinate system
        param_coord_sys = arcpy.Parameter(
            displayName="Output Coordinate System",
            name="output_coordinate_system",
            datatype="GPCoordinateSystem",
            parameterType="Optional",
            direction="Input"
        )
        # Set default to WGS 1984 UTM Zone 36S
        param_coord_sys.value = 'PROJCS["WGS_1984_UTM_Zone_36S",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",10000000.0],PARAMETER["Central_Meridian",33.0],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'
        
        # Export detected constructions
        param_export_constructions = arcpy.Parameter(
            displayName="Export Detected Constructions",
            name="export_constructions",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        param_export_constructions.value = True
        
        # Export demolished buildings
        param_export_buildings = arcpy.Parameter(
            displayName="Export Demolished Buildings",
            name="export_buildings", 
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        param_export_buildings.value = True
        
        # Output feature class name for constructions
        param_output_constructions = arcpy.Parameter(
            displayName="Output Constructions Feature Class Name",
            name="output_constructions_name",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        param_output_constructions.value = "Detected_Constructions"
        
        # Output feature class name for buildings
        param_output_buildings = arcpy.Parameter(
            displayName="Output Buildings Feature Class Name",
            name="output_buildings_name",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        param_output_buildings.value = "Demolished"
        
        parameters = [
            param_detected,
            param_buildings,
            param_output_gdb,
            param_coord_sys,
            param_export_constructions,
            param_export_buildings,
            param_output_constructions,
            param_output_buildings
        ]
        
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        
        # Enable/disable output name parameters based on export checkboxes
        if parameters[4].value:  # export_constructions
            parameters[6].enabled = True
        else:
            parameters[6].enabled = False
            
        if parameters[5].value:  # export_buildings
            parameters[7].enabled = True
        else:
            parameters[7].enabled = False
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        
        # Validate output geodatabase exists
        if parameters[2].value:
            if not arcpy.Exists(parameters[2].valueAsText):
                parameters[2].setErrorMessage("Output geodatabase does not exist")
        
        # Validate output feature class names
        if parameters[4].value and parameters[6].value:
            if not parameters[6].valueAsText.replace(" ", "_").isalnum():
                parameters[6].setWarningMessage("Feature class name should contain only alphanumeric characters and underscores")
                
        if parameters[5].value and parameters[7].value:
            if not parameters[7].valueAsText.replace(" ", "_").isalnum():
                parameters[7].setWarningMessage("Feature class name should contain only alphanumeric characters and underscores")
        
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        
        # Get parameter values
        detected_constructions = parameters[0].valueAsText
        existing_buildings = parameters[1].valueAsText
        output_gdb = parameters[2].valueAsText
        output_coord_sys = parameters[3].value
        export_constructions = parameters[4].value
        export_buildings = parameters[5].value
        output_constructions_name = parameters[6].valueAsText
        output_buildings_name = parameters[7].valueAsText
        
        try:
            # Set up environment
            arcpy.env.overwriteOutput = True
            if output_coord_sys:
                arcpy.env.outputCoordinateSystem = output_coord_sys
            
            messages.addMessage("Starting building construction analysis...")
            
            # Create feature layers if inputs are feature classes
            if arcpy.Describe(detected_constructions).datasetType == "FeatureClass":
                arcpy.management.MakeFeatureLayer(detected_constructions, "detected_constructions_lyr")
                detected_constructions = "detected_constructions_lyr"
            
            if arcpy.Describe(existing_buildings).datasetType == "FeatureClass":
                arcpy.management.MakeFeatureLayer(existing_buildings, "existing_buildings_lyr")
                existing_buildings = "existing_buildings_lyr"
            
            # Step 1: Select constructions that do NOT intersect with existing buildings
            messages.addMessage("Selecting new constructions that do not intersect with existing buildings...")
            arcpy.management.SelectLayerByLocation(
                in_layer=detected_constructions,
                overlap_type="INTERSECT",
                select_features=existing_buildings,
                search_distance=None,
                selection_type="NEW_SELECTION",
                invert_spatial_relationship="INVERT"
            )
            
            # Get count of selected constructions
            construction_count = int(arcpy.management.GetCount(detected_constructions).getOutput(0))
            messages.addMessage(f"Found {construction_count} new constructions that do not intersect with existing buildings")
            
            # Step 2: Export detected constructions if requested
            if export_constructions and construction_count > 0:
                output_constructions_path = os.path.join(output_gdb, output_constructions_name.replace(" ", "_"))
                messages.addMessage(f"Exporting detected constructions to {output_constructions_path}...")
                
                # Build field mapping for constructions
                field_mappings = arcpy.FieldMappings()
                field_mappings.addTable(detected_constructions)
                
                arcpy.conversion.ExportFeatures(
                    in_features=detected_constructions,
                    out_features=output_constructions_path,
                    where_clause="",
                    use_field_alias_as_name="NOT_USE_ALIAS",
                    field_mapping=field_mappings
                )
                messages.addMessage(f"Successfully exported {construction_count} detected construction features")
            
            # Step 3: Select buildings that do NOT intersect with detected constructions (demolished buildings)
            messages.addMessage("Selecting buildings that do not intersect with detected constructions (demolished buildings)...")
            arcpy.management.SelectLayerByLocation(
                in_layer=existing_buildings,
                overlap_type="INTERSECT", 
                select_features=detected_constructions,
                search_distance=None,
                selection_type="NEW_SELECTION",
                invert_spatial_relationship="INVERT"
            )
            
            # Get count of selected buildings
            building_count = int(arcpy.management.GetCount(existing_buildings).getOutput(0))
            messages.addMessage(f"Found {building_count} buildings that do not intersect with detected constructions (potentially demolished)")
            
            # Step 4: Export demolished buildings if requested
            if export_buildings and building_count > 0:
                output_buildings_path = os.path.join(output_gdb, output_buildings_name.replace(" ", "_"))
                messages.addMessage(f"Exporting demolished buildings to {output_buildings_path}...")
                
                # Build field mapping for buildings
                field_mappings = arcpy.FieldMappings()
                field_mappings.addTable(existing_buildings)
                
                arcpy.conversion.ExportFeatures(
                    in_features=existing_buildings,
                    out_features=output_buildings_path,
                    where_clause="",
                    use_field_alias_as_name="NOT_USE_ALIAS",
                    field_mapping=field_mappings
                )
                messages.addMessage(f"Successfully exported {building_count} demolished building features")
            
            # Clear selections
            arcpy.management.SelectLayerByAttribute(detected_constructions, "CLEAR_SELECTION")
            arcpy.management.SelectLayerByAttribute(existing_buildings, "CLEAR_SELECTION")
            
            messages.addMessage("Analysis completed successfully!")
            messages.addMessage(f"Summary:")
            messages.addMessage(f"  - New constructions detected: {construction_count}")
            messages.addMessage(f"  - Buildings potentially demolished: {building_count}")
            
        except Exception as e:
            messages.addErrorMessage(f"Error during analysis: {str(e)}")
            raise
            
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return