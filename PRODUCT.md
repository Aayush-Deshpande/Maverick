# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary (now):** DRDO / iDEX / Smart India Hackathon judges evaluating submissions for Problem Statement 26054. They open the deployed prototype (www.midnight-ciphers.in) at an unknown time, usually alone, on a laptop browser, with minutes to decide whether the team built something real.
- **Intended operators (product story):** UAV ground-station operators, propulsion engineers and maintenance crews running MALE UAVs (TAPAS BH-201 class) in high-altitude and high-heat theatres such as Ladakh and the Thar.

## Product Purpose

ANUMAAN is an AI-enabled real-time digital twin for health monitoring, fault prediction and mission-reliability support of aero piston engines in MALE UAVs (DRDO PS-26054). A single-engine UAV that suffers an in-flight shutdown is lost; ANUMAAN exists to notice a developing engine fault before a fixed redline would, explain it, and turn it into a decision. Success for the hackathon: a judge leaves convinced the system catches faults early, turns detection into decisions, is sovereign/air-gapped, and runs on real engine profiles at real scale.

## Positioning

Not a threshold dashboard. A physics observer predicts what this engine should be doing at the current altitude, throttle and outside air; calibrated residuals, a persistence gate and a reservoir classifier read the gap across channels and time; sensor-sanity quarantine separates a broken sensor from a sick engine; prognostics, mission reliability, glide reachability and ATA-chapter maintenance directives turn the finding into an action. Runs offline, on five real UAV engine profiles, with full CAD models.

## Operating Context

- Judges reach the landing page first, then the console's three workspaces: Engine runtime (multi-engine), 3D twin, Tactical GCS (legacy Rotax console with Voice Copilot, Mission Replay, CBM debrief).
- The deployed backend (Render) is shared by every visitor: fault injection and engine controls are global state.
- Simulated time runs at 20x in the multi-engine runtime (an 18 h ISR sortie in ~54 wall-clock minutes).

## Capabilities and Constraints

- Five engine profiles: Rotax 912 iS, Rotax 914, Rotax 915 iS, Austro AE300, VRDE-Jayem 2.2L (parameterised from public data; many parameters assumed).
- Runtime: virtual plant at 20 Hz, operator levers (throttle, altitude, OAT), profile-valid fault injection (misfire, cooling degradation, oil pressure loss, air filter blockage, sensor stuck, sensor bias drift), tier-0 calibrated residual detector with split-conformal thresholds and persistence gate, tier-1 reservoir readout, UKF parameter estimation, twin validity monitor, Palmgren-Miner damage with split-conformal RUL interval, 18 h ISR mission reliability, glide reachability to Ladakh airfields, deterministic ATA-chapter diagnostic agent.
- Legacy Tactical GCS: 8 DRDO fault modes, 9-stage detection pipeline, voice copilot, mission replay, CBM debrief.
- Copilot LLM default is Qwen (Chinese-origin) in parts of the code: do not claim the copilot is fully sovereign-model until changed.
- Data is simulation evidence. No live aircraft bus, no flight validation, no certified diagnosis.

## Brand Commitments

- Name: ANUMAAN (Sanskrit/Hindi "inference"). Team: Midnight Ciphers. Problem statement: DRDO SIH PS-26054.
- Full-detail Blender CAD engine models are a deliberate differentiator: never replace them with simplified or low-detail versions.
- Claim tone (confirmed 2026-11-18): confident, active voice about what the system does; one compact prototype-boundary note (simulation, advisory) rather than a caveat in every section.

## Evidence on Hand

- Live deployed prototype and backend (www.midnight-ciphers.in, anumaan-backend-5ru5.onrender.com).
- Engineering notes site: https://anumaan-doc-1797.vercel.app/
- Full CAD GLB models in `frontend/public/models/`; studio renders in `frontend/public/studio/images/`.
- Logo intro video `frontend/public/vids/Anumaan_start.mp4`. No product demo film exists yet; any film must be recorded from the real console.
- No validated accuracy numbers, benchmark wins, customers or flight trials: never state any.

## Product Principles

1. Show the mechanism working, not adjectives about it: every claim on the page should be visible in the console a click away.
2. Detection is only half: always carry a finding through to the decision it supports.
3. A judge must never meet a broken-looking state: shared demo state resets, alarms mean something, numbers are fresh.
4. Real engines at full fidelity are part of the argument.
5. Honest about the prototype boundary in one place, confident everywhere else.
