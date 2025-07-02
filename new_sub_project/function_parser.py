"""Module for parsing and extracting function definitions from agent responses."""

import re
from typing import Dict, List, Tuple

def extract_function_code(text: str) -> Dict[str, str]:
    """
    Extract function code from text.
    
    Returns:
        Dictionary mapping function names to their code.
    """
    # Pattern to match Python function definitions
    pattern = r'```python\s*(?:@staticmethod\s*)?def\s+([a-zA-Z0-9_]+)\s*\([^)]*\).*?```'
    
    # Find all function blocks in code fence blocks
    matches = re.finditer(pattern, text, re.DOTALL)
    
    functions = {}
    for match in matches:
        code_block = match.group(0).strip('`')
        code_block = code_block.replace('```python', '').strip()
        
        # Extract function name
        func_name_match = re.search(r'def\s+([a-zA-Z0-9_]+)', code_block)
        if func_name_match:
            func_name = func_name_match.group(1)
            
            # Format code for class method
            formatted_code = f"""    @staticmethod
{code_block.replace('def ', 'def ')}"""
            functions[func_name] = formatted_code
    
    return functions


def extract_function_sequence(text: str) -> List[str]:
    """
    Extract the sequence of functions to call from text.
    
    Returns:
        List of function names to call in sequence.
    """
    # Look for patterns like "call sequence: func1, func2, func3"
    sequence_pattern = r'(?:call|execute|run|invoke)(?:\s+in)?(?:\s+this)?\s+sequence[:\s]+([a-zA-Z0-9_, ]+)'
    sequence_match = re.search(sequence_pattern, text, re.IGNORECASE)
    
    if sequence_match:
        sequence_str = sequence_match.group(1)
        return [func.strip() for func in sequence_str.split(',')]
    
    # Try to find function calls directly
    func_calls = re.findall(r'call\s+`?([a-zA-Z0-9_]+)`?', text)
    if func_calls:
        return func_calls
    
    # Extract any function names mentioned in the text as a fallback
    func_names = re.findall(r'def\s+([a-zA-Z0-9_]+)', text)
    return func_names


def parse_plan_from_agent_response(response: str) -> Tuple[Dict[str, str], List[str], str]:
    """
    Parse an agent's response to extract:
    1. Function definitions
    2. Sequence of function calls
    3. Suggested name for composite function
    
    Returns:
        Tuple of (function_dict, sequence, composite_name)
    """
    # Extract function code
    functions = extract_function_code(response)
    
    # Extract sequence
    sequence = extract_function_sequence(response)
    
    # Extract composite function name suggestion
    composite_name = "run_task"  # Default name
    composite_pattern = r'(?:composite|combined|wrapper)\s+function(?:\s+name)?[:\s]+`?([a-zA-Z0-9_]+)`?'
    composite_match = re.search(composite_pattern, response, re.IGNORECASE)
    if composite_match:
        composite_name = composite_match.group(1)
    
    return functions, sequence, composite_name 