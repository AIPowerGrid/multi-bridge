#!/usr/bin/env python3
"""
This is the bridge, which connects the horde with the ML processing.

This version supports both KoboldAI and OpenAI-compatible endpoints.
For KoboldAI: Checks if the aphrodite engine is running on port 2242 and launches it if needed
For OpenAI: Connects directly to the OpenAI API using the provided credentials
"""
# isort: off
import threading
import time
import socket
import subprocess
import sys
import shutil
import yaml
import os

from worker.argparser.scribe import args
from worker.utils.set_envs import set_worker_env_vars_from_config
set_worker_env_vars_from_config()  # Get necessary environment variables

from worker.bridge_data.scribe import KoboldAIBridgeData  # noqa: E402
from worker.logger import logger, quiesce_logger, set_logger_verbosity  # noqa: E402
from worker.workers.scribe import ScribeWorker  # noqa: E402
# isort: on

def is_engine_running(host='localhost', port=2242, timeout=5):
    """
    Check if the aphrodite engine is running by attempting to connect to the given host and port.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def tail_docker_logs(container_id):
    """Tail the logs of a docker container and print them to stdout."""
    try:
        log_proc = subprocess.Popen(
            ["docker", "logs", "-f", container_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        for line in log_proc.stdout:
            print("[DOCKER LOG]", line.rstrip())
    except Exception as e:
        print("Error tailing docker logs:", e)

def start_aphrodite_engine(model_name, gpu_count=1, old_nvidia_compute=False, download_dir="./models"):
    """
    Launch the aphrodite engine as a Docker container with the specified model.
    
    Args:
        model_name (str): The model to load.
        gpu_count (int): Number of GPUs to allocate to the container.
        old_nvidia_compute (bool): Whether to use old NVIDIA compute settings.
        download_dir (str): Directory to download models to and mount into Docker.
    """
    if shutil.which("docker") is None:
        print("Error: The 'docker' command is not found in your PATH. Please install Docker.")
        sys.exit(1)
    
    # Ensure the download directory exists
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    # Set the --gpus parameter based on gpu_count
    gpus_param = f"count={gpu_count}" if gpu_count > 0 else "all"
    
    # Build the Docker command with dynamic tensor-parallel-size
    command = [
        "docker", "run", "--rm", "-d",
        "--gpus", gpus_param,
        "-p", "2242:2242",
        "--ipc=host",
        "-v", f"{download_dir}:/app/models",
        "alpindale/aphrodite-openai:latest",
        "--model", model_name,
        "--tensor-parallel-size", str(gpu_count),
        "--download-dir", "/app/models",
    ]
    
    if old_nvidia_compute:
        command.append("--dtype")
        command.append("half")
    
    command.append("--launch-kobold-api")
    
    print("Starting aphrodite engine with command:", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print("Failed to launch docker container for aphrodite engine:")
        print(result.stderr)
        sys.exit(1)
    
    container_id = result.stdout.strip()
    print("Started aphrodite docker container with ID:", container_id)
    
    # Start a background thread to tail the container's logs.
    log_thread = threading.Thread(target=tail_docker_logs, args=(container_id,), daemon=True)
    log_thread.start()
    
    # Wait until the engine is up and listening on port 2242.
    retries = 0
    while retries < 10:
        if is_engine_running():
            print("Aphrodite engine is up and running.")
            return container_id
        time.sleep(2)
        retries += 1
        
    print("Failed to start aphrodite engine after container launch. Exiting.")
    subprocess.run(["docker", "kill", container_id])
    sys.exit(1)

def main():
    set_logger_verbosity(args.verbosity)
    quiesce_logger(args.quiet)
    
    # Load configuration
    with open('bridgeData.yaml', 'rt', encoding='utf-8') as configfile:
        config = yaml.safe_load(configfile)
    
    # Set up bridge data
    bridge_data = KoboldAIBridgeData()
    
    # Set API type (default to koboldai if not specified)
    bridge_data.api_type = config.get('api_type', 'koboldai').lower()
    
    # Set common configuration
    bridge_data.worker_name = config.get('worker_name', 'DefaultWorker')
    bridge_data.api_key = config.get('api_key', '')
    bridge_data.model_name = config.get('model_name')
    if not bridge_data.model_name:
        print("No model specified in bridgeData.yaml. Exiting.")
        sys.exit(1)
    
    # Set the horde URL
    bridge_data.horde_url = config.get('horde_url', bridge_data.horde_url)
    
    # Set terminal UI setting
    bridge_data.terminal_ui_enabled = config.get('terminal_ui_enabled', False)
    
    # Handle API-specific configuration
    if bridge_data.api_type == 'openai':
        # For OpenAI, configure the endpoints and authentication
        bridge_data.openai_api_key = config.get('openai_api_key', '')
        if not bridge_data.openai_api_key:
            print("ERROR: OpenAI API key is required when using OpenAI API type. Please check your bridgeData.yaml file.")
            sys.exit(1)
        
        bridge_data.openai_url = config.get('openai_url', 'https://api.openai.com/v1')
        bridge_data.openai_model = config.get('openai_model', 'gpt-3.5-turbo')
        
        # Set the model name if not specified
        if not bridge_data.model_name or bridge_data.model_name == "stabilityai/stable-code-3b":
            bridge_data.model_name = f"OpenAI {bridge_data.openai_model}"
            
        print(f"Using OpenAI API with endpoint {bridge_data.openai_url} and model {bridge_data.openai_model}")
        print(f"Worker will be registered with model name: {bridge_data.model_name}")
        
    else:
        # For KoboldAI, set the KAI URL and check if the engine is running
        bridge_data.kai_url = config.get('kai_url', 'http://localhost:2242')
        
        old_nvidia_compute = config.get('old_nvidia_compute', False)
        download_dir = config.get('download_dir', './models')
        gpu_count = config.get('gpu_count', 1)  # Default to 1 if not specified
        
        # Only start the engine if we're using KoboldAI
        if not is_engine_running():
            print("Aphrodite engine is not running. Launching via Docker...")
            engine_container = start_aphrodite_engine(
                bridge_data.model_name, 
                gpu_count=gpu_count,
                old_nvidia_compute=old_nvidia_compute, 
                download_dir=download_dir
            )
            print("\nAphrodite engine has been launched! Check the logs above for details.")
            input("Press Enter to continue and start the text worker...\n")
        else:
            print("Aphrodite engine is already running.")
    
    # Set length parameters from config
    if 'max_length' in config:
        bridge_data.max_length = int(config.get('max_length'))
    if 'max_context_length' in config:
        bridge_data.max_context_length = int(config.get('max_context_length'))
    
    # Start the worker
    try:
        worker = ScribeWorker(bridge_data)
        worker.start()
    except KeyboardInterrupt:
        logger.info("Keyboard Interrupt Received. Ending Process")
    logger.init(f"{bridge_data.worker_name} Instance", status="Stopped")

if __name__ == "__main__":
    main()