# coding: utf-8
import datetime

SECONDS_IN_A_DAY = 24*60*60.0
DEFAULT_JULIAN_DAY_EPOC = datetime.datetime(1950, 1, 1)
DEFAULT_DATE_FORMAT_MIN = "%Y%m%d%H%M"

def date2julian(date, epoc = DEFAULT_JULIAN_DAY_EPOC):
    """
    In this case the julian day is the number of days since 1950, 1, 1.
    """
    diff_date = (date - epoc)
    return diff_date.days + diff_date.seconds/SECONDS_IN_A_DAY

def julian2date(julian_day, epoc = DEFAULT_JULIAN_DAY_EPOC):
    """
    Julian day to datetime.
    """
    julian_seconds = julian_day * SECONDS_IN_A_DAY
    return epoc + datetime.timedelta(seconds=julian_seconds)
