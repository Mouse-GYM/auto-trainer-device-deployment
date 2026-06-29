# NB: designed to be sourced from .bashrc, for instance.

echo -n "Auto-activating auto-trainer-1 conda environment .."

if ! conda activate auto-trainer-1
then
  echo "Could not activate auto-trainer-1 ; has it been created ?" >&2
  echo "Skipping other parts of auto-trainer load environment." >&2
else

echo " done."

echo -n "Auto-exporting LD_PRELOAD with required auto-trainer libs .."

__extend_ldpreload_arr=(
  /usr/lib/aarch64-linux-gnu/libffi.so.7
  /lib/aarch64-linux-gnu/libGLdispatch.so.0
)

# allows to handle different site-packages dir,
# for instance with:
# /home/autotrainer/anaconda3/envs/auto-trainer-1/lib/python3.8/site-packages
# vs
# /home/autotrainer/miniconda3/envs/auto-trainer-1/lib/python3.8/site-packages

__site_packages_dir=$(python -c "import site; print(site.getsitepackages()[0])")
__scikit_gomp=$(find "${__site_packages_dir}/scikit_learn.libs/" -regextype posix-extended -iregex ".*/libgomp.*so.*$")
if test -f "${__scikit_gomp}"
then
  __extend_ldpreload_arr+=( "${__scikit_gomp}" )
else
  echo "Did not find scikit_learn gomp shared lib, is environment fully setup ?" >&2
fi
unset __scikit_gomp __site_packages_dir


function __join_by {
  local d=${1-} f=${2-}
  if shift 2; then
    printf %s "$f" "${@/#/$d}"
  fi
}

export LD_PRELOAD="$LD_PRELOAD:$(__join_by ":" "${__extend_ldpreload_arr[@]}")"
unset __extend_ldpreload_arr

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
  command -v "py-spy" >/dev/null || {
    echo "py-spy missing/not available. You can install it with pip install py-spy" >&2
    return 1
  }
  echo "Trying to detect auto-trainer main process pid.."
  local -a pids
  mapfile -t pids < <(
    ps -U "${USER}" -ao pid,cmd \
    | grep -E "auto-trainer-1|python .*auto-trainer-local.py" \
    | grep -Ev "grep|spawn|resource_tracker|ipython" \
    | awk '{print $1}')
  if (( ${#pids[@]} == 0 )); then
    echo "Could not find autotrainer main process pid, is it running ?" >&2
    return 1
  fi
  (( ${#pids[@]} > 1 )) && echo "Warning: multiple candidate PIDs (${pids[*]}), using ${pids[0]}" >&2
  local pid
  pid=${pids[0]}
  echo "Found pid=${pid}: $(ps -p ${pid})"
  local out_file=~/dump_autotrainer_stack_"$(date +%Y%m%d_%H%M%S)".dat
  # display with colors and copy to file:
  sudo env PATH="${PATH}" py-spy dump --pid "${pid}" -ll -n --full-filenames 2>&1 | tee "${out_file}"
  echo
  echo "Above stack traces also added to ${out_file}, that you can now copy."
}


cat << END

Feel free to use 'show_autotrainer_top' to display auto-trainer live processes

other available shell tools:

+ autotrainer_dump_stack_trace: allows to dump stack trace of main process

END

fi
