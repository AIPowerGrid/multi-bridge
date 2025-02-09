#!/usr/bin/env python3
"""
This is the bridge, which connects the horde with the ML processing.

This version checks if the aphrodite engine (an OpenAI-compatible model server)
is running on port 2242. If it's not running, it automatically launches the engine
inside a Docker container using the model specified in bridgeData.yaml.
After the engine starts, it pauses so you can review the logs before proceeding.
"""
# isort: off
import threading
import time
import socket
import subprocess
import sys
import shutil
import yaml

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

def start_aphrodite_engine(model_name, old_nvidia_compute=False, api_key="sk-dummy"):
    """
    Launch the aphrodite engine as a Docker container with the specified model.
    If old_nvidia_compute is True, include the '--dtype half' flag.
    """
    if shutil.which("docker") is None:
        print("Error: The 'docker' command is not found in your PATH. Please install Docker.")
        sys.exit(1)
    
    command = [
        "docker", "run", "--rm", "-d",
        "--gpus", "all",
        "-p", "2242:2242",
        "--ipc=host",
        "alpindale/aphrodite-openai:latest", # This is the latest version of the aphrodite engine
        "--model", model_name, # Set from bridgeData.yaml
        "--tensor-parallel-size", "1", # You can change this if you want to use more than 1 GPU
    ]
    
    # Add "--dtype half" if using an older Nvidia GPU.
    if old_nvidia_compute:
        command.extend(["--dtype", "half"])
    
    command.extend([
        "--launch-kobold-api",
    ])
    
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
    
    with open('bridgeData.yaml', 'rt', encoding='utf-8') as configfile:
        config = yaml.safe_load(configfile)
    
    bridge_data = KoboldAIBridgeData()
    bridge_data.worker_name = config.get('worker_name', 'DefaultWorker')
    bridge_data.api_key = config.get('api_key', '')
    bridge_data.model_name = config.get('model_name')
    if not bridge_data.model_name:
        print("No model specified in bridgeData.yaml. Exiting.")
        sys.exit(1)
    
    # Set the URLs from the YAML (using external URLs if preferred).
    bridge_data.horde_url = config.get('horde_url', bridge_data.horde_url)
    bridge_data.kai_url = config.get('kai_url', bridge_data.horde_url)
    
    old_nvidia_compute = config.get('old_nvidia_compute', False)
    
    if not is_engine_running():
        print("Aphrodite engine is not running. Launching via Docker...")
        engine_container = start_aphrodite_engine(bridge_data.model_name, old_nvidia_compute, bridge_data.api_key)
        print("\nAphrodite engine has been launched! Check the logs above for details.")
        input("Press Enter to continue and start the text worker...\n")
    else:
        print("Aphrodite engine is already running.")
    
    try:
        worker = ScribeWorker(bridge_data)
        worker.start()
    except KeyboardInterrupt:
        logger.info("Keyboard Interrupt Received. Ending Process")
    logger.init(f"{bridge_data.worker_name} Instance", status="Stopped")

if __name__ == "__main__":
    main()