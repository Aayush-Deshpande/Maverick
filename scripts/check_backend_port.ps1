# Pre-flight check run by launch_backend_server.bat before starting uvicorn on port 8000.
#
# Kept as a standalone .ps1 (invoked via `-File`) rather than an inline `powershell -Command
# "..."` one-liner embedded in the .bat file: that one-liner approach was tried first and
# broke in practice. launch_backend_server.bat has `setlocal enabledelayedexpansion` (line 2),
# which makes cmd.exe treat any two `!` characters on the same logical line as delimiters
# around a variable reference - and the warning text below uses "[!]" three times. cmd.exe
# silently deleted everything between the 1st and 2nd "!" (a chunk that happened to include
# balanced parentheses) before PowerShell ever saw the string, so the parser choked on
# "missing closing ')'" - a real repro, not a hypothetical. A separate .ps1 file sidesteps
# cmd.exe's quoting/escaping rules (`!`, `%`, `^`, `&`, `|`, unbalanced parens) entirely.

$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $procId = $conn[0].OwningProcess
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    $procName = if ($proc) { $proc.ProcessName } else { "unknown" }
    Write-Host "[WARNING] Port 8000 is already in use by PID $procId ($procName)."
    Write-Host "[WARNING] This is almost always a backend server left running from an earlier session"
    Write-Host "[WARNING] (e.g. a console window that was closed with the X instead of Ctrl+C)."
    Write-Host "[WARNING] The new server below will fail to start until that process is closed."
    Write-Host "    To stop it: taskkill /PID $procId /F"
    Write-Host ""
}
