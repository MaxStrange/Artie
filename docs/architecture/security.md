# Security Design

Since one of the main purposes of Artie is data collection during experimentation,
it makes sense to give some thought to how to protect the data that gets collected,
especially as some of it may be personally-identifiable information (PII), such
as voice, or images of faces.

To this end, this document breaks down the security design of Artie.

## Where's the Money Lebowski?

Before we can discuss what security measures are in place, we should first
discuss what we are trying to protect. If there is nothing to protect, no
security is necessary, after all.

In our case, we can think of the following things that might be of value:

* Physical Artie - the actual Artie robot. It represents a significant cost investment.
* Data, which may be further subdivided:
    * Sensor Data:
        * Personally-Identifiable Data (PII): Data such as images of people's faces, or
          recordings of their voices. This information must be protected, if for no
          other reason than from an ethical standpoint.
        * Non-PII sensor data: Data like accelerometer values or temperature readings.
          This data probably does not represent much value for an attacker.
        * Internal network traffic: Artie sends many commands and responses throughout
          his system all the time, such as 'drive motor A to whatever degrees'.
          This is valuable to an attacker only insofar as it can provide insights into
          how best to design an attack that produces value somewhere else or if it can
          provide insights into secret algorithms.
        * Experimental/secret algorithms: These are closed-source "secret sauce" algorithms.
          I personally open-source all of my work, but Artie has an MIT license,
          and people can use him to test out algorithms that are closed-source.
          Some effort should be taken to protect this information.

## Security Boundaries

### Physical

I take the view that if an attacker has somehow gained physical access to Artie,
it is game over. It takes a lot of money and time to put together an Artie;
you should protect him.

As such, there is no effort to encrypt or authenticate at the physical level.
All information over the i2c, SPI, CAN, etc. buses is unencrypted,
and any node on these buses could have access to all of their traffic.

Firmware is not encrypted, as it is open-source anyway, and test points (where
they exist) are not necessarily disabled "in production".

### Remote Access

This is where we take our stand, so to speak. Specifically:

* We do not trust the Wifi network we are on.
* We *do* trust all pods in the Kubernetes cluster.
    * As such, all inter-pod communication inside the cluster is allowed.
      Only very specific pods are allowed to accept connections from outside
      the Kubernetes cluster, and to do so, we require some form of authentication.
    * All traffic *inside* the Kubernetes cluster is encrypted, to prevent
      simple network sniffers from picking up on data transferred over Wifi.
* We *do not* trust network traffic that originates outside the Kubernetes cluster.
    * As such, we require authentication for incoming traffic.
    * The Kubernetes control plane is secured using best practices.
    * All traffic in/out of the cluster must also be encrypted.
* We use best practices (in release mode) for Docker environments and K3S deployment.
* We do not allow SSH (in release mode) into any of the Yocto images by default (after setup).
  In fact, the only ports that are open in the Yocto images are the ones required
  by Kubernetes Services that need to communicate off-board.
