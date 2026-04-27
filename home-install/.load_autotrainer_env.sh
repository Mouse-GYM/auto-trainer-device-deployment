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

echo "Feel free to use 'show_autotrainer_top' to display auto-trainer live processes"
