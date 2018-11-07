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
# see work request #8499
#-------------------------------------------------------------------------------

import arcpy, os, math, datetime, xlrd
from util import updateDecisionField
import config

arcpy.env.overwriteOutput = True


# INPUTS -----------------------------------------------------------------------
MacJac_combo = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Fragility_RepairCosts.mdb\MacJacobs_combo"

# MATERIAL VALUE PATCH
# creates a lookup dictionary from the Nulls spreadsheet
# use to fill the MATERIAL field for the records that match the key val Compkeys
# use "if compkey = x and origval = y then set = to newval - this serves as a check that you're not overwriting valid values
patch_dict = createMaterialPatch_dict(config.materialPatch_xls)


# FUNCTIONS --------------------------------------------------------------------

def status(msg):
    print msg + " : " + datetime.datetime.now().strftime('%x %X')

def calcRate(sourceFC,sourceID,sourceField1,sourceField2,targetFC,targetID,targetField, rate):
# generate value from source fc to be populated in target fc
# assumes sourceField 1 and 2 have numeric values and a certain % of range between values will be taken

    values={}
    with arcpy.da.SearchCursor(sourceFC,[sourceID, sourceField1, sourceField2]) as cursor:
        for row in cursor:
            mylist = []
            mylist.append(row[1])
            mylist.append(row[2])
            values[row[0]] = mylist

    with arcpy.da.UpdateCursor(targetFC,[targetID,targetField]) as cursor:
        for row in cursor:
            if row[0] in values:
                if row[0] != None and values[row[0]][0] != None and values[row[0]][1] != None:
                    print row[0], config.rateCalc(values[row[0]][0], values[row[0]][1], config.MJ_rate)
                    row[1] = config.rateCalc(values[row[0]][0], values[row[0]][1], config.MJ_rate)
            cursor.updateRow(row)
    status("  Done")

""" # THESE TWO FUNCTIONS ARE NOT EVEN USED IN THIS FILE = ?
def CopyFieldFromFeature(sourceFC,sourceID,sourceField,targetFC,targetID,targetField):
#copy value from a field in one feature class to another through an ID field link - used in place of a table join and field populate (faster)

    values={}
    with arcpy.da.SearchCursor(sourceFC,[sourceID,sourceField]) as cursor:
        for row in cursor:
            values[row[0]] = row[1]

    with arcpy.da.UpdateCursor(targetFC,[targetID,targetField]) as cursor:
        for row in cursor:
            if row[0] in values:
                if values[row[0]] != None:
                    row[1] = values[row[0]]
            cursor.updateRow(row)
    status("  Done")


def calcField_fromOverlap(targetFC,targetField,ID,overlapFC,overlapField):
    # fills field with values from another field where overlap exists
    # also aggregates values for you - this accounts for where intersect occurs across geometry with different values

    sect_result = arcpy.Intersect_analysis([targetFC,overlapFC],"in_memory\sect_result","NO_FID","","LINE")
    agg_in = overlapField + " MAX"
    agg_out = "MAX_" + overlapField
    result = arcpy.Dissolve_management(sect_result, "in_memory\diss_result", ID, agg_in)
    values={}
    with arcpy.da.SearchCursor(result,[ID,agg_out]) as cursor:
        for row in cursor:
            if row[0] != None:
                values[row[0]] = row[1]

    with arcpy.da.UpdateCursor(targetFC, [ID, targetField]) as cursor:
        for row in cursor:
            if row[0] in values:
                if values[row[0]] != None:
                    row[1] = values[row[0]]
            cursor.updateRow(row)
    status("  Done")
"""

# CORE -------------------------------------------------------------------------

status("STARTING FRAGILITY EXTRACTION")

status("Getting list of MacJac compkeys/globalids")
# get list of COMPKEYs (if COMPKEY != None) / GLOBALIDs (if GLOABALID != 0)
compkeylist = []
globallist = []
with arcpy.da.SearchCursor(MacJac_combo, ["COMPKEY", "GLOBALID"]) as cursor:
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
status("Adding required fields")
field_names = ("mean_depth", "PGV", "Liq_Prob", "PGD_LS", "PGD_Set", "PGD_Liq_Tot", "PGD_Landslide", "K1", "K2_Don",
"RR_Don_PGV", "RR_Don_PGD_Liq", "RR_Don_PGD_Landslide", "RR_Don_FIN", "RR_Don_breaknum", "Decision")

# separated out and not used for now (DCA - 1/31/2018)
#GS_field_names = ("K2_GS", "RR_GS_PGV", "RR_GS_PGD_Liq", "RR_GS_PGD_Landslide","RR_GS_FIN", "RR_GS_breaknum")

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
# copy over data from MacJac backbone to 'fragility pipes' using Compkey/ GLOBALID - use CopyFieldFromFeature funct
status("Calculating values from MacJac data")
# run using COMPKEY
calcRate(MacJac_combo, "COMPKEY", "MJA_PGV_min", "MJA_PGV_max", fragility_pipes, "COMPKEY", "PGV", config.MJ_rate)
calcRate(MacJac_combo, "COMPKEY", "MJA_latspr_min", "MJA_latspr_max", fragility_pipes, "COMPKEY", "PGD_LS", config.MJ_rate)
calcRate(MacJac_combo, "COMPKEY", "MJA_liq_min", "MJA_liq_max", fragility_pipes, "COMPKEY", "PGD_Set", config.MJ_rate)
calcRate(MacJac_combo, "COMPKEY", "MJA_landslide_min", "MJA_landslide_max", fragility_pipes, "COMPKEY", "PGD_Landslide", config.MJ_rate)
# run again using GLOBALID
calcRate(MacJac_combo, "GLOBALID", "MJA_PGV_min", "MJA_PGV_max", fragility_pipes, "COMPKEY", "PGV", config.MJ_rate)
calcRate(MacJac_combo, "GLOBALID", "MJA_latspr_min", "MJA_latspr_max", fragility_pipes, "COMPKEY", "PGD_LS", config.MJ_rate)
calcRate(MacJac_combo, "GLOBALID", "MJA_liq_min", "MJA_liq_max", fragility_pipes, "COMPKEY", "PGD_Set", config.MJ_rate)
calcRate(MacJac_combo, "GLOBALID", "MJA_landslide_min", "MJA_landslide_max", fragility_pipes, "COMPKEY", "PGD_Landslide", config.MJ_rate)

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

# CALC VALUES ----------------------------------------------------------------------------------
# GS components --------------------------------------------------------------------------------
# calculate K values using materials and dictionarys
status("Filling K1")
with arcpy.da.UpdateCursor(fragility_pipes, ["MATERIAL", "K1"]) as cursor:
        for row in cursor:
            if row[0] is None or row[0] == " ":
                row[1] = 0.8 # from Joe's list, Null = 0.8
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
                row[1] = 0.8 # from Joe's list, Null = 0.8
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
# ACCOUNT FOR VALUES OF 0 AND TREAT THE SAME AS NULL
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
updateDecisionField(fragility_pipes)



# -------------------------------------------------------------------------------------------------------------------

status("FRAGILITY EXTRACTION COMPLETE")
print "Output saved to: " + full_outfile




