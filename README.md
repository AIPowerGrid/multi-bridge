# SimpleGrid Text Worker

A utility to connect the Grid with ML processing by launching an Aphrodite engine (an OpenAI-compatible model server) in a Docker container and then starting a worker process.

## Features

- **Docker Launch:**  
  Launch the Aphrodite engine automatically via Docker using settings from `bridgeData.yaml`.

- **Old NVIDIA Compute Flag:**  
  If you have an older NVIDIA GPU (for example, a 2080), enable the `old_nvidia_compute` flag so that the engine launches with half-precision (`--dtype half`).

- **Unified Configuration:**  
  All settings are managed via `bridgeData.yaml` so that you can specify the model, URLs, and other options in one place. `bridgeData_template.yaml` is provided as a starting point.

- **Streamlined Logging and UI:**  
  The utility first tails the Docker logs to confirm that the engine has started and that your model is loading. Once you're satisfied (or if you press Enter), it enters a plain mode that persistently shows grid-relevant logs and status details.

## Installation

### Python Dependencies

Ensure you have Python 3 installed. Then run:

```bash
pip install -r requirements.txt
```

### Docker

Docker must be installed and available on your PATH. The Aphrodite engine runs inside Docker.

## Configuration

All settings are managed in the `bridgeData.yaml` file. An example configuration is provided in `bridgeData_template.yaml`.

- **horde_url:**  
  The URL for your Horde endpoint.

- **kai_url:**  
  The URL for interacting with the KoboldAI API via the Aphrodite engine.

- **worker_name:**  
  A descriptive name for your worker instance.

- **old_nvidia_compute:**  
  Set to `true` if you have an older NVIDIA GPU (e.g., a 2080) to enable half-precision via the `--dtype half` flag.

- **model_name:**  
  The model to load, such as `stabilityai/stable-code-3b`.

## Usage

```bash
python start_worker.py
```

The script will:

1. **Check for the Aphrodite engine:**  
   If it isn't running on port 2242, the engine is automatically launched in Docker with the specified model and GPU settings.

2. **Show Docker Logs:**  
   Docker logs are tailed to verify that the engine has started and the model is loading.

3. **User Confirmation:**  
   The process pauses so you can review the logs. Press Enter to immediately proceed to display grid-relevant logs via a persistent plain mode interface.

4. **Launch Worker UI:**  
   Once confirmed, the worker starts, showing ongoing status (such as CPU usage and memory) alongside processing logs in plain mode.

## Managing the Docker Container

When the program starts, it will also start a Docker container as mentioned. However, when you close the program or press `Ctrl+C`, the Docker container will **not** automatically be killed.

The reason for this behavior is to allow quick restarts with the model still loaded in your GPU VRAM, avoiding long reload times.

### Stopping the Docker Container Manually

If you need to stop the running container for any reason, you can use the following commands:

- **View running containers:**
  ```bash
  docker ps
  ```
  This will list all currently running Docker containers, including the Aphrodite engine.

- **Kill the container:**
  ```bash
  docker kill <container_id>
  ```
  Replace `<container_id>` with the actual ID (a hash-like string) of the running container from `docker ps`.

## FAQ

**Q:** *The model takes a while to load and I see errors initially. Is that normal?*  
**A:** Yes. Larger models may take several minutes to initialize. If you see errors at first, wait about five minutes before assuming there's an issue. For testing purposes, consider using the small, known-working model `stabilityai/stable-code-3b`.

**Q:** *I have an NVIDIA 2080 card. What do I need to do?*  
**A:** Set `old_nvidia_compute: true` in your `bridgeData.yaml` to ensure the Docker container is launched with the `--dtype half` flag for half-precision processing.

**Q:** *How are logs handled?*  
**A:** The utility first tails Docker logs so you can verify that the engine has started and the model is loading. Then, after you press Enter, it displays a persistent log view with grid-relevant details and system status.

## Troubleshooting

- **Docker Issues:**  
  Verify Docker is installed and your user has permission to execute Docker commands.

- **Model Loading Delays:**  
  Some models may require five minutes or more to load fully, especially those with higher GPU demands. Patience is advised.

- **Configuration Mismatches:**  
  Double-check your `bridgeData.yaml` to ensure that all URLs and settings match your deployment environment.

