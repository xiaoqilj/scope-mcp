# scope-mcp 🔬

**示波器 HTTP REST API 封装层** — 让 AI、脚本、任何工具通过 HTTP 程控示波器。

```
AI / 脚本 ──HTTP──→ scope-mcp ──VISA──→ 示波器
```

## 快速开始

### 安装

```bash
pip install scope-mcp
```

或者从源码安装：

```bash
git clone https://github.com/your-org/scope-mcp.git
cd scope-mcp
pip install -e .
```

### 启动

```bash
# 指定示波器 IP（本地直连）
scope-mcp --scope-ip 192.168.1.100

# 或通过环境变量
SCOPE_MCP_IP=192.168.1.100 scope-mcp

# 或使用配置文件
cp config.example.yaml config.yaml
# 编辑 config.yaml 改 IP
scope-mcp --config config.yaml
```

启动后，打开浏览器访问 http://localhost:8123 可以看到可用工具列表。

### 调用

```bash
# 获取设备信息
curl http://localhost:8123/call -X POST \
  -H "Content-Type: application/json" \
  -d '{"action": "idn"}'

# 截图（返回 base64）
curl http://localhost:8123/call -X POST \
  -H "Content-Type: application/json" \
  -d '{"action": "screenshot"}'

# 直接下载 PNG（浏览器也能打开）
curl -o scope.png http://localhost:8123/screenshot

# 测个参数
curl http://localhost:8123/call -X POST \
  -H "Content-Type: application/json" \
  -d '{"action": "add_measurement", "args": {"meas_num": 1, "meas_type": "FREQUENCY", "source": "CH1"}}'

# 发任意 SCPI 命令
curl http://localhost:8123/call -X POST \
  -H "Content-Type: application/json" \
  -d '{"action": "send_scpi", "args": {"cmd": "HORIZONTAL:MAIN:SCALE 1e-9"}}'

# 获取全部测量值
curl http://localhost:8123/call -X POST \
  -H "Content-Type: application/json" \
  -d '{"action": "get_all_measurements"}'
```

## API 参考

### 可用操作

| 操作 | 说明 |
|------|------|
| `idn` | 获取设备信息（型号、固件版本） |
| `screenshot` | 截图，返回 base64 PNG |
| `send_scpi` | 发送任意 SCPI 命令 |
| `set_vertical` | 设置垂直参数（刻度、位置、耦合、带宽） |
| `get_vertical` | 获取垂直参数 |
| `set_horizontal` | 设置水平参数（时基、采样率、记录长度） |
| `get_horizontal` | 获取水平参数 |
| `set_trigger` | 设置触发条件 |
| `force_trigger` | 强制触发 |
| `set_acquisition` | 设置采集模式 |
| `run_stop` | 运行/停止采集 |
| `autoset` | 自动设置 |
| `add_measurement` | 添加测量项 |
| `get_all_measurements` | 获取全部测量值 |
| `get_waveform` | 获取波形数据 |
| `get_status` | 获取服务+设备状态 |

### REST 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 服务信息、可用工具列表 |
| `POST` | `/call` | RPC 调用（见上方示例） |
| `GET` | `/screenshot` | 直接获取 PNG 图片 |

## 远程访问

### 方案 1：本地网络直连

你的电脑和示波器在同一个局域网即可。适合实验室内部使用。

```bash
scope-mcp --scope-ip 示波器的IP
```

### 方案 2：VPN + MCP（远程办公）

1. 在工作站上启动 scope-mcp
2. 你的电脑通过 VPN 连入内网
3. 直接 `curl http://工作站IP:8123/call` 控制示波器

### 方案 3：树莓派盒子

把 scope-mcp 装在树莓派上，插电即用。树莓派网线连示波器、WiFi 连办公室网络——任何人都能通过 HTTP 控制。

## 配置

支持三种配置方式，按优先级：

1. **CLI 参数** — `scope-mcp --scope-ip 192.168.1.100`
2. **环境变量** — `export SCOPE_MCP_IP=192.168.1.100`
3. **配置文件** — `config.yaml` 或 `~/.scope-mcp/config.yaml`

详见 `config.example.yaml`。

## 开发

```bash
# 克隆 + 安装开发依赖
git clone https://github.com/your-org/scope-mcp.git
cd scope-mcp
pip install -e ".[dev]"

# 配置
cp config.example.yaml config.local.yaml
# 编辑 config.local.yaml 填入你的示波器 IP

# 启动
scope-mcp --config config.local.yaml

# 测试（需要示波器在线）
pytest tests/
```

## 设计理念

不是取代 tm_devices，而是**在其上层提供一层 HTTP 适配器**：

- **AI / 远程调用** → 走 HTTP，不需要装 VISA
- **批量自动化测试** → 走 tm_devices 直连，零延迟
- **两路并存**，按场景切换

底层 tm_devices 处理了 VXI-11 超时、raw socket 脏数据等已知坑点。上层 AI 不需要关心这些。

## 依赖

- Python ≥ 3.10
- [tm_devices](https://github.com/tektronix/tm_devices) — 泰克官方设备控制库
- Flask — HTTP 服务

---

**License:** MIT
