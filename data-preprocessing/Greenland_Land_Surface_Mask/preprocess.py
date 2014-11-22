#!/usr/bin/env python

from PISMNC import PISMDataset as NC
import subprocess
import numpy as np
import os

http_url = "http://bprc.osu.edu/~jbox/data/mask/"
filename = "MODIS_1250m_landuse_mask_float_2006_1860x1740_v20091101_J_Box.img"

subprocess.call(["wget", "-nc", http_url + filename])

mask = np.fromfile(filename, dtype="f4", count=-1)

shape = (1740, 1860)

x0 = -2443456.992
y0 = -2493592.067
dx = 1250.0
dy = 1250.0
x1 = x0 + (shape[1] - 1) * dx
y1 = y0 + (shape[0] - 1) * dx
x = np.linspace(x0, x1, shape[1])
y = np.linspace(y1, y0, shape[0])

nc = NC("Greenland_Land_Surface_Mask.nc", 'w')
nc.create_dimensions(x, y)
nc.define_2d_field("mask", time_dependent = False, nc_type='f',
                   attrs = {"long_name"   : "land surface classification mask",
                            "comment"     : "Downloaded from %s" % (http_url + filename),
                            "mapping"     : "mapping"})
nc.write_2d_field("mask", mask)

mapping = nc.createVariable("mapping", 'c')
mapping.grid_mapping_name = "lambert_azimuthal_equal_area"
mapping.longitude_of_projection_origin = 0.0
mapping.latitude_of_projection_origin = 90.0
mapping.false_easting = 0.0
mapping.false_northing = 0.0
mapping.ellipsoid = "sphere"

nc.Conventions = "CF-1.4"
nc.title = "Greenland Land Surface Classification Mask"
nc.source = "J. Box and others, Byrd Polar Research Center, http://bprc.osu.edu/wiki/Jason_Box_Datasets#Greenland_Land_Surface_Classification_Mask"
nc.projection = "+proj=laea +ellps=sphere +lon_0=0 +lat_0=90.0 +x_0=0.0 +y_0=0.0 +units=m"
nc.close()
