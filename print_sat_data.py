#!/usr/bin/env python
# coding: utf-8
import logging
import datetime
import sys
import os
import libs.satellite

LOG = logging.getLogger(__name__)

def get_available_date_strings(data_dir):
        assert(os.path.isdir(data_dir))
        date_strings = [date.strftime("%Y-%m-%d") for date in libs.satellite.get_available_dates(data_dir)]
        date_strings.sort()
        LOG.info("Available dates:")
        return date_strings

def pick_any_file(data_dir):
    # There are no satellite files before this date. :)
    date_from_including = datetime.datetime(1900, 1, 1)
    
    # Probably no files from tomorrow today?
    date_to_excluding = datetime.datetime.now() + datetime.timedelta(days=1)
        
    # Just pick the first file (it's a generator).
    return libs.satellite.get_files_from_datadir(data_dir, date_from_including, date_to_excluding).next()



if __name__ == "__main__":
    try:
        import argparse
    except Exception, e:
        print ""
        print "Try running 'sudo apt-get install python-argparse' or 'sudo easy_install argparse'!!"
        print ""
        raise e

    def date( date_string ):
        return datetime.datetime.strptime(date_string, '%Y-%m-%d')

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
    parser.add_argument('--print-lat-lon-ranges', action="store_true", help="Print the max/min lat/lon values in the file.")
    parser.add_argument('--print-dates', action="store_true", help="Print the dates available in the data-dir. The dates are based on the file names in the data directory.")

    parser.add_argument('-f', '--filter', action="append", nargs="*", help="Only return a string with some of the values. Based on the header file. --print-variables to see the available filter options.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--debug', action='store_true', help="Output debugging information.")
    group.add_argument('-v', '--verbose', action='store_true', help="Output info.")

    parser.add_argument('--log-filename', type=str, help="File used to output logging information.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--input-filename', type=file, help="Input filename.")
    group.add_argument('--date', type=date, help='Only print data values from (including) this date.', default=datetime.datetime.now())
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

    # Print the dates availabe by filenames (in the datadir).
    if args.print_dates:
        for date_string in get_available_date_strings(args.data_dir):
            print date_string
        sys.exit()

    # Either a input file has been specified,
    # or it is determined by the date values.
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

        LOG.debug("Data dir: %s. Date from: %s. Date to: %s"%(args.data_dir, args.date, args.date_to))
        input_files = list(libs.satellite.get_files_from_datadir(args.data_dir, args.date, args.date_to))

    # Print the varialbes.
    if args.print_variables:
        if len(input_files) == 0:
            # If the dates have not been specified, then there may be that there are no files to
            # pick the variables from, as the dates have default values.
            # Then just pick a file from the data dir and print the variables for that file.
            input_filename = pick_any_file(args.data_dir)
        else:
            input_filename = input_files[-1]

        LOG.info("Available variables for %s:"%(input_filename))
        with libs.satellite.Satellite(input_filename) as sat:
            variable_names = sat.get_variable_names()
        print "'%s'"%("', '".join(variable_names))
        sys.exit()

    # Print lat/lon ranges.
    if args.print_lat_lon_ranges:
        if len(input_files) == 0:
            input_filename = pick_any_file(args.data_dir)
        else:
            input_filename = input_files[-1]

        with libs.satellite.Satellite(input_filename) as sat:
            lats, lons = sat.get_lat_lon_ranges()
        LOG.info("")
        LOG.info("Filename: '%s'"%(input_filename))
        print "Lats: %s"%(" - ".join([str(lat) for lat in lats]))
        print "Lons: %s"%(" - ".join([str(lon) for lon in lons]))
        sys.exit()


    # In the case that there still are no files,
    # print the available dates, where there are some files.
    if len(input_files) == 0:
        print "No files to get data from. Please specify another date (--date) or date range (--date-from/--date-to)."
        if args.date:
            print "Date from: '%s'."%(args.date.date()) 
        if args.date:
            print "Date to: '%s'."%(args.date_to.date())
        print ""
        print "Use --help for details."
        print ""
        print "'%s'"%("', '".join(get_available_date_strings(args.data_dir)))
        print ""
        print "Data dir: '%s'."%(os.path.abspath(args.data_dir))
        sys.exit(1)

    LOG.debug("Date from: %s. Date to: %s."%(args.date, args.date_to))
    try:


        if args.lat == None or args.lon == None:
            raise argparse.ArgumentTypeError("Both lat ('%s') and lon ('%s') must be set to extract the variables!\nUse --print-lat-lon-ranges to see available lat/lon values for the given date."%(args.lat, args.lon))

        # Print the values.
        for input_filename in input_files:
            with libs.satellite.Satellite(input_filename) as sat:
                assert(sat.has_variables(["lat", "lon"]))

                # Filtering.
                # It was not really possible to create a default filter with argparse. The new filter variables were inserted
                # into a new list, alongside the default list.
                variables_to_print = []
                if args.filter == None:
                    args.filter = [None,]
                    variables_to_print = sat.get_variable_names()
                else:
                    # Just make sure the filter variable is a list, and not a str, e.g.
                    assert(isinstance(args.filter, list))
                    variables_to_print = args.filter[0]

                assert(sat.has_variables(list(variables_to_print)))
                print "# %s"%(" ".join(variables_to_print))

                values = sat.data(args.lat, args.lon)
                if values != None:
                    print values.filter(variables_to_print, args.ignore_if_missing)
                else:
                    print values
                sys.exit()

    except argparse.ArgumentTypeError, e:
        print("")
        print("Error: %s"%(e.message))
        sys.exit(1)
