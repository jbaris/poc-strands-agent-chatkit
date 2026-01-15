from datetime import datetime
from typing import Any, AsyncIterator

from agents import Agent

from chatkit.server import ChatKitServer
from chatkit.store import AttachmentStore, Store
from chatkit.types import (
    ThreadMetadata,
    UserMessageItem,
    ThreadStreamEvent,
    ThreadItemAddedEvent,
    ThreadItemUpdated,
    AssistantMessageItem,
    AssistantMessageContentPartTextDelta, AssistantMessageContent,
)
from chatkit.types import (
    UserMessageTextContent,
)

from strands import Agent
from strands.models.openai import OpenAIModel

import base64
import os
import logging

# Enables Strands debug log level
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# This builds the Basic Auth header required for the OTLP endpoint
LANGFUSE_AUTH = base64.b64encode(
    f"{os.environ.get('LANGFUSE_PUBLIC_KEY')}:{os.environ.get('LANGFUSE_SECRET_KEY')}".encode()
).decode()
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {LANGFUSE_AUTH}"

# Enables telemetry with OTLP exporter
from strands.telemetry import StrandsTelemetry
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

class MyChatKitServer(ChatKitServer):
    def __init__(
        self, data_store: Store, attachment_store: AttachmentStore | None = None
    ):
        super().__init__(data_store, attachment_store)
        model = OpenAIModel(
            client_args={
                "api_key": os.getenv("OPENAI_API_KEY"),
            },
            model_id="gpt-4o-mini"
        )
        self.agent = Agent(
            model=model,
            system_prompt="You are a helpful assistant."
        )

    async def respond(
            self,
            thread: ThreadMetadata,
            input_item: UserMessageItem | None,  # Input can be None (e.g., tool outputs)
            context: Any,
    ) -> AsyncIterator[ThreadStreamEvent]:

        # Extract the user's input text
        user_text = ""
        if input_item and isinstance(input_item, UserMessageItem):
            for content in input_item.content:
                if isinstance(content, UserMessageTextContent):
                    user_text += content.text
        if not user_text:
            return

        # Create a placeholder for the Assistant's response
        message_id = self.store.generate_item_id("message", thread, context)
        yield ThreadItemAddedEvent(
            item=AssistantMessageItem(
                created_at=datetime.now(),
                id=message_id,
                thread_id=thread.id,
                content=[AssistantMessageContent(text="")]  # Initial empty content
            )
        )

        # Call the Strands Agent and stream the response
        async for event in self.agent.stream_async(user_text):
            chunk = ""
            if isinstance(event, dict):
                chunk = event.get("data", "")
            if chunk:
                yield ThreadItemUpdated(
                    item_id=message_id,
                    update=AssistantMessageContentPartTextDelta(
                        content_index=0,
                        delta=chunk
                    )
                )
