#!/system/bin/sh
# SDM660 frequence
sdm660_fre=(1804800 1555200 1296000 1017600 768000 681600 547200 412800 300000 200000);
# SDM670 frequence
sdm670_fre=(1804800 1555200 1296000 1017600 768000 681600 547200 412800 300000 200000);
# SDM845 frequence
sdm845_fre=(1804800 1555200 1353600 1017600 768000 681600 547200 451200 300000 200000); 
# SDM855 frequence
sdm855_fre=(2092800 1804800 1555200 1353600 1017600 768000 681600 547200 451200); 

start_time=$(date +%s)
cur_time=$(date +%s)
file_name="ddr_freq_"$start_time.txt
touch /data/local/tmp/$file_name
log_file_path="/data/local/tmp/$file_name"
echo "start_time: $start_time"

#get the device name 
device=`getprop ro.product.brand`
#get the platform information
platform=`getprop ro.board.platform`

display_freq() {
	if [ -f /sys/kernel/debug/clk/bimc_clk/measure ]; then
    		echo "$(date +%s): " $(< /sys/kernel/debug/clk/bimc_clk/measure) >> $log_file_path
  	elif [ -f /sys/kernel/debug/clk/bimc_clk/clk_measure ]; then
    		echo "$(date +%s): " $(< /sys/kernel/debug/clk/bimc_clk/clk_measure) >> $log_file_path
  	elif [ -f /sys/kernel/debug/clk/measure_only_bimc_clk/clk_measure ]; then
    		echo "$(date +%s): " $(< /sys/kernel/debug/clk/measure_only_bimc_clk/clk_measure) >> $log_file_path
	#for 855 platform	
  	elif [ -f /sys/kernel/debug/clk/measure_only_mccc_clk/clk_measure ]; then
    		echo "$(date +%s): " $(< /sys/kernel/debug/clk/measure_only_mccc_clk/clk_measure) >> $log_file_path
  	else
    		echo "BIMC measure unsupported"
  	fi
}

bimc_freq_switch() {
  	## don't turn off thermal-engine, otherwise thermal reset will be triggered easily. #stop thermal-engine

    display_freq
    sleep $interval

		a=$(($interval + $a));
		if [ $a -ge $t_temp ]; then
			if [ -f /sys/kernel/debug/clk/measure_only_mccc_clk/clk_measure ]; then
    				echo "$(date +%s): " $(< /sys/kernel/debug/clk/measure_only_mccc_clk/clk_measure) >> $log_file_path
			elif [ -f /sys/kernel/debug/clk/measure_only_bimc_clk/clk_measure ]; then
    				echo "$(date +%s): " $(< /sys/kernel/debug/clk/measure_only_bimc_clk/clk_measure) >> $log_file_path
			else
    				echo "BIMC measure unsupported" >> $log_file_path
			fi
			end_time=$(date +%s)
			echo "end_time:$end_time"
			total_time=`expr $end_time - $start_time`
			echo "total_time:$total_time"
			exit
		fi
}

#loop freq switch
loop_bimc_freq_switch() {
	a=0
	while [ 1 ] ; do
		bimc_freq_switch
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
