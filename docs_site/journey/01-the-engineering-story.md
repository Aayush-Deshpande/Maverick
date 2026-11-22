# Our Story: From an Empty Screen to a Working Twin

When the problem statements for Smart India Hackathon (SIH 2026) were announced, most college teams were naturally looking for web apps, booking systems, or automated chatbots. We scrolled past dozens of ideas until one title stopped us in our tracks:

**PS-26054 (DRDO): "AI-Enabled Real-Time Digital Twin for Health Monitoring, Fault Prediction, and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs."**

It sounded massive. It sounded terrifying. Aero piston engines? Medium-Altitude Long-Endurance (MALE) drones? Real-time thermodynamics? Unscented Kalman Filters?

None of us were aerospace scientists. We were undergraduate engineering students who loved building things. Some friends in college advised us to pick an easier problem statement with ready-made tutorials on YouTube. But something about this problem pulled us in. We thought: *If we are going to spend months of our college lives building something, why not build something that actually matters for our national defense?*

We chose PS-26054, formed our team, and began our journey.

---

## 2 September: The Visit to DRDO Pune that Changed Everything

Reading manuals and research papers in our college library was one thing, but we quickly realized that we could not build a defense system by guessing. We needed to understand what happens in the real world.

On 2nd September, our team traveled to Pune to visit the **DRDO Research & Development Establishment (Engineers) - R&DE (Engrs)**.

![Our visit to the gates of DRDO R&DE (Engrs) in Pune on 2nd September](/images/DRDO.webp)

Walking up to that gate in Pune was a turning point for us. Seeing the facility, talking with experienced mentors and understanding the sheer scale of Indian defense research made everything very real.

During our discussions, the reality of unmanned aerial vehicle operations became crystal clear:
1. **The stakes are huge:** A MALE UAV like Tapas or Rustam is not a small toy drone. It is a multi-million-rupee military asset designed for critical surveillance and border reconnaissance.
2. **The flight conditions are brutal:** These aircraft fly missions that last 18 to 24 hours. They take off in the scorching +50°C summer heat of Rajasthan deserts, climb through turbulent air, and loiter over the freezing -40°C mountain peaks of Ladakh at 25,000 feet.
3. **There is no roadside assistance in the sky:** If a cylinder starts misfiring, if an oil seal cracks, or if the turbocharger begins to lag over hostile terrain, a pilot cannot pull over. The ground operator has only seconds to detect the problem, decide whether to abort, and glide the aircraft back safely.

When we walked out of the DRDO gates on 2nd September, our mindset had completely shifted. This was no longer just a college project to get good grades or win a certificate. We promised ourselves that ANUMAAN would not use fake dummy data or pre-recorded demo graphs. Every single number, every single temperature rise, and every single fault alarm had to be backed by real physics.

---

## Sleepless Nights, Hostel Labs, and Endless Cups of Chai

The weeks following our DRDO visit were some of the most intense, exhausting, and rewarding weeks of our college lives.

Our typical day started with morning college lectures, followed by lab practicals, and then heading straight to the computer labs or cramming into a hostel room. Work would start at 6:00 PM and easily stretch until 4:00 AM.

![Late night hackathon grind with code, coffee, and textbooks](/assets/playwright/01_runtime_workspace.png)

Anyone who walked into our workspace during those weeks would see:
* Laptops running hot with fans spinning at maximum speed.
* Tables covered in handwritten equations of engine kinematics and gas laws.
* Multiple Blender tabs trying to clean up heavy 3D CAD meshes.
* Sticky notes on the walls tracking bugs that refused to go away.
* Mountains of paper cups from late-night canteen chai and empty biscuit packets.

Balancing semester exams, submission deadlines, and hackathon development pushed us to our limits. There were days when we were completely drained of energy, running on three hours of sleep, debating each other over how a graph should look or why a sensor reading was drifting.

---

## The Bugs That Kept Us Awake

Building a real-time digital twin from scratch is not smooth sailing. We ran into walls almost every single day:

* **The 3D Engine Meltdown:** When we first imported the Rotax 912 engine model into WebGL, the browser tab froze instantly. The model had hundreds of thousands of raw polygons. Our laptops stuttered, and the page took 45 seconds just to load. We had to spend days learning Draco mesh compression and separating the engine into individual components so we could highlight a single faulty spark plug without lagging the user interface.
* **The Infinity Math Bug:** In the first week of our physics engine, every time we accelerated the simulated engine to 5,000 RPM, the calculated cylinder pressure would suddenly explode to `NaN` (Not a Number) and crash the entire backend. It took us until 3:00 AM one night to realize we had passed an angle in degrees instead of radians into the mathematical sine function.
* **The CAN Bus Mystery:** Real aircraft engines talk to avionics computers over a digital network called the CAN bus. None of us had parsed raw CAN hex frames before. We sat with technical manuals, breaking down 29-bit message IDs and byte masks by hand until our eyes burned, making sure our system could read live engine frames at 20 times every second without dropping a single packet.

---

## The 3:30 AM Breakthrough

Every student who has built a complex project knows that one magical moment where everything finally clicks.

For us, it happened at around 3:30 in the morning on a Tuesday.

We had spent four consecutive nights connecting the physics backend to the real-time WebSocket telemetry stream and the 3D visualizer. We started the engine simulation, set the virtual throttle to cruise at 5,000 RPM, and clicked the button to inject **Fault F01: Ignition Misfire on Cylinder 2**.

For the first time ever:
1. The simulated engine rotational speed dropped noticeably from the loss of combustion torque.
2. The exhaust temperature on Cylinder 2 plummeted from 780°C down to ambient cold.
3. The vibration chart showed a sharp, distinct pulse at half-order engine frequency.
4. On the 3D model, Cylinder 2 smoothly illuminated in warning amber.
5. The diagnostic panel immediately diagnosed: *"Cylinder 2 Ignition Misfire (Confidence: 99.4%)"*.

Nobody spoke for about three seconds. Then the entire room erupted in cheers. We high-fived, woke up a few friends in the neighboring room, and poured ourselves another round of victory chai.

All those hours of reading thermodynamics textbooks, debugging matrix math, and fixing shader glitches had actually worked. We had built a living, breathing digital twin of an aircraft engine.

---

## Moving Forward to the Evaluation

Building the software was only the first half of the battle. The next hurdle was standing in front of our college professors and technical judges to prove that our system was real, reliable, and ready for defense evaluation.

Read the next chapter: [Facing the Evaluators: College Round to the Grand Finale](02-preparing-for-evaluation.md).
