#-------------------------------------------------------------------------------
# Name:        fragility.py
# Purpose:
#
# Author:      DASHNEY
#
# Created:     11/17/2016
#
# Automates Fragility equations/ products
# see work request #8802, 8071, previous work #s 8010 and 6255
#-------------------------------------------------------------------------------

import arcpy, os, math, datetime, xlrd
from util import status
from util import CopyFieldFromFeature
from util import calcField_fromOverlap
from util import updateDecisionField
import config, util

arcpy.env.overwriteOutput = True


def Fragility():

    # save copy of pipes to output
    datestamp = datetime.datetime.today().strftime('%Y%m%d')
    outfile = "fragility_city_" + datestamp
    full_outfile = os.path.join(config.resiliency_gdb, "fragility_city_" + datestamp)
    status("Copying pipes to output - called " + outfile)
    fragility_pipes = arcpy.CopyFeatures_management(pipes, full_outfile) # THIS IS A CITY-WIDE VERSION

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


    # add all necessary fields
    util.addFields(fragility_pipes)

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
    PGV_values = arcpy.sa.ExtractValuesToPoints(pipe_points, config.DOG_PGV, "in_memory\PGV_values", "NONE", "VALUE_ONLY")
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

    status("Re-setting lowest range Landslide values to 0")
    with arcpy.da.UpdateCursor(fragility_pipes, ["PGD_Landslide"]) as cursor:
            for row in cursor:
                if row[0] == config.PGD_Landslide_val:
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


    # calculate K values using materials and dictionaries
    calcValues(fragility_pipes)


    status("Updating Decision field")
    updateDecisionField(fragility_pipes, "PGD_Liq_Tot", "RR_Don_FIN", "PGD_Set")


    status("FRAGILITY EXTRACTION COMPLETE")
    print "Output saved to: " + full_outfile

    return fragility_pipes




