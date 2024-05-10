<div align="center">
  <img src="./res/logo.png" alt="ARC Search Engine Logo" width="100"/>
</div>

# ARC Search Engine / 弧光搜索引擎

## Installation and Usage

1. Install MongoDB.

2. Install Redis and update the corresponding directory in the `config.ini` file.

3. Install Anaconda for Python environment setup and management. After installing Anaconda, navigate to the `ARCSearchEngineAlgorithmModule` directory and run `init_python_environment.bat` to automatically create the Python environment required for the project.

4. Install mpm, then navigate to `ARCSearchEngineFrontend` directory and run `init.bat` to compile frontend application.

5. Once everything is installed, run `start.bat` to start the search engine service. The frontend is accessible by default at `http://localhost:8080/`.

6. You can give the search engine the websites you want to set as start website by clicking crawler button in the main page, then input the website list in the type of 'website-url1 max-sub-site-number, website-url2 max number' and press submit button. For example: https://aaa.com 10, https://bbb.com 1000, https://ccc.com, https://ddd.com

## 安装和使用方法

1. 安装 MongoDB。

2. 安装 Redis 并将对应目录写入 `config.ini` 文件中。

3. 安装 Anaconda 用于 Python 环境的搭建与管理。安装好 Anaconda 后，进入 `ARCSearchEngineAlgorithmModule` 目录，执行 `init_python_environment.bat`，就会自动创建项目所需的 Python 环境。

4. 安装 mpm ,安装完毕后进入 `ARCSearchEngineFrontend` 目录，运行 `init.bat` ，就会自动编译前端。

5. 所有组件安装完成后，运行 `start.bat` 即可开启搜索引擎服务。前端默认访问地址为 `http://localhost:8080/`。

6. 你可以在主页下方找到爬虫按钮，点开后的弹出菜单里输入一些网址，就可以让搜索引擎把这些网址当作起始站点，爬取相关链接进入搜索引擎的数据库。形式应当为：'website-url1 max-sub-site-number, website-url2 max number'，例如： https://aaa.com 10, https://bbb.com 1000, https://ccc.com, https://ddd.com

## Developer / 开发者

DEVILENMO
