@echo off

REM 设置 Conda 环境名称和 Python 版本
set ENV_NAME=Python311-ARCSearchEngine
set PYTHON_VERSION=3.11

REM 创建 Conda 环境
echo Creating Conda environment %ENV_NAME% with Python %PYTHON_VERSION%...
conda create --name %ENV_NAME% python=%PYTHON_VERSION% -y

REM 激活 Conda 环境
echo Activating Conda environment %ENV_NAME%...
call activate %ENV_NAME%

REM 安装 requirements.txt 中的包
echo Installing packages from requirements.txt...
pip install -r requirements.txt

REM 提示环境创建完成
echo Conda environment %ENV_NAME% created and packages installed successfully!

pause