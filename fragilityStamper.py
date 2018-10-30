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
from util import status
from util import getField_Names

# core and MacJac basenames
city_basename = "fragility_city_"
city_date = "20180213" # SUBJECT TO CHANGE IF FULL PROCESS IS RERUN
suffix = "_compiled"

MJA_basename = "fragility_MJA_backbone_"

# file date stamps
# FOR NOW THESE ARE MANUAL INPUTS AND MUST BE CHANGED IF FULL PROCESS IS RERUN
city_date = "20180213"
MJA_date = "20180207"

resiliency_gdb = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Seismic_Analysis.gdb"
fragility_compiled = os.path.join(resiliency_gdb, city_basename + city_date + suffix)
MJA_backbone = os.path.join(resiliency_gdb, MJA_basename + MJA_date)

fieldlist = (['PGV', 'Liq_Prob', 'PGD_LS', 'PGD_Set', 'PGD_Liq_Tot', 'PGD_Landslide',
'K1', 'K2_Don', 'RR_Don_PGV', 'RR_Don_PGD_Liq', 'RR_Don_PGD_Landslide', 'RR_Don_FIN', 'RR_Don_breaknum'])

status("STARTING PROCESS TO ADD MACJAC FRAGILITY RESULT")

# create dict with {original field: MJ field}
fieldlist_MJ = {}

for field in fieldlist:
    fieldlist_MJ[field] = "MJ_" + field

status("Adding and populating 'MJ_' fields")
# add MJ fields and populate values from MacJac fragility result
ID_field = "GLOBALID"
field_names = getField_Names(fragility_compiled)
for name in fieldlist_MJ.keys():
    if fieldlist_MJ[name] not in field_names:
        if name == "Liq_Prob":
            status(" - adding " + fieldlist_MJ[name])
            arcpy.AddField_management(fragility_compiled, fieldlist_MJ[name], "TEXT")
        else:
            status(" - adding " + fieldlist_MJ[name])
            arcpy.AddField_management(fragility_compiled, fieldlist_MJ[name], "DOUBLE")
    else:
        status(fieldlist_MJ[name] + " already exists - no field added")

    status( "-- calculating " + fieldlist_MJ[name])
    CopyFieldFromFeature(MJA_backbone, ID_field, name, fragility_compiled, ID_field, fieldlist_MJ[name])

status("PROCESS COMPLETE")

