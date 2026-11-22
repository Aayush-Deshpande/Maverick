# Facing the Evaluators: College Round to the Grand Finale

Building a complex engineering project in the quiet hours of the night is one thing. Standing in front of a panel of senior professors and technical judges to defend your work is a completely different ballgame.

In November, after weeks of relentless coding, we reached our first major milestone: the **Institute-Level Presentation and Evaluation Round** at our college (JSPM RSCOE Innovation and Incubation Foundation - IIF).

This was the hurdle that would decide whether ANUMAAN would be selected to represent our college in the Smart India Hackathon.

---

## The Nervous Energy Outside the Room

On the morning of the presentation, the hallway outside the incubation foundation room was packed with teams. Every group was pacing up and down, reviewing PowerPoint slides, adjusting ties, and doing last-minute dry runs.

We were nervous, but we made a conscious decision: **no boring slide decks**.

Almost every team was planning to present 20 slides filled with bullet points and static screenshots. We decided to do something bolder. We decided to walk in, introduce our project briefly, open our laptops, and run the complete system live in front of the judges.

Running a live demo during an evaluation is notoriously risky. If the local server crashes, if a WebSocket drops, or if a browser memory leak occurs, the presentation can fall apart in seconds. But we had tested ANUMAAN so many times that we trusted our code.

---

## Walking into the Presentation Room

When our turn was called, we walked into the glass-walled discussion room. Sitting across the wooden desk were our evaluators: senior professors and technical mentors with years of academic and industrial experience.

![Presenting our live digital twin to the college evaluators and professors](/images/sih-2026-1.jpg)

We plugged in our laptops, launched the backend simulation server, opened the Flight Deck console, and began our story.

We did not start with dry definitions. We told the panel about our visit to DRDO R&DE (Engrs) in Pune on 2nd September. We explained why MALE UAVs flying long border surveillance missions in harsh desert heat and sub-zero Himalayan altitudes desperately need proactive engine health monitoring instead of simple warning lights that turn on after an engine has already failed.

The evaluators sat forward in their chairs. You could immediately feel the atmosphere in the room shift from a routine academic grading session to an active technical discussion.

---

## Demonstrating the 3D Twin & Defending Our Code

As the presentation progressed, we turned the laptop toward the judges to walk them through the interactive 3D digital twin.

![Demonstrating the 3D engine model and answering questions from the evaluation panel](/images/sih-2026-2.jpg)

We demonstrated how the system operates in real time:
1. **Normal Cruise:** Showing the engine running smoothly at 5,000 RPM, with telemetry updating across all four cylinders at 20 times every second.
2. **Injecting a Real-Time Fault:** Triggering a simulated fuel injector clogging event. The judges watched as the fuel flow dipped, the affected cylinder cooled down, and the exact component lit up on the 3D model.
3. **Emergency Glide and Derate:** Showing how the system advises the pilot with an immediate throttle derate to prevent engine seizure, while calculating whether the UAV can safely glide back to base.

The judges did not just nod and smile; they grilled us with sharp, probing questions:

* *"Is this 3D view just a pre-rendered video, or is it genuinely tied to your calculations?"*
  We invited one of the professors to pick a cylinder on his own and choose a fault. He chose an ignition misfire on Cylinder 4. Within half a second, the screen updated, the sensor residuals spiked, and Cylinder 4 turned red on the 3D model.
* *"Where did you get the engine parameters? Are these made-up numbers?"*
  We showed them our research documentation, engine manuals, and public flight logs from Rotax 912 and NASA Altus UAV flights. We explained how our formulas calculate pressure, torque, and temperatures directly from first principles of thermodynamics.
* *"Can an AI like this actually run on a lightweight UAV computer?"*
  We explained how we separated the heavy processing: lightweight anomaly detection runs fast at the edge, while deeper diagnostics and fleet analytics run on the ground station.

---

## The Verdict and What It Meant to Us

After nearly twenty minutes of intense demonstration and cross-questioning, the lead evaluator leaned back, took off his glasses, and smiled.

He told us that seeing undergraduate students tackle a genuine defense problem statement with this level of depth, building their own physics models rather than pasting together generic templates, was rare and deeply commendable.

When the internal evaluation results were announced, our team was selected to represent our institute for SIH 2026.

Walking out of that room, the feeling of relief was overwhelming. All the sleepless nights, the cold chai, the frustrating bugs, and the sacrifice of weekends felt completely worth it.

---

## The Road Ahead: The Grand Finale

Winning the college round was a proud moment, but we know our journey is far from over.

The Smart India Hackathon Grand Finale will bring together the sharpest student teams and defense evaluators from across the country. Our focus now is refining every edge of ANUMAAN: making the user experience smoother, tightening our fault detection latencies, and ensuring that our digital twin stands as a benchmark of student engineering.

We are ready.

---

## Watch Our System Walkthrough

You can watch our full video demonstration walking through the real-time flight deck, failure injection, and 3D digital twin:

[![Watch ANUMAAN System Demonstration](https://img.youtube.com/vi/L97JAlS9Z7c/maxresdefault.jpg)](https://youtu.be/L97JAlS9Z7c)

Watch on YouTube: [https://youtu.be/L97JAlS9Z7c](https://youtu.be/L97JAlS9Z7c)

---

Back to [SIH Journey Overview](index.md) or explore our [Technical Documentation](../technical/01-introducing-ps26054.md).
