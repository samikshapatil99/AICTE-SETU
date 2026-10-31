@echo off
title AICTE-SETU Backend Server
echo Starting AICTE-SETU FastAPI Backend on port 8000...
cd backend
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
