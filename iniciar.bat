@echo off
title SeuBot
cd /d "%~dp0"
python bot.py
echo.
echo O bot parou. Pressione uma tecla para fechar.
pause >nul
