# 🧠 Knowledge Store, Vector RAG & Local AI Copilot
**DRDO / iDEX Problem Statement ID: 26054**  
*Air-Gapped Document Ingestion, Semantic Vector RAG & Local 4-bit Qwen3-4B LLM*

---

## 1. Air-Gapped Technical Manual Ingestion

To support Explainable AI (XAI) and authoritative maintenance guidance without internet or cloud access, the system includes a dedicated offline document indexing pipeline (`LocalKnowledgeStore`).

```
data/documents/
├── ROTAX_912_iS_Line_Maintenance_Manual_MML.pdf / .docx / .md
├── ROTAX_912_iS_Heavy_Maintenance_and_Overhaul_Manual.pdf / .docx / .md
├── ROTAX_912_iS_Illustrated_Parts_Catalog_and_Torque_Specs.pdf / .docx / .md
├── ROTAX_912_iS_Operators_Manual_OM.pdf / .docx / .md
├── ROTAX_912_iS_Service_Bulletins_SB_SI.pdf / .docx / .md
├── DRDO_FMECA_Failure_Modes_and_Effects_Analysis.pdf / .docx / .md
└── DRDO_TAPAS_BH201_Flight_Operations_and_SOP.pdf / .docx / .md
```

### Document Loading & Chunking Pipeline
* **Loaders:** `pdf_loader.py` (PyPDF), `office_loader.py` (python-docx, python-pptx), `text_loader.py`.
* **Chunking (`chunker.py`):** Sliding-window chunker with a 500-token window and 100-token overlap, preserving ATA section headings and mechanical torque tables.

---

## 2. Multi-Tier Semantic Vector Retrieval (RAG)

When a query is received, `LocalKnowledgeStore` executes a 3-tier ranking strategy:

```
                                  ┌─────────────────────────────────────┐
                                  │           OPERATOR QUERY            │
                                  └──────────────────┬──────────────────┘
                                                     │
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: SEMANTIC EMBEDDING RETRIEVAL (Primary)                                                         │
│ • Encodes query and passages with all-MiniLM-L6-v2 (CPU / PyTorch).                                     │
│ • Computes dense cosine similarity over all cached document vectors.                                   │
└────────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                     │ (If sentence-transformers available)
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 2: FLASHRANK LOCAL CROSS-ENCODER (Reranking)                                                      │
│ • Quantized ONNX TinyBERT cross-encoder reranks top 10 candidates.                                     │
│ • Computes deep passage-query cross-attention scores with zero external API calls.                    │
└────────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                     │ (If FlashRank installed)
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 3: DETERMINISTIC LEXICAL KEYWORD OVERLAP (Fallback)                                               │
│ • Exact keyword frequency matching with inverse document length normalization.                         │
│ • Guarantees sub-second retrieval even on barebones systems with zero dependencies.                    │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Local 4-bit NF4 Qwen3-4B Reasoning Engine

To provide natural language reasoning on defense laptops without internet or cloud APIs, the system runs **Qwen3-4B** locally on the workstation GPU:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                         LOCAL QWEN3-4B REASONING ENGINE                                  │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ • Base Model: Qwen/Qwen3-4B causal language model                                        │
│ • Quantization: 4-bit NormalFloat4 (NF4) via BitsAndBytes                                │
│ • Compute Dtype: bfloat16                                                                │
│ • VRAM Allocation: ~2.5 GB allocated (Fits comfortably on 6GB RTX 4050 Laptop GPUs)     │
│ • Execution Mode: 100% On-Device / Fully Air-Gapped                                      │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ ARCHITECTURAL GUARDS:                                                                    │
│ 1. Lazy Loading: Loaded on-demand into VRAM only when first required.                   │
│ 2. Soft Failure: GPU errors or missing CUDA fall back to fast extractive RAG.           │
│ 3. Thread Decoupling: Generates on a worker thread, never blocking 50 Hz telemetry.     │
│ 4. Thinking Mode Off: Disables <think> reasoning preamble to cut latency in half.        │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Defense Safety Guardrails

All operator inputs pass through defense safety filters in `MissionCopilot.check_guardrails()`:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             DEFENSE SAFETY GUARDRAIL MATRIX                              │
├───────────────────────┬──────────────────────────────────┬───────────────────────────────┤
│ Guardrail Category    │ Trigger Pattern Examples         │ System Response               │
├───────────────────────┼──────────────────────────────────┼───────────────────────────────┤
│ **Jailbreak / Prompt  │ "ignore previous instructions",  │ "Security alert: Flight       │
│ Injection**           │ "you are now DAN", "bypass"      │ parameters and safety policies│
│                       │                                  │ cannot be overridden."        │
├───────────────────────┼──────────────────────────────────┼───────────────────────────────┤
│ **Unsafe Flight       │ "shut down engine mid-air",      │ "COMMAND REJECTED: Safety     │
│ Directives**          │ "fly into mountain", "exceed max │ guardrails prevent commands   │
│                       │ redline RPM"                     │ that violate flight limits."  │
├───────────────────────┼──────────────────────────────────┼───────────────────────────────┤
│ **Off-Topic Queries** │ "tell me a joke", "write a poem",│ "I am the Rotax 912 iS Copilot│
│                       │ "who won the game", "recipes"    │ I assist with propulsion, ATA │
│                       │                                  │ manuals, and sorties."        │
└───────────────────────┴──────────────────────────────────┴───────────────────────────────┘
```

---

## 5. Deterministic Causal Grounding (Zero Hallucination)

In military aviation, language models must **never invent sensor values or hallucinate failure causes**. The system enforces strict physical grounding:

```
Plane 1 Deterministic Engine
(Computes Ground Truth: Fault ID, 14 Residuals, Causal Chain)
                       │
                       ▼
Prompt Constructor passes ground truth explicitly:
"Diagnosed Fault: CYLINDER_2_CHT_OVERHEAT (ATA 72-00)
 Causal Chain: Baffle seal leak -> CHT_2 surges -> EGT_2 climbs -> Oil temp rises"
                       │
                       ▼
Retrieved Technical Manual Passages (ATA 72-00-00 MML)
                       │
                       ▼
System Prompt Constraint:
"You are given ground truth computed by the physics engine. Your job is ONLY to
 explain this exact causal chain using the retrieved passages. NEVER invent
 sensor values, fault IDs, or steps not present in the provided state."
                       │
                       ▼
High-Fidelity, Operationally Grounded Explanation
```
