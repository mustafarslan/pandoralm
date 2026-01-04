from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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

            # Simulate streaming generation
            answer = context.content
            chunk_size = 50
            for i in range(0, len(answer), chunk_size):
                yield StreamProtocol.text_chunk(answer[i:i+chunk_size])
            
    except Exception as e:
        yield StreamProtocol.error_chunk(str(e))
