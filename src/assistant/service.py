"""Safety Copilot AI Assistant service."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import openai
except ImportError:
    openai = None


@dataclass
class AssistantQuery:
    """Query to the assistant."""
    
    question: str
    run_id: Optional[str] = None
    category: Optional[str] = None
    language: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class AssistantResponse:
    """Response from the assistant."""
    
    answer: str
    query: str
    context_used: Dict[str, Any]
    latency_ms: int
    model: str
    tokens_used: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "answer": self.answer,
            "query": self.query,
            "context_used": self.context_used,
            "latency_ms": self.latency_ms,
            "model": self.model,
            "tokens_used": self.tokens_used,
        }


class SafetyCopilot:
    """AI assistant for safety evaluation analysis.
    
    Helps users understand evaluation results and safety policies through
    natural language conversation powered by an LLM.
    """
    
    # System prompt for the assistant
    SYSTEM_PROMPT = """You are Safety Copilot, an AI assistant helping users understand AI content safety evaluations.

Your role is to:
1. Explain why content was flagged or not flagged
2. Describe safety categories and policies
3. Help users understand metrics (precision, recall, FNR, FPR)
4. Suggest ways to improve evaluation results
5. Answer questions about the safety evaluation system

Guidelines:
- Be concise but thorough
- Use simple language for technical concepts
- Reference specific metrics/data from the provided context
- Stay focused on content safety topics
- If asked about unrelated topics, politely redirect to safety evaluation
- Never provide instructions for creating harmful content
- Format responses with markdown for readability (bold, lists, code blocks)

Context will be provided for each question. Use it to give specific, accurate answers."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        max_tokens: int = 500,
        temperature: float = 0.7,
    ):
        """Initialize Safety Copilot.
        
        Args:
            api_key: OpenAI API key (required)
            model: Model to use (gpt-4, gpt-3.5-turbo, etc.)
            max_tokens: Max tokens in response
            temperature: Temperature for generation (0.0-1.0)
        """
        if openai is None:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        if not api_key:
            raise ValueError("OpenAI API key is required for Safety Copilot")
        
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = openai.OpenAI(api_key=api_key)
    
    def query(self, query: AssistantQuery, tenant_id: str) -> AssistantResponse:
        """Answer a user query.
        
        Args:
            query: User query
            tenant_id: Tenant ID
            
        Returns:
            AssistantResponse
        """
        start_time = time.perf_counter()
        
        # Gather context
        from .context import gather_context
        
        context_data = gather_context(
            tenant_id=tenant_id,
            run_id=query.run_id
        )
        
        # Add query-specific context
        if query.category:
            context_data["query_category"] = query.category
        if query.language:
            context_data["query_language"] = query.language
        if query.context:
            context_data.update(query.context)
        
        # Build messages
        messages = self._build_messages(query.question, context_data)
        
        # Moderate question first
        if not self._is_question_safe(query.question):
            return AssistantResponse(
                answer="I can only answer questions about content safety evaluation. Please ask a question related to safety policies, evaluation results, or metrics.",
                query=query.question,
                context_used=context_data,
                latency_ms=int((time.perf_counter() - start_time) * 1000),
                model=self.model,
            )
        
        # Call LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            answer = response.choices[0].message.content or "No response generated"
            tokens_used = response.usage.total_tokens if response.usage else None
            
            logger.info(f"Assistant query answered in {latency_ms}ms, {tokens_used} tokens")
            
            return AssistantResponse(
                answer=answer,
                query=query.question,
                context_used=context_data,
                latency_ms=latency_ms,
                model=self.model,
                tokens_used=tokens_used,
            )
        
        except Exception as e:
            logger.error(f"Error querying LLM: {e}")
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            return AssistantResponse(
                answer=f"I encountered an error processing your question: {str(e)}",
                query=query.question,
                context_used=context_data,
                latency_ms=latency_ms,
                model=self.model,
            )
    
    def _build_messages(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Build messages for LLM.
        
        Args:
            question: User question
            context: Context data
            
        Returns:
            List of messages
        """
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        
        # Add context as user message
        context_text = self._format_context(context)
        if context_text:
            messages.append({
                "role": "user",
                "content": f"Context:\n\n{context_text}"
            })
        
        # Add user question
        messages.append({
            "role": "user",
            "content": f"Question: {question}"
        })
        
        return messages
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for LLM.
        
        Args:
            context: Context dictionary
            
        Returns:
            Formatted context string
        """
        parts = []
        
        if "policy" in context:
            parts.append(f"Policy Information:\n{context['policy']}")
        
        if "run" in context:
            parts.append(f"\nEvaluation Run:\n{context['run']}")
        
        if "query_category" in context:
            parts.append(f"\nQueried Category: {context['query_category']}")
        
        if "query_language" in context:
            parts.append(f"Queried Language: {context['query_language']}")
        
        return "\n".join(parts)
    
    def _is_question_safe(self, question: str) -> bool:
        """Check if question is safe and on-topic.
        
        Args:
            question: User question
            
        Returns:
            True if safe
        """
        # Simple keyword-based filtering
        # In production, could use moderation API
        
        question_lower = question.lower()
        
        # Check for safety-related keywords
        safety_keywords = [
            "safety", "flag", "policy", "category", "violence", "hate",
            "harassment", "evaluation", "score", "metric", "precision",
            "recall", "false positive", "false negative", "run", "result",
            "why", "how", "what", "explain", "analysis", "guard",
        ]
        
        # If question contains safety keywords, likely on-topic
        if any(keyword in question_lower for keyword in safety_keywords):
            return True
        
        # Check if question is very short (likely relevant)
        if len(question.split()) <= 3:
            return True
        
        # For longer questions without safety keywords, be cautious
        return True  # Default to allowing (LLM will redirect if needed)
    
    def health_check(self) -> bool:
        """Check if assistant is healthy.
        
        Returns:
            True if can connect to LLM
        """
        try:
            # Try a simple completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "test"}
                ],
                max_tokens=5,
            )
            return len(response.choices) > 0
        except Exception as e:
            logger.error(f"Assistant health check failed: {e}")
            return False


# Global copilot instance
_global_copilot: Optional[SafetyCopilot] = None


def get_copilot(
    api_key: Optional[str] = None,
    model: str = "gpt-4",
) -> SafetyCopilot:
    """Get global Safety Copilot instance.
    
    Args:
        api_key: OpenAI API key (uses env var if not provided)
        model: Model to use
        
    Returns:
        SafetyCopilot instance
    """
    global _global_copilot
    
    if _global_copilot is None:
        import os
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        _global_copilot = SafetyCopilot(
            api_key=api_key,
            model=model,
        )
    
    return _global_copilot


__all__ = ["SafetyCopilot", "AssistantQuery", "AssistantResponse", "get_copilot"]

