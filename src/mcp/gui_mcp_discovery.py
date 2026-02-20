"""
GUI per il discovery di risorse e prompt MCP.
Implementa un dialog con tabs per esplorare e utilizzare risorse e prompt dai server MCP.
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
    
    if "mcp_selected_resources" not in st.session_state:
        st.session_state.mcp_selected_resources = []
    
    if "mcp_selected_prompt" not in st.session_state:
        st.session_state.mcp_selected_prompt = None
    
    if "mcp_recent_resources" not in st.session_state:
        st.session_state.mcp_recent_resources = []
    
    if "mcp_recent_prompts" not in st.session_state:
        st.session_state.mcp_recent_prompts = []
    
    if "mcp_search_query" not in st.session_state:
        st.session_state.mcp_search_query = ""


def _add_to_recent(item: Dict[str, Any], item_type: str, max_recent: int = 5):
    """Aggiunge un elemento alla lista dei recenti"""
    recent_key = f"mcp_recent_{item_type}s"
    recent_list = st.session_state.get(recent_key, [])
    
    # Rimuovi duplicati
    recent_list = [r for r in recent_list if r.get('id') != item.get('id')]
    
    # Aggiungi in testa
    recent_list.insert(0, item)
    
    # Mantieni solo gli ultimi N
    st.session_state[recent_key] = recent_list[:max_recent]


# ──────────────────────────────────────────────────────────────────────────────
# Funzioni di ricerca
# ──────────────────────────────────────────────────────────────────────────────

def _search_items(items: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """Filtra gli elementi in base alla query di ricerca"""
    if not query:
        return items
    
    query_lower = query.lower()
    filtered = []
    
    for item in items:
        # Cerca in nome, descrizione e URI (se presente)
        searchable_text = f"{item.get('name', '')} {item.get('description', '')} {item.get('uri', '')}".lower()
        if query_lower in searchable_text:
            filtered.append(item)
    
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


def _render_resource_item(resource: Dict[str, Any], index: int):
    """Renderizza un singolo elemento risorsa"""
    col1, col2 = st.columns([0.9, 0.1])
    
    with col1:
        with st.expander(f"📄 {resource['name']}", expanded=False):
            st.write(f"**URI**: `{resource['uri']}`")
            if resource.get('description'):
                st.write(f"**Descrizione**: {resource['description']}")
            if resource.get('mimeType'):
                st.write(f"**Tipo**: {resource['mimeType']}")
    
    with col2:
        if st.button("📎", key=f"attach_resource_{index}", help="Allega al prossimo messaggio"):
            resource_id = f"{resource['uri']}_{resource['name']}"
            resource_with_id = {**resource, 'id': resource_id}
            
            # Aggiungi alla selezione corrente
            if resource_with_id not in st.session_state.mcp_selected_resources:
                st.session_state.mcp_selected_resources.append(resource_with_id)
            
            # Aggiungi ai recenti
            _add_to_recent(resource_with_id, 'resource')
            
            st.success(f"✓ Risorsa '{resource['name']}' allegata", icon="✅")
            st.rerun()


def _render_prompt_item(prompt: Dict[str, Any], index: int, server_name: str):
    """Renderizza un singolo elemento prompt"""
    col1, col2 = st.columns([0.9, 0.1])
    
    with col1:
        with st.expander(f"💬 {prompt['name']}", expanded=False):
            if prompt.get('description'):
                st.write(f"**Descrizione**: {prompt['description']}")
            
            if prompt.get('arguments'):
                st.write("**Argomenti**:")
                for arg in prompt['arguments']:
                    required = "✓ obbligatorio" if arg['required'] else "○ opzionale"
                    st.write(f"- `{arg['name']}` ({required}): {arg.get('description', '')}")
    
    with col2:
        if st.button("✨", key=f"use_prompt_{index}", help="Usa come messaggio di sistema"):
            prompt_id = f"{server_name}_{prompt['name']}"
            prompt_with_id = {**prompt, 'id': prompt_id, 'server': server_name}
            
            # Imposta come prompt selezionato
            st.session_state.mcp_selected_prompt = prompt_with_id
            
            # Aggiungi ai recenti
            _add_to_recent(prompt_with_id, 'prompt')
            
            st.success(f"✓ Prompt '{prompt['name']}' impostato", icon="✅")
            st.rerun()


def _render_resources_tab(server_name: str):
    """Renderizza il tab delle risorse"""
    st.subheader(f"Risorse di {server_name}")
    
    # Barra di ricerca
    search_query = st.text_input(
        "🔍 Cerca risorse",
        value=st.session_state.mcp_search_query,
        key="resource_search",
        placeholder="Cerca per nome, descrizione o URI..."
    )
    st.session_state.mcp_search_query = search_query
    
    # Carica risorse
    manager = get_mcp_client_manager()
    
    with st.spinner("Caricamento risorse..."):
        try:
            resources = asyncio.run(manager.list_available_resources(server_name))
            
            # Applica filtro di ricerca
            filtered_resources = _search_items(resources, search_query)
            
            if not filtered_resources:
                if search_query:
                    st.info(f"Nessuna risorsa trovata per '{search_query}'")
                else:
                    st.info("Nessuna risorsa disponibile")
            else:
                st.write(f"**{len(filtered_resources)} risorse trovate**")
                
                # Renderizza ogni risorsa
                for idx, resource in enumerate(filtered_resources):
                    _render_resource_item(resource, idx)
                    
        except Exception as e:
            st.error(f"Errore nel caricamento risorse: {e}")


def _render_prompts_tab(server_name: str):
    """Renderizza il tab dei prompt"""
    st.subheader(f"Prompt di {server_name}")
    
    # Barra di ricerca
    search_query = st.text_input(
        "🔍 Cerca prompt",
        value=st.session_state.mcp_search_query,
        key="prompt_search",
        placeholder="Cerca per nome o descrizione..."
    )
    st.session_state.mcp_search_query = search_query
    
    # Carica prompt
    manager = get_mcp_client_manager()
    
    with st.spinner("Caricamento prompt..."):
        try:
            prompts = asyncio.run(manager.list_available_prompts(server_name))
            
            # Applica filtro di ricerca
            filtered_prompts = _search_items(prompts, search_query)
            
            if not filtered_prompts:
                if search_query:
                    st.info(f"Nessun prompt trovato per '{search_query}'")
                else:
                    st.info("Nessun prompt disponibile")
            else:
                st.write(f"**{len(filtered_prompts)} prompt trovati**")
                
                # Renderizza ogni prompt
                for idx, prompt in enumerate(filtered_prompts):
                    _render_prompt_item(prompt, idx, server_name)
                    
        except Exception as e:
            st.error(f"Errore nel caricamento prompt: {e}")


def _render_recent_items():
    """Renderizza la sezione degli elementi recenti"""
    st.subheader("📌 Usati di recente")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Risorse**")
        recent_resources = st.session_state.get('mcp_recent_resources', [])
        if recent_resources:
            for idx, resource in enumerate(recent_resources[:3]):
                if st.button(
                    f"📄 {resource['name'][:30]}...",
                    key=f"recent_resource_{idx}",
                    use_container_width=True
                ):
                    if resource not in st.session_state.mcp_selected_resources:
                        st.session_state.mcp_selected_resources.append(resource)
                        st.success(f"✓ Risorsa allegata", icon="✅")
                        st.rerun()
        else:
            st.caption("Nessuna risorsa recente")
    
    with col2:
        st.write("**Prompt**")
        recent_prompts = st.session_state.get('mcp_recent_prompts', [])
        if recent_prompts:
            for idx, prompt in enumerate(recent_prompts[:3]):
                if st.button(
                    f"💬 {prompt['name'][:30]}...",
                    key=f"recent_prompt_{idx}",
                    use_container_width=True
                ):
                    st.session_state.mcp_selected_prompt = prompt
                    st.success(f"✓ Prompt impostato", icon="✅")
                    st.rerun()
        else:
            st.caption("Nessun prompt recente")


def _render_selected_items():
    """Renderizza la sezione degli elementi selezionati"""
    st.divider()
    st.subheader("✓ Selezione corrente")
    
    # Risorse selezionate
    selected_resources = st.session_state.get('mcp_selected_resources', [])
    if selected_resources:
        st.write(f"**Risorse allegate ({len(selected_resources)})**:")
        for idx, resource in enumerate(selected_resources):
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                st.caption(f"📄 {resource['name']}")
            with col2:
                if st.button("❌", key=f"remove_resource_{idx}", help="Rimuovi"):
                    st.session_state.mcp_selected_resources.remove(resource)
                    st.rerun()
    
    # Prompt selezionato
    selected_prompt = st.session_state.get('mcp_selected_prompt')
    if selected_prompt:
        st.write("**Prompt come messaggio di sistema**:")
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.caption(f"💬 {selected_prompt['name']} (da {selected_prompt.get('server', 'N/A')})")
        with col2:
            if st.button("❌", key="remove_prompt", help="Rimuovi"):
                st.session_state.mcp_selected_prompt = None
                st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Dialog principale
# ──────────────────────────────────────────────────────────────────────────────

@st.dialog("🔍 MCP Discovery - Risorse e Prompt", width="large")
def mostra_dialog_mcp_discovery():
    """Mostra il dialog per il discovery di risorse e prompt MCP"""
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
        _render_recent_items()
    
    with col_content:
        if selected_server:
            # Tabs per risorse e prompt
            tab_resources, tab_prompts = st.tabs(["📄 Risorse", "💬 Prompt"])
            
            with tab_resources:
                _render_resources_tab(selected_server)
            
            with tab_prompts:
                _render_prompts_tab(selected_server)
            
            # Mostra selezione corrente
            _render_selected_items()
    
    # Pulsanti azione
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔄 Aggiorna cache", use_container_width=True):
            manager.invalidate_discovery_cache()
            st.success("Cache invalidata", icon="✅")
            st.rerun()
    
    with col2:
        if st.button("🗑️ Pulisci selezione", use_container_width=True):
            st.session_state.mcp_selected_resources = []
            st.session_state.mcp_selected_prompt = None
            st.success("Selezione pulita", icon="✅")
            st.rerun()
    
    with col3:
        if st.button("✓ Applica e chiudi", type="primary", use_container_width=True):
            st.session_state.mcp_discovery_open = False
            st.rerun()


def mostra_quick_access_buttons():
    """Mostra i pulsanti di quick access per risorse e prompt recenti nella chat"""
    _init_discovery_state()
    
    # Pulsante per aprire il dialog
    if st.button("🔍 MCP Discovery", use_container_width=True, help="Esplora risorse e prompt MCP"):
        st.session_state.mcp_discovery_open = True
        st.rerun()
    
    # Mostra elementi selezionati in modo compatto
    selected_resources = st.session_state.get('mcp_selected_resources', [])
    selected_prompt = st.session_state.get('mcp_selected_prompt')
    
    if selected_resources or selected_prompt:
        with st.expander("✓ Selezione MCP attiva", expanded=False):
            if selected_resources:
                st.caption(f"📎 {len(selected_resources)} risorsa/e allegata/e")
            if selected_prompt:
                st.caption(f"💬 Prompt: {selected_prompt['name']}")


def get_selected_mcp_resources() -> List[Dict[str, Any]]:
    """Ottiene le risorse MCP selezionate"""
    _init_discovery_state()
    return st.session_state.get('mcp_selected_resources', [])


def get_selected_mcp_prompt() -> Optional[Dict[str, Any]]:
    """Ottiene il prompt MCP selezionato"""
    _init_discovery_state()
    return st.session_state.get('mcp_selected_prompt')


def clear_mcp_selection():
    """Pulisce la selezione MCP dopo l'invio del messaggio"""
    st.session_state.mcp_selected_resources = []
    st.session_state.mcp_selected_prompt = None


# Made with Bob