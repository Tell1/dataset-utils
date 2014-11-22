from PISMNC import PISMDataset as NC
import os
import csv
import scipy.io
import numpy as np
import argparse
import subprocess

# Download and unpack CReSIS 0.5 km gridded data (copyed from MEaSUREs_Greenland_Ice_Velocity/preprocess.py"
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
            os.stat(full_filename + ".zip")
        except:
            print "Downloading '%s'..." % (full_filename + '.zip')
            subprocess.call(["wget", "-nc", "--directory-prefix=%s" %output_dir, url + filename + ".zip"])

        print "Unpacking %s..." % full_filename
        subprocess.call(["unzip", full_filename + ".zip", "-d", output_dir])

# Load CReSIS data and store in variables
def readComposite(file_name):
    file = open(file_name,'rb')
    reader = csv.reader(file)

    ncols = reader.next()
    ncols = int(ncols[0].split()[1])
    nrows = reader.next()
    nrows = int(nrows[0].split()[1])
    xllcorner = reader.next()
    xllcorner = float(xllcorner[0].split()[1])
    yllcorner = reader.next()
    yllcorner = float(yllcorner[0].split()[1])
    cellsize = reader.next()
    cellsize = float(cellsize[0].split()[1])
    fill_value = reader.next()
    fill_value = float(fill_value[0].split()[1])

    var = np.zeros((nrows,ncols))
    for i,row in enumerate(reader):
        values = row[0].split()
        for j in range(int(ncols)):
            var[i,j] = float(values[j])

    # Make grid (start from upper left corner because of matrix indices in python)
    xulcorner = xllcorner 
    yulcorner = yllcorner+cellsize*nrows
    x = np.linspace(xulcorner,xulcorner+cellsize*(ncols-1),ncols)
    y = np.linspace(yulcorner,yulcorner-cellsize*(nrows-1),nrows)

    return x,y,var,fill_value

def grid2netcdf(filename_base,output_filename):
    print "Reading txt files with data ..."
    x,y,topg,fill_value = readComposite('%sbottom.txt'%filename_base)
    x,y,thk,fill_value = readComposite('%sthickness.txt'%filename_base)
    x,y,usurf,fill_value = readComposite('%ssurface.txt'%filename_base)

    nc = NC('%s.nc'%output_filename, "w")
    nc.create_dimensions(x, y)

    names = []
    for (short_name, long_name) in [("topg", "bedrock surface elevation"),
                                    ("thk", "land ice thickness"),
                                    ("usurf", "ice upper surface elevation")
                                    ]:
        entry = (short_name,long_name)
        names.append(entry)

    var = [topg,thk,usurf]
    for i,(short_name, long_name) in enumerate(names):
        nc.define_2d_field(short_name, time_dependent = False, nc_type='f4',
                           attrs = {"long_name" : long_name,
                                    "comment" : "Downloaded from ftp://data.cresis.ku.edu/data/grids/Jakobshavn_2006_2012_Composite.zip",
                                    "units" : "m",
                                    "mapping" : "mapping",
                                    "_FillValue" : fill_value})

        nc.write_2d_field(short_name, var[i])

    # Add a mask that shows where observations are present 
    nc.define_2d_field("obs_mask", time_dependent = False, nc_type='i',
                       attrs = {"long_name"   : "Mask observations; 1 where observations available",
                                "units"       : "",
                                "mapping"     : "mapping",
                                "_FillValue"  : 0})
    mask = np.ones(thk.shape)
    mask[thk == fill_value] = 0.
    nc.write_2d_field("obs_mask", mask)

    mapping = nc.createVariable("mapping", 'c')
    mapping.grid_mapping_name = "polar_stereographic"
    mapping.standard_parallel = 70.0
    mapping.latitude_of_projection_origin = 90.0
    mapping.straight_vertical_longitude_from_pole = -45.0
    mapping.ellipsoid = "WGS84"

    nc.Conventions = "CF-1.4"
    nc.projection = "+proj=stere +ellps=WGS84 +datum=WGS84 +lon_0=-45 +lat_0=90 +lat_ts=70 +units=m"
    nc.reference = "Gogineni, Prasad. 2012. CReSIS Radar Depth Sounder Data, Lawrence, Kansas, USA. Digital Media. http://data.cresis.ku.edu"
    nc.title = "CReSIS Gridded Depth Sounder Data for Jakobshavn, Greenland"
    nc.acknowledgement = "We acknowledge the use of data and/or data products from CReSIS generated with support from NSF grant ANT-0424589 and NASA grant NNX10AT68G"

    from time import asctime
    import sys
    separator = ' '
    historystr = "%s: %s\n" % (asctime(), separator.join(sys.argv))
    nc.history = historystr
    print "Done writing %s.nc ..."%output_filename

    nc.close()

    # Run nc2cdo to add lat/lon
    print "Adding lat/lon by running nc2cdo.py ..."
    os.system('nc2cdo.py %s.nc'%output_filename)


## Main code starts here ##
if __name__ == "__main__":
    ## Set up the option parser
    parser = argparse.ArgumentParser(description='This script downloads and preprocesses CReSIS gridded 0.5 km radar depth sounder data.')
    parser.add_argument("-o","--output_directory", dest="output_dir", help="Output directory (needs a '/')", default="CReSIS_data/")
    parser.add_argument("--add_mask", action="store_true", dest="add_mask", help="Add a mask showing where observations are available")
    
    args = parser.parse_args()
    output_dir = args.output_dir
    
    filename = "Jakobshavn_2006_2012_Composite"
    ftp_url = "ftp://data.cresis.ku.edu/data/grids/"

    download_and_unpack(ftp_url, filename, output_dir)

    filename_base = "%s%s/grids/jakobshavn_2006_2012_composite_" %(output_dir,filename)
    output_filename = "%sjak0.5km_CReSIS" % (output_dir)

    grid2netcdf(filename_base, output_filename)
