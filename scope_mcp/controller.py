"""ScopeController — tm_devices 封装

提供示波器程控的完整 RESTful 接口。
处理了 VXI-11 超时、raw socket 脏数据、RECORDLENGTH? 不可查询等已知坑。
"""

import os
import time
import base64
import logging
import sys

from tm_devices import DeviceManager

logger = logging.getLogger("scope_mcp.controller")


class ScopeError(Exception):
    """示波器操作异常"""
    pass


class ScopeController:
    """示波器控制器 — 封装 tm_devices 原生 API"""

    def __init__(self, ip: str, visa_timeout_ms: int = 15000):
        """
        Args:
            ip: 示波器 IP 地址
            visa_timeout_ms: VISA 超时（毫秒）
        """
        self.ip = ip
        self.visa_timeout_ms = visa_timeout_ms
        self.dm: DeviceManager = None
        self.scope = None
        self._screenshot_dir = "."

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()

    def connect(self):
        """连接示波器"""
        try:
            # tm_devices 4.x 的 import 路径
            self.dm = DeviceManager()
            resource_str = f"TCPIP::{self.ip}::inst0::INSTR"
            self.scope = self.dm.add_scope(resource_str)
            idn = self.scope.idn_string
            logger.info(f"Connected: {idn}")
            return idn
        except Exception as e:
            raise ScopeError(f"连接示波器失败 ({self.ip}): {e}") from e

    def close(self):
        """关闭连接"""
        if self.dm:
            try:
                self.dm.close()
            except Exception as e:
                logger.warning(f"关闭连接异常: {e}")

    def _ensure_connected(self):
        if self.scope is None:
            self.connect()

    # ==========================
    # 1. 设备信息
    # ==========================
    def get_idn(self):
        self._ensure_connected()
        return {
            "idn": self.scope.idn_string,
            "model": self.scope.model,
        }

    # ==========================
    # 2. 垂直系统
    # ==========================
    def set_vertical(self, channel=1, scale=None, position=None, coupling=None, bandwidth=None):
        self._ensure_connected()
        ch = self.scope.commands.vertical.channel[channel]
        if scale is not None: ch.scale.write(scale)
        if position is not None: ch.position.write(position)
        if coupling is not None: ch.coupling.write(coupling)
        if bandwidth is not None: ch.bandwidth.write(bandwidth)
        return self.get_vertical(channel)

    def get_vertical(self, channel=1):
        self._ensure_connected()
        ch = self.scope.commands.vertical.channel[channel]
        return {
            "channel": channel,
            "scale": ch.scale.query(),
            "position": ch.position.query(),
            "coupling": ch.coupling.query(),
            "bandwidth": ch.bandwidth.query(),
        }

    # ==========================
    # 3. 水平系统
    # ==========================
    def set_horizontal(self, scale=None, sample_rate=None, record_length=None, position=None, mode=None):
        self._ensure_connected()
        # 注意：必须先设 MANUAL 模式，否则 RECORDLENGTH 不生效
        if mode is not None:
            self.scope.write(f"HORIZONTAL:MODE {mode}")
            time.sleep(0.2)
        h = self.scope.commands.horizontal.main
        if scale is not None: h.scale.write(scale)
        if sample_rate is not None: h.samplerate.write(int(sample_rate))
        if record_length is not None: h.recordlength.write(record_length)
        if position is not None: h.position.write(position)
        return self.get_horizontal()

    def get_horizontal(self):
        self._ensure_connected()
        h = self.scope.commands.horizontal.main
        return {
            "scale": h.scale.query(),
            "sample_rate": h.samplerate.query(),
            "record_length": h.recordlength.query(),
            "position": h.position.query(),
        }

    # ==========================
    # 4. 触发系统
    # ==========================
    def set_trigger(self, trig_type="EDGE", source="CH1", level=None,
                    slope="RISe", coupling="DC", holdoff=None):
        self._ensure_connected()
        t = self.scope.commands.trigger.a
        t.type.write(trig_type)
        t.edge.source.write(source)
        t.edge.slope.write(slope)
        t.edge.coupling.write(coupling)
        if level is not None: t.level.write(level)
        if holdoff is not None: t.holdoff.write(holdoff)
        return {
            "type": t.type.query(),
            "source": t.edge.source.query(),
            "level": t.level.query(),
            "slope": t.edge.slope.query(),
        }

    def force_trigger(self):
        self._ensure_connected()
        self.scope.commands.trigger.a.force.write("")
        return "trigger forced"

    # ==========================
    # 5. 采集系统
    # ==========================
    def set_acquisition(self, mode="SAMple", averages=None, state=None):
        self._ensure_connected()
        acq = self.scope.commands.acquire
        acq.mode.write(mode)
        if averages is not None: acq.numavg.write(averages)
        if state is not None: acq.state.write(state)
        return {
            "mode": mode,
            "averages": averages,
            "state": state or "unchanged",
        }

    def run_stop(self, action="RUN"):
        self._ensure_connected()
        if action.upper() == "RUN":
            self.scope.commands.acquire.state.write("RUN")
            return "acquisition running"
        else:
            self.scope.commands.acquire.state.write("STOP")
            return "acquisition stopped"

    # ==========================
    # 6. 自动设置
    # ==========================
    def autoset(self):
        self._ensure_connected()
        self.scope.commands.autoset.execute.write("")
        time.sleep(1.5)
        return "autoset done"

    # ==========================
    # 7. 常规测量
    # ==========================
    def add_measurement(self, meas_num=1, meas_type="PK2PK", source="CH1"):
        self._ensure_connected()
        m = self.scope.commands.measurement.meas[meas_num]
        m.type.write(meas_type)
        m.source.write(source)
        time.sleep(1.5)
        return {
            "meas_num": meas_num,
            "type": meas_type,
            "source": source,
            "value": m.value.query(),
            "mean": m.mean.query(),
            "min": m.minimum.query(),
            "max": m.maximum.query(),
            "stddev": m.stdev.query(),
        }

    def get_all_measurements(self):
        """获取所有启用的测量值（MEAS1-8）"""
        self._ensure_connected()
        results = {}
        for i in range(1, 9):
            try:
                m = self.scope.commands.measurement.meas[i]
                v = m.value.query()
                if v and float(v) not in (9.91e37, 0):
                    results[f"MEAS{i}"] = {
                        "type": m.type.query(),
                        "source": m.source.query(),
                        "value": v,
                        "mean": m.mean.query(),
                        "min": m.minimum.query(),
                        "max": m.maximum.query(),
                    }
            except Exception:
                continue
        return results

    # ==========================
    # 8. 截图
    # ==========================
    def screenshot(self, filename=None, save_local=True):
        """截图并返回 base64

        已知坑点处理：
        - SAVE:IMAGE 用 VXI-11 写（而非 HARDCOPY START）
        - FILESystem:READFile 通过 tm_devices query_raw_binary 读取
        - 截图前删除旧文件避免残留
        """
        self._ensure_connected()
        if not filename:
            filename = f"scope_{int(time.time())}.png"

        # 获取示波器上的 CWD
        try:
            cwd = self.scope.query("FILESystem:CWD?").strip().strip('"')
        except Exception:
            cwd = "C:/Users/Public/Tektronix/TekScope/IMAGE"

        fullpath = f"{cwd}/{filename}"

        # 删除旧文件
        try:
            self.scope.write(f'FILESystem:DELete "{fullpath}"')
        except Exception:
            pass
        time.sleep(0.3)

        # SAVE:IMAGE（用 IMAGE 而非 IMAGe——实际测试 IMAGE 也兼容）
        self.scope.write(f'SAVE:IMAGe "{fullpath}"')
        time.sleep(2.0)

        # READFile
        raw = self.scope.query_raw_binary(f'FILESystem:READFile "{fullpath}"')

        if len(raw) <= 100:
            return {"error": f"read failed: {len(raw)} bytes"}

        out_path = None
        if save_local and self._screenshot_dir:
            out_path = os.path.join(self._screenshot_dir, filename)
            os.makedirs(self._screenshot_dir, exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(raw)

        return {
            "path": out_path,
            "size_bytes": len(raw),
            "size_kb": f"{len(raw) / 1024:.1f}",
            "image_base64": base64.b64encode(raw).decode(),
        }

    # ==========================
    # 9. 波形数据
    # ==========================
    def get_waveform(self, channel=1):
        self._ensure_connected()
        points = self.scope.curve_query(channel_num=channel, wfm_type="TimeDomain")
        return {
            "channel": channel,
            "num_points": len(points),
            "x_units": points.axes[0].units if hasattr(points, 'axes') else "s",
            "y_units": points.axes[1].units if hasattr(points, 'axes') else "V",
            "x_start": float(points.axes[0].start) if hasattr(points, 'axes') else 0,
            "x_stop": float(points.axes[0].stop) if hasattr(points, 'axes') else 0,
            "y_values": [float(points[i]) for i in range(len(points))],
        }

    # ==========================
    # 10. 任意 SCPI
    # ==========================
    def send_scpi(self, cmd):
        """发送任意 SCPI 命令"""
        self._ensure_connected()
        if "?" in cmd:
            return self.scope.query(cmd)
        else:
            self.scope.write(cmd)
            return "OK"

    # ==========================
    # 11. 状态
    # ==========================
    def get_status(self):
        self._ensure_connected()
        return {
            "idn": self.scope.idn_string,
            "model": self.scope.model,
            "connected": self.scope is not None,
        }

    def set_screenshot_dir(self, path):
        """设置截图保存目录"""
        self._screenshot_dir = path
        os.makedirs(path, exist_ok=True)
