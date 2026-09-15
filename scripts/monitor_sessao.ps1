# monitor_sessao.ps1 — amostra o consumo do Lumenia durante uma sessao real de pintura.
#
# Fecha o item de portao "teste de sessao longa": memoria e handles NAO devem
# crescer monotonicamente. Crescer e cair e normal (cache, undo, tiles). Crescer
# sempre, sem nunca cair, e vazamento.
#
# Uso (deixe rodando numa janela enquanto pinta):
#     powershell -ExecutionPolicy Bypass -File monitor_sessao.ps1
#
# Ao terminar, feche com Ctrl+C. O CSV fica em %USERPROFILE%\lumenia_sessao.csv

param(
    [string]$Processo = "Lumenia",
    [int]$IntervaloSegundos = 60,
    [string]$Saida = "$env:USERPROFILE\lumenia_sessao.csv"
)

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
        Write-Host "  (processo '$Processo' nao encontrado — confira o nome no Gerenciador de Tarefas)"
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
