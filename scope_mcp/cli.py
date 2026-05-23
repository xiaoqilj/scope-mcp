"""scope-mcp CLI 入口

Usage:
    scope-mcp --scope-ip <IP> [--port 8123] [--host 0.0.0.0]
    scope-mcp --config config.yaml
    SCOPE_MCP_IP=192.168.1.100 scope-mcp
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="scope-mcp: 示波器 HTTP REST API 封装层",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  scope-mcp --scope-ip 134.64.228.125
  scope-mcp --scope-ip 192.168.1.100 --port 9123
  scope-mcp --config ./config.local.yaml
  SCOPE_MCP_IP=192.168.1.100 scope-mcp
        """,
    )

    # 连接参数
    parser.add_argument("--scope-ip", help="示波器 IP 地址（必填，也可通过环境变量 SCOPE_MCP_IP 设置）")
    parser.add_argument("--visa-timeout", type=int, default=15000, help="VISA 超时（毫秒，默认 15000）")

    # 服务参数
    parser.add_argument("--host", default="0.0.0.0", help="HTTP 服务监听地址（默认 0.0.0.0）")
    parser.add_argument("--port", type=int, default=8123, help="HTTP 服务端口（默认 8123）")

    # 配置
    parser.add_argument("--config", help="配置文件路径（YAML），优先级最高")
    parser.add_argument("--screenshot-dir", default="./scope_output", help="截图保存目录（默认 ./scope_output）")

    # 其他
    parser.add_argument("--version", action="store_true", help="显示版本号")

    args = parser.parse_args()

    if args.version:
        from scope_mcp import __version__
        print(f"scope-mcp v{__version__}")
        return

    # 确定 scope IP（CLI > 环境变量 > 配置文件中）
    scope_ip = (args.scope_ip
                or os.environ.get("SCOPE_MCP_IP")
                or os.environ.get("SCOPE_MCP_SCOPE_IP")
                or "")

    # 支持 --config 加载
    config_path = args.config

    if config_path:
        # 从配置文件加载
        from scope_mcp.config import load_config
        cfg = load_config(config_path)
        if not scope_ip:
            scope_ip = cfg.scope.ip
        if not args.host or args.host == "0.0.0.0":
            args.host = cfg.server.host
        if args.port == 8123:
            args.port = cfg.server.port
        if not scope_ip:
            scope_ip = cfg.scope.ip
    else:
        # 没有 config 文件，也可以用环境变量
        pass

    if not scope_ip:
        parser.print_help()
        print("\n❌ 错误: 未指定示波器 IP。请通过 --scope-ip 或 SCOPE_MCP_IP 环境变量设置。")
        sys.exit(1)

    # 启动服务器
    from scope_mcp.server import run_server

    run_server(
        scope_ip=scope_ip,
        host=args.host,
        port=args.port,
        visa_timeout_ms=args.visa_timeout,
        screenshot_dir=args.screenshot_dir,
    )


if __name__ == "__main__":
    main()
