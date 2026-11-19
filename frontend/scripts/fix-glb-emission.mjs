// Clears a Blender-export emission bug: every material exported with emissiveFactor [1,1,1] and
// KHR_materials_emissive_strength 5, which renders the whole engine as a white silhouette.
// Patches only the GLB's JSON chunk; the binary chunk (Draco geometry, textures) is copied untouched.
// A material keeps its emission when it has an emissive texture or when the bug is not model-wide.
// Run: node scripts/fix-glb-emission.mjs public/models/austro_ae300.glb [...more.glb]
import fs from 'node:fs';

for (const file of process.argv.slice(2)) {
  const buf = fs.readFileSync(file);
  if (buf.readUInt32LE(0) !== 0x46546c67) throw new Error(`${file} is not a GLB`);
  const jsonLen = buf.readUInt32LE(12);
  const json = JSON.parse(buf.subarray(20, 20 + jsonLen).toString('utf8'));
  const rest = buf.subarray(20 + jsonLen); // BIN chunk header + payload, unchanged
  const mats = json.materials ?? [];
  const isBug = (m) => !m.emissiveTexture && Array.isArray(m.emissiveFactor) && m.emissiveFactor.every((v) => v >= 0.99);
  const affected = mats.filter(isBug);
  if (affected.length < Math.max(3, mats.length * 0.6)) { console.log(`${file}: no model-wide emission bug (${affected.length}/${mats.length}), unchanged`); continue; }
  for (const m of affected) {
    delete m.emissiveFactor;
    if (m.extensions) { delete m.extensions.KHR_materials_emissive_strength; if (!Object.keys(m.extensions).length) delete m.extensions; }
  }
  const stillUsed = mats.some((m) => m.extensions?.KHR_materials_emissive_strength);
  if (!stillUsed) {
    json.extensionsUsed = (json.extensionsUsed ?? []).filter((e) => e !== 'KHR_materials_emissive_strength');
    if (!json.extensionsUsed.length) delete json.extensionsUsed;
  }
  let text = Buffer.from(JSON.stringify(json), 'utf8');
  const pad = (4 - (text.length % 4)) % 4;
  text = Buffer.concat([text, Buffer.alloc(pad, 0x20)]);
  const header = Buffer.alloc(20);
  header.writeUInt32LE(0x46546c67, 0); header.writeUInt32LE(2, 4);
  header.writeUInt32LE(20 + text.length + rest.length, 8);
  header.writeUInt32LE(text.length, 12); header.writeUInt32LE(0x4e4f534a, 16);
  fs.writeFileSync(file, Buffer.concat([header, text, rest]));
  console.log(`${file}: cleared white emission on ${affected.length}/${mats.length} materials`);
}
