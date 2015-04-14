#!/usr/bin/env python
# coding: utf-8
import logging
import datetime
import sys
import os
import libs.satellite
import libs.buoy
import libs.datetimehelper
import libs.filterhelper

LOG = logging.getLogger(__name__)

def filename(date_from, date_to, buoy_name, depth, path=None):
    # L4_valid_$Buoy_$depth_20150406_20150407_NSB_0.02.asc
    filename = "L4_valid_{buoy}_{depth}_{date_from_including}_{date_to_excluding}_NSB_0.02.asc".format(
        buoy=buoy_name,
        depth=depth,
        date_from_including=date_from.strftime("%Y%d%m"),
        date_to_excluding=date_to.strftime("%Y%d%m")
        )
    if path != None:
        filename = os.path.join(path, filename)
    return os.path.abspath(filename)



if __name__ == "__main__":
    import argparse

    def date(date_string):
        return datetime.datetime.strptime(date_string, '%Y-%m-%d')

    def directory(path):
        if not os.path.isdir(path):
            raise argparse.ArgumentTypeError("'%s' does not exist. Please specify save directory!"%(path))
        return path

    def file(path):
        if not os.path.isdir(os.path.dirname(path)):
            raise argparse.ArgumentTypeError("Directory for '%s' does not exist. Please specify a valid path!"%(path))
        return path

    def existing_file(path):
        if not os.path.isfile(path):
            raise argparse.ArgumentTypeError("File '%s' does not exist. Please specify a valid input file!"%(path))
        return path

    def filter(filter_element):
        start_values = ["s:", "b:", "dummy:"]
        for start_value in start_values:
            if filter_element.startswith(start_value):
                return filter_element
        raise argparse.ArgumentTypeError("Filter element, '%s', must start with '%s'."%(filter_element, "', '".join(start_values)))

    parser = argparse.ArgumentParser(description='Compare the satellite data with the buoy data. For each file of satellite data, the specified buoy data is found. Each line in the buoy data is compared with the satellite.')

    parser.add_argument('--data-dir-sat', type=directory, help='Specify the directory where the satellite data files can be found.', default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sat"))
    parser.add_argument('--data-dir-buoy', type=directory, help='Specify the directory where the buoy data files can be found.', default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "buoy"))

    parser.add_argument('--print-buoy-names', action='store_true', help="Print available buoy snort names to use with --buoy.")
    parser.add_argument('-b', '--buoy', type=str, help="Buoy short name. Can be found by calling script with option --print-buoy-names. This is actually a required option, even though an option should be optional, by definition.")


    parser.add_argument('--print-header', action='store_true', help="Print the header when writing the output.")
    parser.add_argument('-f', '--filter', type=filter, action="append", nargs="*", help="""Only return a string with some of the values. Example: 's:lat b:WT:2 s:lon b:date:'. 's' is the satellite prefix and 'b' is the buoy prefix. 2 values for each satellite filter element, and 3 values for each buoy filter element.""")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--debug', action='store_true', help="Output debugging information.")
    group.add_argument('-v', '--verbose', action='store_true', help="Output info.")

    parser.add_argument('--log-filename', type=str, help="File used to output logging information.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--sat-input-filename', type=existing_file, help="Input filename. This is a satellite data filename..")
    group.add_argument('--date', type=date, help='Only print data values from (including) this date.', default=datetime.datetime.now())
    group.add_argument('--date-from', type=date, help='Only print data values from (including) this date.')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--date-to', type=date, help='Only print data untill (exclusive) this date.')
    group.add_argument('--days-back-in-time', type=int, help='Only print data from --date or --date-from and this number of days back in time.')
    group.add_argument('--days-forward-in-time', type=int, help='Only print data from --date or --date-from and this number of days forward in time.')

    parser.add_argument("--ignore-if-missing", action="store_true", help="Add this option to print the values only if there are NO missing values for the specified lat/lon values.")

    parser.add_argument('-o', '--output-filename', type=file, help="Output filename. If not given, a filename will be created.")
    parser.add_argument('--overwrite', action='store_true', help="Overwrite existing files.")

     
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
        print "Available buoy names for '%s':"%(os.path.abspath(args.data_dir_buoy))
        print ", ".join(libs.buoy.get_buoy_names(args.data_dir_buoy))
        sys.exit()

    buoy_names = libs.buoy.get_buoy_names(args.data_dir_buoy)
    if args.buoy != None:
        if args.buoy not in buoy_names:
            raise argparse.ArgumentTypeError("'%s' can not be found. Please specify another buoy data dir (current: '%s') with --data-dir-buoy, or select one of the buoy names: '%s'!"%(args.buoy, args.data_dir_buoy, "', '".join(buoy_names)))
        buoy_names = [args.buoy,]
    else:
        raise argparse.ArgumentTypeError("Please specify buoy name. Available buoy names for '%s' are: '%s'"%(args.data_dir_buoy, "', '".join(buoy_names)))

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
            args.date_to = args.date + datetime.timedelta(days = 1)

        sat_input_filenames = list(libs.satellite.get_files_from_datadir(args.data_dir_sat, args.date, args.date_to))

    if len(sat_input_filenames) == 0:
        print "No satellite files to get data from. Please specify another date (--date) or date range (--date-from/--date-to)."
        print "Use --help for details."
        print ""
        print "Satellite data dir: '%s'."%(os.path.abspath(args.data_dir_sat))
        sys.exit(1)

    LOG.debug("Date from: %s. Date to: %s."%(args.date, args.date_to))


    try:
        # Make sure the output file does not exist, or deleted if specified.
        if args.output_filename and os.path.isfile(args.output_filename):
            if args.overwrite:
                os.remove(args.output_filename)
            else:
                raise argparse.ArgumentTypeError("File '%s' may not exist. Please delete first, or use option --overwrite!"%(args.output_filename))

        # Get the data.
        for sat_input_filename in sat_input_filenames:
            with libs.satellite.Satellite(sat_input_filename) as sat:
                assert(sat.has_variables(["lat", "lon"]))

                # Make sure the satellite variables are there.
                if args.filter != None:
                    for f in args.filter[0]:
                        if f.startswith("s:"):
                            dummy, sat_filter = f.split(":", 1)
                            if sat_filter.startswith("time:"):
                                sat_filter, date_format = sat_filter.split(":",)
                            if not sat.has_variables(sat_filter):
                                raise argparse.ArgumentTypeError("'%s' cannot be found for satellite data. Must be one of '%s'."%(sat_filter, "', '".join(sat.get_variable_names())))
                                

                # Get the date from the satellite file.
                LOG.debug("Satellite intput filename: %s"%(sat_input_filename))
                satellite_date = sat.get_date()

                # Calculate the valid time period for the file.
                date_from_including = satellite_date - datetime.timedelta(hours=12)
                date_to_excluding = satellite_date + datetime.timedelta(hours=12)

                # Loop through the available buoys and write the output.
                for buoy_name in buoy_names:
                    LOG.debug("Buoy short name: %s. Satellite date: %s."%(buoy_name, satellite_date))
                    with libs.buoy.Buoy(buoy_name, args.data_dir_buoy) as b:
                        if args.filter != None: 
                            for f in args.filter[0]:
                                if f.startswith("b:"):
                                    dummy, buoy_filter = f.split(":", 1)
                                    if buoy_filter.startswith("date:"):
                                        buoy_filter, dateformat = buoy_filter.split(":", 1)
                                        buoy_filter = "%s:"%buoy_filter
                                    if buoy_filter != "lat" and buoy_filter != "lon" and not b.has_variables(buoy_filter):
                                        raise argparse.ArgumentTypeError("'%s' cannot be found for buoy '%s' ('%s'). Must be one of '%s'."%(buoy_filter, b.name, b.short_name, "', '".join(b.get_header_strings())))


                        # Print the header.
                        if args.print_header:
                            # Create the header.
                            if args.filter != None:
                                header = " ".join(args.filter[0])
                            else:
                                header = "b:%s s:%s"%(" b:".join(b.get_header_strings()), " s:".join(sat.get_variable_names()))

                            # Make the output.
                            if args.output_filename:
                                with open(args.output_filename, 'w') as fp:
                                    fp.write(header)
                            else:
                                print header
                                
                        # Selecting the satellite data from the buoy lat/lon values.
                        sat_data = sat.data(b.lat, b.lon)

                        # Looping over buoy data that correspond to the satellite data.
                        for buoy_data in b.data(date_from_including, date_to_excluding):
                            # If the data is not filtered, just write erything.
                            if args.filter == None:
                                output = "%s %s"%(buoy_data, sat_data)
                            else:
                                output_parts = []
                                for f in args.filter[0]:
                                    LOG.debug("FILTER: %s"%(f))
                                    filter_type, filter_value = f.split(":", 1)
                                    if filter_type == "s":
                                        output_parts.append(sat_data.filter(filter_value))
                                    elif filter_type == "b":
                                        output_parts.append(buoy_data.filter(filter_value))
                                    elif filter_type == "dummy":
                                        output_parts.append(libs.filterhelper.format(filter_value))
                                output = " ".join(output_parts)

                            # Output the content...
                            if args.output_filename:
                                # ...to file.
                                with open(args.output_filename, 'a') as fp:
                                    fp.write(output+"\n")
                            else:
                                # ...to screen.
                                print output

    # If something went wrong.
    except argparse.ArgumentTypeError, e:
        print("")
        print("Error: %s"%(e.message))
        sys.exit(1)
