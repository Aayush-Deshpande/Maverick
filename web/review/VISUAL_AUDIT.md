# ANUMAAN — visual and 3D presentation audit

Reviewed 4 November 2026. Scope follows the user's clarification: **models, graphics, visual design, animation, lighting, framing and presentation**, rather than a functionality audit. No application code, model, material, image or deployed website was changed.

## Overall assessment

The project already has enough visual material for a convincing SIH presentation. The strongest asset is the detailed Rotax 912 model. The warm paper background, dark typography and restrained rust accent give the site an identifiable editorial character. Keep that identity.

The main visual weakness is **inconsistent art direction**. The engine collection alternates between textured machinery, shiny CAD, very dark untextured surfaces and almost white assemblies. The same viewer presentation does not suit all those assets. Consequently the collection feels assembled from different sources rather than curated as one product. More polygons would not solve this.

The second weakness is composition. The dark floor grid competes with the model; tall assemblies approach or pass behind the controls; the airframe occupies relatively little of its viewport; and the captions are small enough to become visual noise during a projected demonstration. Below the hero, repeated large headings and generous blank bands dominate the page, while the actual explanatory graphics remain small and abstract.

**Evidence labels:** “Observed” means seen in the open Chrome website or inspected existing image. “Source-confirmed” means supported by checked-out files. Recommendations are design judgments, not measured defects or claims of manufacturer accuracy.

## Model-by-model review

| Model | What to keep | Observed visual problem | Why it matters | Recommended improvement | Priority |
|---|---|---|---|---|---|
| Rotax 912 iS | Recognizable green covers, hoses, distinct assemblies and dense mechanical detail. Strongest overall material differentiation. | Black components merge in some views; loose peripheral assemblies widen the silhouette. The floor grid runs through the caption area. | Detail is present but the viewer has to work to read it. | Curate a stable three-quarter starting view. Add restrained fill/rim lighting to separate dark parts; use a faint ground plane/contact shadow. Keep the green identity. | High |
| Rotax 914 F | Clear mechanical silhouette, distinguishable cylinder covers and turbo/pipework. | Bright silver, gold/yellow and red surfaces have a shiny CAD appearance, unlike the 912. Some large cylindrical surfaces show visible faceting. | Switching engines changes the apparent rendering standard, weakening the collection. | Separate cast aluminium, machined metal, painted parts and rubber through roughness and restrained reflections. Smooth visible cylindrical silhouettes where needed. Match the common studio lighting. | High |
| Rotax 915 iS | Rich geometry, recognizable plumbing and useful blue accents. | The observed rotating view was dominated by black and dark grey, hiding the internal separation of parts. A bright pale pipe attracts more attention than the main assembly. | This model has nearly two million displayed triangles, but much of that detail is visually lost. | Choose a view that exposes the engine's recognizable side; lift dark-part separation with fill/rim light and material variation, rather than increasing exposure for everything. | High |
| Austro AE300 | Distinct upright architecture, blue hose bands and readable pipe routing. | Tall components approach the upper toolbar; bright white/silver surfaces look flat or plastic in places. A dark intake silhouette shows faceting. | The model needs its own framing and material treatment; the generic engine camera does not keep a consistent safe margin. | Use an upright-engine camera preset with headroom, differentiated cast/finished metal, darker cavities and controlled highlights. Check silhouette smoothing. Clearly disclose a proxy asset where applicable. | High |
| VRDE 2.2L | Clear assembly layout, many individually readable parts and useful coloured fittings. | Large pale surfaces lose depth; strong blue/yellow accents dominate. Materials look closer to a clean CAD assembly than a finished engine. | It looks like a different production stage from the 912, despite being presented as a peer. | Add material hierarchy: cast block, machined faces, rubber hoses, painted fittings and fasteners. Use contact/cavity shading gently. Give colours a consistent part-identification purpose. | High |
| MALE airframe | Recognizable aircraft silhouette and a useful way to give propulsion context. | The 3D aircraft is small relative to its grid. Image mode shows a visibly different twin-boom aircraft while retaining the Predator-Class name. | This is an immediately visible identity mismatch. The small silhouette also wastes the hero's largest visual surface. | Use matching 3D and image assets, the same viewpoint and consistent identity. Fit the wingspan with useful padding, soften/remove the engine floor grid, and give the aircraft a dedicated overview composition. | Critical |

The airframe mismatch is confirmed by `frontend/src/components/landing/aeroLineup.ts:172`: `uav_predator.glb` is paired with `sc_bayraktar_tb3.png`. This is an internal visual identity finding; dimensional and manufacturer accuracy have not been independently validated.

## Viewer and presentation modules

### Landing 3D viewer — High

**Observed:** the floor grid is one of the highest-contrast elements in the hero. It crosses under small labels and can occupy more visual area than the aircraft. The 914/Austro appear much brighter than the 915. The tall Austro model competes with the top controls. Mesh/triangle metadata persists from the previous selection during loading.

**Improve:** establish one neutral studio rig, a subtle contact shadow, and an optional low-contrast inspection grid. Fit each asset's visible bounds into a safe area that excludes the toolbar and captions. Give each model a curated initial angle rather than relying on a shared angle and continuous rotation. Keep previous statistics hidden until the new model is ready. Use a clear poster while loading, rather than making the main hero feel empty.

Source: `LandingHero3D.tsx:129` normalizes engines to a common visual span; `:302` creates the grid; `aeroLineup.ts` gives all five engines the same camera distance/elevation/angle. Actual live controls differ somewhat from this checkout, so implementation changes must first identify the deployed version.

### Materials, lighting and asset consistency — High

**Observed:** materials do not have a common level of realism across the collection. The stored studio images also use different backgrounds and lighting: the 912 beauty image uses a dark blue studio, while other images have different framing/backdrop treatment. These inconsistencies remain even before considering the live viewer.

**Improve:** create a small reference sheet for cast aluminium, polished/machined steel, painted metal, rubber, plastic and wiring. Preserve authentic engine colours. Use a common lighting direction and colour balance; tune exposure only after the materials are sensible. Match 3D and Image modes in angle, object scale, background and crop. Do not apply one blanket metalness/roughness override to every material.

**Existing image exports need reframing:** `render_914_solid.png` cuts off upper components and shows conspicuous faceted pipe surfaces; `render_austro_ae300.png` is an extreme close crop with components passing beyond the image; `render_915is_framing.png` leaves the engine relatively small in a large empty field; `render_vrde_jayem.png` places the assembly well to the right with a large blank left area. These are inspected image assets, separate from the live-viewer framing findings. Re-export a matched full-assembly set, then offer intentional close-ups separately. Check smoothing/weighted normals and purposeful hard edges before increasing polygon counts.

Source: `frontend/public/models/*.glb`, `frontend/public/images/lineup/*`, `LandingHero3D.tsx:145`, `docs_site/src/components/ModelViewerModal.tsx:52`. Local metadata is recorded in `model-visual-metadata.json`. The 914/915 assets contain no image textures; that does not inherently make them bad, but it helps explain why geometry and procedural material choices carry their appearance. No Blender topology/UV or dimensional certification is claimed.

### Camera, rotation and animation — High

**Observed:** auto-rotation moves through weaker rear/side views as well as the good views. Selecting a different landing model turns rotation back on. Exploding the embedded twin can move a substantial portion of the assembly outside the currently visible camera composition.

**Improve:** start on a deliberately chosen three-quarter view; offer clearly labelled Front/Rear/Top and component views. Preserve the user's pause preference across model changes. Refit the camera to the expanded bounds when entering exploded view, and restore the assembled camera afterward. Use short eased transitions without making the target drift.

All six inspected GLBs contain zero embedded animation clips. The website can still animate objects in code, but camera orbit by itself does not explain engine motion. A later optional cutaway could illustrate one piston/crank cycle or a labelled fuel/air path. This is a suggested explanatory visual, not a claim that the present assets contain animated internals.

### Embedded technical twin — High

**Works visually:** the Rotax 912 eventually loaded, displayed a detailed engine, and supported exploded and thermal views. It must not be described as permanently broken because the initial download was slow.

**Observed:** the top telemetry strip and tool labels are very small. The diagnostic card competes with the engine for space. Exploded geometry can leave the useful frame. Wireframe did not remain visually consistent when combined with thermal/restore transitions during the inspected sequence. This last point needs an isolated mode-combination check before implementation.

**Improve:** give the engine a protected central safe area; put the diagnostic summary in a clear side panel; increase essential labels. Provide separate, explicit Beauty / Inspection / Exploded modes. In inspection mode, use restrained highlighting with readable component labels and leader lines. Avoid covering an entire assembly in multiple equally bright colours.

Source: `apps/threejs_twin/index.html:1620`, `:1672`, `:1693`. The current thermal palette is chosen from mesh names in `getThermalConfig`, not a per-surface temperature field. Visually label it as a schematic thermal view unless a measured or calculated field actually drives it.

### Documentation 3D modal — High

**Confirmed defect:** the 912 rendered correctly, but clicking Light Studio to change to Dark Studio removed the engine and left the grid while the old mesh statistics remained. The scene initialization depends on `darkStudio`, while the model-loading effect does not. The render loop also closes over the initial `autoRotate` value; the Pause control needs explicit visual verification after repair.

**Improve:** retain the loaded model when adjusting lighting; update the background/light settings in place. Keep camera/framing consistent between studio modes. Change wireframe on existing materials rather than downloading/rebuilding the same model. Show a useful fallback on asset failure.

Source: `docs_site/src/components/ModelViewerModal.tsx:120`, `:142`, `:231`.

### Landing layout, type and navigation — Medium

**Keep:** the paper/ink/rust palette, large editorial headings, thin separators and restrained footer. The hero has a distinct personality and does not need a wholesale aesthetic replacement.

**Observed:** a tiny logo and a rail of almost identical dashes provide weak orientation. Repeated large two-column headings, long blank bands and similarly structured sections make the page feel repetitive. Small uppercase monospace captions become hard to read at presentation distance. The hero model's footer is especially crowded over the grid.

**Improve:** make section names or numbers visible; add a clear active marker. Reduce large vertical gaps by roughly one third as an initial design experiment, then judge the result at the actual presentation resolution. Keep large type for the hero and a few major moments; give explanatory figures more area. Make useful labels visibly readable, aiming for 12–14 px desktop captions and 14–16 px important controls as starting sizes, with projection checks. Move model title/specifications onto a stable caption surface outside the 3D scene.

Source: `landing-editorial.css:20`, `:176`, `:250`, `:278`; `LandingPage.tsx`.

### Explanatory graphics — High

**Observed:** the threshold comparison is a line and point; the reference comparison is a line with a short sloped segment. The temporal-inference graphic is parallel flat strokes feeding a FlyBrain box. Diagnosis is mainly four text steps. The layout allocates more attention to the headings than to these graphics.

**Improve:** develop one coherent illustrated example: engine component → labelled sensor trace → highlighted deviation → component callout. For the comparison, show the same small trace in both panels with an obvious residual gap. For temporal inference, use short channel waveforms with one aligned time window, not static bars. For diagnosis, connect an actual engine crop to the relevant trace and explanation. Label schematic examples clearly. Retain concise motion or a scrubber only where it helps explain a change; do not replace evidence with decorative animation.

Source: `LandingPage.tsx:93`, `:150`; `landing-editorial.css:304`, `:345`.

### Runtime and Tactical GCS visual design — Medium

**Observed:** the runtime has a reasonable top-level hierarchy, but many panels use the same pale fill, thin border and small monospace text. The fleet selection is subtle. The channel grid places many dissimilar measurements in visually equivalent tiles. Tactical GCS adds several stacked navigation/header rows and dense tables, making it visually busier than the landing page.

**Improve:** give the selected engine a stronger visible selection treatment and, where space permits, a small consistent engine thumbnail. Establish three levels: primary engine/status, main visual/trend, and secondary engineering detail. Group thermal, lubrication, electrical and vibration data visually rather than presenting a uniform alphabetic wall. Use monospace for aligned values and identifiers, ordinary text for explanations. Consolidate header rows and standardize panel spacing across all role views. Maintain text/icons as well as colour for state meaning.

Source: `frontend/src/App.tsx`, `EngineRuntimeConsole.tsx`, `ReadingsPanel.tsx`, `PropulsionEngineerPanel.tsx`, `MaintenanceDashboardPanel.tsx`, `DiagnosticCard.tsx`, `frontend/src/index.css`.

### Documentation graphics and brand continuity — Medium

**Observed:** the docs have a different AN square mark, black/stone palette and dense three-column article layout. The System Architecture article contains a diagram error. The RUL article shows a filename as its title and visibly starts its body with `w#`.

**Improve:** share the main logo, type roles, accent and caption treatment. Make diagrams readable at article width, with a helpful fallback rather than “review console.” Fix the RUL heading. Give long diagrams a deliberate full-width presentation instead of shrinking labels. The architecture chart's `Link` cluster contains an edge to `Link` itself, producing the observed Mermaid cycle error.

Source: `docs_site/technical/04-system-architecture.md:206`, `docs_site/technical/14-remaining-useful-life.md:1`, `docs_site/src/components/Header.tsx`, `MermaidDiagram.tsx`.

## Prioritized visual improvement roadmap

1. **Immediate visual corrections:** match the airframe image and model; fix the disappearing docs model; fix the RUL title and architecture diagram. Hide stale loading statistics. These are visible errors, not redesign preferences.
2. **One polished reference model:** use Rotax 912 to establish the common studio light, subtle ground/contact shadow, clean caption area, camera safe margins and readable controls. Preserve its existing detail and identity.
3. **Bring the other engines to that standard:** give the 914 controlled metal reflections, the 915 dark-part separation, and Austro/VRDE differentiated surfaces. Set individual camera presets. Export matched poster images from the same assets and views.
4. **Repair inspection composition:** camera fitting for exploded view, component names/leader lines, a clearly explained thermal palette and dependable mode combinations. Keep the diagnostic panel outside the engine's protected area.
5. **Improve the landing's graphical story:** reduce repeated whitespace, strengthen navigation and replace abstract line/box diagrams with one concrete illustrated engine example. Keep the existing editorial colour scheme.
6. **Unify presentation surfaces:** apply the same type hierarchy, spacing, caption style and engine identity to the runtime, role panels, twin and documentation.
7. **SIH presentation check:** inspect at the real laptop/projector resolution. Every model should appear promptly, stay fully framed through orbit/zoom/explode, have readable labels, retain its identity across 3D/Image modes and recover to a good home view. Check the exact deployed version before presenting.

## Scope limits

All six landing assets were visually inspected in Chrome, along with the full landing sequence, runtime, role interfaces, loaded embedded twin and documentation views. Existing studio renders and GLB metadata were inspected locally. The audit does not claim a full Blender topology, UV, rigging, dimensional accuracy, mobile, hardware, or frame-time benchmark. No new fault scenario, signoff, AI message or recording was submitted. Findings about materials and art direction are visual judgments; confirmed UI defects and file mismatches are identified separately.

The interactive comparison uses **existing local studio renders**, reduced only for review display. They are not screenshots of newly improved models or a proposed implementation.
