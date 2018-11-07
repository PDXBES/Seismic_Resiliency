#-------------------------------------------------------------------------------
# Name:        fragility.py
# Purpose:
#
# Author:      DASHNEY
#
# Created:     11/17/2016
#
# Automates Fragility equations/ products
# see work request #8071, previous work #s 8010 and 6255
#-------------------------------------------------------------------------------

import arcpy, os, math, datetime, xlrd
from util import status
from util import CopyFieldFromFeature
from util import calcField_fromOverlap
from util import updateDecisionField
import config

arcpy.env.overwriteOutput = True

# INPUTS
# DOGAMI = r"\\besfile1\gis3\DataX\DOGAMI\Oregon_Resilience_Plan\extracted" # SHOULD DATA HERE BE COPIED TO SAME AS PWB LOCATION?
PWB = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Snapshot_05262016.gdb"

DOG_PGV = r"\\cgisfile\public\water\Seismic Hazard Study\SupportingData\ORP_GroundMotionAndFailure.gdb\Oregon_M_9_Scenario_Site_PGV"

# Portland Water Bureau sources - these are all vectors
PWB_Liq = os.path.join(PWB, "Seismic_Study_Deliverables_2016_Liquefaction")
PWB_LS = os.path.join(PWB, "Seismic_Study_Deliverables_2016_Lateral_Spread")
PWB_LD = os.path.join(PWB, "Seismic_Study_Deliverables_2016_Landslide_Deformation")
PWB_GS = os.path.join(PWB, "Seismic_Study_Deliverables_2016_Ground_Settlement")


# MATERIAL VALUE PATCH
# creates a lookup dictionary from the Nulls spreadsheet
# use to fill the MATERIAL field for the records that match the key val Compkeys
# use "if compkey = x and origval = y then set = to newval - this serves as a check that you're not overwriting valid values
patch_dict = createMaterialPatch_dict(config.materialPatch_xls)

# CORE

status("STARTING FRAGILITY EXTRACTION")

# subset collection lines to pipes only
status("Subsetting collection system to pipes only")
pipes = arcpy.MakeFeatureLayer_management(config.collection_lines, "pipes", "LAYER_GROUP in ( 'SEWER PIPES' , 'STORM PIPES' )")

print str(arcpy.GetCount_management(pipes)) + " pipes"

# save copy of pipes to output
datestamp = datetime.datetime.today().strftime('%Y%m%d')
outfile = "fragility_city_" + datestamp
full_outfile = os.path.join(config.resiliency_gdb, "fragility_city_" + datestamp)
status("Copying pipes to output - called " + outfile)
fragility_pipes = arcpy.CopyFeatures_management(pipes, full_outfile) # THIS IS A CITY-WIDE VERSION

# add all necessary fields
status("Adding required fields")
field_names = ("mean_depth", "PGV", "Liq_Prob", "PGD_LS", "PGD_Set", "PGD_Liq_Tot", "PGD_Landslide", "K1", "K2_Don",
"RR_Don_PGV", "RR_Don_PGD_Liq", "RR_Don_PGD_Landslide", "RR_Don_FIN", "RR_Don_breaknum", "Decision")

"""
# separated out and not used for now (DCA - 1/31/2018)
GS_field_names = ("K2_GS", "RR_GS_PGV", "RR_GS_PGD_Liq", "RR_GS_PGD_Landslide","RR_GS_FIN", "RR_GS_breaknum")
"""

for name in field_names:
    if name == "Liq_Prob" or name == "Decision":
        arcpy.AddField_management(fragility_pipes, name, "TEXT")
    else:
        arcpy.AddField_management(fragility_pipes, name, "DOUBLE")

# DATA PATCHES -----------------------------------------------------------------------------
# fix for materials that are weird - only affects a few pipes
status("Adjusting a few erroneous pipe values")
with arcpy.da.UpdateCursor(fragility_pipes, ["COMPKEY","MATERIAL"]) as cursor:
    for row in cursor:
        if row[0] == 132037:
            row[1] = "PVC"
        elif row[0] ==490799:
            row[1] = "CIPP"
        cursor.updateRow(row)

# patch backbone Null values using patch_dict
status("Patching missing Materials in backbone segments")
patch_Materials(fragility_pipes, patch_dict)


# CONDITION AND EXTRACT DATA --------------------------------------------------------------------

# get PGV value from raster
# convert pipes to points
status("Converting pipes to points")
pipe_points = arcpy.FeatureToPoint_management(pipes,"in_memory\pipe_points")
# extract raster values to points
status("Extracting DOGAMI PGV raster values to points")
arcpy.CheckOutExtension("Spatial")
PGV_values = arcpy.sa.ExtractValuesToPoints(pipe_points, DOG_PGV, "in_memory\PGV_values", "NONE", "VALUE_ONLY")
# assign value to fragility_pipes
status("Assigning PGV values to fragility_pipes")
CopyFieldFromFeature(PGV_values, "COMPKEY", "RASTERVALU", fragility_pipes, "COMPKEY", "PGV")

# get other values from vectors
status("Extracting Liq_Prob values") # this one is not aggregated as it is a text value
targetFC = fragility_pipes
targetField = "Liq_Prob"
ID = "COMPKEY"
overlapFC = PWB_Liq
overlapField = "LiqExpl"
result = arcpy.Intersect_analysis([targetFC,overlapFC],"in_memory\sect_result","NO_FID","","LINE")
values={}
with arcpy.da.SearchCursor(result,[ID,overlapField]) as cursor:
    for row in cursor:
        if row[0] != None:
            values[row[0]] = row[1]

with arcpy.da.UpdateCursor(targetFC,[ID, targetField]) as cursor:
    for row in cursor:
        if row[0] in values:
            if values[row[0]] != None:
                row[1] = values[row[0]]
        cursor.updateRow(row)

# these are aggregated (MAX value taken)
status("Extracting PGD_LS values")
calcField_fromOverlap(fragility_pipes, "PGD_LS", "COMPKEY", PWB_LS, "LATERALSPREAD_80pct")
status("Extracting PGD_Set values")
calcField_fromOverlap(fragility_pipes, "PGD_Set", "COMPKEY", PWB_GS, "Ground_Settlement_80pct")
status("Extracting PGD_Landslide values")
calcField_fromOverlap(fragility_pipes, "PGD_Landslide", "COMPKEY", PWB_LD, "DEF_FEET_80pct")

# convert PGD field values from feet to inches
status("Converting PGD values from feet to inches")
convertfields = ("PGD_LS", "PGD_Set", "PGD_Landslide")
for field in convertfields:
    with arcpy.da.UpdateCursor(fragility_pipes, [field]) as cursor:
        for row in cursor:
            if row[0] is not None:
                row[0] = row[0]*12
            cursor.updateRow(row)

# set PGD_Landslide value to 0 if = 4.8
# BETTER WATCH OUT FOR THIS MAGIC NUMBER CHANGING WITH FUTURE DATA INPUTS
status("Re-setting lowest range Landslide values to 0")
with arcpy.da.UpdateCursor(fragility_pipes, ["PGD_Landslide"]) as cursor:
        for row in cursor:
            if row[0] == 4.800000000000001: # this is the actual value, not just 4.8, sort of kludgey for sure
                row[0] = 0
            cursor.updateRow(row)

# calculate aggregate PGD (LS + Set) - nothing can stop my pythagorean style
status("Calculating PGD_Liq_Tot")
with arcpy.da.UpdateCursor(fragility_pipes, ["PGD_Liq_Tot", "PGD_LS", "PGD_Set"]) as cursor:
        for row in cursor:
            if row[1] is not None and row[2] is not None:
                row[0] = pow((pow(row[1],2) + pow(row[2],2)),0.5)
            elif row[1] is None and row[2] is not None:
                row[0] = row[2]
            elif row[1] is not None and row[2] is None:
                row[0] = row[1]
            cursor.updateRow(row)

# CALC VALUES ----------------------------------------------------------------------------------
# calculate K values using materials and dictionarys
status("Filling K1")
with arcpy.da.UpdateCursor(fragility_pipes, ["MATERIAL", "K1"]) as cursor:
        for row in cursor:
            if row[0] is None or row[0] == " ":
                row[1] = 0.8 # from Joe's list
            else:
                if any(row[0] in val for val in config.DBBK1.values()) == 1: # if material in orig dict, use that k val
                    val1 = [key for key, value in config.DBBK1.items() if row[0] in value][0]
                    if val1 != None or val1 != "" or val1 != " ":
                        row[1] = val1
                elif any(row[0] in val for val in config.K1_patch.values()) == 1: # otherwise use the patch dict value
                    val2 = [key for key, value in config.K1_patch.items() if row[0] in value][0]
                    if val2 != None or val2 != "" or val2 != " ":
                        row[1] = val2
            cursor.updateRow(row)

status("Filling K2_Don")
with arcpy.da.UpdateCursor(fragility_pipes, ["MATERIAL", "K2_Don"]) as cursor:
        for row in cursor:
            if row[0] is None or row[0] == " ":
                row[1] = 0.8 # from Joe's list
            else:
                if any(row[0] in val for val in config.DBBK2.values()) == 1: # if material in orig dict, use that k val
                    val1 = [key for key, value in config.DBBK2.items() if row[0] in value][0]
                    if val1 != None or val1 != "" or val1 != " ":
                        row[1] = val1
                elif any(row[0] in val for val in config.K2_patch.values()) == 1: # otherwise use the patch dict value
                    val2 = [key for key, value in config.K2_patch.items() if row[0] in value][0]
                    if val2 != None or val2 != "" or val2 != " ":
                        row[1] = val2
            cursor.updateRow(row)

# run ALA equations for calculating wave propagation and permanent ground deformation
status("Calculating RR_Don_PGV")
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_Don_PGV", "K1", "PGV"]) as cursor:
        for row in cursor:
            if row[1] is not None and row[2] is not None:
                row[0] = config.RR_waveprop_Calc(row[1], row[2])
            cursor.updateRow(row)

status("Calculating RR_Don_PGD_Liq")
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_Don_PGD_Liq", "K2_Don", "PGD_Liq_Tot"]) as cursor:
    for row in cursor:
        if row[1] is not None and row[2] is not None:
            row[0] = config.RR_PGD_Calc(row[1], row[2])
        cursor.updateRow(row)

status("Calculating RR_Don_PGD_Landslide")
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_Don_PGD_Landslide", "K2_Don", "PGD_Landslide"]) as cursor:
    for row in cursor:
        if row[1] is not None and row[2] is not None:
            row[0] = config.RR_PGD_Calc(row[1], row[2])
        cursor.updateRow(row)

# final calculations
status("Calculating RR_Don_FIN") # take whichever value is highest or which has a value if the others are Null
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_Don_FIN", "RR_Don_PGD_Liq", "RR_Don_PGD_Landslide", "RR_Don_PGV"]) as cursor:
        for row in cursor:
            if row[1] is not None and row[2] is None and row[3] is None:
                row[0] = row[1]
            elif row[1] is None and row[2] is not None and row[3] is None:
                row[0] = row[2]
            elif row[1] is None and row[2] is None and row[3] is not None:
                row[0] = row[3]

            elif row[1] is not None and row[2] is not None and row[3] is None and row[1] > row[2]:
                row[0] = row[1]
            elif row[1] is not None and row[2] is not None and row[3] is None and row[1] < row[2]:
                row[0] = row[2]

            elif row[1] is not None and row[2] is None and row[3] is not None and row[1] > row[3]:
                row[0] = row[1]
            elif row[1] is not None and row[2] is None and row[3] is not None and row[1] < row[3]:
                row[0] = row[3]

            elif row[1] is None and row[2] is not None and row[3] is not None and row[2] > row[3]:
                row[0] = row[2]
            elif row[1] is None and row[2] is not None and row[3] is not None and row[2] < row[3]:
                row[0] = row[3]

            elif row[1] is not None and row[2] is not None and row [3] is not None and row[1] > row[2] and row[1] > row[3]:
               row[0] = row[1]
            elif row[1] is not None and row[2] is not None and row [3] is not None and row[2] > row[1] and row[2] > row[3]:
               row[0] = row[2]
            elif row[1] is not None and row[2] is not None and row [3] is not None and row[3] > row[1] and row[3] > row[1]:
               row[0] = row[3]
            cursor.updateRow(row)

# break number - calculate actual number of breaks per pipe - USE shape_len if SRVY_LEN is Null?
status("Calculating RR_Don_breaknum")
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_Don_breaknum", "SRVY_LEN", "RR_Don_FIN", "Shape_Length"]) as cursor:
        for row in cursor:
            if row[2] is not None:
                if row[1] is not None:
                    row[0] = (row[1] / 1000) * row[2]
                else:
                    row[0] = (row[3] / 1000) * row[2]
            cursor.updateRow(row)

# calculate mean depth - use whatever value is available, or 0 if you cannot calculate the mean
status("Calculating mean_depth")
with arcpy.da.UpdateCursor(fragility_pipes, ["FRM_DEPTH", "TO_DEPTH", "mean_depth"]) as cursor:
        for row in cursor:
            if row[0] is  not None and row[1] is not None:
                row[2] = (row[0] + row[1]) / 2
            elif row[0] is not None and row[1] is None:
                row[2] = row[0]
            elif row[0] is None and row[1] is not None:
                row[2] = row[1]
            else:
                row[2] = 0
            cursor.updateRow(row)

status("Updating Decision field")
updateDecisionField(fragility_pipes, "PGD_Liq_Tot", "RR_Don_FIN", "PGD_Set")


status("FRAGILITY EXTRACTION COMPLETE")
print "Output saved to: " + full_outfile




