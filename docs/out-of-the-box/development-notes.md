# Dev Notes

Here are some random tidbits of information I don't want to forget. Possibly I'll organize these
into something more formal at some point.

## Pulling Images from an Insecure Registry

On Artie's nodes, you need to ensure that /etc/default/docker.json has the following contents:

```json
{
    "insecure-registries": ["10.0.0.249:5000"]
}
```

or whatever your IP address is for the development registry.

Do not include "http://".

**Note** that on Ubuntu 22.04, this may be at /etc/docker/daemon.json instead.

## Exec format error

When building on Ubuntu, if you run into "exec format error", it likely means
buildx is not able to use qemu. Run `sudo apt install qemu-user-static`,
noting that qemu-system does NOT work (though you are free to install that package as well).

## Qemu: uncaught target signal 11 (Segmentation fault) - core dumped

When building on Windows, if you run into "qemu: uncaught target signal 11 (Segmentation fault) - core dumped",
try the following steps:

1. `docker run --privileged --rm tonistiigi/binfmt --install all`
1. `docker run --rm --privileged multiarch/qemu-user-static --reset -p yes -c yes`
