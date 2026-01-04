"""
VRAM Calculator
Estimates GPU memory requirements for LLM models before download
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import math


class Precision(str, Enum):
    """Model quantization/precision levels."""
    FP32 = "fp32"  # Full precision
    FP16 = "fp16"  # Half precision
    BF16 = "bf16"  # Brain float 16
    INT8 = "int8"  # 8-bit quantization
    INT4 = "int4"  # 4-bit quantization (GGUF Q4)
    Q4_K_M = "q4_k_m"  # GGUF K-quant
    Q5_K_M = "q5_k_m"  # GGUF K-quant
    Q6_K = "q6_k"  # GGUF K-quant
    Q8_0 = "q8_0"  # GGUF 8-bit


@dataclass
class ModelSpec:
    """Specification of a model for VRAM calculation."""
    name: str
    parameters_billions: float
    architecture: str = "transformer"
    context_length: int = 4096
    hidden_size: int = 4096
    num_layers: int = 32
    num_heads: int = 32
    vocab_size: int = 32000


@dataclass
class VRAMEstimate:
    """VRAM estimation result."""
    model_name: str
    precision: Precision
    model_size_gb: float
    kv_cache_gb: float
    overhead_gb: float
    total_vram_gb: float
    can_fit_gpus: List[str]
    warnings: List[str]
    
    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "precision": self.precision.value,
            "model_size_gb": round(self.model_size_gb, 2),
            "kv_cache_gb": round(self.kv_cache_gb, 2),
            "overhead_gb": round(self.overhead_gb, 2),
            "total_vram_gb": round(self.total_vram_gb, 2),
            "can_fit_gpus": self.can_fit_gpus,
            "warnings": self.warnings,
        }


# Known GPU VRAM capacities
GPU_VRAM = {
    "RTX 4090": 24,
    "RTX 4080": 16,
    "RTX 4070 Ti": 12,
    "RTX 4070": 12,
    "RTX 3090": 24,
    "RTX 3080 Ti": 12,
    "RTX 3080": 10,
    "A100 (40GB)": 40,
    "A100 (80GB)": 80,
    "H100": 80,
    "V100 (16GB)": 16,
    "V100 (32GB)": 32,
    "A10": 24,
    "T4": 16,
    "L4": 24,
    "Apple M1 Max": 32,
    "Apple M2 Max": 38,
    "Apple M3 Max": 48,
    "Apple M2 Ultra": 76,
    "Apple M3 Ultra": 128,
}

# Bytes per parameter by precision
BYTES_PER_PARAM = {
    Precision.FP32: 4.0,
    Precision.FP16: 2.0,
    Precision.BF16: 2.0,
    Precision.INT8: 1.0,
    Precision.INT4: 0.5,
    Precision.Q4_K_M: 0.5625,  # ~4.5 bits average
    Precision.Q5_K_M: 0.6875,  # ~5.5 bits average
    Precision.Q6_K: 0.8125,   # ~6.5 bits average
    Precision.Q8_0: 1.0,
}

# Known model specifications
KNOWN_MODELS: Dict[str, ModelSpec] = {
    # LLaMA family
    "llama-7b": ModelSpec("LLaMA 7B", 7, context_length=4096, hidden_size=4096, num_layers=32),
    "llama-13b": ModelSpec("LLaMA 13B", 13, context_length=4096, hidden_size=5120, num_layers=40),
    "llama-70b": ModelSpec("LLaMA 70B", 70, context_length=4096, hidden_size=8192, num_layers=80),
    
    # LLaMA 3
    "llama3-8b": ModelSpec("LLaMA 3 8B", 8, context_length=8192, hidden_size=4096, num_layers=32),
    "llama3-70b": ModelSpec("LLaMA 3 70B", 70, context_length=8192, hidden_size=8192, num_layers=80),
    
    # Mistral
    "mistral-7b": ModelSpec("Mistral 7B", 7, context_length=32768, hidden_size=4096, num_layers=32),
    "mixtral-8x7b": ModelSpec("Mixtral 8x7B", 47, context_length=32768, hidden_size=4096, num_layers=32),
    
    # GPT variants
    "gpt2": ModelSpec("GPT-2", 1.5, context_length=1024, hidden_size=1600, num_layers=48),
    "gpt-j-6b": ModelSpec("GPT-J 6B", 6, context_length=2048, hidden_size=4096, num_layers=28),
    
    # Qwen
    "qwen-7b": ModelSpec("Qwen 7B", 7, context_length=8192, hidden_size=4096, num_layers=32),
    "qwen-14b": ModelSpec("Qwen 14B", 14, context_length=8192, hidden_size=5120, num_layers=40),
    "qwen-72b": ModelSpec("Qwen 72B", 72, context_length=32768, hidden_size=8192, num_layers=80),
}


class VRAMCalculator:
    """
    Calculates GPU VRAM requirements for running LLM models.
    
    Components considered:
    1. Model weights
    2. KV cache (per token * context length)
    3. Activation memory
    4. CUDA/framework overhead
    """
    
    # Overhead multiplier for frameworks (PyTorch, CUDA, etc.)
    OVERHEAD_MULTIPLIER = 1.2  # 20% overhead
    
    # KV cache bytes per token per layer (for FP16)
    KV_BYTES_PER_TOKEN_LAYER = 256  # 2 * hidden_size / num_heads * 2 bytes
    
    def estimate_vram(
        self,
        model_name: str = None,
        parameters_billions: float = None,
        precision: Precision = Precision.FP16,
        context_length: int = 4096,
        batch_size: int = 1,
    ) -> VRAMEstimate:
        """
        Estimate VRAM requirements for a model.
        
        Args:
            model_name: Name of known model (optional)
            parameters_billions: Model size in billions of parameters
            precision: Quantization/precision level
            context_length: Maximum context length to support
            batch_size: Batch size for inference
            
        Returns:
            VRAMEstimate with detailed breakdown
        """
        warnings = []
        
        # Get model spec
        if model_name and model_name.lower() in KNOWN_MODELS:
            spec = KNOWN_MODELS[model_name.lower()]
            params = spec.parameters_billions
            if context_length > spec.context_length:
                warnings.append(
                    f"Requested context ({context_length}) exceeds model's "
                    f"max ({spec.context_length})"
                )
        elif parameters_billions:
            params = parameters_billions
            spec = None
        else:
            raise ValueError("Must provide model_name or parameters_billions")
        
        # Calculate model size
        bytes_per_param = BYTES_PER_PARAM[precision]
        model_size_bytes = params * 1e9 * bytes_per_param
        model_size_gb = model_size_bytes / (1024 ** 3)
        
        # Calculate KV cache size
        # KV cache = 2 * batch * layers * context * hidden_size * bytes_per_element
        if spec:
            num_layers = spec.num_layers
            hidden_size = spec.hidden_size
        else:
            # Estimate based on parameter count
            num_layers = int(math.sqrt(params * 1e9 / 12e6))  # Rough estimate
            hidden_size = int(math.sqrt(params * 1e9 * 12))
        
        kv_bytes_per_layer = 2 * batch_size * context_length * hidden_size * 2  # FP16
        kv_cache_bytes = kv_bytes_per_layer * num_layers
        kv_cache_gb = kv_cache_bytes / (1024 ** 3)
        
        # Scale KV cache by precision (approximately)
        if precision in [Precision.INT4, Precision.Q4_K_M]:
            kv_cache_gb *= 0.5  # KV cache often kept in higher precision
        elif precision in [Precision.INT8, Precision.Q8_0]:
            kv_cache_gb *= 0.75
        
        # Add overhead
        overhead_gb = (model_size_gb + kv_cache_gb) * (self.OVERHEAD_MULTIPLIER - 1)
        
        # Total VRAM
        total_vram_gb = model_size_gb + kv_cache_gb + overhead_gb
        
        # Determine which GPUs can fit
        can_fit_gpus = [
            gpu for gpu, vram in GPU_VRAM.items()
            if vram >= total_vram_gb
        ]
        
        # Add warnings
        if total_vram_gb > 80:
            warnings.append("Requires multi-GPU setup or cloud inference")
        elif total_vram_gb > 24:
            warnings.append("Requires high-end professional GPU (A100/H100)")
        elif total_vram_gb > 12:
            warnings.append("Requires RTX 4090/3090 or higher")
        
        if precision == Precision.FP32:
            warnings.append("FP32 is rarely used for inference; consider FP16")
        
        if context_length > 32768:
            warnings.append("Very long context may cause OOM even with estimates")
        
        return VRAMEstimate(
            model_name=model_name or f"{params}B model",
            precision=precision,
            model_size_gb=model_size_gb,
            kv_cache_gb=kv_cache_gb,
            overhead_gb=overhead_gb,
            total_vram_gb=total_vram_gb,
            can_fit_gpus=can_fit_gpus,
            warnings=warnings,
        )
    
    def list_known_models(self) -> List[Dict[str, Any]]:
        """List all known model specifications."""
        return [
            {
                "id": key,
                "name": spec.name,
                "parameters_billions": spec.parameters_billions,
                "context_length": spec.context_length,
            }
            for key, spec in KNOWN_MODELS.items()
        ]
    
    def compare_precisions(
        self,
        model_name: str = None,
        parameters_billions: float = None,
        context_length: int = 4096,
    ) -> List[VRAMEstimate]:
        """Compare VRAM requirements across all precision levels."""
        estimates = []
        
        for precision in Precision:
            try:
                estimate = self.estimate_vram(
                    model_name=model_name,
                    parameters_billions=parameters_billions,
                    precision=precision,
                    context_length=context_length,
                )
                estimates.append(estimate)
            except Exception:
                pass
        
        return sorted(estimates, key=lambda e: e.total_vram_gb)


# Singleton instance
_calculator: Optional[VRAMCalculator] = None


def get_vram_calculator() -> VRAMCalculator:
    """Get or create the VRAM calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = VRAMCalculator()
    return _calculator
