"""
MCP Server with Agent-to-Agent (A2A) Protocol for Skill Orchestration

Enhanced with monorepo patterns for constitutional oversight, debate coordination,
and multi-agent sessions. Supports:
- Agent roles (SKILL, JUDGE, EVIDENCE_GATHERER, REFLEXION_MEDIATOR)
- Session management for coordinated activities
- Constitutional oversight via judge approval
- Evidence gathering for compliance
- Reflexion mediation for debate coordination
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum


class MessageType(Enum):
    """Types of messages in the A2A protocol"""
    REQUEST = "request"
    RESPONSE = "response"
    DELEGATE = "delegate"
    ERROR = "error"
    STATUS = "status"
    # Enhanced oversight types from monorepo
    OVERSIGHT_REQUEST = "oversight_request"
    OVERSIGHT_RESPONSE = "oversight_response"
    EVIDENCE_REQUEST = "evidence_request"
    EVIDENCE_RESPONSE = "evidence_response"
    JUDGE_RULING = "judge_ruling"
    DEBATE_INVITATION = "debate_invitation"
    DEBATE_ARGUMENT = "debate_argument"
    DEBATE_SYNTHESIS = "debate_synthesis"
    AGENT_REGISTRATION = "agent_registration"
    SESSION_COORDINATION = "session_coordination"
    REFLEXION_MEDIATION = "reflexion_mediation"


class A2AAgentRole(str, Enum):
    """Roles of agents in A2A coordination (from monorepo patterns)"""
    SKILL = "skill"  # Original skill agents
    MCP_AGENT = "mcp_agent"
    JUDGE = "judge"
    EVIDENCE_GATHERER = "evidence_gatherer"
    REFLEXION_MEDIATOR = "reflexion_mediator"
    ADVOCATE = "advocate"
    SKEPTIC = "skeptic"
    IMPLEMENTER = "implementer"


@dataclass
class A2AMessage:
    """Standard message format for agent-to-agent communication (enhanced from monorepo)"""
    message_id: str
    message_type: MessageType
    sender_skill: str
    recipient_skill: Optional[str]
    payload: Dict[str, Any]
    context: Dict[str, Any]
    parent_message_id: Optional[str] = None
    session_id: Optional[str] = None  # From monorepo: session tracking
    timestamp: datetime = field(default_factory=datetime.now)  # From monorepo
    requires_response: bool = False  # From monorepo: synchronous patterns
    response_timeout: float = 30.0  # From monorepo

    def to_dict(self):
        result = asdict(self)
        result['message_type'] = self.message_type.value
        result['timestamp'] = self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp
        return result


@dataclass
class A2ASession:
    """A2A coordination session for multi-agent activities (from monorepo)"""
    session_id: str
    session_type: str  # "oversight", "debate", "evidence_gathering", "workflow"
    coordinator: str  # Agent ID of session coordinator
    participants: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    session_state: str = "active"
    message_history: List[A2AMessage] = field(default_factory=list)
    context_vars: Dict[str, Any] = field(default_factory=dict)


@dataclass
class A2AAgent:
    """A2A agent registration information (from monorepo)"""
    agent_id: str
    agent_role: A2AAgentRole
    capabilities: List[str] = field(default_factory=list)
    active_sessions: Set[str] = field(default_factory=set)
    message_handlers: Dict[MessageType, Callable] = field(default_factory=dict)
    last_seen: datetime = field(default_factory=datetime.now)
    connected: bool = True


class Skill:
    """Base class for skills that can communicate via A2A protocol"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.message_handlers: Dict[str, Callable] = {}
        self.orchestrator: Optional['WorkflowOrchestrator'] = None
    
    async def handle_message(self, message: A2AMessage) -> A2AMessage:
        """Handle incoming A2A message"""
        if message.message_type == MessageType.REQUEST:
            return await self.process_request(message)
        elif message.message_type == MessageType.DELEGATE:
            return await self.process_delegation(message)
        else:
            return self.create_error_response(
                message, 
                f"Unsupported message type: {message.message_type}"
            )
    
    async def process_request(self, message: A2AMessage) -> A2AMessage:
        """Override this to implement skill-specific logic"""
        raise NotImplementedError("Subclasses must implement process_request")
    
    async def process_delegation(self, message: A2AMessage) -> A2AMessage:
        """Handle delegated tasks from other skills"""
        return await self.process_request(message)
    
    async def delegate_to_skill(
        self, 
        target_skill: str, 
        payload: Dict[str, Any],
        context: Dict[str, Any],
        parent_message_id: str
    ) -> A2AMessage:
        """Delegate a task to another skill"""
        if not self.orchestrator:
            raise RuntimeError("Skill not registered with orchestrator")
        
        message = A2AMessage(
            message_id=self.orchestrator.generate_message_id(),
            message_type=MessageType.DELEGATE,
            sender_skill=self.name,
            recipient_skill=target_skill,
            payload=payload,
            context=context,
            parent_message_id=parent_message_id
        )
        
        return await self.orchestrator.route_message(message)
    
    def create_response(
        self, 
        original_message: A2AMessage, 
        result: Any
    ) -> A2AMessage:
        """Create a response message"""
        return A2AMessage(
            message_id=f"{original_message.message_id}_response",
            message_type=MessageType.RESPONSE,
            sender_skill=self.name,
            recipient_skill=original_message.sender_skill,
            payload={"result": result},
            context=original_message.context,
            parent_message_id=original_message.message_id
        )
    
    def create_error_response(
        self, 
        original_message: A2AMessage, 
        error: str
    ) -> A2AMessage:
        """Create an error response message"""
        return A2AMessage(
            message_id=f"{original_message.message_id}_error",
            message_type=MessageType.ERROR,
            sender_skill=self.name,
            recipient_skill=original_message.sender_skill,
            payload={"error": error},
            context=original_message.context,
            parent_message_id=original_message.message_id
        )


class WorkflowOrchestrator:
    """
    Orchestrates A2A communication between skills (enhanced from monorepo)

    Features from monorepo:
    - Agent registration and discovery
    - Session management for multi-agent coordination
    - Constitutional oversight via judge agents
    - Evidence gathering coordination
    - Synchronous message patterns with timeouts
    """

    def __init__(self):
        # Original skill registry
        self.skills: Dict[str, Skill] = {}
        self.workflows: Dict[str, 'Workflow'] = {}
        self.message_counter = 0
        self.message_history: List[A2AMessage] = []

        # Enhanced from monorepo: agent registry
        self.registered_agents: Dict[str, A2AAgent] = {}
        self.active_sessions: Dict[str, A2ASession] = {}
        self.pending_responses: Dict[str, asyncio.Future] = {}

        # Enhanced from monorepo: role-specific registries
        self.available_judges: Set[str] = set()
        self.available_evidence_gatherers: Set[str] = set()
        self.reflexion_mediators: Set[str] = set()
    
    def register_skill(self, skill: Skill):
        """Register a skill with the orchestrator"""
        self.skills[skill.name] = skill
        skill.orchestrator = self
    
    def register_workflow(self, workflow: 'Workflow'):
        """Register a workflow"""
        self.workflows[workflow.name] = workflow
    
    def generate_message_id(self) -> str:
        """Generate unique message ID"""
        self.message_counter += 1
        return f"msg_{self.message_counter}"
    
    async def route_message(self, message: A2AMessage) -> A2AMessage:
        """Route message to appropriate skill"""
        self.message_history.append(message)
        
        if not message.recipient_skill:
            return A2AMessage(
                message_id=self.generate_message_id(),
                message_type=MessageType.ERROR,
                sender_skill="orchestrator",
                recipient_skill=message.sender_skill,
                payload={"error": "No recipient specified"},
                context=message.context
            )
        
        target_skill = self.skills.get(message.recipient_skill)
        if not target_skill:
            return A2AMessage(
                message_id=self.generate_message_id(),
                message_type=MessageType.ERROR,
                sender_skill="orchestrator",
                recipient_skill=message.sender_skill,
                payload={"error": f"Skill not found: {message.recipient_skill}"},
                context=message.context
            )
        
        return await target_skill.handle_message(message)
    
    async def execute_workflow(
        self,
        workflow_name: str,
        input_data: Dict[str, Any]
    ) -> A2AMessage:
        """Execute a named workflow"""
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_name}")

        return await workflow.execute(self, input_data)

    # ========================================================================
    # Enhanced methods from monorepo for agent coordination
    # ========================================================================

    async def register_agent(
        self,
        agent_id: str,
        agent_role: A2AAgentRole = A2AAgentRole.SKILL,
        capabilities: List[str] = None
    ) -> Dict[str, Any]:
        """Register agent in A2A protocol (from monorepo pattern)"""
        agent = A2AAgent(
            agent_id=agent_id,
            agent_role=agent_role,
            capabilities=capabilities or []
        )

        self.registered_agents[agent_id] = agent

        # Update role-specific registries
        if agent_role == A2AAgentRole.JUDGE:
            self.available_judges.add(agent_id)
        elif agent_role == A2AAgentRole.EVIDENCE_GATHERER:
            self.available_evidence_gatherers.add(agent_id)
        elif agent_role == A2AAgentRole.REFLEXION_MEDIATOR:
            self.reflexion_mediators.add(agent_id)

        # Broadcast registration message
        registration_msg = A2AMessage(
            message_id=self.generate_message_id(),
            sender_skill="orchestrator",
            recipient_skill="all",
            message_type=MessageType.AGENT_REGISTRATION,
            payload={
                "agent_id": agent_id,
                "agent_role": agent_role.value,
                "capabilities": capabilities or [],
                "action": "registered"
            },
            context={}
        )

        self.message_history.append(registration_msg)

        return {
            "success": True,
            "agent_id": agent_id,
            "agent_role": agent_role.value,
            "capabilities": capabilities or []
        }

    def get_available_agents(self, role: Optional[A2AAgentRole] = None) -> List[str]:
        """Get list of available agents, optionally filtered by role"""
        if role:
            return [agent_id for agent_id, agent in self.registered_agents.items()
                   if agent.agent_role == role and agent.connected]
        return [agent_id for agent_id, agent in self.registered_agents.items() if agent.connected]

    def get_available_judges(self) -> List[str]:
        """Get list of available judge agents"""
        return list(self.available_judges)

    def get_available_evidence_gatherers(self) -> List[str]:
        """Get list of available evidence gatherer agents"""
        return list(self.available_evidence_gatherers)

    def get_reflexion_mediators(self) -> List[str]:
        """Get list of available reflexion mediator agents"""
        return list(self.reflexion_mediators)

    async def create_session(
        self,
        session_id: str = None,
        session_type: str = "coordination",
        participant_agents: List[str] = None,
        evidence_gatherer: str = None
    ) -> Dict[str, Any]:
        """Create A2A coordination session (from monorepo pattern)"""
        if not session_id:
            session_id = f"a2a_{session_type}_{int(time.time())}"

        session = A2ASession(
            session_id=session_id,
            session_type=session_type,
            coordinator="orchestrator",
            participants=participant_agents or []
        )

        # Add evidence gatherer if specified
        if evidence_gatherer:
            session.participants.append(evidence_gatherer)
            session.context_vars["evidence_gatherer"] = evidence_gatherer

        self.active_sessions[session_id] = session

        # Notify participants
        for participant in session.participants:
            coordination_msg = A2AMessage(
                message_id=self.generate_message_id(),
                sender_skill="orchestrator",
                recipient_skill=participant,
                message_type=MessageType.SESSION_COORDINATION,
                session_id=session_id,
                payload={
                    "action": "session_created",
                    "session_type": session_type,
                    "coordinator": "orchestrator",
                    "participants": session.participants
                },
                context={}
            )
            self.message_history.append(coordination_msg)

        return {
            "success": True,
            "session_id": session_id,
            "session_type": session_type,
            "participants": session.participants
        }

    def get_session(self, session_id: str) -> Optional[A2ASession]:
        """Get A2A session by ID"""
        return self.active_sessions.get(session_id)

    async def close_session(self, session_id: str) -> Dict[str, Any]:
        """Close A2A coordination session"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}

        session = self.active_sessions[session_id]
        session.session_state = "closed"

        # Notify participants
        for participant in session.participants:
            coordination_msg = A2AMessage(
                message_id=self.generate_message_id(),
                sender_skill="orchestrator",
                recipient_skill=participant,
                message_type=MessageType.SESSION_COORDINATION,
                session_id=session_id,
                payload={
                    "action": "session_closed",
                    "coordinator": "orchestrator"
                },
                context={}
            )
            self.message_history.append(coordination_msg)

        del self.active_sessions[session_id]

        return {"success": True, "session_id": session_id}

    async def send_message_and_wait_response(
        self,
        message: A2AMessage,
        timeout_seconds: float = 30.0
    ) -> Dict[str, Any]:
        """Send message and wait for response (from monorepo pattern)"""
        message.requires_response = True
        message.response_timeout = timeout_seconds

        # Create future for response
        response_future = asyncio.Future()
        self.pending_responses[message.message_id] = response_future

        # Add to history
        self.message_history.append(message)

        # Route to skill (simulated for now - real impl would use actual async routing)
        target_skill = self.skills.get(message.recipient_skill)
        if target_skill:
            response = await target_skill.handle_message(message)
            response_future.set_result(response.payload)

        try:
            # Wait for response
            response_payload = await asyncio.wait_for(response_future, timeout=timeout_seconds)
            return response_payload
        except asyncio.TimeoutError:
            # Cleanup pending response
            if message.message_id in self.pending_responses:
                del self.pending_responses[message.message_id]

            return {
                "success": False,
                "error": "Response timeout",
                "timeout_seconds": timeout_seconds
            }

    async def request_judge_approval(
        self,
        operation_name: str,
        parameters: Dict[str, Any],
        session_id: str = None
    ) -> Dict[str, Any]:
        """Request judge approval for operation (from monorepo pattern)"""
        available_judges = self.get_available_judges()
        if not available_judges:
            return {"error": "No judges available", "approved": False}

        # Send to first available judge
        judge_id = available_judges[0]

        oversight_request = A2AMessage(
            message_id=self.generate_message_id(),
            sender_skill="orchestrator",
            recipient_skill=judge_id,
            message_type=MessageType.OVERSIGHT_REQUEST,
            session_id=session_id,
            payload={
                "operation_name": operation_name,
                "parameters": parameters,
                "requesting_agent": "orchestrator"
            },
            context={}
        )

        return await self.send_message_and_wait_response(oversight_request)

    async def request_evidence_gathering(
        self,
        operation_name: str,
        parameters: Dict[str, Any],
        context_info: str = "",
        session_id: str = None
    ) -> Dict[str, Any]:
        """Request evidence gathering for operation (from monorepo pattern)"""
        available_gatherers = self.get_available_evidence_gatherers()
        if not available_gatherers:
            return {"error": "No evidence gatherers available"}

        # Send to first available evidence gatherer
        gatherer_id = available_gatherers[0]

        evidence_request = A2AMessage(
            message_id=self.generate_message_id(),
            sender_skill="orchestrator",
            recipient_skill=gatherer_id,
            message_type=MessageType.EVIDENCE_REQUEST,
            session_id=session_id,
            payload={
                "operation_name": operation_name,
                "parameters": parameters,
                "context": context_info,
                "requesting_agent": "orchestrator"
            },
            context={}
        )

        return await self.send_message_and_wait_response(evidence_request)

    def get_a2a_status(self) -> Dict[str, Any]:
        """Get A2A protocol status (from monorepo pattern)"""
        return {
            "registered_agents": len(self.registered_agents),
            "registered_skills": len(self.skills),
            "active_sessions": len(self.active_sessions),
            "pending_responses": len(self.pending_responses),
            "available_judges": len(self.available_judges),
            "available_evidence_gatherers": len(self.available_evidence_gatherers),
            "reflexion_mediators": len(self.reflexion_mediators),
            "message_history_count": len(self.message_history)
        }


@dataclass
class WorkflowStep:
    """A step in a workflow"""
    skill_name: str
    input_mapping: Optional[Dict[str, str]] = None  # Map context keys to skill inputs
    output_mapping: Optional[Dict[str, str]] = None  # Map skill outputs to context keys
    condition: Optional[Callable[[Dict], bool]] = None  # Conditional execution


class Workflow:
    """Defines a workflow as a sequence of skill executions"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.steps: List[WorkflowStep] = []
    
    def add_step(
        self, 
        skill_name: str,
        input_mapping: Optional[Dict[str, str]] = None,
        output_mapping: Optional[Dict[str, str]] = None,
        condition: Optional[Callable[[Dict], bool]] = None
    ):
        """Add a step to the workflow"""
        self.steps.append(WorkflowStep(
            skill_name=skill_name,
            input_mapping=input_mapping,
            output_mapping=output_mapping,
            condition=condition
        ))
        return self
    
    async def execute(
        self, 
        orchestrator: WorkflowOrchestrator,
        input_data: Dict[str, Any]
    ) -> A2AMessage:
        """Execute the workflow"""
        context = {"workflow_input": input_data, "workflow_name": self.name}
        last_response = None
        
        for step in self.steps:
            # Check condition if present
            if step.condition and not step.condition(context):
                continue
            
            # Map inputs from context
            payload = {}
            if step.input_mapping:
                for target_key, source_key in step.input_mapping.items():
                    if source_key in context:
                        payload[target_key] = context[source_key]
            else:
                # Use last response or initial input
                if last_response and last_response.payload.get("result"):
                    payload = {"input": last_response.payload["result"]}
                else:
                    payload = input_data
            
            # Create and route message
            message = A2AMessage(
                message_id=orchestrator.generate_message_id(),
                message_type=MessageType.REQUEST,
                sender_skill=self.name,
                recipient_skill=step.skill_name,
                payload=payload,
                context=context
            )
            
            last_response = await orchestrator.route_message(message)
            
            # Handle errors
            if last_response.message_type == MessageType.ERROR:
                return last_response
            
            # Map outputs to context
            if step.output_mapping and last_response.payload.get("result"):
                result = last_response.payload["result"]
                for target_key, source_key in step.output_mapping.items():
                    if isinstance(result, dict) and source_key in result:
                        context[target_key] = result[source_key]
                    else:
                        context[target_key] = result
        
        return last_response


# ============================================================================
# Example Skills Implementation
# ============================================================================

class DataFetcherSkill(Skill):
    """Example skill that fetches data"""
    
    def __init__(self):
        super().__init__(
            name="data_fetcher",
            description="Fetches data from various sources"
        )
    
    async def process_request(self, message: A2AMessage) -> A2AMessage:
        source = message.payload.get("source", "default")
        query = message.payload.get("query", "")
        
        # Simulate data fetching
        await asyncio.sleep(0.1)
        
        result = {
            "data": f"Fetched data from {source} for query: {query}",
            "source": source,
            "count": 42
        }
        
        return self.create_response(message, result)


class DataProcessorSkill(Skill):
    """Example skill that processes data"""
    
    def __init__(self):
        super().__init__(
            name="data_processor",
            description="Processes and transforms data"
        )
    
    async def process_request(self, message: A2AMessage) -> A2AMessage:
        input_data = message.payload.get("input", {})
        operation = message.payload.get("operation", "transform")
        
        # Simulate processing
        await asyncio.sleep(0.1)
        
        result = {
            "processed_data": f"Processed with {operation}: {input_data}",
            "operation": operation,
            "status": "complete"
        }
        
        return self.create_response(message, result)


class AnalyzerSkill(Skill):
    """Example skill that analyzes data and may delegate to other skills"""
    
    def __init__(self):
        super().__init__(
            name="analyzer",
            description="Analyzes data and delegates to other skills as needed"
        )
    
    async def process_request(self, message: A2AMessage) -> A2AMessage:
        input_data = message.payload.get("input", {})
        
        # Check if we need to fetch more data
        if message.payload.get("needs_data_fetch", False):
            # Delegate to data fetcher
            fetch_response = await self.delegate_to_skill(
                target_skill="data_fetcher",
                payload={
                    "source": "analysis_db",
                    "query": "additional_context"
                },
                context=message.context,
                parent_message_id=message.message_id
            )
            
            if fetch_response.message_type == MessageType.ERROR:
                return fetch_response
            
            input_data = {
                **input_data,
                "additional_data": fetch_response.payload["result"]
            }
        
        # Perform analysis
        result = {
            "analysis": f"Analyzed: {input_data}",
            "insights": ["insight1", "insight2"],
            "confidence": 0.95
        }
        
        return self.create_response(message, result)


class ReportGeneratorSkill(Skill):
    """Example skill that generates reports"""
    
    def __init__(self):
        super().__init__(
            name="report_generator",
            description="Generates formatted reports"
        )
    
    async def process_request(self, message: A2AMessage) -> A2AMessage:
        data = message.payload.get("input", {})
        format_type = message.payload.get("format", "markdown")
        
        # Generate report
        report = f"""
# Analysis Report

**Format**: {format_type}

**Data Summary**:
{json.dumps(data, indent=2)}

**Generated**: Workflow completed successfully
"""
        
        result = {
            "report": report,
            "format": format_type
        }
        
        return self.create_response(message, result)


# ============================================================================
# MCP Server Integration
# ============================================================================

class MCPServer:
    """MCP Server that exposes workflows as tools"""
    
    def __init__(self):
        self.orchestrator = WorkflowOrchestrator()
        self.setup_skills()
        self.setup_workflows()
    
    def setup_skills(self):
        """Register all available skills"""
        skills = [
            DataFetcherSkill(),
            DataProcessorSkill(),
            AnalyzerSkill(),
            ReportGeneratorSkill()
        ]
        
        for skill in skills:
            self.orchestrator.register_skill(skill)
    
    def setup_workflows(self):
        """Define and register workflows"""
        
        # Simple linear workflow
        simple_workflow = Workflow(
            name="simple_analysis",
            description="Fetch, process, and analyze data"
        )
        simple_workflow.add_step(
            skill_name="data_fetcher",
            input_mapping={"source": "workflow_input.source", "query": "workflow_input.query"},
            output_mapping={"fetched_data": "data"}
        ).add_step(
            skill_name="data_processor",
            input_mapping={"input": "fetched_data"},
            output_mapping={"processed_data": "processed_data"}
        ).add_step(
            skill_name="analyzer",
            input_mapping={"input": "processed_data"}
        )
        
        # Complex workflow with delegation
        complex_workflow = Workflow(
            name="full_report",
            description="Complete data analysis with report generation"
        )
        complex_workflow.add_step(
            skill_name="data_fetcher",
            input_mapping={"source": "workflow_input.source", "query": "workflow_input.query"},
            output_mapping={"raw_data": "data"}
        ).add_step(
            skill_name="analyzer",
            input_mapping={"input": "raw_data"},
            output_mapping={"analysis": "analysis"}
        ).add_step(
            skill_name="report_generator",
            input_mapping={"input": "analysis"},
            output_mapping={"final_report": "report"}
        )
        
        self.orchestrator.register_workflow(simple_workflow)
        self.orchestrator.register_workflow(complex_workflow)
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool (workflow) via MCP"""
        try:
            result = await self.orchestrator.execute_workflow(tool_name, arguments)
            
            if result.message_type == MessageType.ERROR:
                return {
                    "success": False,
                    "error": result.payload.get("error", "Unknown error")
                }
            
            return {
                "success": True,
                "result": result.payload.get("result", {}),
                "message_history": [msg.to_dict() for msg in self.orchestrator.message_history[-10:]]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools (workflows) for MCP"""
        tools = []
        
        for workflow_name, workflow in self.orchestrator.workflows.items():
            tools.append({
                "name": workflow_name,
                "description": workflow.description,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Data source"},
                        "query": {"type": "string", "description": "Query string"}
                    }
                }
            })
        
        return tools


# ============================================================================
# Example Usage
# ============================================================================

async def main():
    """Demonstrate the MCP server with A2A protocol"""
    
    print("=" * 80)
    print("MCP Server with Agent-to-Agent Protocol")
    print("=" * 80)
    print()
    
    # Initialize server
    server = MCPServer()
    
    # Show available tools
    print("Available Tools (Workflows):")
    for tool in server.get_available_tools():
        print(f"  - {tool['name']}: {tool['description']}")
    print()
    
    # Execute simple workflow
    print("Executing 'simple_analysis' workflow...")
    print("-" * 80)
    result1 = await server.execute_tool(
        "simple_analysis",
        {
            "source": "database",
            "query": "user_behavior"
        }
    )
    print(f"Success: {result1['success']}")
    print(f"Result: {json.dumps(result1.get('result', {}), indent=2)}")
    print()
    
    # Execute complex workflow
    print("Executing 'full_report' workflow...")
    print("-" * 80)
    result2 = await server.execute_tool(
        "full_report",
        {
            "source": "analytics",
            "query": "quarterly_metrics"
        }
    )
    print(f"Success: {result2['success']}")
    if result2['success']:
        report = result2['result'].get('report', '')
        print(f"Generated Report:\n{report}")
    print()
    
    # Show message history
    print("Message History (last 10 messages):")
    print("-" * 80)
    for msg in result2.get('message_history', []):
        print(f"{msg['sender_skill']} -> {msg['recipient_skill']}: {msg['message_type']}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
