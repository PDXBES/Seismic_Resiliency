#-------------------------------------------------------------------------------
# Name:        fragility.py
# Purpose:
#
# Author:      DASHNEY
#
# Created:     11/17/2016
#
# Automates Fragility equations/ products
# see work request #8071, previous work #s 8010 and 6255
#-------------------------------------------------------------------------------

import arcpy, os, math, datetime, xlrd, sys

arcpy.env.overwriteOutput = True

# CONNECTIONS
sde_egh_public = r"\\oberon\grp117\DAshney\Scripts\connections\egh_public on gisdb1.rose.portland.local.sde"

# INPUTS
# DOGAMI = r"\\besfile1\gis3\DataX\DOGAMI\Oregon_Resilience_Plan\extracted" # SHOULD DATA HERE BE COPIED TO SAME AS PWB LOCATION?
PWB = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Snapshot_05262016.gdb"

"""
# NO LONGER USED
# DOGAMI sources - these are all rasters
DOG_Liq = os.path.join(DOGAMI,"ORP_Liquefaction_PGD_GIS.img") # in previous work for Greg was liquefaction
DOG_LS = os.path.join(DOGAMI,"ORP_LS_PGD_GIS_Rev1.img") # in previous work for Greg was landslide/ perm ground def
DOG_PGV = os.path.join(DOGAMI, "ORP_PGA_g.img") # in previous work for Greg was called PGA (for some reason, = ?)
"""

DOG_PGV = r"\\cgisfile\public\water\Seismic Hazard Study\SupportingData\ORP_GroundMotionAndFailure.gdb\Oregon_M_9_Scenario_Site_PGV"

# Portland Water Bureau sources - these are all vectors
PWB_Liq = os.path.join(PWB, "Seismic_Study_Deliverables_2016_Liquefaction")
PWB_LS = os.path.join(PWB, "Seismic_Study_Deliverables_2016_Lateral_Spread")
PWB_LD = os.path.join(PWB, "Seismic_Study_Deliverables_2016_Landslide_Deformation")
PWB_GS = os.path.join(PWB, "Seismic_Study_Deliverables_2016_Ground_Settlement")

collection_lines = sde_egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.collection_lines_bes_pdx"

# OUTPUT
output_gdb = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Seismic_Analysis.gdb"

# spreadsheet created by Joe Hoffman
materialPatch_xls = r"\\BESFile1\Resiliency_Plan\03.1 Project Work\Seismic\Conveyance Spine Repair Costs\Assumed Material.xlsx"

# EQUATIONS

def Liq_Calc(K, D, PGD): # D = pipe diameter
    return K * (1.092/(1+7.408 * pow(math.e, (-0.6886 * D)))) * (pow(PGD, 0.319))

def LS_Calc(K, mean_depth, PGD): # H = pipe depth (mean depth is used in place of H here)
     return (K * 1.06 * (pow(PGD, 0.319))) * (1.3922/(1 + pow(math.e, -0.94621 + 0.10201 * mean_depth)))

def PGV_Calc(K, PGV):
     return K * 0.00475 * PGV

def RR_waveprop_Calc(K1, PGV):
     return K1 * 0.00187 * PGV

def RR_PGD_Calc(K2, PGD):
     return K2 * 1.06 * pow(PGD, 0.319)

def rateCalc(minval, maxval, rate): # rate needs 0.8 for 80% eg
    return ((maxval - minval) * rate) + minval

# Decision Logic constants
pipe_depth = 30
sum_deformation = 6
RR1 = 1
RR2 = 4

# MATERIAL VALUE PATCH
# creates a lookup dictionary from the Nulls spreadsheet
# use to fill the MATERIAL field for the records that match the key val Compkeys
# use "if compkey = x and origval = y then set = to newval - this serves as a check that you're not overwriting valid values
patch_dict = {}
wb = xlrd.open_workbook(materialPatch_xls)
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

# K VALUES
"""
SavageK2 = ({0.15:("H.D.P.","HDP","HDPE","ADS","SLIP"), 0.43:("D.I.P.","DIP","DI","D. TIL","D.TIL"),0.62:("STEEL"),
0.75:("RCP","RCSP","R.C.S.","MON","MON.","MON.C","MON. C","MCP","CIPP","MONO","MONO.","MONOLI","MONO.C","MONO-C","PRECAS","REINF.","PS","RMCP","CONBRK"),
0.8:("CSP","C.S.P.","CP","C.P.","CONC","CONC.","CON","CON.","CONCRE","CCP","P.V.C.","PVC"),0.83:("CMP","COR.S","COR.I.","CORR."),
0.88:("ASBEST","ASBES","ABS","ACP","ACPP","A.C.P.","FRP","CIP","C.I.P.","C.I.","CI","IRON"),0.92:("NCP","NCP OR","Wood"),
0.94:("CLAY","CT","TILE","V.S.P.","VSP","VCP","T.C.P.","TCP"),0.95:("BRCK","BRICK","BRCK.","BRK","BRK.","B","BR.","BRKSTN","B.&S.")})
"""

DBBK1 = ({0.15:("H.D.P.","HDP","HDPE","ADS","STEEL","SLIP"), 0.5:("D.I.P.","DIP","DI","D. TIL","D.TIL","Steel","ASBEST","ASBES","ABS","ACP","ACPP","A.C.P.","FRP"),
0.8:("RCP","RCSP","R.C.S.","MON","MON.","MON.C","MON. C","MCP","CIPP","MONO","MONO.","MONOLI","MONO.C","MONO-C","PRECAS","REINF.","PS","RMCP","CSP",
"C.S.P.","CP","C.P.","CONC","CONC.","CON","CON.","CONCRE","CCP","CONBRK"),0.6:("P.V.C.","PVC"),0.3:("CMP","COR.S","COR.I.","CORR."),
1:("CIP","C.I.P.","C.I.","CI","IRON"),1.3:("NCP","NCP OR"),0.7:("Wood","CLAY","CT","TILE",
"V.S.P.","VSP","VCP","T.C.P.","TCP","BRCK","BRICK","BRCK.","BRK","BRK.","B","BR.","BRKSTN","B.&S.")})

DBBK2 = ({0.15:("H.D.P.","HDP","HDPE","ADS","STEEL","SLIP"), 0.5:("D.I.P.","DIP","DI","D. TIL","D.TIL","Steel"),
0.8:("RCP","RCSP","R.C.S.","MON","MON.","MON.C","MON. C","MCP","CIPP","MONO","MONO.","MONOLI","MONO.C","MONO-C","PRECAS","REINF.","PS","RMCP","CSP",
"C.S.P.","CP","C.P.","CONC","CONC.","CON","CON.","CONCRE","CCP","ASBEST","ASBES","ABS","ACP","ACPP","A.C.P.","FRP","CONBRK"),0.9:("P.V.C.","PVC"),
0.3:("CMP","COR.S","COR.I.","CORR."),1:("CIP","C.I.P.","C.I.","CI","IRON"),0.7:("Wood","CLAY","CT","TILE",
"V.S.P.","VSP","VCP","T.C.P.","TCP"),1.3:("BRCK","BRICK","BRCK.","BRK","BRK.","B","BR.","BRKSTN","B.&S.","NCP","NCP OR")})

# K VALUE PATCH
# values from Joe Hoffman (Null val (assigned 0.8) accounted for in k value assignment section
K1_patch = ({0.8:("brick_tunnel_liner_plate", "brick_conc_liner", "CONSTN", "VARIES", "UNSPEC", "stub", "STUB", "STUB _PLUG",
"STUB&PLUG", "STUB & PLUG", "STUB]", "WOOD", "WOOD FLUME"), 0.75:("brick_fbr_liner")})

K2_patch = ({0.8:("brick_tunnel_liner_plate", "CONSTN", "VARIES", "UNSPEC", "stub", "STUB", "STUB _PLUG",
"STUB&PLUG", "STUB & PLUG", "STUB]", "WOOD", "WOOD FLUME"), 0.75:("brick_fbr_liner"), 1:("brick_conc_liner")})

# FUNCTIONS

def status(msg):
    print msg + " : " + datetime.datetime.now().strftime('%x %X')

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

# CORE

status("STARTING FRAGILITY EXTRACTION")

# subset collection lines to pipes
# FIRST ONE HERE IS FOR ALL PIPES, SECOND FOR LARGE DIAMETER PIPES
status("Subsetting collection system to pipes only")
pipes = arcpy.MakeFeatureLayer_management(collection_lines, "pipes", "LAYER_GROUP in ( 'SEWER PIPES' , 'STORM PIPES' )")

#status("Subsetting collection system to Large Diameter pipes only")
# THIS (COMMENTED OUT BELOW) SUBSETS THE COLLECTION SYSTEM TO THE BACKBONE ONLY - WE ARE NOT USING THIS BUT RUNNING FOR THE WHOLE NETWORK
#pipes = arcpy.MakeFeatureLayer_management(collection_lines, "pipes", "COMPKEY in (122413,122418,122420,122437,122450,122453,122456,122459,
# 122469,122485,122486,122487,122489,122497,122498,122499,122500,122509,122510,122514,122636,127322,127446,127447,127448,127449,127450,127451,
# 127452,127453,127461,127464,127476,127477,127512,127514,127515,127517,127522,127523,127524,127525,127526,127527,127528,127529,127530,127532,
# 127535,127539,127540,127546,127559,127602,127603,127613,127631,127635,127641,130891,131206,131244,131251,131259,131266,131268,131270,131335,
# 131336,131337,131338,131339,131346,131347,131464,131468,131469,131541,131562,131564,131565,131586,131602,131699,131741,131763,386617,401331,
# 401332,408485,411855,420113,420124,420144,427632,434753,443054,450598,490271,490283,490288,490290,490292,490296,490298,490300,490306,490314,
# 490320,490321,502875,490269,490267,490265,490263,484272,140112,127695,127698,127710,127729,127741,127790,127837,127855,127870,127880,127881,
# 127882,127897,127902,127947,127948,127949,127950,127951,127952,127966,127969,131896,131900,131905,131984,131985,131986,131987,132035,132036,
# 132037,132045,132047,132048,132049,132051,132066,132067,132092,132098,132106,132116,132117,132118,132159,132160,132243,132244,132245,132246,
# 132247,132248,132403,132404,132405,132406,132409,132436,135029,135030,135032,135230,135231,135232,135294,135303,135304,135313,135326,135327,
# 135354,135362,135363,135364,135365,135366,135367,135368,135385,135387,135388,135404,135407,135414,135460,135480,135481,135482,135483,135491,
# 135497,135501,135571,135572,135659,135660,135662,135663,135664,135665,135673,135674,135675,135677,135678,135687,135688,135705,135706,135708,
# 135723,135736,135739,135740,135741,135742,135743,135744,135746,135751,135752,135754,135755,135759,135761,135771,135780,135781,135787,135792,
# 135793,135794,135860,135866,135870,139662,140265,403425,411051,414922,421121,424576,425750,435009,448045,476823,484609,490343,490349,490351,
# 490356,490358,156314,156315,156213,156210,156240,156243,156296,156300,156304,491872,156312,487429,487427,487425,487423,487410,491973,487396,
# 487391,151327,151353,151312,151314,151305,151340,151341,151342,151343,151344,147312,147277,147278,147279,147280,490820,490819,490817,490812,
# 490809,490806,490799,418594,407110,146927,146930,146931,146935,146932,146936,147017,146933,146956,146955,146952,147145,147146,147297,147298,
# 147147,147155,147141,147299,147193,147303,147305,490558,490557,490536,490534,490532,490530,490528,487750,487747,487743,487740,487736,487730,12763)")

print str(arcpy.GetCount_management(pipes)) + " pipes"

# save copy of pipes to output
datestamp = datetime.datetime.today().strftime('%Y%m%d')
outfile = "fragility_city_" + datestamp
full_outfile = os.path.join(output_gdb, "fragility_city_" + datestamp)
status("Copying pipes to output - called " + outfile)
fragility_pipes = arcpy.CopyFeatures_management(pipes, full_outfile) # THIS IS A CITY-WIDE VERSION

# add all necessary fields
status("Adding required fields")
field_names = ("mean_depth", "PGV", "Liq_Prob", "PGD_LS", "PGD_Set", "PGD_Liq_Tot", "PGD_Landslide", "K1", "K2_Don",
"RR_Don_PGV", "RR_Don_PGD_Liq", "RR_Don_PGD_Landslide", "RR_Don_FIN", "RR_Don_breaknum", "Decision")

# separated out and not used for now (DCA - 1/31/2018)
GS_field_names = ("K2_GS", "RR_GS_PGV", "RR_GS_PGD_Liq", "RR_GS_PGD_Landslide","RR_GS_FIN", "RR_GS_breaknum")

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
with arcpy.da.UpdateCursor(fragility_pipes,["COMPKEY", "MATERIAL"]) as cursor:
    for row in cursor:
        if row[0] in patch_dict:
            if patch_dict[row[0]] != None: # if compkey is not Null
                if patch_dict[row[0]][0] == row[1]: # if existing material is the same as the lookup old material
                    row[1] = patch_dict[row[0]][1] # set material = to assumed material
            cursor.updateRow(row)

# CONDITION AND EXTRACT DATA --------------------------------------------------------------------

# get PGV value from raster
# convert pipes to points
status("Converting pipes to points")
pipe_points = arcpy.FeatureToPoint_management(pipes,"in_memory\pipe_points")
# extract raster values to points
status("Extracting DOGAMI PGV raster values to points")
arcpy.CheckOutExtension("Spatial")
PGV_values = arcpy.sa.ExtractValuesToPoints(pipe_points, DOG_PGV, "in_memory\PGV_values", "NONE", "VALUE_ONLY")
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

# set PGD_Landslide value to 0 if = 4.8
# BETTER WATCH OUT FOR THIS MAGIC NUMBER CHANGING WITH FUTURE DATA INPUTS
status("Re-setting lowest range Landslide values to 0")
with arcpy.da.UpdateCursor(fragility_pipes, ["PGD_Landslide"]) as cursor:
        for row in cursor:
            if row[0] == 4.800000000000001: # this is the actual value, not just 4.8, sort of kludgey for sure
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

# CALC VALUES ----------------------------------------------------------------------------------
# GS components --------------------------------------------------------------------------------
# calculate K values using materials and dictionarys
status("Filling K1")
with arcpy.da.UpdateCursor(fragility_pipes, ["MATERIAL", "K1"]) as cursor:
        for row in cursor:
            if row[0] is None or row[0] == " ":
                row[1] = 0.8 # from Joe's list
            else:
                if any(row[0] in val for val in DBBK1.values()) == 1: # if material in orig dict, use that k val
                    val1 = [key for key, value in DBBK1.items() if row[0] in value][0]
                    if val1 != None or val1 != "" or val1 != " ":
                        row[1] = val1
                elif any(row[0] in val for val in K1_patch.values()) == 1: # otherwise use the patch dict value
                    val2 = [key for key, value in K1_patch.items() if row[0] in value][0]
                    if val2 != None or val2 != "" or val2 != " ":
                        row[1] = val2
            cursor.updateRow(row)

status("Filling K2_Don")
with arcpy.da.UpdateCursor(fragility_pipes, ["MATERIAL", "K2_Don"]) as cursor:
        for row in cursor:
            if row[0] is None or row[0] == " ":
                row[1] = 0.8 # from Joe's list
            else:
                if any(row[0] in val for val in DBBK2.values()) == 1: # if material in orig dict, use that k val
                    val1 = [key for key, value in DBBK2.items() if row[0] in value][0]
                    if val1 != None or val1 != "" or val1 != " ":
                        row[1] = val1
                elif any(row[0] in val for val in K2_patch.values()) == 1: # otherwise use the patch dict value
                    val2 = [key for key, value in K2_patch.items() if row[0] in value][0]
                    if val2 != None or val2 != "" or val2 != " ":
                        row[1] = val2
            cursor.updateRow(row)

# run ALA equations for calculating wave propagation and permanent ground deformation
status("Calculating RR_Don_PGV")
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_Don_PGV", "K1", "PGV"]) as cursor:
        for row in cursor:
            if row[1] is not None and row[2] is not None:
                row[0] = RR_waveprop_Calc(row[1], row[2])
            cursor.updateRow(row)

status("Calculating RR_Don_PGD_Liq")
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_Don_PGD_Liq", "K2_Don", "PGD_Liq_Tot"]) as cursor:
    for row in cursor:
        if row[1] is not None and row[2] is not None:
            row[0] = RR_PGD_Calc(row[1], row[2])
        cursor.updateRow(row)

status("Calculating RR_Don_PGD_Landslide")
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_Don_PGD_Landslide", "K2_Don", "PGD_Landslide"]) as cursor:
    for row in cursor:
        if row[1] is not None and row[2] is not None:
            row[0] = RR_PGD_Calc(row[1], row[2])
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

# Decision Logic piece for Rehab/ Replacement planning - CHECK THIS!
status("Creating and filling Decision field")
val1 = "Monitor"
val2 = "Whole Pipe"
val3 = "Spot Line"
with arcpy.da.UpdateCursor(fragility_pipes, ["mean_depth", "PGD_Liq_Tot", "RR_Don_FIN", "PGD_Set", "Decision"]) as cursor:
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


"""
# GS components --------------------------------------------------------------------------------------------

# calculate K values using materials and dictionarys
# NOTE - NO K VAL DICT PATCH FOR GS (DCA - 1/31/2018)
status("Filling K2_GS")
with arcpy.da.UpdateCursor(fragility_pipes, ["MATERIAL", "K2_GS"]) as cursor:
        for row in cursor:
            if row[0] is not None:
                for key, value in SavageK2.iteritems():
                    if row[0] in value:
                        row[1] = key
            cursor.updateRow(row)

# run Greg's formulas
status("Calculating RR_GS_PGV")
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_GS_PGV", "K1", "PGV"]) as cursor:
        for row in cursor:
            if row[1] is not None and row[2] is not None:
                row[0] = PGV_Calc(row[1], row[2])
            cursor.updateRow(row)

status("Calculating RR_GS_PGD_Liq")
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_GS_PGD_Liq", "K2_GS", "PIPESIZE", "PGD_Liq_Tot"]) as cursor:
        for row in cursor:
            if row[1] is not None and row[2] is not None and row[3] is not None:
                row[0] = Liq_Calc(row[1], row[2], row[3])
            cursor.updateRow(row)

status("Calculating RR_GS_PGD_Landslide")
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_GS_PGD_Landslide", "K2_GS", "mean_depth", "PGD_Landslide"]) as cursor:
        for row in cursor:
            if row[1] is not None and row[2] is not None and row[3] is not None:
                row[0] = LS_Calc(row[1], row[2], row[3])
            cursor.updateRow(row)

# final calculations
status("Calculating RR_GS_FIN") # take whichever value is highest or which has a value if the others are Null
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_GS_FIN", "RR_GS_PGD_Liq", "RR_GS_PGD_Landslide", "RR_GS_PGV"]) as cursor:
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

status("Calculating RR_GS_breaknum")
with arcpy.da.UpdateCursor(fragility_pipes, ["RR_GS_breaknum", "SRVY_LEN", "RR_GS_FIN", "Shape_Length"]) as cursor:
        for row in cursor:
            if row[2] is not None:
                if row[1] is not None:
                    row[0] = (row[1] / 1000) * row[2]
                else:
                    row[0] = (row[3] / 1000) * row[2]
            cursor.updateRow(row)
"""
# -------------------------------------------------------------------------------------------------------------------

status("FRAGILITY EXTRACTION COMPLETE")
print "Output saved to: " + full_outfile




