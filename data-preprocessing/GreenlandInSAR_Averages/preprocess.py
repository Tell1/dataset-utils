#!/usr/bin/env python

from PISMNC import PISMDataset as NC
import subprocess
import numpy as np
import os
import optparse

## Set up the option parser
parser = optparse.OptionParser()
parser.usage = """usage: %prog [options] start_year
Here start_year is one of '2000', '2007'."""
parser.description = "This script downloads and preprocesses Joughin's Greenland Ice Velocity data averages"

parser.add_option("-o","--output_directory", dest="output_dir", help="Output directory (needs a '/')", default="")
parser.add_option("--add_mask", action="store_true", dest="add_mask", help="Add a mask showing where observations are available")

(options, args) = parser.parse_args()
output_dir = options.output_dir

if len(args) == 1 and args[0] in ["2000", "2007"]:
    start_year = int(args[0])
else:
    parser.print_help()
    exit(0)

vx_filename  = "mosaicOffsets.vx" 
vy_filename  = "mosaicOffsets.vy" 
zip_location = "marmaduke.gi.alaska.edu:/home2/tmp/GreenlandInSAR/"
if start_year == 2000:
    zip_filename = "GreenlandInSARvelocities.tar.gz"
    unpack_cmd = "tar"
    unpack_options = "-zxvfC %s" %output_dir
elif start_year == 2007:
    zip_filename = "GreenlandInSARvelocities2012.zip"
    unpack_cmd = "unzip"
    unpack_options = ""

try:
    os.stat("%s%s" %(output_dir,vx_filename))
    print "File '%s%s' already exists." %(output_dir,vx_filename)
except:
    try:
        os.stat("%s%s" %(output_dir,zip_filename))
    except:
        print "Downloading '%s'..." % (zip_filename)
        os.system("scp " + zip_location + zip_filename + " " + output_dir)
        
    print "Unpacking %s..." % zip_filename
    print "Trying: [" + unpack_cmd+','+unpack_options+','+output_dir + zip_filename+']'
    os.system(unpack_cmd + " " + unpack_options + " " + output_dir + zip_filename + " -d " + output_dir)

if not output_dir == "":
    vx_filename  = "%smosaicOffsets.vx" % output_dir
    vy_filename  = "%smosaicOffsets.vy" % output_dir


grid = np.loadtxt(vx_filename + ".geodat", skiprows=1, comments="&")

shape = (int(grid[0,1]), int(grid[0,0]))
x0 = grid[2,0] * 1e3
y0 = grid[2,1] * 1e3
dx = grid[1,0]
dy = grid[1,1]
x1 = x0 + (shape[1] - 1) * dx
y1 = y0 + (shape[0] - 1) * dx
x = np.linspace(x0, x1, shape[1])
y = np.linspace(y0, y1, shape[0])

nc = NC("%Greenland_Average_%s.nc" % (output_dir,years), 'w')
nc.create_dimensions(x, y)

for (filename, short_name, long_name) in [(vx_filename, "vx", "ice surface velocity in the X direction"),
                                          (vy_filename, "vy", "ice surface velocity in the Y direction"),
                                          ]:

    nc.define_2d_field(short_name, time_dependent = False, nc_type='f4',
                       attrs = {"long_name"   : long_name,
                                "comment"     : "Data directly received from Ian Joughin stored on marmaduke.gi.alaska.edu",
                                "units"       : "m / year",
                                "mapping"     : "mapping",
                                "_FillValue"  : -2e+9})

    var = np.fromfile(filename, dtype=">f4", count=-1)

    nc.write_2d_field(short_name, var)

# Add a mask that shows where observations are present 
if options.add_mask == True:
    nc.define_2d_field("vel_surface_mask", time_dependent = False, nc_type='i',
                       attrs = {"long_name"   : "Mask observations; 1 where surface vel. available",
                                "comment"     : "Used as vel_misfit_weight in inversion for tauc",
                                "units"       : "",
                                "mapping"     : "mapping",
                                "_FillValue"  : 0})
    var = np.fromfile(vx_filename, dtype=">f4", count=-1)
    mask = var/var
    mask[var == -2e9] = 0.
    nc.write_2d_field("vel_surface_mask", mask)

mapping = nc.createVariable("mapping", 'c')
mapping.grid_mapping_name = "polar_stereographic"
mapping.standard_parallel = 70.0
mapping.latitude_of_projection_origin = 90.0
mapping.straight_vertical_longitude_from_pole = -45.0
mapping.ellipsoid = "WGS84"

nc.Conventions = "CF-1.4"
nc.projection = "+proj=stere +ellps=WGS84 +datum=WGS84 +lon_0=-45 +lat_0=90 +lat_ts=70 +units=m"
nc.reference  = "Joughin, I., B. Smith, I. Howat, and T. Scambos. 2010. MEaSUREs Greenland Ice Velocity Map from InSAR Data. Boulder, Colorado, USA: National Snow and Ice Data Center. Digital media."
nc.title      = "MEaSUREs Greenland Ice Velocity Map from InSAR Data"

from time import asctime
import sys
separator = ' '
historystr = "%s: %s\n" % (asctime(), separator.join(sys.argv))
nc.history = historystr

nc.close()


