# coding: utf-8
import logging
import datetime
import numpy as np
import netCDF4
import os

# Define the logger
LOG = logging.getLogger(__name__)
DATE_FORMAT = "%Y%m%d%H%M%S"

class SatDataException(Exception):
    pass


def get_files_from_datadir(data_dir, date_from, date_to):
    """
    Getting the files from the data dir.
    It does a walk through the data dir and finds files that
    - Starts with a date in the specified date range.
    - Contains the string "-DMI-L4"
    - Ends with .nc
    """
    LOG.debug("Data dir: '%s'"%data_dir)
    LOG.debug("Date from: '%s'."%date_from)
    LOG.debug("Date to: '%s'."%date_to)

    # Make sure that date_from allways is before date_to.
    # Be aware of that this must be done in one step. If not a temp variable is needed.
    date_from, date_to = min(date_from, date_to), max(date_from, date_to)

    LOG.debug("Dates after min/max:")
    LOG.debug("Date from: '%s'."%date_from)
    LOG.debug("Date to: '%s'."%date_to)

    for root, dirs, files in os.walk(data_dir):
        LOG.debug("Looking for files in '%s'."%(os.path.abspath(root)))
        # Walk through every files/directories in the data_dir.
        # Filename example: 20150313000000-DMI-L4_GHRSST-SSTfnd-DMI_OI-NSEABALTIC-v02.0-fv01.0.nc.gz
        # f.endswith((".nc", ".nc.gz"))
        for filename in [f for f in files
                         if f.endswith(".nc")
                         and "-DMI-L4" in f
                         and date_from <= get_date_from_filename(f) <= date_to]:
            abs_filename = os.path.abspath(os.path.join(root, filename))
            LOG.debug("Found file '%s'."%(abs_filename))
            yield abs_filename

def get_available_dates(data_dir):
    """
    Gets the dates that are availabe.

    That is, it
    - finds all the relevant files (see get_files_from_datadir) in the data dir,
    - parses the filenames
    - returns the date from the filename (not the content of the file).
    """
    date_from = datetime.datetime(1981, 1, 1)
    date_to = datetime.datetime.now() + datetime.timedelta(days = 1)
    for filename in get_files_from_datadir(data_dir, date_from, date_to):
        yield get_date_from_filename(filename)


def get_date_from_filename(filename):
    return datetime.datetime.strptime(os.path.basename(filename).split("-")[0], DATE_FORMAT)


class Satellite(object):
    def __init__(self, input_filename):
        self.input_filename = input_filename
        
    def __enter__(self):
        return self.

    def __exit__(self, type, value, traceback):
        pass

    def variables_is_in_file(self, required_variables):
        """
        Makes sure that the variables in the "required_variables"
        can actually be found in the file.
        """
        LOG.debug("Required variables: %s"%(required_variables))
        assert(isinstance(required_variables, list))

        variable_names = self.get_variable_names()
        for required_variable in required_variables:
            if required_variable not in variable_names:
                LOG.warning("The file, '%s', must have the variable '%s'."%(self.input_filename, required_variable))
                return False
        return True

    def get_closest_lat_lon_indexes(self, lat, lon):
        """
        Gets the indexes for the specified lat/lon values.
        
        E.g. analysed_sst is a grid. The indexes correspond to (time, lat, lon).
        Time is only one dimension in our files, so we need the lat / lon indexes.
        
        TODO:
                         LON
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  |
        +-----+-----+-----+-----+-----+-----+ LAT
        |  x  |  x  |  x  |  x  |  x  |  x  |
        +-----+-----+-----+-----+-----+-----+
        
        The lat/lon points are the center values in the grid cell.
        The edges are therefore not included below. Fix this by:
        - adding grid_width/2 to the max lon values
        - subtract grid_width/2 to the min lon valus
        - adding grid_height/2 to the max lat values
        - subtract grid_height/2 to the min lat valus
        """
        lats, lons = self.get_lat_lon_ranges()
    
        # TODO: Missing the edges!!
        # lat[0] - grid_cell_height/2, lat[1] + grid_cell_height/2
        if not lats[0] <= lat <= lats[1]:
            raise SatDataException("Latitude %s is outside latitude range %s."%(lat, " - ".join([str(l) for l in lats])))
    
        # lon[0] - grid_cell_width/2, lon[1] + grid_cell_width/2
        if not lons[0] <= lon <= lons[1]:
            raise SatDataException("Longitude %s is outside longitude range %s."%(lon, " - ".join([str(l) for l in lons])))

        nc = netCDF4.Dataset(self.input_filename)
        try:
            lat_index = abs((nc.variables['lat'] - np.float32(lat))).argmin()
            lon_index = abs((nc.variables['lon'] - np.float32(lon))).argmin()

            LOG.debug("Lat index: %i. Lat: %f."%(lat_index, nc.variables['lat'][lat_index]))
            LOG.debug("Lon index: %i. Lon: %f."%(lon_index, nc.variables['lon'][lon_index]))
            return lat_index, lon_index
        finally:
            nc.close()

    def get_values(self, lat, lon, variables_to_print=None, ignore_if_missing=False):
        """
        Getting the values for the specified lat / lon values.
        
        It gets the indexes closest to lat/lon and
        returns a list of the values specified in variables_to_print.
        
        If ignore_if_missing is set, None will be returned, if one of the values are missing.
        """
        # Get the closes indexes for the lat lon.
        LOG.debug("Getting the values from the file.")

        LOG.debug("Getting the indexes for lat/lon: %f/%f"%(lat, lon))
        lat_index, lon_index = self.get_closest_lat_lon_indexes(lat, lon)

        LOG.debug("The lat/lo indexes for %f/%f were: %i, %i"%(lat, lon, lat_index, lon_index))

        if variables_to_print == None:
            LOG.debug("Setting variables to print to:")
            variables_to_print = self.get_variable_names()
            LOG.debug(variables_to_print)

        # Do the work.
        nc = netCDF4.Dataset(self.input_filename)
        try:
            items_to_print = []
            one_of_the_values_are_missing = False
            for variable_name in variables_to_print:
                LOG.debug("Adding variable name: %s."%(variable_name))
                if variable_name == "lat":
                    items_to_print.append(nc.variables['lat'][lat_index])
                elif variable_name == "lon":
                    items_to_print.append(nc.variables['lon'][lon_index])
                elif variable_name == "time":
                    # The time variable is seconds since 1981-01-01.
                    start_date = datetime.datetime(1981, 1, 1)
                    items_to_print.append((start_date + datetime.timedelta(seconds=int(nc.variables['time'][0]))))
                else:
                    variable = nc.variables[variable_name][0][lat_index][lon_index]
                    if hasattr(variable, "mask"):
                        if variable.mask:
                            one_of_the_values_are_missing = True
                    items_to_print.append(variable)

            LOG.debug("Checking if any of the values are missing.")
            if one_of_the_values_are_missing:
                LOG.debug("Checking if we are to print the values or not even if one of the values are missing.")
                if ignore_if_missing:
                    LOG.debug("Returning None because one fo the values were missing.")
                    return None

            # There were no missing values or we will return it after all...
            LOG.debug("Converting all items to string")
            items_to_print = map(lambda x: str(x), items_to_print)

            # Returning the items list.
            LOG.debug("Items to string: %s"%(items_to_print))
            return items_to_print
        finally:
            nc.close()

    def get_lat_lon_ranges(self):
        """
        Getting the lat long ranges from a input file.
        
        Opens the file, reads the lat/lon arrays and finds the min/max values.
        """
        nc = netCDF4.Dataset(self.input_filename)
        try:
            return [min(nc.variables['lat']), max(nc.variables['lat'])], [min(nc.variables['lon']), max(nc.variables['lon'])]
        finally:
            nc.close()


    def get_variable_names(self):
        """
        Gets the variable names in the file. That means the variables that can be read from the file.
        """
        LOG.debug("Getting variable names from %s"%self.input_filename)
        nc = netCDF4.Dataset(self.input_filename)
        try:
            return {str(var) for var in nc.variables}
        finally:
            nc.close()

