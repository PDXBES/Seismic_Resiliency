#-------------------------------------------------------------------------------
# Name:        fragility_final_Values
# Purpose:
#
# Author:      DASHNEY
#
# Created:     29/10/2018
#
# applies process logic to calculate final values and applies final Decision values (again)
#
#-------------------------------------------------------------------------------

from util import updateDecisionField
from util import getField_Names
from util import status
import arcpy, os

resiliency_gdb = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Seismic_Analysis.gdb"
city_basename = "fragility_city_"
city_date = "20180213" # SUBJECT TO CHANGE IF FULL PROCESS IS RERUN
suffix = "_compiled"
fragility_compiled = os.path.join(resiliency_gdb, city_basename + city_date + suffix)

fieldlist = (['PGV', 'Liq_Prob', 'PGD_LS', 'PGD_Set', 'PGD_Liq_Tot', 'PGD_Landslide',
'K1', 'K2_Don', 'RR_Don_PGV', 'RR_Don_PGD_Liq', 'RR_Don_PGD_Landslide', 'RR_Don_FIN', 'RR_Don_breaknum'])

status("STARTING PROCESS TO ADD FINAL FRAGILITY RESULT")

#create dict with {original field: final field}
fieldlist_FinalVal = {}

for field in fieldlist:
    fieldlist_FinalVal[field] = "Final_" + field

status("Adding 'Final_' fields")
field_names = getField_Names(fragility_compiled)
for name in fieldlist_FinalVal.keys():
    if fieldlist_FinalVal[name] not in field_names:
        if name == "Liq_Prob":
            status(" - adding " + fieldlist_FinalVal[name])
            arcpy.AddField_management(fragility_compiled, fieldlist_FinalVal[name], "TEXT")
        else:
            status(" - adding " + fieldlist_FinalVal[name])
            arcpy.AddField_management(fragility_compiled, fieldlist_FinalVal[name], "DOUBLE")
    else:
        status(" - " + fieldlist_FinalVal[name] + " already exists - no field added")


prefixes = ("wLandslide_", "MJ_wLandslide_", "MJ_", "Final_")
newlist = []
fulllist = []
for field in fieldlist:
    newlist.append(field)
    if field in ("RR_Don_FIN", "RR_Don_breaknum"):
        for item in prefixes:
            newlist.append(item + field)
        fulllist.append(newlist)
        newlist = []
    else:
        for item in prefixes[-2:]:
            newlist.append(item + field)
        fulllist.append(newlist)
        newlist = []


# priority order: MJ_wLandslide_, MJ_, wLandslide_, WB
# OR : MJ_, WB (if no depth/landslide patch was done for that field ie not RR_Don_FIN or RR_Don_breaknum)

status("Populating 'Final_' fields using field prioritization")
for target_fields in fulllist:
    with arcpy.da.UpdateCursor(fragility_compiled, target_fields) as cursor:
        for row in cursor:
            if len(cursor.fields) == 5:
                status(" - Populating values for " + target_fields[4])
                for row in cursor:
                    if row[2] != None:
                        row[4] = row[2]
                    elif row[2] == None and row[3] != None:
                        row[4] = row[3]
                    elif row[2] == None and row[3] == None and row[1] != None:
                        row[4]= row[1]
                    else:
                        row[4] = row[0]
                    cursor.updateRow(row)
            elif len(cursor.fields) == 3:
                status(" - Populating values for " + target_fields[2])
                for row in cursor:
                    if row[1] != None:
                        row[2] = row[1]
                    else:
                        row[2] = row[0]
                    cursor.updateRow(row)


status("Populating 'Decision' field")
updateDecisionField(fragility_compiled, "Final_PGD_Liq_Tot", "Final_RR_Don_FIN", "Final_PGD_Set")

status("PROCESS COMPLETE")
