# Pre-flight check run by launch_standalone_app.bat before opening the Blender 3D twin, to
# report whether the 20 Hz backend is already reachable (live telemetry) or the twin will
# fall back to Autonomous Digital Twin Mode.
#
# Kept as a standalone .ps1 (invoked via `-File`) rather than an inline `powershell -Command
# "..."` one-liner embedded in the .bat file, for the same reason as
# scripts\check_backend_port.ps1: cmd.exe's quoting rules mangle a `try { ... } catch { ... }`
# one-liner in some invocation contexts (confirmed repro: running the .bat via `cmd /c` from
# inside PowerShell threw "`. was unexpected at this time."` from the corrupted string before
# PowerShell's own parser ever saw valid syntax). A separate .ps1 file sidesteps cmd.exe's
# quoting/escaping entirely. Exit code 0 = backend reachable, 1 = not reachable.

try {
    Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 1 -UseBasicParsing | Out-Null
    exit 0
} catch {
    exit 1
}
