from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Generator
import requests
import json
import sseclient
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentWorkflow(ABC):
    """
    Base class for AI Agent workflows
    Provides common interface for different agent platforms
    """
    
    def __init__(self, name: str):
        self.name = name
        self.session = requests.Session()
        logger.info(f"Initialized {self.name} agent")
    
    @abstractmethod
    def send_request(self, *args, **kwargs) -> Any:
        """Send request to the agent platform"""
        pass
    
    @abstractmethod
    def process_response(self, response: Any) -> Any:
        """Process the response from the agent platform"""
        pass
    
    def close(self):
        """Clean up resources"""
        self.session.close()
        logger.info(f"Closed {self.name} agent session")


class N8nAgent(AgentWorkflow):
    """
    n8n Webhook Agent with streaming support
    Handles webhook requests and streaming responses
    """
    
    def __init__(self, webhook_url: str, api_key: Optional[str] = None, timeout: int = 30):
        super().__init__("n8n")
        self.webhook_url = webhook_url
        self.api_key = api_key
        self.timeout = timeout
        
        # Setup headers
        self.headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
    
    def send_request(self, data: Dict[str, Any], stream: bool = True) -> requests.Response:
        """
        Send request to n8n webhook
        
        Args:
            data: Payload to send to the webhook
            stream: Whether to enable streaming response
            
        Returns:
            Response object
        """
        try:
            logger.info(f"Sending request to n8n webhook: {self.webhook_url}")
            response = self.session.post(
                self.webhook_url,
                json=data,
                headers=self.headers,
                stream=stream,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending request to n8n: {str(e)}")
            raise
    
    def process_response(self, response: requests.Response, stream: bool = True) -> Any:
        """
        Process n8n webhook response
        
        Args:
            response: Response object from n8n
            stream: Whether to process as stream
            
        Returns:
            Processed response data or generator for streaming
        """
        if stream:
            return self._process_streaming_response(response)
        else:
            return response.json()
    
    def _process_streaming_response(self, response: requests.Response) -> Generator[str, None, None]:
        """
        Process streaming response from n8n webhook
        
        Yields:
            Chunks of streaming data
        """
        try:
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    # Remove 'data: ' prefix if present
                    if line.startswith('data: '):
                        line = line[6:]
                    
                    if line.strip() == '[DONE]':
                        logger.info("Streaming completed")
                        break
                    
                    try:
                        data = json.loads(line)
                        yield data
                    except json.JSONDecodeError:
                        # If not JSON, yield raw text
                        yield line
        except Exception as e:
            logger.error(f"Error processing streaming response: {str(e)}")
            raise
    
    def run_workflow(self, workflow_data: Dict[str, Any], stream: bool = True) -> Any:
        """
        Complete workflow: send request and process response
        
        Args:
            workflow_data: Data to send to the workflow
            stream: Whether to use streaming
            
        Returns:
            Processed response
        """
        response = self.send_request(workflow_data, stream=stream)
        return self.process_response(response, stream=stream)


class DifyAgent(AgentWorkflow):
    """
    Dify SSE Agent
    Handles Server-Sent Events (SSE) API requests
    """
    
    def __init__(self, api_url: str, api_key: str, timeout: int = 60):
        super().__init__("Dify")
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        
        # Setup headers for Dify API
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def send_request(self, 
                     query: str, 
                     user_id: str,
                     conversation_id: Optional[str] = None,
                     inputs: Optional[Dict[str, Any]] = None,
                     response_mode: str = "streaming") -> requests.Response:
        """
        Send request to Dify API
        
        Args:
            query: User query/message
            user_id: Unique user identifier
            conversation_id: Optional conversation ID for context
            inputs: Optional additional inputs
            response_mode: 'streaming' or 'blocking'
            
        Returns:
            Response object
        """
        payload = {
            "query": query,
            "user": user_id,
            "response_mode": response_mode,
            "inputs": inputs or {}
        }
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        try:
            logger.info(f"Sending request to Dify API: {self.api_url}")
            response = self.session.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                stream=(response_mode == "streaming"),
                timeout=self.timeout
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending request to Dify: {str(e)}")
            raise
    
    def process_response(self, response: requests.Response, streaming: bool = True) -> Any:
        """
        Process Dify API response
        
        Args:
            response: Response object from Dify
            streaming: Whether response is streaming
            
        Returns:
            Processed response or generator for streaming
        """
        if streaming:
            return self._process_sse_stream(response)
        else:
            return response.json()
    
    def _process_sse_stream(self, response: requests.Response) -> Generator[Dict[str, Any], None, None]:
        """
        Process Server-Sent Events stream from Dify
        
        Yields:
            Parsed SSE events
        """
        try:
            client = sseclient.SSEClient(response)
            
            for event in client.events():
                if not event.data:
                    continue
                
                # Skip empty or ping events
                if event.data.strip() in ['', 'ping', ':']:
                    continue
                
                try:
                    data = json.loads(event.data)
                    
                    # Handle different event types
                    event_type = data.get('event', '')
                    
                    if event_type == 'message':
                        # Regular message chunk
                        yield {
                            'type': 'message',
                            'content': data.get('answer', ''),
                            'conversation_id': data.get('conversation_id')
                        }
                    elif event_type == 'message_end':
                        # End of message
                        yield {
                            'type': 'message_end',
                            'metadata': data.get('metadata', {}),
                            'conversation_id': data.get('conversation_id')
                        }
                        logger.info("SSE streaming completed")
                        break
                    elif event_type == 'error':
                        # Error occurred
                        logger.error(f"Dify error: {data.get('message')}")
                        yield {
                            'type': 'error',
                            'message': data.get('message', 'Unknown error')
                        }
                        break
                    elif event_type == 'agent_message' or event_type == 'agent_thought':
                        # Agent events (optional to show)
                        yield {
                            'type': event_type,
                            'content': data.get('thought', '') or data.get('message', ''),
                            'conversation_id': data.get('conversation_id')
                        }
                    else:
                        # Other event types - yield as-is but add type if missing
                        if 'type' not in data:
                            data['type'] = event_type or 'unknown'
                        yield data
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse SSE data: {event.data[:100]}... Error: {str(e)}")
                    # Try to yield as plain text
                    yield {
                        'type': 'text',
                        'content': event.data
                    }
                    continue
                except Exception as e:
                    logger.error(f"Error processing SSE event: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing SSE stream: {str(e)}")
            yield {
                'type': 'error',
                'message': str(e)
            }
    
    def chat(self, 
             query: str, 
             user_id: str,
             conversation_id: Optional[str] = None,
             inputs: Optional[Dict[str, Any]] = None,
             streaming: bool = True) -> Any:
        """
        Complete chat workflow: send request and process response
        
        Args:
            query: User message
            user_id: User identifier
            conversation_id: Optional conversation ID
            inputs: Optional additional inputs
            streaming: Whether to use streaming
            
        Returns:
            Processed response or generator
        """
        response_mode = "streaming" if streaming else "blocking"
        response = self.send_request(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            inputs=inputs,
            response_mode=response_mode
        )
        return self.process_response(response, streaming=streaming)


# Example usage
if __name__ == "__main__":
    # Example 1: n8n Webhook with streaming
    print("=== n8n Example ===")
    n8n_agent = N8nAgent(
        webhook_url="https://your-n8n-instance.com/webhook/your-workflow-id",
        api_key="your_api_key_if_needed"
    )
    
    try:
        # Send request and get streaming response
        stream = n8n_agent.run_workflow(
            workflow_data={
                "message": "Hello, how are you?",
                "user_id": "user_123"
            },
            stream=True
        )
        
        # Process streaming chunks
        for chunk in stream:
            print(f"n8n chunk: {chunk}")
    except Exception as e:
        print(f"n8n error: {str(e)}")
    finally:
        n8n_agent.close()
    
    print("\n=== Dify Example ===")
    # Example 2: Dify SSE API
    dify_agent = DifyAgent(
        api_url="https://api.dify.ai/v1/chat-messages",
        api_key="your_dify_api_key"
    )
    
    try:
        # Send chat request with streaming
        stream = dify_agent.chat(
            query="What is artificial intelligence?",
            user_id="user_123",
            streaming=True
        )
        
        # Process SSE events
        for event in stream:
            if event['type'] == 'message':
                print(f"Dify message: {event['content']}")
            elif event['type'] == 'end':
                print(f"Dify conversation ended: {event['conversation_id']}")
            elif event['type'] == 'error':
                print(f"Dify error: {event['message']}")
    except Exception as e:
        print(f"Dify error: {str(e)}")
    finally:
        dify_agent.close()