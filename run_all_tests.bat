@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "OUTDIR=%ROOT%outputs"
set "LOGFILE=%OUTDIR%\complete_state.log"
set "OVERALL_STATUS=0"

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

> "%LOGFILE%" (
  echo ===== RUN START =====
  echo Timestamp: %date% %time%
  echo WorkingDir: %CD%
  echo.
)

call :run_step "pytest" "python -m pytest tests -v"
call :run_step "generation-quota" "python main.py generation-quota --iterations 5"
call :run_step "diversity" "python main.py diversity"
call :run_step "evolve" "python main.py evolve --iterations 20 --folds 4 --mc-iterations 300 --perturbation-trials 60"
call :run_step "basket" "python main.py basket --status deployable"
call :run_step "portfolio-probationary" "python main.py portfolio-probationary"
call :run_step "distributed-evolve" "python main.py distributed-evolve --iterations 20 --worker-count 4 --batch-size 6"
call :run_step "protectons" "python main.py protections"
call :run_step "registry-summary" "python main.py registry-summary"
call :run_step "state" "python main.py state"

>> "%LOGFILE%" (
  echo.
  echo ===== RUN END =====
  echo overall_status=!OVERALL_STATUS!
)

echo.
echo Logs written to %LOGFILE%
exit /b !OVERALL_STATUS!

:run_step
set "STEP_NAME=%~1"
set "STEP_CMD=%~2"

>> "%LOGFILE%" (
  echo ----- %STEP_NAME% -----
  echo Command: %STEP_CMD%
)

cmd /c %STEP_CMD% >> "%LOGFILE%" 2>&1
set "STEP_EXIT=!errorlevel!"
if not "!STEP_EXIT!"=="0" set "OVERALL_STATUS=1"

>> "%LOGFILE%" (
  echo [exit_code=!STEP_EXIT!]
  echo.
)
exit /b 0
