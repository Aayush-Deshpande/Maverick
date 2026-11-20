# web/: static marketing/demo site
Global rules: ../AGENTS.md and ../DECISIONS.md.

- `site/`: static site (`index.html`, `js/`, `css/`, `assets/models/`). It contains `js/telemetry/sim-engine.js`, a separate fake engine simulator. Either connect it to the backend, or label every number as ILLUSTRATION (P Part 0 D1, R section 13).
- `site/assets/models/rotax_915is.glb` is actually the 912 model (byte-identical). It is fixed when the site reads the single GLB set from `assets/web/` (card C-05).
- `usavionix/mirror/` was renamed on disk by Prasad to `Crazy_Landing/` (his own separate experiment). It is moved to `archive_tracked/crazy_landing/` in card P0-04 (D42). Do not edit it, and never copy its code into the product.
- Vendored three.js / GLTFLoader / Draco decoder here are duplicates (R section 13). The product uses the frontend's three.js. Do not add more vendored copies.
