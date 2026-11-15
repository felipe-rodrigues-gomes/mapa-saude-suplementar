# Valida a sintaxe do TMDL com a biblioteca que vem no Power BI Desktop (versão Store).
param([string]$Pasta)
$pkg = (Get-AppxPackage -Name Microsoft.MicrosoftPowerBIDesktop).InstallLocation
$bin = Join-Path $pkg "bin"
[AppDomain]::CurrentDomain.add_AssemblyResolve({ param($s, $e)
    $n = (New-Object Reflection.AssemblyName($e.Name)).Name + ".dll"
    $p = Join-Path $bin $n
    if (Test-Path $p) { return [Reflection.Assembly]::LoadFrom($p) } return $null })
$asm = [Reflection.Assembly]::LoadFrom((Join-Path $bin "Microsoft.PowerBI.Tabular.dll"))
$ser = $asm.GetTypes() | Where-Object { $_.Name -eq "TmdlSerializer" } | Select-Object -First 1
if (-not $ser) { Write-Output "TmdlSerializer não encontrado"; exit 1 }
try {
    $db = $ser.GetMethod("DeserializeDatabaseFromFolder", [Type[]]@([string])).Invoke($null, @($Pasta))
    $m = $db.Model
    Write-Output ("OK: {0} tabelas, {1} relações, {2} medidas" -f $m.Tables.Count, $m.Relationships.Count, ($m.Tables | ForEach-Object { $_.Measures.Count } | Measure-Object -Sum).Sum)
} catch {
    Write-Output ("ERRO: " + $_.Exception.InnerException.Message)
    exit 1
}
