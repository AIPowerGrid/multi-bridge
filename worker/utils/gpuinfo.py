import os
import contextlib
import GPUtil

class GPUInfo:
    def __init__(self):
        self.avg_load = []
        self.avg_temp = []
        self.avg_power = []  # Not provided by GPUtil; placeholder for compatibility.
        # Average period in samples, default 10 samples per second, period 5 minutes.
        self.samples_per_second = 10
        # Use the CUDA_VISIBLE_DEVICES environment variable for a forced GPU.
        self.forced_gpu = os.getenv("CUDA_VISIBLE_DEVICES", None) is not None
        self.device = int(os.getenv("CUDA_VISIBLE_DEVICES", 0))
        self.ui_show_n_gpus = int(os.getenv("AIWORKER_UI_SHOW_N_GPUS", 1))

    def get_num_gpus(self):
        """Return the number of GPUs available."""
        if self.forced_gpu:
            return 1
        if self.ui_show_n_gpus:
            return self.ui_show_n_gpus
        try:
            gpus = GPUtil.getGPUs()
            return len(gpus)
        except Exception:
            return 0

    def _get_gpu_data(self, device=0):
        """Return the GPU object for a given device index, if available."""
        try:
            gpus = GPUtil.getGPUs()
            if len(gpus) > device:
                return gpus[device]
        except Exception:
            return None

    def _mem(self, raw):
        """Format raw memory (in MB) to a human-readable string."""
        if raw < 1024:
            return f"{raw} MB"
        else:
            gb = raw / 1024
            return f"{round(gb, 2)} GB"

    def get_total_vram_mb(self):
        """Return the total VRAM in MB for the first GPU (or forced GPU)."""
        gpu = self._get_gpu_data()
        if gpu:
            return gpu.memoryTotal
        return 0

    def get_free_vram_mb(self):
        """Return the free VRAM in MB for the first GPU (or forced GPU)."""
        gpu = self._get_gpu_data()
        if gpu:
            return gpu.memoryFree
        return 0

    def get_info(self, device_id=0):
        """Collect and return a dictionary of GPU statistics."""
        # If we're overriding the device using the CUDA_VISIBLE_DEVICES hack.
        if self.forced_gpu:
            device_id = self.device

        data = self._get_gpu_data(device_id)
        if not data:
            return None

        try:
            # GPUtil returns load as a fraction (e.g., 0.45 means 45%).
            gpu_util = int(data.load * 100)
        except Exception:
            gpu_util = 0

        try:
            gpu_temp = int(data.temperature)
        except Exception:
            gpu_temp = 0

        # GPUtil does not provide power usage. We'll use a placeholder.
        gpu_power = "N/A"

        # Keep averages for load and temperature.
        self.avg_load.append(gpu_util)
        self.avg_temp.append(gpu_temp)
        self.avg_power.append(0)  # Placeholder for power.
        # Limit the history to the last (samples_per_second * 60 * 5) samples.
        self.avg_load = self.avg_load[-(self.samples_per_second * 60 * 5):]
        self.avg_temp = self.avg_temp[-(self.samples_per_second * 60 * 5):]
        self.avg_power = self.avg_power[-(self.samples_per_second * 60 * 5):]

        avg_load = int(sum(self.avg_load) / len(self.avg_load))
        avg_temp = int(sum(self.avg_temp) / len(self.avg_temp))
        avg_power = "N/A"

        info = {
            "product": data.name,
            "vram_total": self._mem(data.memoryTotal),
            "vram_used": self._mem(data.memoryUsed),
            "vram_free": self._mem(data.memoryFree),
            "load": f"{gpu_util}%",
            "temp": f"{gpu_temp}°C",
            "power": f"{gpu_power}",
            "avg_load": f"{avg_load}%",
            "avg_temp": f"{avg_temp}°C",
            "avg_power": f"{avg_power}",
        }
        return info
