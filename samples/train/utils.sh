function dls_create_log {
    OLD_UMASK=`umask`
    umask 0022
    local log_url="$1"
    local MindXDL_PIPE="MindXDL-pipe"
    if [ "$log_url" = "" ]
    then
        echo "[MindXDL Service Log][MindXDL_create_log] do not create log"
    else
        command -v "${MindXDL_PIPE}" > /dev/null 2>&1
        if [ "$?" = "0" ]
        then
            echo "[MindXDL Service Log][MindXDL_create_log] ${MindXDL_PIPE} found"
            "$MindXDL_PIPE" "${log_url}" create
        else
            echo "[MindXDL Service Log][MindXDL_create_log] ${MindXDL_PIPE} not found, use mkdir/touch instead (owner/mode may be incorrect!)"
            local log_dir="`dirname -- "${log_url}"`"
            mkdir -p "${log_dir}"
            touch "${log_url}"
        fi
    fi
    umask ${OLD_UMASK}
}

function dls_logger {
    OLD_UMASK=`umask`
    umask 0022
    local log_url="$1"
    local param="$2"
    local MindXDL_PIPE="MindXDL-pipe"
    if [ "${log_url}" = "" ]
    then
        echo "[MindXDL Service Log][MindXDL_logger] discard log"
        cat > /dev/null
    else
        command -v "${MindXDL_PIPE}" > /dev/null 2>&1
        if [ "$?" = "0" ]
        then
            echo "[MindXDL Service Log][MindXDL_logger] ${MindXDL_PIPE} found"
            if [ ! -z "${param}" ]
            then
                stdbuf -oL -eL "${MindXDL_PIPE}" "${log_url}" "$param"
            else
                stdbuf -oL -eL "${MindXDL_PIPE}" "${log_url}"
            fi
        else
            echo "[MindXDL Service Log][MindXDL_logger] ${MindXDL_PIPE} not found, use cat instead"
            local log_dir="`dirname -- "${log_url}"`"
            mkdir -p "${log_dir}"
            if [ "${param}" = "append" ]
            then
                cat >> "${log_url}"
            else
                cat > "${log_url}"
            fi
        fi
    fi
    umask $OLD_UMASK
}

function dls_get_executor {
    local filename="`basename -- "$1"`"
    local extension="${filename##*.}"
    extension="`echo "$extension" | tr '[:upper:]' '[:lower:]'`"
    case "$extension" in
    py|pyc|pyw|pyo|pyd)
        which python
        ;;
    sh)
        which bash
        ;;
    *)
        ;;
    esac
}

function install_dependencies {
    dependencies_file_dir="$1"
    cd "$dependencies_file_dir"
    if [ -f "$dependencies_file_dir/requirements.txt" ];then
        logger_info " exec pip install"
        pip install -r "$dependencies_file_dir/requirements.txt"
    fi
    cd -
}

function logger {
    echo "[MindXDL Service Log]$*"
}

function logger_error() {
    logger "[ERROR]$*"
}

function logger_warn() {
    logger "[WARN]$*"
}

function logger_info() {
    logger "[INFO]$*"
}

