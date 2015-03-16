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
    parser.add_argument('--data-dir', type=directory, help='Specify the directory where the data files can be found.')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--print-buoy-names', action='store_true', help='Prints the name of the available buoys for a given data dir.')
    # group.add_argument('--all', action='store_true', help="Process all buoys.")
    group.add_argument('-b', '--buoy', type=str, help="Specify the name of the buoy.")

    parser.add_argument('--print-header', action='store_true', help='Prints the name of the available buoys for a given data dir.')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--debug', action='store_true', help="Output debugging information.")
    group.add_argument('-v', '--verbose', action='store_true', help="Output info.")

    parser.add_argument('--log-filename', type=str, help="File used to output logging information.")

    parser.add_argument('--order', action="append", nargs="*")
    parser.add_argument('--date-from', type=date, help='Only print data values from (including) this date.')
    parser.add_argument('--date-to', type=date, help='Only print data untill (exclusive) this date.')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig( filename=args.log_filename, level=logging.DEBUG )
    elif args.verbose:
        logging.basicConfig( filename=args.log_filename, level=logging.INFO )
    else:
        logging.basicConfig( filename=args.log_filename, level=logging.WARNING )

    # Output what is in the args variable.
    LOG.debug(args)

    if args.print_buoy_names:
        print "'%s'."%"', '".join(buoy.get_buoy_names(args.data_dir))
        sys.exit()

    if args.print_header and args.buoy == None:
        raise argparse.ArgumentTypeError("Please specify buoy to print header for.")

    buoy_names = buoy.get_buoy_names(args.data_dir)
    if args.buoy:
        if args.buoy not in buoy_names:
            raise argparse.ArgumentTypeError( "'%s' must be one of '%s'!"%(args.buoy, "', '".join(buoy.get_buoy_names(args.data_dir))))
        buoy = buoy.buoy_factory(args.buoy)
    else:
        header_strings = ["%s:%s"%(buoy.header[i].type, buoy.header[i].value) for i in buoy.header]
        header_strings.insert(0, "date:")
        if args.print_header:
            print "Available headers for '%s' (%s):"%(buoy.name, args.buoy)
            print "'%s'"%("', '".join(header_strings))
            sys.exit()
        else:
            if args.order == None:
                args.order = [None]
            assert(instanceof(args.order, list))
            if args.order[0] != None: # [None,], when empty (default).
                for o in args.order[0]:
                    if o not in header_strings:
                        raise argparse.ArgumentTypeError("The order option '%s' must be one of '%s'!"%(o, "', '".join(header_strings)))
                
            for data in buoy.data(args.date_from, args.date_to):
                print data.filter(args.order[0])
        
