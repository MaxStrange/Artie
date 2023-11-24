import re
import sys

# Example of what we read:
#
#(artie-id) module:
#    submodule01: [working, degraded, not working, or unknown]
#    submodule02: [working, degraded, not working, or unknown]
#    etc.
#

retcode = 0
submodule_status_pattern = re.compile("\s+?P<submodule>:\s+\[?P<status>\]\s*")
for line in sys.stdin.read():
    if line.strip().endswith("]"):
        match = re.match(submodule_status_pattern, line)
        status = match.groupdict().get('status', '').lower()
        submodule = match.groupdict().get('submodule', '').lower()
        if status != "working":
            print(f"Error: submodule {submodule} status: {status}")
            retcode = 1

exit(retcode)
