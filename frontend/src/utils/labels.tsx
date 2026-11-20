import { createContext, useContext, useEffect, useState } from 'react';

/* Human names for channels, parts and status (configs/ui/labels_<lang>.json via /api/v1/ui/labels, M6-06).
   Display text only. Without the file the console still works: ids are shown humanized. */

export type Labels = {
  channels: Record<string, string>;
  components: Record<string, string>;
  status: Record<string, { title: string; text: string }>;
};

const EMPTY: Labels = { channels: {}, components: {}, status: {} };

/** oil_filter -> "Oil filter", egt[2] -> "Egt 2", vib_1X -> "Vib 1X" */
export function humanize(id: string): string {
  const s = id.replace(/\[(\d+)\]/g, ' $1').replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
  return s ? s[0].toUpperCase() + s.slice(1) : id;
}

function lookup(table: Record<string, string>, id: string): string {
  if (table[id]) return table[id];
  for (const [key, text] of Object.entries(table)) {
    if (!key.includes('{n}')) continue;
    const re = new RegExp(`^${key.replace(/[.*+?^$()|[\]\\]/g, '\\$&').replace('{n}', '(\\d+)')}$`);
    const m = re.exec(id);
    if (m) return text.replace('{n}', m[1]);
  }
  return humanize(id);
}

export const channelLabel = (l: Labels, id: string) => lookup(l.channels, id);
export const componentLabel = (l: Labels, id: string) => lookup(l.components, id);

export const LabelsContext = createContext<Labels>(EMPTY);
export const useLabels = () => useContext(LabelsContext);

/** Fetch the label file once per API base; the caller provides the result through LabelsContext. */
export function useFetchLabels(api: (path: string, method: string) => Promise<any>): Labels {
  const [labels, setLabels] = useState<Labels>(EMPTY);
  useEffect(() => {
    api('/api/v1/ui/labels?lang=en', 'GET')
      .then((d) => setLabels({ channels: d.channels ?? {}, components: d.components ?? {}, status: d.status ?? {} }))
      .catch(() => setLabels(EMPTY));                    // ids stay readable through humanize()
  }, [api]);
  return labels;
}
