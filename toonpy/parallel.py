"""
Optional parallel processing utilities for large datasets.

This module provides parallel processing capabilities for serializing
large arrays, similar to what can be done in C# with Task Parallel Library.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, Callable, Sequence

__all__ = ["parallel_serialize_chunks"]


def parallel_serialize_chunks(
    chunks: list[Sequence[Any]],
    serializer_func: Callable[[Any], str],
    *,
    use_threads: bool = False,
    max_workers: int | None = None,
) -> list[str]:
    """Serialize multiple chunks in parallel.
    
    Useful for processing large arrays by dividing them into chunks
    and processing each chunk in parallel.
    
    Args:
        chunks: List of data chunks to serialize
        serializer_func: Function that takes a chunk and returns TOON string
        use_threads: If True, use ThreadPoolExecutor (for I/O bound),
                   otherwise use ProcessPoolExecutor (for CPU bound)
        max_workers: Maximum number of workers (None = auto)
        
    Returns:
        List of serialized TOON strings (one per chunk)
        
    Example:
        >>> from toonpy import ToonSerializer
        >>> serializer = ToonSerializer()
        >>> chunks = [[{"id": i} for i in range(100)] for _ in range(4)]
        >>> results = parallel_serialize_chunks(
        ...     chunks, 
        ...     serializer.dumps,
        ...     use_threads=True
        ... )
    """
    executor_class = ThreadPoolExecutor if use_threads else ProcessPoolExecutor
    
    with executor_class(max_workers=max_workers) as executor:
        futures = [executor.submit(serializer_func, chunk) for chunk in chunks]
        return [future.result() for future in futures]


def chunk_sequence(seq: Sequence[Any], chunk_size: int) -> list[Sequence[Any]]:
    """Divide a sequence into chunks of specified size.
    
    Args:
        seq: Sequence to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
        
    Example:
        >>> data = list(range(10))
        >>> chunks = chunk_sequence(data, 3)
        >>> len(chunks)
        4
    """
    chunks = []
    for i in range(0, len(seq), chunk_size):
        chunks.append(seq[i : i + chunk_size])
    return chunks

