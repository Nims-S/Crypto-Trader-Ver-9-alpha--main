@echo off
setlocal EnableExtensions EnableDelayedExpansion

if not exist outputs mkdir outputs
set "LOGFILE=outputs\full_run.log"
set "OVERALL_STATUS=0"

> "%LOGFILE%" echo ===== pytest =====
call :run_section "pytest" python -m pytest tests -v

>> "%LOGFILE%" echo.
>> "%LOGFILE%" echo ===== generation-quota =====
call :run_section "generation-quota" python main.py generation-quota --iterations 5

>> "%LOGFILE%" echo.
>> "%LOGFILE%" echo ===== diversity =====
call :run_section "diversity" python main.py diversity

>> "%LOGFILE%" echo.
>> "%LOGFILE%" echo ===== evolve =====
call :run_section "evolve" python main.py evolve --iterations 20 --folds 4 --mc-iterations 300 --perturbation-trials 60

>> "%LOGFILE%" echo.
>> "%LOGFILE%" echo ===== basket =====
call :run_section "basket" python main.py basket --status deployable

>> "%LOGFILE%" echo.
>> "%LOGFILE%" echo ===== portfolio-probationary =====
call :run_section "portfolio-probationary" python main.py portfolio-probationary

>> "%LOGFILE%" echo.
>> "%LOGFILE%" echo ===== distributed-evolve =====
call :run_section "distributed-evolve" python main.py distributed-evolve --iterations 20 --worker-count 4 --batch-size 6

>> "%LOGFILE%" echo.
>> "%LOGFILE%" echo ===== summary =====
>> "%LOGFILE%" echo overall_status=!OVERALL_STATUS!

echo.
echo Logs written to %LOGFILE%
exit /b !OVERALL_STATUS!

:run_section
set "SECTION=%~1"
shift
>> "%LOGFILE%" echo ----- !SECTION! -----
%* >> "%LOGFILE%" 2>&1
set "RC=!errorlevel!"
>> "%LOGFILE%" echo [exit_code=!RC!]
if not "!RC!"=="0" set "OVERALL_STATUS=1"
exit /b 0
