// Copy the single canonical engine GLBs (assets/web/engines/) into the folders each web app serves (card P0-07, D28).
// The copies are gitignored; never edit them. Usage: node scripts/assets/sync_web_models.mjs [frontend|docs_site|web|all]
import { copyFileSync, existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const source = join(root, "assets", "web", "engines");
const targets = {
  frontend: join(root, "frontend", "public", "models"),
  docs_site: join(root, "docs_site", "public", "assets", "models"),
  web: join(root, "web", "site", "assets", "models"),
};

const which = process.argv[2] || "all";
const selected = which === "all" ? Object.keys(targets) : [which];
if (!existsSync(source)) {
  console.error(`[sync_web_models] missing ${source}`);
  process.exit(1);
}
const files = readdirSync(source).filter((f) => f.endsWith(".glb"));
for (const key of selected) {
  const dest = targets[key];
  if (!dest) {
    console.error(`[sync_web_models] unknown target "${key}" (use frontend, docs_site, web or all)`);
    process.exit(1);
  }
  mkdirSync(dest, { recursive: true });
  for (const f of files) {
    const from = join(source, f);
    const to = join(dest, f);
    if (!existsSync(to) || statSync(to).size !== statSync(from).size || statSync(to).mtimeMs < statSync(from).mtimeMs) {
      copyFileSync(from, to);
    }
  }
  console.log(`[sync_web_models] ${files.length} engine models -> ${dest}`);
}
