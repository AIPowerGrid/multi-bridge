#!/usr/bin/env python3
"""
Startup script that creates bridgeData.yaml from environment variables for Coolify deployment
"""
import os
import yaml

def create_config_from_env():
    """Create bridgeData.yaml from environment variables"""
    
    # Get API key from environment
    api_key = os.getenv('API_KEY')
    if not api_key:
        raise ValueError("API_KEY environment variable is required")
    
    # Create configuration
    config = {
        'horde_url': os.getenv('HORDE_URL', 'https://api.aipowergrid.io/'),
        'api_key': api_key,
        'queue_size': int(os.getenv('QUEUE_SIZE', '0')),
        'endpoints': [
            {
                'type': 'openai',
                'name': 'groq-endpoint',
                'api_key': os.getenv('GROQ_API_KEY'),
                'url': 'https://api.groq.com/openai/v1',
                'models': [
                    {
                        'name': 'daddyhalfgemma.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'gemma2-9b-it',
                        'max_threads': 1,
                        'max_length': 8192,
                        'max_context_length': 8192
                    },
                    {
                        'name': 'daddyhalflama3.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'llama-3.1-8b-instant',
                        'max_threads': 1,
                        'max_length': 131072,
                        'max_context_length': 131072
                    },
                    {
                        'name': 'daddyhalflama70.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'llama-3.3-70b-versatile',
                        'max_threads': 1,
                        'max_length': 32768,
                        'max_context_length': 131072
                    },
                    {
                        'name': 'daddyhalfguard4.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'meta-llama/llama-guard-4-12b',
                        'max_threads': 1,
                        'max_length': 1024,
                        'max_context_length': 131072
                    },
                    {
                        'name': 'daddyhalfdeepseek.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'deepseek-r1-distill-llama-70b',
                        'max_threads': 1,
                        'max_length': 131072,
                        'max_context_length': 131072
                    },
                    {
                        'name': 'daddyhalfmav17.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'meta-llama/llama-4-maverick-17b-128e-instruct',
                        'max_threads': 1,
                        'max_length': 8192,
                        'max_context_length': 131072
                    },
                    {
                        'name': 'daddyhalfscout17.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'meta-llama/llama-4-scout-17b-16e-instruct',
                        'max_threads': 1,
                        'max_length': 8192,
                        'max_context_length': 131072
                    },
                    {
                        'name': 'daddyhalfkimi.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'moonshotai/kimi-k2-instruct',
                        'max_threads': 1,
                        'max_length': 16384,
                        'max_context_length': 131072
                    },
                    {
                        'name': 'daddyhalfqwen32.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'qwen/qwen3-32b',
                        'max_threads': 1,
                        'max_length': 40960,
                        'max_context_length': 131072
                    }
                ]
            }
        ]
    }
    
    # Write configuration file
    with open('bridgeData.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print("Configuration created successfully from environment variables:")
    print(f"- Horde URL: {config['horde_url']}")
    print(f"- API Key: {'*' * len(config['api_key']) if config['api_key'] else 'Not set'}")
    print(f"- Groq API Key: {'*' * len(config['endpoints'][0]['api_key']) if config['endpoints'][0]['api_key'] else 'Not set'}")
    print(f"- Models: {len(config['endpoints'][0]['models'])}")

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
