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
            local log_dir="$(dirname -- "${log_url}")"
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
            local log_dir="$(dirname -- "${log_url}")"
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
    local filename="$(basename -- "$1")"
    local extension="${filename##*.}"
    extension="$(echo "$extension" | tr '[:upper:]' '[:lower:]')"
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

function set_env {
    export install_path=/usr/local/Ascend

    if [ -d ${install_path}/toolkit ]; then
        export LD_LIBRARY_PATH=/usr/include/hdf5/lib/:/usr/local/:/usr/local/lib/:/usr/lib/:${install_path}/fwkacllib/lib64/:${install_path}/driver/lib64/common/:${install_path}/driver/lib64/driver/:${install_path}/add-ons:${path_lib}:${LD_LIBRARY_PATH}
        export PATH=${install_path}/fwkacllib/ccec_compiler/bin:${install_path}/fwkacllib/bin:$PATH
        export PYTHONPATH=${install_path}/fwkacllib/python/site-packages:${install_path}/tfplugin/python/site-packages:${install_path}/toolkit/python/site-packages:$PYTHONPATH
        export PYTHONPATH=/usr/local/python3.7.5/lib/python3.7/site-packages:$PYTHONPATH
        export ASCEND_OPP_PATH=${install_path}/opp
else
        if [ -d ${install_path}/nnae/latest ];then
            export LD_LIBRARY_PATH=/usr/local/:/usr/local/python3.7.5/lib/:/usr/local/openblas/lib:/usr/local/lib/:/usr/lib64/:/usr/lib/:${install_path}/nnae/latest/fwkacllib/lib64/:${install_path}/driver/lib64/common/:${install_path}/driver/lib64/driver/:${install_path}/add-ons/:/usr/lib/aarch64_64-linux-gnu:$LD_LIBRARY_PATH
            export PATH=$PATH:${install_path}/nnae/latest/fwkacllib/ccec_compiler/bin/:${install_path}/nnae/latest/toolkit/tools/ide_daemon/bin/
            export ASCEND_OPP_PATH=${install_path}/nnae/latest/opp/
            export OPTION_EXEC_EXTERN_PLUGIN_PATH=${install_path}/nnae/latest/fwkacllib/lib64/plugin/opskernel/libfe.so:${install_path}/nnae/latest/fwkacllib/lib64/plugin/opskernel/libaicpu_engine.so:${install_path}/nnae/latest/fwkacllib/lib64/plugin/opskernel/libge_local_engine.so
            export PYTHONPATH=${install_path}/nnae/latest/fwkacllib/python/site-packages/:${install_path}/nnae/latest/fwkacllib/python/site-packages/auto_tune.egg/auto_tune:${install_path}/nnae/latest/fwkacllib/python/site-packages/schedule_search.egg:$PYTHONPATH
            export ASCEND_AICPU_PATH=${install_path}/nnae/latest
    else
            export LD_LIBRARY_PATH=/usr/local/:/usr/local/lib/:/usr/lib64/:/usr/lib/:/usr/local/python3.7.5/lib/:/usr/local/openblas/lib:${install_path}/ascend-toolkit/latest/fwkacllib/lib64/:${install_path}/driver/lib64/common/:${install_path}/driver/lib64/driver/:${install_path}/add-ons/:/usr/lib/aarch64-linux-gnu:$LD_LIBRARY_PATH
            export PATH=$PATH:${install_path}/ascend-toolkit/latest/fwkacllib/ccec_compiler/bin/:${install_path}/ascend-toolkit/latest/toolkit/tools/ide_daemon/bin/
            export ASCEND_OPP_PATH=${install_path}/ascend-toolkit/latest/opp/
            export OPTION_EXEC_EXTERN_PLUGIN_PATH=${install_path}/ascend-toolkit/latest/fwkacllib/lib64/plugin/opskernel/libfe.so:${install_path}/ascend-toolkit/latest/fwkacllib/lib64/plugin/opskernel/libaicpu_engine.so:${install_path}/ascend-toolkit/latest/fwkacllib/lib64/plugin/opskernel/libge_local_engine.so
            export PYTHONPATH=${install_path}/ascend-toolkit/latest/fwkacllib/python/site-packages/:${install_path}/ascend-toolkit/latest/fwkacllib/python/site-packages/auto_tune.egg/auto_tune:${install_path}/ascend-toolkit/latest/fwkacllib/python/site-packages/schedule_search.egg:$PYTHONPATH
            export ASCEND_AICPU_PATH=${install_path}/ascend-toolkit/latest
        fi
    fi
}

function install_dependencies {
    dependencies_file_dir="$1"
    if [ -f "$dependencies_file_dir/requirements.txt" ];then
        logger_info " exec pip install"
        pip install -r "$dependencies_file_dir/requirements.txt"
    fi
}

function logger {
    echo "[$(date +%Y%m%d-%H:%M:%S)] [MindXDL Service Log]$*"
}

function logger_error() {
    logger "[$(date +%Y%m%d-%H:%M:%S)] [ERROR]$*"
}

function logger_warn() {
    logger "[$(date +%Y%m%d-%H:%M:%S)] [WARN]$*"
}

function logger_info() {
    logger "[$(date +%Y%m%d-%H:%M:%S)] [INFO]$*"
}