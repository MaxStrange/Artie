1. User starts Artie Workbench
1. If this installation of Artie Workbench can see:
    * User has no Arties installed: application drops you into
      a "new Artie wizard".
    * User has exactly one Artie installed: application drops you
      into a dashboard view of that Artie.
    * User has more than one Artie installed: application displays
      a dialog that asks you to select an Artie or add a new one.

# New Artie Wizard

This Wizard does the following (all with pretty graphics, as applicable):

1. Prompts you to plug Artie's power cable in
1. Prompts you to plug into Artie's serial port USB
1. Prompts the user to supply a username and password for this Artie.
   The credentials are stored in an OS-specific way that prevents users
   from seeing them in plaintext.
1. Displays the wifi networks that Artie can see and prompts the user to
   select one and input credentials for it. These credentials are not stored
   by the GUI (they are stored by Artie's OS).
1. Collects Artie's IP address and stores it in the Artie Profile for this Artie.
1. Prompts you to give this Artie a unique name.
1. `python artie-tool.py install --username <USERNAME> --artie-ip <ARTIE IP> --admin-ip <ADMIN IP> --artie-name <ARTIE_NAME>`
    * `USERNAME` is the username you created when you logged onto Artie.
    * `ARTIE IP` is the IP address of the Artie you want to add.
    * `ADMIN IP` is the IP address of the admin server you installed.
    * `ARTIE_NAME` is the name you supplied.
    * Enter the password you used when you logged onto Artie when prompted.
    * Enter the token when prompted (this token came from the Admind installation,
      and can be found on the admin server at /var/lib/rancher/k3s/server/node-token)
1. python artie-tool.py deploy base
1. python artie-tool.py test all-hw

# Dashboard

This is the typical view. It shows a tabbed view of the following tabs:

* Hardware
    * Shows status of each single board computer (status is gleaned from the K3S status of this node).
      The status includes the Yocto image version.
    * Shows the status of each microcontroller (status is gleaned from heartbeat signal of each MCU,
      which is put on the CAN bus and reported by some application that's part of Artie base deployment),
      the status includes the firmware version.
    * Shows the status of each actuator (gleaned from the messages sent from their MCUs on CAN bus and
      reported by some application that is part of Artie base deployment)
* Software
    * Shows status of each K3S pod
* Teleop
    * Allows for manual control of Artie
* Logging
    * Allows for live viewing all the logs/telemetry coming in from the system
    * Allows for querying all so-far collected logs/telemetry from all previous sessions
* Sensors
    * Shows livestream of sensor data
* Experiment progress
    * Shows where we are in the experiment schedule
    * Allows for manual control of the experiment schedule

# Menubar

In the menu bar, you can:

* Switch between different Arties
* Choose other deployments (other Helm charts to deploy to this Artie)
