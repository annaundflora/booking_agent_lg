from typing import Dict, TypedDict, Annotated, Literal, Optional, List
from langgraph.graph import Graph, StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.callbacks import get_openai_callback
from dotenv import load_dotenv
from IPython.display import Image, display
import os
from pathlib import Path
from pydantic import BaseModel, Field
from enum import IntEnum
import streamlit as st
from chat_window import create_chat_ui, get_user_input, initialize_chat_state

# Lade die Umgebungsvariablen aus .env
load_dotenv()

# Stelle sicher, dass der API Key geladen wurde
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY nicht in .env gefunden")

# Definition der Load Carrier Codes
class LoadCarrier(IntEnum):
    """Definiert die möglichen Ladungsträger mit ihren Codes."""
    PALETTE = 1
    PAKET = 2
    GITTERBOX = 3
    DOKUMENTE = 4
    SONSTIGE = 5

class ShipmentItem(BaseModel):
    load_carrier: LoadCarrier = Field(..., description="Code des Ladungsträgers (1=Palette, 2=Paket, 3=Gitterbox, 4=Dokumente, 5=Sonstige)")
    name: str = Field("", description="Name des Items")
    quantity: int = Field(1, ge=1, description="Anzahl der Items")
    length: Optional[float] = Field(None, gt=0, description="Länge in cm")
    width: Optional[float] = Field(None, gt=0, description="Breite in cm")
    height: Optional[float] = Field(None, gt=0, description="Höhe in cm")
    weight: Optional[float] = Field(None, gt=0, description="Gewicht in kg")
    stackable: Literal["yes", "no"] = Field("no", description="Stapelbarkeit (yes/no)")
    notes: Optional[str] = Field(None, description="Zusätzliche Hinweise")

class Shipment(BaseModel):
    items: List[ShipmentItem] = Field(default_factory=list, description="Liste der Sendungsitems")

class TransportDetails(BaseModel):
    pickup_address: Optional[str] = Field(None, description="Abholadresse")
    pickup_datetime: Optional[str] = Field(None, description="Abholdatum und -zeit")
    delivery_address: Optional[str] = Field(None, description="Zustelladresse")

class BookingState(BaseModel):
    items: List[Dict] = []
    pickup_address: Optional[Dict] = None
    delivery_address: Optional[Dict] = None
    shipment: Shipment = Field(default_factory=Shipment)
    transport: TransportDetails = Field(default_factory=TransportDetails)
    current_item_index: int = Field(0, description="Index des aktuellen Items")
    current_focus: str = Field("load_carrier", description="Aktueller Fokus der Abfrage")

    def __init__(self, **data):
        super().__init__(**data)
        if not self.shipment.items:
            self.add_new_item()

    def add_new_item(self):
        """Fügt ein neues leeres Item zur Sendung hinzu"""
        self.shipment.items.append(ShipmentItem(
            load_carrier=LoadCarrier.PALETTE,
            name="",
            quantity=1,
            stackable="no"
        ))

    def format_context(self) -> str:
        """Formatiert den Buchungsstatus als Kontext für das Modell"""
        current_item = self.shipment.items[self.current_item_index]
        
        return f"""
Buchungsstatus:
1. Aktuelles Item ({self.current_item_index + 1} von {len(self.shipment.items)}):
   - Ladungsträger: {LoadCarrier(current_item.load_carrier).name if current_item.load_carrier else 'Nicht gesetzt'}
   - Name: {current_item.name if current_item.name else 'Nicht gesetzt'}
   - Anzahl: {current_item.quantity}
   - Maße (LxBxH): {current_item.length or '-'} x {current_item.width or '-'} x {current_item.height or '-'} cm
   - Gewicht: {current_item.weight or '-'} kg
   - Stapelbar: {current_item.stackable}
   - Hinweise: {current_item.notes if current_item.notes else 'Keine'}

2. Transport Details:
   - Abholadresse: {self.transport.pickup_address or 'Nicht gesetzt'}
   - Abholdatum/-zeit: {self.transport.pickup_datetime or 'Nicht gesetzt'}
   - Lieferadresse: {self.transport.delivery_address or 'Nicht gesetzt'}

3. Nächster Schritt:
   - Fokus: {self.current_focus}
"""

# Anpassung der AgentState Definition
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], "Der Chatverlauf"]
    next: Annotated[str, "Nächster Schritt im Workflow"]
    booking: Annotated[BookingState, "Status der Buchung"]

# Erstellen des Chat-Models mit expliziten Parametern
model = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    streaming=False,
    request_timeout=10
)

def load_instructions(file_path: str = "instructions.md") -> str:
    """Lädt die System-Instruktionen aus einer Markdown-Datei."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Warnung: {file_path} nicht gefunden. Verwende Standard-Instruktionen.")
        return """Du bist ein hilfreicher Transport-Booking Agent. 
        Deine Aufgabe ist es, Kunden bei der Buchung von Transporten zu unterstützen."""
    except Exception as e:
        print(f"Fehler beim Lesen der Instruktionen: {e}")
        return """Du bist ein hilfreicher Transport-Booking Agent. 
        Deine Aufgabe ist es, Kunden bei der Buchung von Transporten zu unterstützen."""

# Lade die Instruktionen
system_instructions = load_instructions()

# Angepasstes Prompt Template
booking_agent_prompt = ChatPromptTemplate.from_messages([
    ("system", system_instructions),
    ("system", "Aktueller Buchungsstatus: {context}"),
    MessagesPlaceholder(variable_name="messages"),
    ("human", "{input}")
])

def should_continue(state: AgentState) -> Literal["chat", END]:
    """Bestimmt, ob der Graph weiterlaufen soll."""
    if not state["messages"]:
        return "chat"
    
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage):
        return END
    if isinstance(last_message, HumanMessage) and last_message.content.lower() == "quit":
        return END
    return "chat"

def create_initial_state() -> AgentState:
    """Erstellt den initialen State mit Booking-Informationen und Begrüßungsnachricht."""
    welcome_message = AIMessage(content="""
Willkommen! Ich bin Ihr Transport-Booking Assistant. 
Ich helfe Ihnen bei der Buchung Ihres Transports und führe Sie Schritt für Schritt durch den Prozess.

Wir erfassen zunächst die Details Ihrer Sendung (Ladungsträger, Maße, Gewicht etc.) und anschließend die Transport-Informationen (Abhol- und Lieferadresse).

Lassen Sie uns beginnen! Welchen Ladungsträger benötigen Sie für das erste Item?
- Palette (Code 1)
- Paket (Code 2)
- Gitterbox (Code 3)
- Dokumente (Code 4)
- Sonstige (Code 5)
""".strip())

    return {
        "messages": [welcome_message],
        "next": "chat",
        "booking": BookingState()
    }

def chat_node(state: AgentState) -> AgentState:
    """Verarbeitet die Benutzereingabe und generiert eine Antwort."""
    messages = state["messages"]
    booking = state["booking"]
    
    try:
        with get_openai_callback() as cb:
            response = model.invoke(
                booking_agent_prompt.format_messages(
                    messages=messages[:-1],
                    context=booking.format_context(),
                    input=messages[-1].content
                )
            )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Fehler bei der Modellanfrage: {error_details}")
        return {
            "messages": messages + [AIMessage(content="Entschuldigung, es gab einen technischen Fehler. Bitte versuchen Sie es erneut.")],
            "next": END,
            "booking": booking
        }
    
    return {
        "messages": messages + [AIMessage(content=response.content)],
        "next": "chat",
        "booking": booking
    }

def create_workflow() -> Graph:
    """Erstellt und konfiguriert den Workflow-Graphen."""
    workflow = StateGraph(AgentState)
    
    # Konfiguriere den Graphen
    workflow.add_node("chat", chat_node)
    workflow.set_entry_point("chat")
    workflow.add_conditional_edges(
        "chat",
        should_continue,
        {
            "chat": "chat",
            END: END
        }
    )
    
    # Visualisiere den Workflow
    try:
        graph = workflow.compile()
        png_data = graph.get_graph().draw_mermaid_png()
        with open("workflow_graph.png", "wb") as f:
            f.write(png_data)
        print("Workflow-Diagramm wurde als 'workflow_graph.png' gespeichert.")
    except Exception as e:
        print(f"Visualisierung konnte nicht erstellt werden: {e}")
    
    return workflow.compile()

def main() -> None:
    """Hauptfunktion für die Benutzerinteraktion mit Streamlit."""
    from chat_window import create_chat_ui, get_user_input, initialize_chat_state
    
    # Initialisiere zuerst den Chat-State
    initialize_chat_state()
    
    # Erstelle den Workflow nur einmal und speichere ihn im Session State
    if "agent" not in st.session_state:
        st.session_state.agent = create_workflow()
    
    # Initialisiere den Agent-State
    if "agent_state" not in st.session_state:
        st.session_state.agent_state = create_initial_state()
        st.session_state.messages.append(st.session_state.agent_state["messages"][0])
    
    # Kein Booking-Objekt mehr übergeben
    create_chat_ui()
    
    user_input = get_user_input()
    if user_input:
        st.session_state.agent_state["messages"].append(HumanMessage(content=user_input))
        st.session_state.messages.append(HumanMessage(content=user_input))
        
        result = st.session_state.agent.invoke(st.session_state.agent_state)
        st.session_state.agent_state = result
        
        if result["messages"]:
            bot_message = result["messages"][-1]
            if isinstance(bot_message, AIMessage):
                st.session_state.messages.append(bot_message)
        
        st.rerun()

if __name__ == "__main__":
    main() 