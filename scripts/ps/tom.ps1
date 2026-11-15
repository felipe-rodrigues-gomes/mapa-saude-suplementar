# Conecta no modelo aberto no Power BI Desktop (versão Store) via TOM/ADOMD.
# -Acao refresh : atualiza todas as tabelas (Full) e salva
# -Acao dax     : roda a consulta DAX do arquivo -Arquivo e imprime o resultado
param([string]$Acao = "info", [string]$Arquivo = "")
$pkg = (Get-AppxPackage -Name Microsoft.MicrosoftPowerBIDesktop).InstallLocation
$bin = Join-Path $pkg "bin"
[AppDomain]::CurrentDomain.add_AssemblyResolve({ param($s, $e)
    $n = (New-Object Reflection.AssemblyName($e.Name)).Name + ".dll"
    $p = Join-Path $bin $n
    if (Test-Path $p) { return [Reflection.Assembly]::LoadFrom($p) } return $null })
[void][Reflection.Assembly]::LoadFrom((Join-Path $bin "Microsoft.AnalysisServices.Server.Core.dll"))
[void][Reflection.Assembly]::LoadFrom((Join-Path $bin "Microsoft.AnalysisServices.Server.Tabular.dll"))
[void][Reflection.Assembly]::LoadFrom((Join-Path $bin "Microsoft.PowerBI.AdomdClient.dll"))
$proc = Get-Process msmdsrv | Sort-Object StartTime -Descending | Select-Object -First 1
$porta = (Get-NetTCPConnection -State Listen -OwningProcess $proc.Id | Select-Object -First 1).LocalPort
$cs = "Data Source=localhost:$porta"
if ($Acao -eq "dax") {
    $c = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection($cs); $c.Open()
    $cmd = $c.CreateCommand(); $cmd.CommandText = [IO.File]::ReadAllText($Arquivo, [Text.Encoding]::UTF8)
    $r = $cmd.ExecuteReader()
    $cols = 0..($r.FieldCount - 1) | ForEach-Object { $r.GetName($_) }
    Write-Output ($cols -join " | ")
    while ($r.Read()) { Write-Output ((0..($r.FieldCount - 1) | ForEach-Object { $r.GetValue($_) }) -join " | ") }
    $c.Close(); exit 0
}
$srv = New-Object Microsoft.AnalysisServices.Tabular.Server; $srv.Connect($cs)
$db = $srv.Databases[0]; $m = $db.Model
if ($Acao -eq "refresh") {
    $m.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
    $m.SaveChanges() | Out-Null
}
foreach ($t in $m.Tables) {
    $p = $t.Partitions[0]
    Write-Output ("{0,-14} estado={1}  {2}" -f $t.Name, $p.State, $p.ErrorMessage)
}
$srv.Disconnect()
