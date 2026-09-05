Thoroughly inspect `@docs/insider/1.1_pillar_1_deep_technical_breakdown.md` and use it as the technical source of truth for Pillar 1.

First, understand the complete intended functionality, architecture, calculations, data flow, models, readings, fault detection/anomaly logic, and other requirements described in the document. Then independently audit the current implementation against it.

Identify **everything that is missing, incomplete, incorrectly implemented, incorrectly wired, inconsistent, broken, or only superficially implemented**. Do not assume that something is correct simply because it exists. Trace the actual implementation and verify that the functionality described in the document is genuinely working end-to-end.

For every issue you find:

- Determine what the intended behavior should be.
- Identify what is currently wrong or missing.
- Fix the implementation properly rather than adding superficial placeholders or UI-only fixes.
- Ensure all components are correctly connected and the resulting data flow is functional.
- Re-check the implementation after making changes to ensure the fixes actually work.

### Redesign the Web Dashboard

The current web dashboard, particularly the area where the engine readings and fault information are displayed, is poorly structured and visually feels like generic AI-generated UI. **Do not simply tweak the existing design. Reimagine and redesign the dashboard substantially.**

The new design should feel like a serious **engineering / aerospace engine health-monitoring system**, not a generic AI dashboard.

Avoid:

- Excessive gradients
- Decorative AI-style visual effects
- Unnecessary glowing elements
- Excessive rounded cards
- Random visual blocks
- Generic "AI dashboard" aesthetics
- Overloaded layouts
- Information being scattered without a clear hierarchy

Prioritize:

- Clear information hierarchy
- Technical credibility
- Readability
- Dense but organized engineering information
- Consistent spacing and typography
- Meaningful visualizations
- Clear relationships between inputs, calculations, detections, and outputs
- A professional aerospace/industrial monitoring aesthetic

### Pillar 1 Readings / Fault Simulation Section

Reorganize the relevant dashboard area into clear, logical sections.

There should be a dedicated **Fault Simulation** section near the top containing selectable fault-simulation cards. These should be properly designed and clearly communicate what fault/scenario is being simulated.

Directly below the fault simulation controls, display the **live/current engine readings** being used by Pillar 1.

Organize the readings logically rather than dumping everything into one large collection of cards. Group related telemetry and measurements into meaningful categories, and make it immediately clear which values are:

- Raw inputs/readings
- Derived values
- Status indicators
- Threshold-related values
- Values involved in anomaly/fault detection

Below the readings, include a **Technical Calculations / Detection Logic** section.

This section should demonstrate the most important formulas and calculations actually used by Pillar 1 to derive things such as anomaly scores, fault indicators, health metrics, thresholds, deviations, or other meaningful outputs.

**Do not dump every formula into the UI.**

Use judgment to determine:

1. Which formulas are important enough to demonstrate to judges because they explain how the system works.
2. Which calculations are important to the actual system but do not need to be exposed in full detail.
3. Which formulas would unnecessarily clutter the interface and should remain internal.

The formulas that are shown should be presented clearly and professionally, with:

- The formula
- A short explanation of what it calculates
- The relevant input variables
- Where appropriate, the resulting value or interpretation

The goal is for a judge to be able to look at the dashboard and understand the chain:

**Fault Simulation → Engine Telemetry → Derived Metrics → Detection/Anomaly Calculation → Health/Fault Result**

### Overall Goal

Treat this as a **technical implementation audit + functional repair + complete dashboard redesign**, not merely a styling task.

Use your own engineering judgment throughout. If the existing implementation contradicts the technical document, prioritize the documented intended behavior and fix the implementation accordingly.

Do not stop after finding the first few issues. Perform a comprehensive pass across the Pillar 1 implementation and dashboard, including:

- Backend logic
- Physics/engineering calculations
- Telemetry generation
- Fault simulation
- Data processing
- Thresholds
- Anomaly/fault detection
- Models and algorithms
- Data flow
- Frontend state management
- API/backend integration
- Visualizations
- Dashboard structure
- User interactions
- Error/edge cases
- Anything else required for Pillar 1 to function correctly

After implementing the fixes and redesign, perform a final verification pass against `@docs/insider/1.1_pillar_1_deep_technical_breakdown.md` and ensure that the resulting system is coherent, functional, technically defensible, and presentation-ready.

Do not merely make it _look_ correct. Make sure the underlying implementation actually works.
