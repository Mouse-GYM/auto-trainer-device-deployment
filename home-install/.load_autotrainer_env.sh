# NB: designed to be sourced from .bashrc, for instance.

echo -n "Auto-activating auto-trainer-1 conda environment .."

if ! conda activate auto-trainer-1
then
  echo "Could not activate auto-trainer-1 ; has it been created ?" >&2
  echo "Skipping other parts of auto-trainer load environment." >&2
  exit 0
fi

echo " done."

__prepend_unique() {  # $1 = var name, $2 = entry
  local m=${2%/}
  case "${!1}" in
    "$m") ;;
    "$m/") ;;
    "$m:"*) ;;
    "$m/:"*) ;;
    *":$m") ;;
    *":$m:"*) ;;
    *":$m/:"*) ;;
    *)
      export "$1=$m${!1:+:${!1}}" ;;
  esac
}

echo -n "Auto-exporting LD_LIBRARY_PATH and LD_PRELOAD with required auto-trainer libs .."

__gomp="${CONDA_PREFIX}/lib/libgomp.so"
if [ ! -e "${__gomp}" ]; then
  echo "Expected ${__gomp} not found, is the environment fully set up?" >&2
fi

# ensure system libraries from conda env are used :

__prepend_unique LD_PRELOAD "${__gomp}"
__prepend_unique LD_LIBRARY_PATH "${CONDA_PREFIX}/lib"
__prepend_unique LD_LIBRARY_PATH "${CONDA_PREFIX}/lib64"   # prepended last so lib64 ends up first, matching current order

unset __prepend_unique __join_by __gomp

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
