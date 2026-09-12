import os
import json
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import logging

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_code(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        pass
    
    @abstractmethod
    async def chat(self, messages: list, system_prompt: str) -> str:
        pass

class GeminiProvider(LLMProvider):
    """Google Gemini API provider"""
    
    def __init__(self, api_key: str):
        if not genai:
            raise ImportError("google-generativeai not installed")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    async def generate_code(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        system_prompt = """You are an expert CAD designer and Python programmer. 
Generate CadQuery/Build123d Python code to create 3D models based on text descriptions.
Return ONLY valid Python code, no explanations.

Example format:
from build123d import *

with BuildPart() as bp:
    Box(10, 10, 10)
"""
        
        full_prompt = f"{system_prompt}\n\nUser request: {prompt}"
        if context:
            full_prompt += f"\n\nContext: {json.dumps(context)}"
        
        try:
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    async def chat(self, messages: list, system_prompt: str) -> str:
        try:
            chat_session = self.model.start_chat()
            response = chat_session.send_message(messages[-1]['content'])
            return response.text
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            raise

class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self, api_key: str):
        if not OpenAI:
            raise ImportError("openai not installed")
        self.client = OpenAI(api_key=api_key)
    
    async def generate_code(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        system_prompt = """You are an expert CAD designer and Python programmer.
Generate CadQuery/Build123d Python code to create 3D models based on text descriptions.
Return ONLY valid Python code, no explanations."""
        
        full_prompt = prompt
        if context:
            full_prompt += f"\n\nContext: {json.dumps(context)}"
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def chat(self, messages: list, system_prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": system_prompt}] + messages,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise

class LLMEngine:
    """Main LLM orchestration engine"""
    
    def __init__(self):
        provider_name = os.getenv("LLM_PROVIDER", "gemini").lower()
        
        if provider_name == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set")
            self.provider = GeminiProvider(api_key)
        elif provider_name == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self.provider = OpenAIProvider(api_key)
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
        
        logger.info(f"LLM Engine initialized with {provider_name} provider")
    
    async def generate_cad_code(self, description: str, design_history: Optional[list] = None) -> str:
        """Generate CAD Python code from natural language description"""
        context = {}
        if design_history:
            context["previous_designs"] = design_history[-3:]  # Last 3 iterations
        
        return await self.provider.generate_code(description, context)
    
    async def process_chat_message(self, messages: list, system_prompt: str) -> str:
        """Process chat messages"""
        return await self.provider.chat(messages, system_prompt)
