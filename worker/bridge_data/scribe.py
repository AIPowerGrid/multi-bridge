"""The configuration of the bridge"""
import os
import re
from urllib.parse import urlparse

import requests
from loguru import logger

from worker.argparser.scribe import args
from worker.bridge_data.framework import BridgeDataTemplate


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
    
    # If we got openai as a domain, keep it as is
    if domain == 'openai':
        return domain
    
    return domain or "gridbridge"


class KoboldAIBridgeData(BridgeDataTemplate):
    """Configuration object"""

    def __init__(self):
        super().__init__(args)
        # Common configuration
        self.model = None
        self.model_name = None  # Will store the formatted model name with domain prefix
        self.max_length = int(os.environ.get("HORDE_MAX_LENGTH", "80"))
        self.max_context_length = int(os.environ.get("HORDE_MAX_CONTEXT_LENGTH", "1024"))
        self.branded_model = os.environ.get("HORDE_BRANDED_MODEL", "false") == "true"
        self.nsfw = os.environ.get("HORDE_NSFW", "true") == "true"
        self.blacklist = list(filter(lambda a: a, os.environ.get("HORDE_BLACKLIST", "").split(",")))
        self.terminal_ui_enabled = False
        
        # API type (koboldai or openai)
        self.api_type = "koboldai"
        
        # KoboldAI specific configuration
        self.kai_available = False
        self.kai_url = "http://localhost:5000"
        self.softprompts = {}
        self.current_softprompt = None
        
        # OpenAI specific configuration
        self.openai_available = False
        self.openai_url = "https://api.openai.com/v1"
        self.openai_api_key = ""
        self.openai_model = "gpt-3.5-turbo"

    @logger.catch(reraise=True)
    def reload_data(self):
        """Reloads configuration data"""
        previous_url = self.horde_url
        super().reload_data()
        if hasattr(self, "scribe_name") and not self.args.worker_name:
            self.worker_name = self.scribe_name
            
        # Set the API type
        if hasattr(self, "api_type"):
            self.api_type = self.api_type.lower()
        
        # Handle KoboldAI specific configuration
        if args.kai_url:
            self.kai_url = args.kai_url
        if args.sfw:
            self.nsfw = False
        if args.blacklist:
            self.blacklist = args.blacklist
            
        # Validate the appropriate API based on api_type
        if self.api_type == "openai":
            self.validate_openai()
            if self.openai_available and not self.initialized and previous_url != self.horde_url:
                logger.init(
                    (
                        f"Username '{self.username}'. Server Name '{self.worker_name}'. "
                        f"Horde URL '{self.horde_url}'. OpenAI URL '{self.openai_url}'. "
                        "Worker Type: Scribe (OpenAI)"
                    ),
                    status="Joining Horde",
                )
        else:  # Default to koboldai
            self.validate_kai()
            if self.kai_available and not self.initialized and previous_url != self.horde_url:
                logger.init(
                    (
                        f"Username '{self.username}'. Server Name '{self.worker_name}'. "
                        f"Horde URL '{self.horde_url}'. KoboldAI Client URL '{self.kai_url}'. "
                        "Worker Type: Scribe"
                    ),
                    status="Joining Horde",
                )
                
        # If model_name has been set externally (by start_worker.py), use that
        # Otherwise, create it with the domain prefix
        if not self.model_name and self.model:
            if self.api_type == "openai":
                domain_prefix = parse_domain_from_url(self.openai_url)
                self.model_name = f"{domain_prefix}/{self.openai_model}"
            else:
                domain_prefix = parse_domain_from_url(self.kai_url)
                self.model_name = f"{domain_prefix}/{self.model}"

    @logger.catch(reraise=True)
    def validate_kai(self):
        """Validates the KoboldAI API connection"""
        logger.debug("Retrieving settings from KoboldAI Client...")
        # Prepare headers with the API key if available.
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            # Request the model with authentication headers.
            req = requests.get(self.kai_url + "/api/latest/model", headers=headers)
            logger.debug("Response from /api/latest/model: [{}] {}", req.status_code, req.text)
            req.raise_for_status()  # raises an error if the status isn't 200
            json_data = req.json()
            logger.debug("JSON decoded: {}", json_data)
            
            if "result" not in json_data:
                logger.error("Expected key 'result' not found in response: {}", json_data)
                self.kai_available = False
                return
            
            self.model = json_data["result"]
            # Normalize huggingface and local downloaded model names
            if "/" not in self.model:
                self.model = self.model.replace("_", "/", 1)
                
            # Set the model_name with domain prefix
            domain_prefix = parse_domain_from_url(self.kai_url)
            self.model_name = f"{domain_prefix}/{self.model}"
            logger.debug(f"Set model_name to: {self.model_name}")
            
            # Retrieve soft prompts list if needed.
            if self.model not in self.softprompts:
                req = requests.get(self.kai_url + "/api/latest/config/soft_prompts_list", headers=headers)
                logger.debug("Response from /api/latest/config/soft_prompts_list: [{}] {}", req.status_code, req.text)
                req.raise_for_status()
                sp_data = req.json()
                if "values" in sp_data:
                    self.softprompts[self.model] = [sp["value"] for sp in sp_data["values"]]
                else:
                    logger.error("Unexpected format for soft_prompts_list: {}", sp_data)
            
            # Retrieve current soft prompt.
            req = requests.get(self.kai_url + "/api/latest/config/soft_prompt", headers=headers)
            logger.debug("Response from /api/latest/config/soft_prompt: [{}] {}", req.status_code, req.text)
            req.raise_for_status()
            soft_prompt_data = req.json()
            if "value" not in soft_prompt_data:
                logger.error("Expected key 'value' not found in soft_prompt response: {}", soft_prompt_data)
                self.kai_available = False
                return
            self.current_softprompt = soft_prompt_data["value"]

        except requests.exceptions.RequestException as e:
            logger.error("Request error while validating KAI at {}: {}", self.kai_url, e)
            self.kai_available = False
            return
        except Exception as e:
            logger.error("Unexpected error during KAI validation: {}", e)
            self.kai_available = False
            return

        self.kai_available = True
        
    @logger.catch(reraise=True)
    def validate_openai(self):
        """Validates the OpenAI API connection"""
        logger.debug("Validating OpenAI API connection...")
        
        # If the API key is not set, we can't proceed
        if not self.openai_api_key:
            logger.error("OpenAI API key is not set")
            self.openai_available = False
            return
            
        try:
            # Set up headers with API key
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            # Test the connection by listing models
            url = f"{self.openai_url}/models"
            logger.debug(f"Testing OpenAI connection with URL: {url}")
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Check if specified model is valid
            if self.openai_model:
                model_found = False
                models_data = response.json()
                
                # Log available models for debugging
                logger.debug(f"OpenAI API returned {len(models_data.get('data', []))} models")
                
                # Look for the specified model
                for model in models_data.get("data", []):
                    if model.get("id") == self.openai_model:
                        model_found = True
                        break
                
                if not model_found:
                    logger.warning(f"Specified model '{self.openai_model}' was not found in the available models")
                    # We'll continue anyway as custom endpoints might not list all models
            
            logger.info(f"OpenAI API connection successful with endpoint: {self.openai_url}")
            self.openai_available = True
            
            # For internal reference, set the model name to the OpenAI model
            self.model = self.openai_model
            
            # Set the model_name with domain prefix
            domain_prefix = parse_domain_from_url(self.openai_url)
            self.model_name = f"{domain_prefix}/{self.openai_model}"
            logger.debug(f"Set model_name to: {self.model_name}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to OpenAI API: {e}")
            self.openai_available = False
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI validation: {e}")
            self.openai_available = False
