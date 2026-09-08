function Test-EvilTwinWindowsHost {
    [CmdletBinding()]
    param()

    return (
        [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
    )
}

function Assert-EvilTwinWindowsHost {
    [CmdletBinding()]
    param(
        [string]$Message = "This command requires Windows."
    )

    if (-not (Test-EvilTwinWindowsHost)) {
        throw $Message
    }
}

function Get-EvilTwinPowerShellRuntime {
    [CmdletBinding()]
    param()

    $Edition = "Desktop"

    if (
        $PSVersionTable.ContainsKey("PSEdition") -and $PSVersionTable.PSEdition
    ) {
        $Edition = [string]$PSVersionTable.PSEdition
    }

    return [PSCustomObject]@{
        Version = [string]$PSVersionTable.PSVersion
        Edition = $Edition
        IsWindows = [bool](Test-EvilTwinWindowsHost)
    }
}
