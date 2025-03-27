import asyncio
from app.core.celery_app import celery_app
from app.core.config import settings
from app.tasks.tasks import AsyncAITask, GenericPromptTask, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE
from typing import Dict, Any, Optional, List

# Default model configuration for Cerebras
DEFAULT_MODEL = "llama3.1-8b"

# Create a mock Cerebras client when API key is not available
class MockCerebrasClient:
    """A mock client that provides a compatible API but returns simple responses"""
    
    class ChatCompletions:
        async def create(self, model, messages, max_tokens, temperature, top_p=1, **kwargs):
            """Mock the completions create method"""
            response_text = "// Mock Cerebras response. This is placeholder code.\n\n"
            response_text += "// Create a basic cube\n"
            response_text += "const geometry = new THREE.BoxGeometry(1, 1, 1);\n"
            response_text += "const material = new THREE.MeshStandardMaterial({ color: 0x1a85ff });\n"
            response_text += "const cube = new THREE.Mesh(geometry, material);\n"
            response_text += "cube.position.set(0, 0.5, 0);\n\n"
            response_text += "// Return the cube\n"
            response_text += "return cube;"
            
            # Create a mock response object with the necessary structure
            class MockResponse:
                def __init__(self, text):
                    self.model = "mock-cerebras-model"
                    self.choices = [type('obj', (object,), {
                        'message': type('obj', (object,), {
                            'content': text
                        })
                    })]
                    self.usage = type('obj', (object,), {
                        'prompt_tokens': 10,
                        'completion_tokens': 50,
                        'total_tokens': 60
                    })
            
            return MockResponse(response_text)
    
    def __init__(self):
        self.chat = type('obj', (object,), {'completions': self.ChatCompletions()})

# Create Cerebras client
async def get_cerebras_client():
    if not settings.CEREBRAS_API_KEY:
        print("Warning: Cerebras API key not configured. Using mock client.")
        return MockCerebrasClient()
    
    try:
        # Only import the real client if we have an API key
        from cerebras.cloud.sdk import AsyncCerebras
        client = AsyncCerebras(api_key=settings.CEREBRAS_API_KEY)
        return client
    except ImportError:
        print("Warning: cerebras.cloud.sdk package not found. Using mock client.")
        return MockCerebrasClient()
    except Exception as e:
        print(f"Error initializing Cerebras client: {e}. Using mock client.")
        return MockCerebrasClient()

class AsyncCerebrasTask(AsyncAITask):
    """Base class for Cerebras Celery tasks that use async functions."""
    _client = None
    
    @property
    async def client(self):
        if self._client is None:
            self._client = await get_cerebras_client()
        return self._client

class CerebrasPromptTask(GenericPromptTask, AsyncCerebrasTask):
    """Task to process a prompt with Cerebras LLaMA."""
    
    def prepare_message_params(self, prompt: str, system_prompt: Optional[str] = None,
                             max_tokens: int = DEFAULT_MAX_TOKENS, 
                             temperature: float = DEFAULT_TEMPERATURE,
                             additional_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepare the message parameters for Cerebras."""
        messages = []
        
        # Add system message if provided
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
            
        # Add user message
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Prepare parameters
        message_params = {
            "model": DEFAULT_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Add any additional parameters
        if additional_params:
            message_params.update(additional_params)
            
        return message_params
    
    async def send_message(self, client, message_params: Dict[str, Any]) -> Any:
        """Send the message to Cerebras."""
        model = message_params.pop("model")
        return await client.chat.completions.create(model=model, top_p=1, **message_params)
    
    def extract_content(self, response: Any) -> str:
        """Extract the content from Cerebras response."""
        return response.choices[0].message.content.lstrip("```javascript").rstrip("```")
    
    def prepare_final_response(self, task_id: str, response: Any, content: str) -> Dict[str, Any]:
        """Prepare the final response with Cerebras-specific metadata."""
        return {
            "status": "success",
            "content": content,
            "model": response.model,
            "usage": {
                "input_tokens": getattr(response.usage, "prompt_tokens", 0),
                "output_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0)
            },
            "task_id": task_id
        }

# Register the task properly with Celery
CerebrasPromptTask = celery_app.register_task(CerebrasPromptTask())