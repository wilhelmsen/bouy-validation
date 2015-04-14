# coding: utf-8
import logging
import datetime
import numpy as np
import netCDF4
import os
import datetimehelper
import filterhelper

# Define the logger
LOG = logging.getLogger(__name__)
class SatDataException(Exception):
    pass


def get_files_from_datadir(data_dir, date_from_including, date_to_excluding):
    """
    Getting the files from the data dir.
    It does a walk through the data dir and finds files that
    - Starts with a date in the specified date range.
    - Contains the string "-DMI-L4"
    - Ends with .nc
    """
    LOG.debug("Data dir: '%s'"%data_dir)
    LOG.debug("Date from: '%s'."%date_from_including)
    LOG.debug("Date to: '%s'."%date_to_excluding)

    # Make sure that date_from allways is before date_to.
    # Be aware of that this must be done in one step. If not a temp variable is needed.
    date_from_including, date_to_excluding = min(date_from_including, date_to_excluding), max(date_from_including, date_to_excluding)

    LOG.debug("Dates after min/max:")
    LOG.debug("Date from (including): '%s'."%date_from_including)
    LOG.debug("Date to: '%s'."%date_to_excluding)

    for root, dirs, files in os.walk(data_dir):
        LOG.debug("Looking for files in '%s'."%(os.path.abspath(root)))
        # Walk through every files/directories in the data_dir.
        # Filename example: 20150313000000-DMI-L4_GHRSST-SSTfnd-DMI_OI-NSEABALTIC-v02.0-fv01.0.nc.gz
        # f.endswith((".nc", ".nc.gz"))
        for filename in [f for f in files
                         if f.endswith(".nc")
                         and "-DMI-L4" in f
                         and date_from_including <= _get_date_from_filename(f) < date_to_excluding]:
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
        yield _get_date_from_filename(filename)


def _get_date_from_filename(filename):
    FILENAME_DATE_FORMAT = "%Y%m%d%H%M%S"
    return datetime.datetime.strptime(os.path.basename(filename).split("-")[0], FILENAME_DATE_FORMAT)

class SatelliteDataPoint(object):
    def __init__(self):
        # Make the data element ready.
        self.data = {}
    
    def append(self, key, value):
        """
        Appends a key-value-pair to a datapoint.
        """
        self.data[key] = value

    def filter(self, order=None, ignore_point_if_missing=False):
        """
        Returns a string with the values corresponding to what is given in order.
        If order is None, all the values are written.

        Order can be either a list ["lat", "lon"] or a string with one key "lat".
        """
        # If one of the values are missing, and the filter is to ignore the missing values,
        # None is returned at once.
        for key, value in self.data.iteritems():
            if ignore_point_if_missing and hasattr(variable, "mask"):
                if variable.mask:
                    return None
        values = []

        # If the datapoint is actually filtered.
        if order != None:
            LOG.debug("Order:")
            LOG.debug(order)
            if isinstance(order, str):
                order = [order, ] 
            for key in order:
                if ":" in key:
                    key, extra_filter_option = key.split(":", 1)
                if key == "time":
                    if extra_filter_option == "julian":
                        values.append(datetimehelper.date2julian(self.data[key]))
                    elif extra_filter_option != "":
                        values.append(self.data[key].strftime(extra_filter_option))
                    else:
                        values.append(self.data[key].strftime(datetimehelper.DEFAULT_DATE_FORMAT_MIN))
                elif key == "dummy":
                    values.append(extra_filter_option)
                else:
                    values.append(self.data[key])

        # No filtering. All data is written.
        else:
            for key in self.data:
                if key == "time":
                    values.append(self.data[key].strftime(datetimehelper.DEFAULT_DATE_FORMAT_MIN))
                else:
                    values.append((self.data[key]))

        # Return a string with all the values.
        output = ""
        for value in values:
            output += filterhelper.format(value)
        return output

    def __str__(self):
        return self.filter()



class Satellite(object):
    def __init__(self, input_filename):
        self.input_filename = input_filename
        self.nc = netCDF4.Dataset(self.input_filename)
        
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.nc and self.nc != None:
            self.nc.close()

    def get_date(self):
        return _get_date_from_filename(self.input_filename)

    def has_variables(self, required_variables):
        """
        Makes sure that the variables in the "required_variables"
        can actually be found in the file.
        """
        LOG.debug("Required variables: %s"%(required_variables))
        if isinstance(required_variables, str):
            required_variables = (required_variables,)

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

        lat_index = abs((self.nc.variables['lat'] - np.float32(lat))).argmin()
        lon_index = abs((self.nc.variables['lon'] - np.float32(lon))).argmin()

        LOG.debug("Lat index: %i. Lat: %f."%(lat_index, self.nc.variables['lat'][lat_index]))
        LOG.debug("Lon index: %i. Lon: %f."%(lon_index, self.nc.variables['lon'][lon_index]))
        return lat_index, lon_index

    def data(self, lat, lon):
        """
        Getting the values (datapoint) for the specified lat / lon values.
        It gets the indexes closest to lat/lon and returns a SatelliteDataPoint with the values.
        """
        # Get the closes indexes for the lat lon.
        LOG.debug("Getting the values from the file.")

        LOG.debug("Getting the indexes for lat/lon: %f/%f"%(lat, lon))
        lat_index, lon_index = self.get_closest_lat_lon_indexes(lat, lon)

        LOG.debug("The lat/lo indexes for %f/%f were: %i, %i"%(lat, lon, lat_index, lon_index))

        data_point = SatelliteDataPoint()
        # Add the values to the datapoint.
        for variable_name in self.get_variable_names():
            LOG.debug("Adding variable name: %s."%(variable_name))
            if variable_name == "lat":
                variable_value = self.nc.variables[variable_name][lat_index]
            elif variable_name == "lon":
                variable_value = self.nc.variables[variable_name][lon_index]
            elif variable_name == "time":
                # The time variable is seconds since 1981-01-01.
                start_date = datetime.datetime(1981, 1, 1)
                variable_value = (start_date + datetime.timedelta(seconds=int(self.nc.variables['time'][0])))
            elif variable_name == "analysed_sst":
                variable_value = float(self.nc.variables[variable_name][0][lat_index][lon_index]) - 273.15
            else:
                variable_value = self.nc.variables[variable_name][0][lat_index][lon_index]
            # Append the value to the datapoint.
            data_point.append(variable_name, variable_value)

        # All values has been inserted. Return the point.
        return data_point

    def get_lat_lon_ranges(self):
        """
        Getting the lat long ranges from a input file.
        
        Opens the file, reads the lat/lon arrays and finds the min/max values.
        """
        return [min(self.nc.variables['lat']), max(self.nc.variables['lat'])], [min(self.nc.variables['lon']), max(self.nc.variables['lon'])]

    def get_variable_names(self):
        """
        Gets the variable names in the file. That means the variables that can be read from the file.
        """
        LOG.debug("Getting variable names from %s"%self.input_filename)
        return {str(var) for var in self.nc.variables}

