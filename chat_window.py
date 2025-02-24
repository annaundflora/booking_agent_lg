import streamlit as st
from typing import List
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage

def initialize_chat_state():
    """Initialisiert den Chat-Status in der Streamlit Session."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

def display_message(message: BaseMessage):
    """Zeigt eine einzelne Nachricht im Chat an."""
    is_ai = isinstance(message, AIMessage)
    with st.chat_message("assistant" if is_ai else "user"):
        st.write(message.content)

def render_chat_messages(messages: List[BaseMessage]):
    """Rendert die Chat-Nachrichten."""
    for message in messages:
        display_message(message)

def get_user_input() -> str | None:
    """Erfasst die Benutzereingabe über das Streamlit Chat-Input."""
    return st.chat_input("Ihre Nachricht...")

def display_address(address: dict, title: str):
    """Zeigt eine einzelne Adresse an."""
    if address:
        st.write(f"**{title}:**")
        st.write(f"- {address.get('name', '-')}")
        st.write(f"- {address.get('street', '-')}")
        st.write(f"- {address.get('postal_code', '-')} {address.get('city', '-')}")
        st.write(f"- {address.get('country', '-')}")
    else:
        st.info(f"{title} noch nicht angegeben")

def display_transport_data(booking):
    """Zeigt die Transportdaten in einer übersichtlichen Form an."""
    with st.container():
        # Adressen anzeigen
        with st.expander("📍 Adressen", expanded=True):
            cols = st.columns(2)
            with cols[0]:
                display_address(getattr(booking, 'pickup_address', {}), "Abholadresse")
            with cols[1]:
                display_address(getattr(booking, 'delivery_address', {}), "Lieferadresse")
        
        # Ladungsdaten anzeigen
        st.subheader("Ladungsdaten")
        if not booking.items:
            st.info("Noch keine Ladung eingegeben")
            return
            
        # Für jedes Item eine Karte erstellen
        for idx, item in enumerate(booking.items, 1):
            with st.expander(f"📦 Ladung {idx}: {item.get('name', 'Unbenannt')}", expanded=True):
                cols = st.columns(2)
                with cols[0]:
                    st.write("📐 Abmessungen:")
                    st.write(f"- Länge: {item.get('length', '-')} cm")
                    st.write(f"- Breite: {item.get('width', '-')} cm")
                    st.write(f"- Höhe: {item.get('height', '-')} cm")
                
                with cols[1]:
                    st.write("⚖️ Weitere Details:")
                    st.write(f"- Gewicht: {item.get('weight', '-')} kg")
                    st.write(f"- Menge: {item.get('quantity', '-')} Stück")
                    st.write(f"- Stapelbar: {'Ja' if item.get('stackable') == 'yes' else 'Nein'}")
                    st.write(f"- Ladungsträger: {item.get('load_carrier', '-')}")

def create_chat_ui():
    """Erstellt die Chat-Benutzeroberfläche."""
    st.title("Transport Booking Assistant")
    
    # Chat-Container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    render_chat_messages(st.session_state.messages)
    st.markdown('</div>', unsafe_allow_html=True) 