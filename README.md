# SimpleGrid Text Worker

A utility to connect the Grid with ML processing, supporting both KoboldAI (via Aphrodite engine) and OpenAI-compatible APIs.

## Features

- **Dual API Support:**  
  Connect either through KoboldAI (using Aphrodite engine in Docker) or directly to OpenAI API.

- **Docker Launch (KoboldAI mode):**  
  Launch the Aphrodite engine automatically via Docker using settings from `bridgeData.yaml`.

- **Old NVIDIA Compute Flag (KoboldAI mode):**  
  If you have an older NVIDIA GPU (for example, a 2080), enable the `old_nvidia_compute` flag so that the engine launches with half-precision (`--dtype half`).

- **Direct OpenAI Connection:**  
  Connect directly to OpenAI's API to use their models like GPT-3.5 and GPT-4.

- **Unified Configuration:**  
  All settings are managed via `bridgeData.yaml` so that you can specify the API type, model, URLs, and other options in one place. `bridgeData_template.yaml` is provided as a starting point.

- **Streamlined Logging and UI:**  
  The utility provides logs and status details appropriate to the chosen API type.

## Installation

### Python Dependencies

Ensure you have Python 3 installed. Then run:

```bash
pip install -r requirements.txt
```

### Docker (For KoboldAI mode)

Docker must be installed and available on your PATH if you're using KoboldAI mode. The Aphrodite engine runs inside Docker.

## Configuration

All settings are managed in the `bridgeData.yaml` file. An example configuration is provided in `bridgeData_template.yaml`.

### Common Settings

- **api_type:**  
  Choose between "koboldai" or "openai" to determine which API to use.

- **model_name:**  
  For KoboldAI, the model to load in the Aphrodite engine. For OpenAI, used as a display name in the horde.

- **worker_name:**  
  A descriptive name for your worker instance.

- **horde_url:**  
  The URL for your Horde endpoint.

- **api_key:**  
  Your AIPG API key.

- **max_length:**  
  The maximum number of tokens to generate.

- **max_context_length:**  
  The maximum number of tokens to use from the prompt.

### KoboldAI-specific Settings

- **kai_url:**  
  The URL for interacting with the KoboldAI API via the Aphrodite engine.

- **gpu_count:**  
  The number of GPUs to use. Defaults to 1. Adjust this based on your hardware capabilities.

- **download_dir:**  
  The directory to download models to. Defaults to the "models" folder.

- **old_nvidia_compute:**  
  Set to `true` if you have an older NVIDIA GPU to enable half-precision.

### OpenAI-specific Settings

- **openai_api_key:**  
  Your OpenAI API key (starts with "sk-").

- **openai_url:**  
  The OpenAI API URL (defaults to https://api.openai.com/v1).

- **openai_model:**  
  The OpenAI model to use (e.g., "gpt-3.5-turbo").

## Usage

```bash
python start_worker.py
```

The script will:

1. **Check the API type:**  
   Determine whether to use KoboldAI or OpenAI based on the `api_type` setting.

2. For KoboldAI:
   - **Check for the Aphrodite engine:**  
     If it isn't running on port 2242, the engine is automatically launched in Docker.
   - **Show Docker Logs:**  
     Docker logs are tailed to verify that the engine has started.
   - **User Confirmation:**  
     The process pauses so you can review the logs.

3. For OpenAI:
   - **Validate API Connection:**  
     Check that the OpenAI API key and endpoint are working correctly.

4. **Launch Worker:**  
   Start the worker with the configured API, showing ongoing status and processing logs.

## Managing the Docker Container (KoboldAI mode)

When using KoboldAI mode, the program starts a Docker container. When you close the program, the Docker container will **not** automatically be killed, allowing for quick restarts.

### Stopping the Docker Container Manually

If you need to stop the running container for any reason, you can use the following commands:

- **View running containers:**
  ```bash
  docker ps
  ```

- **Kill the container:**
  ```bash
  docker kill <container_id>
  ```

## FAQ

**Q:** *Should I use KoboldAI or OpenAI mode?*  
**A:** Use KoboldAI if you want to run models locally on your own hardware. Use OpenAI if you want to connect to OpenAI's hosted models.

**Q:** *I have an NVIDIA 2080 card. What do I need to do?*  
**A:** When using KoboldAI mode, set `old_nvidia_compute: true` in your `bridgeData.yaml`.

**Q:** *How do I get an OpenAI API key?*  
**A:** Sign up at https://platform.openai.com/ and create an API key in your account settings.

## Troubleshooting

- **Docker Issues (KoboldAI mode):**  
  Verify Docker is installed and your user has permission to execute Docker commands.

- **OpenAI Authentication:**  
  If you see 401 Unauthorized errors, check that your OpenAI API key is correctly entered and valid.

- **OpenAI Rate Limits:**  
  If you encounter rate limit errors, your account may have reached its quota. Check your OpenAI dashboard.

