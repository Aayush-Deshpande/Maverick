// Content loader and parser for ANUMAAN documentation corpus

export interface DocHeading {
  id: string;
  text: string;
  level: number;
}

export interface DocArticle {
  slug: string;
  filename: string;
  title: string;
  category: string;
  group: string;
  abstract: string;
  content: string;
  headings: DocHeading[];
  wordCount: number;
  readTime: string;
  evidenceStatus: 'VERIFIED' | 'INFERENCE' | 'ASSUMPTION' | 'SPECIFICATION';
  osacbmLayer?: string;
  engineScope?: string;
  order: number;
}

export interface NavGroup {
  name: string;
  items: {
    title: string;
    slug: string;
    badge?: string;
  }[];
}

// Vite glob imports for markdown files
const technicalRaw: Record<string, string> = import.meta.glob('/technical/*.md', { query: '?raw', import: 'default', eager: true });
const journeyRaw: Record<string, string> = import.meta.glob('/journey/*.md', { query: '?raw', import: 'default', eager: true });
const rootRaw: Record<string, string> = import.meta.glob('/*.md', { query: '?raw', import: 'default', eager: true });

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-');
}

function parseMarkdownArticle(path: string, rawContent: string): DocArticle {
  const filename = path.split('/').pop() || '';
  const lines = rawContent.split('\n');

  let title = '';
  let abstract = '';
  const headings: DocHeading[] = [];
  const contentLines: string[] = [];

  let foundTitle = false;
  let collectingAbstract = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // Check for main H1 title
    if (!foundTitle && line.startsWith('# ')) {
      title = line.replace(/^#\s+/, '').trim();
      foundTitle = true;
      collectingAbstract = true;
      continue;
    }

    // Extract H2 and H3 for Table of Contents
    if (line.startsWith('## ') || line.startsWith('### ')) {
      collectingAbstract = false;
      const level = line.startsWith('### ') ? 3 : 2;
      const text = line.replace(/^#{2,3}\s+/, '').trim();
      const id = slugify(text);
      headings.push({ id, text, level });
    }

    // First non-empty paragraph after H1 is the abstract
    if (collectingAbstract && line.trim().length > 0 && !line.startsWith('#')) {
      if (!abstract) {
        abstract = line.trim();
      } else {
        abstract += ' ' + line.trim();
      }
    }

    contentLines.push(line);
  }

  // Derive slug
  let slug = '';
  if (path.includes('/technical/')) {
    const base = filename.replace(/\.md$/, '');
    slug = `technical/${base}`;
  } else if (path.includes('/journey/')) {
    const base = filename.replace(/\.md$/, '');
    slug = base === 'index' ? 'journey' : `journey/${base}`;
  } else {
    slug = 'home';
  }

  // Determine category and group
  let category = 'Technical Documentation';
  let group = 'Orientation';
  let evidenceStatus: DocArticle['evidenceStatus'] = 'VERIFIED';
  let osacbmLayer = 'Layer 1-6 Architecture';
  let engineScope = 'Rotax 912 iS & 5-Engine Fleet';

  if (slug.startsWith('technical/01') || slug.startsWith('technical/02') || slug.startsWith('technical/03')) {
    category = 'Orientation';
    group = 'Orientation';
    osacbmLayer = 'Scope & Mission Context';
  } else if (slug.startsWith('technical/04')) {
    category = 'Architecture';
    group = 'System Architecture';
    osacbmLayer = 'ISO 13374 / Layers 1 to 6';
  } else if (slug.startsWith('technical/05') || slug.startsWith('technical/06') || slug.startsWith('technical/07') || slug.startsWith('technical/08')) {
    category = 'Digital Twin & Physics';
    group = 'Digital Twin & Physics';
    osacbmLayer = slug.includes('07') ? 'Layer 1: Data Acquisition' : 'Layer 2: Data Manipulation & State';
    engineScope = 'Rotax 912 iS (Thermodynamic Core)';
  } else if (slug.startsWith('technical/09') || slug.startsWith('technical/10') || slug.startsWith('technical/11') || slug.startsWith('technical/12') || slug.startsWith('technical/13') || slug.startsWith('technical/14')) {
    category = 'AI / ML & Prognostics';
    group = 'AI and ML Stack';
    osacbmLayer = slug.includes('10') ? 'Layer 3: State Detection' : slug.includes('11') ? 'Layer 4: Health Assessment' : 'Layer 5: Prognostics Assessment';
  } else if (slug.startsWith('technical/15')) {
    category = 'Data Strategy';
    group = 'Data Strategy';
    osacbmLayer = 'Verification Benchmark Tiers';
  } else if (slug.startsWith('technical/16') || slug.startsWith('technical/17')) {
    category = 'Mission Systems';
    group = 'Mission Systems';
    osacbmLayer = 'Layer 6: Advisory & Mission Risk';
    engineScope = 'Kinematics & Monte Carlo Hazard';
  } else if (slug.startsWith('technical/18') || slug.startsWith('technical/19')) {
    category = '3D & Simulation';
    group = '3D and Simulation';
    osacbmLayer = 'Visual Twin & Replay';
    engineScope = 'Five Draco GLB Engines';
  } else if (slug.startsWith('technical/20')) {
    category = 'Operator GCS';
    group = 'Operator Interface';
    osacbmLayer = 'Operator Interaction';
  } else if (slug.startsWith('technical/21') || slug.startsWith('technical/22') || slug.startsWith('technical/23')) {
    category = 'Validation & Reference';
    group = 'Validation and Reference';
    osacbmLayer = 'Characterization & Benchmarks';
  } else if (slug.startsWith('journey')) {
    category = 'SIH Journey';
    group = 'Our SIH Journey';
  }

  const wordCount = rawContent.split(/\s+/).filter(Boolean).length;
  const readTime = `${Math.ceil(wordCount / 200)} min read`;

  // Sort order
  let order = 0;
  const numMatch = filename.match(/^(\d+)/);
  if (numMatch) {
    order = parseInt(numMatch[1], 10);
  }

  return {
    slug,
    filename,
    title: title || filename,
    category,
    group,
    abstract,
    content: rawContent,
    headings,
    wordCount,
    readTime,
    evidenceStatus,
    osacbmLayer,
    engineScope,
    order,
  };
}

// Build articles index
export const allArticles: DocArticle[] = [];

// Load technical articles
for (const [path, content] of Object.entries(technicalRaw)) {
  allArticles.push(parseMarkdownArticle(path, content));
}

// Load journey articles
for (const [path, content] of Object.entries(journeyRaw)) {
  allArticles.push(parseMarkdownArticle(path, content));
}

// Sort technical articles
export const technicalArticles = allArticles
  .filter((a) => a.slug.startsWith('technical/'))
  .sort((a, b) => a.order - b.order);

// Sort journey articles
export const journeyArticles = allArticles
  .filter((a) => a.slug.startsWith('journey/'))
  .sort((a, b) => a.order - b.order);

export const journeyIndex = allArticles.find((a) => a.slug === 'journey');

// Article lookup map
export const articleBySlug = new Map<string, DocArticle>();
for (const art of allArticles) {
  articleBySlug.set(art.slug, art);
}

// Sidebar hierarchy according to user specifications
export const technicalNavGroups: NavGroup[] = [
  {
    name: 'Orientation',
    items: [
      { title: 'SIH Problem Statement 26054', slug: 'technical/01-introducing-ps26054' },
      { title: 'Understanding the Engineering Problem', slug: 'technical/02-the-engineering-problem' },
      { title: 'Introducing ANUMAAN', slug: 'technical/03-introducing-anumaan' },
    ],
  },
  {
    name: 'System Architecture',
    items: [
      { title: 'System Architecture & Coexisting Runtimes', slug: 'technical/04-system-architecture' },
    ],
  },
  {
    name: 'Digital Twin & Physics Core',
    items: [
      { title: 'The Digital Twin Core', slug: 'technical/05-the-digital-twin' },
      { title: 'Engine Physics & Combustion Modeling', slug: 'technical/06-engine-physics' },
      { title: 'Telemetry & Sensor Intelligence', slug: 'technical/07-telemetry-and-sensors' },
      { title: 'Residual Analysis & Validation Shield', slug: 'technical/08-residual-analysis' },
    ],
  },
  {
    name: 'AI & ML Stack',
    items: [
      { title: 'AI & ML Architecture Overview', slug: 'technical/09-ai-ml-architecture' },
      { title: 'Bio-Inspired Sparse Novelty Coding', slug: 'technical/10-bio-inspired-sparse-novelty-coding', badge: 'FlyHash' },
      { title: 'Bayesian Fault Diagnosis', slug: 'technical/11-fault-diagnosis' },
      { title: 'Vibration Order Tracking & Demodulation', slug: 'technical/12-vibration-analysis' },
      { title: 'Degradation Modeling (Miner & Rainflow)', slug: 'technical/13-degradation-modeling' },
      { title: 'Remaining Useful Life & Conformal Bounds', slug: 'technical/14-remaining-useful-life' },
    ],
  },
  {
    name: 'Data Strategy',
    items: [
      { title: 'Dataset Strategy & Benchmarks', slug: 'technical/15-dataset-strategy' },
    ],
  },
  {
    name: 'Mission Systems',
    items: [
      { title: 'Mission Planning & Kinematics Executive', slug: 'technical/16-mission-planning' },
      { title: 'Monte Carlo Mission Reliability R(t)', slug: 'technical/17-mission-reliability', badge: 'Monte Carlo' },
    ],
  },
  {
    name: '3D Twin & Simulation',
    items: [
      { title: 'The 3D Digital Twin (Five Engines)', slug: 'technical/18-3d-digital-twin' },
      { title: 'Blender & Canyon Simulation Environment', slug: 'technical/19-blender-and-simulation-environment' },
    ],
  },
  {
    name: 'Operator Interface',
    items: [
      { title: 'The Operator Ground Control Station', slug: 'technical/20-operator-gcs' },
    ],
  },
  {
    name: 'Validation & Reference',
    items: [
      { title: 'Validation, Characterization & Tests', slug: 'technical/21-validation-and-experiments' },
      { title: 'End-to-End Demonstration Methodology', slug: 'technical/22-end-to-end-demonstration' },
      { title: 'Technology Stack & Architecture Anchor', slug: 'technical/23-technology-stack' },
    ],
  },
];

export const journeyNavGroups: NavGroup[] = [
  {
    name: 'Field Notebook',
    items: [
      { title: 'Journey Overview', slug: 'journey' },
      { title: '01 The Engineering Story', slug: 'journey/01-the-engineering-story' },
      { title: '02 Demonstration & Verification', slug: 'journey/02-preparing-for-evaluation' },
    ],
  },
];
