import os
import glob
import logging
import datetime
import re

# Define the logger
LOG = logging.getLogger(__name__)

# 
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_DATE_FORMAT = "%Y%m%d%H%M"
DEFAULT_MISSING_VALUE = -99.0

class BuoyException(Exception):
    pass

def get_buoy_names(data_dir=None):
    if data_dir==None:
        # One back and into "data".
        data_dir = DEFAULT_DATA_DIR

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
    def __init__(self, line, header_dict):
        """
        The BuoyDataElement. The data from the <buoy_short_name>.dat file will be read
        in to this element. The header_dict must be an indexed dict of BuoyHeaderElements
        that describes what is being read from the line, i.e. what is read from the
        <buoy_short_name>.dat_head.dat file.
        """
        self.header_dict = header_dict

        LOG.debug(line.strip())
        line_parts = line.split()

        # Prepare the header types. These are the ones from the
        # <buoy_short_name>.dat_head.dat file. Each distinct type
        # becomes a new dict in the self.__dict__.
        disctinct_header_types = {x.type for x in self.header_dict.values()}
        for header_type in disctinct_header_types:
            self.__dict__[header_type] = {}
        LOG.debug("Dict after header_dict types: %s"%(self.__dict__))

        # TODO: Move this out and read / filter the lines in separate method, from here.

        # The first element in every line is the date.
        self.date = datetime.datetime.strptime(line_parts[0], DEFAULT_DATE_FORMAT)
        line_parts = line_parts[1:]

        # As the values are not space separated, some of the values can be contracted into one
        # "number" with several dots, e.g. "-99.0001030.000".
        # Using a regular expression to separate them. Remembering the possibility of negative
        # numbers, "-*".
        i = 0
        while i < len(header_dict):
            # Extracting valus from a string of floats with the "fortran format" "F8.3".
            # The values end up in a list [val1, val2, ...].
            values = [float(x) for x in re.findall("-*\d{1,4}\.\d{3}", line_parts[i])]
            for value in values:
                self.__dict__[header_dict[i].type][header_dict[i].value] = value
                i += 1

        if i != len(header_dict):
            raise BuoyException("The number of values in the data line, %i, does not match the number of header elements, %i."%(i, len(header_dict)))

    def filter(self, order=None):
        """
        
        """
        LOG.debug("Order: '%s'."%(order))
        # import sys; sys.exit() # Debug.

        string_elements = []
        if order != None:
            for t, v in [x.split(":") for x in order]:
                LOG.debug("%s %s"%(t, v))
                if t == "date":
                    string_elements.append("%s"%self.date.strftime(DEFAULT_DATE_FORMAT))
                else:
                    string_elements.append("%s"%self.__dict__[t][v])
        else:
            # No filter
            string_elements.append(self.date.strftime(DEFAULT_DATE_FORMAT))
            for i in range(len(self.header_dict)):
                header = self.header_dict[i]
                string_elements.append("%s"%self.__dict__[header.type][header.value])
        return " ".join(string_elements)

    def __str__(self):
        return "%s"%self.filter()


class Buoy:
    def __init__(self, short_buoy_name, data_dir=None):
        """
        Initiates the buoy.

        Based on the input name, it sets the data file and the corresponding header file.

        The data file must be named:   <name>.dat
        The header file must be named: <name>.dat_head.dat

        They must both exist in the data_dir, which can be specified. If not,
        the "data" directory is used.

        The header types are read (from the header file) into an indexed header dict.
        self.header[0] = first_header_element
        self.header[1] = second_header_element
        etc.
        """
        LOG.debug("Buoy short name (used to find data and header files): '%s'."%(short_buoy_name))

        buoys = get_buoy_names(data_dir)
        if short_buoy_name not in buoys:
            raise BuoyException("The input name of the buoy, %s, must be one of %s. Or the data file is missing?"%( \
                    short_buoy_name, ",".join(buoys)))

        if data_dir == None:
            data_dir = DEFAULT_DATA_DIR

        self.data_file = os.path.join(data_dir, "%s.dat"%(short_buoy_name))
        self.data_header_file = os.path.join(data_dir, "%s.dat_head.dat"%(short_buoy_name))

        assert(os.path.isfile(self.data_file))
        assert(os.path.isfile(self.data_header_file))

        LOG.debug("Building header.")
        self.header = {}
        with open(self.data_header_file) as fp:
            # The first name is the name of the buoy.
            self.name = fp.readline().strip()
            LOG.info(self.name)

            i = 0
            for line in fp:
                LOG.debug(line)
                if len(line.split()) == 2:
                    self.header[i] = BuoyHeaderElement(line)
                    i += 1

        LOG.debug("Number of header elements: %i"%len(self.header))

    def data(self, date_from_including=None, date_to_excluding=None):
        with open(self.data_file) as fp:
            for line in fp:
                b = BuoyDataElement(line, self.header)

                # Make sure the data date is larger than (or equal to) date from.
                if date_from_including != None and date_from_including >= b.date:
                    continue

                # Make sure the data date is smaller than date to.
                if date_to_excluding != None and date_to_excluding < b.date:
                    continue

                # Return the data.
                yield b


"""
arko.dat                arko.dat_head.dat
arko.datneu.dat         arko.datneu_head.dat
dars.dat                dars.dat_head.dat
dars.datneu.dat         dars.datneu_head.dat
dbucht.dat              dbucht.dat_head.dat
ems.dat                 ems.dat_head.dat
fehm.dat                fehm.dat_head.dat
fino1.dat               fino1.dat_head.dat
info.txt                info.txt~  
kiel.dat                kiel.dat_head.dat
nsb.dat                 nsb.dat_head.dat
nsb3.dat                nsb3.dat_head.dat
oder.dat                oder.dat_head.dat
readme.txt
"""
