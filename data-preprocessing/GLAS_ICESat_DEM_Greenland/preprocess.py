#!/usr/bin/env python

from PISMNC import PISMDataset as NC
import subprocess
import numpy as np
import os

dem_filename  = "NSIDC_Grn1km_wgs84_elev_cm.dat"
dist_filename = "NSIDC_Grn1km_dist_mm.dat"
ftp_url = "ftp://anonymous@sidads.colorado.edu/pub/DATASETS/DEM/nsidc0305_icesat_greenland_dem/"

def download_and_unpack(url, filename):
    try:
        os.stat(filename)
        print "File '%s' already exists." % filename
    except:
        try:
            os.stat(filename + ".gz")
        except:
            print "Downloading '%s'..." % (filename + '.gz')
            subprocess.call(["wget", "-nc", url + filename + ".gz"])

        print "Unpacking '%s'..." % filename
        subprocess.call(["gunzip", filename + ".gz"])

download_and_unpack(ftp_url, dem_filename)
download_and_unpack(ftp_url, dist_filename)

usurf = np.fromfile(dem_filename, dtype=">i", count=-1)
dist = np.fromfile(dist_filename, dtype=">i", count=-1)

fill_value = -1
# fill obvious holes with fill_value
usurf[usurf <= 0] = fill_value

# fill less obvious holes nicely

shape = (2782, 2611)

usurf = usurf.reshape(shape)

def fill_holes(data):
    row = np.array([-1,  0,  1, -1, 1, -1, 0, 1])
    col = np.array([-1, -1, -1,  0, 0,  1, 1, 1])

    def fix_a_hole(i, j):
        # grab the 8 immediate neighbors
        nearest = data[j + row, i + col]
        # filter out missing ones
        nearest = nearest[nearest != fill_value]

        if nearest.size > 6:
            return nearest.sum() / nearest.size

        return fill_value

    for j in xrange(1,shape[0]-1):
        for i in xrange(1,shape[1]-1):
            if data[j,i] == fill_value:
                data[j,i] = fix_a_hole(i, j)

fill_holes(usurf)

x = np.linspace(-890500., 1720500., shape[1])
y = np.linspace(-628500., -3410500., shape[0])

nc = NC("NSIDC_Greenland_1km.nc", 'w')
nc.create_dimensions(x, y)
nc.define_2d_field("usurf", time_dependent = False, nc_type='i',
                   attrs = {"long_name"   : "upper surface elevation DEM",
                            "comment"     : "Downloaded from %s" % (ftp_url),
                            "units"       : "cm",
                            "valid_min"   : 0.0,
                            "mapping"     : "mapping",
                            "_FillValue"   : -1})
nc.write_2d_field("usurf", usurf)

nc.define_2d_field("dist", time_dependent = False, nc_type='i',
                   attrs = {"long_name"   : "Mean distance from contributing GLAS data for each grid cell",
                            "comment"     : "Downloaded from %s" % (ftp_url),
                            "units"       : "mm",
                            "valid_min"   : 0.0,
                            "mapping"     : "mapping"})
nc.write_2d_field("dist", dist)

mapping = nc.createVariable("mapping", 'c')
mapping.grid_mapping_name = "polar_stereographic"
mapping.standard_parallel = 70.0
mapping.latitude_of_projection_origin = 90.0
mapping.straight_vertical_longitude_from_pole = -45.0
mapping.ellipsoid = "WGS84"

nc.Conventions = "CF-1.4"
nc.projection = "+proj=stere +ellps=WGS84 +datum=WGS84 +lon_0=-45 +lat_0=90 +lat_ts=70 +units=m"

from time import asctime
import sys
separator = ' '
historystr = "%s: %s\n" % (asctime(), separator.join(sys.argv))
nc.history = historystr

nc.close()


