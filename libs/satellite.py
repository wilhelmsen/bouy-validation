# coding: utf-8
import logging
import datetime
import numpy as np
import numpy.ma as ma
import netCDF4
import os
import datetimehelper
import filterhelper
import coordinatehelper
import math

# Define the logger
LOG = logging.getLogger(__name__)
ZERO_CELCIUS_IN_KELVIN = 273.15

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
        Time is only one dimension in the files, so we need the lat / lon indexes.
        
                          LON
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  |
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  | LAT
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  |
        +-----+-----+-----+-----+-----+-----+

        The lat/lon points are the center values in the grid cell.
        """
        # lat / lon extremes including the edges.
        lats, lons = self.get_lat_lon_ranges()
    
        # Make sure the lat/lon values are within the ranges where there are data.
        # lat[0] - grid_cell_height/2, lat[1] + grid_cell_height/2
        if not lats[0] <= lat <= lats[1]:
            raise SatDataException("Latitude %s is outside latitude range %s."%(lat, " - ".join([str(l) for l in lats])))
    
        # lon[0] - grid_cell_width/2, lon[1] + grid_cell_width/2
        if not lons[0] <= lon <= lons[1]:
            raise SatDataException("Longitude %s is outside longitude range %s."%(lon, " - ".join([str(l) for l in lons])))

        lat_index = self.get_index_of_closest_float_value('lat', lat) 
        lon_index = self.get_index_of_closest_float_value('lon', lon)

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
                variable_value = float(self.nc.variables[variable_name][0][lat_index][lon_index]) - ZERO_CELCIUS_IN_KELVIN

            elif variable_name == "analysed_sst_smooth":
                variable_value = self.calculate_analysed_sst_smooth(lat, lon) - ZERO_CELCIUS_IN_KELVIN

            elif variable_name == "dist2ice":
                variable_value = self.calculate_distance_to_ice(lat, lon)

            else:
                variable_value = self.nc.variables[variable_name][0][lat_index][lon_index]
            # Append the value to the datapoint.
            data_point.append(variable_name, variable_value)

        # All values has been inserted. Return the point.
        return data_point

    def get_lat_index(self, lat):
        """
        Gets the index of the closest lat value.
        """
        return get_index_of_closest_float_value("lat", lat)

    def get_lon_index(self, lon):
        """
        Gets the index of the closest lon value.
        """
        return get_index_of_closest_float_value("lon", lon)

    def get_index_of_closest_float_value(self, variable_name, value):
        """
        Gets the index of the closest float value.
        """
        return abs((self.nc.variables[variable_name] - np.float32(value))).argmin()

    def calculate_analysed_sst_smooth(self, lat, lon, analysed_sst_smooth_radius_km=25):
        """
        Gets the average analysed_sst within a squared grid (km).


                         LON
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  |
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  | LAT
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  |
        +-----+-----+-----+-----+-----+-----+

        """
        delta_lat = coordinatehelper.km_2_lats(analysed_sst_smooth_radius_km)
        delta_lon = coordinatehelper.km_2_lons(analysed_sst_smooth_radius_km, lat)

        # Mask everything outside latitude interval.
        lat_mask = (self.nc.variables['lat'][:] >= lat-delta_lat) & (self.nc.variables['lat'][:] <= lat+delta_lat)
        lon_mask = (self.nc.variables['lon'][:] > lon-delta_lon) & (self.nc.variables['lon'][:] < lon+delta_lon)
        
        # Combine the lat mask with the lon mask.
        lat_lon_mask = np.reshape([i&j for i in lat_mask for j in lon_mask], (len(lat_mask), len(lon_mask)))

        # The values must be from water. That means that bit 1 must be set in the land/sea-mask.
        # The result is an array with 1s and 0s. It is converted to an array of bools.
        sea_mask = np.array((self.nc.variables['mask'][0] & 1), dtype=bool)

        # The resulting mask. Both True values from lat_lon and True values from the land/sea mask.
        resulting_mask = lat_lon_mask & sea_mask

        # Get the values
        data = self.nc.variables['analysed_sst'][0]

        # Add the original mask.
        data.mask = ~resulting_mask | data.mask
        return data.mean()


    def calculate_distance_to_ice(self, lat, lon, output_ice_point_to_log_info=False):
        """
        Finds the minimum distance to ice.

                         LON
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  |
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  | LAT
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  |
        +-----+-----+-----+-----+-----+-----+

        """
        MAX_DISTANCE_KM=500
        NO_ICE_DISTANCE_KM=1000

        MIN_SEA_ICE_FRACTION=0.15

        LOG.debug("Icemask where sea ice fraction is > %f "%(MIN_SEA_ICE_FRACTION))
        sea_ice_fraction_mask = self.nc.variables['sea_ice_fraction'][0] > MIN_SEA_ICE_FRACTION

        LOG.debug("The sea mask: Where the first bit in the 'mask' variable (nc file) is set")
        sea_mask = np.array((self.nc.variables['mask'][0] & 1), dtype=bool)

        LOG.debug("Combine sea mask and sea ice fraction mask into sea ice mask.")
        sea_ice_mask = sea_ice_fraction_mask & sea_mask

        # Creating a matrix with very large values.
        # This will be used to fill in the values distance values.
        distances_km = np.empty(sea_ice_mask.shape)
        distances_km.fill(MAX_DISTANCE_KM)
        
        if output_ice_point_to_log_info:
            # For book keeping.
            min_value = 500
            min_lat = None
            min_lon = None

        for lat_idx in np.arange(len(self.nc.variables['lat'])):
            if not sea_ice_mask[lat_idx].any():
                # If there are no ice in the sea for the current sea mask row,
                # go to the next row.
                continue

            # There ice values for this sea mask row.
            # Get the y component to the length to the latitude.
            latitude = self.nc.variables['lat'][lat_idx]
            y = coordinatehelper.lats_2_km(np.abs(latitude-lat))

            # Run through every point in the row and check if there is
            # any ice in that point.
            for lon_idx in np.arange(len(self.nc.variables['lon'])):
                # Is there ice in the point?
                if not sea_ice_mask[lat_idx][lon_idx]:
                    # No there were no ice.
                    continue

                # Yes there were ice.
                # Get the x component for the length to the ice point.
                longitude = self.nc.variables['lon'][lon_idx]
                x = coordinatehelper.lons_2_km(np.abs(longitude - lon), latitude)

                # Calculate the resulting distance.
                distances_km[lat_idx][lon_idx] = np.sqrt(x**2 + y**2)

                if output_ice_point_to_log_info and distances_km[lat_idx][lon_idx] < min_value:
                    min_value = distances_km[lat_idx][lon_idx]
                    min_lat = latitude
                    min_lon = longitude

        # The smallest distance to the ice.
        min_distance_km = distances_km.min()

        # Only when outputting the distance.
        if output_ice_point_to_log_info:
            LOG.info("dist2ice:(%s, %s) -> (%s, %s): %f km: "%(lat, lon, min_lat, min_lon, min_distance_km))

        # If the minimum distance is greater than the allowed (500 km), 
        # return a default value.
        if min_distance_km > MAX_DISTANCE_KM:
            LOG.debug("Returning default value: %s"%(NO_ICE_DISTANCE_KM))
            return NO_ICE_DISTANCE_KM

        # Else the minimum distance found is returned.
        return min_distance_km


    def get_lat_lon_ranges(self):
        """
        Getting the lat long ranges from a input file, including the extra area on the edges.
        
        Opens the file, reads the lat/lon arrays and finds the min/max values.

                         LON
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  |
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  | LAT
        +-----+-----+-----+-----+-----+-----+
        |  x  |  x  |  x  |  x  |  x  |  x  |
        +-----+-----+-----+-----+-----+-----+

        As the lat/lons are center values in the grid cells, the edges are added to the range.
        """
        lat_edge = self.nc.geospatial_lat_resolution/2.0
        lat_ranges = [min(self.nc.variables['lat']) - lat_edge,
                      max(self.nc.variables['lat']) + lat_edge]

        lon_edge = self.nc.geospatial_lon_resolution/2.0
        lon_ranges = [min(self.nc.variables['lon']) - lon_edge,
                      max(self.nc.variables['lon']) + lon_edge]

        return lat_ranges, lon_ranges 

    def get_variable_names(self):
        """
        Gets the variable names in the file. That means the variables that can be read from the file.
        """
        LOG.debug("Getting variable names from %s"%self.input_filename)
        variables = list(self.nc.variables)
        variables.append("analysed_sst_smooth")
        variables.append("dist2ice")
        return {str(var) for var in variables}
