$pgHbaPath = "C:\Program Files\PostgreSQL\18\data\pg_hba.conf"
$serviceName = "postgresql-x64-18"
$psqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe"

# Backup pg_hba.conf
Copy-Item $pgHbaPath "$pgHbaPath.bak" -Force

# Replace scram-sha-256 with trust
(Get-Content $pgHbaPath) -replace 'scram-sha-256', 'trust' | Set-Content $pgHbaPath

# Restart PostgreSQL service
Restart-Service -Name $serviceName -Force
Start-Sleep -Seconds 5

# Reset password to 'postgres'
& $psqlPath -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"
& $psqlPath -U postgres -c "CREATE DATABASE skinsync;"

# Restore pg_hba.conf
Copy-Item "$pgHbaPath.bak" $pgHbaPath -Force

# Restart PostgreSQL service again
Restart-Service -Name $serviceName -Force
Start-Sleep -Seconds 5

Write-Output "Password reset to 'postgres' and skinsync database created."
