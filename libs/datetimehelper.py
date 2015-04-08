import datetime

SECONDS_IN_A_DAY = 24*60*60.0
JULIAN_DAY_EPOC = datetime.datetime(1950, 1, 1)

def date2julian(date):
    """
    In this case the julian day is the number of days since 1950, 1, 1.
    """
    diff_date = (date - JULIAN_DAY_EPOC)
    return diff_date.days + diff_date.seconds/SECONDS_IN_A_DAY

