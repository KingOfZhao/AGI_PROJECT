import re
from typing import Tuple, List

def quantify_ambiguity(
    text: str, 
    threshold: float = 0.5,
    vague_words: List[str] = None,
    min_sentence_length: int = 10,
    max_sentence_length: int = 30
) -> Tuple[float, str]:
    """
    Quantifies text ambiguity and determines whether AI summarization or human clarification is needed.
    
    Args:
        text: Input text to analyze
        threshold: Ambiguity threshold (0-1). Above threshold requires human intervention
        vague_words: List of words indicating vagueness (default: common vague terms)
        min_sentence_length: Minimum acceptable sentence length
        max_sentence_length: Maximum acceptable sentence length
        
    Returns:
        Tuple containing:
        - Ambiguity score (0-1)
        - Decision: "AI_GENERATE" or "HUMAN_INTERVENTION"
        
    Raises:
        ValueError: If threshold is not between 0 and 1
        TypeError: If input text is not a string
    """
    # Validate inputs
    if not isinstance(text, str):
        raise TypeError("Input text must be a string")
    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must be between 0 and 1")
    
    # Default vague words list
    if vague_words is None:
        vague_words = [
            'maybe', 'perhaps', 'possibly', 'probably', 'likely',
            'uncertain', 'unclear', 'ambiguous', 'uncertainly',
            'approximately', 'roughly', 'about', 'around',
            'suggest', 'indicate', 'appear', 'seem', 'might',
            'could', 'may', 'should', 'would', 'might'
        ]
    
    # Preprocess text
    try:
        # Clean and tokenize
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        words = clean_text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Calculate metrics
        vague_count = sum(1 for word in words if word in vague_words)
        vague_ratio = vague_count / max(len(words), 1)
        
        sentence_lengths = [len(s.split()) for s in sentences]
        avg_sentence_length = sum(sentence_lengths) / max(len(sentence_lengths), 1)
        
        # Calculate length deviation penalty
        length_deviation = 0
        for length in sentence_lengths:
            if length < min_sentence_length:
                length_deviation += (min_sentence_length - length) / min_sentence_length
            elif length > max_sentence_length:
                length_deviation += (length - max_sentence_length) / max_sentence_length
        
        length_penalty = min(length_deviation / max(len(sentence_lengths), 1), 1.0)
        
        # Calculate final ambiguity score (weighted average)
        ambiguity_score = 0.7 * vague_ratio + 0.3 * length_penalty
        
        # Determine intervention decision
        decision = "HUMAN_INTERVENTION" if ambiguity_score > threshold else "AI_GENERATE"
        
        return ambiguity_score, decision
        
    except Exception as e:
        raise RuntimeError(f"Error processing text: {str(e)}")

# Example usage
if __name__ == "__main__":
    test_text = "The results might indicate a possible correlation, but we are uncertain about the exact relationship. Further analysis is required."
    
    try:
        score, decision = quantify_ambiguity(test_text, threshold=0.4)
        print(f"Ambiguity Score: {score:.2f}")
        print(f"Decision: {decision}")
    except Exception as e:
        print(f"Error: {str(e)}")