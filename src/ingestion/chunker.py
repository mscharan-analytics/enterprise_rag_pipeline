class RecursiveCharacterChunker:
    """
    A robust text chunker that splits text recursively based on a list of separators
    (paragraphs, newlines, spaces) to fit chunks into the target size while respecting
    word and structure boundaries, applying a specified overlap between adjacent chunks.
    """
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", " ", ""]

    def _split_text(self, text: str, separators: list) -> list:
        final_chunks = []
        
        # If no separators left, force split by character index
        if not separators:
            return [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]
            
        separator = separators[0]
        next_separators = separators[1:]
        
        # Split text by current separator
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)
            
        current_chunk = []
        current_len = 0
        
        for split in splits:
            split_len = len(split) + (len(separator) if current_chunk else 0)
            
            if current_len + split_len <= self.chunk_size:
                current_chunk.append(split)
                current_len += split_len
            else:
                # Save the current chunk if it has content
                if current_chunk:
                    merged = separator.join(current_chunk)
                    final_chunks.append(merged)
                
                # If a single split is larger than chunk_size, delegate it to finer separators
                if len(split) > self.chunk_size:
                    sub_chunks = self._split_text(split, next_separators)
                    final_chunks.extend(sub_chunks)
                    current_chunk = []
                    current_len = 0
                else:
                    current_chunk = [split]
                    current_len = len(split)
                    
        if current_chunk:
            merged = separator.join(current_chunk)
            final_chunks.append(merged)
            
        return self._apply_overlap(final_chunks)

    def _apply_overlap(self, chunks: list) -> list:
        if len(chunks) <= 1:
            return chunks
            
        overlapped_chunks = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped_chunks.append(chunk)
                continue
            
            prev_chunk = chunks[i - 1]
            # Take overlapping slice from previous chunk
            overlap_len = min(self.chunk_overlap, len(prev_chunk))
            overlap_prefix = prev_chunk[-overlap_len:] if overlap_len > 0 else ""
            
            # Combine the overlap prefix and current chunk
            overlapped_chunks.append((overlap_prefix + " " + chunk).strip())
            
        return overlapped_chunks

    def chunk_text(self, text: str) -> list:
        cleaned_text = " ".join(text.strip().split())
        if not cleaned_text:
            return []
        return self._split_text(cleaned_text, self.separators)
