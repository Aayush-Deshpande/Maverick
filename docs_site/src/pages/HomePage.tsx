import React from "react";
import {
    ArrowRight,
    Box,
    ShieldCheck,
    Activity,
    Cpu,
    Layers,
    GitBranch,
    Terminal,
    ExternalLink,
} from "lucide-react";
import { ArticleCard } from "../components/ArticleCard";
import { MermaidDiagram } from "../components/MermaidDiagram";

interface HomePageProps {
    onNavigate: (path: string) => void;
    onOpenModelViewer: () => void;
}

export const HomePage: React.FC<HomePageProps> = ({
    onNavigate,
    onOpenModelViewer,
}) => {
    const coreArchitectureMermaid = `flowchart TB
    subgraph Layer0["Layer 1: Sensor and Propulsion Ingest"]
        T1["Rotax 912 iS, 914, 915 iS"] --> DAQ["20 Hz Synchronous Frame Ingest"]
        T2["Austro AE300 and VRDE Jayem"] --> DAQ
        DAQ --> SV["Sensor Validation and Shielding"]
    end

    subgraph Layer1["Layer 2: Digital Twin Physics Core"]
        SV --> RES["State Estimation and Residual Engine"]
        CK["Slider-Crank and Wiebe Combustion"] --> RES
        PL["Independent Plant Model G01"] --> RES
    end

    subgraph Layer2["Layer 3: Sparse Novelty Detection"]
        RES --> FH["Bio-Inspired Sparse Novelty Coding"]
        FH -->|Novelty Trigger| DIAG["Layer 4: Bayesian Fault Diagnosis"]
    end

    subgraph Layer3["Layer 5 and 6: Prognostics and Mission Executive"]
        DIAG --> RUL["Rainflow, Miner and Conformal RUL"]
        RUL --> ME["Authoritative Mission Executive"]
        ME --> MC["Monte Carlo Hazard Reliability R[t]"]
    end

    subgraph Layer4["Operator Interface and 3D Twin"]
        MC --> GCS["Operator Ground Control Station"]
        ME --> GCS
        GCS --> TWIN["Three.js 5-Engine Draco Twin and Blender Master"]
    end`;

    return (
        <div className="min-h-screen bg-[#f6f5f3] text-[#1c1917] font-sans">
            <div className="max-w-[1280px] mx-auto bg-[#fafaf9] sm:border-x border-stone-200/90 shadow-xs relative">
                {/* 1. HERO SECTION (Extend Architectural Technical Style) */}
                <section className="relative border-b border-stone-200 bg-stone-50/80 pt-16 pb-20 px-4 sm:px-6 lg:px-12">
                    {/* Subtle corner registration marks */}
                    <div
                        aria-hidden="true"
                        className="size-1.5 rounded-full bg-stone-300 absolute top-3 left-3"
                    />
                    <div
                        aria-hidden="true"
                        className="size-1.5 rounded-full bg-stone-300 absolute top-3 right-3"
                    />
                    <div
                        aria-hidden="true"
                        className="size-1.5 rounded-full bg-stone-300 absolute bottom-3 left-3"
                    />
                    <div
                        aria-hidden="true"
                        className="size-1.5 rounded-full bg-stone-300 absolute bottom-3 right-3"
                    />

                    <div className="max-w-4xl mx-auto flex flex-col items-center text-center space-y-6">
                        {/* Technical Metadata Pill */}
                        <div className="flex flex-wrap items-center justify-center gap-x-2.5 gap-y-1 px-3 py-1 rounded-[2px] border border-stone-300 bg-white text-stone-700 font-mono text-[11px] uppercase tracking-wider">
                            <span className="inline-flex items-center gap-1.5">
                                <span className="size-2 rounded-full bg-blue-600 animate-pulse" />
                                <span>DRDO SIH PS-26054</span>
                            </span>
                            <span className="text-stone-300 hidden sm:inline">
                                |
                            </span>
                            <span>MALE UAV PROPULSION HEALTH</span>
                            <span className="text-stone-300 hidden sm:inline">
                                |
                            </span>
                            <span className="hidden sm:inline">
                                STANAG 4586 LOI 2
                            </span>
                        </div>

                        {/* Overline & Main Title */}
                        <div className="space-y-3">
                            <span className="block font-mono text-xs uppercase tracking-[0.14em] text-stone-500 font-semibold">
                                PROJECT ANUMAAN // VIRTUAL ENGINE CORPS
                            </span>
                            <h1 className="text-2xl sm:text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-stone-950 leading-[1.15]">
                                AI-Powered Real-Time Digital Twin for
                                Aero-Piston Engine Health &amp; Mission
                                Reliability
                            </h1>
                        </div>

                        {/* Technical Abstract */}
                        <p className="max-w-3xl text-sm sm:text-base md:text-lg text-stone-600 font-normal leading-relaxed">
                            A physics-grounded virtual engine framework that
                            couples crank-angle thermodynamics, Bio-Inspired
                            Sparse Novelty Coding, and Bayesian fault isolation
                            with Monte Carlo mission reliability forecasting
                            across a five-engine UAV propulsion family.
                        </p>

                        {/* Tactile Action Buttons */}
                        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3 pt-2 w-full sm:w-auto">
                            <button
                                onClick={() =>
                                    onNavigate(
                                        "technical/01-introducing-ps26054",
                                    )
                                }
                                className="btn-extend-primary"
                            >
                                <span>Explore Technical Docs</span>
                                <ArrowRight size={14} />
                            </button>
                            <button
                                onClick={onOpenModelViewer}
                                className="btn-extend-tactile"
                            >
                                <Box size={14} />
                                <span>Inspect 3D Twin (GLB)</span>
                            </button>
                        </div>
                    </div>
                </section>

                {/* 2. TWO PRIMARY SECTIONS (The Two Architectural Portals) */}
                <section className="py-16 px-4 sm:px-6 lg:px-12 border-b border-stone-200">
                    <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-4">
                        <div>
                            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500 font-semibold block">
                                [01 // SYSTEM ENTRY POINTS]
                            </span>
                            <h2 className="text-2xl sm:text-3xl font-bold text-stone-900 mt-1 tracking-tight">
                                Two Primary Entry Points
                            </h2>
                        </div>
                        <p className="text-xs text-stone-500 font-mono max-w-md">
                            Structured into two distinct publication streams:
                            the rigorous engineering reference and the
                            chronological field notebook.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        {/* SECTION 01: TECHNICAL DOCUMENTATION */}
                        <div
                            onClick={() =>
                                onNavigate("technical/01-introducing-ps26054")
                            }
                            className="extend-card-corner-dots group relative flex flex-col justify-between p-8 rounded-[2px] border border-stone-300 bg-white hover:border-stone-400 hover:shadow-xs transition-all cursor-pointer"
                        >
                            <div className="space-y-5">
                                <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                                    <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-600 font-bold bg-stone-100 border border-stone-200 px-2.5 py-0.5 rounded-[2px]">
                                        SECTION 01 // ARCHITECTURAL
                                        SPECIFICATION
                                    </span>
                                    <span className="font-mono text-[10px] text-stone-400 font-medium">
                                        23 ARTICLES
                                    </span>
                                </div>

                                <div className="space-y-2">
                                    <h3 className="text-2xl font-bold text-stone-950 group-hover:text-stone-700 transition-colors tracking-tight">
                                        TECHNICAL DOCUMENTATION
                                    </h3>
                                    <p className="text-xs font-mono text-stone-500 uppercase tracking-wider">
                                        Physics Core · FlyHash Novelty ·
                                        Bayesian Diagnostics · Conformal RUL ·
                                        Mission R(t)
                                    </p>
                                    <p className="text-sm text-stone-600 leading-relaxed pt-1">
                                        The engineering architecture,
                                        crank-angle slider-crank physics, 20 Hz
                                        neuromorphic novelty detection, exact
                                        Bayesian fault isolation, degradation
                                        modeling, split conformal RUL bounds,
                                        and flight mission reliability.
                                    </p>
                                </div>

                                {/* Subsystem Highlights List */}
                                <div className="p-3 bg-stone-50 border border-stone-200 rounded-[2px] space-y-1.5 font-mono text-[11px] text-stone-700">
                                    <div className="flex items-center gap-2">
                                        <span className="size-1.5 rounded-full bg-stone-900" />
                                        <span>
                                            Layer 2: Slider-crank Wiebe
                                            thermodynamics and Δω(θ) torque
                                            deficit
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="size-1.5 rounded-full bg-stone-900" />
                                        <span>
                                            Layer 3: 20 Hz continuous FlyHash
                                            random projections
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="size-1.5 rounded-full bg-stone-900" />
                                        <span>
                                            Layer 4 &amp; 5: MIL-STD-1629A exact
                                            Bayesian network and conformal RUL
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div className="pt-6 mt-6 border-t border-stone-100 flex items-center justify-between font-mono text-xs text-stone-900 font-semibold uppercase tracking-wider group-hover:text-stone-700">
                                <span>Enter Technical Reference</span>
                                <ArrowRight
                                    size={15}
                                    className="transition-transform group-hover:translate-x-1"
                                />
                            </div>
                        </div>

                        {/* SECTION 02: OUR SIH JOURNEY */}
                        <div
                            onClick={() => onNavigate("journey")}
                            className="extend-card-corner-dots group relative flex flex-col justify-between p-8 rounded-[2px] border border-stone-300 bg-white hover:border-stone-400 hover:shadow-xs transition-all cursor-pointer"
                        >
                            <div className="space-y-5">
                                <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                                    <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-600 font-bold bg-stone-100 border border-stone-200 px-2.5 py-0.5 rounded-[2px]">
                                        SECTION 02 // FIELD NOTEBOOK &amp; AUDIT
                                    </span>
                                    <span className="font-mono text-[10px] text-stone-400 font-medium">
                                        CHRONICLE &amp; DEFENSE
                                    </span>
                                </div>

                                <div className="space-y-2">
                                    <h3 className="text-2xl font-bold text-stone-950 group-hover:text-stone-700 transition-colors tracking-tight">
                                        OUR SIH JOURNEY
                                    </h3>
                                    <p className="text-xs font-mono text-stone-500 uppercase tracking-wider">
                                        27 Research Studies · 66 Verified
                                        Commits · Comprehensive Verification
                                        Protocol
                                    </p>
                                    <p className="text-sm text-stone-600 leading-relaxed pt-1">
                                        The engineering evolution of ANUMAAN
                                        from problem statement analysis to
                                        plant-model physics, dual-runtime
                                        architecture, characterization testing,
                                        and full multi-engine integration.
                                    </p>
                                </div>

                                {/* Subsystem Highlights List */}
                                <div className="p-3 bg-stone-50 border border-stone-200 rounded-[2px] space-y-1.5 font-mono text-[11px] text-stone-700">
                                    <div className="flex items-center gap-2">
                                        <span className="size-1.5 rounded-full bg-stone-900" />
                                        <span>
                                            Research First: 27 foundational
                                            study documents before production
                                            code
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="size-1.5 rounded-full bg-stone-900" />
                                        <span>
                                            Rigorous Benchmarking:
                                            First-principles verification across
                                            every subsystem
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="size-1.5 rounded-full bg-stone-900" />
                                        <span>
                                            Adversarial Scrutiny: Pytest
                                            characterization regression suite
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div className="pt-6 mt-6 border-t border-stone-100 flex items-center justify-between font-mono text-xs text-stone-900 font-semibold uppercase tracking-wider group-hover:text-stone-700">
                                <span>Read The Engineering Chronicle</span>
                                <ArrowRight
                                    size={15}
                                    className="transition-transform group-hover:translate-x-1"
                                />
                            </div>
                        </div>
                    </div>
                </section>

                {/* 3. TECHNICAL SNAPSHOT (Contiguous Paneled Metrics Bar) */}
                <section className="py-12 border-b border-stone-200 bg-stone-50/50 px-4 sm:px-6 lg:px-12">
                    <div className="space-y-6">
                        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                            <div>
                                <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500 font-semibold block">
                                    [02 // FLEET METRICS &amp; GROUND TRUTH]
                                </span>
                                <h2 className="text-xl sm:text-2xl font-bold text-stone-900 mt-1 tracking-tight">
                                    Subsystem Operating Parameters &amp;
                                    Reachability
                                </h2>
                            </div>
                            <p className="text-xs text-stone-500 font-mono max-w-md">
                                Every value is verified against active
                                repository code, tests, and manufacturer engine
                                manuals. Zero fabricated metrics.
                            </p>
                        </div>

                        {/* Contiguous Paneled Metric Bar */}
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 divide-y lg:divide-y-0 lg:divide-x divide-stone-200 border border-stone-200 bg-white rounded-[2px] overflow-hidden">
                            {[
                                {
                                    label: "TELEMETRY RATE",
                                    val: "20 Hz",
                                    sub: "Synchronized wall loop",
                                },
                                {
                                    label: "FLEET PROFILES",
                                    val: "5 Engines",
                                    sub: "Rotax 912/914/915, AE300, VRDE",
                                },
                                {
                                    label: "PS FAULT MODES",
                                    val: "8 Faults",
                                    sub: "Physics-derived signatures",
                                },
                                {
                                    label: "FMECA TAXONOMY",
                                    val: "20 Modes",
                                    sub: "MIL-STD-1629A RPN scored",
                                },
                                {
                                    label: "MISSION RISK",
                                    val: "P(Mission)",
                                    sub: "Monte Carlo hazard rate",
                                },
                                {
                                    label: "INTEROPERABILITY",
                                    val: "STANAG 4586",
                                    sub: "Level of Interoperability 2",
                                },
                            ].map((stat, i) => (
                                <div
                                    key={i}
                                    className="p-4 bg-white flex flex-col justify-between"
                                >
                                    <span className="block font-mono text-[9px] uppercase tracking-[0.1em] text-stone-500 font-semibold">
                                        {stat.label}
                                    </span>
                                    <span className="block font-mono text-2xl font-bold text-stone-950 mt-1 tabular-nums">
                                        {stat.val}
                                    </span>
                                    <span className="block text-[11px] text-stone-500 mt-0.5">
                                        {stat.sub}
                                    </span>
                                </div>
                            ))}
                        </div>

                        {/* Two Runtimes Architecture Note */}
                        <div className="p-4 bg-white border border-stone-200 rounded-[2px] flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs">
                            <div className="flex items-center gap-3">
                                <span className="size-2 rounded-full bg-emerald-600"></span>
                                <span className="font-mono font-semibold uppercase text-stone-900">
                                    Coordinated Runtime Architecture:
                                </span>
                                <span className="text-stone-600">
                                    Multi-engine <strong>RuntimeHub</strong> (5
                                    selectable profiles, tier-0 FlyHash novelty
                                    per tick) runs in coordinated partnership
                                    with the{" "}
                                    <strong>Rotax 912 iS Diagnostic GCS</strong>{" "}
                                    workspace (Bayesian network, RUL, voice
                                    copilot).
                                </span>
                            </div>
                            <button
                                onClick={() =>
                                    onNavigate(
                                        "technical/04-system-architecture",
                                    )
                                }
                                className="font-mono text-[11px] text-stone-900 hover:underline uppercase shrink-0 font-semibold"
                            >
                                Architecture Spec →
                            </button>
                        </div>
                    </div>
                </section>

                {/* 4. FEATURED ENGINEERING ARTICLE (Extend Hero Card Pattern) */}
                <section className="py-16 px-4 sm:px-6 lg:px-12 border-b border-stone-200">
                    <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
                        <div>
                            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500 font-semibold block">
                                [03 // FLAGSHIP COMBUSTION SUBSYSTEM]
                            </span>
                            <h2 className="text-2xl sm:text-3xl font-bold text-stone-900 mt-1 tracking-tight">
                                Featured Engineering Article
                            </h2>
                        </div>
                        <span className="font-mono text-xs text-stone-500 font-semibold">
                            TECHNICAL / 06
                        </span>
                    </div>

                    <div className="extend-card-corner-dots border border-stone-300 rounded-[2px] bg-white p-6 sm:p-8 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
                        <div className="lg:col-span-7 space-y-4">
                            <div className="flex items-center gap-2">
                                <span className="font-mono text-[10px] uppercase tracking-wider bg-stone-100 text-stone-700 px-2 py-0.5 rounded-[2px] border border-stone-300 font-semibold">
                                    PHYSICS &amp; COMBUSTION
                                </span>
                                <span className="text-stone-300">|</span>
                                <span className="font-mono text-[10px] text-stone-500 uppercase">
                                    ROTAX 912 iS SPECIFICATION
                                </span>
                            </div>

                            <h3 className="text-2xl sm:text-3xl font-bold text-stone-950 tracking-tight leading-snug">
                                Crank-Angle Combustion Dynamics &amp;
                                Torque-Deficit Misfire Detection
                            </h3>

                            <p className="text-sm text-stone-600 leading-relaxed">
                                Rather than asserting hand-drawn synthetic
                                signatures, ANUMAAN derives cylinder pressure
                                from slider-crank kinematics and a Wiebe heat
                                release function, propagating gas and
                                reciprocating inertial torque into instantaneous
                                crankshaft angular velocity &omega;(&theta;). A
                                single cylinder misfire produces genuine
                                physical coupling across vibration, torque, and
                                exhaust gas temperatures.
                            </p>

                            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
                                <div className="p-3 border border-stone-200 rounded-[2px] bg-stone-50">
                                    <dt className="font-mono text-[9px] uppercase tracking-wider text-stone-500">
                                        Firing Order
                                    </dt>
                                    <dd className="font-mono text-lg font-bold text-stone-900 mt-1">
                                        1-4-2-3
                                    </dd>
                                    <dd className="text-[10px] text-stone-500">
                                        Boxer-4 720° cycle
                                    </dd>
                                </div>
                                <div className="p-3 border border-stone-200 rounded-[2px] bg-stone-50">
                                    <dt className="font-mono text-[9px] uppercase tracking-wider text-stone-500">
                                        Bore × Stroke
                                    </dt>
                                    <dd className="font-mono text-lg font-bold text-stone-900 mt-1">
                                        84 × 61 mm
                                    </dd>
                                    <dd className="text-[10px] text-stone-500">
                                        1,352 cm³ displacement
                                    </dd>
                                </div>
                                <div className="p-3 border border-stone-200 rounded-[2px] bg-stone-50">
                                    <dt className="font-mono text-[9px] uppercase tracking-wider text-stone-500">
                                        Misfire Metric
                                    </dt>
                                    <dd className="font-mono text-lg font-bold text-stone-900 mt-1">
                                        Δω(θ) Deficit
                                    </dd>
                                    <dd className="text-[10px] text-stone-500">
                                        Per-cylinder attribution
                                    </dd>
                                </div>
                            </dl>

                            <div className="pt-4 flex flex-wrap items-center gap-3">
                                <button
                                    onClick={() =>
                                        onNavigate(
                                            "technical/06-engine-physics",
                                        )
                                    }
                                    className="btn-extend-primary"
                                >
                                    <span>Read Full Article</span>
                                    <ArrowRight size={14} />
                                </button>
                                <button
                                    onClick={onOpenModelViewer}
                                    className="btn-extend-tactile"
                                >
                                    <Box size={14} />
                                    <span>View Engine CAD</span>
                                </button>
                            </div>
                        </div>

                        <div className="lg:col-span-5 relative bg-stone-100 border border-stone-200 rounded-[2px] overflow-hidden">
                            <img
                                src="/assets/blender/engine_master_hero.png"
                                alt="ANUMAAN Master Engine Twin CAD Model"
                                className="w-full h-auto object-cover hover:scale-102 transition-transform duration-300"
                            />
                            <div className="p-3 bg-stone-50 border-t border-stone-200 text-[11px] font-mono text-stone-500 flex items-center justify-between">
                                <span>Blender Master Model: Rotax 912 iS</span>
                                <span className="uppercase text-stone-400">
                                    Draco GLB
                                </span>
                            </div>
                        </div>
                    </div>
                </section>

                {/* 5. CORE ARCHITECTURE DIAGRAM */}
                <section className="py-16 px-4 sm:px-6 lg:px-12 border-b border-stone-200 bg-stone-50/50">
                    <div className="space-y-6">
                        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                            <div>
                                <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500 font-semibold block">
                                    [04 // CORE ARCHITECTURE BLUEPRINT]
                                </span>
                                <h2 className="text-2xl sm:text-3xl font-bold text-stone-900 mt-1 tracking-tight">
                                    Core System Architecture &amp; Data Path
                                </h2>
                            </div>
                            <p className="text-xs text-stone-600 max-w-lg">
                                Monochrome interactive representation of the
                                OSA-CBM six-layer pipeline from real-time
                                ingestion and crank-angle physics to sparse
                                novelty, Bayesian diagnosis, and mission
                                reliability.
                            </p>
                        </div>

                        <MermaidDiagram
                            chart={coreArchitectureMermaid}
                            caption="Figure 1: ANUMAAN seven-layer runtime architecture, illustrating deterministic low-latency detection vs cognitive diagnostic split."
                        />
                    </div>
                </section>

                {/* 6. SELECTED TECHNICAL ARTICLES (Extend Benchmarks Cards Grid) */}
                <section className="py-16 px-4 sm:px-6 lg:px-12 border-b border-stone-200">
                    <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-4">
                        <div>
                            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500 font-semibold block">
                                [05 // SELECTED TECHNICAL MODULES]
                            </span>
                            <h2 className="text-2xl sm:text-3xl font-bold text-stone-900 mt-1 tracking-tight">
                                Selected Technical Articles
                            </h2>
                        </div>
                        <button
                            onClick={() =>
                                onNavigate("technical/01-introducing-ps26054")
                            }
                            className="btn-extend-tactile"
                        >
                            <span>View All 23 Articles</span>
                            <ArrowRight size={13} />
                        </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {/* Card 1: Sparse Novelty Coding */}
                        <ArticleCard
                            category="AI / ML NOVELTY"
                            title="Bio-Inspired Sparse Novelty Coding (FlyHash)"
                            description="Continuous per-tick expand-and-sparsify random projection modeled on the fruit fly olfactory circuit. Detects departures from nominal engine behavior without requiring labeled fault datasets."
                            slug="technical/10-bio-inspired-sparse-novelty-coding"
                            metrics={[
                                {
                                    label: "TICK FREQUENCY",
                                    value: "20 Hz",
                                    subtext: "Continuous per-tick",
                                },
                                {
                                    label: "ENCODING",
                                    value: "FlyHash",
                                    subtext: "Neuromorphic sparse",
                                },
                            ]}
                            specs={[
                                {
                                    label: "Algorithm",
                                    value: "Locality-Sensitive Sparse Random Projection",
                                },
                                {
                                    label: "Feature Input",
                                    value: "Order-Domain Vibration + Physics Residuals",
                                },
                                {
                                    label: "Honesty Note",
                                    value: "Application scoped; established ML family",
                                },
                            ]}
                            sources={[
                                {
                                    title: "backend/ml/flyhash_novelty.py",
                                    meta: "Per-tick detector",
                                },
                                {
                                    title: "docs/study/20_novelty_and_research.md",
                                    meta: "Published research correction",
                                },
                            ]}
                            onNavigate={onNavigate}
                        />

                        {/* Card 2: Bayesian Fault Diagnosis */}
                        <ArticleCard
                            category="DIAGNOSTICS"
                            title="Bayesian Fault Diagnosis &amp; Isolability"
                            description="Dual diagnostic engine: deterministic ATA-chapter rule-based agent combined with an exact Bayesian network reasoning over 20 FMECA failure modes and isolability signatures."
                            slug="technical/11-fault-diagnosis"
                            metrics={[
                                {
                                    label: "FAULT TARGETS",
                                    value: "8 Modes",
                                    subtext: "DRDO PS matrix",
                                },
                                {
                                    label: "DIAGNOSTIC AGENT",
                                    value: "Deterministic",
                                    subtext: "Zero hallucination risk",
                                },
                            ]}
                            specs={[
                                {
                                    label: "Taxonomy",
                                    value: "MIL-STD-1629A Failure Modes",
                                },
                                {
                                    label: "Evidence Input",
                                    value: "Channel-level residual threshold exceedances",
                                },
                                {
                                    label: "Action Output",
                                    value: "ATA-Chapter Directive & Checklist",
                                },
                            ]}
                            sources={[
                                {
                                    title: "backend/diagnose/bn.py",
                                    meta: "Bayesian isolability engine",
                                },
                                {
                                    title: "backend/agent/diagnostic_agent.py",
                                    meta: "ATA-chapter generator",
                                },
                            ]}
                            onNavigate={onNavigate}
                        />

                        {/* Card 3: Vibration Order Tracking */}
                        <ArticleCard
                            category="SIGNAL PROCESSING"
                            title="Tach-Synchronous Vibration Order Tracking"
                            description="Angular resampling of vibration signals synchronized to shaft RPM, converting fixed-frequency smearing into invariant engine orders, with Hilbert envelope demodulation for bearings."
                            slug="technical/12-vibration-analysis"
                            metrics={[
                                {
                                    label: "RESAMPLING",
                                    value: "Tach-Sync",
                                    subtext: "Order-domain angle",
                                },
                                {
                                    label: "DEMODULATION",
                                    value: "Hilbert",
                                    subtext: "Bearing fault envelopes",
                                },
                            ]}
                            specs={[
                                {
                                    label: "Harmonics",
                                    value: "Half-order combustion, 1X, 2X, 3X mesh",
                                },
                                {
                                    label: "Differentiator",
                                    value: "Speed-invariant under UAV throttle sweeps",
                                },
                            ]}
                            sources={[
                                {
                                    title: "docs/study/26_order_tracking_and_envelope.md",
                                    meta: "Formulation",
                                },
                                {
                                    title: "docs/audit/05_expanded_survey.md",
                                    meta: "Competitive benchmark",
                                },
                            ]}
                            onNavigate={onNavigate}
                        />

                        {/* Card 4: Degradation & Conformal RUL */}
                        <ArticleCard
                            category="PROGNOSTICS"
                            title="Degradation Modeling &amp; Split Conformal RUL"
                            description="Thermal and mechanical stress accumulation via Rainflow cycle counting and Miner linear damage rule, paired with split conformal prediction providing a calibrated lower confidence bound."
                            slug="technical/14-remaining-useful-life"
                            metrics={[
                                {
                                    label: "DAMAGE RULE",
                                    value: "Miner's Rule",
                                    subtext: "Rainflow stress cycles",
                                },
                                {
                                    label: "BOUND TYPE",
                                    value: "Conformal",
                                    subtext: "Guaranteed finite coverage",
                                },
                            ]}
                            specs={[
                                {
                                    label: "Components",
                                    value: "Cylinder heads, bearings, turbocharger",
                                },
                                {
                                    label: "Output",
                                    value: "Lower RUL bound at specified (1 - α) coverage",
                                },
                            ]}
                            sources={[
                                {
                                    title: "backend/prognose/rul.py",
                                    meta: "Prognostic estimators",
                                },
                                {
                                    title: "backend/evaluation/conformal.py",
                                    meta: "Calibration suite",
                                },
                            ]}
                            onNavigate={onNavigate}
                        />

                        {/* Card 5: Monte Carlo Mission Reliability */}
                        <ArticleCard
                            category="MISSION RELIABILITY"
                            title="Mission Executive &amp; Monte Carlo Hazard R(t)"
                            description="Computes mission reliability R = P(mission completes without abort | health, profile, environment) via Monte Carlo integration over per-component hazard rates across 10 flight phases."
                            slug="technical/17-mission-reliability"
                            metrics={[
                                {
                                    label: "RISK INTEGRATION",
                                    value: "Monte Carlo",
                                    subtext: "Hazard rate composition",
                                },
                                {
                                    label: "MISSION PHASES",
                                    value: "10 Phases",
                                    subtext: "Taxi to descent/landing",
                                },
                            ]}
                            specs={[
                                {
                                    label: "Executive Rate",
                                    value: "20 Hz Kinematics State Machine",
                                },
                                {
                                    label: "Atmosphere Model",
                                    value: "ISA Temperature Lapse & Density",
                                },
                                {
                                    label: "Action",
                                    value: "Throttle derate & profile replan advisory",
                                },
                            ]}
                            sources={[
                                {
                                    title: "backend/mission/reliability.py",
                                    meta: "Hazard model logic",
                                },
                                {
                                    title: "backend/mission/executive.py",
                                    meta: "Authoritative state machine",
                                },
                            ]}
                            onNavigate={onNavigate}
                        />

                        {/* Card 6: 3D Twin & Simulation */}
                        <ArticleCard
                            category="3D TWIN &amp; SIMULATION"
                            title="The 3D Digital Twin: WebGL &amp; Blender Master"
                            description="Three visualization tracks consuming one authoritative runtime state: Draco-compressed Three.js browser twin for 5 engines, Blender master twin, and Ladakh canyon simulation."
                            slug="technical/18-3d-digital-twin"
                            metrics={[
                                {
                                    label: "FORMAT",
                                    value: "Draco GLB",
                                    subtext: "Ultra-compressed web mesh",
                                },
                                {
                                    label: "PLATFORMS",
                                    value: "5 Engines",
                                    subtext: "Rotax, Austro, VRDE",
                                },
                            ]}
                            specs={[
                                {
                                    label: "Highlighting",
                                    value: "Component-specific fault targeting",
                                },
                                {
                                    label: "Synchronization",
                                    value: "WebSocket telemetry stream",
                                },
                            ]}
                            sources={[
                                {
                                    title: "apps/threejs_twin/index.html",
                                    meta: "WebGL frontend",
                                },
                                {
                                    title: "assets/models/draco/",
                                    meta: "Verified GLB assets",
                                },
                            ]}
                            onNavigate={onNavigate}
                        />
                    </div>
                </section>

                {/* 7. DATASET / RESEARCH FEATURE */}
                <section className="py-16 px-4 sm:px-6 lg:px-12 border-b border-stone-200 bg-stone-50/50">
                    <div className="space-y-8">
                        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                            <div>
                                <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500 font-semibold block">
                                    [06 // DATASET VERIFICATION TIERS]
                                </span>
                                <h2 className="text-2xl sm:text-3xl font-bold text-stone-900 mt-1 tracking-tight">
                                    Dataset Strategy: Six-Tier Validation
                                    Architecture
                                </h2>
                            </div>
                            <button
                                onClick={() =>
                                    onNavigate("technical/15-dataset-strategy")
                                }
                                className="btn-extend-tactile"
                            >
                                <span>Explore Dataset Strategy</span>
                                <ArrowRight size={13} />
                            </button>
                        </div>

                        {/* Visual ML Pipeline */}
                        <div className="p-6 bg-white border border-stone-300 rounded-[2px]">
                            <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500 font-semibold block mb-4">
                                Machine Learning &amp; Prognostics Verification
                                Flow
                            </span>
                            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 text-center">
                                {[
                                    {
                                        step: "01. RAW DATASET",
                                        desc: "Public benchmarks and HIL generator",
                                        label: "C-MAPSS / CWRU / ACES",
                                    },
                                    {
                                        step: "02. PREPROCESSING",
                                        desc: "Tach-sync order tracking and ISA correction",
                                        label: "Angle Resampling",
                                    },
                                    {
                                        step: "03. REPRESENTATION",
                                        desc: "Residuals and sparse FlyHash projections",
                                        label: "Hyperdimensional Vector",
                                    },
                                    {
                                        step: "04. MODEL INFERENCE",
                                        desc: "Bayesian network and conformal bounds",
                                        label: "Hazard and Isolability",
                                    },
                                    {
                                        step: "05. VALIDATION",
                                        desc: "Characterization test pinning and ground truth",
                                        label: "Closed-Loop Verification",
                                    },
                                ].map((pipe, i) => (
                                    <div
                                        key={i}
                                        className="p-3 border border-stone-200 rounded-[2px] bg-stone-50 flex flex-col justify-between"
                                    >
                                        <span className="font-mono text-[10px] text-stone-700 font-semibold">
                                            {pipe.step}
                                        </span>
                                        <span className="font-sans font-bold text-xs text-stone-900 my-1">
                                            {pipe.label}
                                        </span>
                                        <span className="text-[10px] text-stone-500">
                                            {pipe.desc}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Verified Dataset Comparison Table */}
                        <div className="border border-stone-300 rounded-[2px] bg-white overflow-x-auto shadow-xs">
                            <table className="w-full text-left border-collapse text-xs">
                                <thead>
                                    <tr className="border-b border-stone-200 bg-stone-100 font-mono text-[10px] text-stone-700 uppercase tracking-wider">
                                        <th className="p-3.5 font-semibold">
                                            Tier
                                        </th>
                                        <th className="p-3.5 font-semibold">
                                            Dataset
                                        </th>
                                        <th className="p-3.5 font-semibold">
                                            Domain &amp; Platform
                                        </th>
                                        <th className="p-3.5 font-semibold">
                                            Engineering Use in ANUMAAN
                                        </th>
                                        <th className="p-3.5 font-semibold">
                                            Target Subsystem
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-stone-100 font-sans">
                                    <tr>
                                        <td className="p-3.5 font-mono font-semibold text-stone-900">
                                            Tier 1
                                        </td>
                                        <td className="p-3.5 font-bold text-stone-900">
                                            NASA C-MAPSS / N-CMAPSS
                                        </td>
                                        <td className="p-3.5 text-stone-600">
                                            Simulated turbofan run-to-failure
                                        </td>
                                        <td className="p-3.5 text-stone-600">
                                            Prognostics pipeline validation
                                            &amp; asymmetric scoring
                                        </td>
                                        <td className="p-3.5 font-mono text-stone-800">
                                            Remaining Useful Life (RUL)
                                        </td>
                                    </tr>
                                    <tr>
                                        <td className="p-3.5 font-mono font-semibold text-stone-900">
                                            Tier 2
                                        </td>
                                        <td className="p-3.5 font-bold text-stone-900">
                                            CWRU &amp; Paderborn
                                        </td>
                                        <td className="p-3.5 text-stone-600">
                                            Bearing vibration &amp; motor
                                            current
                                        </td>
                                        <td className="p-3.5 text-stone-600">
                                            Hilbert envelope demodulation &amp;
                                            defect frequency isolation
                                        </td>
                                        <td className="p-3.5 font-mono text-stone-800">
                                            Gearbox &amp; Bearing Diagnostics
                                        </td>
                                    </tr>
                                    <tr>
                                        <td className="p-3.5 font-mono font-semibold text-stone-900">
                                            Tier 3
                                        </td>
                                        <td className="p-3.5 font-bold text-stone-900">
                                            ALFA &amp; NASA ACES
                                        </td>
                                        <td className="p-3.5 text-stone-600">
                                            Altus II UAV (Rotax 914 Turbo) &amp;
                                            Autonomous Flights
                                        </td>
                                        <td className="p-3.5 text-stone-600">
                                            Real UAV operational flight state
                                            &amp; engine-out transients
                                        </td>
                                        <td className="p-3.5 font-mono text-stone-800">
                                            Flight Telemetry &amp; Detection
                                            Latency
                                        </td>
                                    </tr>
                                    <tr>
                                        <td className="p-3.5 font-mono font-semibold text-stone-900">
                                            Tier 6
                                        </td>
                                        <td className="p-3.5 font-bold text-stone-900">
                                            Calibrated HIL Physics Generator
                                        </td>
                                        <td className="p-3.5 text-stone-600">
                                            ANUMAAN 1st-principles piston plant
                                            model
                                        </td>
                                        <td className="p-3.5 text-stone-600">
                                            Injects all 8 DRDO PS fault modes
                                            with verified ground truth
                                        </td>
                                        <td className="p-3.5 font-mono text-stone-800">
                                            End-to-End System Evaluation
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>

                {/* 8. SIH JOURNEY FEATURE (Field Notebook Style) */}
                <section className="py-16 px-4 sm:px-6 lg:px-12">
                    <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
                        <div>
                            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500 font-semibold block">
                                [07 // FIELD NOTEBOOK &amp; AUDIT]
                            </span>
                            <h2 className="text-2xl sm:text-3xl font-bold text-stone-900 mt-1 tracking-tight">
                                Our SIH Journey: Research, Rigor &amp;
                                Verification
                            </h2>
                        </div>
                        <button
                            onClick={() =>
                                onNavigate("journey/01-the-engineering-story")
                            }
                            className="btn-extend-tactile"
                        >
                            <span>Read Engineering Story</span>
                            <ArrowRight size={13} />
                        </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        {/* Chapter 01 Card */}
                        <div className="extend-card-corner-dots p-6 sm:p-7 border border-stone-300 rounded-[2px] bg-white space-y-4">
                            <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                                <span className="font-mono text-[10px] uppercase tracking-wider bg-stone-100 px-2 py-0.5 rounded-[2px] border border-stone-200 text-stone-700 font-semibold">
                                    CHAPTER 01 // GENESIS
                                </span>
                                <span className="font-mono text-xs text-stone-400">
                                    66 COMMITS ANALYZED
                                </span>
                            </div>
                            <h3 className="text-xl font-bold text-stone-950 tracking-tight">
                                The Engineering Story: Research First, Code
                                Second
                            </h3>
                            <p className="text-xs text-stone-600 leading-relaxed">
                                How the project began with a 27-part research
                                study, evolved into a dual-runtime architecture,
                                constructed the crank-angle physics chain, and
                                achieved end-to-end integration across all five
                                engine platforms.
                            </p>
                            <div className="p-3.5 bg-stone-50 border-l-2 border-stone-800 rounded-[2px] text-xs space-y-1">
                                <span className="font-mono text-[10px] text-stone-600 uppercase font-semibold block">
                                    Scientific Discipline
                                </span>
                                <p className="text-stone-700 italic">
                                    &ldquo;Bio-Inspired Sparse Novelty Coding
                                    fuses hyperdimensional olfactory projection
                                    circuits with order-domain aero piston
                                    vibration and physics residuals under strict
                                    UAV datalink bandwidth constraints.&rdquo;
                                </p>
                            </div>
                            <button
                                onClick={() =>
                                    onNavigate(
                                        "journey/01-the-engineering-story",
                                    )
                                }
                                className="btn-extend-tactile w-full justify-between"
                            >
                                <span>Read Chapter 01</span>
                                <ArrowRight size={13} />
                            </button>
                        </div>

                        {/* Chapter 02 Card */}
                        <div className="extend-card-corner-dots p-6 sm:p-7 border border-stone-300 rounded-[2px] bg-white space-y-4">
                            <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                                <span className="font-mono text-[10px] uppercase tracking-wider bg-stone-100 px-2 py-0.5 rounded-[2px] border border-stone-200 text-stone-700 font-semibold">
                                    CHAPTER 02 // DEFENSE
                                </span>
                                <span className="font-mono text-xs text-stone-400">
                                    CHARACTERIZATION TESTS
                                </span>
                            </div>
                            <h3 className="text-xl font-bold text-stone-950 tracking-tight">
                                Demonstration Methodology & Verification
                                Discipline
                            </h3>
                            <p className="text-xs text-stone-600 leading-relaxed">
                                Controlled engineering demonstrations,
                                characterization regression tests pinning
                                headline numbers, automated browser Playwright
                                verification, and proving why the system stays
                                quiet during legitimate throttle transients.
                            </p>
                            <div className="p-3.5 bg-stone-50 border-l-2 border-stone-800 rounded-[2px] text-xs space-y-1">
                                <span className="font-mono text-[10px] text-stone-600 uppercase font-semibold block">
                                    Verification Discipline
                                </span>
                                <p className="text-stone-700">
                                    Characterization tests in pytest pin results
                                    automatically so numbers quoted to
                                    evaluators cannot quietly drift over time.
                                </p>
                            </div>
                            <button
                                onClick={() =>
                                    onNavigate(
                                        "journey/02-preparing-for-evaluation",
                                    )
                                }
                                className="btn-extend-tactile w-full justify-between"
                            >
                                <span>Read Chapter 02</span>
                                <ArrowRight size={13} />
                            </button>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
};
