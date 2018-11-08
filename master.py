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


WB_fragility_pipes = Fragility()
MJ_fragility_pipes = FragilityMacJac()
addLandslideDepth_fields(WB_fragility_pipes, "wLandslide_RR_Don_FIN", "wLandslide_breaknum")
addLandslideDepth_fields(MJ_fragility_pipes, "MJ_wLandslide_RR_Don_FIN", "MJ_wLandslide_breaknum")
compiled = createCompiled_fc(WB_fragility_pipes)
FragilityStamper(compiled, MJ_fragility_pipes)
FragilityFinalValues(compiled)

