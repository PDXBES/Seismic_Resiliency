#-------------------------------------------------------------------------------
# Name:        master
# Purpose:
#
# Author:      dashney
#
# Created: 11/08/2018
#
#-------------------------------------------------------------------------------


from fragility import Fragility
from fragility_MacJac import FragilityMacJac
from fragilityStamper import FragilityStamper
from util import createCompiled_fc
from util import addLandslideDepth_fields
from fragility_final_Values import FragilityFinalValues

# fragility run separately for WB and MJ inputs
#WB_fragility_pipes = Fragility()
#MJ_fragility_pipes = FragilityMacJac()

WB_fragility_pipes = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Seismic_Analysis.gdb\fragility_city_20181119"
MJ_fragility_pipes = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Seismic_Analysis.gdb\fragility_MJA_backbone_20181120"

# landslide depth patch is applied independently to WB and MJ results
addLandslideDepth_fields(WB_fragility_pipes, "wLandslide_RR_Don_FIN", "wLandslide_RR_Don_breaknum")
addLandslideDepth_fields(MJ_fragility_pipes, "wLandslide_RR_Don_FIN", "wLandslide_RR_Don_breaknum")

# a 'compiled' version is created, based on WB result
compiled = createCompiled_fc(WB_fragility_pipes)

# MJ fields are added to the 'compiled' version
FragilityStamper(compiled, MJ_fragility_pipes)

# 'Final' fields are added logic applied to populate them from either the MJ or WB results
FragilityFinalValues(compiled)



# TEST ------------------------------------------------------------------------------------------------------
# compiled_fc = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Seismic_Analysis.gdb\fragility_city_20180213_compiled"
# MJ_fc = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Seismic_Analysis.gdb\fragility_MJA_backbone_20180207"
# FragilityFinalValues(compiled_fc)

# TODO - could do all the above in_memory then save out result at the end. Would speed things up but perhaps harder to QC