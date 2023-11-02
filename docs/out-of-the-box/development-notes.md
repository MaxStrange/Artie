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

**Note** that on Ubuntu 22.04, this may be at /etc/docker/daemon.json instead.
