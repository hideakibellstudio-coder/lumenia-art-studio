# monitor_sessao.ps1 - amostra o consumo do Lumenia durante uma sessao real de pintura.
#
# Fecha o item de portao "teste de sessao longa": memoria e handles NAO devem
# crescer monotonicamente. Crescer e cair e normal (cache, undo, tiles). Crescer
# sempre, sem nunca cair, e vazamento.
#
# Uso para monitoramento ao vivo:
#     powershell -ExecutionPolicy Bypass -File monitor_sessao.ps1
#
# Uso para avaliacao pos-sessao (Gate P4):
#     powershell -ExecutionPolicy Bypass -File monitor_sessao.ps1 -Analisar caminho_do_arquivo.csv

param(
    [string]$Processo = "Lumenia",
    [int]$IntervaloSegundos = 60,
    [string]$Saida = "$env:USERPROFILE\lumenia_sessao.csv",
    [string]$Analisar = ""
)

if ($Analisar -ne "") {
    if (-not (Test-Path $Analisar)) {
        Write-Error "Arquivo CSV para analise nao encontrado: $Analisar"
        exit 1
    }
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host "  ANALISE ESTATISTICA DE SESSAO REAL (GATE P4) - LUMENIA" -ForegroundColor Cyan
    Write-Host "  Arquivo analisado: $Analisar" -ForegroundColor Cyan
    Write-Host "============================================================"

    $dados = Import-Csv $Analisar
    if ($dados.Count -lt 4) {
        Write-Warning "Amostras insuficientes para julgamento confiavel (minimo 4 amostras)."
        exit 1
    }

    $total_min = [double]$dados[-1].minutos
    $warmup_min = [math]::Round($total_min * 0.25, 1)
    $estavel = $dados | Where-Object { [double]$_.minutos -ge $warmup_min }

    if ($estavel.Count -lt 2) { $estavel = $dados }

    $p0 = $estavel[0]
    $pf = $estavel[-1]

    $delta_gdi = [int]$pf.gdi - [int]$p0.gdi
    $delta_hnd = [int]$pf.handles - [int]$p0.handles

    # Regressao linear simples para memoria privada por hora
    $n = $estavel.Count
    $x_vals = $estavel | ForEach-Object { [double]$_.minutos }
    $y_vals = $estavel | ForEach-Object { [double]$_.private_mb }

    $mean_x = ($x_vals | Measure-Object -Average).Average
    $mean_y = ($y_vals | Measure-Object -Average).Average

    $num = 0.0
    $den = 0.0
    for ($i = 0; $i -lt $n; $i++) {
        $num += ($x_vals[$i] - $mean_x) * ($y_vals[$i] - $mean_y)
        $den += [math]::Pow(($x_vals[$i] - $mean_x), 2)
    }
    $slope_min = if ($den -gt 0) { $num / $den } else { 0.0 }
    $drift_hora = [math]::Round($slope_min * 60.0, 3)

    Write-Host ("  Duracao Total Monitorada:  {0} min" -f $total_min)
    Write-Host ("  Aquecimento Descartado:    {0} min" -f $warmup_min)
    Write-Host ("  Amostras no Plato:         {0} pontos" -f $n)
    Write-Host ("  Delta GDI Objects:         {0:+0;-0;+0}  (Tolerancia: 0)" -f $delta_gdi)
    Write-Host ("  Delta OS Handles:          {0:+0;-0;+0}  (Tolerancia: ate 5)" -f $delta_hnd)
    Write-Host ("  Drift de Memoria Privada:  {0:+0.000;-0.000;+0.000} MB/hora  (Teto: ate 5.0 MB/h)" -f $drift_hora)

    $pass_gdi = ($delta_gdi -eq 0)
    $pass_hnd = ([math]::Abs($delta_hnd) -le 5)
    $pass_ram = ($drift_hora -le 5.0)

    Write-Host "------------------------------------------------------------"
    Write-Host ("  [1] GDI Objects sem vazamento:   [{0}]" -f (if ($pass_gdi) { "APROVADO" } else { "REPROVADO" })) -ForegroundColor (if ($pass_gdi) { "Green" } else { "Red" })
    Write-Host ("  [2] Handles de SO estaveis:      [{0}]" -f (if ($pass_hnd) { "APROVADO" } else { "REPROVADO" })) -ForegroundColor (if ($pass_hnd) { "Green" } else { "Red" })
    Write-Host ("  [3] Plato de Memoria Estavel:    [{0}]" -f (if ($pass_ram) { "APROVADO" } else { "REPROVADO" })) -ForegroundColor (if ($pass_ram) { "Green" } else { "Red" })
    Write-Host "------------------------------------------------------------"

    $passou = ($pass_gdi -and $pass_hnd -and $pass_ram)
    $veredicto = if ($passou) { "APROVADO - SESSAO ESTAVEL SEM VAZAMENTOS" } else { "REPROVADO - VAZAMENTO DETECTADO" }
    Write-Host "  VEREDICTO FINAL DO GATE: $veredicto`n" -ForegroundColor (if ($passou) { "Green" } else { "Red" })
    exit (if ($passou) { 0 } else { 1 })
}

if (-not (Test-Path $Saida)) {
    "horario,minutos,working_set_mb,private_mb,handles,threads,gdi" | Set-Content $Saida
}

Write-Host "Monitorando '$Processo' a cada $IntervaloSegundos s."
Write-Host "Gravando em: $Saida"
Write-Host "Ctrl+C para parar.`n"

$inicio = Get-Date
$primeiro = $null

# GDI objects: vazamento classico de app Qt/Windows, invisivel no Gerenciador.
$assinatura = '[DllImport("user32.dll")] public static extern int GetGuiResources(IntPtr h, int f);'
$Api = Add-Type -MemberDefinition $assinatura -Name GuiRes -Namespace W32 -PassThru

while ($true) {
    $p = Get-Process -Name $Processo -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $p) {
        Write-Host "  (processo '$Processo' nao encontrado - confira o nome no Gerenciador de Tarefas)"
    } else {
        $min = [math]::Round(((Get-Date) - $inicio).TotalMinutes, 1)
        $ws  = [math]::Round($p.WorkingSet64 / 1MB, 1)
        $pv  = [math]::Round($p.PrivateMemorySize64 / 1MB, 1)
        $gdi = try { $Api::GetGuiResources($p.Handle, 0) } catch { -1 }

        if ($null -eq $primeiro) { $primeiro = $ws }
        $delta = [math]::Round($ws - $primeiro, 1)
        $sinal = if ($delta -ge 0) { "+" } else { "" }

        "{0},{1},{2},{3},{4},{5},{6}" -f (Get-Date -Format "HH:mm:ss"), $min, $ws, $pv,
            $p.HandleCount, $p.Threads.Count, $gdi | Add-Content $Saida

        Write-Host ("  {0}  {1,6} min   RAM {2,8} MB ({3}{4} MB)   handles {5,6}   GDI {6,6}" -f `
            (Get-Date -Format "HH:mm:ss"), $min, $ws, $sinal, $delta, $p.HandleCount, $gdi)
    }
    Start-Sleep -Seconds $IntervaloSegundos
}
