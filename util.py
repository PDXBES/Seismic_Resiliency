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

import arcpy, os, datetime


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

    # Decision Logic constants
    pipe_depth = 30
    sum_deformation = 6
    RR1 = 1 # I have forgotted what this value means (DCA)
    RR2 = 4 # I have forgotted what this value means (DCA)
    val1 = "Monitor"
    val2 = "Whole Pipe"
    val3 = "Spot Line"

    with arcpy.da.UpdateCursor(input_fc, ["mean_depth", PGD_Liq_Tot, RR_Don_FIN, PGD_Set, "Decision"]) as cursor:
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
    status("Done")



