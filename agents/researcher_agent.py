#!/usr/bin/env python3

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from contextlib import AsyncExitStack
import openai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearcherAgent:
    """
    Financial researcher agent with Brave Search + LibSQL Memory integration
    
    This agent specializes in:
    - Web research using Brave Search for financial news
    - Storing and retrieving research findings in LibSQL memory
    - Providing research insights as a tool for trading agents
    
    Follows the agent-as-tool pattern from agents/6_mcp
    """
    
    def __init__(self, name: str = "Researcher", model_name: str = "gpt-4o-mini"):
        self.name = name
        self.model_name = model_name
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # MCP server connections (will be injected)
        self.brave_search_tools = None
        self.memory_tools = None
        self.fetch_tools = None
    
    def set_mcp_tools(self, brave_search_tools, memory_tools, fetch_tools=None):
        """Inject MCP tool connections"""
        self.brave_search_tools = brave_search_tools
        self.memory_tools = memory_tools
        self.fetch_tools = fetch_tools
    
    def get_instructions(self) -> str:
        """Get researcher instructions following the source project pattern"""
        return f"""You are a financial researcher. You are able to search the web for interesting financial news,
look for possible trading opportunities, and help with research.
Based on the request, you carry out necessary research and respond with your findings.
Take time to make multiple searches to get a comprehensive overview, and then summarize your findings.
If the web search tool raises an error due to rate limits, then use your other tool that fetches web pages instead.

Important: making use of your knowledge graph to retrieve and store information on companies, websites and market conditions:

Make use of your knowledge graph tools to store and recall entity information; use it to retrieve information that
you have worked on previously, and store new information about companies, stocks and market conditions.
Also use it to store web addresses that you find interesting so you can check them later.
Draw on your knowledge graph to build your expertise over time.

If there isn't a specific request, then just respond with investment opportunities based on searching latest news.
The current datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    async def search_financial_news(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for financial news using Brave Search"""
        if not self.brave_search_tools:
            logger.warning("Brave Search tools not available")
            return []
        
        try:
            # Use Brave Search to find financial news
            search_results = await self.brave_search_tools.search(
                query=f"{query} financial news stock market",
                count=max_results
            )
            
            # Store search results in memory for future reference
            if self.memory_tools:
                await self._store_search_results_in_memory(query, search_results)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching financial news: {e}")
            return []
    
    async def _store_search_results_in_memory(self, query: str, results: List[Dict[str, Any]]):
        """Store search results in LibSQL memory"""
        try:
            import time
            timestamp = int(time.time())
            
            # Create entities for each search result
            entities = []
            for i, result in enumerate(results[:5]):  # Store top 5 results
                entity = {
                    "name": f"search_result_{query.replace(' ', '_')}_{i}_{timestamp}",
                    "entityType": "financial_news",
                    "observations": [
                        f"Query: {query}",
                        f"Title: {result.get('title', 'N/A')}",
                        f"URL: {result.get('url', 'N/A')}",
                        f"Description: {result.get('description', 'N/A')}",
                        f"Timestamp: {timestamp}",
                        f"Researcher: {self.name}"
                    ]
                }
                entities.append(entity)
            
            if entities:
                await self.memory_tools.create_entities(entities)
                logger.info(f"Stored {len(entities)} search results in memory for query: {query}")
                
        except Exception as e:
            logger.warning(f"Failed to store search results in memory: {e}")
    
    async def retrieve_past_research(self, topic: str) -> str:
        """Retrieve past research from memory"""
        if not self.memory_tools:
            return "No memory system available."
        
        try:
            # Search for past research on this topic
            search_query = f"financial_news {topic}"
            past_research = await self.memory_tools.search_nodes(search_query)
            
            if past_research and past_research != '{"entities": [], "relations": []}':
                return f"Past research on {topic}:\n{past_research}"
            else:
                return f"No past research found for {topic}."
                
        except Exception as e:
            logger.warning(f"Failed to retrieve past research: {e}")
            return "Error retrieving past research."
    
    async def analyze_market_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Analyze market sentiment for a specific stock symbol"""
        try:
            # Search for recent news about the symbol
            news_results = await self.search_financial_news(f"{symbol} stock news earnings", max_results=5)
            
            # Get past research context
            past_context = await self.retrieve_past_research(symbol)
            
            # Generate sentiment analysis prompt
            prompt = f"""
Analyze the market sentiment for {symbol} based on the following recent news and past research:

RECENT NEWS:
{json.dumps(news_results, indent=2)}

PAST RESEARCH CONTEXT:
{past_context}

Provide a sentiment analysis including:
1. Overall sentiment (Positive/Negative/Neutral)
2. Key factors influencing sentiment
3. Potential trading implications
4. Confidence level (1-10)

Respond with a JSON object containing these fields.
"""
            
            # Call OpenAI for sentiment analysis
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a financial analyst. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            sentiment_analysis = json.loads(response_text)
            
            # Store analysis in memory
            if self.memory_tools:
                await self._store_sentiment_analysis_in_memory(symbol, sentiment_analysis)
            
            return sentiment_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market sentiment for {symbol}: {e}")
            return {
                "sentiment": "Neutral",
                "key_factors": [f"Error in analysis: {str(e)}"],
                "trading_implications": "Unable to determine due to analysis error",
                "confidence": 1
            }
    
    async def _store_sentiment_analysis_in_memory(self, symbol: str, analysis: Dict[str, Any]):
        """Store sentiment analysis in memory"""
        try:
            import time
            timestamp = int(time.time())
            
            entity = {
                "name": f"sentiment_analysis_{symbol}_{timestamp}",
                "entityType": "sentiment_analysis",
                "observations": [
                    f"Symbol: {symbol}",
                    f"Sentiment: {analysis.get('sentiment', 'Unknown')}",
                    f"Key Factors: {json.dumps(analysis.get('key_factors', []))}",
                    f"Trading Implications: {analysis.get('trading_implications', 'None')}",
                    f"Confidence: {analysis.get('confidence', 0)}",
                    f"Timestamp: {timestamp}",
                    f"Researcher: {self.name}"
                ]
            }
            
            await self.memory_tools.create_entities([entity])
            logger.info(f"Stored sentiment analysis in memory for {symbol}")
            
        except Exception as e:
            logger.warning(f"Failed to store sentiment analysis in memory: {e}")
    
    async def research_request(self, request: str) -> str:
        """Handle a research request from a trading agent"""
        try:
            # Generate research prompt
            prompt = f"""
{self.get_instructions()}

RESEARCH REQUEST: {request}

Please carry out comprehensive research on this request. Use your web search capabilities to find relevant financial news and information. Store important findings in your knowledge graph for future reference.

Provide a detailed research report with:
1. Key findings
2. Market implications
3. Relevant news sources
4. Investment opportunities or risks
5. Confidence level in your analysis
"""
            
            # Call OpenAI for research
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a professional financial researcher with access to web search and memory tools."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.5
            )
            
            research_report = response.choices[0].message.content.strip()
            
            # Store research request and response in memory
            if self.memory_tools:
                await self._store_research_request_in_memory(request, research_report)
            
            return research_report
            
        except Exception as e:
            logger.error(f"Error handling research request: {e}")
            return f"Error processing research request: {str(e)}"
    
    async def _store_research_request_in_memory(self, request: str, response: str):
        """Store research request and response in memory"""
        try:
            import time
            timestamp = int(time.time())
            
            entity = {
                "name": f"research_request_{timestamp}",
                "entityType": "research_request",
                "observations": [
                    f"Request: {request}",
                    f"Response: {response[:500]}...",  # Truncate long responses
                    f"Timestamp: {timestamp}",
                    f"Researcher: {self.name}"
                ]
            }
            
            await self.memory_tools.create_entities([entity])
            logger.info("Stored research request in memory")
            
        except Exception as e:
            logger.warning(f"Failed to store research request in memory: {e}")
    
    def as_tool(self, tool_name: str = "Researcher", tool_description: str = None) -> Dict[str, Any]:
        """
        Convert this researcher agent into a tool that can be used by trading agents
        Following the exact pattern from agents/6_mcp/traders.py:64
        """
        if tool_description is None:
            tool_description = """This tool researches online for news and opportunities, 
either based on your specific request to look into a certain stock, 
or generally for notable financial news and opportunities. 
Describe what kind of research you're looking for."""
        
        return {
            "name": tool_name,
            "description": tool_description,
            "function": self.research_request,
            "parameters": {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "The research request or query"
                    }
                },
                "required": ["request"]
            }
        }

# Factory functions following the source project pattern
async def get_researcher(mcp_servers, model_name: str = "gpt-4o-mini") -> ResearcherAgent:
    """Create a researcher agent with MCP server connections"""
    researcher = ResearcherAgent(name="Researcher", model_name=model_name)
    
    # Extract MCP tools from servers (this would be implemented based on your MCP connector)
    # For now, we'll set placeholders that would be replaced with actual MCP tool connections
    brave_search_tools = None
    memory_tools = None
    fetch_tools = None
    
    # In a real implementation, you would extract these from mcp_servers
    # brave_search_tools = mcp_servers.get_brave_search_tools()
    # memory_tools = mcp_servers.get_memory_tools()
    # fetch_tools = mcp_servers.get_fetch_tools()
    
    researcher.set_mcp_tools(brave_search_tools, memory_tools, fetch_tools)
    return researcher

async def get_researcher_tool(mcp_servers, model_name: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Get researcher as a tool for trading agents - following agents/6_mcp pattern"""
    researcher = await get_researcher(mcp_servers, model_name)
    return researcher.as_tool(
        tool_name="Researcher", 
        tool_description="""This tool researches online for news and opportunities, 
either based on your specific request to look into a certain stock, 
or generally for notable financial news and opportunities. 
Describe what kind of research you're looking for."""
    )