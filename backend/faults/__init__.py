"""Fault registry (configs/faults.json) and, from card M0-04, the fault manager. DECISIONS D2, D9."""
from backend.faults.registry import FaultRegistry, FaultRegistryError, FaultRejected, load_fault_registry

__all__ = ["FaultRegistry", "FaultRegistryError", "FaultRejected", "load_fault_registry"]
