#-------------------------------------------------------------------------------
# Name:        fragility_MacJac.py
# Purpose:
#
# Author:      DASHNEY
#
# Created:     02/15/2018
#
# Automates Fragility equations/ products for the MacMillan Jacabs inputs
# which only provides data for a subset of the system (ie the backbone).
# This result is then "stamped" over the city-wide fragility result.
# see work request #8802, 8071, previous work #s 8010 and 6255, 8499
#-------------------------------------------------------------------------------

import arcpy, os, math, datetime, xlrd
from util import updateDecisionField
import config, util

arcpy.env.overwriteOutput = True

def FragilityMacJac():
    # MATERIAL VALUE PATCH
    # creates a lookup dictionary from the Nulls spreadsheet
    # use to fill the MATERIAL field for the records that match the key val Compkeys
    # use "if compkey = x and origval = y then set = to newval - this serves as a check that you're not overwriting valid values
    patch_dict = createMaterialPatch_dict(config.materialPatch_xls)


    # CORE -------------------------------------------------------------------------

    status("STARTING FRAGILITY EXTRACTION")

    status("Getting list of MacJac compkeys/globalids")
    # get list of COMPKEYs (if COMPKEY != None), GLOBALIDs (if GLOABALID != 0)
    compkeylist = []
    globallist = []
    with arcpy.da.SearchCursor(config.MacJac_combo, ["COMPKEY", "GLOBALID"]) as cursor:
        for row in cursor:
            if row[0] != None:
                compkeylist.append(row[0])
            else:
                if row[1] != 0:
                    globallist.append(row[1])

    # removing facilities like inlets and laterals
    status("Subsetting to sewer/ storm pipes")
    pipes = arcpy.MakeFeatureLayer_management(config.collection_lines, "pipes", "LAYER_GROUP in ( 'SEWER PIPES' , 'STORM PIPES' )")
    print str(arcpy.GetCount_management(pipes)) + " pipes"

    # subset collection lines to segments in MacJac backbone
    status("Subsetting collection system to MacJac")
    compkey_piece = str(tuple(compkeylist))
    globalid_piece = str(tuple(globallist))
    MacJac_pipes = arcpy.MakeFeatureLayer_management(config.collection_lines, "pipes", "COMPKEY in {0} or GLOBALID in {1}".format(compkey_piece, globalid_piece))
    print str(arcpy.GetCount_management(MacJac_pipes)) + " pipes"

    # save copy of pipes to output
    datestamp = datetime.datetime.today().strftime('%Y%m%d')
    outfile = "fragility_MJA_backbone_" + datestamp
    full_outfile = os.path.join(config.resiliency_gdb, "fragility_MJA_backbone_" + datestamp)
    status("Copying pipes to output - called " + outfile)
    fragility_pipes = arcpy.CopyFeatures_management(MacJac_pipes, full_outfile) # THIS IS A CITY-WIDE COPY

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

    status("Calculating values from MacJac data")
    # run using COMPKEY
    util.calcRate(config.MacJac_combo, "COMPKEY", "MJA_PGV_min", "MJA_PGV_max", fragility_pipes, "COMPKEY", "PGV", config.MJ_rate)
    util.calcRate(config.MacJac_combo, "COMPKEY", "MJA_latspr_min", "MJA_latspr_max", fragility_pipes, "COMPKEY", "PGD_LS", config.MJ_rate)
    util.calcRate(config.MacJac_combo, "COMPKEY", "MJA_liq_min", "MJA_liq_max", fragility_pipes, "COMPKEY", "PGD_Set", config.MJ_rate)
    util.calcRate(config.MacJac_combo, "COMPKEY", "MJA_landslide_min", "MJA_landslide_max", fragility_pipes, "COMPKEY", "PGD_Landslide", config.MJ_rate)
    # run again using GLOBALID
    util.calcRate(config.MacJac_combo, "GLOBALID", "MJA_PGV_min", "MJA_PGV_max", fragility_pipes, "COMPKEY", "PGV", config.MJ_rate)
    util.calcRate(config.MacJac_combo, "GLOBALID", "MJA_latspr_min", "MJA_latspr_max", fragility_pipes, "COMPKEY", "PGD_LS", config.MJ_rate)
    util.calcRate(config.MacJac_combo, "GLOBALID", "MJA_liq_min", "MJA_liq_max", fragility_pipes, "COMPKEY", "PGD_Set", config.MJ_rate)
    util.calcRate(config.MacJac_combo, "GLOBALID", "MJA_landslide_min", "MJA_landslide_max", fragility_pipes, "COMPKEY", "PGD_Landslide", config.MJ_rate)

    # convert PGD field values from feet to inches
    status("Converting PGD values from feet to inches")
    convertfields = ("PGD_LS", "PGD_Set", "PGD_Landslide")
    for field in convertfields:
        with arcpy.da.UpdateCursor(fragility_pipes, [field]) as cursor:
            for row in cursor:
                if row[0] is not None:
                    row[0] = row[0]*12
                cursor.updateRow(row)

    # calculate aggregate PGD (LS + Set)
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
    updateDecisionField(fragility_pipes)


    # -------------------------------------------------------------------------------------------------------------------

    status("FRAGILITY EXTRACTION COMPLETE")
    print "Output saved to: " + full_outfile




