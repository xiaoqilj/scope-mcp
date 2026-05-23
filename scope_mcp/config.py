"""scope-mcp 配置管理

优先级：CLI args > 环境变量 > config.yaml > 默认值
"""

import os
import yaml
from dataclasses import dataclass, field, asdict
from typing import Optional

# 默认配置文件路径
DEFAULT_CONFIG_PATHS = [
    "./config.yaml",
    "./config.local.yaml",
    "~/.scope-mcp/config.yaml",
    "/etc/scope-mcp/config.yaml",
]


@dataclass
class ScopeConfig:
    """示波器连接配置"""
    ip: str = ""                         # 示波器 IP 地址（必填）
    visa_timeout_ms: int = 15000         # VISA 超时（毫秒）
    record_length_default: int = 2000000 # 默认记录长度
    cwd: str = ""                        # 示波器上截图保存目录（空=自动检测）


@dataclass
class ServerConfig:
    """HTTP 服务配置"""
    host: str = "0.0.0.0"
    port: int = 8123
    screenshot_dir: str = "./scope_output"  # 截图保存到本地的路径


@dataclass
class AppConfig:
    scope: ScopeConfig = field(default_factory=ScopeConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """加载配置，返回 AppConfig 对象"""
    cfg = AppConfig()

    # 1. 从文件加载
    paths = [config_path] if config_path else DEFAULT_CONFIG_PATHS
    loaded = {}
    for p in paths:
        expanded = os.path.expanduser(p)
        if os.path.exists(expanded):
            with open(expanded) as f:
                loaded = yaml.safe_load(f) or {}
            break

    # 2. 合并到 dataclass
    if loaded:
        sc = loaded.get("scope", {})
        sv = loaded.get("server", {})
        if "ip" in sc:          cfg.scope.ip = sc["ip"]
        if "visa_timeout_ms" in sc: cfg.scope.visa_timeout_ms = sc["visa_timeout_ms"]
        if "record_length_default" in sc: cfg.scope.record_length_default = sc["record_length_default"]
        if "cwd" in sc:         cfg.scope.cwd = sc["cwd"]
        if "host" in sv:        cfg.server.host = sv["host"]
        if "port" in sv:        cfg.server.port = sv["port"]
        if "screenshot_dir" in sv: cfg.server.screenshot_dir = sv["screenshot_dir"]

    # 3. 环境变量覆盖
    if os.environ.get("SCOPE_MCP_IP"):
        cfg.scope.ip = os.environ["SCOPE_MCP_IP"]
    if os.environ.get("SCOPE_MCP_PORT"):
        cfg.server.port = int(os.environ["SCOPE_MCP_PORT"])
    if os.environ.get("SCOPE_MCP_HOST"):
        cfg.server.host = os.environ["SCOPE_MCP_HOST"]
    if os.environ.get("SCOPE_MCP_TIMEOUT"):
        cfg.scope.visa_timeout_ms = int(os.environ["SCOPE_MCP_TIMEOUT"])

    return cfg
