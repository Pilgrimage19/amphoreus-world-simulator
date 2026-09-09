# 开发环境约定

状态：已确认  
最后更新：2026-09-05

## 本项目专属环境

本项目使用 Conda 环境：

```text
环境名：amphoreus-world-simulator
解释器：D:\miniconda\miniconda3\envs\amphoreus-world-simulator\python.exe
Python：3.12.14
```

## 强制约定

- 所有测试必须通过本项目 Conda 环境运行；
- 任何新增依赖只安装到这个环境；
- 不使用系统 Python、`base` 环境或其他项目环境；
- 新增依赖时，同时更新项目依赖声明与安装说明；
- 同一原则适用于其他项目：每个项目只使用自己的独立环境。

## 常用命令

在项目根目录运行：

```powershell
$env:PYTHONPATH = 'src'
conda run --no-capture-output -n amphoreus-world-simulator python -m unittest discover -s tests -v
```

运行模拟：

```powershell
$env:PYTHONPATH = 'src'
conda run --no-capture-output -n amphoreus-world-simulator python -m amphoreus_sim.cli --seed 42 --ticks 20
```

