import arcpy
import os

class DeepLearningDetectionTool:
    """
    ArcGIS Pro Geoprocessing Tool for Deep Learning Object Detection
    Simplified version with only 3 visible parameters
    """
    
    def __init__(self):
        self.label = "Deep Learning Object Detection"
        self.description = "Detects objects in raster imagery using deep learning models"
        self.category = "Deep Learning"
        self.canRunInBackground = True
        
    def getParameterInfo(self):
        """Define the tool parameters"""
        
        # Parameter 0: Input Raster (VISIBLE)
        param0 = arcpy.Parameter(
            displayName="Input Raster",
            name="in_raster",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input"
        )
        
        # Parameter 1: Deep Learning Model (VISIBLE)
        param1 = arcpy.Parameter(
            displayName="Deep Learning Model (.dlpk)",
            name="in_model_definition",
            datatype="DEFile",
            parameterType="Required",
            direction="Input"
        )
        param1.filter.list = ['dlpk']
        
        # Parameter 2: Output Detected Objects (VISIBLE)
        param2 = arcpy.Parameter(
            displayName="Output Detected Objects",
            name="out_detected_objects",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output"
        )
        
        # Parameter 3: Confidence Threshold (HIDDEN)
        param3 = arcpy.Parameter(
            displayName="Confidence Threshold",
            name="confidence_threshold",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        param3.value = 0.1
        param3.category = "Advanced Settings"
        
        # Parameter 4: Tile Size (HIDDEN)
        param4 = arcpy.Parameter(
            displayName="Tile Size",
            name="tile_size",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )
        param4.value = 256
        param4.category = "Advanced Settings"
        
        # Parameter 5: Batch Size (HIDDEN)
        param5 = arcpy.Parameter(
            displayName="Batch Size",
            name="batch_size",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )
        param5.value = 2
        param5.category = "Advanced Settings"
        
        # Parameter 6: Padding (HIDDEN)
        param6 = arcpy.Parameter(
            displayName="Padding",
            name="padding",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )
        param6.value = 64
        param6.category = "Advanced Settings"
        
        # Parameter 7: Max Overlap Ratio (HIDDEN)
        param7 = arcpy.Parameter(
            displayName="Max Overlap Ratio",
            name="max_overlap_ratio",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        param7.value = 0.0
        param7.category = "Advanced Settings"
        
        # Parameter 8: Return Bounding Boxes (HIDDEN)
        param8 = arcpy.Parameter(
            displayName="Return Bounding Boxes",
            name="return_bboxes",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        param8.value = False
        param8.category = "Advanced Settings"
        
        # Parameter 9: Test Time Augmentation (HIDDEN)
        param9 = arcpy.Parameter(
            displayName="Test Time Augmentation",
            name="test_time_augmentation",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        param9.value = False
        param9.category = "Advanced Settings"
        
        # Parameter 10: Merge Policy (HIDDEN)
        param10 = arcpy.Parameter(
            displayName="Merge Policy",
            name="merge_policy",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        param10.filter.type = "ValueList"
        param10.filter.list = ["max", "mean", "min"]
        param10.value = "max"
        param10.category = "Advanced Settings"
        
        # Parameter 11: Use GPU Processing (HIDDEN)
        param11 = arcpy.Parameter(
            displayName="Use GPU Processing",
            name="use_gpu",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        param11.value = True
        param11.category = "Advanced Settings"
        
        # Parameter 12: Output Coordinate System (HIDDEN)
        param12 = arcpy.Parameter(
            displayName="Output Coordinate System",
            name="output_coordinate_system",
            datatype="GPCoordinateSystem",
            parameterType="Optional",
            direction="Input"
        )
        # Set default to WGS 1984 UTM Zone 36S
        param12.value = 'PROJCS["WGS_1984_UTM_Zone_36S",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",10000000.0],PARAMETER["Central_Meridian",33.0],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'
        param12.category = "Advanced Settings"
        
        # Parameter 13: Processing Extent (HIDDEN)
        param13 = arcpy.Parameter(
            displayName="Processing Extent",
            name="processing_extent",
            datatype="GPExtent",
            parameterType="Optional",
            direction="Input"
        )
        param13.category = "Advanced Settings"
        
        # Parameter 14: Scratch Workspace (HIDDEN)
        param14 = arcpy.Parameter(
            displayName="Scratch Workspace",
            name="scratch_workspace",
            datatype="DEWorkspace",
            parameterType="Optional",
            direction="Input"
        )
        param14.category = "Advanced Settings"
        
        return [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10, param11, param12, param13, param14]
    
    def isLicensed(self):
        """Set whether tool is licensed to execute"""
        # Check if Image Analyst extension is available
        return arcpy.CheckExtension("ImageAnalyst") == "Available"
    
    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal validation"""
        return
    
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation"""
        # Check if Image Analyst extension is available
        if arcpy.CheckExtension("ImageAnalyst") != "Available":
            parameters[0].setErrorMessage("Image Analyst extension is required but not available")
        
        # Validate confidence threshold
        if parameters[3].value is not None:
            if parameters[3].value < 0 or parameters[3].value > 1:
                parameters[3].setErrorMessage("Confidence threshold must be between 0 and 1")
        
        # Validate tile size
        if parameters[4].value is not None:
            if parameters[4].value < 64 or parameters[4].value > 2048:
                parameters[4].setWarningMessage("Tile size should typically be between 64 and 2048 pixels")
        
        # Validate batch size
        if parameters[5].value is not None:
            if parameters[5].value < 1:
                parameters[5].setErrorMessage("Batch size must be at least 1")
        
        return
    
    def execute(self, parameters, messages):
        """Execute the tool"""
        try:
            # Check out Image Analyst extension
            if arcpy.CheckExtension("ImageAnalyst") == "Available":
                arcpy.CheckOutExtension("ImageAnalyst")
            else:
                arcpy.AddError("Image Analyst extension is not available")
                return
            
            # Get input parameters
            in_raster = parameters[0].valueAsText
            in_model_definition = parameters[1].valueAsText
            out_detected_objects = parameters[2].valueAsText
            confidence_threshold = parameters[3].value if parameters[3].value is not None else 0.1
            tile_size = parameters[4].value if parameters[4].value is not None else 256
            batch_size = parameters[5].value if parameters[5].value is not None else 2
            padding = parameters[6].value if parameters[6].value is not None else 64
            max_overlap_ratio = parameters[7].value if parameters[7].value is not None else 0.0
            return_bboxes = parameters[8].value if parameters[8].value is not None else False
            test_time_augmentation = parameters[9].value if parameters[9].value is not None else False
            merge_policy = parameters[10].valueAsText if parameters[10].valueAsText else "max"
            use_gpu = parameters[11].value if parameters[11].value is not None else True
            output_coordinate_system = parameters[12].valueAsText
            processing_extent = parameters[13].valueAsText
            scratch_workspace = parameters[14].valueAsText if parameters[14].valueAsText else ""
            
            # Build arguments string
            arguments = f"padding {padding};batch_size {batch_size};threshold {confidence_threshold};return_bboxes {str(return_bboxes)};test_time_augmentation {str(test_time_augmentation)};merge_policy {merge_policy};tile_size {tile_size}"
            
            # Set processor type based on GPU preference
            processor_type = "GPU" if use_gpu else "CPU"
            
            arcpy.AddMessage("Starting Deep Learning Object Detection...")
            arcpy.AddMessage(f"Input Raster: {in_raster}")
            arcpy.AddMessage(f"Model: {in_model_definition}")
            arcpy.AddMessage(f"Output: {out_detected_objects}")
            arcpy.AddMessage(f"Processor Type: {processor_type}")
            arcpy.AddMessage(f"Using default optimized settings")
            
            # Set up environment manager with all the settings
            env_settings = {}
            
            if output_coordinate_system:
                env_settings['outputCoordinateSystem'] = output_coordinate_system
            
            if processing_extent:
                env_settings['extent'] = processing_extent
            
            env_settings['processorType'] = processor_type
            
            if scratch_workspace:
                env_settings['scratchWorkspace'] = scratch_workspace
            
            # Execute the deep learning detection with environment settings
            with arcpy.EnvManager(**env_settings):
                arcpy.AddMessage("Executing DetectObjectsUsingDeepLearning...")
                
                out_classified_raster = arcpy.ia.DetectObjectsUsingDeepLearning(
                    in_raster=in_raster,
                    out_detected_objects=out_detected_objects,
                    in_model_definition=in_model_definition,
                    arguments=arguments,
                    run_nms="NMS",
                    confidence_score_field="Confidence",
                    class_value_field="Class",
                    max_overlap_ratio=max_overlap_ratio,
                    processing_mode="PROCESS_AS_MOSAICKED_IMAGE",
                    use_pixelspace="NO_PIXELSPACE",
                    in_objects_of_interest=None
                )
                
                # Save the raster if there's an output path specified
                if hasattr(out_classified_raster, 'save'):
                    raster_output_path = out_detected_objects.replace('.gdb\\', '.gdb\\') + "_raster"
                    out_classified_raster.save(raster_output_path)
                    arcpy.AddMessage(f"Classified raster saved to: {raster_output_path}")
            
            # Get count of detected objects
            result = arcpy.management.GetCount(out_detected_objects)
            object_count = int(result[0])
            
            arcpy.AddMessage("=" * 60)
            arcpy.AddMessage("DEEP LEARNING DETECTION COMPLETE!")
            arcpy.AddMessage("=" * 60)
            arcpy.AddMessage(f"Output Feature Class: {out_detected_objects}")
            arcpy.AddMessage(f"Total Objects Detected: {object_count}")
            arcpy.AddMessage(f"Confidence Threshold: {confidence_threshold}")
            arcpy.AddMessage(f"Processing Mode: {processor_type}")
            arcpy.AddMessage("=" * 60)
            
        except Exception as e:
            arcpy.AddError(f"An error occurred during execution: {str(e)}")
            raise e
        
        finally:
            # Check in Image Analyst extension
            try:
                arcpy.CheckInExtension("ImageAnalyst")
            except:
                pass


class Toolbox:
    """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
    
    def __init__(self):
        self.label = "Deep Learning Detection Toolbox"
        self.alias = "DeepLearningDetection"
        self.description = "Tools for deep learning object detection in raster imagery"
        
        # List of tool classes associated with this toolbox
        self.tools = [DeepLearningDetectionTool]