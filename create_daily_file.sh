#!/bin/bash

# The minimum WT depths for the differnt buoys.
# These values are found from buoy data header files.
declare -A arr
arr[dars.datneu]="2"
arr[fino1]="3"
arr[arko]="2"
arr[dbucht]="3"
arr[arko.datneu]="2"
arr[dars]="2"
arr[oder]="3"
arr[nsb]="3"
arr[nsb3]="4"
arr[fehm]="1"
arr[ems]="3"
arr[kiel]="0"

# This is the base directory.
cd /home/hw/dvl/copernicus/buoy-validation/

# Loop through the last 7 days, starting with yesterday.(--start-days-back-in-time = 1)
python print_last_dates.py ${1:-7} --start-days-back-in-time 1 | while read sat_date
do
    # For each date, get the day before. These are used for the file name. The date format is therefore a little different.
    # The valid buoy data for midnight is 12 hours before and 12 hours after, which is why the 12 is appended to the dates.

    # Yesterday for the current date 
    file_date_from=$(python -c "import datetime; print (datetime.datetime.strptime('${sat_date}', '%Y-%m-%d')-datetime.timedelta(days=1)).strftime('%Y%m%d')")"12"

    # The current date.
    file_date_to=$(python -c "import datetime; print datetime.datetime.strptime('${sat_date}', '%Y-%m-%d').strftime('%Y%m%d')")"12"

    # This is the date format for the filter. That is, the dates in the output files are converted to julian date.
    DATE_FORMAT="julian"
    
    for buoy_name in ${!arr[@]}
    do
	# Get the depth for the buoy.
	depth=${arr[${buoy_name}]}

	output_filename=/home/hw/tmp/buoy/L4_valid_${buoy_name}_${depth}_${file_date_from}_${file_date_to}_NSB_0.02.asc

	# Create the file.
	# /scratch/sstdev/SAT_EYE/L4_VALID/VALID/Marnet/L4_valid_$Buoy_$depth_20150406_20150407_NSB_0.02.asc
	echo "python compare_sat_with_bouy.py -b ${buoy_name} --date $sat_date --filter b:lon b:lat b:date:julian b:WT:${depth} s:lon s:lat s:analysed_sst s:analysed_sst_smooth  dummy:-99.0 s:sea_ice_fraction s:dist2ice s:analysis_error -o ${output_filename} --overwrite"
	time python compare_sat_with_bouy.py \
	    -b ${buoy_name} \
	    --date $sat_date \
	    --filter b:lon       b:lat              b:date:julian  b:WT:${depth} \
	             s:lon       s:lat              s:analysed_sst s:analysed_sst_smooth \
	             dummy:-99.0 s:sea_ice_fraction s:dist2ice     s:analysis_error \
	    -o ${output_filename} \
	    --overwrite

	# Exit if an error occurs.
	return_code=$?
	if [[ ${return_code} -ne 0 ]] ; then
	    echo ""
	    echo "ERROR..."
	    exit ${return_code}
	fi
    done
done

cd -
