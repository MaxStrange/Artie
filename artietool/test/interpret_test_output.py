import re
import sys

# Example of what we read:
#
#(artie-id) module:
#    submodule01: [working, degraded, not working, or unknown]
#    submodule02: [working, degraded, not working, or unknown]
#    etc.
#
# OR
#(artie-id) module:
#    Error: [<error message>]
#

def _process_line(line: str) -> bool:
    """
    Return True if there was an error while processing.
    """
    submodule_status_pattern = re.compile("\s+?P<submodule>.*:\s+\[?P<status>.*\]\s*")
    if not line.strip().endswith("]"):
        print("Ignoring line that does not end with ']'")
        return False

    match = re.match(submodule_status_pattern, line)
    if not match:
        print(f"Got a line that ends with ']' but doesn't match the regular expression. Most likely this is an error line.")
        return True

    status = match.groupdict().get('status', '').lower()
    submodule = match.groupdict().get('submodule', '').lower()
    if status != "working":
        print(f"Error: submodule {submodule} status: {status}")
        return True

    print("No errors detected on this line")
    return False

if __name__ == "__main__":
    retcode = 0
    nprocessed = 0
    for line in sys.stdin.readlines():
        print("Processing line:", line)
        nprocessed += 1
        err = _process_line(line)
        if err:
            print("Got an error while trying to process this line. Setting error code.")
            retcode = 1

    if nprocessed == 0:
        print("Did not process any input. This is an error.")
        retcode = 1

    exit(retcode)
