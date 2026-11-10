import psutil
import pynvml
import asyncio
from datetime import datetime


def get_system_metrics():
    metrics = {}
    metrics["cpu_percent"] = psutil.cpu_percent(interval=None)
    metrics["ram_used_mb"] = psutil.virtual_memory().used / (1024 * 1024)

    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        metrics["gpu_vram_used_mb"] = mem_info.used / (1024 * 1024)
        metrics["gpu_util_percent"] = utilization.gpu
        pynvml.nvmlShutdown()
    except pynvml.NVMLError:
        metrics["gpu_vram_used_mb"] = 0
        metrics["gpu_util_percent"] = 0

    metrics["timestamp"] = datetime.now().isoformat()
    return metrics


async def metrics_logger(interval: float, metrics_list: list, stop_event: asyncio.Event):
    while not stop_event.is_set():
        metrics_list.append(get_system_metrics())
        await asyncio.sleep(interval)