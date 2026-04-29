#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vnpy-tx模块的安装脚本
"""

from setuptools import setup, find_packages

setup(
    name="vnpy-tx",
    version="0.1.0",
    author="vnpy开发团队",
    author_email="dev@vnpy.com",
    description="基于腾讯财经API的vn.py行情数据源模块",
    long_description="基于腾讯财经API的vn.py行情数据源模块，使用AKShare库获取A股历史数据",
    long_description_content_type="text/markdown",
    url="https://github.com/vnpy/vnpy-tx",
    packages=find_packages(),
    install_requires=[
        "vnpy>=3.0.0",
        "akshare>=1.0.0",
        "pandas>=1.0.0",
        "numpy>=1.15.0"
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)