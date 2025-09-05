#!/usr/bin/env python3
"""
Startup script for Coolify deployment that handles environment variable substitution
"""
import os
import yaml
import re
from pathlib import Path

def substitute_env_vars(value):
    """Substitute environment variables in a string value"""
    if isinstance(value, str):
        # Pattern to match ${VAR_NAME:-default_value} or ${VAR_NAME}
        pattern = r'\$\{([^}]+)\}'
        
        def replace(match):
            var_expr = match.group(1)
            if ':-' in var_expr:
                var_name, default = var_expr.split(':-', 1)
                return os.getenv(var_name, default)
            else:
                return os.getenv(var_expr, '')
        
        return re.sub(pattern, replace, value)
    return value

def process_yaml_value(value):
    """Recursively process YAML values to substitute environment variables"""
    if isinstance(value, dict):
        return {k: process_yaml_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [process_yaml_value(item) for item in value]
    else:
        return substitute_env_vars(value)

def create_config_from_env():
    """Create bridgeData.yaml from environment variables"""
    
    # Check if we have a template file
    template_path = Path('bridgeData_coolify.yaml')
    if template_path.exists():
        # Load and process template
        with open(template_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Process all values to substitute environment variables
        config = process_yaml_value(config)
    else:
        # Create minimal config from environment variables
        config = {
            'horde_url': os.getenv('HORDE_URL', 'https://api.aipowergrid.io/'),
            'api_key': os.getenv('API_KEY', ''),
            'queue_size': int(os.getenv('QUEUE_SIZE', '0')),
            'endpoints': []
        }
        
        # Add OpenAI endpoint if configured
        if os.getenv('OPENAI_API_KEY'):
            config['endpoints'].append({
                'type': 'openai',
                'name': 'openai-endpoint',
                'api_key': os.getenv('OPENAI_API_KEY'),
                'url': os.getenv('OPENAI_URL', 'https://api.openai.com/v1'),
                'models': [{
                    'name': 'openai-worker',
                    'model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
                    'max_threads': int(os.getenv('OPENAI_MAX_THREADS', '1')),
                    'max_length': int(os.getenv('OPENAI_MAX_LENGTH', '512')),
                    'max_context_length': int(os.getenv('OPENAI_MAX_CONTEXT_LENGTH', '4096'))
                }]
            })
        
        # Add KoboldAI endpoint if configured
        if os.getenv('KAI_URL'):
            config['endpoints'].append({
                'type': 'koboldai',
                'name': 'koboldai-endpoint',
                'url': os.getenv('KAI_URL'),
                'models': [{
                    'name': 'koboldai-worker',
                    'max_threads': int(os.getenv('KAI_MAX_THREADS', '1')),
                    'max_length': int(os.getenv('KAI_MAX_LENGTH', '512')),
                    'max_context_length': int(os.getenv('KAI_MAX_CONTEXT_LENGTH', '4096'))
                }]
            })
    
    # Validate configuration
    if not config.get('api_key'):
        raise ValueError("API_KEY environment variable is required")
    
    if not config.get('endpoints'):
        raise ValueError("No endpoints configured. Please set OPENAI_API_KEY or KAI_URL")
    
    # Write configuration file
    with open('bridgeData.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print("Configuration created successfully:")
    print(f"- Horde URL: {config['horde_url']}")
    print(f"- API Key: {'*' * len(config['api_key']) if config['api_key'] else 'Not set'}")
    print(f"- Endpoints: {len(config['endpoints'])}")
    
    for endpoint in config['endpoints']:
        print(f"  - {endpoint['type']}: {endpoint['name']}")
        for model in endpoint.get('models', []):
            print(f"    - Model: {model['name']}")

if __name__ == "__main__":
    try:
        create_config_from_env()
        print("Starting AI Power Grid Bridge...")
        # Import and run the main worker
        from start_worker import main
        main()
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
