@echo off
setlocal

set "CONFIG_FILE=plct-ai-data-unifier-config.yaml"
set "MODE=bootstrap"
set "BASE_DIR=repos"
set "OUTPUT_DIR=dataset"
set "JOBS=1"

if not "%~1"=="" set "CONFIG_FILE=%~1"
if not "%~2"=="" set "MODE=%~2"
if not "%~3"=="" set "BASE_DIR=%~3"
if not "%~4"=="" set "OUTPUT_DIR=%~4"
if not "%~5"=="" set "JOBS=%~5"

if not exist "%CONFIG_FILE%" (
  echo Missing config file: %CONFIG_FILE%
  echo Usage: run-au.bat [config-file] [mode] [base-dir] [output-dir] [jobs]
  echo Example: run-au.bat plct-ai-data-unifier-config.yaml bootstrap repos dataset 1
  exit /b 1
)

echo Syncing dependencies with uv...
uv sync
if errorlevel 1 goto :fail

if /i "%MODE%"=="git-sync" (
  echo Running PLCT AI Data Unifier: git-sync...
  uv run plct-ai-data-unifier git-sync --config "%CONFIG_FILE%" --base-dir "%BASE_DIR%"
  if errorlevel 1 goto :fail
) else if /i "%MODE%"=="prepare-dataset" (
  echo Running PLCT AI Data Unifier: prepare-dataset...
  uv run plct-ai-data-unifier prepare-dataset --base-dir "%BASE_DIR%" --output-dir "%OUTPUT_DIR%" --jobs "%JOBS%"
  if errorlevel 1 goto :fail
) else if /i "%MODE%"=="bootstrap" (
  echo Running PLCT AI Data Unifier: bootstrap...
  uv run plct-ai-data-unifier bootstrap --config "%CONFIG_FILE%" --base-dir "%BASE_DIR%" --output-dir "%OUTPUT_DIR%" --jobs "%JOBS%"
  if errorlevel 1 goto :fail
) else (
  echo Unknown mode: %MODE%
  echo Supported modes: bootstrap, git-sync, prepare-dataset
  exit /b 1
)

echo Run completed successfully.
echo Output is preserved in: %BASE_DIR% and %OUTPUT_DIR%
goto :done

:fail
echo Run failed.

:done
endlocal
exit /b %errorlevel%
