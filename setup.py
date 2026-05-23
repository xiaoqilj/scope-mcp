"""scope-mcp — 示波器 HTTP REST API 封装层"""
from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="scope-mcp",
    version="0.1.0",
    description="示波器 HTTP REST API 封装层 — 让 AI/脚本通过 HTTP 程控示波器",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="TekScope MCP Team",
    url="https://github.com/your-org/scope-mcp",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "tm_devices>=4.0",
        "flask>=3.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "requests>=2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "scope-mcp=scope_mcp.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Electronic Test Equipment",
    ],
)
