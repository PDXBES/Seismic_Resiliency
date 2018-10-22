#-------------------------------------------------------------------------------
# Name:        linkSource
# Purpose:
#
# Author:      dashney
#
# Created:     01/11/2016
#
# For each record, iterates through an ID field. This value is matched to
# a field name (if exists) in the specified directory of reference docs.
#
#-------------------------------------------------------------------------------

import os, arcpy, datetime

#boreholes = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Borings_Liq_TrigPGA.gdb\Drillholes_Subset_TrigPGA_Sat"
boreholes = r"\\besfile1\Resiliency_Plan\GIS\pgdb\Borings_Liq_TrigPGA.gdb\Drillholes_Subset_TrigPGA_Unsat"
docpath = r"\\besfile1\Resiliency_Plan\Background Documents\PWB\PWB Boring Logs\DOGAMI Info\Data on boreholes"
pathdict = {}

# create dict of file names and paths
print datetime.datetime.now().strftime('%x %X') + " - creating dictionary of 'file name : file path' for specified directory"
for dirname, dirnames, filenames in os.walk(docpath):
	for filename in filenames:
         if filename.split(".")[-1] == "pdf":
            pathdict[filename]=os.path.join(dirname, filename)

print datetime.datetime.now().strftime('%x %X') + " - count of files found = " + str(len(pathdict))

# cursor through borehole records and match LOG_ID to the key value
# for each match populate field with full file path (value)
print datetime.datetime.now().strftime('%x %X') + " - updating field where file name match is found"
counter = 0
with arcpy.da.UpdateCursor(boreholes, ["LOG_ID", "docpath"]) as cursor:
    for row in cursor:
        for key, value in pathdict.iteritems():
            if row[0] == key.split(".")[0]:
                row[1] = str(value)
                counter = counter + 1
            cursor.updateRow(row)

print datetime.datetime.now().strftime('%x %X') + " - done - " + str(counter) + " records populated with path"

