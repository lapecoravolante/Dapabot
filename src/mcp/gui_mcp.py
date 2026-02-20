"""
Interfaccia GUI per la gestione dei server MCP in Streamlit.
Dialog modale per configurazione server MCP, simile al sistema tools.
"""

import streamlit as st
from src.ConfigurazioneDB import ConfigurazioneDB
from src.mcp.client import get_mcp_client_manager


def _on_close_mcp_dialog():
    """
    Callback chiamato quando la dialog MCP viene chiusa.
    Aggiorna il DB con le selezioni fatte nel multiselect.
    Gestisce individualmente TUTTI i server che cambiano stato (locali e remoti).
    """
    st.session_state["mcp_dialog_open"] = False
    
    # Aggiorna il DB solo se ci sono modifiche
    if "mcp_servers_selezionati_temp" in st.session_state:
        servers_selezionati = st.session_state["mcp_servers_selezionati_temp"]
        
        # Ottieni lo stato precedente dal database
        servers_db = ConfigurazioneDB.carica_mcp_servers()
        servers_attivi_prima = {s['nome']: s for s in servers_db if s.get('attivo', False)}
        servers_selezionati_set = set(servers_selezionati)
        
        # Gestisci individualmente TUTTI i server che cambiano stato
        manager = get_mcp_client_manager()
        
        # Server da attivare (locali E remoti)
        for nome_server in servers_selezionati_set:
            if nome_server not in servers_attivi_prima:
                # Server che passa da inattivo ad attivo
                server_info = next((s for s in servers_db if s['nome'] == nome_server), None)
                if server_info:
                    # Gestisci sia locali che remoti
                    manager.salva_mcp_server(
                        nome=nome_server,
                        tipo=server_info['tipo'],
                        descrizione=server_info.get('descrizione', ''),
                        configurazione=server_info.get('configurazione', {}),
                        attivo=True
                    )
        
        # Server da disattivare (locali E remoti)
        for nome_server, server_info in servers_attivi_prima.items():
            if nome_server not in servers_selezionati_set:
                # Server che passa da attivo a inattivo
                manager.salva_mcp_server(
                    nome=nome_server,
                    tipo=server_info['tipo'],
                    descrizione=server_info.get('descrizione', ''),
                    configurazione=server_info.get('configurazione', {}),
                    attivo=False
                )
        
        # NON chiamare più aggiorna_stati_mcp_servers() perché abbiamo già
        # aggiornato individualmente tutti i server che hanno cambiato stato
        
        # Pulisci lo stato temporaneo
        del st.session_state["mcp_servers_selezionati_temp"]
    
    # Pulisci altri stati temporanei
    if "selected_mcp_server" in st.session_state:
        del st.session_state["selected_mcp_server"]
    if "mcp_server_config_temp" in st.session_state:
        del st.session_state["mcp_server_config_temp"]


@st.dialog(
    "🔌 Configurazione Server MCP",
    width="large",
    dismissible=True,
    on_dismiss=lambda: _on_close_mcp_dialog()
)
def mostra_dialog_mcp():
    """
    Dialog per configurare i server MCP disponibili.
    Layout con due colonne: lista server a sinistra, configurazione a destra.
    """
    st.caption("Configura i server MCP per estendere le capacità dell'agent")
    
    # Carica i server dal database
    servers_db = ConfigurazioneDB.carica_mcp_servers()
    servers_dict = {s["nome"]: s for s in servers_db}
    
    # Inizializza lo stato della sessione
    if "selected_mcp_server" not in st.session_state:
        st.session_state["selected_mcp_server"] = None
    if "mcp_server_config_temp" not in st.session_state:
        st.session_state["mcp_server_config_temp"] = {}
    
    # Layout a due colonne
    col_left, col_right = st.columns([1, 2])
    
    # ==================== COLONNA SINISTRA: LISTA SERVER ====================
    with col_left:
        st.subheader("📋 Server Disponibili")
        st.caption(f"Totale: {len(servers_db)} server")
        
        # Filtro di ricerca
        search_filter = st.text_input("🔍 Cerca server", placeholder="Filtra per nome...", key="mcp_search")
        
        # Filtra i server in base alla ricerca
        server_names = list(servers_dict.keys())
        filtered_servers = [s for s in server_names if search_filter.lower() in s.lower()] if search_filter else server_names
        
        # Container scrollabile per la lista
        with st.container(height=400):
            if filtered_servers:
                for server_name in sorted(filtered_servers):
                    server = servers_dict[server_name]
                    tipo_label = server['tipo']
                    
                    # Pulsante che seleziona il server quando cliccato
                    if st.button(
                        f"{server_name} ({tipo_label})",
                        key=f"select_mcp_{server_name}",
                        use_container_width=True
                    ):
                        st.session_state["selected_mcp_server"] = server_name
                        # Carica la configurazione esistente
                        st.session_state["mcp_server_config_temp"] = {
                            'nome': server['nome'],
                            'tipo': server['tipo'],
                            'descrizione': server.get('descrizione', ''),
                            'configurazione': server.get('configurazione', {}),
                            'attivo': server.get('attivo', False)
                        }
                        st.rerun()
            else:
                st.info("Nessun server trovato")
    
    # Multiselect per selezionare server attivi (dopo le colonne)
    st.divider()
    st.subheader("🔧 Selezione Server Attivi")
    
    # Ottieni tutti i server disponibili
    tutti_servers_disponibili = list(servers_dict.keys())
    
    # Ottieni i server attivi dal DB
    servers_attivi_db = [s["nome"] for s in servers_db if s.get("attivo", False)]
    
    # Inizializza lo stato se non esiste
    if "mcp_servers_selezionati_temp" not in st.session_state:
        st.session_state["mcp_servers_selezionati_temp"] = servers_attivi_db
    
    st.caption("ℹ️ Solo i server selezionati saranno disponibili per il tool MCP")
    
    servers_selezionati = st.multiselect(
        "Seleziona quali server MCP vuoi rendere attivi",
        options=sorted(tutti_servers_disponibili),
        default=st.session_state["mcp_servers_selezionati_temp"],
        key="mcp_servers_attivi_multiselect",
        help="Solo i server selezionati saranno caricati quando il tool MCP è attivo"
    )
    
    # Salva la selezione corrente nel session state (senza rerun)
    st.session_state["mcp_servers_selezionati_temp"] = servers_selezionati
    
    # ==================== COLONNA DESTRA: CONFIGURAZIONE ====================
    with col_right:
        st.subheader("🔧 Configurazione Server")
        
        selected_server = st.session_state.get("selected_mcp_server")
        
        if not selected_server:
            st.info("👈 Seleziona un server dalla lista per configurarlo")
        else:
            config_temp = st.session_state["mcp_server_config_temp"]
            st.markdown(f"**Server selezionato:** `{selected_server}`")
            
            # Nome (editabile)
            nome = st.text_input(
                "Nome",
                value=config_temp.get('nome', ''),
                help="Nome identificativo del server",
                key="mcp_nome"
            )
            
            # Aggiorna il nome nella config temporanea
            config_temp['nome'] = nome
            
            # Tipo
            tipo = st.selectbox(
                "Tipo",
                options=["local", "remote"],
                index=0 if config_temp.get('tipo') == 'local' else 1,
                help="Tipo di server MCP",
                key="mcp_tipo"
            )
            
            # Descrizione
            descrizione = st.text_area(
                "Descrizione",
                value=config_temp.get('descrizione', ''),
                help="Descrizione opzionale del server",
                key="mcp_descrizione"
            )
            
            # Configurazione specifica per tipo
            configurazione_esistente = config_temp.get('configurazione', {})
            
            if tipo == "local":
                st.markdown("**Configurazione Server Locale**")
                comando = st.text_input(
                    "Comando",
                    value=configurazione_esistente.get('comando', ''),
                    help="Comando per avviare il server (es. 'python', 'node', 'npx')",
                    key="mcp_comando"
                )
                args_str = st.text_input(
                    "Argomenti",
                    value=' '.join(configurazione_esistente.get('args', [])),
                    help="Argomenti separati da spazio",
                    key="mcp_args"
                )
                env_str = st.text_area(
                    "Variabili d'ambiente",
                    value='\n'.join([f"{k}={v}" for k, v in configurazione_esistente.get('env', {}).items()]),
                    help="Una per riga nel formato CHIAVE=valore",
                    key="mcp_env"
                )
                
                configurazione = {
                    'comando': comando,
                    'args': args_str.split() if args_str else [],
                    'env': dict(line.split('=', 1) for line in env_str.split('\n') if '=' in line)
                }
            else:  # remote
                st.markdown("**Configurazione Server Remoto**")
                url = st.text_input(
                    "URL",
                    value=configurazione_esistente.get('url', ''),
                    help="URL del server MCP",
                    key="mcp_url"
                )
                api_key = st.text_input(
                    "API Key",
                    value=configurazione_esistente.get('api_key', ''),
                    type="password",
                    help="API key per l'autenticazione (opzionale)",
                    key="mcp_api_key"
                )
                headers_str = st.text_area(
                    "Headers HTTP",
                    value='\n'.join([f"{k}: {v}" for k, v in configurazione_esistente.get('headers', {}).items()]),
                    help="Uno per riga nel formato Chiave: valore",
                    key="mcp_headers"
                )
                
                configurazione = {
                    'url': url,
                    'api_key': api_key if api_key else None,
                    'headers': dict(line.split(': ', 1) for line in headers_str.split('\n') if ': ' in line)
                }
            
            # Aggiorna config_temp con i nuovi valori
            config_temp['tipo'] = tipo
            config_temp['descrizione'] = descrizione
            config_temp['configurazione'] = configurazione
            st.session_state["mcp_server_config_temp"] = config_temp
    
    st.divider()
    
    # ==================== PULSANTI AZIONE ====================
    col_add, col_delete, col_save = st.columns(3)
    
    with col_add:
        if st.button("➕ Aggiungi Nuovo Server", use_container_width=True):
            # Genera un nome univoco per il nuovo server
            base_name = "nuovo_server"
            counter = 1
            nuovo_nome = base_name
            while nuovo_nome in servers_dict:
                nuovo_nome = f"{base_name}_{counter}"
                counter += 1
            
            # Crea un nuovo server con configurazione di default (inattivo)
            # Usa il nuovo metodo del manager che gestisce anche il PID
            manager = get_mcp_client_manager()
            manager.salva_mcp_server(
                nome=nuovo_nome,
                tipo="local",
                descrizione="",
                configurazione={'comando': '', 'args': [], 'env': {}},
                attivo=False  # I nuovi server sono inattivi di default
            )
            
            # Feedback con toast
            st.toast(f"✅ Server '{nuovo_nome}' creato! Configuralo e attivalo nel multiselect.", icon="✅")
            
            st.rerun()
    
    with col_delete:
        selected_server = st.session_state.get("selected_mcp_server")
        if st.button("🗑️ Elimina Server", use_container_width=True, disabled=not selected_server):
            if selected_server:
                try:
                    # Usa il nuovo metodo del manager che gestisce anche il PID
                    manager = get_mcp_client_manager()
                    manager.cancella_mcp_server(selected_server)
                    
                    # Feedback con toast
                    st.toast(f"🗑️ Server '{selected_server}' eliminato!", icon="🗑️")
                    
                    # Reset della selezione
                    st.session_state["selected_mcp_server"] = None
                    st.session_state["mcp_server_config_temp"] = {}
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore eliminazione: {e}")
    
    with col_save:
        selected_server = st.session_state.get("selected_mcp_server")
        if st.button("💾 Salva", type="primary", use_container_width=True, disabled=not selected_server):
            if selected_server:
                config_temp = st.session_state["mcp_server_config_temp"]
                nome_nuovo = config_temp.get('nome', '').strip()
                tipo = config_temp.get('tipo')
                configurazione = config_temp.get('configurazione', {})
                
                # Validazione
                errori = []
                if not nome_nuovo:
                    errori.append("Il nome del server è obbligatorio")
                if tipo == "local" and not configurazione.get('comando'):
                    errori.append("Il comando è obbligatorio per server locali")
                elif tipo == "remote" and not configurazione.get('url'):
                    errori.append("L'URL è obbligatorio per server remoti")
                
                if errori:
                    for errore in errori:
                        st.error(errore)
                else:
                    # Determina lo stato attivo dal multiselect
                    servers_selezionati = st.session_state.get("mcp_servers_selezionati_temp", [])
                    
                    manager = get_mcp_client_manager()
                    
                    # Se il nome è cambiato, cancella il vecchio server
                    if nome_nuovo != selected_server:
                        manager.cancella_mcp_server(selected_server)
                        # Aggiorna il multiselect: rimuovi il vecchio nome e aggiungi il nuovo se era selezionato
                        if selected_server in servers_selezionati:
                            servers_selezionati.remove(selected_server)
                            servers_selezionati.append(nome_nuovo)
                            st.session_state["mcp_servers_selezionati_temp"] = servers_selezionati
                    
                    # Salva con il nuovo metodo del manager che gestisce anche il PID
                    attivo = nome_nuovo in servers_selezionati
                    manager.salva_mcp_server(
                        nome=nome_nuovo,
                        tipo=tipo,
                        descrizione=config_temp.get('descrizione', ''),
                        configurazione=configurazione,
                        attivo=attivo
                    )
                    
                    # Feedback con toast
                    st.toast(f"✅ Server '{nome_nuovo}' salvato con successo!", icon="✅")
                    
                    # Reset della selezione per ripulire il form
                    st.session_state["selected_mcp_server"] = None
                    st.session_state["mcp_server_config_temp"] = {}
                    
                    st.rerun()
    
    st.divider()
    
    # ==================== PULSANTE CHIUDI ====================
    if st.button("✅ Chiudi", use_container_width=True):
        _on_close_mcp_dialog()
        st.rerun()


# Made with Bob