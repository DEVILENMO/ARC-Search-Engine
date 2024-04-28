<div align="center">
  <img src="logo.png" alt="ARC Search Engine Logo" width="100"/>
</div>

# ARC Search Engine / 弧光搜索引擎

## Installation and Usage

1. Install MongoDB and load the database.

2. Install Redis and update the corresponding directory in the `config.ini` file.

3. Install Anaconda for Python environment setup and management. After installing Anaconda, navigate to the `ARCSearchEngineAlgorithmModule` directory and run `init_python_environment.bat` to automatically create the Python environment required for the project.

4. Once everything is installed, run `start.bat` to start the search engine service. The frontend is accessible by default at `http://localhost:8080/`.

## 安装和使用方法

1. 安装 MongoDB 并载入数据库。

2. 安装 Redis 并将对应目录写入 `config.ini` 文件中。

3. 安装 Anaconda 用于 Python 环境的搭建与管理。安装好 Anaconda 后,进入 `ARCSearchEngineAlgorithmModule` 目录,执行 `init_python_environment.bat`,就会自动创建项目所需的 Python 环境。

4. 所有组件安装完成后,运行 `start.bat` 即可开启搜索引擎服务。前端默认访问地址为 `http://localhost:8080/`。