"""
Generates a single requirements.txt file for the whole directory.
"""
import os

if __name__ == "__main__":
    dpath = os.path.abspath(os.path.dirname(__file__))
    assert dpath.endswith("dev"), "This script must be used from the firmware/controller-module/dev folder."

    topdpath = os.path.abspath(os.path.join(dpath, "../../.."))
    requirements = ""
    for root, dirs, files in os.walk(topdpath):
        for fname in files:
            if fname.lower() == "requirements.txt":
                with open(os.path.join(root, fname), 'r') as f:
                    requirements += ''.join(f.readlines()).strip() + '\n'

    with open('requirements.txt', 'w') as f:
        f.write(requirements)
