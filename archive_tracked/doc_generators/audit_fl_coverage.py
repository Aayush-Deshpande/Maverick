import os
import sys

TARGET_DIR = r"e:\backup-llm\backup-no-llm\3d_engine\final_touch"

KEY_CONCEPTS = [
    # Foundations & Architectures
    "Cross-Silo", "Cross-Device", "Split Learning", "Hierarchical Federated Learning", "Decentralized / P2P",
    "NVFlare", "DXO", "FL Model Controller",
    # Aggregation & Optimization
    "FedAvg", "FedProx", "SCAFFOLD", "FedOpt", "FedNova", "FedAdagrad", "FedAdam", "FedYogi", "q-FFL",
    "Client Drift", "Proximal Term", "Control Variates", "Objective Inconsistency",
    # Privacy, Security & Attacks
    "Differential Privacy", "Renyi Differential Privacy", "Moments Accountant", "Gradient Inversion",
    "Deep Leakage from Gradients", "Geiping", "Label Restoration", "Deep Inception", "Byzantine",
    "Krum", "Multi-Krum", "Trimmed Mean", "Bulyan", "Sybil Attack", "Backdoor Attack",
    # Efficiency, PEFT & Preprocessing
    "Parameter-Efficient Fine-Tuning", "LoRA", "FedRand", "Noise Amplification", "Quantization", "Sparsification",
    "FedPS", "Count-Min Sketch", "KLL Sketch", "PowerTransform", "Box-Cox", "Yeo-Johnson",
    # Non-IID & Personalization
    "Dirichlet Distribution", "Earth Mover's Distance", "HtFLlib", "FedRep", "FedPer", "pFedMe", "Ditto",
    "FedProto", "FedGH", "FML", "Federated Mutual Learning",
    # Healthcare & Applications
    "HIPAA", "GDPR", "DICOM", "FHIR", "Electronic Health Records", "SaMD", "GMLP", "Model Inversion"
]

all_text = ""
file_texts = {}
for fname in os.listdir(TARGET_DIR):
    if fname.startswith("FL_") and fname.endswith(".md"):
        fpath = os.path.join(TARGET_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            all_text += "\n" + content
            file_texts[fname] = content

print(f"Total Knowledge Base Size: {len(all_text):,} characters across {len(file_texts)} documents.\n")

missing = []
found = []

for concept in KEY_CONCEPTS:
    count = all_text.lower().count(concept.lower())
    if count == 0:
        missing.append(concept)
    else:
        found.append((concept, count))

print(f"Audit Results: {len(found)}/{len(KEY_CONCEPTS)} concepts verified present.")
if missing:
    print(f"MISSING CONCEPTS ({len(missing)}):")
    for m in missing:
        print(f"  - {m}")
else:
    print("ALL 100% OF KEY FEDERATED LEARNING THEORETICAL CONCEPTS FOUND!\n")

print("Sample Concept Frequencies:")
for c, cnt in found[:20]:
    print(f"  {c:<30}: {cnt} occurrences")
