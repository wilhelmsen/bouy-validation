#!/usr/bin/env python
# coding: utf-8
import logging
import datetime
import sys
import os
import satellite

LOG = logging.getLogger(__name__)



if __name__ == "__main__":
    try:
        import argparse
    except Exception, e:
        print ""
        print "Try running 'sudo apt-get install python-argparse' or 'sudo easy_install argparse'!!"
        print ""
        raise e

    def date( date_string ):
        return datetime.datetime.strptime(date_string, '%Y-%m-%d').date()

    def directory(path):
        if not os.path.isdir(path):
            raise argparse.ArgumentTypeError("'%s' does not exist. Please specify save directory!"%(path))
        return path

    def file(path):
        if not os.path.isfile(path):
            raise argparse.ArgumentTypeError("'%s' does not exist. Please specify input file!"%(path))
        return path

    parser = argparse.ArgumentParser(description='Print the data point for a specified lat / lon.')
    parser.add_argument('--data-dir', type=directory, help='Specify the directory where the data files can be found. Ignored if --input-filename is set. It still must exist, though. The files in the data dir must be of the form "<YYYYMMDD>000000-DMI-L4*.nc", e.g: "20150310000000-DMI-L4_GHRSST-SSTfnd-DMI_OI-NSEABALTIC-v02.0-fv01.0.nc".', default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sat"))


    parser.add_argument('--print-variables', action="store_true", help="Print the available variables.")
    parser.add_argument('--print-lat-lon-range', action="store_true", help="Print the max/min lat/lon values in the file.")
    parser.add_argument('--print-dates', action="store_true", help="Print the dates available in the data-dir. The dates are based on the file names in the data directory.")

    parser.add_argument('-f', '--filter', action="append", nargs="*", help="Only return a string with some of the values. Based on the header file. --print-variables to see the available filter options.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--debug', action='store_true', help="Output debugging information.")
    group.add_argument('-v', '--verbose', action='store_true', help="Output info.")

    parser.add_argument('--log-filename', type=str, help="File used to output logging information.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--input-filename', type=file, help="Input filename.")
    group.add_argument('--date', type=date, help='Only print data values from (including) this date.', default=datetime.datetime.now().date())
    group.add_argument('--date-from', type=date, help='Only print data values from (including) this date.')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--date-to', type=date, help='Only print data untill (exclusive) this date.')
    group.add_argument('--days-back-in-time', type=int, help='Only print data from --date or --date-from and this number of days back in time.')
    group.add_argument('--days-forward-in-time', type=int, help='Only print data from --date or --date-from and this number of days forward in time.')

    parser.add_argument("--ignore-if-missing", action="store_true", help="Add this option to print the values only if there are NO missing values for the specified lat/lon values.")
    parser.add_argument("--lat", type=float, help="Specify which latitude value to use.")
    parser.add_argument("--lon", type=float, help="Specify which longitude value to use get.")
     
    # Do the parsing.
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
            args.date_to = args.date + datetime.timedelta(days = args.days_forward_in_time)
        # if date_to has not been set by the two above:
        if not args.date_to:
            # Date is set one day forward.
            args.date_to = args.date + datetime.timedelta(days = 1)

        input_files = list(satellite.get_files_from_datadir(args.data_dir, args.date, args.date_to))

    if len(input_files) == 0:
        print "No files to get data from. Please specify another date (--date) or date range (--date-from/--date-to)."
        print "Use --help for details."
        print ""
        print "Data dir: '%s'."%(os.path.abspath(args.data_dir))

    LOG.debug("Date from: %s. Date to: %s."%(args.date, args.date_to))

    try:
        # Print the dates availabe by filenames (in the datadir).
        if args.print_dates or len(input_files) == 0:
            assert(os.path.isdir(args.data_dir))
            date_strings = [date.strftime("%Y-%m-%d") for date in satellite.get_available_dates(args.data_dir)]
            date_strings.sort()
            print "Available dates:"
            print ", ".join(date_strings)
            if len(input_files) == 0:
                sys.exit(1)
            sys.exit()

        # print lat/lon ranges.
        if args.print_lat_lon_range:
            for input_filename in input_files:
                lats, lons = satellite.get_lat_lon_ranges(input_filename)
                print ""
                print "Filename: '%s'"%(input_filename)
                print "Lats: %s"%(" - ".join([str(lat) for lat in lats]))
                print "Lons: %s"%(" - ".join([str(lon) for lon in lons]))
            sys.exit()

        # Print variable names.
        if args.print_variables:
            for input_filename in input_files:
                variable_names = satellite.get_variable_names(input_filename)
                print "Available variables for %s:"%(input_filename)
                print "'%s'"%("', '".join(variable_names))
                sys.exit()


        if args.lat == None or args.lon == None:
            raise argparse.ArgumentTypeError("Both lat ('%s') and lon ('%s') must be set to extract the variables!"%(args.lat, args.lon))

        # Print the values.
        for input_filename in input_files:
            assert(satellite.variables_is_in_file(["lat", "lon"], input_filename))

            # Filtering.
            # It was not really possible to create a default filter with argparse. The new filter variables were inserted
            # into a new list, alongside the default list.
            variables_to_print = []
            if args.filter == None:
                args.filter = [None,]
                variables_to_print = satellite.get_variable_names(input_filename)
            else:
                # Just make sure the filter variable is a list, and not a str, e.g.
                assert(isinstance(args.filter, list))
                variables_to_print = args.filter[0]

            assert(satellite.variables_is_in_file(list(variables_to_print), input_filename))
            print "# %s"%(" ".join(variables_to_print))

            values = satellite.get_values(input_filename, args.lat, args.lon, variables_to_print, ignore_if_missing=args.ignore_if_missing)
            if values != None:
                print " ".join(values)
            else:
                print values
            sys.exit()
                


    except argparse.ArgumentTypeError, e:
        print("")
        print("Error: %s"%(e.message))
        sys.exit(1)
