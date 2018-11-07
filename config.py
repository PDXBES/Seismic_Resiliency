#-------------------------------------------------------------------------------
# Name:        config
# Purpose:
#
# Author:      dashney
#
# Created:     07/11/2018
#
#
#-------------------------------------------------------------------------------

# OUTPUT
resiliency_gdb = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Seismic_Analysis.gdb"

# EQUATIONS/ CONSTANTS

def RR_waveprop_Calc(K1, PGV):
     return K1 * 0.00187 * PGV

def RR_PGD_Calc(K2, PGD):
     return K2 * 1.06 * pow(PGD, 0.319)

def rateCalc(minval, maxval, rate): # rate needs 0.8 for 80% eg
    return ((maxval - minval) * rate) + minval

MJ_rate = 0.8 # value to assume within MacJac ranges

# spreadsheet created by Joe Hoffman
materialPatch_xls = r"\\BESFile1\Resiliency_Plan\03.1 Project Work\Seismic\Conveyance Spine Repair Costs\Assumed Material.xlsx"

# K VALUES

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