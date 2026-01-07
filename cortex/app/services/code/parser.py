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
    
    # Try loading via tree-sitter-languages (Preferred)
    try:
        from tree_sitter_languages import get_language
        for lang in ["python", "javascript", "typescript", "go", "rust"]:
            try:
                _languages[lang] = get_language(lang)
                logger.info(f"Loaded {lang} via tree-sitter-languages")
            except Exception as e:
                logger.warning(f"Failed to load {lang} via tree-sitter-languages: {e}")
                
        if _languages:
            _tree_sitter_available = True
            return True
    except ImportError:
        logger.debug("tree-sitter-languages not found, falling back to manual loading")

    # Try to load each language binding manually
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
            try:
                # API change in tree-sitter 0.22+: Language(ptr, name)
                _languages[lang_name] = _Language(lang_func(), lang_name)
            except TypeError:
                # Legacy API: Language(ptr)
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
                parser.set_language(_languages[lang_name])
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

    def _extract_imports(self, root_node, language: str, source_code: str) -> List[str]:
        """Extract imported modules."""
        imports = []
        
        # Simplified query for imports based on language
        if language == "python":
            for node in root_node.children:
                if node.type == "import_statement":
                    # import x, y
                    for child in node.children:
                        if child.type == "dotted_name":
                            imports.append(child.text.decode("utf8"))
                elif node.type == "import_from_statement":
                    # from x import y
                    module_name = node.child_by_field_name("module_name")
                    if module_name:
                        imports.append(module_name.text.decode("utf8"))
                        
        elif language in ["javascript", "typescript"]:
            for node in root_node.children:
                if node.type == "import_statement":
                    # import { x } from "y"
                    source = node.child_by_field_name("source")
                    if source:
                        # Remove quotes
                        raw_source = source.text.decode("utf8")
                        imports.append(raw_source.strip("'\""))
                        
        return list(set(imports))

    def _extract_bases(self, node, language: str, source_code: str) -> List[str]:
        """Extract base classes."""
        bases = []
        if language == "python":
            # class Foo(Bar, Baz):
            args = node.child_by_field_name("superclasses") or node.child_by_field_name("argument_list")
            if args:
                for child in args.children:
                    if child.type in ["identifier", "attribute", "call"]:
                        bases.append(child.text.decode("utf8"))
                        
        elif language in ["javascript", "typescript"]:
            # class Foo extends Bar
            heritage = node.child_by_field_name("class_heritage")
            if heritage:
                for child in heritage.children:
                    if child.type == "extends_clause":
                        # extends Bar
                        for grandchild in child.children:
                            if grandchild.type == "identifier":
                                bases.append(grandchild.text.decode("utf8"))
                                
        return bases

    def _extract_calls(self, node, language: str, source_code: str) -> List[str]:
        """Extract function calls from body."""
        calls = []
        
        # Simple recursive walker for calls
        def walk_for_calls(curr):
            if language == "python":
                if curr.type == "call":
                    func_node = curr.child_by_field_name("function")
                    if func_node:
                        # Handle methods: self.foo() -> foo
                        if func_node.type == "attribute":
                            attr = func_node.child_by_field_name("attribute")
                            if attr:
                                calls.append(attr.text.decode("utf8"))
                        else:
                            calls.append(func_node.text.decode("utf8"))
                            
            elif language in ["javascript", "typescript"]:
                if curr.type == "call_expression":
                    func_node = curr.child_by_field_name("function")
                    if func_node:
                        # Handle method calls: obj.method() -> method
                        if func_node.type == "member_expression":
                            prop = func_node.child_by_field_name("property")
                            if prop:
                                calls.append(prop.text.decode("utf8"))
                        else:
                            calls.append(func_node.text.decode("utf8"))
            
            for child in curr.children:
                walk_for_calls(child)
                
        # Walk the body/block of the function
        body = node.child_by_field_name("body")
        if body:
            walk_for_calls(body)
            
        return list(set(calls))

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
        parent_id: Optional[str] = None,
        file_imports: Optional[List[str]] = None
    ):
        """Recursively extract relevant nodes."""
        
        node_type = node.type
        is_relevant = False
        chunk_type = "block"
        chunk_name = "anonymous"
        metadata = {}
        
        # Top level file imports (passed down)
        if file_imports is None and parent_id is None:
             file_imports = self._extract_imports(node, language, source_code)

        # 1. Identify Node Type (simplified mapping)
        if node_type in ["class_definition", "class_declaration"]:
            is_relevant = True
            chunk_type = "class"
            chunk_name = self._get_node_name(node, source_code)
            metadata["bases"] = self._extract_bases(node, language, source_code)
            metadata["raw_name"] = chunk_name
            # Attach imports to class level chunks as they are top-level context
            if file_imports:
                metadata["imports"] = file_imports
            
        elif node_type in ["function_definition", "function_declaration", "method_definition", "method_declaration"]:
            is_relevant = True
            chunk_type = "function"
            chunk_name = self._get_node_name(node, source_code)
            metadata["calls"] = self._extract_calls(node, language, source_code)
            metadata["raw_name"] = chunk_name
            # Provide imports for context here too if it's a top level function
            if file_imports and parent_id is None:
                metadata["imports"] = file_imports

        # 2. Extract Chunk if relevant
        current_id = parent_id
        if is_relevant:
            # Handle tree-sitter point types (tuple vs object)
            sp = node.start_point
            ep = node.end_point
            
            start_line = (sp[0] if isinstance(sp, tuple) else sp.row) + 1
            end_line = (ep[0] if isinstance(ep, tuple) else ep.row) + 1
            
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
                metadata=metadata
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
                parent_id=current_id if is_relevant else parent_id,
                file_imports=file_imports
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
