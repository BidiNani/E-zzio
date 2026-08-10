param()

$ErrorActionPreference="Stop"

$Root="G:\AI\E-zzio"

$Runtime="$Root\runtime"

$Log="$Runtime\supervisor\watchdog.log"


function Write-Log {

    param(
        [string]$Message
    )

    "$(Get-Date -Format o) | $Message" |
    Add-Content $Log

}



function Repair-Lock {


    $Lock="$Runtime\ezzio.lock"


    if(Test-Path $Lock){


        try{

            $data=Get-Content `
            $Lock `
            -Raw |
            ConvertFrom-Json


            if($data.pid){

                if(Get-Process `
                    -Id $data.pid `
                    -ErrorAction SilentlyContinue){

                    Write-Log "LOCK OK PID $($data.pid)"
                    return

                }

            }


        }
        catch{

            Write-Log "LOCK CORRUPT"

        }


        Remove-Item `
        $Lock `
        -Force `
        -ErrorAction SilentlyContinue


        Write-Log "LOCK RESET"

    }


}



function Test-API {


    try{

        $health=Invoke-RestMethod `
        "http://127.0.0.1:8001/health" `
        -TimeoutSec 5


        if($health.status -eq "ONLINE"){

            Write-Log "API ONLINE"
            return $true

        }

    }
    catch{

        Write-Log "API DOWN"

    }


    return $false

}




Write-Log "SUPERVISOR START"


Repair-Lock


if(Test-API){

    Write-Log "SYSTEM HEALTHY"

}
else{

    Write-Log "RECOVERY REQUIRED"

}



Write-Log "SUPERVISOR END"

