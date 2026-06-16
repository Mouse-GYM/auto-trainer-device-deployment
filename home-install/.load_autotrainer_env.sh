# NB: designed to be sourced from .bashrc, for instance.

echo -n "Auto-activating auto-trainer-1 conda environment .."
conda activate auto-trainer-1
echo " done."

echo -n "Auto-exporting LD_PRELOAD with required auto-trainer libs .."

_extend_ldpreload="/usr/lib/aarch64-linux-gnu/libffi.so.7:/usr/lib/aarch64-linux-gnu/libgomp.so.1:/lib/aarch64-linux-gnu/libGLdispatch.so.0:/home/$USER/anaconda3/envs/auto-trainer-1/lib/python3.8/site-packages/sklearn/__check_build/../../scikit_learn.libs/libgomp-d22c30c5.so.1.0.0"
export LD_PRELOAD="$LD_PRELOAD:${_extend_ldpreload}"

echo " done."

echo

# some utility function(s) :

show_autotrainer_top() {
	local -a pids=(
	  $(pgrep -f auto-trainer-1) \
	  $(pgrep -f tools.acquisition) \
	  $(pgrep -f auto-trainer-headless) \
	  $(pgrep -f auto-trainer-local) \
  )
	echo
	ps -eo pid,lstart,cmd | grep auto-trainer
	echo
	free -h
	echo
	if test "${pids}" ; then
	  top -d 3 $(for p in ${pids[@]} ; do echo "-p $p" ; done)
  else
    echo "Detected no auto-trainer process"
  fi
}


autotrainer_dump_stack_trace() {
  which "py-spy" >/dev/null || {
    echo "py-spy missing/not available. You can install it with pip install py-spy" >&2
    return 1
  }
  local pid
  echo "Trying to detect auto-trainer main process pid.."
  # somehow not clean:
  pid=$(ps -U "autotrainer" -ao pid,cmd | egrep "auto-trainer-1|python .*auto-trainer-local.py" | egrep -v "grep|spawn|resource_tracker|ipython" | awk '{print $1}')
  if ! test "${pid}" ; then
    echo "Could not find autotrainer main process pid, is it running ?" >&2
    return 1
  fi
  echo "Found pid=${pid}: $(ps -p ${pid})"
  local out_file=~/dump_autotrainer_stack_"$(date +%Y%m%d_%H%M%S)".dat
  local res
  # display with colors:
  sudo env PATH="${PATH}" py-spy dump --pid "${pid}" -ll
  sudo env PATH="${PATH}" py-spy dump --pid "${pid}" -ll &> "${out_file}"
  echo
  echo "Above stack traces also added to ${out_file}, that you can now copy."
}


cat << END

Feel free to use 'show_autotrainer_top' to display auto-trainer live processes

other available shell tools:

+ autotrainer_dump_stack_trace: allows to dump stack trace of main process

END
