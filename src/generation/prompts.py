"""
Prompt templates for RAG-based answer generation.

This module provides prompt templates that structure the context and question
for the LLM, ensuring proper citation format and factual accuracy.
"""

from src.generation.models import ContextChunk


def build_rag_prompt(question: str, context_chunks: list[ContextChunk]) -> str:
    """
    Build RAG prompt with context chunks and citations.

    Creates a structured prompt that includes:
    - System instructions for factual, citation-based answers
    - Numbered context chunks with source metadata
    - User's question

    Args:
        question: User's question
        context_chunks: Retrieved chunks to use as context

    Returns:
        Formatted prompt string ready for LLM

    Example:
        >>> chunks = [
        ...     ContextChunk(text="ML is AI subset", filename="ml.pdf", page=1, score=0.95)
        ... ]
        >>> prompt = build_rag_prompt("What is ML?", chunks)
    """
    # Build context section with citations
    context_parts = []
    for i, chunk in enumerate(context_chunks, start=1):
        source_info = f"Source: {chunk.filename}"
        if chunk.page is not None:
            source_info += f", Page: {chunk.page}"

        context_parts.append(f"[{i}] {chunk.text}\n({source_info})")

    context_text = "\n\n".join(context_parts) if context_parts else "No context available."

    # Build full prompt
    prompt = f"""You are an educational AI assistant helping students learn.

IMPORTANT INSTRUCTIONS:
- Answer using ONLY the provided context below
- Include citations [1], [2], etc. for each fact you mention
- If the context doesn't contain enough information to answer the question, say so clearly
- Be concise but complete
- Use a teaching tone that encourages understanding

Context:
{context_text}

Question: {question}

Answer:"""

    return prompt


def build_system_message() -> str:
    """
    Build system message for chat-based models.

    Returns:
        System message string
    """
    return """You are an educational AI assistant helping students learn.

Your role:
- Answer questions using ONLY the provided context
- Include citations [1], [2] for each fact
- If context is insufficient, say so clearly
- Be concise but complete
- Use a teaching tone that encourages understanding"""


def build_user_message(question: str, context_chunks: list[ContextChunk]) -> str:
    """
    Build user message with context and question.

    Args:
        question: User's question
        context_chunks: Retrieved chunks to use as context

    Returns:
        Formatted user message
    """
    # Build context section
    context_parts = []
    for i, chunk in enumerate(context_chunks, start=1):
        source_info = f"Source: {chunk.filename}"
        if chunk.page is not None:
            source_info += f", Page: {chunk.page}"

        context_parts.append(f"[{i}] {chunk.text}\n({source_info})")

    context_text = "\n\n".join(context_parts) if context_parts else "No context available."

    return f"""Context:
{context_text}

Question: {question}"""
