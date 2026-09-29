# ANUMAAN: A Digital Twin for Aero Piston Engines

ANUMAAN is a digital twin, fault diagnosis, and mission reliability system built for aero piston engines powering Medium Altitude Long Endurance UAVs. It replaces threshold-based, reactive engine monitoring with a physics-grounded twin that computes what an engine's telemetry should look like at its current operating point, watches for departures from that prediction, diagnoses what those departures mean, and reasons about their consequences for the mission currently in progress.

The system is built for SIH Problem Statement 26054, issued by DRDO under the Robotics and Drones theme. It spans a five-engine platform family, with the Rotax 912 iS as its most thoroughly documented reference engine, and covers the full brief the problem statement asks for: a synchronized digital twin core, sensor-level health monitoring, fault detection and predictive analytics, an AI and machine learning layer, mission simulation and replay, and an operator-facing visualization dashboard.

This site documents ANUMAAN from two directions. The Technical Documentation section explains the system itself: the physics that drives the twin, the AI and ML stack built on top of it, the mission reliability engine, and the ground control station that ties them together. The SIH Journey section documents how the team engineered the system, from first-principles research through competitive benchmarking to full software and hardware verification.

## Facts

| | |
|---|---|
| Problem statement | SIH PS-26054 |
| Issuing body | DRDO, Department of Defence R&D |
| Theme | Robotics and Drones |
| Reference engine | Rotax 912 iS, across a five-engine platform family |

## Explore the documentation

### [Technical Documentation](technical/01-introducing-ps26054.md)
How ANUMAAN works: the problem statement, the system architecture, the physics-based digital twin core, the AI and ML stack including Bio-Inspired Sparse Novelty Coding, mission planning and reliability, the dataset strategy, and the operator ground control station.

### [Our SIH Journey](journey/01-the-engineering-story.md)
How ANUMAAN was built: the research-first methodology, competitive benchmarking, bio-inspired novelty detection foundations, and the mission planning executive.
