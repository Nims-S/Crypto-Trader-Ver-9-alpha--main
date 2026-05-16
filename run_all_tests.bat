@echo off
setlocal EnableExtensions EnableDelayedExpansion

if not exist outputs mkdir outputs
set "LOGFILE=outputs\full_run.log"
set "OVERALL_STATUS=0"

> "%LOGFILE%" echo ===== RUN START =====
>> "%LOGFILE%" echo Timestamp: %date% %time%
>> "%LOGFILE%" echo WorkingDir: %CD%
>> "%LOGFILE%" echo.

>> "%LOGFILE%" echo ----- pytest -----
>> "%LOGFILE%" echo Command: python -m pytest tests -v
python -m pytest tests -v >> "%LOGFILE%" 2>&1
if errorlevel 1 set "OVERALL_STATUS=1"
>> "%LOGFILE%" echo [exit_code=!errorlevel!]
>> "%LOGFILE%" echo.

>> "%LOGFILE%" echo ----- generation-quota -----
>> "%LOGFILE%" echo Command: python main.py generation-quota --iterations 5
python main.py generation-quota --iterations 5 >> "%LOGFILE%" 2>&1
if errorlevel 1 set "OVERALL_STATUS=1"
>> "%LOGFILE%" echo [exit_code=!errorlevel!]
>> "%LOGFILE%" echo.

>> "%LOGFILE%" echo ----- diversity -----
>> "%LOGFILE%" echo Command: python main.py diversity
python main.py diversity >> "%LOGFILE%" 2>&1
if errorlevel 1 set "OVERALL_STATUS=1"
>> "%LOGFILE%" echo [exit_code=!errorlevel!]
>> "%LOGFILE%" echo.

>> "%LOGFILE%" echo ----- evolve -----
>> "%LOGFILE%" echo Command: python main.py evolve --iterations 20 --folds 4 --mc-iterations 300 --perturbation-trials 60
python main.py evolve --iterations 20 --folds 4 --mc-iterations 300 --perturbation-trials 60 >> "%LOGFILE%" 2>&1
if errorlevel 1 set "OVERALL_STATUS=1"
>> "%LOGFILE%" echo [exit_code=!errorlevel!]
>> "%LOGFILE%" echo.

>> "%LOGFILE%" echo ----- basket -----
>> "%LOGFILE%" echo Command: python main.py basket --status deployable
python main.py basket --status deployable >> "%LOGFILE%" 2>&1
if errorlevel 1 set "OVERALL_STATUS=1"
>> "%LOGFILE%" echo [exit_code=!errorlevel!]
>> "%LOGFILE%" echo.

>> "%LOGFILE%" echo ----- portfolio-probationary -----
>> "%LOGFILE%" echo Command: python main.py portfolio-probationary
python main.py portfolio-probationary >> "%LOGFILE%" 2>&1
if errorlevel 1 set "OVERALL_STATUS=1"
>> "%LOGFILE%" echo [exit_code=!errorlevel!]
>> "%LOGFILE%" echo.

>> "%LOGFILE%" echo ----- distributed-evolve -----
>> "%LOGFILE%" echo Command: python main.py distributed-evolve --iterations 20 --worker-count 4 --batch-size 6
python main.py distributed-evolve --iterations 20 --worker-count 4 --batch-size 6 >> "%LOGFILE%" 2>&1
if errorlevel 1 set "OVERALL_STATUS=1"
>> "%LOGFILE%" echo [exit_code=!errorlevel!]
>> "%LOGFILE%" echo.

>> "%LOGFILE%" echo ===== RUN END =====
>> "%LOGFILE%" echo overall_status=!OVERALL_STATUS!

echo.
echo Logs written to %LOGFILE%
exit /b !OVERALL_STATUS!
