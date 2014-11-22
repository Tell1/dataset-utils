#!/usr/bin/env python

from PISMNC import PISMDataset as NC
import subprocess
import numpy as np
import os
import optparse

# Function that downloads and unpacks NSIDC velocity maps
def download_and_unpack(url, filename, output_dir):
    if output_dir == "":
        full_filename = filename
    else:
        full_filename = "%s%s" %(output_dir,filename)

    try:
        os.stat(full_filename)
        print "File '%s' already exists." % full_filename
    except:
        try:
            os.stat(full_filename + ".gz")
        except:
            print "Downloading '%s'..." % (full_filename + '.gz')
            subprocess.call(["wget", "-nc", "--directory-prefix=%s" %output_dir, url + filename + ".gz"])

        print "Unpacking %s..." % full_filename
        subprocess.call(["gunzip", full_filename + ".gz"])

# Get Joughins vel_mosaic files into PISM usable netcdf format
def vel_mosaic2netcdf(filename_base, output_filename):
    files = []
    for (short_name, long_name) in [("vx", "ice surface velocity in the X direction"),
                                    ("vy", "ice surface velocity in the Y direction"),
                                    ("ex",
                                     "error estimates for the X-component of the ice surface velocity"),
                                    ("ey",
                                     "error estimates for the Y-component of the ice surface velocity"),
                                    ]:

        try:
            os.stat(filename_base + "." + short_name)
            entry = ("%s.%s" %(filename_base,short_name), short_name, long_name)
            files.append(entry)
        except:
            print "Missing %s.%s. If this file ends with ex or ey the script will work just fine" %(filename_base, short_name)

    grid = np.loadtxt(filename_base + ".vx.geodat", skiprows=1, comments="&")
    
    shape = (int(grid[0,1]), int(grid[0,0]))
    x0 = grid[2,0] * 1e3
    y0 = grid[2,1] * 1e3
    dx = grid[1,0]
    dy = grid[1,1]
    x1 = x0 + (shape[1] - 1) * dx
    y1 = y0 + (shape[0] - 1) * dx
    x = np.linspace(x0, x1, shape[1])
    y = np.linspace(y0, y1, shape[0])
    
    nc = NC("%s.nc" % output_filename, 'w')
    nc.create_dimensions(x, y)
    
    for (filename, short_name, long_name) in files:
        
        nc.define_2d_field(short_name, time_dependent = False, nc_type='f4',
                           attrs = {"long_name"   : long_name,
                                    "comment"     : "Downloaded from %s" % (ftp_url + filename),
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
        var = np.fromfile(filename_base + ".vx", dtype=">f4", count=-1)
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

## Main code starts here
if __name__ == "__main__":
    ## Set up the option parser
    parser = optparse.OptionParser()
    parser.usage = """usage: %prog [options] start_year
    Here start_year is one of '2000', '2005', '2006'."""
    parser.description = "This script downloads and preprocesses MEaSUREs Greenland Ice Velocity data"

    parser.add_option("-o","--output_directory", dest="output_dir", help="Output directory (needs a ", default="")
    parser.add_option("--add_mask", action="store_true", dest="add_mask", help="Add a mask showing where observations are available")
    
    (options, args) = parser.parse_args()
    output_dir = options.output_dir
    
    if len(args) == 1 and args[0] in ["2000", "2005", "2006","2007","2008"]:
        start_year = int(args[0])
    else:
        parser.print_help()
        exit(0)
        
    years = "%d_%d" % (start_year, start_year + 1)
    filename = "greenland_vel_mosaic500_%s" % years
    ftp_url = "ftp://anonymous@sidads.colorado.edu/pub/DATASETS/nsidc0478_MEASURES_greenland_V01/%d/" % start_year

    for ending in [".vx",".vy",".ex",".ey"]:
        download_and_unpack(ftp_url, filename + ending, output_dir)

    download_and_unpack(ftp_url, filename + ".vx.geodat", output_dir)

    output_filename = "%sMEASUREs_Greenland_%s" %(output_dir,years)
    filename_base = "%sgreenland_vel_mosaic500_%s" % (output_dir,years)
    vel_mosaic2netcdf(filename_base, output_filename)
