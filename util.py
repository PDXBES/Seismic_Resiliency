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

import arcpy, os, datetime, config, xlrd


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

def calcRate(sourceFC,sourceID,sourceField1,sourceField2,targetFC,targetID,targetField, rate):
# generate value from source fc and populate in target fc
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

def calcValues(input_fc):
    # CALC VALUES ----------------------------------------------------------------------------------
    # calculate K values using materials and dictionaries
    # assumes a lot of field values already exist, make sure they've been added prior to using this function
    status("Filling K1")
    with arcpy.da.UpdateCursor(input_fc, ["MATERIAL", "K1"]) as cursor:
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
    with arcpy.da.UpdateCursor(input_fc, ["MATERIAL", "K2_Don"]) as cursor:
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
    with arcpy.da.UpdateCursor(input_fc, ["RR_Don_PGV", "K1", "PGV"]) as cursor:
            for row in cursor:
                if row[1] is not None and row[2] is not None:
                    row[0] = config.RR_waveprop_Calc(row[1], row[2])
                cursor.updateRow(row)

    status("Calculating RR_Don_PGD_Liq")
    with arcpy.da.UpdateCursor(input_fc, ["RR_Don_PGD_Liq", "K2_Don", "PGD_Liq_Tot"]) as cursor:
        for row in cursor:
            if row[1] is not None and row[2] is not None:
                row[0] = config.RR_PGD_Calc(row[1], row[2])
            cursor.updateRow(row)

    status("Calculating RR_Don_PGD_Landslide")
    with arcpy.da.UpdateCursor(input_fc, ["RR_Don_PGD_Landslide", "K2_Don", "PGD_Landslide"]) as cursor:
        for row in cursor:
            if row[1] is not None and row[2] is not None:
                row[0] = config.RR_PGD_Calc(row[1], row[2])
            cursor.updateRow(row)

    # final calculations
    status("Calculating RR_Don_FIN") # take whichever value is highest or which has a value if the others are Null
    with arcpy.da.UpdateCursor(input_fc, ["RR_Don_FIN", "RR_Don_PGD_Liq", "RR_Don_PGD_Landslide", "RR_Don_PGV"]) as cursor:
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
    with arcpy.da.UpdateCursor(input_fc, ["RR_Don_breaknum", "SRVY_LEN", "RR_Don_FIN", "Shape_Length"]) as cursor:
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
    with arcpy.da.UpdateCursor(input_fc, ["FRM_DEPTH", "TO_DEPTH", "mean_depth"]) as cursor:
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

def addFields(input_fragility_fc):
    status("Adding required fields")

    for name in config.field_names:
        if name == "Liq_Prob" or name == "Decision":
            status(" - Adding " + name)
            arcpy.AddField_management(input_fragility_fc, name, "TEXT")
        else:
            status(" - Adding " + name)
            arcpy.AddField_management(input_fragility_fc, name, "DOUBLE")

def addField_test(input_fc, new_field):
    field_names = getField_Names(input_fc)
    if new_field not in field_names:
        status("Adding field - " + new_field)
        arcpy.AddField_management(input_fc, new_field, "DOUBLE")
    else:
        status(new_field + " already exists - no field added")

def addLandslideDepth_fields(input_fc, field1, field2):
    # field1 = the '***_RR_Don_FIN' field
    # field2 = the '***_breaknum' field

    status("Adding depth/landslide fields to " + input_fc)

    # add required fields - RR_Don_FIN_landslide and breaknum_landslide
    addField_test(input_fc, field1)
    addField_test(input_fc, field2)

    status("Using depth limit of " + str(config.depth_limit))
    status("Updating ***_RR_Don_FIN field using largest of 2 PGV values that are NOT landslide where pipe is deeper than depth limit")
    with arcpy.da.UpdateCursor(input_fc, [field1, "mean_depth", "RR_Don_PGD_Liq", "RR_Don_PGV"]) as cursor:
        for row in cursor:
            if row[1] >= config.depth_limit:
                if row[2] is not None and row[3] is not None and row[2] > row[3]:
                    row[0] = row[2]
                elif row[2] is not None and row[3] is not None and row[3] > row[2]:
                    row[0] = row[3]
                elif row[2] is not None and row[3] is None:
                    row[0] = row[2]
                elif row[2] is None and row[3] is not None:
                    row[0] = row[3]
            cursor.updateRow(row)

    status("Updating ***_breaknum (aka Breaks per 1000')") # uses SRVY_LEN over Shape_Length if possible
    with arcpy.da.UpdateCursor(input_fc, [field2, "SRVY_LEN", "wLandslide_RR_Don_FIN", "Shape_Length"]) as cursor:
            for row in cursor:
                if row[2] is not None:
                    if row[1] is not None:
                        row[0] = (row[1] / 1000) * row[2]
                    else:
                        row[0] = (row[3] / 1000) * row[2]
                cursor.updateRow(row)





