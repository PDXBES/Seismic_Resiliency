#-------------------------------------------------------------------------------
# Name:        landslide_depth_patch
# Purpose:
#
# Author:      BES-ASM-DCA
#
# Created:     09/05/2018
#
# Creates a new feature class which is a modified version of the result which
# comes out of the fragilityStamper process.
# This script looks for risk values that have been determined using landslide
# as the largest contributing factor. Where this is the case, if mean depth is
# >= a given distance then the largest of the two other PGD values will be used
# to determine risk.
#-------------------------------------------------------------------------------


import arcpy, os

def status(msg):
    print msg + " : " + datetime.datetime.now().strftime('%x %X')

output_gdb = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Seismic_Analysis.gdb"
city_basename = "fragility_combo_"
city_date = "20180213" # SUBJECT TO CHANGE IF FULL PROCESS IS RERUN
fragility_combo = os.path.join(output_gdb, city_basename + city_date)

status("STARTING PROCESS TO CREATE REVISED FRAGILITY RESULT")

copy_path = fragility_combo + "_revised"
if arcpy.Exists(copy_path) == False:
    status("Making copy of fragility result")
    fragility_revised = arcpy.CopyFeatures_management(fragility_combo, copy_path)
else:
    status("Copy already exists - skipping copy process")
    fragility_revised = copy_path

depth_limit = 20
status("Using depth limit of " + str(depth_limit))
status("Updating fields RR_Don_FIN field using largest of 2 PGV values that are NOT landslide where pipe is deeper than limit")
with arcpy.da.UpdateCursor(fragility_revised, ["RR_Don_FIN", "mean_depth", "RR_Don_PGD_Landslide", "RR_Don_PGD_Liq", "RR_Don_PGV"]) as cursor:
    for row in cursor:
        if row[0] == row[2] and row[1] >= depth_limit:
            if row[3] is not None and row[4] is not None and row[3] > row[4]:
                row[0] = row[3]
            elif row[3] is not None and row[4] is not None and row[4] > row[3]:
                row[0] = row[4]
        cursor.updateRow(row)

status("Updating breaknum (aka Breaks per 1000')")
with arcpy.da.UpdateCursor(fragility_revised, ["RR_Don_breaknum", "SRVY_LEN", "RR_Don_FIN", "Shape_Length"]) as cursor:
        for row in cursor:
            if row[2] is not None:
                if row[1] is not None:
                    row[0] = (row[1] / 1000) * row[2]
                else:
                    row[0] = (row[3] / 1000) * row[2]
            cursor.updateRow(row)

status("Updating Decision field")
val1 = "Monitor"
val2 = "Whole Pipe"
val3 = "Spot Line"
pipe_depth = 30
sum_deformation = 6
RR1 = 1
RR2 = 4
with arcpy.da.UpdateCursor(fragility_revised, ["mean_depth", "PGD_Liq_Tot", "RR_Don_FIN", "PGD_Set", "Decision"]) as cursor:
    for row in cursor:
        if row[0] > pipe_depth:
            row[4] = val1
        else:
            if row[1] >= sum_deformation:
                row[4] = val2
            else:
                if row[3] <> 0:
                    if row[2] >= RR1:
                        row[4] = val2
                    else:
                        row[4] = val3
                else:
                    if row[2] >= RR2:
                        row[4] = val2
                    else:
                        row[4] = val1
        cursor.updateRow(row)

status("PROCESS COMPLETE")



