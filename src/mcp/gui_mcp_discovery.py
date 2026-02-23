"""
GUI per il discovery di tools, risorse e prompt MCP.
Implementa un dialog con tabs per esplorare cosa offre ogni server MCP prima di attivarlo.
"""

import streamlit as st
import asyncio
from typing import Dict, List, Any, Optional
from src.mcp.client import get_mcp_client_manager


# ──────────────────────────────────────────────────────────────────────────────
# Gestione stato sessione
# ──────────────────────────────────────────────────────────────────────────────

def _init_discovery_state():
    """Inizializza lo stato della sessione per il discovery MCP"""
    if "mcp_discovery_open" not in st.session_state:
        st.session_state.mcp_discovery_open = False
    
    if "mcp_selected_server" not in st.session_state:
        st.session_state.mcp_selected_server = None
    
    if "mcp_preview_data" not in st.session_state:
        st.session_state.mcp_preview_data = {}
    
    if "mcp_search_query" not in st.session_state:
        st.session_state.mcp_search_query = ""


# ──────────────────────────────────────────────────────────────────────────────
# Funzioni di ricerca
# ──────────────────────────────────────────────────────────────────────────────

def _search_tools(tools: List[Any], query: str) -> List[Any]:
    """Filtra i tools in base alla query di ricerca"""
    if not query:
        return tools
    
    query_lower = query.lower()
    filtered = []
    
    for tool in tools:
        # Cerca in nome e descrizione
        name = getattr(tool, 'name', '')
        description = getattr(tool, 'description', '')
        searchable_text = f"{name} {description}".lower()
        
        if query_lower in searchable_text:
            filtered.append(tool)
    
    return filtered


# ──────────────────────────────────────────────────────────────────────────────
# Componenti UI
# ──────────────────────────────────────────────────────────────────────────────

def _render_server_list(servers: List[str]) -> Optional[str]:
    """Renderizza la lista dei server MCP"""
    if not servers:
        st.info("Nessun server MCP configurato")
        return None
    
    st.subheader("Server MCP")
    
    selected = st.radio(
        "Seleziona server",
        servers,
        key="mcp_server_selector",
        label_visibility="collapsed"
    )
    
    return selected


def _render_tool_item(tool: Any, index: int, tool_type: str):
    """
    Renderizza un singolo elemento (tool, risorsa o prompt).
    
    Args:
        tool: Tool LangChain da visualizzare
        index: Indice per chiavi univoche
        tool_type: Tipo ('tool', 'resource', 'prompt')
    """
    # Icone per tipo
    icons = {
        'tool': '🔧',
        'resource': '📄',
        'prompt': '💬'
    }
    icon = icons.get(tool_type, '🔹')
    
    name = getattr(tool, 'name', 'Unknown')
    description = getattr(tool, 'description', 'Nessuna descrizione disponibile')
    
    with st.expander(f"{icon} {name}", expanded=False):
        st.write(f"**Descrizione**: {description}")
        
        # Mostra schema argomenti se disponibile
        if hasattr(tool, 'args_schema') and tool.args_schema:
            st.write("**Argomenti**:")
            try:
                # Prova a ottenere lo schema
                if hasattr(tool.args_schema, 'schema'):
                    schema = tool.args_schema.schema()
                    properties = schema.get('properties', {})
                    required = schema.get('required', [])
                    
                    for arg_name, arg_info in properties.items():
                        is_required = "✓ obbligatorio" if arg_name in required else "○ opzionale"
                        arg_desc = arg_info.get('description', '')
                        arg_type = arg_info.get('type', 'any')
                        st.write(f"- `{arg_name}` ({arg_type}, {is_required}): {arg_desc}")
            except Exception:
                st.caption("Schema argomenti non disponibile")


def _render_tools_tab(tools: List[Any]):
    """Renderizza il tab dei tools"""
    st.subheader("🔧 Tools")
    
    # Barra di ricerca
    search_query = st.text_input(
        "🔍 Cerca tools",
        value=st.session_state.mcp_search_query,
        key="tool_search",
        placeholder="Cerca per nome o descrizione..."
    )
    st.session_state.mcp_search_query = search_query
    
    # Applica filtro di ricerca
    filtered_tools = _search_tools(tools, search_query)
    
    if not filtered_tools:
        if search_query:
            st.info(f"Nessun tool trovato per '{search_query}'")
        else:
            st.info("Nessun tool disponibile")
    else:
        st.write(f"**{len(filtered_tools)} tools trovati**")
        
        # Renderizza ogni tool
        for idx, tool in enumerate(filtered_tools):
            _render_tool_item(tool, idx, 'tool')


def _render_resources_tab(resources: List[Any]):
    """Renderizza il tab delle risorse"""
    st.subheader("📄 Risorse")
    
    # Barra di ricerca
    search_query = st.text_input(
        "🔍 Cerca risorse",
        value=st.session_state.mcp_search_query,
        key="resource_search",
        placeholder="Cerca per nome o descrizione..."
    )
    st.session_state.mcp_search_query = search_query
    
    # Applica filtro di ricerca
    filtered_resources = _search_tools(resources, search_query)
    
    if not filtered_resources:
        if search_query:
            st.info(f"Nessuna risorsa trovata per '{search_query}'")
        else:
            st.info("Nessuna risorsa disponibile")
    else:
        st.write(f"**{len(filtered_resources)} risorse trovate**")
        st.caption("Le risorse sono esposte come tools che l'agent può chiamare per ottenere contenuti.")
        
        # Renderizza ogni risorsa
        for idx, resource in enumerate(filtered_resources):
            _render_tool_item(resource, idx, 'resource')


def _render_prompts_tab(prompts: List[Any]):
    """Renderizza il tab dei prompt"""
    st.subheader("💬 Prompt")
    
    # Barra di ricerca
    search_query = st.text_input(
        "🔍 Cerca prompt",
        value=st.session_state.mcp_search_query,
        key="prompt_search",
        placeholder="Cerca per nome o descrizione..."
    )
    st.session_state.mcp_search_query = search_query
    
    # Applica filtro di ricerca
    filtered_prompts = _search_tools(prompts, search_query)
    
    if not filtered_prompts:
        if search_query:
            st.info(f"Nessun prompt trovato per '{search_query}'")
        else:
            st.info("Nessun prompt disponibile")
    else:
        st.write(f"**{len(filtered_prompts)} prompt trovati**")
        st.caption("I prompt sono esposti come tools che l'agent può chiamare per ottenere template di messaggi.")
        
        # Renderizza ogni prompt
        for idx, prompt in enumerate(filtered_prompts):
            _render_tool_item(prompt, idx, 'prompt')


def _render_summary_info(tools_count: int, resources_count: int, prompts_count: int):
    """Renderizza il riepilogo delle informazioni"""
    st.divider()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🔧 Tools", tools_count)
    
    with col2:
        st.metric("📄 Risorse", resources_count)
    
    with col3:
        st.metric("💬 Prompt", prompts_count)
    
    with col4:
        total = tools_count + resources_count + prompts_count
        st.metric("📊 Totale", total)
    
    if total > 0:
        st.info(
            "💡 **Nota**: Quando attivi questo server MCP, tutti questi elementi "
            "saranno disponibili per l'agent in modalità agentica."
        )


async def _load_preview_data(server_name: str) -> Dict[str, List[Any]]:
    """
    Carica i dati di preview per un server specifico.
    
    Args:
        server_name: Nome del server
        
    Returns:
        Dizionario con tools, resources e prompts
    """
    manager = get_mcp_client_manager()
    
    # Ottieni l'adapter
    adapter = manager.get_adapter()
    client = manager.get_client()
    
    # Crea tutti gli elementi
    await adapter.create_all(client)
    
    return {
        'tools': adapter.tools,
        'resources': adapter.resources,
        'prompts': adapter.prompts
    }


# ──────────────────────────────────────────────────────────────────────────────
# Dialog principale
# ──────────────────────────────────────────────────────────────────────────────

@st.dialog("🔍 MCP Discovery - Preview Server", width="large")
def mostra_dialog_mcp_discovery():
    """Mostra il dialog per il discovery di tools, risorse e prompt MCP"""
    _init_discovery_state()
    
    # Ottieni lista server
    manager = get_mcp_client_manager()
    manager.carica_configurazioni_da_db()
    servers = manager.get_server_names()
    
    if not servers:
        st.warning("Nessun server MCP configurato. Configura almeno un server nella sezione MCP.")
        if st.button("Chiudi"):
            st.session_state.mcp_discovery_open = False
            st.rerun()
        return
    
    # Layout principale: sidebar con server + contenuto principale
    col_servers, col_content = st.columns([0.25, 0.75])
    
    with col_servers:
        selected_server = _render_server_list(servers)
        st.session_state.mcp_selected_server = selected_server
        
        st.divider()
        
        # Pulsante per ricaricare
        if st.button("🔄 Ricarica", use_container_width=True):
            # Invalida cache per forzare ricaricamento
            manager.invalidate_cache()
            if selected_server in st.session_state.mcp_preview_data:
                del st.session_state.mcp_preview_data[selected_server]
            st.rerun()
    
    with col_content:
        if selected_server:
            # Carica dati di preview se non in cache
            if selected_server not in st.session_state.mcp_preview_data:
                with st.spinner(f"Caricamento preview per {selected_server}..."):
                    try:
                        preview_data = asyncio.run(_load_preview_data(selected_server))
                        st.session_state.mcp_preview_data[selected_server] = preview_data
                    except Exception as e:
                        st.error(f"Errore nel caricamento preview: {e}")
                        return
            
            # Ottieni dati dalla cache
            preview_data = st.session_state.mcp_preview_data.get(selected_server, {})
            tools = preview_data.get('tools', [])
            resources = preview_data.get('resources', [])
            prompts = preview_data.get('prompts', [])
            
            # Mostra riepilogo
            _render_summary_info(len(tools), len(resources), len(prompts))
            
            # Tabs per tools, risorse e prompt
            tab_tools, tab_resources, tab_prompts = st.tabs([
                f"🔧 Tools ({len(tools)})",
                f"📄 Risorse ({len(resources)})",
                f"💬 Prompt ({len(prompts)})"
            ])
            
            with tab_tools:
                _render_tools_tab(tools)
            
            with tab_resources:
                _render_resources_tab(resources)
            
            with tab_prompts:
                _render_prompts_tab(prompts)
    
    # Pulsante chiudi
    st.divider()
    if st.button("✓ Chiudi", type="primary", use_container_width=True):
        st.session_state.mcp_discovery_open = False
        st.rerun()


def mostra_quick_access_button():
    """Mostra il pulsante di quick access per aprire il discovery"""
    _init_discovery_state()
    
    # Pulsante per aprire il dialog
    if st.button("🔍 MCP Discovery", use_container_width=True, help="Esplora tools, risorse e prompt MCP"):
        st.session_state.mcp_discovery_open = True
        st.rerun()


# Funzioni di compatibilità (mantenute per non rompere codice esistente)
def get_selected_mcp_resources() -> List[Dict[str, Any]]:
    """Funzione di compatibilità - ritorna lista vuota"""
    return []


def get_selected_mcp_prompt() -> Optional[Dict[str, Any]]:
    """Funzione di compatibilità - ritorna None"""
    return None


def clear_mcp_selection():
    """Funzione di compatibilità - non fa nulla"""
    pass


# Made with Bob