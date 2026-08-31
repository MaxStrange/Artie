# Artie

**This code is pre-release: you cannot yet build an Artie bot - not all of the software and hardware is ready!**

Artie is an open source developmental robotics platform. This repository is the
documentation hub and the place to start; the software itself lives in the component
repositories listed below.

The purpose of Artie is twofold: data collection and testing developmental robotics theories.

The vision is that Artie will be fully open source, 3D-printable, and as cheap as is feasible,
while still being easy to use and extend.

## The repositories

| Repository | What it is |
|---|---|
| **Artie** (this one) | Documentation, architecture, getting started. Cite this repository. |
| [ArDK](https://github.com/ArtieBots/ArDK) | The Artie Development Kit: the libraries you write applications and drivers against, the platform services, the base Docker image, and the protocol specifications. |
| [ArtieTool](https://github.com/ArtieBots/ArtieTool) | Builds, tests, flashes and deploys everything. Installs the `artie-tool` command. |
| [ArtieWorkbench](https://github.com/ArtieBots/ArtieWorkbench) | The graphical application most people use to set up and drive an Artie. |
| [ArtieCLI](https://github.com/ArtieBots/ArtieCLI) | A command line interface to a running Artie, for testing and low-level debugging. |
| [ArtieDaemons](https://github.com/ArtieBots/ArtieDaemons) | Host daemons for the Kubernetes cluster an Artie runs on. |
| [Artie00](https://github.com/ArtieBots/Artie00) | The first Artie: its hardware manifest, bill of materials, firmware, drivers and schematics. |

Your own code stays in your own repository. You depend on Artie's libraries, build your
applications and firmware into images following the usage guidelines, and deploy them
with Helm - normally through Artie Workbench or Artie Tool. Nothing about Artie asks you
to build on top of a checkout of Artie.

## Get Started

**Looking for the contributing guide?** [See here](./CONTRIBUTING.md)

### Using Artie

Most people want Artie Workbench, which installs Artie Tool along with it:

```bash
pip install artieworkbench
artie-workbench
```

If you would rather work from a terminal, or you are automating something:

```bash
pip install artietool
artie-tool workspace status    # where each component resolves to
artie-tool workspace sync      # clone the components you want to build from source
artie-tool build all
artie-tool deploy artie
```

Artie Tool reads its configuration from `~/.artie/config.yaml`, from `ARTIE_*` environment
variables, and from command line arguments, in increasing order of precedence. Point a
component at a checkout of your own and Artie Tool will build from it and never overwrite
it:

```yaml
# ~/.artie/config.yaml
workspace: ~/artie-workspace
repos:
  ardk: { path: ~/repos/ArDK }   # your working copy; sync leaves it alone
```

Which versions of the components make a working Artie is stated by a release manifest -
see [versioning and releases](./docs/contributing/versioning.md). That manifest is what to
attach to an experiment's data and cite in a paper.

Before you can use Artie, you need to build him.

**Please note:** you cannot yet build an Artie! These instructions will certainly change, the bill of materials
will change, the schematics will change, etc.

### Building Artie

Building Artie is composed of the following steps:

1. Get your parts
1. Flash the parts
1. Build your bot

[See here for the full instructions](./docs/building/building-artie-main.md)

### Artie Out of the Box

Once you have built an Artie, [see here for instructions on using your Artie](./docs/out-of-the-box/getting-started.md).

## Motivation

### Why Developmental Robotics?

Developmental robotics is the study of human development by means of simulating it.
It is an important field of study for at least the following reasons:

1. Developmental robotics informs the study of human development. What better way to test a theory
   of how a human develops than to try to build a human?
1. Developmental robotics informs the study of artificial intelligence. AI can benefit from any advances
   in our understanding of human intelligence.
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
In fact, when you try to go from a theory to a physical implementation, you always find that the theory
was underspecified: in implementing the theory, you have to make decisions about things that the theory
did not address. This process of implementation forces you to refine the theory and address gaps that
you did not know existed.

Nonetheless, there is a place for virtual simulation in developmental robotics, and Artie
will hopefully incorporate a simulator, since working with an actual robot is way less convenient
than working in a video game, but this simulator is a long way off for now. Get in touch if
you'd like to help build it!

One last thing about robots: embodiment is a two-way street. Though you can get by to an extent with
datasets that are impersonal and aggregated (as in the typical supervised learning paradigm of machine learning),
humans do not learn this way. Humans learn from interacting with their environment and by their environment
interacting with them. Parents speak directly to their children using infant-directed speech, based on
what their children are currently doing. Teenagers navigate social environments that are unique to their
particular group of friends. Young adults take elective classes at university that are interesting to them.
*An intelligent agent has an active, often causative relationship with the data from which it learns.*
Hence, you need to place the subject into an environment to truly study the development of natural intelligence.

Finally, robots are awesome!

### Why not Buy a Robot that Already Exists?

We found that we needed a robot that fulfilled the following criteria:

* Open Source - both hardware and software
* Affordable - we wanted to be able to build multiple copies of the robot without grant funding.
  We think this is key: robotics research is slowly coming to the masses of hobbyists, students,
  and citizen scientists, but developmental robotics research is still mostly confined to well-funded labs.
* Designed for Developmental Robotics - many existing robots are designed for other purposes,
  such as research in traditional robotics, human-robot interaction, or AI. These robots never
  take into account the specific needs of developmental robotics research, such as the physical constraints
  of a human infant, or the physiological requirements of various sensor components. Artie is designed
  from the ground up with developmental robotics in mind: we have compromised on biomimicry only as far
  as is absolutely necessary to make the robot affordable and buildable.
* Modular and Extensible - we wanted a robot that could be easily modified, extended, and repaired.
  Research moves quickly, and we wanted a robot that could keep pace.
  We also wanted a robot that could be customized to fit the needs of different researchers
  and different experiments, which means that we aren't building a robot - we are building a robotics ecosystem.
* Easy to Build - we wanted a robot that could be built by a single person with moderate technical skills
  and a small budget. This means that we had to make the robot as easy to assemble as possible,
  while still maintaining the other criteria.
* Professional grade - we wanted a robot that was reliable and fun to use. Every layer of Artie's
  software stack is designed to be robust, maintainable, and to follow engineering best practices,
  so that researchers can focus on their research, not on debugging the robot.
* Data provenance and reproducibility - we wanted a robot that could keep track of where its data came from, so that
  researchers can be sure that their experiments are reproducible and that their data is trustworthy.
  Artie uses containerization and orchestration to ensure that software environments are consistent
  across different deployments. Additionally, even the single board computers are running custom
  Linux images built using Yocto, so that the entire software stack is under control: if it worked once,
  it should work every time; you are running an experiment with Artie, not just getting him to work this one time.
* Fun to use - we wanted a robot that was enjoyable to work with, both for researchers and for
  the subjects of experiments. A robot that is engaging and appealing is more likely to elicit
  natural behaviors from human subjects, which is crucial for developmental robotics research.

Alternatives exist, but they don't meet these criteria. For example, there's:
  - [Poppy](https://www.generationrobots.com/en/312-poppy-humanoid-robot), which is about $10k USD,
    and while it's open source and extensible, it's not designed specifically for developmental robotics,
    with very little biomimicry.
  - [Nao](https://en.wikipedia.org/wiki/Nao_(robot)), which is about $15k USD, and while it is well-regarded
    and used extensively, its hardware is not extensible or modifiable, and it
    is designed more for human-robot interaction than developmental robotics. Again, very little biomimicry.
  - [iCub](https://icub.iit.it/products/product-catalog), which is about$250k USD, and while it is
    designed for developmental robotics and has a high degree of biomimicry, its cost
    makes it inaccessible to most researchers.
  - [Berkeley Humanoid Lite](https://lite.berkeley-humanoid.org/), which is about $5k USD, and while it is affordable
    and open source, it is not designed specifically for developmental robotics, again with very little biomimicry
    in mind.

Additionally, we did not use ROS (Robot Operating System) as the basis for Artie's software stack.
While ROS is a great tool for traditional robotics development, we felt it was not well-suited
for reproducible developmental robotics research. ROS's architecture is not designed
for containerization and orchestration, which are key to ensuring that experiments
are reproducible and that software environments are consistent across different deployments.
Also, while ROS has a huge ecosystem and excellent community support/adoption, it is too general purpose
for our needs: we wanted a software stack that was specifically designed for developmental robotics and for research.
Really the only thing that we could have used from ROS was its inter-process communication (IPC) mechanisms.
I suppose its physics simulator would have been nice, too.
