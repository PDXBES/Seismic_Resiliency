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

# core and MacJac basenames
city_basename = "fragility_combo_"
MJA_basename = "fragility_MJA_backbone_"

# file date stamps
# FOR NOW THESE ARE MANUAL INPUTS AND MUST BE CHANGED IF FULL PROCESS IS RERUN
city_date = "20180213"
MJA_date = "20180207"

output_gdb = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Seismic_Analysis.gdb"
fragility_combo = os.path.join(output_gdb, city_basename + city_date)
MJA_backbone = os.path.join(output_gdb, MJA_basename + MJA_date)

# PUT THIS IN A UTIL MODULE!
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

fieldlist = (['PGV', 'Liq_Prob', 'PGD_LS', 'PGD_Set', 'PGD_Liq_Tot', 'PGD_Landslide',
'K1', 'K2_Don', 'RR_Don_PGV', 'RR_Don_PGD_Liq', 'RR_Don_PGD_Landslide', 'RR_Don_FIN', 'RR_Don_breaknum', 'Decision'])

ID_field = "GLOBALID"
for field in fieldlist:
     CopyFieldFromFeature(MJA_backbone, ID_field, field, fragility_combo, ID_field, field)



