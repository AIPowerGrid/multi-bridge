# SimpleGrid Text Bridge

A lightweight bridge to connect OpenAI-compatible and KoboldAI endpoints to the AI Power Grid distributed inference network.

## Overview

This bridge enables you to contribute your local or remote LLM endpoints to the [AI Power Grid](https://docs.aipowergrid.io/) network. It supports:

- OpenAI API-compatible endpoints (OpenAI, Azure, local servers)
- KoboldAI-compatible endpoints
- Multiple workers with different configurations
- Automatic model name prefixing for endpoint identification

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `bridgeData_template.yaml` to `bridgeData.yaml` and configure your endpoints:

```yaml
# Global settings
horde_url: "https://api.aipowergrid.io/"
api_key: "your-api-key-here"
queue_size: 0

# Example configurations
endpoints:
  # OpenAI-compatible endpoint
  - type: "openai"
    name: "openai-endpoint"
    api_key: "your-api-key"
    url: "https://api.openai.com/v1"
    models:
      - name: "gpt35-worker"
        model: "gpt-3.5-turbo"
        max_threads: 1
        max_length: 512
        max_context_length: 4096

  # Local KoboldAI endpoint
  - type: "koboldai"
    name: "local-kobold"
    url: "http://localhost:5000"
    models:
      - name: "local-model"
        max_threads: 1
        max_length: 512
        max_context_length: 4096
```

3. Start the bridge:
```bash
python start_worker.py
```

## Configuration Reference

### Global Settings
- `horde_url`: AI Power Grid API endpoint
- `api_key`: Your Grid API key
- `queue_size`: Request queue size (0 for unlimited)

### Endpoint Settings
- `type`: API type ("openai" or "koboldai")
- `name`: Endpoint identifier
- `url`: Base API URL
- `api_key`: API key for OpenAI-compatible endpoints

### Model Settings
- `name`: Worker instance name
- `model`: Model identifier (OpenAI-compatible only)
- `max_threads`: Concurrent request limit
- `max_length`: Maximum generation length
- `max_context_length`: Maximum input context length

## Notes

- Model names are automatically prefixed with the endpoint domain
- Local/IP endpoints use "gridbridge" prefix
- Each model configuration creates a separate worker thread

## Contributing

Contributions welcome! Please submit issues and pull requests on GitHub.

