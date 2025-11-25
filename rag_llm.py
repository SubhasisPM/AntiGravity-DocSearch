"""
RAG LLM Integration Module
Supports multiple LLM providers: OpenAI, Google Gemini, and Local (Ollama)
"""

import os
import logging
from typing import List, Dict, Optional, Generator
from enum import Enum

logging.basicConfig(level=logging.INFO)


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    MOCK = "mock"  # For testing without API


class RAGLLMIntegration:
    """
    LLM Integration for RAG System
    Supports OpenAI, Gemini, and local Ollama models
    """
    
    def __init__(
        self,
        provider: str = "gemini",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ):
        """
        Initialize LLM integration
        
        Args:
            provider: "openai", "gemini", "ollama", or "mock"
            api_key: API key for cloud providers
            model: Specific model name
            temperature: Response creativity (0-1)
            max_tokens: Maximum response length
        """
        self.provider = LLMProvider(provider.lower())
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Set default models
        self.model = model or self._get_default_model()
        
        # Initialize the appropriate client
        self.client = None
        self._initialize_client()
        
        logging.info(f"LLM Integration initialized: {self.provider.value} ({self.model})")
    
    def _get_default_model(self) -> str:
        """Get default model for each provider"""
        defaults = {
            LLMProvider.OPENAI: "gpt-4-turbo-preview",
            LLMProvider.GEMINI: "gemini-pro",
            LLMProvider.OLLAMA: "llama2",
            LLMProvider.MOCK: "mock-model"
        }
        return defaults.get(self.provider, "gpt-4")
    
    def _initialize_client(self):
        """Initialize the LLM client based on provider"""
        try:
            if self.provider == LLMProvider.OPENAI:
                self._init_openai()
            elif self.provider == LLMProvider.GEMINI:
                self._init_gemini()
            elif self.provider == LLMProvider.OLLAMA:
                self._init_ollama()
            elif self.provider == LLMProvider.MOCK:
                self._init_mock()
        except Exception as e:
            logging.error(f"Failed to initialize {self.provider.value}: {e}")
            # Fallback to mock for development
            self.provider = LLMProvider.MOCK
            self._init_mock()
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            import openai
            if not self.api_key:
                raise ValueError("OpenAI API key required")
            openai.api_key = self.api_key
            self.client = openai
            logging.info("OpenAI client initialized")
        except ImportError:
            logging.error("openai package not installed. Run: pip install openai")
            raise
    
    def _init_gemini(self):
        """Initialize Google Gemini client"""
        try:
            import google.generativeai as genai
            if not self.api_key:
                raise ValueError("Gemini API key required")
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
            logging.info("Gemini client initialized")
        except ImportError:
            logging.error("google-generativeai package not installed. Run: pip install google-generativeai")
            raise
    
    def _init_ollama(self):
        """Initialize Ollama client (local)"""
        try:
            import ollama
            self.client = ollama
            logging.info("Ollama client initialized (local)")
        except ImportError:
            logging.error("ollama package not installed. Run: pip install ollama")
            raise
    
    def _init_mock(self):
        """Initialize mock client for testing"""
        self.client = "mock"
        logging.warning("Using MOCK LLM - for testing only!")
    
    def generate_answer(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
        stream: bool = False
    ) -> str:
        """
        Generate answer using RAG context
        
        Args:
            query: User's question
            context: Retrieved context from documents
            system_prompt: Optional system instructions
            stream: Whether to stream the response
            
        Returns:
            Generated answer
        """
        if not query or not context:
            return "I don't have enough information to answer that question."
        
        # Build the prompt
        prompt = self._build_rag_prompt(query, context, system_prompt)
        
        # Generate based on provider
        if self.provider == LLMProvider.OPENAI:
            return self._generate_openai(prompt, stream)
        elif self.provider == LLMProvider.GEMINI:
            return self._generate_gemini(prompt, stream)
        elif self.provider == LLMProvider.OLLAMA:
            return self._generate_ollama(prompt, stream)
        else:  # MOCK
            return self._generate_mock(prompt)
    
    def _build_rag_prompt(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Build RAG prompt with context"""
        default_system = """You are a helpful AI assistant that answers questions based on provided context.

INSTRUCTIONS:
1. Answer the question using ONLY the information in the context
2. If the context doesn't contain the answer, say so clearly
3. Cite sources using [Document Name, Page X] format
4. Be concise but comprehensive
5. Use bullet points for multiple items
6. Maintain a professional, executive-ready tone"""
        
        system = system_prompt or default_system
        
        prompt = f"""{system}

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:"""
        
        return prompt
    
    def _generate_openai(self, prompt: str, stream: bool = False) -> str:
        """Generate answer using OpenAI"""
        try:
            response = self.client.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=stream
            )
            
            if stream:
                return self._stream_openai(response)
            else:
                return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"OpenAI generation error: {e}")
            return f"Error generating answer: {str(e)}"
    
    def _generate_gemini(self, prompt: str, stream: bool = False) -> str:
        """Generate answer using Gemini"""
        try:
            response = self.client.generate_content(
                prompt,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_tokens
                },
                stream=stream
            )
            
            if stream:
                return self._stream_gemini(response)
            else:
                return response.text.strip()
        except Exception as e:
            logging.error(f"Gemini generation error: {e}")
            return f"Error generating answer: {str(e)}"
    
    def _generate_ollama(self, prompt: str, stream: bool = False) -> str:
        """Generate answer using Ollama (local)"""
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                },
                stream=stream
            )
            
            if stream:
                return self._stream_ollama(response)
            else:
                return response['response'].strip()
        except Exception as e:
            logging.error(f"Ollama generation error: {e}")
            return f"Error generating answer: {str(e)}"
    
    def _generate_mock(self, prompt: str) -> str:
        """Generate mock answer for testing"""
        return f"""Based on the provided context, here's a mock answer to your question.

**Key Points:**
• This is a simulated response for testing
• Real LLM integration requires API keys
• Configure OpenAI, Gemini, or Ollama for production

**Sources:** [Mock Document, Page 1]

*Note: This is a MOCK response. Configure a real LLM provider for actual answers.*"""
    
    def _stream_openai(self, response) -> Generator[str, None, None]:
        """Stream OpenAI response"""
        for chunk in response:
            if chunk.choices[0].delta.get("content"):
                yield chunk.choices[0].delta.content
    
    def _stream_gemini(self, response) -> Generator[str, None, None]:
        """Stream Gemini response"""
        for chunk in response:
            yield chunk.text
    
    def _stream_ollama(self, response) -> Generator[str, None, None]:
        """Stream Ollama response"""
        for chunk in response:
            yield chunk['response']
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)"""
        # Rough estimate: 1 token ≈ 4 characters
        return len(text) // 4
    
    def truncate_context(
        self,
        context: str,
        max_context_tokens: int = 3000
    ) -> str:
        """Truncate context to fit within token limit"""
        estimated_tokens = self.estimate_tokens(context)
        
        if estimated_tokens <= max_context_tokens:
            return context
        
        # Truncate to fit
        char_limit = max_context_tokens * 4
        truncated = context[:char_limit]
        
        # Try to end at a sentence
        last_period = truncated.rfind('.')
        if last_period > char_limit * 0.8:  # If we can keep 80%+
            truncated = truncated[:last_period + 1]
        
        logging.warning(f"Context truncated from {estimated_tokens} to ~{max_context_tokens} tokens")
        return truncated + "\n\n[Context truncated due to length...]"


# Convenience function
def create_llm(
    provider: str = "gemini",
    api_key: Optional[str] = None,
    **kwargs
) -> RAGLLMIntegration:
    """
    Create LLM integration instance
    
    Args:
        provider: "openai", "gemini", "ollama", or "mock"
        api_key: API key (or set via environment variable)
        **kwargs: Additional configuration
        
    Returns:
        RAGLLMIntegration instance
    """
    return RAGLLMIntegration(provider=provider, api_key=api_key, **kwargs)


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("RAG LLM Integration - Testing")
    print("=" * 80)
    
    # Test with mock provider (no API key needed)
    llm = create_llm(provider="mock")
    
    # Sample context
    context = """
    Customer churn rate is defined as the percentage of customers who stop 
    using a service during a given time period. [Q4 Analytics Report, Page 23]
    
    Our analysis shows a churn rate of 15% annually, which is higher than 
    the industry average of 12%. [Q4 Analytics Report, Page 23]
    
    The primary reasons for customer churn include poor customer service (35%), 
    high pricing (28%), and lack of features (22%). [Customer Feedback Analysis, Page 8]
    """
    
    # Generate answer
    query = "What is our customer churn rate and why are customers leaving?"
    answer = llm.generate_answer(query, context)
    
    print(f"\nQuery: {query}")
    print(f"\nAnswer:\n{answer}")
    print("\n" + "=" * 80)
    print("Test completed successfully")
    print("=" * 80)
    
    print("\nTo use real LLMs:")
    print("1. OpenAI: export OPENAI_API_KEY='your-key' && python rag_llm.py")
    print("2. Gemini: export GEMINI_API_KEY='your-key' && python rag_llm.py")
    print("3. Ollama: Install Ollama locally and run: python rag_llm.py")
