# Esempio di Utilizzo del Discovery MCP

Questo documento mostra come utilizzare i nuovi metodi di discovery per elencare risorse e prompt disponibili dai server MCP.

## Approccio Ibrido

Dapabot ora utilizza un approccio ibrido per gestire i server MCP:

- **langchain-mcp-adapters**: Per ottenere i tools e integrarli con LangChain
- **SDK nativo MCP**: Per il discovery di risorse e prompt

## Esempio di Codice

```python
import asyncio
from src.mcp.client import get_mcp_client_manager

async def esempio_discovery():
    """Esempio di utilizzo dei metodi di discovery"""
    
    # Ottieni il manager MCP
    manager = get_mcp_client_manager()
    
    # Carica le configurazioni dal database
    manager.carica_configurazioni_da_db()
    
    # Ottieni i nomi dei server configurati
    server_names = manager.get_server_names()
    print(f"Server MCP configurati: {server_names}")
    
    # Per ogni server, elenca risorse e prompt
    for server_name in server_names:
        print(f"\n=== Server: {server_name} ===")
        
        # Elenca le risorse disponibili
        try:
            resources = await manager.list_available_resources(server_name)
            print(f"\nRisorse disponibili ({len(resources)}):")
            for resource in resources:
                print(f"  - {resource['name']}")
                print(f"    URI: {resource['uri']}")
                print(f"    Descrizione: {resource['description']}")
                print(f"    MIME Type: {resource['mimeType']}")
        except Exception as e:
            print(f"  Errore nel recupero risorse: {e}")
        
        # Elenca i prompt disponibili
        try:
            prompts = await manager.list_available_prompts(server_name)
            print(f"\nPrompt disponibili ({len(prompts)}):")
            for prompt in prompts:
                print(f"  - {prompt['name']}")
                print(f"    Descrizione: {prompt['description']}")
                if prompt['arguments']:
                    print(f"    Argomenti:")
                    for arg in prompt['arguments']:
                        required = "obbligatorio" if arg['required'] else "opzionale"
                        print(f"      • {arg['name']} ({required}): {arg['description']}")
        except Exception as e:
            print(f"  Errore nel recupero prompt: {e}")

# Esegui l'esempio
if __name__ == "__main__":
    asyncio.run(esempio_discovery())
```

## Utilizzo nella GUI

I nuovi metodi possono essere integrati nella GUI per mostrare all'utente:

1. **Risorse disponibili**: Elenco di file, documenti, API endpoints, ecc.
2. **Prompt disponibili**: Template di prompt con i loro argomenti

```python
import streamlit as st
import asyncio
from src.mcp.client import get_mcp_client_manager

def mostra_risorse_server(server_name: str):
    """Mostra le risorse disponibili per un server nella GUI"""
    manager = get_mcp_client_manager()
    
    # Esegui la query asincrona
    resources = asyncio.run(manager.list_available_resources(server_name))
    
    if resources:
        st.subheader(f"Risorse di {server_name}")
        for resource in resources:
            with st.expander(resource['name']):
                st.write(f"**URI**: {resource['uri']}")
                st.write(f"**Descrizione**: {resource['description']}")
                st.write(f"**Tipo**: {resource['mimeType']}")
    else:
        st.info(f"Nessuna risorsa disponibile per {server_name}")

def mostra_prompt_server(server_name: str):
    """Mostra i prompt disponibili per un server nella GUI"""
    manager = get_mcp_client_manager()
    
    # Esegui la query asincrona
    prompts = asyncio.run(manager.list_available_prompts(server_name))
    
    if prompts:
        st.subheader(f"Prompt di {server_name}")
        for prompt in prompts:
            with st.expander(prompt['name']):
                st.write(f"**Descrizione**: {prompt['description']}")
                if prompt['arguments']:
                    st.write("**Argomenti**:")
                    for arg in prompt['arguments']:
                        required = "✓" if arg['required'] else "○"
                        st.write(f"- {required} `{arg['name']}`: {arg['description']}")
    else:
        st.info(f"Nessun prompt disponibile per {server_name}")
```

## Caching

I metodi di discovery utilizzano un sistema di caching intelligente:

- La cache viene invalidata automaticamente quando le configurazioni cambiano
- È possibile forzare il refresh passando `use_cache=False`
- La cache viene condivisa tra tutte le chiamate per lo stesso server

```python
# Usa la cache (default)
resources = await manager.list_available_resources("my-server")

# Forza il refresh
resources = await manager.list_available_resources("my-server", use_cache=False)

# Invalida manualmente tutta la cache
manager.invalidate_discovery_cache()
```

## Note Tecniche

### Supporto Transport

I metodi di discovery supportano entrambi i tipi di transport:

- **stdio**: Server locali che comunicano tramite standard input/output
- **http**: Server remoti accessibili via HTTP/SSE

### Gestione Errori

Se un server non è disponibile o non risponde, i metodi restituiscono una lista vuota invece di sollevare un'eccezione. Questo permette alla GUI di continuare a funzionare anche se alcuni server sono offline.

### Performance

- Prima chiamata: Connessione al server + query (~100-500ms)
- Chiamate successive (con cache): Istantanee (~1ms)
- La cache viene invalidata automaticamente quando necessario

## Vantaggi dell'Approccio Ibrido

1. ✅ **Compatibilità**: Mantiene l'integrazione esistente con LangChain
2. ✅ **Estensibilità**: Aggiunge nuove capacità senza rompere il codice esistente
3. ✅ **Performance**: Sistema di caching intelligente per ridurre le chiamate di rete
4. ✅ **Flessibilità**: Supporta sia server locali che remoti
5. ✅ **Robustezza**: Gestione errori che non blocca l'applicazione