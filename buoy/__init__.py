import os
import glob
import logging
import datetime
import re

# Define the logger
LOG = logging.getLogger(__name__)

# 
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "buoy")
DEFAULT_DATE_FORMAT = "%Y%m%d%H%M"
DEFAULT_MISSING_VALUE = -99.0

class BuoyException(Exception):
    pass

def get_buoy_names(data_dir=None):
    if data_dir==None:
        # One back and into "data".
        data_dir = DEFAULT_DATA_DIR

    LOG.debug("Data directory: %s"%(data_dir))

    # Return a set of all the filenames, with one dot with the .dat extension, in the data directory.
    # "header" files (files with the "header" somewhere in the name) are ignored.
    # E.g. arko.dat arko.dat_head.dat arko.datneu.dat arko.datneu_head.dat dars.dat dars.dat_head.dat
    # becomes arko, arko.datneu and dars.
    if os.path.isdir(data_dir):
        return {os.path.splitext(filename)[0].lower() \
                    for filename in os.walk((os.path.abspath(os.path.join(data_dir)))).next()[2] \
                    if os.path.splitext(filename)[1].lower() == ".dat" \
                    and "head" not in filename.lower()}

    LOG.error("Missing data dir: '%s'"%(data_dir))
    raise BuoyException("Missing data dir: '%s'"%(data_dir))

def buoy_factory(name):
    """
    Creates a buoy object from a string.
    """
    return Buoy(name)

def get_header_filename(buoy_short_name):
    if "neu" in buoy_short_name:
        return "%s_head.dat"%(buoy_short_name) # dars.datneu_head.dat
    return "%s.dat_head.dat"%(buoy_short_name)


class BuoyHeaderElement(object):
    def __init__(self, line):
        """
        The header element.
        It simply contains a value and a type.

        It is inserted into a indexed dict in the buoy object to
        control what is what in the data file.
        """
        LOG.debug("Header file line: '%s'"%(line))
        self.value, self.type = line.split()

class BuoyDataElement(object):
    def __init__(self, line, headers):
        """
        The BuoyDataElement. The data from the <buoy_short_name>.dat file will be read
        in to this element. The headers must be a list of BuoyHeaderElements that describes
        what is being read from the line, i.e. what is read from the <buoy_short_name>.dat_head.dat file.
        """
        self.headers = headers

        LOG.debug(line.strip())
        line_parts = line.split()

        # Prepare the header types. These are the ones from the
        # <buoy_short_name>.dat_head.dat file. Each distinct type
        # becomes a new dict in the self.__dict__.
        for header_type in {header.type for header in self.headers}: # Distinct header type.
            self.__dict__[header_type] = {}
        LOG.debug("Dict after headers prepeared: %s"%(self.__dict__))

        # The first element in every line is the date.
        self.date = datetime.datetime.strptime(line_parts[0], DEFAULT_DATE_FORMAT)
        line_parts = line_parts[1:]

        # As the values are not space separated, some of the values can be contracted into one
        # "number" with several dots, e.g. "-99.0001030.000".
        # Using a regular expression to separate them. Remembering the possibility of negative
        # numbers, "-*".
        i = 0
        for line_part in line_parts:
            # Extracting valus from a string of floats with the "fortran format" "F8.3".
            # The values end up in a list [val1, val2, ...].
            values = [float(x) for x in re.findall("-*\d{1,4}\.\d{3}", line_part)]
            for value in values:
                self.__dict__[self.headers[i].type][self.headers[i].value] = value
                i += 1

        if i != len(self.headers):
            raise BuoyException("The number of values in the data line, %i, does not match the number of header elements, %i."%(i, len(self.header)))

    def filter(self, order=None):
        """
        A filter is applied to the data when printing it.

        The order filter must correspond to the data in the dat_header.dat file.
        It must be a list of key/values, e.g.: [WT:3, WT:6]
        """
        LOG.debug("Order: '%s'."%(order))
        string_elements = []
        if order != None:
            # The order must be a list. Se __doc__ above.
            assert(isinstance(order, list))
            for header_type, header_value in [x.split(":") for x in order]:
                LOG.debug("%s %s"%(header_type, header_value))
                if header_type == "date":
                    string_elements.append("%s"%self.date.strftime(DEFAULT_DATE_FORMAT))
                else:
                    string_elements.append("%s"%self.__dict__[header_type][header_value])
        else:
            # No filter. Everything is printed.
            string_elements.append(self.date.strftime(DEFAULT_DATE_FORMAT))
            for header in self.headers:
                string_elements.append("%s"%self.__dict__[header.type][header.value])
        return " ".join(string_elements)

    def __str__(self):
        return "%s"%self.filter()


class Buoy:
    def __init__(self, short_buoy_name, data_dir=None, data_file=None, data_header_file=None):
        """
        Initiates the buoy.

        Based on the input name, it sets the data file and the corresponding header file.

        The data file must be named:   <name>.dat
        The header file must be named: <name>.dat_head.dat

        They must both exist in the data_dir, which can be specified. If not,
        the "data" directory is used.

        The header types are read (from the header file) into a list of BuoyHeaderElements.
        """
        LOG.debug("Buoy short name (used to find data and header files): '%s'."%(short_buoy_name))

        buoys = get_buoy_names(data_dir)
        if short_buoy_name not in buoys:
            raise BuoyException("The input name of the buoy, %s, must be one of '%s'. Or the data file is missing?"%( \
                    short_buoy_name, "', '".join(buoys)))

        self.short_name = short_buoy_name

        if data_dir == None:
            data_dir = DEFAULT_DATA_DIR

        # Specify the data file, or use the default.
        if data_file == None:
            self.data_file = os.path.join(data_dir, "%s.dat"%(short_buoy_name))
        else:
            self.data_file = data_file

        # Specify data header file, or use the default for that name.
        if data_header_file == None:
            self.data_header_file = os.path.join(data_dir, get_header_filename(short_buoy_name))
        else:
            self.data_header_file = data_header_file

        # Make sure the files exist.
        assert(os.path.isfile(self.data_file))
        assert(os.path.isfile(self.data_header_file))

        LOG.debug("Building header.")
        self.headers = []
        with open(self.data_header_file) as fp:
            # The first name is the name of the buoy.
            self.name = fp.readline().strip()
            LOG.info(self.name)
            for line in fp:
                LOG.debug(line)
                if len(line.split()) == 2:
                    self.headers.append(BuoyHeaderElement(line))

        LOG.debug("Number of header elements: %i"%len(self.headers))

    def get_header_strings(self):
        header_strings = ["%s:%s"%(header.type, header.value) for header in self.headers]
        # The first element is allways a string.
        header_strings.insert(0, "date:")
        return header_strings

    def data(self, date_from_including=None, date_to_excluding=None):
        """
        Getting the data for the specific buoy (self).
        A generator is created, yielding each line of the data. The data line
        is turned into a buoy object, which is what is being returned.

        If the data is outside the dates specified, it just moves on to the next line in the
        data file. It is possible to only specifiy date_from_including, or only
        date_to_excluding.

        Excluding is chosen to be able to do from the 1st in a month, to the 1st in another month,
        without knowing the number of days in the month.
        """
        with open(self.data_file) as fp:
            for line in fp:
                # Read in the data from the line.
                b = BuoyDataElement(line, self.headers)

                # No need to continue if the data date is outside interval.
                #
                # Make sure the data date is larger than (or equal to) date from.
                if date_from_including != None and date_from_including >= b.date:
                    continue

                # Make sure the data date is smaller than date to.
                if date_to_excluding != None and date_to_excluding < b.date:
                    continue

                # Return the buoy object.
                yield b
