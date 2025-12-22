# Artie

**This code is pre-release: you cannot yet build an Artie bot - not all of the software and hardware is ready!**

The purpose of Artie is twofold: data collection and testing developmental robotics theories.

The vision is that Artie will be fully open source, 3D-printable, and as cheap as is feasible,
while still being easy to use and extend.

## Get Started

**Looking for the contributing guide?** [See here](./CONTRIBUTING.md)

Before you can use Artie, you need to build him.

**Please note:** you cannot yet build an Artie! These instructions will certainly change, the bill of materials
will change, the schematics will change, etc.

### Building Artie

Building Artie is composed of the following steps:

1. Get your parts
1. Flash the parts
1. Build your bot

[See here for the full instructions](./docs/building/building-artie-main.md)

### Using Artie

The Artie ecosystem consists of the following:

* *Artie*: The actual robot itself - the PCBs, 3D printed parts, the single board computers (SBCs),
           microcontroller units (MCUs), sensors, actuators, LCDs, etc.
    - *Firmware*: The MCU firmware.
    - *Yocto Images*: The custom embedded Linux images.
    - *Libraries*: Libraries shared between all the software components.
    - *Drivers*: Applications that run on the SBCs and interface with hardware.
* *Artie CLI*: The simplest way to control a physical Artie. Used mostly for testing.
* *Artie Tool*: A single tool to flash, test, build, release, etc.
* *Artie Workbench*: A web app that allows an authenticated user to control and configure Artie.
* (Planned) *Demo Stack*: A demo that uses traditional robotics algorithms to control Artie.
* (Planned) *Reference Stack*: A reference implementation of developmental robotics theories used to control Artie.
* (Planned) *Simulator*: A simulated environment and simulated Artie for training and testing without a physical bot.

Artie is meant to be used to collect data in real-life social situations as well as to test
theories of developmental robotics.

### Artie Out of the Box

There are three planned ways to deploy an Artie:

* **Cloud**
  - You own, operate, and maintain Artie's hardware
  - Artie compute required for administration is provided by the cloud
  - Any additional compute required for experiments or workload is provided by the cloud
  - [See here for how to get started with this route](./docs/out-of-the-box/cloud.md)
* **Fog**
  - You own, operate, and maintain Artie's hardware
  - Artie compute required for administration is owned, operated, and maintained by you in the same network as Artie
  - Any additional compute required for experiments or workload is provided by the cloud
  - [See here for how to get started with this route](./docs/out-of-the-box/fog.md)
* **Edge**
  - You own, operate, and maintain Artie's hardware
  - Artie compute required for administration is owned, operated, and maintained by you in the same network as Artie
  - Any additional compute required for experiments or workload is provided by you locally in the same network as Artie
  - [See here for how to get started with this route](./docs/out-of-the-box/edge.md)

**Note that since Artie is so early in development, none of these are viable options yet!**
**Additionally, Edge is the highest priority for development, while the other options are ones I hope to get to, but may not.**

## Motivation

### Why Developmental Robotics?

Developmental robotics is the study of human development by means of simulating it.
It is an important field of study for at least the following two reasons:

1. Developmental robotics informs the study of human development. What better way to test a theory
   of how a human develops than to try to build a human?
1. Developmental robitics informs the study of artificial intelligence. Although not typically the main
   focus of developmental robotics, AI can benefit from any advances in our understanding of human intelligence.
1. Developmental robotics informs the study of robotics. Building a robot always involves solving difficult
   engineering problems. Building a robot that can learn and adapt like a human is even more difficult,
   and any advances in this field will likely have applications in more traditional robotics or in soft robotics.

Here's a great excerpt from Wikipedia:

> As in human children, learning is expected to be cumulative and of progressively increasing complexity,
  and to result from self-exploration of the world in combination with social interaction.
  The typical methodological approach consists in starting from theories of human and animal development
  elaborated in fields such as developmental psychology, neuroscience, developmental and evolutionary biology,
  and linguistics, then to formalize and implement them in robots

Developmental robotics is such a cool field. I wish way more people were interested in it.

### Embodiment

A central tenet of developmental robotics is that embodiment (agency) is necessary for intelligence.
Human intelligence stems from a need to manipulate the world and ourselves in response to the world.
It does not exist in a vacuum. Hence, it makes sense to embody an intelligent agent in a physical
(or at least virtual) world.

### Why a Robot?

If developmental robotics is the study of human development by means of simulating it, why
build an actual robot? Why not just simulate one in a physics simulator?

The answer is simple: humans aren't simulated - they exist in a messy, physical world. Any theory
of how a human develops must ultimately be put to the test in the same world with the same parameters.

Nonetheless, there is a place for virtual simulation in developmental robotics, and Artie
will hopefully incorporate a simulator, since working with an actual robot is way less convenient
than working in a video game.

One last thing about robots: embodiment is a two-way street. Though you can get by to an extent with
datasets that are impersonal and aggregated (as in the typical supervised learning paradigm of machine learning),
humans do not learn this way. Humans learn from interacting with their environment and by their environment
interacting with them. Parents speak directly to their children using infant-directed speech.
Teenagers navigate social environments that are unique to their particular group of friends.
Young adults take elective classes at university that are interesting to them.
*An intelligent agent has an active, often causative relationship with the data from which it learns.*
Hence, you need to place the subject into an environment to truly study the development of natural intelligence.

Also, robots are awesome!

### Why not Buy a Robot that Already Exists?

A few reasons:

* They're so expensive. Holy crap are they expensive:
  - [Poppy](https://www.generationrobots.com/en/312-poppy-humanoid-robot) ~ $10k
  - [Nao](https://en.wikipedia.org/wiki/Nao_(robot)) ~ $15k
  - [iCub](https://icub.iit.it/products/product-catalog) ~ $250k
* Affordable ones cannot feasibly be used to study human development:
  - [Hiwonder](https://www.robotshop.com/products/hiwonder-tonypi-ai-intelligent-vision-humanoid-robot-powered-by-raspberry-pi-4b-4gb-advanced-kit)

Artie is built from the ground up explicitly for the purpose of developmental robotics.
He's also open source, and as cheap as is feasible (though it turns out, that's still
pretty expensive).
