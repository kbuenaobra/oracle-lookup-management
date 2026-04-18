@echo off
cd /d "c:\Users\user\Documents\Working Folder\AI\Oracle Lookup Project"
sqlplus -s system/xe@localhost:1521/XEPDB1 @schema.sql
pause
