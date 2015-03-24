#!/usr/bin/env python
import logging

# Define the logger
LOG = logging.getLogger(__name__)

if __name__ == "__main__":
    import sys
    import buoy
    import os
    import datetime
    try:
        import argparse
    except Exception, e:
        print ""
        print "Try running 'sudo apt-get install python-argparse' or 'sudo easy_install argparse'!!"
        print ""
        raise e

    def date( date_string ):
        # argparse.ArgumentTypeError()
        return datetime.datetime.strptime( date_string, '%Y-%m-%d' )

    def directory( dir_path ):
        if not os.path.isdir( dir_path ):
            raise argparse.ArgumentTypeError( "'%s' does not exist. Please specify save directory!"%(dir_path))
        return dir_path

    parser = argparse.ArgumentParser(description='Some description. This script does this and that...')
    parser.add_argument('--data-dir', type=directory, help='Specify the directory where the data files can be found.',
                        default=buoy.DEFAULT_DATA_DIR)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--print-buoy-names', action='store_true', help='Prints the name of the available buoys for a given data dir.')
    group.add_argument('-b', '--buoy', type=str, help="Specify the name of the buoy.")

    parser.add_argument('--print-header', action='store_true', help='Prints the name of the available buoys for a given data dir.')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--debug', action='store_true', help="Output debugging information.")
    group.add_argument('-v', '--verbose', action='store_true', help="Output info.")

    parser.add_argument('--log-filename', type=str, help="File used to output logging information.")

    parser.add_argument('-f', '--filter', action="append", nargs="*", help="Only return a string with some of the values. Based on the header file. --print-header to see the available filter options.")
    parser.add_argument('--date-from', type=date, help='Only print data values from (including) this date.')
    parser.add_argument('--date-to', type=date, help='Only print data untill (exclusive) this date.')

    # Do the parser.
    args = parser.parse_args()

    # Set the log options.
    if args.debug:
        logging.basicConfig( filename=args.log_filename, level=logging.DEBUG )
    elif args.verbose:
        logging.basicConfig( filename=args.log_filename, level=logging.INFO )
    else:
        logging.basicConfig( filename=args.log_filename, level=logging.WARNING )

    # Output what is in the args variable.
    LOG.debug(args)

    try:
        if not os.path.isdir(args.data_dir):
            raise argparse.ArgumentTypeError("Missing data directory: '%s'."%(args.data_dir))

        if args.print_buoy_names:
            print "'%s'."%"', '".join(buoy.get_buoy_names(args.data_dir))
            sys.exit()

        # Get all the buoy names from the data directory.
        buoy_names = buoy.get_buoy_names(args.data_dir)
        if buoy_names == None or len(buoy_names) == 0:
            # If there were no data in the data directory stop here.
            raise argparse.ArgumentTypeError("No data. Please specify a data dir with data. Default: %s"%(args.data_dir))

        # Printing the header. This is taken from the dat_header.dat file. The buoy name must also be specified.
        if args.print_header:
            if args.buoy == None or args.buoy not in buoy_names:
                raise argparse.ArgumentTypeError("Buoy name must be specifired with option -b when printing header: Available for buoy names: '%s'. Example: '-b %s'."%("', '".join(buoy_names), iter(buoy_names).next()))
            buoy = buoy.buoy_factory(args.buoy)

            # The header strings. The first header i all the files is the date.
            header_strings = buoy.get_header_strings()

            # Output.
            print "Available headers for '%s' (%s):"%(buoy.name, args.buoy)
            print "'%s'"%("', '".join(header_strings))
            sys.exit()
            
        buoys = []
        if args.buoy != None:
            # Select only one buoy.
            if args.buoy not in buoy_names:
                raise argparse.ArgumentTypeError("'%s' must be one of '%s'!"%(args.buoy, "', '".join(buoy.get_buoy_names(args.data_dir))))
            buoys.append(buoy.buoy_factory(args.buoy))
        else:
            # Select all available buoys
            for buoy_name in buoy_names:
                buoys.append(buoy.buoy_factory(buoy_name))
    
        ## Filtering.
        # It was not really possible to create a default filter with argparse. The new filter variables were inserted
        # into a new list, alongside the default list.
        if args.filter == None:
            args.filter = [None]
        # Just make sure the filter variable is a list, and not a str, e.g.
        assert(isinstance(args.filter, list))

        # Make sure the header strings (filters) exist.
        if args.filter[0] != None: # [None,], when empty (default).
            for f in args.filter[0]:
                for buoy in buoys:
                    header_strings = buoy.get_header_strings()
                    if f not in header_strings:
                        raise argparse.ArgumentTypeError("The filter option '{filter_option}' does not exist for buoy '{buoy_name}'. Available filter options for {buoy_name}: '{filter_options}'!".format(filter_option=f, buoy_name=buoy.name, filter_options="', '".join(header_strings)))
        
        # Print the data.
        for buoy in buoys:
            print ""
            print "# %s ('%s')"%(buoy.name, buoy.short_name)

            if args.filter[0] != None:
                print "# '%s'"%("', '".join(args.filter[0]))
            else:
                print "# '%s'"%("', '".join(buoy.get_header_strings()))

            for data in buoy.data(args.date_from, args.date_to):
                print data.filter(args.filter[0])
    except argparse.ArgumentTypeError, e:
        print "Error: %s"%(e.message)
        sys.exit(1)
