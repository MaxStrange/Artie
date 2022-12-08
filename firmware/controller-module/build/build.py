"""
Build the Controller Module's custom Linux image and package it into a single file for flashing onto an SD card.
Unfortunately, not all of this can be done in Docker due to limitations in Docker build.
"""
import argparse
import getpass
import os
import pathlib
import random
import shutil
import string
import subprocess
import time

ON_WINDOWS = os.name == "nt"
TARGET_HOSTNAME = "artie-controller-node"
TMP_PATH = "/tmp/pi-img"

class CustomLinuxImage:
    def __init__(self) -> None:
        self.imgsdir = "/firmware/rpi64/build/tmp/deploy/images/raspberrypi4-64"
        self.hostdpath = TMP_PATH
        _run_cmd(f"mkdir -p {self.hostdpath}", wsl=True)
        self.dtbs = {
            "docker": f"{self.imgsdir}/device-tree.dtb",
            "host": f"{self.hostdpath}/bcm2711-rpi-4-b.dtb"
        }
        self.kernelimg = {
            "docker": f"{self.imgsdir}/pi-image.bin",
            "host": f"{self.hostdpath}/kernel8.img"
        }

        self.dtbsoverlays = {
            "docker": f"{self.imgsdir}/dtboverlays",
            "host": f"{self.hostdpath}"
        }

        self.bootfiles = {
            "docker": f"{self.imgsdir}/bootfiles",
            "host": f"{self.hostdpath}"
        }

        self.rootfs = {
            "docker": f"{self.imgsdir}/rootfs.tar.xz",
            "host": f"{self.hostdpath}/console-image-raspberrypi4-64.tar.xz"
        }

    def _move_to_dst(self, src, dst):
        """
        Moves the given "src" into "dst". If we are running on Windows, we
        move from C: drive to the WSL.
        """
        if ON_WINDOWS:
            wsl_src = _make_path(src)
            subprocess.run(["wsl", "mv", wsl_src, dst]).check_returncode()
        else:
            shutil.move(src, dst)

    def copy_from_container(self, container_id: str) -> None:
        """
        Copy all the files we need from the given Docker container to the host.
        """
        # Bootfiles
        src = f"{self.bootfiles['docker']}/"
        dst = f"{self.bootfiles['host']}/"
        tmpdst = os.path.abspath("./")
        os.makedirs(tmpdst, exist_ok=True)
        _run_cmd(f"docker cp {container_id}:{src} {tmpdst}")
        for fname in os.listdir(tmpdst):
            fpath = os.path.join(tmpdst, fname)
            self._move_to_dst(fpath, dst)

        # dtbsoverlays
        src = f"{self.dtbsoverlays['docker']}/"
        dst = f"{self.dtbsoverlays['host']}/"
        tmpdst = os.path.abspath("./")
        os.makedirs(tmpdst, exist_ok=True)
        _run_cmd(f"docker cp {container_id}:{src} {tmpdst}")
        for fname in os.listdir(tmpdst):
            fpath = os.path.join(tmpdst, fname)
            self._move_to_dst(fpath, dst)

        # kernel img
        src = f"{self.kernelimg['docker']}"
        dst = f"{self.kernelimg['host']}"
        tmpdst = "./tmp"
        _run_cmd(f"docker cp {container_id}:{src} {tmpdst}")
        self._move_to_dst(os.path.abspath(tmpdst), dst)

        # dtbs
        src = f"{self.dtbs['docker']}"
        dst = f"{self.dtbs['host']}"
        tmpdst = "./tmp"
        _run_cmd(f"docker cp {container_id}:{src} {tmpdst}")
        self._move_to_dst(os.path.abspath(tmpdst), dst)

        # Rootfs
        src = f"{self.rootfs['docker']}"
        dst = f"{self.rootfs['host']}"
        tmpdst = "./tmp"
        _run_cmd(f"docker cp {container_id}:{src} {tmpdst}")
        self._move_to_dst(os.path.abspath(tmpdst), dst)

    def copy_fat_partition(self, password: str, mnt: str):
        """
        Copy all the FAT partition's files to it.
        """
        # Bootfiles
        _run_cmd(f"sudo -S cp -r {self.bootfiles['host']}/bootfiles/* {mnt}/", password=password, wsl=True)

        # Device tree binary
        _run_cmd(f"sudo -S cp {self.dtbs['host']} {mnt}/", password=password, wsl=True)

        # Device tree overlays
        dst = f"{mnt}/overlays"
        _run_cmd(f"sudo -S mkdir {dst}", password=password, wsl=True)
        _run_cmd(f"sudo -S cp -r {self.dtbsoverlays['host']}/dtboverlays/* {dst}/", password=password, wsl=True)

        # Copy kernel
        _run_cmd(f"sudo -S cp {self.kernelimg['host']} {mnt}/", password=password, wsl=True)

    def copy_ext_partition(self, password: str, mnt: str):
        """
        Copy all the ext4 partition's files to it.
        """
        # Copy the rootfs
        src = self.rootfs['host']
        dst = mnt
        _run_cmd(f"sudo -S tar --numeric-owner -C {dst} -xJf {src}", password=password, wsl=True)

        # Generate random seed for urandom
        _run_cmd(f"sudo -S mkdir -p {mnt}/var/lib/urandom", password=password, wsl=True)
        _run_cmd(f"sudo -S dd if=/dev/urandom of={mnt}/var/lib/urandom/random-seed bs=512 count=1", password=password, wsl=True)
        _run_cmd(f"sudo -S chmod 600 {mnt}/var/lib/urandom/random-seed", password=password, wsl=True)

        # Set the controller module's hostname
        tmpath = os.path.abspath("tmphostname")
        with open(tmpath, 'w') as f:
            f.write(TARGET_HOSTNAME)
        _run_cmd(f"sudo -S mv {_make_path(tmpath)} {mnt}/etc/hostname", password=password, wsl=True)

    def remove_artifacts(self):
        """
        Clean up all the stuff we copied to the image.
        """
        _run_cmd(f"rm -rf {self.hostdpath}", wsl=True)

def _make_cmd(cmd_args):
    if ON_WINDOWS:
        cmd_args.insert(0, "wsl")
    print("     > " + " ".join(cmd_args))
    return cmd_args

def _make_path(fpath: str) -> str:
    """
    Return a path to the item from the WSL's view if on Windows, otherwise just return fpath.
    """
    if ON_WINDOWS:
        wsl_fpath = "/mnt/c" + str(pathlib.PurePosixPath(pathlib.PureWindowsPath(fpath))).lstrip("C:\\")
        return wsl_fpath
    else:
        return fpath

def _run_cmd(cmd, password=None, wsl=False):
    """
    """
    if type(cmd) == str:
        cmd = cmd.split(' ')

    if wsl:
        cmd = _make_cmd(cmd)

    if "sudo" in cmd:
        subprocess.run(cmd, input=password, capture_output=True, encoding='utf-8').check_returncode()
    else:
        subprocess.run(cmd, capture_output=True).check_returncode()

def build_docker_file(curdir: str) -> str:
    """
    Build "Dockerfile" in `curdir` and return the built image's name.
    """
    docker_image = "artie-controller-module-build-image-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    proc = subprocess.run(["docker", "build", "-t", docker_image, curdir])
    if proc.returncode:
        print(f"Docker build returned an error code {proc.returncode}")
        exit(1)
    return docker_image

def copy_files_from_docker(docker_image: str) -> CustomLinuxImage:
    """
    Run the given `docker_image` and get the needed build artifacts out of it,
    placing them into a newly created directory.
    """
    # Make the tmpdir
    image_mappings = CustomLinuxImage()

    # Start docker process
    docker_proc_id = None
    container_id_fpath = os.path.abspath("tmpcontainerid")
    proc = subprocess.Popen(["docker", "run", "--rm", f"--cidfile={container_id_fpath}", docker_image])
    try:
        # Need to wait a bit for docker to start
        start_time = time.time()
        while not os.path.isfile(container_id_fpath):
            if time.time() - start_time > 5:
                print("Timed out waiting for Docker to start the container.")
                exit(1)

        # Get the container's ID (Docker takes a moment to write to the file after it gets created)
        while not docker_proc_id:
            with open(container_id_fpath, 'r') as f:
                docker_proc_id = f.readline().strip()

        # Copy the files out of the docker container
        image_mappings.copy_from_container(docker_proc_id)
    finally:
        # Do our best to clean up the running Docker process
        proc.kill()
        if docker_proc_id is not None:
            _run_cmd(f"docker stop {docker_proc_id}")
        if os.path.exists(container_id_fpath):
            os.remove(container_id_fpath)

    return image_mappings

def create_and_partition_file(image_fname: str, password: str) -> str:
    """
    Create and partition a file into FAT and ext4, then return
    the path to that file.
    """
    # Create a 2GB file (where the image will go)
    image_fpath = os.path.abspath(image_fname)
    with open(image_fpath, 'wb') as f:
        f.truncate(int(128e6 * 16))

    # Partition the file into two partitions and format those partitions as FAT and ext4
    try:
        _run_cmd("sfdisk --help", wsl=True)
    except Exception:
        print("fdisk does not seem to be installed. Please install it before continuing.")
        os.remove(image_fpath)
        exit(1)

    # Mount the image file as a loopback device and take note of which device
    cmd = _make_cmd(["sudo", "-S", "losetup", "-fP", _make_path(image_fpath), "--show"])
    proc = subprocess.run(cmd, input=password, capture_output=True, encoding="utf-8", timeout=5)
    proc.check_returncode()
    device = proc.stdout.strip()
    assert device.startswith("/dev/loop")

    # Run the sfdisk command to partition the image file
    sfdisk_input = """\
1,+256M,c
,
""".replace(os.linesep, "\n")
    cmd = _make_cmd(["sudo", "-S", "sfdisk", device])
    subprocess.run(cmd, input=password + "\n" + sfdisk_input, timeout=5, encoding="utf-8").check_returncode()

    # Format the two partitions into FAT and ext4
    _run_cmd(f"sync", wsl=True)
    _run_cmd(f"sudo -S mkfs.vfat -F 32 {device}p1", password=password, wsl=True)
    _run_cmd(f"sudo -S mkfs.ext4 -F -q {device}p2", password=password, wsl=True)

    return image_fpath, device

def mount_and_copy(image_mappings: CustomLinuxImage, image_fpath: str, device: str, partition: str, password: str):
    """
    Mounts `image_fpath` at the correct partition, based on `partition`,
    then copies the correct files from `image_mappings` into it, then unmounts.

    `device` is the loopdevice.
    `partition` should be either "FAT" or "ext4".
    """
    mountdir = "/tmp/mnt"
    _run_cmd(f"mkdir -p {mountdir}", wsl=True)
    if partition == "FAT":
        # Mount the given partition
        _run_cmd(f"sudo -S mount -o loop {device}p1 {mountdir}", password=password, wsl=True)
        # Copy all the FAT partition files
        image_mappings.copy_fat_partition(password, mountdir)
        # Unmount
        _run_cmd(f"sudo -S umount {mountdir}", password=password, wsl=True)
    elif partition == "ext4":
        # Mount the given partition
        _run_cmd(f"sudo -S mount -o loop {device}p2 {mountdir}", password=password, wsl=True)
        # Copy all the ext4 partition files
        image_mappings.copy_ext_partition(password, mountdir)
        # Unmount
        _run_cmd(f"sudo -S umount {mountdir}", password=password, wsl=True)
    else:
        raise ValueError(f"Can't understand given partition for mount_and_copy: {partition}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=str, default=None, help="If given, we skip the Docker build step and use the given Docker image.")
    parser.add_argument("--delete-image", action="store_true", help="If given, we delete the Docker image afterwards.")
    parser.add_argument("--output-image-fname", type=str, default="pi.img", help="The filepath of the output image.")
    args = parser.parse_args()

    # First check if we are running in the right directory
    curdir = os.path.abspath(os.path.dirname(__file__))
    if "Dockerfile" not in os.listdir(curdir):
        print("This script must be located in the directory with the Dockerfile, but it seems that it has been moved.")
        exit(1)

    # Do the Docker build
    docker_image = args.image
    if not docker_image:
        print("Building image - if not cached, this can take several hours...")
        docker_image = build_docker_file(curdir)

    # Pull out the artifacts we need into a temporary directory
    print("Pulling out the build artifacts from the Docker container...")
    image_mappings = copy_files_from_docker(docker_image)

    # Create and partition a file
    print("Creating image file and partitioning it...")
    if ON_WINDOWS:
        password = getpass.getpass("WSL sudo password:")
    else:
        password = getpass.getpass("Sudo password:")
    image_fpath, device = create_and_partition_file(args.output_image_fname, password)

    # Copy all the files
    print("Copying files into image file...")
    mount_and_copy(image_mappings, image_fpath, device, "FAT", password)
    mount_and_copy(image_mappings, image_fpath, device, "ext4", password)

    # Remove the loopback device and all the tmp directory items
    _run_cmd(f"sudo -S losetup --detach {device}", password=password, wsl=True)
    image_mappings.remove_artifacts()

    # Delete the Docker image if user requested it
    if args.delete_image:
        _run_cmd(f"docker rmi {docker_image}")

    print(f"SD card image successfully created at {image_fpath}")
