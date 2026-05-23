"""scope-mcp HTTP Server — Flask 实现

提供 RESTful API，将示波器操作封装为 HTTP 端点。
"""

import json
import logging
import sys

try:
    from flask import Flask, jsonify, request, Response, send_file
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

from scope_mcp.controller import ScopeController, ScopeError
from scope_mcp import __version__

logger = logging.getLogger("scope_mcp.server")


def create_app(controller: ScopeController) -> "Flask":
    """创建 Flask 应用"""
    if not HAS_FLASK:
        raise ImportError("需要 Flask: pip install flask")

    app = Flask(__name__)

    # ==========================
    # 根路径 — 服务信息
    # ==========================
    @app.route("/")
    def index():
        return jsonify({
            "server": "scope-mcp",
            "version": __version__,
            "status": "running",
            "tools": [
                "idn",
                "set_vertical", "get_vertical",
                "set_horizontal", "get_horizontal",
                "set_trigger", "force_trigger",
                "set_acquisition", "run_stop",
                "autoset",
                "add_measurement", "get_all_measurements",
                "screenshot",
                "get_waveform",
                "send_scpi",
                "status",
            ],
        })

    # ==========================
    # REST API
    # ==========================
    @app.route("/call", methods=["POST"])
    def call():
        """通用 RPC 调用

        请求体: {"action": "...", "args": {...}}
        """
        data = request.get_json(silent=True)
        if not data or "action" not in data:
            return jsonify({"error": "需要 action 字段"}), 400

        action = data["action"]
        args = data.get("args", {})

        try:
            result = _route(controller, action, args)
            return jsonify({"result": result})
        except ScopeError as e:
            return jsonify({"error": str(e)}), 500
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.exception(f"Action {action} 执行失败")
            return jsonify({"error": f"{type(e).__name__}: {e}"}), 500

    @app.route("/screenshot", methods=["GET"])
    def get_screenshot():
        """GET /screenshot — 直接返回 PNG 图片"""
        try:
            result = controller.screenshot(save_local=True)
            if "image_base64" in result:
                import base64
                img = base64.b64decode(result["image_base64"])
                return Response(img, mimetype="image/png")
            else:
                return jsonify(result), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


def _route(controller: ScopeController, action: str, args: dict):
    """路由分发"""
    c = controller

    route_map = {
        "idn": lambda: c.get_idn(),
        "status": lambda: c.get_status(),
        "set_vertical": lambda: c.set_vertical(**args),
        "get_vertical": lambda: c.get_vertical(args.get("channel", 1)),
        "set_horizontal": lambda: c.set_horizontal(**args),
        "get_horizontal": lambda: c.get_horizontal(),
        "set_trigger": lambda: c.set_trigger(**args),
        "force_trigger": lambda: c.force_trigger(),
        "set_acquisition": lambda: c.set_acquisition(**args),
        "run_stop": lambda: c.run_stop(args.get("action", "RUN")),
        "autoset": lambda: c.autoset(),
        "add_measurement": lambda: c.add_measurement(**args),
        "get_all_measurements": lambda: c.get_all_measurements(),
        "screenshot": lambda: c.screenshot(args.get("filename")),
        "get_waveform": lambda: c.get_waveform(args.get("channel", 1)),
        "send_scpi": lambda: c.send_scpi(args.get("cmd", "*IDN?")),
    }

    fn = route_map.get(action)
    if fn is None:
        raise ValueError(f"未知操作: {action}。可用: {', '.join(route_map.keys())}")
    return fn()


def run_server(scope_ip: str, host: str = "0.0.0.0", port: int = 8123,
               visa_timeout_ms: int = 15000, screenshot_dir: str = "./scope_output"):
    """启动 MCP Server

    Args:
        scope_ip: 示波器 IP
        host: HTTP 监听地址
        port: HTTP 端口
        visa_timeout_ms: VISA 超时
        screenshot_dir: 截图本地保存路径
    """
    logging.basicConfig(
        level=logging.INFO,
        format="[MCP] %(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info(f"连接示波器 {scope_ip}...")
    controller = ScopeController(scope_ip, visa_timeout_ms=visa_timeout_ms)
    controller.connect()
    controller.set_screenshot_dir(screenshot_dir)

    app = create_app(controller)

    logger.info(f"服务启动: http://{host}:{port}")
    logger.info(f"示波器: {controller.scope.idn_string}")

    try:
        app.run(host=host, port=port, debug=False)
    except KeyboardInterrupt:
        logger.info("正在关闭...")
        controller.close()
