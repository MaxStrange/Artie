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
nprocessed = 0
submodule_status_pattern = re.compile("\s+?P<submodule>:\s+\[?P<status>\]\s*")
for line in sys.stdin.readlines():
    print("Processing line:", line)
    if line.strip().endswith("]"):
        match = re.match(submodule_status_pattern, line)
        if not match:
            print(f"Got a line that doesn't match the regular expression. Here's the line:", line)
            retcode = 1
            continue

        nprocessed += 1
        status = match.groupdict().get('status', '').lower()
        submodule = match.groupdict().get('submodule', '').lower()
        if status != "working":
            print(f"Error: submodule {submodule} status: {status}")
            retcode = 1

if nprocessed == 0:
    retcode = 1

exit(retcode)
