# Originally from this tutorial: https://jumpnowtek.com/rpi/Raspberry-Pi-4-64bit-Systems-with-Yocto.html
FROM ubuntu:20.04

# Use Bash
SHELL ["/bin/bash", "-c"]

# Install packages
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    build-essential \
    chrpath \
    diffstat \
    gawk \
    libncurses5-dev \
    python3-distutils \
    texinfo \
    git \
    cpio \
    wget \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Pull Yocto project
WORKDIR /firmware
RUN git clone -b dunfell git://git.yoctoproject.org/poky.git poky-dunfell

# Pull Yocto layers
WORKDIR /firmware/poky-dunfell
RUN git clone -b dunfell git://git.openembedded.org/meta-openembedded
RUN git clone -b dunfell https://github.com/meta-qt5/meta-qt5
RUN git clone -b dunfell git://git.yoctoproject.org/meta-raspberrypi
RUN git clone -b dunfell git://git.yoctoproject.org/meta-security.git
RUN git clone -b dunfell https://github.com/jumpnow/meta-jumpnow

## K3s layer
WORKDIR /firmware
RUN git clone https://github.com/janeczku/meta-k3s.git

## Jumpnow's RPi layer
WORKDIR /firmware/rpi64
RUN git clone -b dunfell https://github.com/jumpnow/meta-rpi64.git

# Create your work directory
RUN mkdir -p /firmware/rpi64/build/conf

# Copy configuration file samples
WORKDIR /firmware/rpi64
RUN cp meta-rpi64/conf/local.conf.sample build/conf/local.conf
RUN cp meta-rpi64/conf/bblayers.conf.sample build/conf/bblayers.conf

################### Modify bblayers.conf ####################
# Replace ${HOME} with appropriate filepaths
RUN sed -i 's:${HOME}:/firmware:g' build/conf/bblayers.conf 
# Add meta-k3s layer
RUN sed -i '[[:space:]]*/firmware/rpi64/meta-rpi64.*:i /firmware/meta-k3s \'

################### Modify k3s layer.conf ###################
# Update to include compatability with dunfell
RUN sed -i 's:LAYERSERIES_COMPAT_meta-k3s = "*":LAYERSERIES_COMPAT_meta-k3s = "dunfell":g' /firmware/meta-k3s/conf/layer.conf

################### Modify local.conf #######################
# Replace default account password
RUN sed -i 's:jumpnowtek:root:g' build/conf/local.conf
# Use systemd
RUN sed -i 's:VIRTUAL-RUNTIME_init_manager = "sysvinit":VIRTUAL-RUNTIME_init_manager = "systemd":g' build/conf/local.conf
RUN echo 'DISTRO_FEATURES_append = " systemd"' > build/conf/local.conf

################### Modify sanity.conf #######################
# Modify sanity.conf to disable the sanity check about root user
RUN sed -i 's:INHERIT += "sanity":#INHERIT += "sanity:g' /firmware/poky-dunfell/meta/conf/sanity.conf

# Source yocto's env and build (has to be part of the same RUN command)
WORKDIR /firmware/rpi64/build
RUN source /firmware/poky-dunfell/oe-init-build-env /firmware/rpi64/build \
    && bitbake console-image

ARG TMPDIR=/firmware/rpi64/build/tmp
ARG IMAGESDIR=${TMPDIR}/deploy/images/raspberrypi4-64
ARG SCRIPTSDIR=/firmware/rpi64/meta-rpi64/scripts

# All the stuff we need to copy to the SD card image
ENV DTBS=${IMAGESDIR}/bcm2711-rpi-4-b.dtb
ENV BOOTFILESDIR=${IMAGESDIR}/bootfiles
ENV KERNELIMG=${IMAGESDIR}/Image

# Make a special device tree overlay directory containing all the right files
RUN mkdir ${IMAGESDIR}/dtboverlays && \
    ls ${IMAGESDIR}/*.dtbo | grep -v -e "-raspberrypi4-64" | xargs -I{} cp "{}" ${IMAGESDIR}/dtboverlays/

# Resolve the symlinks because we can't copy them out of Docker easily
RUN cp $(readlink -f ${KERNELIMG}) ${IMAGESDIR}/pi-image.bin
RUN cp $(readlink -f ${DTBS}) ${IMAGESDIR}/device-tree.dtb
RUN cp $(readlink -f ${IMAGESDIR}/console-image-raspberrypi4-64.tar.xz) ${IMAGESDIR}/rootfs.tar.xz

CMD [ "/bin/bash", "-c", "sleep infinity" ]