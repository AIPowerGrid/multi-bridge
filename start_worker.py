#!/usr/bin/env python3
"""
This is the bridge, which connects the horde with the ML processing.

This version supports both KoboldAI and OpenAI-compatible endpoints.
For KoboldAI: Connects to an external KoboldAI API endpoint
For OpenAI: Connects directly to the OpenAI API using the provided credentials
"""
# isort: off
import time
import socket
import yaml
import os
import sys
import re
from urllib.parse import urlparse

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
    except Exception:
        return False

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
    if domain == 'localhost' or domain.startswith('localhost:') or re.match(r'^(\d{1,3}\.){3}\d{1,3}(:\d+)?$', domain):
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
    
    # If we got openai as a domain, keep it as is
    if domain == 'openai':
        return domain
    
    return domain or "gridbridge"

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
    if not bridge_data.model_name and bridge_data.api_type == 'openai':
        bridge_data.model_name = config.get('openai_model', 'gpt-3.5-turbo')
    
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
        
        print(f"Using OpenAI API with endpoint {bridge_data.openai_url} and model {bridge_data.openai_model}")
        
    else:
        # For KoboldAI, set the KAI URL
        bridge_data.kai_url = config.get('kai_url', 'http://localhost:5000')
        
        # Check if the server is available
        if not is_server_available(bridge_data.kai_url):
            print(f"KoboldAI server at {bridge_data.kai_url} is not available.")
            print("Please make sure the server is running and the URL is correct.")
            sys.exit(1)
        else:
            print(f"KoboldAI server found at {bridge_data.kai_url}")
    
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