#-------------------------------------------------------------------------------
# Name:        util
# Purpose:
#
# Author:      DASHNEY
#
# Created:     29/10/2018
#
# util functions
#
#-------------------------------------------------------------------------------

import arcpy, os, datetime, config


def status(msg):
    print msg + " : " + datetime.datetime.now().strftime('%x %X')

def getField_Names(feature_class, wildcard = None):
    field_names = []
    fields = arcpy.ListFields(feature_class, wildcard)
    for field in fields:
        field_names.append(field.name)
    return field_names


def CopyFieldFromFeature(sourceFC,sourceID,sourceField,targetFC,targetID,targetField):
#copy value from a field in one feature class to another through an ID field link - used in place of a table join and field populate (faster)

    values={}
    with arcpy.da.SearchCursor(sourceFC,[sourceID,sourceField]) as cursor:
        for row in cursor:
            values[row[0]] = row[1]

    counter = 0
    with arcpy.da.UpdateCursor(targetFC,[targetID,targetField]) as cursor:
        for row in cursor:
            if row[0] in values:
                if values[row[0]] != None:
                    counter = counter + 1
                    row[1] = values[row[0]]
            cursor.updateRow(row)

    source_count = arcpy.GetCount_management(sourceFC)
    target_count = arcpy.GetCount_management(targetFC)
    match_count = counter
    status("Source Record Count: " + str(source_count) + "\n" + "Target Record Count: " + str(target_count) + "\n" + "Match Count: " + str(match_count) + "\n" +  "- Done")


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
    status("Done")

def updateDecisionField(input_fc, PGD_Liq_Tot, RR_Don_FIN, PGD_Set):
    # Decision Logic piece for Rehab/ Replacement planning
    status("Updating Decision field")

    with arcpy.da.UpdateCursor(input_fc, ["mean_depth", PGD_Liq_Tot, RR_Don_FIN, PGD_Set, "Decision"]) as cursor:
        for row in cursor:
            if row[0] > config.pipe_depth:
                row[4] = config.val1
            else:
                if row[1] >= config.sum_deformation:
                    row[4] = config.val2
                else:
                    if row[3] <> 0:
                        if row[2] >= config.RR1:
                            row[4] = config.val2
                        else:
                            row[4] = config.val3
                    else:
                        if row[2] >= config.RR2:
                            row[4] = config.val2
                        else:
                            row[4] = config.val1
            cursor.updateRow(row)
    status("Done")

def createCompiled_fc(input_fc):
    # creates copy of WB result to add fields onto
    # input fc generally WB fragility result

    import os
    copy_path = input_fc + "_compiled" # output feature class
    if arcpy.Exists(copy_path) == False:
        status("Making copy of fragility result")
        fragility_compiled = arcpy.CopyFeatures_management(input_fc, copy_path)
        return fragility_compiled
    else:
        status("Copy already exists - skipping copy process")
        return fragility_compiled

def createMaterialPatch_dict(input_xls):
    # generates dictionary from input xls
    patch_dict = {}
    wb = xlrd.open_workbook(input_xls)
    sh = wb.sheet_by_index(0)
    for item in range(sh.nrows):
        mylist = []
        key = sh.cell(item,0).value
        origval = sh.cell(item,1).value
        newval = sh.cell(item,2).value
        mylist.append(origval)
        mylist.append(newval)
        patch_dict[key] = mylist
    del patch_dict['COMPKEY'] # removes header
    return patch_dict

def patch_Materials(input_fc, patch_dict):
    with arcpy.da.UpdateCursor(input_fc,["COMPKEY", "MATERIAL"]) as cursor:
        for row in cursor:
            if row[0] in patch_dict:
                if patch_dict[row[0]] != None: # if compkey is not Null
                    if patch_dict[row[0]][0] == row[1]: # if existing material is the same as the lookup old material
                        row[1] = patch_dict[row[0]][1] # set material = to assumed material
                cursor.updateRow(row)


def addFields():



