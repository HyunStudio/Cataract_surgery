param([switch]$Editor, [switch]$Test, [switch]$Game)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$engineVersion = '4.7.2-stable'
$engineDir = Join-Path $repoRoot '.tools/godot'
$engineExe = Join-Path $engineDir "Godot_v$($engineVersion)_win64_console.exe"
if (-not (Test-Path -LiteralPath $engineExe)) {
    New-Item -ItemType Directory -Force -Path $engineDir | Out-Null
    $archivePath = Join-Path $repoRoot '.tools/godot.zip'
    Invoke-WebRequest -Uri "https://github.com/godotengine/godot/releases/download/$engineVersion/Godot_v$($engineVersion)_win64.exe.zip" -OutFile $archivePath
    Expand-Archive -LiteralPath $archivePath -DestinationPath $engineDir -Force
}
$projectDir = Join-Path $repoRoot 'godot'
if ($Test) {
    foreach ($suite in @('test_session', 'test_world', 'test_input', 'test_integration', 'test_playthrough', 'test_capsule_solver', 'test_lens_fluid_solver', 'test_instrument_rig', 'test_simulator', 'test_case_director', 'test_case_recording', 'test_incision_model', 'test_iol_dynamics', 'test_lens_surface', 'test_operating_app', 'test_simulation_ui', 'test_surgical_display', 'test_full_encounter', 'test_lens_material', 'test_layered_lens', 'test_surface_contact', 'test_anatomy_contact', 'test_anatomical_app', 'test_tissue_injury', 'test_injury_flow', 'test_injury_case', 'test_injury_app')) {
        & $engineExe --headless --path $projectDir --script "res://tests/$suite.gd"
        if ($LASTEXITCODE -ne 0) { throw "Godot test failed: $suite" }
    }
} elseif ($Editor) {
    & $engineExe --editor --path $projectDir
} elseif ($Game) {
    & $engineExe --path $projectDir res://main.tscn
} else {
    & $engineExe --path $projectDir
}
