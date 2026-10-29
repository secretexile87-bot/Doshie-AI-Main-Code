# doshie_node.ps1 - Native PowerShell Node Agent for Doshie Fleet Management
# Runs on Windows PCs (DuranCyberPwrPC) without requiring Python!
# Listens on port 5055 for authorized remote diagnostics, execution, and code editing.

$Port = 5055
$Listener = New-Object System.Net.HttpListener
$Listener.Prefixes.Add("http://*:$Port/")

try {
    $Listener.Start()
    Write-Host "🚀 Doshie Windows Node Agent running on port $Port..." -ForegroundColor Green
} catch {
    Write-Host "Run as Administrator or reserve port: netsh http add urlacl url=http://*:$Port/ user=Everyone" -ForegroundColor Red
    exit 1
}

while ($Listener.IsListening) {
    $Context = $Listener.GetContext()
    $Request = $Context.Request
    $Response = $Context.Response

    $Url = $Request.Url.AbsolutePath
    $Method = $Request.HttpMethod

    $Body = ""
    if ($Request.HasEntityBody) {
        $Reader = New-Object System.IO.StreamReader($Request.InputStream, $Request.ContentEncoding)
        $Body = $Reader.ReadToEnd()
        $Reader.Close()
    }

    $JsonPayload = $null
    if ($Body) {
        try { $JsonPayload = $Body | ConvertFrom-Json } catch {}
    }

    $StatusCode = 200
    $ResultData = @{}

    if ($Method -eq "GET" -and $Url -eq "/api/health") {
        $os = Get-CimInstance Win32_OperatingSystem
        $cpu = Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average
        $freeRam = [Math]::Round($os.FreePhysicalMemory / 1024 / 1024, 2)
        $totalRam = [Math]::Round($os.TotalVisibleMemorySize / 1024 / 1024, 2)
        $usedRam = [Math]::Round($totalRam - $freeRam, 2)
        $percent = [Math]::Round(($usedRam / $totalRam) * 100, 1)

        $ResultData = @{
            status = "online"
            hostname = $env:COMPUTERNAME
            os = "windows"
            cpu_percent = $cpu.Average
            ram_used_gb = $usedRam
            ram_total_gb = $totalRam
            ram_percent = $percent
        }
    }
    elseif ($Method -eq "POST" -and $Url -eq "/api/exec") {
        $cmd = $JsonPayload.command
        if ($cmd) {
            $procOutput = Invoke-Expression $cmd 2>&1 | Out-String
            $exitCode = if ($LASTEXITCODE -ne $null) { $LASTEXITCODE } else { 0 }
            $ResultData = @{
                ok = ($exitCode -eq 0)
                exit_code = $exitCode
                stdout = $procOutput
                stderr = ""
            }
        } else {
            $StatusCode = 400
            $ResultData = @{ ok = $false; error = "No command provided." }
        }
    }
    elseif ($Method -eq "POST" -and $Url -eq "/api/file/read") {
        $p = $JsonPayload.path
        if (Test-Path $p) {
            $lines = Get-Content $p
            $total = $lines.Count
            $start = [Math]::Max(1, [int]$JsonPayload.start_line) - 1
            $count = if ($JsonPayload.line_count) { [int]$JsonPayload.line_count } else { 150 }
            $idx = $start + 1
            $contentList = @()
            $lines | Select-Object -Skip $start -First $count | ForEach-Object {
                $contentList += "$idx`: $_"
                $idx++
            }
            $ResultData = @{
                ok = $true
                path = $p
                total_lines = $total
                content = ($contentList -join "`n")
            }
        } else {
            $StatusCode = 404
            $ResultData = @{ ok = $false; error = "File not found: $p" }
        }
    }
    elseif ($Method -eq "POST" -and $Url -eq "/api/file/write") {
        $p = $JsonPayload.path
        $content = $JsonPayload.content
        try {
            $dir = [System.IO.Path]::GetDirectoryName($p)
            if ($dir -and !(Test-Path $dir)) { [System.IO.Directory]::CreateDirectory($dir) | Out-Null }
            [System.IO.File]::WriteAllText($p, $content, [System.Text.Encoding]::UTF8)
            $ResultData = @{ ok = $true; path = $p; bytes_written = $content.Length }
        } catch {
            $StatusCode = 500
            $ResultData = @{ ok = $false; error = $_.Exception.Message }
        }
    }
    elseif ($Method -eq "POST" -and $Url -eq "/api/file/replace") {
        $p = $JsonPayload.path
        $target = $JsonPayload.target_content
        $repl = $JsonPayload.replacement_content
        if (Test-Path $p) {
            $content = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8)
            $idx = $content.IndexOf($target)
            if ($idx -lt 0) {
                $StatusCode = 400
                $ResultData = @{ ok = $false; error = "Target content not found in file." }
            } else {
                $lastIdx = $content.LastIndexOf($target)
                if ($idx -ne $lastIdx) {
                    $StatusCode = 400
                    $ResultData = @{ ok = $false; error = "Target content occurs multiple times. Provide unique chunk." }
                } else {
                    $newContent = $content.Remove($idx, $target.Length).Insert($idx, $repl)
                    [System.IO.File]::WriteAllText($p, $newContent, [System.Text.Encoding]::UTF8)
                    $ResultData = @{ ok = $true; path = $p; message = "Replaced target content successfully." }
                }
            }
        } else {
            $StatusCode = 404
            $ResultData = @{ ok = $false; error = "File not found: $p" }
        }
    }
    else {
        $StatusCode = 404
        $ResultData = @{ error = "Not found" }
    }

    $Response.StatusCode = $StatusCode
    $Response.ContentType = "application/json"
    $ResponseBytes = [System.Text.Encoding]::UTF8.GetBytes(($ResultData | ConvertTo-Json -Depth 5))
    $Response.ContentLength64 = $ResponseBytes.Length
    $Response.OutputStream.Write($ResponseBytes, 0, $ResponseBytes.Length)
    $Response.OutputStream.Close()
}
