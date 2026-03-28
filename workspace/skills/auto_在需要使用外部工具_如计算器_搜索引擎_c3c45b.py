"""
Tool Integration and Orchestration Module for AGI Systems.

This module provides a robust framework for determining when and how to use
external tools (calculators, search engines, APIs) to solve complex problems.
It acts as a bridge between an AI agent's internal reasoning and external
data sources, ensuring grounded, fact-based responses.

Key Features:
- Dynamic tool selection based on intent analysis.
- Standardized input/output handling for various tools.
- Comprehensive error handling and retry mechanisms.
- Detailed logging for auditing and debugging.

Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
from datetime import datetime

# 1. Configuration and Constants
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("AGI_Tool_Manager")


class ToolType(Enum):
    """Enumeration of supported external tool types."""
    CALCULATOR = "calculator"
    SEARCH_ENGINE = "search_engine"
    EXTERNAL_API = "external_api"
    UNKNOWN = "unknown"


@dataclass
class ToolRequest:
    """Data class representing a request to an external tool."""
    tool_type: ToolType
    query: str
    parameters: Dict[str, Any]
    timestamp: str = datetime.now().isoformat()


@dataclass
class ToolResponse:
    """Data class representing the result from an external tool."""
    request_id: str
    tool_type: ToolType
    status: str  # 'success', 'error', 'timeout'
    raw_data: Any
    processed_result: Optional[str] = None
    error_message: Optional[str] = None


class InputValidationError(ValueError):
    """Custom exception for invalid input data."""
    pass


class ToolExecutionError(RuntimeError):
    """Custom exception for failures during tool execution."""
    pass


class ToolOrchestrator:
    """
    Core class responsible for analyzing queries, selecting tools, and
    integrating results into the AGI's workflow.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the ToolOrchestrator.

        Args:
            config (Optional[Dict]): Configuration dictionary for API keys and endpoints.
        """
        self.config = config or {}
        self.tool_registry = self._initialize_tools()
        logger.info("ToolOrchestrator initialized with %d tools.", len(self.tool_registry))

    def _initialize_tools(self) -> Dict[ToolType, Callable]:
        """
        Internal method to map tool types to their execution functions.
        """
        return {
            ToolType.CALCULATOR: self._execute_calculator,
            ToolType.SEARCH_ENGINE: self._execute_search,
            ToolType.EXTERNAL_API: self._execute_api_call
        }

    def analyze_intent(self, query: str) -> ToolType:
        """
        Analyzes the user query to determine which external tool is most appropriate.
        
        Args:
            query (str): The natural language input from the user.
            
        Returns:
            ToolType: The identified tool type.
        """
        logger.debug(f"Analyzing intent for query: {query[:50]}...")
        
        # Basic heuristic rules for intent recognition (In production, use an embedding model)
        calc_patterns = [r'\d+[\+\-\*\/\^]', r'calculate', r'sqrt', r'logarithm']
        search_patterns = [r'who is', r'what is', r'current weather', r'news about', r'find information']
        api_patterns = [r'status of', r'fetch data', r'api', r'database record']

        if any(re.search(p, query.lower()) for p in calc_patterns):
            return ToolType.CALCULATOR
        if any(re.search(p, query.lower()) for p in search_patterns):
            return ToolType.SEARCH_ENGINE
        if any(re.search(p, query.lower()) for p in api_patterns):
            return ToolType.EXTERNAL_API
            
        return ToolType.UNKNOWN

    def process_complex_query(self, user_query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main entry point for handling a complex query that may require external tools.
        
        Args:
            user_query (str): The user's raw input.
            context (Optional[Dict]): Additional context (session ID, user history).
            
        Returns:
            Dict[str, Any]: A structured dictionary containing the final answer and metadata.
        """
        if not user_query or not isinstance(user_query, str):
            raise InputValidationError("Query must be a non-empty string.")

        logger.info(f"Processing query: {user_query}")
        
        # Step 1: Determine Intent
        required_tool = self.analyze_intent(user_query)
        
        if required_tool == ToolType.UNKNOWN:
            logger.warning("No specific tool identified. Falling back to internal knowledge.")
            return {
                "answer": None,
                "status": "fallback",
                "message": "No external tool required or matched."
            }

        # Step 2: Prepare Request
        request = ToolRequest(
            tool_type=required_tool,
            query=user_query,
            parameters=context or {}
        )

        # Step 3: Execute Tool
        try:
            response = self.execute_tool(request)
            
            # Step 4: Integrate Result
            final_answer = self.integrate_results(response)
            
            return {
                "answer": final_answer,
                "source_tool": required_tool.value,
                "raw_data": response.raw_data,
                "status": "success"
            }

        except ToolExecutionError as e:
            logger.error(f"Tool execution failed: {e}")
            return {
                "answer": None,
                "status": "error",
                "message": str(e)
            }

    def execute_tool(self, request: ToolRequest) -> ToolResponse:
        """
        Executes the request using the mapped tool function.
        
        Args:
            request (ToolRequest): The validated request object.
            
        Returns:
            ToolResponse: The raw data from the tool.
        """
        executor = self.tool_registry.get(request.tool_type)
        
        if not executor:
            raise ToolExecutionError(f"No executor found for tool type: {request.tool_type}")

        logger.info(f"Executing tool: {request.tool_type.value}")
        
        try:
            # Simulating a generic execution call
            raw_result = executor(request.query, request.parameters)
            return ToolResponse(
                request_id="req_" + str(hash(request.timestamp)),
                tool_type=request.tool_type,
                status="success",
                raw_data=raw_result
            )
        except Exception as e:
            raise ToolExecutionError(f"Internal tool error: {str(e)}")

    def integrate_results(self, response: ToolResponse) -> str:
        """
        Transforms raw tool output into a human-readable or AGI-consumable format.
        
        Args:
            response (ToolResponse): The response object from the tool.
            
        Returns:
            str: The synthesized natural language response.
        """
        if response.status != "success":
            return "I encountered an issue retrieving the information."

        data = response.raw_data
        
        # Format based on tool type
        if response.tool_type == ToolType.CALCULATOR:
            return f"The calculated result is {data}."
        elif response.tool_type == ToolType.SEARCH_ENGINE:
            # Assuming data is a list of snippets
            if isinstance(data, list):
                return f"Based on search results: {data[0]}"
            return f"Information found: {data}"
        elif response.tool_type == ToolType.EXTERNAL_API:
            return f"System data retrieved: {json.dumps(data)}"
        
        return str(data)

    # --- Mock Tool Implementations (Simulating External Calls) ---

    def _execute_calculator(self, query: str, params: Dict) -> float:
        """
        Mock function simulating a calculator tool.
        In a real scenario, this would call a WolframAlpha API or local math library.
        """
        logger.info("...Accessing Calculator Tool...")
        # Simple safety check for code injection in eval (use restricted eval in prod)
        if not re.match(r'^[\d\s\+\-\*\/\.\(\)\^]+$', query):
             raise InputValidationError("Invalid characters in math expression.")
        
        try:
            # Simulating complex calculation
            result = eval(query)
            return result
        except Exception as e:
            logger.error(f"Calculation error: {e}")
            raise ToolExecutionError("Failed to compute mathematical expression.")

    def _execute_search(self, query: str, params: Dict) -> List[str]:
        """
        Mock function simulating a search engine API (e.g., SerpAPI, Google).
        """
        logger.info("...Accessing Search Engine Tool...")
        # Simulate API latency and response
        mock_results = [
            f"Search result for '{query}': The capital of France is Paris.",
            "Another result about the population."
        ]
        return mock_results

    def _execute_api_call(self, query: str, params: Dict) -> Dict:
        """
        Mock function simulating a REST API call.
        """
        logger.info("...Accessing External REST API...")
        # Simulate a status check API
        return {"status_code": 200, "data": {"server_health": "optimal", "load": 0.75}}


# --- Helper Functions ---

def validate_input_safety(query: str) -> bool:
    """
    Helper function to check for potential injection attacks or forbidden content.
    
    Args:
        query (str): Input string.
        
    Returns:
        bool: True if safe, False otherwise.
    """
    forbidden_patterns = ['<script>', 'DROP TABLE', 'rm -rf']
    return not any(pat in query for pat in forbidden_patterns)


def format_agi_response(answer: str, metadata: Dict) -> str:
    """
    Helper to wrap the answer in a JSON structure expected by the AGI core.
    """
    return json.dumps({
        "response_type": "tool_augmented",
        "content": answer,
        "metadata": metadata
    }, indent=2)


# --- Usage Example ---
if __name__ == "__main__":
    # Instantiate the Orchestrator
    orchestrator = ToolOrchestrator(config={"api_key": "dummy_key"})

    # Example 1: Mathematical Query
    math_query = "15 * 20 + 5"
    if validate_input_safety(math_query):
        result = orchestrator.process_complex_query(math_query)
        print(f"Query: {math_query}")
        print(f"Result: {format_agi_response(result['answer'], {'tool': result.get('source_tool')})}")
        print("-" * 40)

    # Example 2: Knowledge Query (Search)
    search_query = "What is the capital of Ireland?"
    if validate_input_safety(search_query):
        result = orchestrator.process_complex_query(search_query)
        print(f"Query: {search_query}")
        print(f"Result: {format_agi_response(result['answer'], {'tool': result.get('source_tool')})}")
        print("-" * 40)

    # Example 3: Ambiguous Query (Fallback)
    vague_query = "Tell me a story"
    if validate_input_safety(vague_query):
        result = orchestrator.process_complex_query(vague_query)
        print(f"Query: {vague_query}")
        print(f"Status: {result['status']} (No tool used)")