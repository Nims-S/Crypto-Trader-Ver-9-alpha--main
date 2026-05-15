@echo off
setlocal EnableExtensions EnableDelayedExpansion

if not exist outputs mkdir outputs
set LOGFILE=outputs\full_run.log

echo ===== pytest ===== > "%LOGFILE%"
python -m pytest tests -v >> "%LOGFILE%" 2>&1
if errorlevel 1 goto :done

echo.>> "%LOGFILE%"
echo ===== generation-quota =====>> "%LOGFILE%"
python main.py generation-quota --iterations 5 >> "%LOGFILE%" 2>&1
if errorlevel 1 goto :done

echo.>> "%LOGFILE%"
echo ===== diversity =====>> "%LOGFILE%"
python main.py diversity >> "%LOGFILE%" 2>&1
if errorlevel 1 goto :done

echo.>> "%LOGFILE%"
echo ===== evolve =====>> "%LOGFILE%"
python main.py evolve --iterations 20 --folds 4 --mc-iterations 300 --perturbation-trials 60 >> "%LOGFILE%" 2>&1
if errorlevel 1 goto :done

echo.>> "%LOGFILE%"
echo ===== basket =====>> "%LOGFILE%"
python main.py basket --status deployable >> "%LOGFILE%" 2>&1
if errorlevel 1 goto :done

echo.>> "%LOGFILE%"
echo ===== portfolio-probationary =====>> "%LOGFILE%"
python main.py portfolio-probationary >> "%LOGFILE%" 2>&1
if errorlevel 1 goto :done

echo.>> "%LOGFILE%"
echo ===== distributed-evolve =====>> "%LOGFILE%"
python main.py distributed-evolve --iterations 20 --worker-count 4 --batch-size 6 >> "%LOGFILE%" 2>&1

:done
echo.
echo Logs written to %LOGFILE%
endlocal
