#!/usr/bin/env python
# coding: utf-8
import logging
import datetime
import sys
import os
import satellite
import buoy

LOG = logging.getLogger(__name__)



if __name__ == "__main__":
    import argparse

    def date(date_string):
        return datetime.datetime.strptime(date_string, '%Y-%m-%d')

    def directory(path):
        if not os.path.isdir(path):
            raise argparse.ArgumentTypeError("'%s' does not exist. Please specify save directory!"%(path))
        return path

    def file(path):
        if not os.path.isfile(path):
            raise argparse.ArgumentTypeError("'%s' does not exist. Please specify input file!"%(path))
        return path

    parser = argparse.ArgumentParser(description='Compare the satellite data with the buoy data.')
    parser.add_argument('--data-dir-sat', type=directory, help='Specify the directory where the satellite data files can be found.', default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sat"))
    parser.add_argument('--data-dir-buoy', type=directory, help='Specify the directory where the buoy data files can be found.', default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "buoy"))
    parser.add_argument("-b", "--buoy", type=str, help="Buoy short name. Can be found by calling script with option --print-buoy-names.")

    parser.add_argument('--print-buoy-names', action='store_true', help="Print available buoy snort names to use with --buoy.")

    parser.add_argument('-f', '--filter', action="append", nargs="*", help="Only return a string with some of the values.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--debug', action='store_true', help="Output debugging information.")
    group.add_argument('-v', '--verbose', action='store_true', help="Output info.")

    parser.add_argument('--log-filename', type=str, help="File used to output logging information.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--sat-input-filename', type=file, help="Input filename. This is a satellite data filename..")
    group.add_argument('--date', type=date, help='Only print data values from (including) this date.', default=datetime.datetime.now())
    group.add_argument('--date-from', type=date, help='Only print data values from (including) this date.')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--date-to', type=date, help='Only print data untill (exclusive) this date.')
    group.add_argument('--days-back-in-time', type=int, help='Only print data from --date or --date-from and this number of days back in time.')
    group.add_argument('--days-forward-in-time', type=int, help='Only print data from --date or --date-from and this number of days forward in time.')

    parser.add_argument("--ignore-if-missing", action="store_true", help="Add this option to print the values only if there are NO missing values for the specified lat/lon values.")
     
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

    if args.print_buoy_names:
        print "Available buoy names:"
        print ", ".join(buoy.get_buoy_names(args.data_dir_buoy))
        sys.exit()

    buoy_names = buoy.get_buoy_names(args.data_dir_buoy)
    if args.buoy != None:
        if args.buoy not in buoy_names:
            raise argparse.ArgumentTypeError("'%s' can not be found. Please specify another buoy data dir (current: '%s') with --data-dir-buoy, or select one of the buoy names: '%s'!"%(args.buoy, args.data_dir_buoy, "', '".join(buoy_names)))
        buoy_names = [args.buoy,]
    

    if args.sat_input_filename:
        sat_input_filenames = [args.sat_input_filename,]
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
            # Date is set to five days back in time.
            args.date_to = args.date - datetime.timedelta(days = 5)

        sat_input_filenames = list(satellite.get_files_from_datadir(args.data_dir_sat, args.date, args.date_to))

    if len(sat_input_filenames) == 0:
        print "No satellite files to get data from. Please specify another date (--date) or date range (--date-from/--date-to)."
        print "Use --help for details."
        print ""
        print "Satellite data dir: '%s'."%(os.path.abspath(args.data_dir_sat))
        sys.exit(1)

    LOG.debug("Date from: %s. Date to: %s."%(args.date, args.date_to))

    try:
        for sat_input_filename in sat_input_filenames:
            assert(satellite.variables_is_in_file(["lat", "lon"], sat_input_filename))
            LOG.debug("Satellite intput filename: %s"%(sat_input_filename))
            satellite_date = satellite.get_date_from_filename(sat_input_filename)

            date_from_including = satellite_date - datetime.timedelta(hours=12)
            date_to_excluding = satellite_date + datetime.timedelta(hours=12)

            for buoy_name in buoy_names:
                LOG.debug("Buoy short name: %s. Satellite date: %s."%(buoy_name, satellite_date))

                b = buoy.Buoy(buoy_name, args.data_dir_buoy)
                sat_data = satellite.get_values(sat_input_filename, b.lat, b.lon, ignore_if_missing=args.ignore_if_missing)
                
                # import pdb; pdb.set_trace()
                for buoy_data in b.data(date_from_including, date_to_excluding):
                    print buoy_data.filter(["date:",]), buoy_data.filter(["WT:2",]), " ".join(sat_data)
                
            sys.exit()

            # Filtering.
            # It was not really possible to create a default filter with argparse. The new filter variables were inserted
            # into a new list, alongside the default list.
            variables_to_print = []
            if args.filter == None:
                args.filter = [None,]
                variables_to_print = satellite.get_variable_names(sat_input_filename)
                variables_to_print = ["s:%s"%x for x in variables_to_print]
            else:
                # Just make sure the filter variable is a list, and not a str, e.g.
                assert(isinstance(args.filter, list))
                variables_to_print = args.filter[0]

            # Printing the header.
            assert(satellite.variables_is_in_file(list(variables_to_print), sat_input_filename))
            print "# %s"%(" ".join(variables_to_print))

            values = satellite.get_values(sat_input_filename, args.lat, args.lon, variables_to_print, ignore_if_missing=args.ignore_if_missing)
            if values != None:
                print " ".join(values)
            else:
                print values
            sys.exit()
                


    except argparse.ArgumentTypeError, e:
        print("")
        print("Error: %s"%(e.message))
        sys.exit(1)
