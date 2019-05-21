#!/system/bin/sh

start_time=$(date +%s)
cur_time=$(date +%s)
file_name="gpu_freq_"$start_time.txt
touch /data/local/tmp/$file_name
log_file_path="/data/local/tmp/$file_name"
echo "start_time: $start_time s"

#get the device name 
device=`getprop ro.product.brand`
#get the platform information
platform=`getprop ro.board.platform`

display_freq() {
	if [ -f /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq ]; then
    		echo "$(date +%s): " $(< /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq) >> $log_file_path
  	else
    		echo "GPU measure unsupported" >> $log_file_path
  	fi
}

gpu_freq_switch() {
  	## don't turn off thermal-engine, otherwise thermal reset will be triggered easily. #stop thermal-engine

    display_freq
    sleep $interval

		a=$(($interval + $a));
		if [ $a -ge $t_temp ]; then
			if [ -f /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq ]; then
    				echo "$(date +%s): " $(< /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq) >> $log_file_path
			else
    				echo "GPU measure unsupported" >> $log_file_path
			fi
			end_time=$(date +%s)
			echo "end_time:$end_time s"
			total_time=`expr $end_time - $start_time`
			echo "total_time:$total_time s"
			exit
		fi
}

#loop freq switch
loop_bimc_freq_switch() {
	a=0
	while [ 1 ] ; do
		gpu_freq_switch
	done
} 

## designed by qishan ##
## entry ###

## get the interval
opt=$1

if [ "$opt" = "-i" ]; then
	shift
	interval=$1
	shift
	opt=$1
	echo "switching interval set to $interval"
else
	interval=3
	#echo "switching interval set to default 3 sec"
fi

## opt: -d  : display the scaling frequency list
if [ "$opt" = "-d" ]; then
	display_freq
	exit
fi

if [ "$opt" = "-t" ]; then
	shift
	t_temp=$1
	shift
	opt=$1
else
	t_temp=0
fi

if [ "$opt" = "-o" ]; then
	#shift
	#FREQ_LIST=$1
	if [ "$device" = "Xiaomi" ]; then
		if [ "$platform" = "sdm845" ]; then
			FREQ_LIST=${sdm845_fre[*]}
		elif [ "$platform" = "sdm660" ]; then
			FREQ_LIST=${sdm660_fre[*]}
		elif [ "$platform" = "sdm670" ]; then
			FREQ_LIST=${sdm670_fre[*]}
		#for 855 platform	
		elif [ "$platform" = "msmnile" ]; then
			FREQ_LIST=${sdm855_fre[*]}
		else
			echo "xiaomi haven't this platform"
		fi
	else
		echo "this device is not Xiaomi"
		exit
	fi
		#bimc_freq_switch
		loop_bimc_freq_switch
	exit
fi

if [ "$opt" = "-h" ]; then
	echo "ddr_clock_switch.sh [-h] [-i <interval>] [-t <time>] [-d] [-o]"
	exit
fi

echo "Bad Argument"
echo "ddr_clock_switch.sh [-h] [-i <interval>] [-t <time>] [-d] [-o]"
exit
