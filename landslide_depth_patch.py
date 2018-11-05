#-------------------------------------------------------------------------------
# Name:        landslide_depth_patch
# Purpose:
#
# Author:      BES-ASM-DCA
#
# Created:     09/05/2018
#
# Creates a new feature class which is a modified version of the WB city result.
# This script looks for risk values that have been determined using landslide
# as the largest contributing factor. Where this is the case, if mean depth is
# >= a given distance then the largest of the two other PGD values will be used
# to determine risk.
#-------------------------------------------------------------------------------



from util import status
from util import getField_Names
import arcpy, os

resiliency_gdb = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Seismic_Analysis.gdb"
city_basename = "fragility_city_"
city_date = "20180213" # SUBJECT TO CHANGE IF FULL PROCESS IS RERUN
fragility_city = os.path.join(resiliency_gdb, city_basename + city_date)

status("STARTING PROCESS TO CREATE LANDSLIDE/ DEPTH FRAGILITY RESULT")

# TODO - make copy its own separate function
copy_path = fragility_city + "_compiled" # output feature class
if arcpy.Exists(copy_path) == False:
    status("Making copy of fragility result")
    fragility_compiled = arcpy.CopyFeatures_management(fragility_city, copy_path)
else:
    status("Copy already exists - skipping copy process")
    fragility_compiled = copy_path

# add required fields - RR_Don_FIN_landslide and breaknum_landslide
add_fields = ['wLandslide_RR_Don_FIN', 'wLandslide_RR_Don_breaknum']
field_names = getField_Names(fragility_compiled)
for field in add_fields:
    if field not in field_names:
        status("Adding field - " + field)
        arcpy.AddField_management(fragility_compiled, field, "DOUBLE")
    else:
        status(field + " already exists - no field added")

depth_limit = 20
status("Using depth limit of " + str(depth_limit))
status("Updating wLandslide_RR_Don_FIN field using largest of 2 PGV values that are NOT landslide where pipe is deeper than depth limit")
with arcpy.da.UpdateCursor(fragility_compiled, ["wLandslide_RR_Don_FIN", "mean_depth", "RR_Don_PGD_Landslide", "RR_Don_PGD_Liq", "RR_Don_PGV"]) as cursor:
    for row in cursor:
        if row[1] >= depth_limit:
            if row[3] is not None and row[4] is not None and row[3] > row[4]:
                row[0] = row[3]
            elif row[3] is not None and row[4] is not None and row[4] > row[3]:
                row[0] = row[4]
            elif row[3] is not None and row[4] is None:
                row[0] = row[3]
            elif row[3] is None and row[4] is not None:
                row[0] = row[4]
        cursor.updateRow(row)

status("Updating wLandslide_breaknum (aka Breaks per 1000')") # uses SRVY_LEN over Shape_Length if possible
with arcpy.da.UpdateCursor(fragility_compiled, ["wLandslide_RR_Don_breaknum", "SRVY_LEN", "wLandslide_RR_Don_FIN", "Shape_Length"]) as cursor:
        for row in cursor:
            if row[2] is not None:
                if row[1] is not None:
                    row[0] = (row[1] / 1000) * row[2]
                else:
                    row[0] = (row[3] / 1000) * row[2]
            cursor.updateRow(row)

status("PROCESS COMPLETE")



