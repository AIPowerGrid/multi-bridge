import yaml
import os
from pathlib import Path
import openai
from grid_client import GridClient  # You'll need to implement this

def load_config():
    config_path = Path('bridgeData.yaml')
    with open(config_path) as f:
        return yaml.safe_load(f)

def main():
    config = load_config()
    
    # Setup OpenAI
    openai.api_key = config['openai_api_key']
    openai.api_base = config['openai_url']
    
    # Setup Grid Client
    grid = GridClient(
        api_key=config['api_key'],
        worker_name=config['worker_name'],
        horde_url=config['horde_url']
    )
    
    # Start processing
    grid.start_processing(
        max_threads=config['max_threads'],
        model=config['openai_model'],
        max_length=config['max_length']
    )

if __name__ == "__main__":
    main() 