"""
Script to build the eyebrows or mouth user-space driver.
"""
import argparse
import errno
import os
import shutil
import subprocess

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("driver", type=str, choices=('mouth', 'eyebrows'), help="Driver to build.")
    parser.add_argument("fw_image", metavar="fw-image", type=str, help="Docker image that contains the FW. Obtain this by first building the eyebrows/mouth FW Docker image, then pushing to a registry.")
    args = parser.parse_args()

    # Directory of the build folder which should contain the Dockerfile
    builddpath = os.path.dirname(os.path.realpath(__file__))

    # Sanity check that Dockerfile is located there
    dockerfpath = os.path.join(builddpath, "Dockerfile")
    if not os.path.isfile(dockerfpath):
        print("Cannot find Dockerfile. Did you move the Dockerfile or this script?")
        exit(errno.ENOENT)

    # Check that Docker is running
    try:
        subprocess.run(["docker", "--version"]).check_returncode()
    except subprocess.CalledProcessError:
        print("Docker doesn't seem to be working. Is it running?")
        exit(errno.ESRCH)

    # Copy Artie libs into ./tmp folder
    tmpdpath = os.path.join(builddpath, "..", "tmp")
    if os.path.isdir(tmpdpath):
        shutil.rmtree(tmpdpath)
    os.mkdir(tmpdpath)
    libpath = os.path.join(builddpath, "..", "..", "..", "libraries")
    libs = ["artie-i2c", "artie-util"]
    for lib in libs:
        shutil.copytree(os.path.join(libpath, lib), os.path.join(tmpdpath, lib))

    # Build the Docker image
    githash = subprocess.run('git log --format="%h" -n 1'.split(), capture_output=True, encoding='utf-8').stdout.strip().strip('"')
    try:
        dockerargs = f"--build-arg DRIVER_TYPE={args.driver} --build-arg FW_IMG={args.fw_image} --env PORT={4242 if args.driver == 'eyebrows' else 4243}"
        dockercmd = f"docker buildx build --load --platform linux/arm64 -f Dockerfile {dockerargs} -t artie-driver-{args.driver}:{githash} .."
        subprocess.run(dockercmd.split(), cwd=os.path.join(builddpath)).check_returncode()
    except subprocess.CalledProcessError:
        print("Error running the Docker build. If your error was something like 'ERROR: failed to solve: rpc error', remember that you have to push the base image to a registry. Buildx can't load from local.")
    finally:
        # Remove tmp folder (which contains the copied libs)
        shutil.rmtree(tmpdpath)
