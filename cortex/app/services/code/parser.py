import logging
import uuid
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy imports for tree-sitter language bindings
# These may fail if native bindings are not properly built
_tree_sitter_available = False
_Language = None
_Parser = None
_languages = {}

def _load_tree_sitter():
    """Lazy load tree-sitter and language bindings with graceful fallback."""
    global _tree_sitter_available, _Language, _Parser, _languages
    
    if _tree_sitter_available:
        return True
    
    try:
        from tree_sitter import Language, Parser
        _Language = Language
        _Parser = Parser
    except ImportError as e:
        logger.warning(f"tree-sitter core not available: {e}")
        return False
    
    # Try to load each language binding
    language_modules = {
        "python": ("tree_sitter_python", "language"),
        "javascript": ("tree_sitter_javascript", "language"),
        "typescript": ("tree_sitter_typescript", "language_typescript"),
        "go": ("tree_sitter_go", "language"),
        "rust": ("tree_sitter_rust", "language"),
    }
    
    for lang_name, (module_name, func_name) in language_modules.items():
        try:
            import importlib
            mod = importlib.import_module(module_name)
            lang_func = getattr(mod, func_name)
            _languages[lang_name] = _Language(lang_func())
            logger.info(f"Loaded tree-sitter binding for {lang_name}")
        except Exception as e:
            logger.warning(f"tree-sitter binding for {lang_name} not available: {e}")
    
    _tree_sitter_available = len(_languages) > 0
    if _tree_sitter_available:
        logger.info(f"Tree-sitter initialized with {len(_languages)} language(s)")
    else:
        logger.warning("No tree-sitter language bindings available - code parsing disabled")
    
    return _tree_sitter_available


# Schemas
from app.schemas.code import CodeChunk


class CodeParser:
    """
    Parses code files into logical chunks using Tree-sitter.
    """
    
    SUPPORTED_LANGUAGES = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
    }
    
    def __init__(self):
        self._parsers = {}
        # Attempt to load tree-sitter on init
        _load_tree_sitter()

    def _get_parser(self, lang_name: str):
        """Lazy load parsers."""
        if not _tree_sitter_available:
            return None
            
        if lang_name not in self._parsers:
            if lang_name not in _languages:
                logger.warning(f"Language {lang_name} not available")
                return None
            
            try:
                parser = _Parser()
                parser.language = _languages[lang_name]
                self._parsers[lang_name] = parser
            except Exception as e:
                logger.error(f"Failed to create parser for {lang_name}: {e}")
                return None
                
        return self._parsers.get(lang_name)

    def parse_file(
        self,
        content: str,
        filename: str,
        workspace_id: str,
        layer_id: str,
        document_id: str,
    ) -> List[CodeChunk]:
        """
        Parse a file into CodeChunks.
        """
        ext = Path(filename).suffix
        lang_name = self.SUPPORTED_LANGUAGES.get(ext)
        
        if not lang_name:
            logger.warning(f"Unsupported language extension: {ext}")
            return []
            
        parser = self._get_parser(lang_name)
        if not parser:
            # Graceful degradation - return empty list instead of crashing
            logger.debug(f"Parser not available for {lang_name}, skipping file {filename}")
            return []
            
        tree = parser.parse(bytes(content, "utf8"))
        root_node = tree.root_node
        
        chunks = []
        
        # Recursive walk to find Classes and Functions
        self._walk_node(root_node, chunks, content, lang_name, filename, workspace_id, layer_id, document_id)
        
        return chunks

    def _walk_node(
        self,
        node,
        chunks: List[CodeChunk],
        source_code: str,
        language: str,
        filename: str,
        workspace_id: str,
        layer_id: str,
        document_id: str,
        parent_id: Optional[str] = None
    ):
        """Recursively extract relevant nodes."""
        
        node_type = node.type
        is_relevant = False
        chunk_type = "block"
        chunk_name = "anonymous"
        
        # 1. Identify Node Type (simplified mapping)
        if node_type in ["class_definition", "class_declaration"]:
            is_relevant = True
            chunk_type = "class"
            chunk_name = self._get_node_name(node, source_code)
            
        elif node_type in ["function_definition", "function_declaration", "method_definition", "method_declaration"]:
            is_relevant = True
            chunk_type = "function"
            chunk_name = self._get_node_name(node, source_code)

        # 2. Extract Chunk if relevant
        current_id = parent_id
        if is_relevant:
            start_line = node.start_point.row + 1
            end_line = node.end_point.row + 1
            
            # Extract content (bytes -> str)
            code_bytes = node.text
            chunk_content = code_bytes.decode("utf8")
            
            # Generate ID
            current_id = str(uuid.uuid4())
            
            # Breadcrumb Header
            header = f"File: {filename} > {chunk_type.title()}: {chunk_name}"
            enriched_content = f"{header}\n\n{chunk_content}"
            
            chunk = CodeChunk(
                id=current_id,
                content=enriched_content,
                embedding=[], # To be filled by embedding service
                document_id=document_id,
                workspace_id=workspace_id,
                layer_id=layer_id,
                visibility="private", # Default code visibility
                node_type=chunk_type,
                language=language,
                start_line=start_line,
                end_line=end_line,
                file_path=filename,
                parent_id=parent_id,
                signature=chunk_name, # Simplified signature
                metadata={"raw_name": chunk_name}
            )
            chunks.append(chunk)
            
        # 3. Recurse
        for child in node.children:
            self._walk_node(
                child, 
                chunks, 
                source_code, 
                language, 
                filename, 
                workspace_id, 
                layer_id, 
                document_id, 
                parent_id=current_id if is_relevant else parent_id
            )

    def _get_node_name(self, node, source_code: str) -> str:
        """Extract identifier from node."""
        # Most languages usage: (class_def name: (identifier))
        child_by_name = node.child_by_field_name("name")
        if child_by_name:
            return child_by_name.text.decode("utf8")
            
        # Fallback: scan children for 'identifier' type
        for child in node.children:
            if child.type == "identifier" or child.type == "type_identifier":
                return child.text.decode("utf8")
                
        return "anonymous"

# Singleton
_code_parser = None

def get_code_parser() -> CodeParser:
    global _code_parser
    if _code_parser is None:
        _code_parser = CodeParser()
    return _code_parser
