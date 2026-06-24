import os
# Force regional Vertex AI routing unconditionally
os.environ.pop("GOOGLE_GENAI_USE_ENTERPRISE", None)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
import json
import uuid
from google.adk.agents.llm_agent import Agent as AdkAgent
from google.adk.runners import Runner
from google.genai import types

from app.prompt import SYSTEM_INSTRUCTION
from app.tools import show_contact_form, save_contact, consultAgent, discover_agents

from app.app_utils.vertex_gemini import get_model

root_agent = AdkAgent(
    model=get_model("gemini-2.5-flash"),
    name='simple_form_agent',
    description='Managed GEAP agent for rendering a contact form and saving details.',
    instruction=SYSTEM_INSTRUCTION,
    tools=[show_contact_form, save_contact, consultAgent, discover_agents],
)

class SimpleFormAgent:
    def __init__(self):
        self.runner = None

    async def query(self, question: str, context: dict = None) -> str:
        runtime_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Diagnostic debug hook
        if question == "debug_env":
            files = []
            for root, dirs, ffiles in os.walk(runtime_dir):
                for ffiles_in_dir in ffiles:
                    files.append(os.path.relpath(os.path.join(root, ffiles_in_dir), runtime_dir))
            return f"SimpleFormAgent Runtime Dir: {runtime_dir}\nFiles:\n" + "\n".join(files)

        from app import hubscape_adk
        user_id = (context or {}).get("userId") or (context or {}).get("user_id") or "anonymous_user"
        org_id = (context or {}).get("orgId") or (context or {}).get("org_id")
        hub_id = (context or {}).get("hubId") or (context or {}).get("hub_id")
        
        # Stable UUID
        agent_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/Zco-AI-Labs/simple-form-agent"))
        project_id = os.getenv("PROJECT_ID") or os.getenv("GCP_PROJECT_ID") or "hubscape-geap"
        
        remote_ctx = hubscape_adk.RemoteContext(
            user_id=user_id, agent_id=agent_uuid, org_id=org_id, hub_id=hub_id,
            project_id=project_id, raw_context=context
        )
        
        session_id = (context or {}).get("sessionId") or f"session_{user_id}_{hub_id}"
        
        with hubscape_adk.context_session(remote_ctx):
            if not self.runner:
                from google.adk.sessions.in_memory_session_service import InMemorySessionService
                from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
                from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
                from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
                
                self.runner = Runner(
                    agent=root_agent,
                    app_name='simple_form_agent',
                    session_service=InMemorySessionService(),
                    artifact_service=InMemoryArtifactService(),
                    memory_service=InMemoryMemoryService(),
                    credential_service=InMemoryCredentialService(),
                    auto_create_session=True
                )
            
            new_message = types.Content(
                parts=[types.Part.from_text(text=question)]
            )
            
            text_response = ""
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=new_message
            ):
                if event.output:
                    text_response += event.output
                elif event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            text_response += part.text
            
            # Asynchronous action extraction
            actions = getattr(remote_ctx, "actions", [])
            if actions:
                widget_action = next((a for a in actions if a["type"] == "OPEN_AGENT_WIDGET"), None)
                if widget_action:
                    payload = widget_action["payload"]
                    return json.dumps({
                        "directive": "execute_host_tool",
                        "target_tool": "openAgentWidget",
                        "parameters": {
                            "widgetId": payload.get("widgetId"),
                            "widgetConfig": payload.get("widgetConfig"),
                            "data": payload.get("data"),
                            "styling": payload.get("styling"),
                            "userPreferences": payload.get("userPreferences")
                        },
                        "message": text_response
                    })
            
            return text_response

# Singleton instance used as the serialization target
simple_form_agent_app = SimpleFormAgent()

from google.adk.apps import App
app = App(
    root_agent=root_agent,
    name="app",
)

