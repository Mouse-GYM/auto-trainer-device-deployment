# NB: designed to be sourced from .bashrc, for instance.

echo -n "Auto-activating auto-trainer-1 conda environment .."

if ! conda activate auto-trainer-1
then
  echo "Could not activate auto-trainer-1 ; has it been created ?" >&2
  echo "Skipping other parts of auto-trainer load environment." >&2
else

echo " done."

function __join_by {
  local d=${1-} f=${2-}
  if shift 2; then
    printf %s "$f" "${@/#/$d}"
  fi
}

echo -n "Auto-exporting LD_LIBRARY_PATH and LD_PRELOAD with required auto-trainer libs .."

__extend_ldpreload_arr=(
  "${CONDA_PREFIX}/lib/libgomp.so"
    # to fix/prevent cannot allocate memory in static TLS block

  # /usr/lib/aarch64-linux-gnu/libfreetype.so.6
    # otherwise the disable state of UI widgets is not dark greyed
    # todoDONE: remove once that disabled state not visually correct fixed with the conda env libfreetype
    # fixed with either install of ffmpeg 6.1.1 or force-reinstall of freetype conda package.

  /lib/aarch64-linux-gnu/libGLdispatch.so.0
    # for GL use for GUI
)
export LD_PRELOAD="$LD_PRELOAD:$(__join_by ":" "${__extend_ldpreload_arr[@]}")"
unset __extend_ldpreload_arr

# ensure system libraries from conda env are used :
conda_libs_paths=(
  "${CONDA_PREFIX}/lib64"
  "${CONDA_PREFIX}/lib"
)
export LD_LIBRARY_PATH="$(__join_by ":" "${conda_libs_paths[@]}" "${LD_LIBRARY_PATH}")"

echo " done."

echo

# some utility function(s) :

show_autotrainer_top() {
	local -a pids=(
    $(pgrep -f auto-trainer-local)
    $(pgrep -f tools.acquisition.gui)
    $(pgrep -f auto-trainer-headless)
    $(pgrep -f tools.acquisition.headless)
    $(pgrep -f auto-trainer-1)
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
