Unnamed project (name pending)
==============================

This is a WIP.

## What is this game?
- short introduction to what the game is about + some screenshots?
Sections coming soon :D:

## How to install?

Just follow these steps:
1. Clone the repo: **TODO add link**
2. Navigate into the top level directory of the cloned  repository.
3. Open a terminal and run `uv sync`. (Only the first time or after updating.)
4. Then start the game with `uv run main.py`.

## Game Manual

### Controls
- There are two types of drives. 
  - Main thruster: powerful, but can only move straight ahead
  - Maneuvering thrusters: much weaker, but can be directed in any direction.

## KNOWN ISSUES
- The FPS drop over time for unknown reasons. (Even in the test world without any inputs.)

## immediate todo
- Proofread especially the doc after all this refactoring
- commit

## TODO
- Improve the optics
  - add a basic ship (use some existing image)
  - add an asteroid
  - add thruster animation for main thruster and maneuvering thrusters 
- Improve movement system
  - clearly separate the responsibilities of engine and dynamics
    - the dynamics should get forces. It should not be concerned with the ships max speeds, just the global ones.
    - The engine should figure out the forces it outputs. (And in case for stabilizing and rotating figure out what it has to do.)
  - Clean up the experimental values for the ship. I think the system is over specified and the values override each other.
  - Allow rotation to go the longer angle, if that would be faster due to having momentum in the direction of the long angle.
- Weapons!
- Sound!
- Upgrade System
- Implement a more general Input system that does not rely on my setup.
- Write a proper ReadMe