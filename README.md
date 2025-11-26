# Rigacar

## Fork

_This fork supports **Blender 4.0+** and consolidates fixes from the community while the maintainer is absent._

## Overview

Rigacar is a Blender addon that generates complete car rigs with animation and deformation controls. This fork is inspired by and reverse-engineered from [Traffiq](https://polygoniq.com/software/traffiq/) by Polygoniq, adapting its rigging and animation concepts for the open-source Rigacar addon.

It's designed to fulfill the following goals:

* Generate a complete rig in seconds for standard car models
* Automate wheel and steering animations with multiple baking strategies
* Enable efficient animation baking for real-time engine exports
* Manage ground detection and suspension dynamics
* Support door and trunk rigging and animation

## Features

### Core Rigging
* Automatic car skeleton generation with deformation controls
* Suspension simulation with pitch and roll factors
* Ground sensor system for wheel-ground interaction

### Animation & Baking
* **Steering Wheel Baking**: Automatically rotates steering wheel based on front wheel angles
* **Wheels Rotation Baking**: Rotates wheels based on car movement with skid detection
* **Drift Baking**: Handles wheel rotation during drift scenarios
* **Ground Projection**: Automatic wheel positioning based on ground geometry
* Clear/reset animation keyframes functionality

### Mesh Organization
* Automatic wheel and brake grouping with configurable naming conventions
* Support for multiple wheel configurations (extra wheels, brake assemblies)
* Mesh consolidation tools for optimized export

### Doors & Trunks
* Bone creation operators for door and trunk rigging
* Custom animation controls for opening/closing mechanisms

Please read [full documentation](http://digicreatures.net/articles/rigacar.html) on the original website.

You can also watch the series of video tutorials:

[![Rigacar Part 1](http://img.youtube.com/vi/D3XQxA_-TzY/0.jpg)](https://www.youtube.com/watch?v=D3XQxA_-TzY&list=PLH_mmrv8SfPFiEj93RJt3sBvHCnipI9qK "Rigacar video tutorials")
