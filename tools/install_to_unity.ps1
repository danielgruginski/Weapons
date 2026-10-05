<#
Copies the weapon kit into a Unity project, under Assets/Weapons:
  unity/Weapons/Runtime, Editor    -> Assets/Weapons/Scripts/Runtime, Editor
  export/Models/Wpn_*.fbx          -> Assets/Weapons/Models
  export/weapons.json              -> Assets/Weapons/Models
  export/Textures/T_Weapons*.png   -> Assets/Weapons/Textures
Files are overwritten in place; their .meta files (import settings, prefab references) are kept.
Afterwards, in Unity: Tools > Weapons > Rebuild Prefabs and Showcase.

Usage:
  powershell -ExecutionPolicy Bypass -File tools\install_to_unity.ps1 -Project E:\Unity\Projects\MedievalSetting
  add -ScriptsOnly to copy only the C# scripts
#>
param(
    [Parameter(Mandatory = $true)][string]$Project,
    [switch]$ScriptsOnly
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$Project = (Resolve-Path $Project).Path
$assets = Join-Path $Project 'Assets'
if (-not (Test-Path $assets)) { throw "No Assets folder in $Project - is it a Unity project?" }
$dst = Join-Path $assets 'Weapons'

function Copy-Into([string]$from, [string]$filter, [string]$to) {
    New-Item -ItemType Directory -Force -Path $to | Out-Null
    $files = @(Get-ChildItem -Path $from -Filter $filter -File)
    foreach ($f in $files) { Copy-Item -LiteralPath $f.FullName -Destination $to -Force }
    Write-Host ("{0,3} x {1,-16} -> {2}" -f $files.Count, $filter, $to.Substring($Project.Length + 1))
}

Copy-Into (Join-Path $root 'unity\Weapons\Runtime') '*.cs' (Join-Path $dst 'Scripts\Runtime')
Copy-Into (Join-Path $root 'unity\Weapons\Editor') '*.cs' (Join-Path $dst 'Scripts\Editor')
if (-not $ScriptsOnly) {
    Copy-Into (Join-Path $root 'export\Models') 'Wpn_*.fbx' (Join-Path $dst 'Models')
    Copy-Into (Join-Path $root 'export') 'weapons.json' (Join-Path $dst 'Models')
    Copy-Into (Join-Path $root 'export\Textures') 'T_Weapons*.png' (Join-Path $dst 'Textures')
}
Write-Host 'Done. In Unity: Tools > Weapons > Rebuild Prefabs and Showcase'
