# Add a test device
$deviceData = @{
    name = "Test Device"
    mac_address = "00:11:22:33:44:55"
    ip_address = "192.168.1.100"
}

Invoke-RestMethod -Uri "http://127.0.0.1:5000/devices/add" `
                  -Method POST `
                  -Body ($deviceData | ConvertTo-Json) `
                  -ContentType "application/json"

# Fetch devices
$response = Invoke-RestMethod -Uri "http://127.0.0.1:5000/devices" -Method GET
$response | ConvertTo-Json -Depth 10
