# SimpleGrid Text Worker

A utility to connect the Grid with ML processing, supporting both external KoboldAI and OpenAI-compatible APIs.

## Features

- **Dual API Support:**  
  Connect either through an external KoboldAI server or directly to OpenAI API.

- **OpenAI Integration:**  
  Connect directly to OpenAI's API to use their models like GPT-3.5 and GPT-4.

- **KoboldAI Integration:**  
  Connect to any KoboldAI-compatible endpoint to use those models.

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

### Common Settings

- **api_type:**  
  Choose between "koboldai" or "openai" to determine which API to use.

- **model_name:**  
  Used as a display name in the horde for both KoboldAI and OpenAI modes. 
  The domain will be automatically added as a prefix (e.g., "openai/gpt-3.5-turbo").

- **worker_name:**  
  Give a name to your worker instance.

- **horde_url:**  
  The URL of the horde API.

- **api_key:**  
  Your API key for the horde.

### KoboldAI-specific Settings

- **kai_url:**  
  The URL of your KoboldAI server, e.g., "http://localhost:5000" or any other KoboldAI-compatible endpoint.

### OpenAI-specific Settings

- **openai_api_key:**  
  Your OpenAI API key (begins with "sk-").

- **openai_url:**  
  The OpenAI API URL (defaults to "https://api.openai.com/v1").

- **openai_model:**  
  The OpenAI model to use (e.g., "gpt-3.5-turbo", "gpt-4").

## Usage

1. Copy `bridgeData_template.yaml` to `bridgeData.yaml` and edit it to match your configuration.

2. Run the worker:

```bash
python start_worker.py
```

## Troubleshooting

- **KoboldAI Connection Issues:**  
  Ensure your KoboldAI server is running and accessible at the URL specified in the configuration.

- **OpenAI Connection Issues:**  
  Verify your API key and check the OpenAI status page for any service disruptions.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

