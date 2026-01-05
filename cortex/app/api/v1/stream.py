from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json
import os

from app.services.graphrag import get_query_router, QueryMode
from app.services.agent.agent import ResearchAgent
from app.auth.keycloak import verifier
from app.api.protocols.vercel import StreamProtocol

router = APIRouter()

class StreamRequest(BaseModel):
    query: str
    workspace_id: str
    mode: str = "auto" # vector, graph, hybrid, research, auto

@router.post("/chat", dependencies=[Depends(verifier.verify_token)])
async def stream_chat(request: StreamRequest):
    """
    Stream chat response using Vercel AI SDK Data Stream Protocol.
    """
    return StreamingResponse(
        event_generator(request),
        media_type="text/plain"  # Vercel SDK often expects text/plain or x-ndjson
    )

async def event_generator(request: StreamRequest):
    """
    Yields chunks formatted for Vercel AI SDK.
    """
    try:
        # 1. Initialize logic
        query_router = get_query_router()
        
        # 2. Determine Mode
        mode = request.mode
        if mode == "auto":
            detection_mode, _ = await query_router._detect_query_mode_llm(request.query)
            mode = detection_mode.value
        
        # Yield Thought as Text (or specific UI component if preferred)
        # For now, we prepend it as a "Thinking" message or structured data?
        # Let's use Data to trigger a "Thinking" UI state if frontend supports it, 
        # but standardized text is safer for basic implementation.
        # "0" is text. We can clearly mark thoughts.
        yield StreamProtocol.data_chunk([{
            "type": "thought", 
            "content": f"Selected mode: {mode.upper()}"
        }])

        # 3. Execution
        if mode == "research":
            yield StreamProtocol.text_chunk("Initiating Deep Research...\n")
            agent = ResearchAgent()
            # Adapter for existing agent stream (assuming it yields objects)
            async for event in agent.execute_stream(request.query):
                # Map internal event to protocol
                if event.event.value == "thought":
                    yield StreamProtocol.data_chunk([{"type": "thought", "content": event.data.get("content")}])
                elif event.event.value == "token":
                    yield StreamProtocol.text_chunk(event.data.get("text", ""))
                
        else:
            yield StreamProtocol.data_chunk([{"type": "thought", "content": "Retrieving context..."}])
            
            q_mode = QueryMode.HYBRID
            if mode == "vector": q_mode = QueryMode.VECTOR
            elif mode == "graph": q_mode = QueryMode.GRAPH
            
            context = await query_router.route_query(
                query=request.query,
                workspace_id=request.workspace_id,
                mode=q_mode,
                use_cognitive_router=False
            )
            
            # --- Generative UI Triggers (Phase 3) ---
            
            # 1. Meeting Intelligence
            # Scan sources for meeting metadata to trigger the Side Panel Player
            seen_meetings = set()
            for source in context.sources:
                meta = source.get("metadata", {})
                if meta and meta.get("source_type") == "meeting":
                    file_id = meta.get("file_id") or source.get("document_id")
                    
                    # Avoid duplicate triggers for the same meeting
                    if file_id and file_id not in seen_meetings:
                        seen_meetings.add(file_id)
                        yield StreamProtocol.meeting_ref(
                            file_id=file_id,
                            timestamp=meta.get("start_time", 0.0), # Use proper timestamp field
                            title=meta.get("meeting_title", "Meeting Recording")
                        )

            # 2. Graph Visualization
            # Trigger Force Graph if we have substantial entities and are in a thematic mode
            if context.entities:
                nodes = [{"id": e["name"], "group": 1, "label": e.get("type", "Entity")} for e in context.entities[:15]]
                yield StreamProtocol.graph_viz(
                    nodes=nodes,
                    edges=[], # TODO: Extract edges from GraphStore response in Phase 3.1
                    title=f"Knowledge Graph Context ({len(nodes)} Nodes)"
                )
            
            # --------------------------------------

            # --- Glass Box LLM Response Generation (RAG) ---
            yield StreamProtocol.thought("GENERATION", "Synthesizing answer from context...", "SYSTEM_2")
            
            # Build numbered source context for citations
            numbered_sources = []
            for idx, source in enumerate(context.sources, 1):
                source_text = source.get("content", "")[:500]
                numbered_sources.append(f"[{idx}] {source_text}")
            
            context_with_citations = "\n\n".join(numbered_sources) if numbered_sources else context.content[:8000]
            
            # Enhanced RAG prompt with citation instructions
            system_prompt = """You are PandoraLM, a transparent AI assistant that explains its reasoning.

IMPORTANT: Before answering, ALWAYS show your step-by-step reasoning inside <think></think> tags.
This helps users understand HOW you arrived at your answer.

INSTRUCTIONS:
1. First, analyze the context in <think> tags - identify key facts, connections, and relevance to the question.
2. Answer the user's question primarily based on the provided context.
3. When citing information, use the format [1], [2], etc. to reference specific sources.
4. If the provided context is not relevant or sufficient, answer based on your general knowledge, but explicitly mention that the answer is not from the provided context sources.
5. Be concise but comprehensive.
6. Use markdown formatting for clarity (headers, bullet points, bold for key terms).

OUTPUT FORMAT:
<think>
[Your reasoning process here - analyze the question, identify relevant sources, plan your answer]
</think>

[Your actual answer with citations]"""
            
            user_prompt = f"""## Context Sources:
{context_with_citations}

## User Question:
{request.query}

## Your Response (with citations):"""
            
            # Call Ollama for generation
            ollama_url = os.getenv("LLM_SOLVER_API_BASE", "http://host.docker.internal:11434")
            model = os.getenv("LLM_SOLVER_MODEL", "deepseek-r1:8b")
            
            # State machine for parsing <think> blocks
            buffer = ""
            in_think_block = False
            think_content = ""
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST",
                    f"{ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": user_prompt,
                        "system": system_prompt,
                        "stream": True,
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    token = data["response"]
                                    buffer += token
                                    
                                    # Parse <think> blocks for Glass Box transparency
                                    while True:
                                        if not in_think_block:
                                            # Look for opening <think> tag
                                            if "<think>" in buffer:
                                                idx = buffer.index("<think>")
                                                # Emit any text before the tag
                                                if idx > 0:
                                                    yield StreamProtocol.text_chunk(buffer[:idx])
                                                buffer = buffer[idx + 7:]  # Skip <think>
                                                in_think_block = True
                                                think_content = ""
                                            else:
                                                # No tag found, emit buffer (keeping last 10 chars for partial tag detection)
                                                if len(buffer) > 10:
                                                    yield StreamProtocol.text_chunk(buffer[:-10])
                                                    buffer = buffer[-10:]
                                                break
                                        else:
                                            # Inside think block, look for closing </think>
                                            if "</think>" in buffer:
                                                idx = buffer.index("</think>")
                                                think_content += buffer[:idx]
                                                buffer = buffer[idx + 8:]  # Skip </think>
                                                in_think_block = False
                                                # Emit thought as Glass Box event
                                                yield StreamProtocol.thought("REASONING", think_content.strip(), "SYSTEM_2")
                                            else:
                                                # Accumulate think content
                                                think_content += buffer
                                                buffer = ""
                                                break
                                                
                            except json.JSONDecodeError:
                                continue
                    
                    # Flush remaining buffer
                    if buffer and not in_think_block:
                        yield StreamProtocol.text_chunk(buffer)
            
            # --- Emit Citations ---
            if context.sources:
                # yield StreamProtocol.thought("CITATIONS", f"Found {len(context.sources)} source documents", "SYSTEM_1")
                for idx, source in enumerate(context.sources[:5], 1):
                    yield StreamProtocol.citation(
                        source_id=source.get("document_id", f"source-{idx}"),
                        text=source.get("content", "")[:150] + "...",
                        page=None
                    )
            
    except Exception as e:
        yield StreamProtocol.error_chunk(str(e))

