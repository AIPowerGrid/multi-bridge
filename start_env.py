#!/usr/bin/env python3
"""
Startup script that creates bridgeData.yaml from environment variables for Coolify deployment
This version preserves the complex model configuration while only substituting sensitive values
"""
import os
import yaml
import re

def substitute_sensitive_values():
    """Create bridgeData.yaml by substituting only sensitive values from environment variables"""
    
    # Get sensitive values from environment
    api_key = os.getenv('API_KEY')
    groq_api_key = os.getenv('GROQ_API_KEY')
    
    if not api_key:
        raise ValueError("API_KEY environment variable is required")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is required")
    
    # Read the template configuration
    template_config = {
        'horde_url': os.getenv('HORDE_URL', 'https://api.aipowergrid.io/'),
        'api_key': api_key,
        'queue_size': int(os.getenv('QUEUE_SIZE', '0')),
        'endpoints': [
            {
                'type': 'openai',
                'name': 'groq-endpoint',
                'api_key': groq_api_key,
                'url': 'https://api.groq.com/openai/v1',
                'models': [
                    # Google Gemma2 9B (Production)
                    {
                        'name': 'daddyhalfgemma.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'gemma2-9b-it',
                        'max_threads': 1,
                        'max_length': 8192,
                        'max_context_length': 8192
                    },
                    # Meta Llama 3.1 8B Instant (Production)
                    {
                        'name': 'daddyhalflama3.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'llama-3.1-8b-instant',
                        'max_threads': 1,
                        'max_length': 131072,
                        'max_context_length': 131072
                    },
                    # Meta Llama 3.3 70B Versatile (Production)
                    {
                        'name': 'daddyhalflama70.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'llama-3.3-70b-versatile',
                        'max_threads': 1,
                        'max_length': 32768,
                        'max_context_length': 131072
                    },
                    # Meta Llama Guard 4 12B (Production)
                    {
                        'name': 'daddyhalfguard4.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'meta-llama/llama-guard-4-12b',
                        'max_threads': 1,
                        'max_length': 1024,
                        'max_context_length': 131072
                    },
                    # DeepSeek R1 Distill Llama 70B (Preview)
                    {
                        'name': 'daddyhalfdeepseek.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'deepseek-r1-distill-llama-70b',
                        'max_threads': 1,
                        'max_length': 131072,
                        'max_context_length': 131072
                    },
                    # Meta Llama 4 Maverick 17B (Preview)
                    {
                        'name': 'daddyhalfmav17.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'meta-llama/llama-4-maverick-17b-128e-instruct',
                        'max_threads': 1,
                        'max_length': 8192,
                        'max_context_length': 131072
                    },
                    # Meta Llama 4 Scout 17B (Preview)
                    {
                        'name': 'daddyhalfscout17.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'meta-llama/llama-4-scout-17b-16e-instruct',
                        'max_threads': 1,
                        'max_length': 8192,
                        'max_context_length': 131072
                    },
                    # Moonshot AI Kimi K2 Instruct (Preview)
                    {
                        'name': 'daddyhalfkimi.Ae5JCH4WfWcu4wjZmv8ZpTPRcK11y3Cb95',
                        'model': 'moonshotai/kimi-k2-instruct',
                        'max_threads': 1,
                        'max_length': 16384,
                        'max_context_length': 131072
                    },
                    # Alibaba Cloud Qwen3 32B (Preview)
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
        yaml.dump(template_config, f, default_flow_style=False, sort_keys=False)
    
    print("Configuration created successfully from environment variables:")
    print(f"- Horde URL: {template_config['horde_url']}")
    print(f"- API Key: {'*' * len(template_config['api_key']) if template_config['api_key'] else 'Not set'}")
    print(f"- Groq API Key: {'*' * len(template_config['endpoints'][0]['api_key']) if template_config['endpoints'][0]['api_key'] else 'Not set'}")
    print(f"- Models: {len(template_config['endpoints'][0]['models'])}")
    
    # Print model names for verification
    for model in template_config['endpoints'][0]['models']:
        print(f"  - {model['name']} ({model['model']})")

if __name__ == "__main__":
    try:
        substitute_sensitive_values()
        print("Starting AI Power Grid Bridge...")
        # Import and run the main worker
        from start_worker import main
        main()
    except Exception as e:
        print(f"Error: {e}")
        exit(1)