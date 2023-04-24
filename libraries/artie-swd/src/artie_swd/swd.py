"""
Common SWD stuff I find myself doing in several drivers.
"""
from artie_util import artie_logging as alog
from artie_util import util
import datetime
import os
import subprocess

def load_fw_file(fw_fpath: str, iface_fname: str):
    """
    Attempt to load the FW file.

    Args
    ----
    - fw_fpath: File path of the .elf file to load.
    - iface_fname: File name of the swd.cfg found in OpenOCD's interface/ directory.
    """
    if not os.path.isfile(fw_fpath):
        raise FileNotFoundError(f"File {fw_fpath} does not exist.")

    if not os.path.isfile(f"/usr/local/share/openocd/scripts/interface/{iface_fname}"):
        raise FileNotFoundError(f"File /usr/local/share/openocd/scripts/interface/{iface_fname} does not exist.")

    openocd_cmds = f'program {fw_fpath} verify reset exit'
    alog.info(f"Attempting to load {fw_fpath} into MCU...")
    cmd = f'openocd -f interface/{iface_fname} -f target/rp2040.cfg -c '
    total_cmd = cmd.split() + [openocd_cmds]

    if util.in_test_mode():
        alog.info(f"Mocking SWD command: {cmd} {openocd_cmds}")
        return

    start_time = datetime.datetime.now().timestamp()
    result = subprocess.run(total_cmd, capture_output=True, encoding='utf-8')
    duration_s = datetime.datetime.now().timestamp() - start_time
    if result.returncode != 0:
        alog.error(f"Non-zero return code when attempting to load FW. Got return code {result.returncode}")
        alog.error(f"Reset MCU may be non-responsive.")
        alog.error(f"Got stdout and stderr from openocd subprocess:")
        alog.error(f"STDOUT: {result.stdout}")
        alog.error(f"STDERR: {result.stderr}")
        alog.update_histogram(duration_s, f"swd-load-{alog.HISTOGRAM_SUFFIX_SECONDS}", unit=alog.Units.SECONDS, description="Histogram of SWD load durations.", attributes={"swd.error": True})
        alog.update_counter(1, "swd-errors", unit=alog.Units.TIMES, description="Number of times SWD fails.")
    else:
        alog.info("Loaded FW successfully.")
        alog.update_histogram(duration_s, f"swd-load-{alog.HISTOGRAM_SUFFIX_SECONDS}", unit=alog.Units.SECONDS, description="Histogram of SWD load durations.", attributes={"swd.error": False})
