import yaml
import os
from pathlib import Path
import openai
import sys
import requests
import json
from loguru import logger

def load_config():
    config_path = Path('bridgeData.yaml')
    if not config_path.exists():
        print("Error: bridgeData.yaml not found. Please create it from the template.")
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)

class GridClient:
    def __init__(self, api_key, worker_name, horde_url):
        self.api_key = api_key
        self.worker_name = worker_name
        self.horde_url = horde_url
        self.max_threads = 1
        self.running = False
        logger.info(f"Initialized GridClient with worker name: {worker_name}")
        
    def start_processing(self, max_threads=1, model=None, max_length=512):
        """Start processing requests from the horde."""
        self.max_threads = max_threads
        self.model = model
        self.max_length = max_length
        self.running = True
        
        logger.info(f"Starting processing with model: {model}, max_length: {max_length}")
        
        # This would normally enter a loop to process requests
        # For now, just print a message
        print(f"Grid client started with {max_threads} threads")
        print(f"Model: {model}")
        print(f"Max length: {max_length}")
        print("Press Ctrl+C to stop")
        
        try:
            # Keep running until interrupted
            while self.running:
                # In a real implementation, this would poll for jobs
                pass
        except KeyboardInterrupt:
            logger.info("Processing stopped by user")
            self.running = False

def main():
    config = load_config()
    
    api_type = config.get('api_type', 'openai').lower()
    model_name = config.get('model_name')
    
    if api_type == 'openai':
        # Setup OpenAI
        openai.api_key = config['openai_api_key']
        openai.api_base = config['openai_url']
        openai_model = config.get('openai_model', 'gpt-3.5-turbo')
        
        # We don't need to set the model prefix here anymore
        # It will be handled by the bridge_data class
        if not model_name:
            model_name = openai_model
        
        print(f"Using OpenAI API with endpoint {config['openai_url']} and model {openai_model}")
    else:
        # Setup KoboldAI
        kai_url = config.get('kai_url', 'http://localhost:5000')
        print(f"Using KoboldAI API with endpoint {kai_url}")
    
    # Setup Grid Client
    grid = GridClient(
        api_key=config['api_key'],
        worker_name=config['worker_name'],
        horde_url=config['horde_url']
    )
    
    # Start processing
    grid.start_processing(
        max_threads=config.get('max_threads', 1),
        model=model_name,
        max_length=config.get('max_length', 512)
    )

if __name__ == "__main__":
    main() 