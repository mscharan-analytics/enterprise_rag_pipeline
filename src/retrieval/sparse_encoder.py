import re
from collections import Counter
import math

# Standard English stopwords to filter out frequent, low-information words
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "arent", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "cant", "cannot", "could",
    "couldnt", "did", "didnt", "do", "does", "doesnt", "doing", "dont", "down", "during", "each", "few", "for",
    "from", "further", "had", "hadnt", "has", "hasnt", "have", "havent", "having", "he", "hed", "hell", "hes",
    "her", "here", "heres", "hers", "herself", "him", "himself", "his", "how", "hows", "i", "id", "ill", "im",
    "ive", "if", "in", "into", "is", "isnt", "it", "its", "itself", "lets", "me", "more", "most", "mustnt", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shant", "she", "shed", "shell", "shes", "should", "shouldnt",
    "so", "some", "such", "than", "that", "thats", "the", "their", "theirs", "them", "themselves", "then",
    "there", "theres", "these", "they", "theyd", "theyll", "theyre", "theyve", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "wasnt", "we", "wed", "well", "were", "weve", "werent",
    "what", "whats", "when", "whens", "where", "wheres", "which", "while", "who", "whos", "whom", "why",
    "whys", "with", "wont", "would", "wouldnt", "you", "youd", "youll", "youre", "youve", "your", "yours",
    "yourself", "yourselves"
}

class SparseEncoder:
    """
    A lightweight, high-performance sparse vector encoder implementing basic TF-IDF term weighting.
    Tokenizes input text, filters stop words, maps tokens to 32-bit unsigned integer hashes,
    and returns a sorted sparse vector representation compatible with Qdrant.
    """
    def __init__(self):
        pass

    def encode(self, text: str) -> dict:
        if not text:
            return {"indices": [], "values": []}
            
        # Lowercase and extract alphanumeric words
        tokens = re.findall(r'[a-z0-9]+', text.lower())
        # Filter stopwords and short tokens
        filtered_tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
        
        if not filtered_tokens:
            return {"indices": [], "values": []}
            
        counts = Counter(filtered_tokens)
        
        indices = []
        values = []
        for token, count in counts.items():
            # Generate a stable 32-bit unsigned integer hash (FNV-1a)
            idx = self._stable_hash(token)
            
            # Simple TF-IDF approximation
            # TF = 1 + log(term_count)
            # IDF heuristic = 1 + 0.1 * min(len(token), 10) (longer words tend to be more specific/rare)
            tf = 1.0 + math.log(count)
            idf = 1.0 + 0.1 * min(len(token), 10)
            
            indices.append(idx)
            values.append(float(tf * idf))
            
        # Qdrant requires sparse vector indices to be unique and sorted in ascending order
        sorted_pairs = sorted(zip(indices, values), key=lambda x: x[0])
        
        # Deduplicate indices (taking the max value in case of rare hash collisions)
        unique_indices = []
        unique_values = []
        for idx, val in sorted_pairs:
            if unique_indices and unique_indices[-1] == idx:
                if val > unique_values[-1]:
                    unique_values[-1] = val
            else:
                unique_indices.append(idx)
                unique_values.append(val)
                
        return {
            "indices": unique_indices,
            "values": unique_values
        }

    def _stable_hash(self, token: str) -> int:
        """
        FNV-1a 32-bit hash algorithm for stable token hashing across different Python runs.
        """
        h = 2166136261
        for char in token:
            h = h ^ ord(char)
            h = (h * 16777619) & 0xffffffff
        return h
