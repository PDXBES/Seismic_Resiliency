#-------------------------------------------------------------------------------
# Name:        fragStamper
# Purpose:
#
# Author:      BES - ASM - DCA
#
# Stamps consultant data over top of citywide data where COMPKEY or GLOBALID matches

# AT THIS POINT THIS SHOULD BE CONSIDERED DOCUMENTATION NOT RELEASED
# THERE ARE MUCH BETTER WAYS OF DOING THIS LIKE PUTTING IT INTO AN OVERAL UTIL MODULE WITH OTHER FRAGILITY UTILS

#-------------------------------------------------------------------------------

import arcpy, os
from util import CopyFieldFromFeature
from util import createCompiled_fc
from util import status
from util import getField_Names
import config

def FragilityStamper(compiled_fc, MJ_fc):

    status("STARTING PROCESS TO ADD MACJAC FRAGILITY RESULT")

    # create dict with {original field: MJ field}
    fieldlist_MJ = {}

    for field in config.calc_fields:
        fieldlist_MJ[field] = "MJ_" + field

    status("Adding and populating 'MJ_' fields")
    # add MJ fields and populate values from MacJac fragility result
    ID_field = "GLOBALID"
    field_names = getField_Names(compiled_fc)
    for name in fieldlist_MJ.keys():
        if fieldlist_MJ[name] not in field_names:
            if name == "Liq_Prob":
                status(" - adding " + fieldlist_MJ[name])
                arcpy.AddField_management(compiled_fc, fieldlist_MJ[name], "TEXT")
            else:
                status(" - adding " + fieldlist_MJ[name])
                arcpy.AddField_management(compiled_fc, fieldlist_MJ[name], "DOUBLE")
        else:
            status(fieldlist_MJ[name] + " already exists - no field added")

        status( "-- calculating " + fieldlist_MJ[name])
        CopyFieldFromFeature(MJ_fc, ID_field, name, compiled_fc, ID_field, fieldlist_MJ[name])

    status("PROCESS COMPLETE")

