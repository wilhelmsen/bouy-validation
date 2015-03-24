#!/usr/bin/env python
import logging
import datetime
import numpy as np

# Define the logger
LOG = logging.getLogger(__name__)
DATE_FORMAT = "%Y%m%d%H%M%S"

class SatDataException(Exception):
    pass


def get_files_from_datadir(data_dir, date_from, date_to):
    LOG.debug("Data dir: '%s'"%data_dir)
    LOG.debug("Date from: '%s'."%date_from)
    LOG.debug("Date to: '%s'."%date_to)

    # Make sure that date_from allways is before date_to.
    date_from = min(date_from, date_to)
    date_to   = max(date_from, date_to)

    for root, dirs, files in os.walk(data_dir):
        # 20150313000000-DMI-L4_GHRSST-SSTfnd-DMI_OI-NSEABALTIC-v02.0-fv01.0.nc.gz
        for filename in [f for f in files if f.endswith((".nc", ".nc.gz"))
                         and "-DMI-L4" in f
                         and date_from <= datetime.datetime.strptime(f.split("-")[0], DATE_FORMAT).date() <= date_to]:
            yield os.path.abspath(os.path.join(root, filename))
            

def get_lat_lon_ranges(input_filename):
    nc = netCDF4.Dataset(input_filename)
    try:
        return [min(nc.variables['lat']), max(nc.variables['lat'])], [min(nc.variables['lon']), max(nc.variables['lon'])]
    finally:
        nc.close()

def get_variable_names(input_filename):
    LOG.debug("Getting variable names from %s"%input_filename)
    nc = netCDF4.Dataset(input_filename)
    try:
        return {str(var) for var in nc.variables}
    finally:
        nc.close()

def variables_is_in_file(required_variables, input_filename):
    assert(isinstance(required_variables, list))

    variable_names = get_variable_names(input_filename)
    for required_variable in required_variables:
        if required_variable not in variable_names:
            LOG.warning("The file, '%s', must have the variable '%s'."%(input_filename, required_variable))
            return False
    return True

def get_available_dates(data_dir):
    date_from = datetime.datetime(1981, 1, 1).date()
    date_to = datetime.datetime.now().date() + datetime.timedelta(days = 1)
    for filename in get_files_from_datadir(data_dir, date_from, date_to):
        yield datetime.datetime.strptime(os.path.basename(filename).split("-")[0], "%Y%m%d%H%M%S").date()


def get_closest_lat_lon_indexes(input_filename, lat, lon):
    LOG.debug("Filename: %s"%(input_filename))
    lats, lons = get_lat_lon_ranges(input_filename)
    
    if not lats[0] <= lat <= lats[1]:
        raise SatDataException("Latitude %s is outside latitude range %s."%(lat, " - ".join([str(l) for l in lats])))
    if not lons[0] <= lon <= lons[1]:
        raise SatDataException("Longitude %s is outside longitude range %s."%(lon, " - ".join([str(l) for l in lons])))

    nc = netCDF4.Dataset(input_filename)
    try:
        return abs((nc.variables['lat'] - np.float32(lat))).argmin(), abs((nc.variables['lon'] - np.float32(lon))).argmin()
    finally:
        nc.close()


def get_values(input_filename, lat, lon, variables_to_print):
    # Get the closes indexes for the lat lon.
    if args.lat != None and args.lon != None:
        LOG.debug("Lat/lon: %f/%f"%(args.lat, args.lon))
        lat_index, lon_index = get_closest_lat_lon_indexes(input_filename, lat, lon)
        LOG.debug("Lat/lon indexes: %i, %i"%(lat_index, lon_index))
        
    # Do the work.
    nc = netCDF4.Dataset(input_filename)
    try:
        items_to_print = []
        for variable_name in variables_to_print:
            LOG.debug("Adding variable name: %s."%(variable_name))
            if variable_name == "lat":
                items_to_print.append(nc.variables['lat'][lat_index])
            elif variable_name == "lon":
                items_to_print.append(nc.variables['lon'][lat_index])
            elif variable_name == "time":
                start_date = datetime.datetime(1981, 1, 1)
                items_to_print.append((start_date + datetime.timedelta(seconds=int(nc.variables['time'][0]))))
            else:
                items_to_print.append(nc.variables[variable_name][0][lat_index][lon_index])
                        
        LOG.debug("Converting all items to string")
        items_to_print = map(lambda x: str(x), items_to_print)

        LOG.debug("Items to string")
        return items_to_print
    finally:
        nc.close()


if __name__ == "__main__":
    import sys
    import os
    import netCDF4
    import glob

    try:
        import argparse
    except Exception, e:
        print ""
        print "Try running 'sudo apt-get install python-argparse' or 'sudo easy_install argparse'!!"
        print ""
        raise e

    def date( date_string ):
        # argparse.ArgumentTypeError()
        return datetime.datetime.strptime( date_string, '%Y-%m-%d' ).date()

    def directory(path):
        if not os.path.isdir(path):
            raise argparse.ArgumentTypeError("'%s' does not exist. Please specify save directory!"%(path))
        return path

    def file(path):
        if not os.path.isfile(path):
            raise argparse.ArgumentTypeError("'%s' does not exist. Please specify input file!"%(path))
        return path

    parser = argparse.ArgumentParser(description='Some description. This script does this and that...')

    parser.add_argument('--print-variables', action="store_true", help="Print the available variables.")
    parser.add_argument('--print-lat-lon-range', action="store_true", help="Print the max and min lat/lon values in the file.")
    parser.add_argument('--print-available-dates', action="store_true", help="Print the dates available in the data-dir.")

    parser.add_argument('-f', '--filter', action="append", nargs="*", help="Only return a string with some of the values. Based on the header file. --print-variables to see the available filter options.")


    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--debug', action='store_true', help="Output debugging information.")
    group.add_argument('-v', '--verbose', action='store_true', help="Output info.")

    parser.add_argument('--log-filename', type=str, help="File used to output logging information.")


    group = parser.add_mutually_exclusive_group()
    group.add_argument('--input-filename', type=file, help="Input filename.")
    group.add_argument('--date', type=date, help='Only print data values from (including) this date.', default=datetime.datetime.now().date())
    group.add_argument('--date-from', type=date, help='Only print data values from (including) this date.')

    parser.add_argument('--data-dir', type=directory, help='Specify the directory where the data files can be found. Ignored if --input-filename is set. It still must exist, though.', default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sat"))

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--date-to', type=date, help='Only print data untill (exclusive) this date.')
    group.add_argument('--days-back-in-time', type=int, help='Only print data from --date or --date-from and this number of days back in time.')
    group.add_argument('--days-forward-in-time', type=int, help='Only print data from --date or --date-from and this number of days forward in time.')


    parser.add_argument("--lat", type=float, help="Specify which latitude value to use.")
    parser.add_argument("--lon", type=float, help="Specify which longitude value to use get.")
     

    # Do the parser.
    args = parser.parse_args()

    # Set the log options.
    if args.debug:
        logging.basicConfig(filename=args.log_filename, level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(filename=args.log_filename, level=logging.INFO)
    else:
        logging.basicConfig(filename=args.log_filename, level=logging.WARNING)

    # Output what is in the args variable.
    LOG.debug(args)

    if args.input_filename:
        input_files = [args.input_filename,]
    else:
        # Date is allways set to the date to start from.
        if args.date_from:
            args.date = args.date_from

        # Date to. 
        if args.days_back_in_time:
            args.date_to = args.date - datetime.timedelta(days = args.days_back_in_time)
        elif args.days_forward_in_time:
            args.date_to = args.date + datetime.timedelta(days = args.days_back_in_time)
        # if date_to has not been set by the two above:
        if not args.date_to:
            # Date is set one day forward.
            args.date_to = args.date + datetime.timedelta(days = 1)

        input_files = list(get_files_from_datadir(args.data_dir, args.date, args.date_to))

    if len(input_files) == 0:
        print "No files get data from... Please specify dates."

    LOG.debug("Date from: %s. Date to: %s."%(args.date, args.date_to))

    try:
        # Print the dates availabe by filenames (in the datadir).
        if args.print_available_dates or len(input_files) == 0:
            assert(os.path.isdir(args.data_dir))
            date_strings = [date.strftime("%Y-%m-%d") for date in get_available_dates(args.data_dir)]
            date_strings.sort()
            print "Available dates:"
            print ", ".join(date_strings)
            sys.exit()

        # print lat/lon ranges.
        if args.print_lat_lon_range:
            for input_filename in input_files:
                lats, lons = get_lat_lon_ranges(input_filename)
                print "Filename: '%s'"%(input_filename)
                print "Lats: %s"%(" - ".join([str(lat) for lat in lats]))
                print "Lons: %s"%(" - ".join([str(lon) for lon in lons]))
            sys.exit()

        # Print variable names.
        if args.print_variables:
            for input_filename in input_files:
                variable_names = get_variable_names(input_filename)
                print "Available variables for %s:"%(input_filename)
                print "'%s'"%("', '".join(variable_names))
                sys.exit()



        # Print the values.
        for input_filename in input_files:
            assert(variables_is_in_file(["lat", "lon"], input_filename))

            # Filtering.
            # It was not really possible to create a default filter with argparse. The new filter variables were inserted
            # into a new list, alongside the default list.
            variables_to_print = []
            if args.filter == None:
                args.filter = [None,]
                variables_to_print = get_variable_names(input_filename)
            else:
                # Just make sure the filter variable is a list, and not a str, e.g.
                assert(isinstance(args.filter, list))
                variables_to_print = args.filter[0]

            assert(variables_is_in_file(variables_to_print, input_filename))
            print "# %s"%(" ".join(variables_to_print))

            values = get_values(input_filename, args.lat, args.lon, variables_to_print)
            print values
            sys.exit()
                


    except argparse.ArgumentTypeError, e:
        print("")
        print("Error: %s"%(e.message))
        sys.exit(1)
