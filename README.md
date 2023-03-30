# Artie

This repository contains the code for a robot that I am slowly working on.

The purpose of Artie is twofold: data collection and testing developmental robotics theories.

The vision is that Artie will be fully open source, 3D-printable, and as cheap as is feasible,
while still being easy to use and extend.

## Get Started

Before you can use Artie, you need to build him.

### Building Artie

Building Artie is composed of the following steps:

1. Get your parts
1. Flash the parts
1. Build your bot

[See here for the full instructions](./docs/building/building-artie-main.md)

### Deploying Experiments

Once you have a functioning Artie, feel free to play around with the following:

* [Command Line Interface (CLI)](./cli/README.md) - this is a way to interface with Artie on a low-level. Use
  this for things like testing his electrical and hardware connections.
* [Use a pre-defined experiment](./docs/deploying/deploying-pre-built-experiments.md) - Artie makes use of experiment
  configuration files to deploy experiments. There are a few already ready to go.
* [Make your own experiment](./docs/deploying/custom-building-experiments.md) - Once you are comfortable with Artie,
  you can start defining your own experiments.

Artie is meant to be used to collect data in real-life social situations as well as to test
theories of developmental robotics.

## Motivation

### Why Developmental Robotics?

Developmental robotics is the study of human development by means of simulating it.
It is an important field of study for at least the following two reasons:

1. Developmental robotics informs the study of human development. What better way to test a theory
   of how a human develops than to try to build a human?
1. Developmental robitics informs the study of artificial intelligence. Although not typically the main
   focus of developmental robotics, AI can benefit from any advances in our understanding of human intelligence.

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
Hence, you need to place the subject into
an environment to truly study the development of intelligence.

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
He's also open source, and as cheap as is feasible (though it turns out, that that's still
pretty expensive).
