# SimpleGrid Text Worker

A utility to connect the Grid with ML processing, supporting both external KoboldAI and OpenAI-compatible APIs.

## Features

- **Dual API Support:**  
  Connect either through an external KoboldAI server or directly to OpenAI API.

- **OpenAI Integration:**  
  Connect directly to OpenAI's API to use their models like GPT-3.5 and GPT-4.

- **KoboldAI Integration:**  
  Connect to any KoboldAI-compatible endpoint to use those models.

- **Multi-Worker Support:**  
  Run multiple workers with different configurations (different models, endpoints, or API types) in a single instance.

- **Intelligent Model Naming:**  
  Automatically prefixes model names with the API domain (e.g., "openai/gpt-3.5-turbo") for better visibility in the horde. Uses "gridbridge" prefix for localhost or IP addresses.

- **Unified Configuration:**  
  All settings are managed via `bridgeData.yaml` so that you can specify the API type, model, URLs, and other options in one place. `bridgeData_template.yaml` is provided as a starting point.

- **Streamlined Logging and UI:**  
  The utility provides logs and status details appropriate to the chosen API type.

## Installation

### Python Dependencies

Ensure you have Python 3 installed. Then run:

```bash
pip install -r requirements.txt
```

## Configuration

All settings are managed in the `bridgeData.yaml` file. An example configuration is provided in `bridgeData_template.yaml`.

### Configuration Structure

The configuration file is divided into two main sections:

1. **Global Configuration**: Settings that apply to all workers
2. **Endpoints Configuration**: Definition of API endpoints, each with multiple models that become workers

### Global Settings

- **horde_url:**  
  The URL of the horde API.

- **api_key:**  
  Your API key for the horde.

- **queue_size:**  
  Number of requests to keep in the queue.

### Endpoints Configuration

Each endpoint represents a connection to an API service (like OpenAI, DeepSeek, Anthropic, or a local KoboldAI server).
Under each endpoint, you can define multiple models, each running as a separate worker.

#### Endpoint Settings

- **type:**  
  The type of API ("openai" or "koboldai").

- **name:**  
  A name for the endpoint.

- **url:**  
  The base URL for the API.

- **api_key:**  
  The API key for this endpoint (for OpenAI-compatible endpoints). Not needed for KoboldAI.

#### Model Settings (each becomes a worker)

- **name:**  
  Give a name to your worker instance.

- **model:**  
  The model to use (for OpenAI-compatible endpoints).

- **max_threads:**  
  How many simultaneous requests this worker should handle.

- **max_length:**  
  The maximum amount of tokens to generate with this worker.

- **max_context_length:**  
  The maximum tokens to use from the prompt.

### Example Configuration

```yaml
## Global Configuration
horde_url: "https://api.aipowergrid.io/"
api_key: "your-api-key-here"
queue_size: 0

## Endpoints Configuration
endpoints:
  # OpenAI API endpoint
  - type: "openai"
    name: "openai-endpoint"
    api_key: "your-openai-api-key"
    url: "https://api.openai.com/v1"
    models:
      # Each model becomes a worker
      - name: "gpt35-worker"
        model: "gpt-3.5-turbo"
        max_threads: 1
        max_length: 512
        max_context_length: 4096
      
      - name: "gpt4-worker"
        model: "gpt-4"
        max_threads: 1
        max_length: 1024
        max_context_length: 8192
  
  # KoboldAI endpoint (local)
  - type: "koboldai"
    name: "kobold-endpoint"
    url: "http://localhost:5000"
    models:
      - name: "kobold-worker"
        max_threads: 1
        max_length: 512
        max_context_length: 4096
```

With this configuration, you would have three workers running simultaneously:
1. An OpenAI GPT-3.5 Turbo worker
2. An OpenAI GPT-4 worker
3. A KoboldAI worker

Each worker runs in its own thread, but shares the global configuration.

## Usage

1. Copy `bridgeData_template.yaml` to `bridgeData.yaml` and edit it to match your configuration.

2. Run the worker:

```bash
python start_worker.py
```

This will start all workers defined in your configuration.

## Troubleshooting

- **KoboldAI Connection Issues:**  
  Ensure your KoboldAI server is running and accessible at the URL specified in the configuration.

- **OpenAI Connection Issues:**  
  Verify your API key and check the OpenAI status page for any service disruptions.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

