# Transport Booking Agent

## Ziele

Erstellen eines Chatbots, der die Buchung von Transportdiensten ermöglicht.

## Voraussetzungen

- Python 3.x
- LangChain und LangGraph
- Sprachmodelle
- Streamlit

## Funktionen

- Chat Interface für die Benutzerinteraktion
- Anzeige der bereits eingegebenen Daten in einem Container neben dem Chat Interface
- Der Bot führt durch den Prozess der Buchung
- Validierung der Eingaben nach Validierungsregeln
- Aufbereitung der Daten in Ausgabeformat zu weiterer Verarbeitung

## Ausgabeformat

{
    "items": [
        {
            "load_carrier": 1,
            "name": "spare parts",
            "quantity": 1,
            "length": 120,
            "width": 100,
            "height": 80,
            "weight": 320,
            "stackable": "no"
        },
        {
            "load_carrier": 1,
            "name": "motor parts",
            "quantity": 2,
            "length": 120,
            "width": 100,
            "height": 120,
            "weight": 500,
            "stackable": "no"
        }
    ]
}

## User Anforderungen

- User können die Daten jederzeit anzeigen und ändern
- User können die Reihenfolge der Eingaben ändern
- User können ganze Texte eingeben, aus denen der Bot die notwendigen Daten extrahiert

