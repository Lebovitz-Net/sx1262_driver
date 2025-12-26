$path = Get-Location
$outputFile = "$path\\filestructure.md"

# Clear or create the output file
Set-Content -Path $outputFile -Value "# Project File Structure`n"

function Write-Tree {
    param (
        [string]$dir,
        [int]$indentLevel,
        [string]$prefix
    )
    $V_BAR  =  "$([char]0x2502)  "
    $T_BAR   = "$([char]0x2502)$([char]0x2014)$([char]0x2014) "
    $UP_BAR  = "$([char]0x2575)$([char]0x2014)$([char]0x2014) "

    $items = Get-ChildItem -LiteralPath $dir | Where-Object { $_.Name -ne "node_modules" }
    $count = $items.Count
    for ($i = 0; $i -lt $count; $i++) {
        $item = $items[$i]
        $isLast = ($i -eq $count - 1)
        $connector = if ($isLast) { $UP_BAR } else { $T_BAR }
        $line = ($V_BAR * $indentLevel) + $connector + $item.Name
        Add-Content -Path $outputFile -Value $line

        if ($item.PSIsContainer) {
            Write-Tree -dir $item.FullName -indentLevel ($indentLevel + 1)
        }
    }
}

Write-Tree -dir $path -indentLevel 0
