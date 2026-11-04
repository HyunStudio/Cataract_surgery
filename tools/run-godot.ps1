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
	& $engineExe --headless --path $projectDir --script "res://tests/test_precise_step_transaction.gd"
	if ($LASTEXITCODE -ne 0) { throw "Godot test failed: test_precise_step_transaction" }
	& $engineExe --headless --path $projectDir --script "res://tests/test_ocular_appearance.gd"
	if ($LASTEXITCODE -ne 0) { throw "Godot test failed: test_ocular_appearance" }
	foreach ($suite in @('test_membrane_cut_patch','test_blade_sweep','test_blade_incisions','test_blade_operator','test_blade_actual','test_blade_closed')) {
		& $engineExe --headless --path $projectDir --script "res://tests/$suite.gd"
		if ($LASTEXITCODE -ne 0) { throw "Godot test failed: $suite" }
	}
	& $engineExe --headless --path $projectDir --script "res://tests/test_joint_anatomy.gd"
	if ($LASTEXITCODE -ne 0) { throw "Godot test failed: test_joint_anatomy" }
	& $engineExe --headless --path $projectDir --script "res://tests/test_anatomical_contact.gd"
	if ($LASTEXITCODE -ne 0) { throw "Godot test failed: test_anatomical_contact" }
	& $engineExe --headless --path $projectDir --script "res://tests/test_physical_instrument_path.gd"
	if ($LASTEXITCODE -ne 0) { throw "Godot test failed: test_physical_instrument_path" }
	& $engineExe --headless --path $projectDir --script "res://tests/test_joint_contact_guards.gd"
	if ($LASTEXITCODE -ne 0) { throw "Godot test failed: test_joint_contact_guards" }
	& $engineExe --headless --path $projectDir --script "res://tests/test_joint_grasp_precision.gd"
	if ($LASTEXITCODE -ne 0) { throw "Godot test failed: test_joint_grasp_precision" }
    foreach ($suite in @('test_capsule_incision','test_membrane_cut','test_control_context','test_injury_parts','test_pivot_body_contact','test_rigid_body_app','test_bilateral_entry','test_instrument_path','test_body_app','test_membrane_contact','test_membrane_normal','test_moving_membrane','test_instrument_profile','test_capsule_surface','test_instrument_body_contact','test_tunnel_surface')) {
        & $engineExe --headless --path $projectDir --script "res://tests/$suite.gd"
        if ($LASTEXITCODE -ne 0) { throw "Godot test failed: $suite" }
    }
    foreach ($suite in @('test_session', 'test_world', 'test_input', 'test_integration', 'test_playthrough', 'test_capsule_solver', 'test_lens_fluid_solver', 'test_instrument_rig', 'test_simulator', 'test_case_director', 'test_case_recording', 'test_incision_model', 'test_iol_dynamics', 'test_lens_surface', 'test_operating_app', 'test_simulation_ui', 'test_surgical_display', 'test_full_encounter', 'test_lens_material', 'test_layered_lens', 'test_surface_contact', 'test_anatomy_contact', 'test_anatomical_app', 'test_tissue_injury', 'test_injury_flow', 'test_injury_case', 'test_injury_app', 'test_visual_snapshot', 'test_anterior_segment', 'test_hydro_surface', 'test_corneal_shell_injury', 'test_volumetric_encounter', 'test_volumetric_injury', 'test_flap_boundary', 'test_capsule_extraction', 'test_extraction_case', 'test_tool_exchange', 'test_boundary_cache', 'test_realtime_clock', 'test_presentation_clock')) {
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
