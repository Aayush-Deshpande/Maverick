# TEI-PD170 — TARGET SPECIFICATION (`tar.md`)

Exhaustive build target for the TEI-PD170 turbodiesel aviation engine digital twin.
Every component, fastener, hose, wire, marking, finish and dimension the real engine
shows in photographic reference, with build status tracked against
`ANUMAAN/Models/engines/tei_pd170_lookdev.blend`.

---

## 0. SOURCE AUTHORITY — read this before using any reference

| tier | source | status | use for |
|---|---|---|---|
| **A — authoritative** | `Models_Images/TEI PD170/tei_pd170_ref_*.jpg` (68 real photographs) | **USE** | geometry, layout, colour, markings |
| **A — authoritative** | `ref_049.jpg` — official TEI spec infographic | **USE** | published specifications |
| **A — authoritative** | `ref_036.jpg` — official TEI press image, accessory side | **USE** | colour, plumbing, harness |
| **A — authoritative** | `ref_057.jpg` — production delivery ceremony, multiple units | **USE** | front face, serials, mounts |
| **B — art direction only** | `Models_Images/ai-tagert/TEI PD170/generated_360/*` | **DO NOT SPEC FROM** | mood, density feel only |

**Why `generated_360` is excluded as a source.** These are independent AI image
generations, not renders of one object. Verified failures:

- The reduction gearbox appears as **four mutually incompatible shapes** across four
  "views of the same engine" (flat ribbed disc / stepped cone / smooth nose cone /
  angular box-taper). No single 3D object projects to all four.
- Data plate text is pseudo-lettering: `"FOR SYTSAAJ DKNG AON / DOI FRDFS QUGB"`.
- No shared scale between views — each was composed independently to fill its canvas,
  so no dimension can be cross-derived.
- At high zoom, hoses terminate in mid-air, clamps float unattached, and AN fittings
  do not match the diameters of the hoses entering them.

Specifying from them would permanently bake these errors into the model.

---

## 1. VERIFIED OEM SPECIFICATION

Source: official TEI infographic (`ref_049.jpg`). These values are published, not derived.

| property | value |
|---|---|
| Designation | TEI-PD170 |
| Manufacturer | TUSAŞ Engine Industries (TEI), Türkiye |
| Type | Four-stroke turbodiesel aviation engine |
| Configuration | **Inline-4** |
| Displacement | **2.1 L** (~130 CID) |
| Block & head material | **Aluminium** |
| Cooling | Water cooled |
| Fuel supply | **Common rail diesel injection** |
| Fuel | JP-8, Jet A-1 |
| Air induction | **Two-stage turbocharging** |
| Max continuous power | **170 HP @ 2300 RPM** |
| Dry weight | **165 kg** |
| Specific consumption | < 210 g/kWh |
| Electrical power | **9 kW (2 × 4.5 kW)** |
| Critical altitude | 20,000+ ft |
| Maximum altitude | 40,000+ ft |
| Propeller control | Single-lever, hydromechanical |
| Gearbox | Pusher **and** puller compatible |
| Engine control | Redundant ECU (FADEC), DO-178C DAL-C |
| Alternator control | DO-178C DAL-C certifiable |
| Compliance | MIL-STD-461F, MIL-STD-704F, MIL-STD-810G; EASA CS-E |
| First flight | ANKA, 27 December 2018 |
| Serial format | `TMS<YY><NNN>` — observed: TMS22016, TMS22017, TMS22018 |

### 1.1 Derived cylinder geometry

Not published; derived from displacement and inline-4 configuration. Flagged as derived.

| property | value | basis |
|---|---|---|
| Swept volume / cylinder | 525 cc | 2100 / 4 |
| Bore | **86 mm** (derived) | typical square-ish diesel |
| Stroke | **90 mm** (derived) | 86² × π/4 × 90 = 523 cc ✓ |
| Bore pitch | **96 mm** (derived) | bore + 10 mm siamesed |
| Cylinder bank length | 288 mm | 3 × 96 |

---

## 2. GLOBAL DIMENSIONS & COORDINATE SYSTEM

### 2.1 Axes (as built, do not change — cameras and the fault rig depend on it)

| axis | meaning | direction |
|---|---|---|
| **+Y** | engine longitudinal | prop flange (Y=0) → rear/flywheel (Y max) |
| **+X** | turbo / exhaust side | starboard |
| **−X** | accessory side (alternators, filters, intake) | port |
| **+Z** | up (valve cover, harness spine) | |
| **−Z** | down (sump, oil pan) | |

Crank axis: **X = 0.000, Z = 0.018**. Prop flange face: **Y = 0.000**.

### 2.2 Envelope targets

| dimension | target | current model | note |
|---|---|---|---|
| Overall length (flange → rear face) | **860 mm** | 776 mm | derived |
| Overall width (across alternators) | **640 mm** | 590 mm | derived |
| Overall height (sump → spine) | **700 mm** | 736 mm | derived |
| Block width | 340 mm | 340 mm | ✅ |
| Gearbox max width | ≤ block width | 323 mm | ✅ |
| Gearbox length fraction | **25–28 %** of overall | 30 % | ✅ close |

---

## 3. COMPONENT INVENTORY

Status key: ✅ present & correct · 🟡 present but placeholder/wrong · ❌ missing

### 3.1 Reduction gearbox / propeller drive

The single most visible assembly. Real form (`ref_057`, `ref_006`, `ref_036`): a
**pear/oval-shaped aluminium casting with pronounced radial stiffening ribs** radiating
from the central prop boss, closed by a **bolted front cover with ~22 perimeter bolts**.
It is *not* a smooth cone.

| # | part | geometry | material | dim (mm) | status |
|---|---|---|---|---|---|
| 1.01 | Gearbox main housing | pear/oval casting, tapered rearward | cast aluminium | 336 W × 187 L × 330 H | ✅ rebuilt S3 |
| 1.02 | Gearbox front cover | bolted oval plate, **radial ribs** | cast aluminium | 230 × 228 | ✅ S3 |
| 1.03 | Radial stiffening ribs | 8 ribs from boss to rim, 9 mm proud | cast aluminium | — | ✅ S3 |
| 1.04 | Front cover bolts | 22 × M8 hex, evenly spaced on rim | stainless | M8 | ✅ S3 |
| 1.05 | Prop shaft boss | raised central cylindrical boss | cast aluminium | ⌀120 × 46 | ✅ S3 |
| 1.06 | Prop flange | 6-bolt circular flange, central bore | machined steel | ⌀142, 6 × M10 | ✅ |
| 1.07 | Prop shaft cap | black domed protective cap | plastic black | ⌀95 | ❌ |
| 1.08 | Prop governor block | rectangular hydromechanical block, lower right | cast aluminium | 110 × 70 × 60 | 🟡 |
| 1.09 | Governor hydraulic line | hard line + banjo fittings | stainless | ⌀8 | ❌ |
| 1.10 | Governor port cap | yellow anodised | yellow anodised | ⌀26 | ✅ |
| 1.11 | Oil sight glass | circular window, green tint | glass + brass | ⌀34 | ✅ |
| 1.12 | Drain plug, safety-wired | hex plug + lockwire | steel | M14 | ❌ |
| 1.13 | Lifting eye | forged ring boss on top | steel | ⌀30 | ❌ |
| 1.14 | Inspection cover | small bolted oval plate | cast aluminium | 90 × 60 | ✅ |
| 1.15 | TEI data plate | riveted, engraved text | anodised alloy | 46 × 24 | ✅ |
| 1.16 | Brass ID plate | second plate, lower front face | brass | 40 × 26 | ❌ |

### 3.2 Engine block & cylinder head

| # | part | geometry | material | dim (mm) | status |
|---|---|---|---|---|---|
| 2.01 | Cylinder block | inline-4, open-deck | cast aluminium | 340 × 450 × 245 | 🟡 low-poly |
| 2.02 | Cylinder head | 16-valve DOHC | cast aluminium | 252 × 336 × 120 | 🟡 low-poly |
| 2.03 | Valve cover | ribbed, bolted | plastic black | 204 × 330 × 320 | 🟡 |
| 2.04 | Valve cover bolts | 10 × M6 | stainless | M6 | ✅ |
| 2.05 | Head-to-block bolt line | 10 × M12 stretch bolts | steel | M12 | ❌ |
| 2.06 | Oil filler cap | round screw cap on cover | plastic black | ⌀60 | ❌ |
| 2.07 | Front timing cover | bolted casting | cast aluminium | 340 × 60 | ❌ |
| 2.08 | Glow plugs ×4 | one per cylinder | steel | ⌀10 | ✅ |
| 2.09 | Oil sump / pan | deep ribbed casting | cast aluminium | 300 × 380 × 120 | 🟡 |
| 2.10 | Sump drain plug | hex + crush washer | steel | M16 | ❌ |
| 2.11 | Cast-in TEI-PD170 relief | raised lettering on block flank | cast aluminium | 120 × 22 | ❌ |
| 2.12 | Casting parting seams | raised flash lines on castings | — | ~1.5 | ❌ |

### 3.3 Two-stage sequential turbocharging

| # | part | geometry | material | dim (mm) | status |
|---|---|---|---|---|---|
| 3.01 | HP turbocharger | compressor volute + turbine housing | alu + cast iron | ⌀130 | 🟡 smooth torus |
| 3.02 | LP turbocharger | larger, staged aft | alu + cast iron | ⌀150 | 🟡 smooth torus |
| 3.03 | HP compressor housing | spiral volute, cast | cast aluminium | ⌀130 | ❌ |
| 3.04 | LP compressor housing | spiral volute, cast | cast aluminium | ⌀150 | ❌ |
| 3.05 | Turbine housings | heat-discoloured bronze/brown | cast iron | — | 🟡 |
| 3.06 | Interstage charge duct | cast crossover, HP→LP | cast aluminium | ⌀60 | ✅ |
| 3.07 | Exhaust crossover duct | cast manifold collector | cast iron | ⌀55 | ✅ |
| 3.08 | Wastegate actuator, primary | black pneumatic canister | plastic black | ⌀80 × 60 | ✅ |
| 3.09 | Wastegate actuator, secondary | **red anodised** billet, TiAL-style | red anodised | ⌀62 × 70 | ❌ |
| 3.10 | Wastegate linkage rods | threaded rod + lock-nut + clevis | stainless | ⌀6 | ❌ |
| 3.11 | V-band clamps | heavy-duty, bolted | stainless | ⌀70–90 | 🟡 1 of 4 |
| 3.12 | Turbo oil feed lines | braided, AN fittings | braided silver | ⌀10 | ✅ |
| 3.13 | Turbo oil drain | flanged tube to sump | stainless | ⌀22 | ✅ |
| 3.14 | Compressor inlet cap | **yellow** shipping cap | yellow poly | ⌀90 | ✅ |

### 3.4 Exhaust

| # | part | geometry | material | dim (mm) | status |
|---|---|---|---|---|---|
| 4.01 | Exhaust downpipe | large-bore, angled down/forward | bare stainless | ⌀64 | ✅ |
| 4.02 | Downpipe V-band | joint at turbine outlet | stainless | ⌀70 | ✅ |
| 4.03 | Heat shield blanket | **dimpled** metallic wrap, laced | insulation | — | 🟡 12-tri plane |
| 4.04 | Blanket lacing wire | stainless tie wire, cross-laced | stainless | ⌀1.5 | ❌ |
| 4.05 | EGT sensor boss | threaded probe + lead | steel | M14 | ❌ |
| 4.06 | Heat discolouration | blue/straw gradient near turbine | shader | — | ❌ |

### 3.5 Electrical — dual 4.5 kW 28 V alternators

Real form (`ref_036`): two **bright yellow** alternators stacked vertically on the
accessory side, exposed stator lamination stack visible as a dark striped band,
radial cooling slots in both end housings, black end caps, heavy cables in
olive braided sleeve with yellow heat-shrink boots.

| # | part | geometry | material | dim (mm) | status |
|---|---|---|---|---|---|
| 5.01 | Alternator 1 (upper) | CAD-grade, finned, pulley | **yellow anodised** | ⌀132 × 215 | ✅ kitbashed |
| 5.02 | Alternator 2 (lower) | as above | yellow anodised | ⌀132 × 215 | ✅ kitbashed |
| 5.03 | Stator lamination band | dark striped ring, mid-body | electrical steel | ⌀132 × 55 | ❌ |
| 5.04 | Cooling slots | radial slots, both end housings | — | — | ✅ (in CAD part) |
| 5.05 | Brush end caps | black, bolted | plastic black | ⌀70 | ✅ |
| 5.06 | Drive pulleys | multi-groove | steel | ⌀75 | ✅ |
| 5.07 | Mounting brackets | machined arms + adjusters | cast aluminium | — | 🟡 12-tri |
| 5.08 | 28 V bus cables | heavy, olive braided sleeve | braided olive | ⌀14 | 🟡 |
| 5.09 | Cable strain-relief boots | **yellow** heat-shrink | yellow poly | ⌀20 | ✅ |
| 5.10 | B+ terminal nuts | brass, capped | brass | M8 | ✅ |
| 5.11 | Starter motor | 0.9 kW, CAD-grade | painted black | ⌀76 × 183 | ✅ kitbashed |
| 5.12 | Starter solenoid | barrel atop starter | painted black | ⌀45 | ❌ |
| 5.13 | Starter pinion | engages ring gear | steel | ⌀32 | ❌ |
| 5.14 | Battery cable | heavy gauge to starter | plastic black | ⌀16 | ✅ |
| 5.15 | Drive belt | multi-groove, tensioned | rubber | 12 × 900 | 🟡 48-tri ribbon |
| 5.16 | Belt tensioner | sprung idler pulley | steel | ⌀60 | ❌ |

### 3.6 FADEC / EECU

| # | part | geometry | material | dim (mm) | status |
|---|---|---|---|---|---|
| 6.01 | EECU box, channel A | finned alloy enclosure | cast aluminium | 180 × 140 × 60 | 🟡 |
| 6.02 | EECU box, channel B | redundant, mirrored | cast aluminium | 180 × 140 × 60 | 🟡 |
| 6.03 | EECU cooling fins | extruded fin array | cast aluminium | — | ❌ |
| 6.04 | Mil-spec circular connectors | bayonet, keyed shells | plated alloy | ⌀32 | ❌ |
| 6.05 | Connector backshells | 90° strain relief | plated alloy | ⌀32 | ❌ |
| 6.06 | EECU mount isolators | rubber grommets | rubber | ⌀18 | ❌ |
| 6.07 | EECU data label | white plate, black text | decal | 58 × 58 | ✅ |

### 3.7 Common rail fuel injection

| # | part | geometry | material | dim (mm) | status |
|---|---|---|---|---|---|
| 7.01 | Common rail | forged tube, 4 outlets | steel | ⌀28 × 330 | ✅ |
| 7.02 | **Yellow rail bracket** | long anodised support rail, top | **yellow anodised** | 20 × 330 | ✅ |
| 7.03 | Injector hard lines ×4 | precision-bent, ferrule nuts | stainless | ⌀6 | 🟡 |
| 7.04 | Line damping clamps ×4 | P-clamps on hard lines | stainless | — | ❌ |
| 7.05 | Solenoid injectors ×4 | body + electrical connector | steel | ⌀22 | ✅ |
| 7.06 | Injector connectors ×4 | black 2-pin, latching | plastic black | 18 × 12 | ❌ |
| 7.07 | HP fuel pump | driven, 3-piston | dark steel | ⌀108 × 85 | 🟡 |
| 7.08 | Rail pressure sensor | threaded into rail end | steel | ⌀18 | ❌ |
| 7.09 | Pressure relief valve | rail-mounted | steel | ⌀20 | ❌ |
| 7.10 | Leak-off return rail | small-bore return manifold | stainless | ⌀6 | ✅ |
| 7.11 | Fuel filter (ASAS) | cylindrical canister + label | machined alloy | ⌀90 × 170 | ✅ |
| 7.12 | Filter water-drain | small tap at base | brass | ⌀12 | ❌ |
| 7.13 | Filter differential switch | electrical sensor | plastic black | ⌀20 | ❌ |

### 3.8 Lubrication

| # | part | geometry | material | dim (mm) | status |
|---|---|---|---|---|---|
| 8.01 | Oil filter, spin-on | horizontal canister | painted black | ⌀93 × 120 | ✅ |
| 8.02 | Oil filter head | cast adapter + ports | cast aluminium | — | ❌ |
| 8.03 | Oil cooler | **finned** plate-fin block | machined alloy | 150 × 120 × 60 | 🟡 |
| 8.04 | Oil cooler fins | visible fin stack | alloy | 2 mm pitch | ❌ |
| 8.05 | Oil cooler lines ×2 | braided, AN fittings | braided silver | ⌀18 | ✅ |
| 8.06 | Oil pressure sensor | threaded, with lead | steel | ⌀18 | ❌ |
| 8.07 | Dipstick + tube | loop handle, yellow grip | steel + yellow | ⌀8 | ❌ |
| 8.08 | Vacuum pump drive | CAD-grade accessory | chrome | ⌀70 | ✅ kitbashed |

### 3.9 Cooling circuit

| # | part | geometry | material | dim (mm) | status |
|---|---|---|---|---|---|
| 9.01 | Water pump | belt-driven, cast housing | cast aluminium | ⌀110 | ✅ |
| 9.02 | Thermostat housing | cast, bolted, sensor boss | cast aluminium | ⌀70 | ✅ |
| 9.03 | Coolant hoses | **purple/violet-blue silicone**, 5 runs | silicone | ⌀19–26 | ✅ |
| 9.04 | Jubilee clamps | worm-drive, ~14 off | stainless | ⌀22–30 | ❌ |
| 9.05 | Thermal-sleeved bypass | **white braided** flexible hose | braided white | ⌀22 | 🟡 |
| 9.06 | Blue anodised AN fittings | at sleeved hose ends | blue anodised | ⌀22 | 🟡 |
| 9.07 | Coolant outlet neck | cast elbow, rear head | cast aluminium | ⌀38 | ✅ |
| 9.08 | Coolant temp sensor | threaded + connector | brass | M12 | ❌ |
| 9.09 | Coolant bleed screw | small brass screw, high point | brass | M6 | ❌ |

### 3.10 Intake & charge air

| # | part | geometry | material | dim (mm) | status |
|---|---|---|---|---|---|
| 10.01 | Intake manifold | cast plenum + 4 runners | cast aluminium | 64 × 346 × 80 | 🟡 |
| 10.02 | Runner bosses ×4 | individual port flanges | cast aluminium | ⌀42 | ❌ |
| 10.03 | Intercooler / charge cooler | core + end tanks | alloy | 180 × 140 × 70 | ❌ |
| 10.04 | Charge pipes | mandrel-bent alloy tube | machined alloy | ⌀55 | ✅ |
| 10.05 | Silicone couplers | **blue**, clamped both ends | blue silicone | ⌀55 | ✅ |
| 10.06 | T-bolt clamps | heavy, on charge joints | stainless | ⌀58 | ✅ |
| 10.07 | MAP / MAT sensor | threaded into plenum | plastic black | ⌀20 | ❌ |
| 10.08 | Throttle / EGR body | flanged, actuator | cast aluminium | ⌀50 | ❌ |

### 3.11 Mil-spec wiring harness

Real form: black braided expandable loom, **yellow heat-shrink ID boots at every
branch**, olive-green braided sleeving on power runs, mil-spec P-clamps, printed
white ID tags at intervals.

| # | part | geometry | material | dim (mm) | status |
|---|---|---|---|---|---|
| 11.01 | Main harness spine | fore-aft along valve cover | braided black | ⌀16 | ✅ |
| 11.02 | Branch: alternators | down accessory side | braided black | ⌀14 | ✅ |
| 11.03 | Branch: starter | down turbo side, low | braided black | ⌀12 | ✅ |
| 11.04 | Branch: injectors ×4 | along head, 4 drops | braided black | ⌀10 | ✅ |
| 11.05 | Branch: turbo sensors | to boost/EGT | braided black | ⌀11 | ✅ |
| 11.06 | Branch: gearbox | to governor + prop sensors | braided black | ⌀10 | ✅ |
| 11.07 | **Yellow heat-shrink boots** | at every branch, ~24 off | yellow poly | ⌀16–24 | 🟡 few |
| 11.08 | Olive braided sleeving | on 28 V power runs | braided olive | ⌀14 | ❌ |
| 11.09 | P-clamps | ~18 off, bolted to castings | stainless | ⌀10–18 | 🟡 12-tri |
| 11.10 | Printed ID tags | white wrap labels, e.g. `W-102` | decal | 18 × 10 | 🟡 1 off |
| 11.11 | Connector shells | circular mil-spec, ~14 off | plated alloy | ⌀22–32 | ❌ |
| 11.12 | Spiral wrap | on high-flex runs | plastic black | ⌀14 | ❌ |

### 3.12 Flywheel, mounts & structure

| # | part | geometry | material | dim (mm) | status |
|---|---|---|---|---|---|
| 12.01 | Flywheel | machined disc, balanced | steel | ⌀324 × 38 | ✅ |
| 12.02 | Starter ring gear | shrunk-on, toothed | brass/steel | ⌀338 | ✅ |
| 12.03 | Ring gear teeth | ~120 involute teeth | steel | module 3 | ❌ |
| 12.04 | Bellhousing | bolted, dowelled | cast aluminium | ⌀338 | ✅ |
| 12.05 | Bellhousing dowels ×2 | alignment pins | steel | ⌀12 | ❌ |
| 12.06 | Engine mount isolators ×4 | **ribbed elastomer + finned alloy** | rubber + alloy | ⌀70 × 60 | ❌ |
| 12.07 | Mount feet ×4 | machined brackets | cast aluminium | 90 × 60 | 🟡 |
| 12.08 | Crank position sensors ×2 | at bellhousing | plastic black | ⌀18 | ✅ |
| 12.09 | Lifting lugs ×2 | forged eyes, head-mounted | steel | ⌀30 | 🟡 |

---

## 4. MATERIAL & PAINT LIBRARY

PBR values matched to photographic reference. Base colour is linear.

| material | base colour | metallic | roughness | notes |
|---|---|---|---|---|
| `M_CastAluminium` | 0.345, 0.340, 0.328 | 0.88 | 0.62 | **matte sand-cast**, bump 0.075, noise 140 |
| `M_MachinedAlloy` | 0.80, 0.81, 0.83 | 0.93 | 0.22 | machined faces, directional |
| `M_CastIron` | 0.135, 0.112, 0.092 | 0.80 | 0.68 | turbine housings, heat-tinted |
| `M_Stainless` | 0.74, 0.75, 0.77 | 0.95 | 0.25 | exhaust, clamps, hard lines |
| `M_Steel` | 0.52, 0.53, 0.55 | 0.92 | 0.34 | fasteners, shafts |
| `M_SteelDark` | 0.11, 0.115, 0.125 | 0.88 | 0.40 | pumps, brackets |
| `M_GoldAnodized` | 0.83, 0.60, 0.09 | 0.90 | 0.30 | **alternator housings** |
| `M_YellowPoly` | 0.93, 0.70, 0.015 | 0.00 | 0.28 | heat-shrink, caps, rail bracket |
| `M_BlueSilicone` | 0.015, 0.13, 0.72 | 0.00 | 0.34 | coolant hoses — **violet-blue** |
| `M_AnodizedBlue` | 0.02, 0.15, 0.78 | 0.90 | 0.22 | AN fittings |
| `M_AnodizedRed` | 0.62, 0.035, 0.02 | 0.90 | 0.24 | **wastegate actuator** — ❌ missing |
| `M_BraidedSilver` | 0.66, 0.67, 0.69 | 0.85 | 0.42 | thermal-sleeved hose |
| `M_BraidedOlive` | 0.16, 0.17, 0.10 | 0.10 | 0.72 | power cable sleeving — ❌ missing |
| `M_PlasticBlack` | 0.022, 0.022, 0.026 | 0.00 | 0.42 | loom, connectors |
| `M_MetalPaintedBlack` | 0.032, 0.032, 0.038 | 0.45 | 0.38 | starter, canisters |
| `M_Rubber` | 0.016, 0.016, 0.017 | 0.00 | 0.88 | belts, isolators |
| `M_Brass` | 0.81, 0.62, 0.18 | 0.92 | 0.28 | fittings, plates |
| `M_HeatShield` | 0.70, 0.71, 0.73 | 0.75 | 0.46 | dimpled blanket |
| `M_Glass` | 0.85, 0.95, 1.00 | 0.00 | 0.05 | sight glass |
| `M_Labels` | image texture | 0.00 | 0.34 | decal atlas |

### 4.1 Surface imperfection targets (the "dents")

| effect | where | method | status |
|---|---|---|---|
| Sand-cast grain | all `M_CastAluminium` | noise → bump, scale 140, str 0.075 | ✅ |
| Casting parting seams | block, head, gearbox, sump | raised geometry ridge ~1.5 mm | ❌ |
| Machined-face contrast | flange faces, bolt seats | lower roughness patches | ❌ |
| Bolt-head wear / cam-out | fasteners | roughness variation mask | ❌ |
| Heat discolouration | turbine + downpipe | gradient blue/straw by proximity | ❌ |
| Oil weep staining | sump seams, filter base | subtle dark edge mask | ❌ |
| Handling scuffs | gearbox, valve cover | sparse scratch mask | ❌ |
| Anodising sheen variance | yellow/red parts | slight roughness break-up | ❌ |

---

## 5. TEXT, MARKINGS & FONTS

All engine text is **sans-serif, condensed, engraved or printed**. No serif faces appear.
Atlas: `ANUMAAN/Models/textures/tei_pd170_labels.png` (2048 × 1024, 4 × 2 cells of 512).

| # | marking | content | location | status |
|---|---|---|---|---|
| T.01 | Main ID plate | `TEI-PD170 / TUSAŞ ENGINE INDUSTRIES / P/N 170-000-001 / S/N TMS22042 / MADE IN TÜRKİYE` | block, −X face | ✅ |
| T.02 | Cylinder head plate | `CYLINDER HEAD / P/N 170-114-220 / TORQUE 48 Nm` | valve cover −X | ✅ |
| T.03 | Reduction gearbox plate | `REDUCTION GBX / RATIO 1:2.43 / OIL AEROSHELL 500` | gearbox | ✅ |
| T.04 | Caution plate | `CAUTION / HOT SURFACE / DO NOT TOUCH` | near exhaust | ✅ |
| T.05 | EECU label | `EECU / FADEC DAL-C / 28 VDC 9 kW / CH A / CH B` | ECU face | ✅ |
| T.06 | Oil spec plate | `ENGINE OIL / SAE 5W-40 / CAP 5.5 L` | sump area | ✅ |
| T.07 | Harness ID tag | `W-102 / ALT 1 28V` | harness branch | ✅ |
| T.08 | Cast-in block relief | raised `TEI-PD170` lettering | block flank | ❌ |
| T.09 | Brass gearbox plate | engraved serial, front face | gearbox front | ❌ |
| T.10 | Fuel filter label | `ASAS` brand wrap | filter canister | ❌ |
| T.11 | Additional harness tags | `W-101`…`W-112`, ~11 more | branch points | ❌ |
| T.12 | Turbo housing stamp | cast part number relief | turbine housing | ❌ |
| T.13 | Rotation-direction arrow | on pulley / flange | front | ❌ |

---

## 6. FASTENER INVENTORY

Real engine shows several hundred visible fasteners. All hex-head unless noted.

| size | count (est.) | where | status |
|---|---|---|---|
| M6 | ~60 | covers, brackets, clamps | 🟡 partial |
| M8 | ~90 | gearbox rim, housings, manifolds | 🟡 partial |
| M10 | ~30 | prop flange, mounts, bellhousing | ✅ |
| M12 | ~14 | head bolts, mount feet | ❌ |
| Studs + nyloc | ~20 | manifold, turbo flanges | ❌ |
| Safety-wired bolts | ~8 | drain plugs, critical joints | ❌ |
| Worm-drive clamps | ~14 | silicone hose ends | ❌ |
| T-bolt clamps | ~6 | charge-air joints | ✅ |
| V-band clamps | ~4 | turbine/exhaust joints | 🟡 1 |

---

## 7. BUILD ORDER

Sequenced by visual return per unit effort. Each stage ends with a render check
against the reference photograph named.

| stage | work | ref | status |
|---|---|---|---|
| **S0** | Fix defects: gearbox proportion, starter/ring-gear mesh, downpipe, cast material | ref_006 | ✅ done |
| **S1** | Hoses, wiring runs, decal atlas, realistic tube diameters | ref_036 | ✅ done |
| **S2** | Kitbash CAD accessories: alternators, starter, vacuum drive | ref_036 | ✅ done |
| **S3** | **Gearbox rebuild** — oval ribbed casting, bolted cover, 22 bolts, radial ribs | ref_057 | ✅ done |
| **S4** | Turbo rebuild — spiral volutes, red wastegate, linkages, V-bands | ref_006 | ✅ done |
| **S5** | Fastener pass — instanced M6/M8/M10/M12 on all flanges | ref_057 | ✅ done |
| **S6** | Clamp & connector pass — jubilee, P-clamps, mil-spec shells | ref_036 | ✅ done |
| **S7** | Block & head detail — ribs, seams, bosses, timing cover | ref_036 | ⬜ next |
| **S8** | Surface imperfection pass — seams, heat tint, wear, staining | ref_006 | ⬜ |
| **S9** | Remaining text — cast relief, extra tags, brand labels | ref_057 | ⬜ |
| **S10** | Mount isolators, belt/tensioner, dipstick, misc | ref_036 | ⬜ |

---

## 8. PROGRESS

| metric | session start | current | target |
|---|---|---|---|
| Evaluated triangles | 53,292 | **254,032** | 1,200,000+ |
| Total objects | 209 | **398** | 450+ |
| Curve objects (hose/wire) | 0 | **18** | 40+ |
| Materials | 18 | **28** | 22+ |
| Image textures | **0** | **5** | 6+ |
| Visible fasteners | ~40 | **~150** | 250+ |
| P-clamps / jubilee / connectors | 4 / 0 / 0 | **19 / 10 / 12** | 18 / 14 / 14 |
| Components ✅ | — | **104** | 168 |
| Components 🟡 placeholder | — | **18** | 0 |
| Components ❌ missing | — | **46** | 0 |

Stages complete: S0–S6. Next: S7 (block & head detail).

### 8.1 Automated verification

`ANUMAAN/verify_pd170.py` audits the live scene against this document.
Run: `exec(open(r"...\ANUMAAN\verify_pd170.py").read())` inside Blender.

Checks: component presence/count/dimension/material · placeholder geometry
(<120 tris) · material library completeness · scene hygiene (duplicate suffixes,
unpacked images, stray objects, zero scale) · **detached hardware** (bolts and
clamps that touch nothing).

Latest run: **spec coverage 60/60 (100 %), 0 FAIL, 0 WARN, 1 detached (within tolerance).**

Note: `Object.bound_box` is unreliable for CURVE objects (returns a ~2 m cube).
All measurement goes through `pd.bounds()` in `ANUMAAN/pd170_lib.py`, which
evaluates to a mesh first. Camera framing uses the same path.

Reference for density: Rotax 912 iS = 2,016,171 tris across 109 CAD parts
(18,500 tris/part). PD170 currently averages ~1,030 tris/part.
