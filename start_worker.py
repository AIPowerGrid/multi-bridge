#!/usr/bin/env python3
"""
This version supports both KoboldAI and OpenAI-compatible endpoints.
"""
# isort: off
import time
import socket
import yaml
import os
import sys
import re
from urllib.parse import urlparse
import threading

from worker.argparser.scribe import args
from worker.utils.set_envs import set_worker_env_vars_from_config
set_worker_env_vars_from_config()  # Get necessary environment variables

from worker.bridge_data.scribe import KoboldAIBridgeData  # noqa: E402
from worker.logger import logger, quiesce_logger, set_logger_verbosity  # noqa: E402
from worker.workers.scribe import ScribeWorker  # noqa: E402
# isort: on

def is_server_available(url, timeout=5):
    """
    Check if a server is available by attempting to connect to the given URL.
    """
    # Extract host and port from URL
    if url.startswith('http://'):
        host = url[7:].split('/')[0]
    elif url.startswith('https://'):
        host = url[8:].split('/')[0]
    else:
        host = url.split('/')[0]
    
    # Extract port if specified
    if ':' in host:
        host, port = host.split(':')
        port = int(port)
    else:
        port = 443 if url.startswith('https://') else 80
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception as e:
        logger.error(f"Error checking server availability: {e}")
        return False
    finally:
        s.close()

def parse_domain_from_url(url):
    """
    Parse the domain from a URL and format it for use as a model prefix.
    - Removes 'www.' and '.com' if present
    - Returns 'gridbridge' if localhost or IP address
    """
    # Handle empty or invalid URLs
    if not url:
        return "gridbridge"
    
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Extract the netloc (domain)
    domain = parsed_url.netloc
    
    # If netloc is empty, the URL might not have http:// prefix
    if not domain and url:
        domain = url.split('/')[0]
    
    # Check if it's localhost or an IP address
    if domain == 'localhost' or re.match(r'^(\d{1,3}\.){3}\d{1,3}(:\d+)?$', domain):
        return "gridbridge"
    
    # Remove port if present
    if ':' in domain:
        domain = domain.split(':')[0]
    
    # Handle api subdomains - if domain starts with 'api.' get the next part
    if domain.startswith('api.'):
        # Get the second part of the domain (after 'api.')
        domain_parts = domain.split('.')
        if len(domain_parts) >= 2:
            domain = domain_parts[1]
    
    # Remove www. prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]
    
    # Remove .com suffix if present
    if domain.endswith('.com'):
        domain = domain[:-4]
    
    # Remove other TLDs if needed
    domain = domain.split('.')[0]
    
    # Special case for groq - return 'grid'
    if domain == 'groq':
        return 'grid'
    
    # If we got openai as a domain, keep it as is
    if domain == 'openai':
        return domain
    
    return domain or "gridbridge"

def start_worker(endpoint_config, model_config, global_config):
    """
    Initialize and start a worker with the given configuration.
    
    Args:
        endpoint_config (dict): The configuration for the endpoint
        model_config (dict): The configuration for the specific model
        global_config (dict): The global configuration shared by all workers
    """
    endpoint_type = endpoint_config.get('type', 'koboldai').lower()
    # Use a more descriptive name if endpoint name is not specified
    endpoint_name = endpoint_config.get('name', f"{endpoint_type}-endpoint")
    model_name = model_config.get('name', 'unnamed-model')
    
    worker_name = f"{model_name}"
    # We'll print a consolidated message after we have all the info
    
    # Set up bridge data
    bridge_data = KoboldAIBridgeData()
    
    # Set common configuration from global settings
    bridge_data.worker_name = worker_name
    bridge_data.api_key = global_config.get('api_key', '')
    bridge_data.horde_url = global_config.get('horde_url', bridge_data.horde_url)
    
    # Set worker-specific configuration
    bridge_data.max_threads = model_config.get('max_threads', 1)
    
    # Set API type
    bridge_data.api_type = endpoint_type
    
    # Set length parameters from config
    if 'max_length' in model_config:
        bridge_data.max_length = int(model_config.get('max_length'))
    if 'max_context_length' in model_config:
        bridge_data.max_context_length = int(model_config.get('max_context_length'))
    
    # Handle API-specific configuration
    if endpoint_type == 'openai':
        # For OpenAI, configure the endpoints and authentication
        bridge_data.openai_api_key = endpoint_config.get('api_key', '')
        if not bridge_data.openai_api_key:
            print(f"ERROR: OpenAI API key is required for endpoint '{endpoint_name}' using OpenAI API type. Skipping workers for this endpoint.")
            return
        
        bridge_data.openai_url = endpoint_config.get('url', 'https://api.openai.com/v1')
        bridge_data.openai_model = model_config.get('model', 'gpt-3.5-turbo')
        
        # Print a more concise connection message
        domain_prefix = parse_domain_from_url(bridge_data.openai_url)
        # Include a shortened URL for context
        short_url = bridge_data.openai_url.replace("https://", "").replace("http://", "").split("/")[0]
        print(f"🔌 Starting worker: {worker_name} using {domain_prefix}/{bridge_data.openai_model} ({short_url})")
        
        # Special case for Llama 4 models - use groq prefix instead of grid
        if bridge_data.openai_model == "meta-llama/llama-4-scout-17b-16e-instruct":
            domain_prefix = "groq"
        elif ("llama-4" in bridge_data.openai_model.lower() or "meta-llama/llama-4" in bridge_data.openai_model.lower()) and domain_prefix == "grid":
            domain_prefix = "groq"
        
        # Set the model_name with domain prefix
        bridge_data.model_name = f"{domain_prefix}/{bridge_data.openai_model}"
        
    else:
        # For KoboldAI, set the KAI URL
        bridge_data.kai_url = endpoint_config.get('url', 'http://localhost:5000')
        
        # Check if the server is available
        if not is_server_available(bridge_data.kai_url):
            print(f"KoboldAI server at {bridge_data.kai_url} is not available for endpoint '{endpoint_name}'.")
            print("Please make sure the server is running and the URL is correct. Skipping workers for this endpoint.")
            return
        else:
            # Get domain for the URL
            short_url = bridge_data.kai_url.replace("https://", "").replace("http://", "").split("/")[0]
            if short_url == "localhost:5000":
                short_url = "localhost"
            
            # Print consolidated message
            print(f"🔌 Starting worker: {worker_name} using KoboldAI/{bridge_data.model} ({short_url})")
    
    # Start the worker
    try:
        worker = ScribeWorker(bridge_data)
        worker.start()
    except Exception as e:
        logger.error(f"Error starting worker '{worker_name}': {e}")

def load_configuration(config_path='bridgeData.yaml'):
    """
    Load and validate configuration from a YAML file.
    """
    with open(config_path, 'rt', encoding='utf-8') as configfile:
        config = yaml.safe_load(configfile)

    global_config = {
        'horde_url': config.get('horde_url', 'https://api.aipowergrid.io/'),
        'api_key': config.get('api_key', ''),
        'queue_size': config.get('queue_size', 0)
    }

    endpoints_config = config.get('endpoints', [])

    if not endpoints_config:
        workers_config = config.get('workers', [])
        if workers_config:
            print("Using previous 'workers' configuration format. Consider updating to the new 'endpoints' format.")
            for worker_config in workers_config:
                api_type = worker_config.get('api_type', 'koboldai').lower()
                if api_type == 'openai':
                    endpoint_config = {
                        'type': 'openai',
                        'name': f"{worker_config.get('name')}-endpoint",
                        'api_key': worker_config.get('openai_api_key', ''),
                        'url': worker_config.get('openai_url', 'https://api.openai.com/v1'),
                        'models': [{
                            'name': worker_config.get('name'),
                            'model': worker_config.get('openai_model', 'gpt-3.5-turbo'),
                            'max_threads': worker_config.get('max_threads', 1),
                            'max_length': worker_config.get('max_length', 512),
                            'max_context_length': worker_config.get('max_context_length', 4096),
                        }]
                    }
                else:
                    endpoint_config = {
                        'type': 'koboldai',
                        'name': f"{worker_config.get('name')}-endpoint",
                        'url': worker_config.get('kai_url', 'http://localhost:5000'),
                        'models': [{
                            'name': worker_config.get('name'),
                            'max_threads': worker_config.get('max_threads', 1),
                            'max_length': worker_config.get('max_length', 512),
                            'max_context_length': worker_config.get('max_context_length', 4096),
                        }]
                    }
                endpoints_config.append(endpoint_config)

        if not endpoints_config:
            print("No endpoints or workers found, using legacy configuration format...")
            api_type = config.get('api_type', 'koboldai').lower()
            worker_name = config.get('worker_name', config.get('scribe_name', 'DefaultWorker'))
            if api_type == 'openai':
                endpoints_config = [{
                    'type': 'openai',
                    'name': 'legacy-openai-endpoint',
                    'api_key': config.get('openai_api_key', ''),
                    'url': config.get('openai_url', 'https://api.openai.com/v1'),
                    'models': [{
                        'name': worker_name,
                        'model': config.get('openai_model', 'gpt-3.5-turbo'),
                        'max_threads': config.get('max_threads', 1),
                        'max_length': config.get('max_length', 512),
                        'max_context_length': config.get('max_context_length', 4096),
                    }]
                }]
            else:
                endpoints_config = [{
                    'type': 'koboldai',
                    'name': 'legacy-koboldai-endpoint',
                    'url': config.get('kai_url', 'http://localhost:5000'),
                    'models': [{
                        'name': worker_name,
                        'max_threads': config.get('max_threads', 1),
                        'max_length': config.get('max_length', 512),
                        'max_context_length': config.get('max_context_length', 4096),
                    }]
                }]

    if not endpoints_config or not any(len(endpoint.get('models', [])) > 0 for endpoint in endpoints_config):
        print("ERROR: No valid endpoints with models defined in configuration file. Please add at least one endpoint with at least one model.")
        sys.exit(1)

    return global_config, endpoints_config

def main():
    set_logger_verbosity(args.verbosity)
    quiesce_logger(args.quiet)

    global_config, endpoints_config = load_configuration()

    total_workers = sum(len(endpoint.get('models', [])) for endpoint in endpoints_config)
    print(f"Found {len(endpoints_config)} endpoint(s) with a total of {total_workers} worker(s) in configuration")

    worker_threads = []
    for endpoint_config in endpoints_config:
        models = endpoint_config.get('models', [])
        for model_config in models:
            worker_thread = threading.Thread(
                target=start_worker,
                args=(endpoint_config, model_config, global_config),
                name=f"Worker-{model_config.get('name', 'unnamed')}"
            )
            worker_threads.append(worker_thread)
            worker_thread.daemon = True
            worker_thread.start()

    try:
        while any(thread.is_alive() for thread in worker_threads):
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard Interrupt Received. Ending Process")

    logger.info("All workers stopped", status="Stopped")

if __name__ == "__main__":
    main()