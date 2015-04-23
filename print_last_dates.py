#!/usr/bin/env python
# coding: UTF-8
import datetime
import logging

# Define the logger
LOG = logging.getLogger(__name__)

def print_dates(number_of_days_back_in_time, start_date=datetime.datetime.now()):
    for i in range(0, number_of_days_back_in_time):
        print (start_date - datetime.timedelta(days=i)).date()



if __name__ == "__main__":
    import argparse

    def date( date_string ):
        # argparse.ArgumentTypeError()
        return datetime.datetime.strptime( date_string, '%Y-%m-%d' )

    def date_back_in_time( number_of_days_back_in_time ):
        number_of_days_back_in_time = int(number_of_days_back_in_time)
        d = datetime.datetime.now() - datetime.timedelta(days=number_of_days_back_in_time)
        return d

    parser = argparse.ArgumentParser(description='Print dates <number_of_days> back in time from start date. Start date can be set by number of days back or to specify the date.')
    parser.add_argument('number_of_days', type=int, help='The number of dates to print.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--start-date', type=date, help='The number of dates to print.', default=datetime.datetime.now())
    group.add_argument('--start-days-back-in-time', type=date_back_in_time, dest='start_date', help='The number of days back in to use as start date.', default=0)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--debug', action='store_true', help="Output debugging information.")
    group.add_argument('-v', '--verbose', action='store_true', help="Output info.")
    parser.add_argument('--log-filename', type=str, help="File used to output logging information.")

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

    print_dates(args.number_of_days, args.start_date)
