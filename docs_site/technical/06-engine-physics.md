# Engine Physics and Combustion Modeling

The expected-value side of every residual in ANUMAAN, described in [The Digital Twin Core](05-the-digital-twin.md), ultimately traces back to a physics core that simulates combustion at the level of crank angle rather than treating engine behavior as a set of prescribed signal patterns. This article covers that physics core: the reference engine constants it is built from, the slider-crank and Wiebe combustion chain that produces crank angular velocity, and why a misfire in this model is a genuine physical event rather than an authored signature.

## The problem

Vibration, torque, and misfire signatures could be approximated by hand: a sum of sine waves at expected engine orders, an impulse deleted from a train to represent a dead cylinder. That approach is enough to exercise a signal-processing pipeline, but it has a structural limitation. A detector trained against a hand-authored impulse train learns to recognize "an impulse is missing from a synthetic train," which is a circular target. It never has to face the actual physical coupling between a missed combustion event and every other observable channel, because that coupling was never modeled in the first place. ANUMAAN's physics core exists to remove that circularity: cylinder pressure, torque, and crank angular velocity are computed from first principles, so that a misfire's full signature, in vibration, in exhaust gas temperature, in angular velocity, emerges from one underlying change rather than being separately painted onto each channel.

## Reference engine constants

The physics core is built from published, verifiable Rotax specifications. The Rotax 912 iS and 914 are both four-cylinder, horizontally opposed, four-stroke engines. The 912 iS has an 84.0 mm bore and 61.0 mm stroke, giving 1,352 cm3 displacement, with a 10.8:1 compression ratio. The 914 has a 79.5 mm bore with the same 61.0 mm stroke, giving 1,211.2 cm3 displacement, with an 8.75:1 compression ratio. Both engines share a 1-4-2-3 firing order, sourced from the manufacturer's maintenance manual. These constants, plus the published gear reduction ratio, anchor every downstream calculation to a real, citable engine rather than an arbitrary parameter set.

## Slider-crank kinematics

Piston position, velocity, and acceleration are derived from the classical slider-crank relationship, with crank radius `r` equal to half the stroke, connecting rod length `l`, and `lambda = r / l`:

```
Piston displacement from TDC:
    x(theta) = r(1 - cos theta) + l(1 - sqrt(1 - lambda^2 sin^2 theta))

Piston velocity (per unit crank rate):
    dx/dtheta = r sin theta * [1 + (lambda cos theta) / sqrt(1 - lambda^2 sin^2 theta)]
```

Cylinder volume follows directly from piston position: swept volume from bore and stroke, clearance volume from the compression ratio, and total volume `V(theta)` as clearance volume plus piston area times displacement. This kinematic chain is computed once per crank angle and reused throughout the cycle, since it depends only on crank angle, not on engine state.

## Wiebe heat release

Combustion is modeled with the Wiebe function, the standard empirical burn-rate correlation used in zero-dimensional combustion simulation. Mass fraction burned as a function of crank angle is:

```
x_b(theta) = 1 - exp(-a * ((theta - theta_0) / delta_theta)^(m+1))
```

for crank angle between combustion start `theta_0` and `theta_0 + delta_theta`, with `x_b = 0` before ignition and `x_b = 1` after burn completion. The burn rate `dx_b/dtheta`, obtained by differentiating this expression, multiplied by total heat release `Q_total` (fuel mass per cycle times lower heating value times combustion efficiency), gives the heat release rate `dQ/dtheta` that drives cylinder pressure.

This is the single point in the model where combustion faults are introduced, and it is what keeps the approach physically honest: a misfire sets `Q_total` to zero for one cylinder on one cycle. A partial burn or injector fault scales `Q_total` down rather than zeroing it. A slow burn from degraded ignition stretches the burn duration `delta_theta`. Combustion instability applies cycle-to-cycle random jitter to `theta_0`, `delta_theta`, and `Q_total` together. Every fault is a modification to a physical parameter feeding the heat release equation, never a direct edit to an output waveform.

## Cylinder pressure to torque to crank dynamics

Cylinder pressure is obtained by integrating the single-zone first law of thermodynamics over the 720-degree four-stroke cycle:

```
dp/dtheta = (gamma - 1) / V(theta) * dQ/dtheta - gamma * p / V(theta) * dV/dtheta
```

with the ratio of specific heats `gamma` around 1.35 for the burned mixture, integrated across intake, compression (polytropic), combustion and expansion (the equation above), and exhaust phases.

Pressure converts to torque through two components. Gas torque comes from the pressure force acting through the slider-crank geometry: `F_gas(theta) = (p(theta) - p_crankcase) * A_p`, then `T_gas(theta) = F_gas(theta) * dx/dtheta`. Inertial torque comes from the reciprocating mass being accelerated by the crank motion itself, and it is not a negligible refinement: it is comparable in magnitude to gas torque at cruise and higher engine speeds, and a model that omits it produces an unrealistically clean angular velocity waveform that would not transfer to a detector meant to work on real data. The four cylinders' torque contributions are summed, phased 180 degrees apart following the 1-4-2-3 firing order, to give total instantaneous torque.

Total torque then drives the crank dynamics equation directly:

```
J * domega/dt = T_total(theta) - T_load(omega)
dtheta/dt = omega
```

where `J` is crank and flywheel inertia and `T_load` is the propeller load through the reduction gearbox plus accessory drag. Integrating this equation over crank angle produces the model's key output signal: `omega(theta)`, instantaneous crankshaft angular velocity.

```mermaid
flowchart LR
    Wiebe[Wiebe heat release] --> Press[Cylinder pressure, first law]
    Press --> GasT[Gas torque]
    Kin[Slider-crank kinematics] --> GasT
    Kin --> InertT[Inertial torque]
    GasT --> Sum[Total torque, 4 cylinders phased 1-4-2-3]
    InertT --> Sum
    Sum --> Crank[Crank dynamics: J domega/dt = T minus load]
    Crank --> Omega[omega(theta)]
```
*Caption: the physics chain from combustion heat release to instantaneous crank angular velocity.*

## Why misfire emerges from physics rather than being authored

A healthy cylinder contributes a torque pulse during its power stroke that accelerates the crank. A misfiring cylinder, with `Q_total` set to zero for that cycle, contributes no gas torque during its stroke, so angular velocity decelerates through that 180-degree window instead of accelerating. Because the deficit appears specifically within the misfiring cylinder's own angular window, cylinder identity comes directly from crank phase rather than from a separate classification step, which is the same principle underlying established crank-angle-based misfire detection in the automotive literature.

Every other downstream signature follows from the same underlying change. With no heat release in that cylinder, its exhaust gas temperature reading drops because there is no combustion gas to heat it, on a thermal lag of roughly five to twenty seconds. The engine's vibration signature shows a rise in half-order energy, because a dead cylinder makes the firing pattern repeat once per full 720-degree cycle instead of once per 180-degree stroke, injecting energy at half-integer orders that a healthy four-cylinder four-stroke engine (dominant at order 2) does not produce. None of these three signatures, the angular velocity dip, the EGT drop, the half-order vibration rise, is separately scripted. They are three independent observations of one physical event, which is what makes their agreement diagnostically meaningful rather than coincidental, a property used directly in cross-domain fault corroboration.

Per-cylinder torque deficit at each cylinder's own firing angle is also the basis for combustion instability detection: cycle-to-cycle variation in that same quantity serves as a coefficient-of-variation proxy for combustion stability, since the engine has no cylinder-pressure sensor of its own to measure true indicated mean effective pressure directly.

## Order tracking as a companion method

Because a UAV engine's shaft speed changes continuously with throttle, analyzing vibration with fixed frequency bins loses resolution as speed changes. The system instead uses tach-synchronous order tracking: angular resampling that converts a time-domain vibration signal into the angle domain, so that a given mechanical event, a gear mesh, a bearing defect, a cylinder firing, lands at the same order regardless of engine speed. Hilbert envelope demodulation is applied on top of this to reveal amplitude-modulated bearing and gear defect signatures that a raw spectrum would otherwise hide. This order-domain view serves as a confirmatory check alongside the segmented torque-deficit method above: a healthy engine shows dominant energy at order 2, while a misfiring cylinder shows order 0.5 and order 1 energy rising and order 2 falling, a speed-invariant ratio that corroborates what the torque-deficit method already attributes to a specific cylinder.

## Honest limits

The physics core is single-zone with no explicit heat transfer submodel; wall heat loss is folded into the combustion efficiency term rather than computed from a correlation, which is adequate for relative fault signatures but not for absolute efficiency prediction. Gas dynamics, intake and exhaust wave action, and valve-overlap scavenging are not modeled; manifold pressure is imposed rather than computed from first principles. The crankshaft is treated as rigid with lumped inertia, so torsional compliance and drivetrain resonance are not represented. These are stated as scope boundaries of the current simulation-grounded implementation, not defects, and they define exactly what a future flight-hardware validation phase would need to characterize.

## Related systems

- [The Digital Twin Core](05-the-digital-twin.md)
- [Residual Analysis](08-residual-analysis.md)
- [Telemetry and Sensor Intelligence](07-telemetry-and-sensors.md)
- [Introducing ANUMAAN](03-introducing-anumaan.md)
