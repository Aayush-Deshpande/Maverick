# SIH Problem Statement 26054

Smart India Hackathon Problem Statement 26054 was issued by the Defence Research and Development Organisation, under the Department of Defence R&D, in the Software category under the Robotics and Drones theme. Its title is AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs.

The statement asks for something specific and bounded: a digital twin, not a dashboard; a system that predicts and reasons about mission reliability, not one that merely displays sensor values after they cross a limit. This article introduces the problem on its own terms, as DRDO framed it, before describing how ANUMAAN answers it.

## Background

Medium Altitude Long Endurance UAVs fly long Intelligence, Surveillance, and Reconnaissance missions, communication relay, maritime surveillance, and strategic defence sorties, often many hours in duration. Propulsion reliability is central to all of them, because a piston-engine failure in flight can end a mission in one of three ways: an aborted sortie, the loss of the airframe, or a forced recovery under unsafe conditions. None of these outcomes are acceptable on a routine basis for a platform expected to fly repeated long-endurance missions.

The problem statement identifies a specific weakness in how these engines are currently watched. Conventional UAV engine monitoring is threshold-based and reactive: a parameter crosses a fixed limit, a warning fires, and by that point the fault has typically already progressed past its earliest, most treatable stage. These systems offer limited or no estimate of Remaining Useful Life, no meaningful degradation trend tracking, and no way to simulate how the engine would behave under a specific future mission profile before that mission is flown.

The stated remedy is a Digital Twin framework: a continuously synchronized virtual representation of the physical engine, built from live sensor data, physics-based models, and AI/ML techniques, intended for eventual deployment in defence-grade ground control stations, engine test rigs, and fleet-level health monitoring infrastructure.

## The expected solution, parts A through F

The problem statement decomposes the expected system into six coordinated parts.

**A. Digital Twin Core Framework.** A virtual engine model kept synchronized with live engine data, built as a modular architecture so it can scale to new engines or platforms, with real-time data ingestion as a baseline capability.

**B. Health Monitoring System.** Continuous assessment of engine subsystem condition and generation of health indices for predictive maintenance, across eight monitored parameter groups: RPM, Cylinder Head Temperature, Exhaust Gas Temperature, oil pressure and temperature, fuel flow, vibration signatures, battery and alternator health, and injection timing parameters.

**C. Fault Detection and Predictive Analytics.** A transition from threshold-based monitoring to predictive diagnostics, targeting eight specific detection and prediction problems: misfire conditions, injector abnormalities, cooling degradation, lubrication issues, sensor drift or failure, combustion instability, overheating trends, and abnormal vibration patterns.

**D. AI/ML Layer.** Adaptive learning capability supporting anomaly detection algorithms, Remaining Useful Life estimation, trend analysis, and predictive maintenance recommendations.

**E. Simulation and Replay Capability.** Reproduction of engine behavior for mission analysis: replay of historical mission data, environmental condition simulation, and behavior simulation across specific stress cases including high-altitude operation, endurance missions, hot-weather operation, and rapid throttle transitions.

**F. Visualization Dashboard.** An operational interface for UAV operators, propulsion engineers, and maintenance teams covering real-time engine health status, fault alerts, efficiency trends, maintenance advisories, and mission-wise health reports.

The problem statement also names desired innovation areas without mandating them: physics-informed AI, edge AI for UAV applications, lightweight onboard analytics, hybrid thermodynamic and data-driven models, federated learning, explainable AI for fault diagnosis, secure telemetry architecture, and autonomous maintenance advisory systems. It expects participating teams to demonstrate understanding of IC engine fundamentals, UAV propulsion systems, sensor fusion, embedded systems, CAN communication, AI/ML analytics, data visualization, simulation modelling, and reliability engineering.

## Expected deliverables

Teams are expected to produce a functional prototype or software demonstrator, a digital twin architecture design, an engine simulation model, an AI/ML-based anomaly detection module, a visualization dashboard, a demonstration using simulated or real engine datasets, and technical documentation with a deployment roadmap.

Two things are worth being precise about. First, the problem statement explicitly permits simulated datasets for the demonstration; it does not require flight hardware access, which no participating team has. Second, the title names three outcomes, not two: health monitoring, fault prediction, and mission reliability enhancement. The first two are the part of this problem most teams converge on. The third, mission reliability, asks for something further: not just knowing the engine's condition, but computing what that condition means for whether the current mission can still be completed. That distinction becomes the throughline of how ANUMAAN is built, and it is the subject of the next article.

## Related systems

- [Understanding the Engineering Problem](02-the-engineering-problem.md)
- [Introducing ANUMAAN](03-introducing-anumaan.md)
- [System Architecture](04-system-architecture.md)
