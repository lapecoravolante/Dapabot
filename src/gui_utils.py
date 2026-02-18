import streamlit as st
import extra_streamlit_components as stx
import base64
from datetime import datetime
from src.Messaggio import Messaggio
from src.ConfigurazioneDB import ConfigurazioneDB
from src.providers.loader import Loader
from src.providers.base import Provider
from src.providers.rag import Rag
from src.tools.loader import Loader as tools_loader

# ──────────────────────────────────────────────────────────────────────────────
# Bootstrap iniziale
# ──────────────────────────────────────────────────────────────────────────────
def _costruisci_chiavi_di_sessione(nome: str) -> dict:
    """Costruisce le chiavi di sessione per un provider.
    
    Args:
        nome: Nome del provider
        
    Returns:
        Dizionario con le chiavi di sessione
    """
    return {
        'apikey': f"api_key_{nome}",
        'modello': f"modello_{nome}",
        'agentic': f"modalita_agentica_{nome}",
        'sysmsg': f"system_msg_{nome}",
        'rag_enabled': f"rag_enabled_{nome}",
        'rag_topk': f"rag_topk_{nome}",
        'rag_model': f"rag_model_{nome}",
        'rag_modalita': f"rag_modalita_ricerca_{nome}"
    }


def _get_provider_defaults(provider: Provider, chiavi: dict) -> dict:
    """Recupera i valori di default per un provider.
    
    Considera nell'ordine:
    - valore in sessione
    - valore memorizzato nel provider
    - valore nella configurazione
    - valore di default
    
    Args:
        provider: Istanza del provider
        chiavi: Dizionario con le chiavi di sessione
        
    Returns:
        Dizionario con i valori di default
    """
    conf = provider.to_dict()
    rag_conf = conf.get("rag", {})
    rag = provider.get_rag()
    
    return {
        chiavi['apikey']: st.session_state.get(chiavi['apikey']) or provider.get_apikey() or conf.get("api_key", provider.get_prefisso_token()),
        chiavi['modello']: st.session_state.get(chiavi['modello']) or provider.get_modello_scelto() or conf.get("modello", ""),
        chiavi['agentic']: st.session_state.get(chiavi['agentic']) or provider.get_modalita_agentica() or conf.get("agentic_mode", False),
        chiavi['sysmsg']: st.session_state.get(chiavi['sysmsg'], ""),
        chiavi['rag_enabled']: st.session_state.get(chiavi['rag_enabled']) or rag.get_attivo() or rag_conf.get("attivo", False),
        chiavi['rag_topk']: st.session_state.get(chiavi['rag_topk']) or rag.get_topk() or rag_conf.get("top_k", Rag.DEFAULT_TOPK),
        chiavi['rag_model']: st.session_state.get(chiavi['rag_model']) or rag.get_modello() or rag_conf.get("modello", Rag.DEFAULT_EMBEDDING_MODEL),
        chiavi['rag_modalita']: st.session_state.get(chiavi['rag_modalita']) or rag.get_modalita_ricerca() or rag_conf.get("modalita_ricerca", Rag.AVAILABLE_SEARCH_MODALITIES[0])
    }

def _inizializza_tools():
    """Inizializza e configura i tools disponibili.
        I tools vengono caricati dinamicamente e
        popolati con le configurazioni prese dal DB.
        Vengono configurati SOLO i tool attivi per evitare errori di validazione.
    """
    if "tools_instances" in st.session_state:
        return
        
    st.session_state.tools_instances = tools_loader.discover_tools()
    # Carica solo i tool attivi per evitare errori di validazione su tool disattivati
    tools_salvati = ConfigurazioneDB.carica_tools_attivi()
    
    for tool_config in tools_salvati:
        nome_tool = tool_config["nome_tool"]
        if nome_tool not in st.session_state.tools_instances:
            continue
            
        instance = st.session_state.tools_instances[nome_tool]
        configurazione = tool_config["configurazione"]
        
        for key, value in configurazione.items():
            if key == "_variabili_necessarie":
                instance.set_variabili_necessarie(value)
            elif hasattr(instance, key):
                setattr(instance, key, value)

def _inizializza_provider(provider: Provider, modello_da_ripristinare: str = ""):
    """Inizializza la configurazione di sessione per un singolo provider.
    
    Args:
        provider: Istanza del provider
        modello_da_ripristinare: Modello da ripristinare (opzionale)
    """
    nome = provider.nome()
    chiavi = _costruisci_chiavi_di_sessione(nome)
    
    if nome not in st.session_state:
        st.session_state[nome] = _get_provider_defaults(provider, chiavi)
    
    if modello_da_ripristinare:
        st.session_state[nome][chiavi['modello']] = modello_da_ripristinare

def inizializza():
    """Bootstrap iniziale dell'applicazione."""
    # Il server sqlite-web per config.db può essere avviato manualmente se necessario
    # ConfigurazioneDB non ha metodi per sqlite-web integrati
    
    # Inizializza tools
    _inizializza_tools()
    
    # Inizializza providers
    if "providers" not in st.session_state:
        st.session_state.providers = Loader.discover_providers()
    
    # Carica i tools attivi nei provider dopo l'inizializzazione
    # Questo assicura che i tool siano disponibili quando viene attivata la modalità agentica
    _carica_tools_nei_provider()
    
    # Inizializza tabbar
    if "tabbar_key" not in st.session_state:
        st.session_state["tabbar_key"] = f"tab_{datetime.now().timestamp()}"
    
    # Inizializza checkbox per visualizzazione chat dal DB
    if "chat_db_key" not in st.session_state:
        st.session_state["chat_db_key"] = False
    
    # Inizializza checkbox per autocaricamento chat dal DB
    if "autoload_chat_db" not in st.session_state:
        st.session_state["autoload_chat_db"] = False
    
    # Gestisce ripristino chat
    provider_da_ripristinare, modello_da_ripristinare = "", ""
    if st.session_state.get("ripristina_chat"):
        provider_da_ripristinare, modello_da_ripristinare = st.session_state["ripristina_chat"].split(" | ")
        st.session_state["provider_da_ripristinare"] = provider_da_ripristinare
        st.session_state["ripristina_chat"] = ""
    
    # Inizializza ogni provider
    for nome, provider in st.session_state.providers.items():
        modello = modello_da_ripristinare if nome == provider_da_ripristinare else ""
        _inizializza_provider(provider, modello)
    
    return st.session_state.providers

# ──────────────────────────────────────────────────────────────────────────────
# Salvataggio configurazione (per TUTTI i provider) + aggiornamento runtime
# ──────────────────────────────────────────────────────────────────────────────
def salva_configurazione(providers: dict[str, Provider]):
    """
    Salva la configurazione di TUTTI i provider leggendo nell'ordine:
    valore in sessione -> valore memorizzato nel provider -> valore nella configurazione -> valore di default
    """
    configurazioni = []
    for nome, provider in providers.items():
        chiavi = _costruisci_chiavi_di_sessione(nome)
        defaults = _get_provider_defaults(provider, chiavi)
        
        # Recupera valori aggiuntivi non gestiti da _get_provider_defaults
        conf = provider.to_dict()
        rag_conf = conf.get("rag", {})
        directory_allegati = provider.get_rag().get_upload_dir() or rag_conf.get("directory_allegati", Rag.DEFAULT_UPLOAD_DIR)
        
        # Salva direttamente nel database unificato
        ConfigurazioneDB.salva_provider(
            nome=nome,
            base_url=provider.get_baseurl(),
            api_key=defaults[chiavi['apikey']],
            modello=defaults[chiavi['modello']],
            rag_config={
                "attivo": defaults[chiavi['rag_enabled']],
                "modello": defaults[chiavi['rag_model']],
                "top_k": defaults[chiavi['rag_topk']],
                "directory_allegati": directory_allegati,
                "modalita_ricerca": defaults[chiavi['rag_modalita']]
            }
        )
        
        # Riflette immediatamente la configurazione sul provider
        try:
            provider.set_modello_scelto(modello=defaults[chiavi['modello']], autoload_chat_db=st.session_state["autoload_chat_db"])
            provider.set_apikey(api_key=defaults[chiavi['apikey']])
            provider.set_rag(
                attivo=defaults[chiavi['rag_enabled']],
                topk=defaults[chiavi['rag_topk']],
                modello=defaults[chiavi['rag_model']],
                modalita_ricerca=defaults[chiavi['rag_modalita']]
            )
        except Exception:
            pass  # Non bloccare il salvataggio su errori runtime
    
    # Configurazione già salvata nel loop precedente
    try:
        st.toast("Configurazione salvata ✅", icon="💾")
    except Exception as e:
        st.toast(f"Errore nel salvataggio: {e}", icon="💩")

# ──────────────────────────────────────────────────────────────────────────────
# Dialog configurazione tools per agent
# ──────────────────────────────────────────────────────────────────────────────
def _on_close_tools_dialog():
    """
    Callback chiamato quando la dialog dei tools viene chiusa.
    Aggiorna il DB con le selezioni fatte nel multiselect.
    """
    st.session_state["tools_dialog_open"] = False
    
    # Aggiorna il DB solo se ci sono modifiche
    if "tools_selezionati_temp" in st.session_state:
        tools_selezionati = st.session_state["tools_selezionati_temp"]
        ConfigurazioneDB.aggiorna_stati_tools(tools_selezionati)
        # Ricarica i tools solo nel provider corrente
        provider_corrente = st.session_state.get("provider_corrente_dialog")
        risultato = _carica_tools_nei_provider(provider_name=provider_corrente)
        
        # Salva gli errori in session_state per mostrarli all'utente
        if risultato['errors']:
            st.session_state["tools_loading_errors"] = risultato['errors']
        else:
            # Rimuovi eventuali errori precedenti
            if "tools_loading_errors" in st.session_state:
                del st.session_state["tools_loading_errors"]
        
        # Pulisci lo stato temporaneo
        del st.session_state["tools_selezionati_temp"]
        if "provider_corrente_dialog" in st.session_state:
            del st.session_state["provider_corrente_dialog"]

@st.dialog(
    "⚙️ Configurazione Tools per Agent",
    width="large",
    dismissible=True,
    on_dismiss=lambda: _on_close_tools_dialog()
)
def mostra_dialog_tools_agent():
    """
    Dialog per configurare i tools disponibili per l'agent.
    I tools sono condivisi tra tutti i provider.
    Layout con tab: Configurazione e Database.
    """
    st.caption("Configura i tools disponibili per tutti i provider")
    
    # Ottieni le istanze dei tools dal session state
    tools_instances = st.session_state.get("tools_instances", {})
    
    if not tools_instances:
        st.warning("Nessun tool disponibile. Verifica l'installazione dei tools in src/tools/")
        return
    
    # Carica i tools già configurati dal DB
    tools_salvati = ConfigurazioneDB.carica_tools()
    tools_salvati_dict = {t["nome_tool"]: t["configurazione"] for t in tools_salvati}
    
    # Inizializza lo stato della sessione per il tool selezionato
    if "selected_tool_for_config" not in st.session_state:
        st.session_state["selected_tool_for_config"] = None
    if "tool_config_temp" not in st.session_state:
        st.session_state["tool_config_temp"] = {}
    
    # Crea le tab
    tab1, tab2 = st.tabs(["⚙️ Configurazione", "🗄️ Database"])
    
    # ==================== TAB 1: CONFIGURAZIONE ====================
    with tab1:
        # Layout a due colonne
        col_left, col_right = st.columns([1, 2])
    
        with col_left:
            st.subheader("📋 Tools Disponibili")
            st.caption(f"Totale: {len(tools_instances)} tools")
            
            # Filtro di ricerca
            search_filter = st.text_input("🔍 Cerca tool", placeholder="Filtra per nome...")
            
            # Filtra i tools in base alla ricerca
            tool_names = list(tools_instances.keys())
            filtered_tools = [t for t in tool_names if search_filter.lower() in t.lower()] if search_filter else tool_names
            
            # Container scrollabile per la lista
            with st.container(height=400):
                for tool_name in sorted(filtered_tools):
                    # Pulsante che seleziona il tool quando cliccato
                    if st.button(tool_name, key=f"select_btn_{tool_name}", use_container_width=True):
                        st.session_state["selected_tool_for_config"] = tool_name
                        # Carica la configurazione esistente se presente
                        if tool_name in tools_salvati_dict:
                            st.session_state["tool_config_temp"] = tools_salvati_dict[tool_name].copy()
                        else:
                            st.session_state["tool_config_temp"] = {}
                        st.rerun()
        
        # Multiselect per selezionare tools attivi (dopo le colonne)
        st.divider()
        st.subheader("🔧 Selezione Tools Attivi")
        
        # Ottieni tutti i tools disponibili dal loader
        tutti_tools_disponibili = list(tools_instances.keys())
        
        # Ottieni i tools attivi dal DB
        tools_attivi_db = [t["nome_tool"] for t in tools_salvati if t.get("attivo", True)]
        
        # Inizializza lo stato se non esiste
        if "tools_selezionati_temp" not in st.session_state:
            st.session_state["tools_selezionati_temp"] = tools_attivi_db
        
        tools_selezionati = st.multiselect(
            "Seleziona quali tools vuoi rendere attivi",
            options=sorted(tutti_tools_disponibili),
            default=st.session_state["tools_selezionati_temp"],
            key="tools_attivi_multiselect",
            help="Solo i tools selezionati saranno disponibili per l'utilizzo in modalità agentica"
        )
        
        # Salva la selezione corrente nel session state (senza rerun)
        st.session_state["tools_selezionati_temp"] = tools_selezionati
        
        with col_right:
            st.subheader("🔧 Configurazione Tool")
            
            selected_tool = st.session_state.get("selected_tool_for_config")
            
            if not selected_tool:
                st.info("👈 Seleziona un tool dalla lista per configurarlo")
            else:
                st.markdown(f"**Tool selezionato:** `{selected_tool}`")
                
                # Ottieni l'istanza del tool
                tool_instance = tools_instances.get(selected_tool)
                
                if not tool_instance:
                    st.error(f"Tool '{selected_tool}' non trovato nelle istanze")
                    return
                
                # Ottieni la configurazione dal tool usando get_configurazione()
                tool_config = tool_instance.get_configurazione()
                
                # Separa parametri configurabili e variabili d'ambiente
                configurable_params = {k: v for k, v in tool_config.items() if not k.startswith('_')}
                variabili_ambiente = tool_config.get('_variabili_necessarie', {})
                
                # ========== SEZIONE PARAMETRI CONFIGURABILI ==========
                if configurable_params:
                    st.divider()
                    st.caption("📝 Parametri configurabili:")
                    
                    # Form dinamico basato sui parametri
                    config_temp = st.session_state["tool_config_temp"]
                    
                    for param_name, param_value in configurable_params.items():
                        # Valore corrente (da config temp o dal tool)
                        current_value = config_temp.get(param_name, param_value)
                        
                        # Crea il widget appropriato in base al tipo
                        if isinstance(param_value, bool):
                            value = st.checkbox(
                                param_name,
                                value=bool(current_value),
                                key=f"param_{selected_tool}_{param_name}"
                            )
                            config_temp[param_name] = value
                        
                        elif isinstance(param_value, int):
                            value = st.number_input(
                                param_name,
                                value=int(current_value) if current_value is not None else 0,
                                key=f"param_{selected_tool}_{param_name}"
                            )
                            config_temp[param_name] = value
                        
                        elif isinstance(param_value, float):
                            value = st.number_input(
                                param_name,
                                value=float(current_value) if current_value is not None else 0.0,
                                key=f"param_{selected_tool}_{param_name}",
                                format="%.2f"
                            )
                            config_temp[param_name] = value
                        
                        elif isinstance(param_value, list):
                            # Per liste, usa text_area con valori separati da virgola
                            list_value = ", ".join(str(v) for v in current_value) if isinstance(current_value, list) else str(current_value or "")
                            value = st.text_area(
                                param_name,
                                value=list_value,
                                help="Valori separati da virgola",
                                key=f"param_{selected_tool}_{param_name}",
                                height=100
                            )
                            # Converti in lista
                            config_temp[param_name] = [v.strip() for v in value.split(",") if v.strip()]
                        
                        else:
                            # Default: text_input per stringhe
                            value = st.text_input(
                                param_name,
                                value=str(current_value) if current_value is not None else "",
                                key=f"param_{selected_tool}_{param_name}"
                            )
                            config_temp[param_name] = value
                    
                    st.session_state["tool_config_temp"] = config_temp
                
                # ========== SEZIONE VARIABILI D'AMBIENTE ==========
                if variabili_ambiente:
                    st.divider()
                    st.caption("🔐 Variabili d'ambiente:")
                    
                    # Inizializza le variabili d'ambiente in config_temp se non presenti
                    if "_variabili_necessarie" not in st.session_state["tool_config_temp"]:
                        st.session_state["tool_config_temp"]["_variabili_necessarie"] = {}
                    
                    env_vars_temp = st.session_state["tool_config_temp"]["_variabili_necessarie"]
                    variabili_vuote = []
                    
                    for var_name, var_default in variabili_ambiente.items():
                        # Valore corrente (da config temp o dal default)
                        current_value = env_vars_temp.get(var_name, var_default)
                        
                        # Widget per la variabile d'ambiente
                        value = st.text_input(
                            var_name,
                            value=str(current_value) if current_value is not None else "",
                            key=f"env_{selected_tool}_{var_name}",
                            help=f"Variabile d'ambiente: {var_name}"
                        )
                        env_vars_temp[var_name] = value
                        
                        # Traccia le variabili vuote per il warning
                        if not value:
                            variabili_vuote.append(var_name)
                    
                    st.session_state["tool_config_temp"]["_variabili_necessarie"] = env_vars_temp
                    
                    # Mostra warning se ci sono variabili vuote
                    if variabili_vuote:
                        st.warning(f"⚠️ Variabili d'ambiente non configurate: {', '.join(variabili_vuote)}")
                
                # Se non ci sono né parametri né variabili
                if not configurable_params and not variabili_ambiente:
                    st.info("Questo tool non ha parametri configurabili né variabili d'ambiente.")
                    st.caption("Puoi comunque salvarlo per renderlo disponibile all'agent.")
                
                st.divider()
                
                # Pulsanti di azione
                col_save, col_remove, col_cancel = st.columns(3)
                
                with col_save:
                    if st.button("💾 Salva Tool", type="primary", use_container_width=True):
                        try:
                            # Aggiorna l'istanza del tool con i nuovi valori
                            for key, value in st.session_state["tool_config_temp"].items():
                                if key == "_variabili_necessarie":
                                    # Gestisce le variabili d'ambiente
                                    tool_instance.set_variabili_necessarie(value)
                                elif hasattr(tool_instance, key):
                                    setattr(tool_instance, key, value)
                            
                            # Salva nel database
                            ConfigurazioneDB.salva_tool(
                                nome_tool=selected_tool,
                                configurazione=st.session_state["tool_config_temp"]
                            )
                            st.success(f"✅ Tool '{selected_tool}' salvato!")
                            st.session_state["selected_tool_for_config"] = None
                            st.session_state["tool_config_temp"] = {}
                            st.rerun()
                        except Exception as e:
                            st.error(f"Errore nel salvataggio: {e}")
                
                with col_remove:
                    if selected_tool in tools_salvati_dict:
                        if st.button("❌ Rimuovi Tool", use_container_width=True):
                            try:
                                ConfigurazioneDB.cancella_tool(selected_tool)
                                st.success(f"🗑️ Tool '{selected_tool}' rimosso!")
                                st.session_state["selected_tool_for_config"] = None
                                st.session_state["tool_config_temp"] = {}
                                st.rerun()
                            except Exception as e:
                                st.error(f"Errore nella rimozione: {e}")
                
                with col_cancel:
                    if st.button("↩️ Annulla", use_container_width=True):
                        st.session_state["selected_tool_for_config"] = None
                        st.session_state["tool_config_temp"] = {}
                        st.rerun()
    
    # ==================== TAB 2: DATABASE ====================
    with tab2:
        st.subheader("🗄️ Gestione Database")
        st.caption("Importa, esporta o elimina la configurazione dei tools")
        
        col_import, col_export, col_delete = st.columns(3)
        
        with col_import:
            st.markdown("### 📥 Importa Tools")
            uploaded_file = st.file_uploader("Seleziona file JSON", type=["json"], key="import_agent_db")
            if uploaded_file and st.button("Importa configurazione tools", key="btn_import_agent_db", use_container_width=True):
                try:
                    import json
                    json_data = uploaded_file.read().decode("utf-8")
                    data = json.loads(json_data)
                    
                    # Importa solo i tools dal JSON
                    if "tools" in data:
                        for tool_data in data["tools"]:
                            ConfigurazioneDB.salva_tool(
                                nome_tool=tool_data["nome_tool"],
                                configurazione=tool_data["configurazione"],
                                attivo=tool_data.get("attivo", True)
                            )
                        st.success(f"✅ Importati {len(data['tools'])} tools!")
                        st.rerun()
                    else:
                        st.warning("Il file JSON non contiene dati sui tools")
                except Exception as e:
                    st.error(f"Errore nell'importazione: {e}")
            st.caption("ℹ️ Importa solo la configurazione dei tools")
        
        with col_export:
            st.markdown("### 📤 Esporta Tools")
            if st.button("Esporta configurazione tools", key="btn_export_agent_db", use_container_width=True):
                try:
                    json_data = ConfigurazioneDB.esporta_json()
                    filename = f"tools-config-{datetime.now().strftime('%Y%m%d')}.json"
                    st.download_button(
                        label="⬇️ Scarica file",
                        data=json_data,
                        file_name=filename,
                        mime="application/json",
                        key="download_agent_db",
                        use_container_width=True
                    )
                    st.caption("ℹ️ Esporta solo la configurazione dei tools")
                except Exception as e:
                    st.error(f"Errore nell'esportazione: {e}")
        
        with col_delete:
            st.markdown("### 🗑️ Elimina Tools")
            if st.button("Elimina tutti i tools", key="btn_delete_agent_db", use_container_width=True, type="secondary"):
                if st.session_state.get("confirm_delete_agent_db", False):
                    try:
                        ConfigurazioneDB.elimina_tutti_tools()
                        # Svuota i tools da tutti i provider
                        providers = st.session_state.get("providers", {})
                        for provider in providers.values():
                            provider.set_tools([])
                            try:
                                provider._crea_agent()
                            except:
                                pass  # Ignora errori durante la ricreazione dell'agent
                        st.success("✅ Tutti i tools eliminati e rimossi dai provider!")
                        st.session_state["confirm_delete_agent_db"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore nell'eliminazione: {e}")
                else:
                    st.session_state["confirm_delete_agent_db"] = True
                    st.warning("⚠️ Clicca di nuovo per confermare l'eliminazione di tutti i tools")
            st.caption("ℹ️ Elimina solo i tools dalla tabella tool")
        
        st.divider()
        
        # Informazioni sul database
        st.markdown("### ℹ️ Informazioni")
        tools_salvati_count = len(ConfigurazioneDB.carica_tools())
        st.info(f"**Tools configurati nel database:** {tools_salvati_count}")
        
        if tools_salvati_count > 0:
            with st.expander("📋 Dettagli tools salvati"):
                for tool in ConfigurazioneDB.carica_tools():
                    st.write(f"• **{tool['nome_tool']}**")
                    config = tool['configurazione']
                    if config:
                        st.json(config)
    
    st.divider()
    
    # Pulsante chiudi (fuori dalle tab, sempre visibile)
    if st.button("✅ Chiudi", type="primary", use_container_width=True):
        # Chiama la stessa funzione del callback on_dismiss
        _on_close_tools_dialog()
        st.rerun()

def _carica_tools_nei_provider(provider_name: str | None = None):
    """
    Carica i tools configurati nei provider e crea l'agent.
    
    Args:
        provider_name: Nome del provider in cui caricare i tools.
                      Se None, carica in tutti i provider.
    
    Returns:
        dict: Dizionario con 'success' (bool), 'tools_count' (int), 'providers_count' (int), 'errors' (list)
    """
    risultato = {
        'success': False,
        'tools_count': 0,
        'providers_count': 0,
        'errors': []
    }
    
    # Ottieni solo i tools attivi dal database
    tools_config = ConfigurazioneDB.carica_tools_attivi()
    
    # Prepara la lista dei tools da passare ai provider
    tools_to_use = []
    
    # Se ci sono tools attivi, caricali
    if tools_config:
        # Ottieni le istanze dei tools già caricate
        all_tools_instances = st.session_state.get("tools_instances", {})
        if not all_tools_instances:
            return risultato
        
        for tool_dict in tools_config:
            tool_name = tool_dict.get("nome_tool")
            
            if tool_name in all_tools_instances:
                tool_instance = all_tools_instances[tool_name]
                
                # Riconfigura l'istanza del tool con i dati dal database
                configurazione = tool_dict.get("configurazione", {})
                for key, value in configurazione.items():
                    if key == "_variabili_necessarie":
                        tool_instance.set_variabili_necessarie(value)
                    elif hasattr(tool_instance, key):
                        setattr(tool_instance, key, value)
                
                # Ottieni i tools effettivi chiamando get_tool()
                # Alcuni tools non richiedono configurazione, altri sì
                # Se get_tool() fallisce, l'errore viene catturato e registrato
                try:
                    tools = tool_instance.get_tool() # torna una lista di tools
                    tools_to_use.extend(tools)
                except Exception as e:
                    # Tool richiede configurazione o ha altri problemi
                    # L'errore viene registrato ma non blocca il caricamento degli altri tools
                    error_msg = f"Errore caricamento tool {tool_name}: {str(e)}"
                    risultato['errors'].append(error_msg)
                    st.toast(f"⚠️ {error_msg}", icon="⚠️")
    
    # Passa i tools ai provider specificati (anche se la lista è vuota)
    providers = st.session_state.get("providers", {})
    providers_aggiornati = 0
    
    # Determina quali provider aggiornare
    if provider_name:
        # Carica solo nel provider specificato
        providers_to_update = {provider_name: providers[provider_name]} if provider_name in providers else {}
    else:
        # Carica in tutti i provider
        providers_to_update = providers
    
    for provider in providers_to_update.values():
        # Aggiorna sempre i tools, anche se la lista è vuota
        provider.set_tools(tools_to_use)
        # Crea sempre l'agent, anche senza tools (funzionerà come un chatbot normale)
        try:
            provider._crea_agent()
            providers_aggiornati += 1
        except Exception as e:
            risultato['errors'].append(f"{provider.nome()}: {str(e)}")
    
    # Prepara il risultato
    risultato['success'] = providers_aggiornati > 0
    risultato['tools_count'] = len(tools_to_use)
    risultato['providers_count'] = providers_aggiornati
    
    return risultato

# ──────────────────────────────────────────────────────────────────────────────
# Dialog globale vector stores
# ──────────────────────────────────────────────────────────────────────────────
@st.dialog(
    "🗄️ Cache dei vector store",
    width="medium",
    dismissible=False,
)
def mostra_dialog_vectorestores_globale():
    st.caption("Vector store presenti nella cache globale")

    # Elenco vectorstore
    righe = Rag.costruisci_righe()

    # =============================================
    # Header delle colonne con st.columns
    # =============================================
    # Imposta larghezze relative qua (es. 4, 4, 1)
    header_col1, header_col2, header_col3 = st.columns([4, 4, 1])
    with header_col1:
        st.markdown("**📄 File**")
    with header_col2:
        st.markdown("**🧠 Modello**")
    with header_col3:
        st.markdown("")  # spazio per i pulsanti

    # =============================================
    # Mostra le righe (se presenti)
    # =============================================
    if righe:
        for idx, (id_str, collection, label, model) in enumerate(righe):
            col1, col2, col3 = st.columns([4, 4, 1])
            with col1:
                st.write(label)
            with col2:
                st.write(model)
            with col3:
                if st.button("❌", key=f"del_vs_{idx}", help="Elimina vector store"):
                    Rag.delete_vectorstore(id_str)
                    st.toast(f"Eliminato: {label}", icon="🗑️")
                    st.rerun()
    else:
        st.info("Nessun vector store presente.")

    st.divider()

    # =============================================
    # Pulsante "Elimina tutto"
    # =============================================
    if st.button("Elimina tutto", type="primary"):
        for id_str, *_ in righe:
            Rag.delete_vectorstore(id_str)
        st.success("Tutti i vector store sono stati rimossi.")
        st.rerun()

    # =============================================
    # Pulsante "Chiudi"
    # =============================================
    if st.button("Chiudi"):
        st.session_state["vs_dialog_global_open"] = False
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────────
def crea_sidebar(providers: dict[str, Provider]):
    st.logo(image="src/img/logo.png", size="large")
    
    with st.sidebar:
        """
            Di seguito viene creata una tabbar con un widget personalizzato (stx.tab_bar, non standard di streamlit).
            Il problema dei widget come questo è che non leggono lo stato da st.session_state e quindi non
            è possibile aggiornarne lo stato scrivendo in st.session_state. Questo significa che se voglio
            cambiare la tab attiva lo posso fare solo in 2 modi: cliccando col mouse oppure, da codice, distruggendo
            il widget e ricreandolo con un default diverso. Affinchè streamlit distrugga e ricrei il widget bisogna 
            cambiargli l'identià, cioè la key che lo individua univocamente dentro st.session_state (cfr.:
            https://docs.streamlit.io/develop/concepts/architecture/widget-behavior#widget-identity-key-based-vs-parameter-based).
            Quindi si fa così:
                1. dentro la funzione "inzializza()" viene generata una chiave random al primo avvio dell'applicazione
                2. ogni volta che l'utente interagisce col mouse, la tab viene cambiata regolarmente, quindi non ci sono problemi
                3. ogni volta che si seleziona una chat da ripristinare di un provider diverso da quello attuale, allora la 
                    callback della selectbox si occupa di cancellare la vecchia key e crearne una nuova, cancellando anche il
                    riferimento alla vecchia tabbar per evitare che si accumulino riferimenti orfani in st.session_state
                4. nella "inizializza()" si imposta il provider da assegnare alla nuova tabbar mettendolo dentro "st.session_state["provider_da_ripristinare"]"
                5. infine qui sotto viene creata la tabbar e selezionata la tab del provider corretto.
        """
        # Costruzione della TabBar con una key dinamica
        schede = [stx.TabBarItemData(id=nome, title=nome, description="") for nome in providers]
        default=schede[0].id
        if "provider_da_ripristinare" in st.session_state:
            default=st.session_state["provider_da_ripristinare"]
        provider_scelto = stx.tab_bar(data=schede, key=st.session_state["tabbar_key"], default=default)
        provider: Provider = providers[provider_scelto]

        # Chiavi per il provider corrente
        apikey_key                  = f"api_key_{provider_scelto}"
        modello_key                 = f"modello_{provider_scelto}"
        agentic_key                 = f"modalita_agentica_{provider_scelto}"
        rag_enabled_key             = f"rag_enabled_{provider_scelto}"
        rag_topk_key                = f"rag_topk_{provider_scelto}"
        rag_model_key               = f"rag_model_{provider_scelto}"
        rag_modalita_ricerca_key    = f"rag_modalita_ricerca_{provider_scelto}"
        sysmsg_key                  = f"system_msg_{provider_scelto}"

        # Opzioni correnti
        modelli     = list(provider.lista_modelli(api_key=st.session_state[provider_scelto][apikey_key]))
        modelli_rag = list(provider.lista_modelli_rag())
        modalities  = list(Rag.AVAILABLE_SEARCH_MODALITIES)

        """
            I widget non renderizzati vengono distrutti per risparmiare e quando vengono ricreati non riprendono il loro stato da st.session_state.
            In questo caso facio il backup dei valori di st.session_state in st.session_state[provider_scelto] e li ripristino dentro la funzione 
            inizializza(). Questo metodo è descritto anche nella documentazione ufficiale: 
            https://docs.streamlit.io/develop/concepts/architecture/widget-behavior#widgets-do-not-persist-when-not-continually-rendered
        """
        def sincronizza_sessione(chiave_widget):
            # copia il valore dalla sessione nel dizionario annidato di ogni provider
            st.session_state[provider_scelto][chiave_widget] = st.session_state[chiave_widget]
            
        # Text input: API key
        api_key = st.text_input("🗝️ API Key", type="password", key=apikey_key, placeholder="Inserisci la tua API key",
            value=st.session_state[provider_scelto][apikey_key],
            # la funzione lambda prende il valore inserito nel text_input e lo copia dentro st.session_state.provider_scelto.apikey_key
            on_change=sincronizza_sessione, args=(apikey_key,)
        )

        # Selectbox: Modello 
        if modelli:   
            if modello_key not in st.session_state:
                st.session_state[modello_key] = st.session_state[provider_scelto][modello_key]
            modello_scelto = st.selectbox("👾 Modello", modelli, key=modello_key,
                #index=modelli.index(st.session_state[provider_scelto][modello_key]) if st.session_state[provider_scelto][modello_key] in modelli else 0,
                on_change=sincronizza_sessione, args=(modello_key,)
            )
        else:
            st.warning("Nessun modello disponibile per questo provider. Inserisci una API key valida o riprova.")
            modello_scelto=""
            st.session_state[provider_scelto][modello_key]=""

        # Messaggio di sistema
        messaggio_di_sistema = st.text_area("📝Messaggio di sistema", key=sysmsg_key,
            placeholder="Il messaggio con cui viene istruito il modello prima di rispondere",            
            value=st.session_state[provider_scelto][sysmsg_key],
            on_change=sincronizza_sessione, args=(sysmsg_key,)
        )
        
        # CHAT RECENTI            
        with st.container(border=True):            
            def on_ripristina_chat():
                val = st.session_state["ripristina_chat"]
                if val:
                    prov, mod = val.split(" | ")
                    # Aggiorna la chiave per la TabBar, forzando la ricreazione del widget e l'aggiornamento del provider corretto
                    if st.session_state.get(f"{st.session_state['tabbar_key']}"):
                        del st.session_state[f"{st.session_state['tabbar_key']}"]
                    st.session_state["tabbar_key"] = f"tab_{datetime.now().timestamp()}"
                    # Aggiorna la selezione del modello per quel provider
                    st.session_state[f"modello_{prov}"] = mod
                    # Carica i messaggi dal database SOLO se "Autocaricamento dal DB" è abilitato
                    if prov in providers and st.session_state.get("autoload_chat_db", False):
                        providers[prov].carica_chat_da_db(modello=mod)
            
            chat_recenti = ["",]
            for nome_prov, prov in providers.items():
                modelli = prov.get_lista_modelli_con_chat()
                chat_recenti.extend([f"{nome_prov} | {modello}" for modello in modelli])
            if "chat_db_key" in st.session_state and st.session_state["chat_db_key"]:
                chat_su_disco=set([f"{prov} | {mod}" for prov, mod in ConfigurazioneDB.ritorna_chat_recenti()])
                chat_recenti=sorted(list(chat_su_disco.union(set(chat_recenti))))
            if len(chat_recenti)>1:
                st.selectbox("📂 Riapri chat recente:", options=chat_recenti, key="ripristina_chat", on_change=on_ripristina_chat)
            else:
                st.caption("📂 Nessuna chat recente")
            col1, col2 = st.columns(2)
            with col1:
                st.checkbox("Elenca chat su DB", key="chat_db_key", help="Se abilitato elenca le chat memorizzate su disco nella lista qui sopra", label_visibility="visible")
            with col2:
                if st.checkbox("Autocaricamento dal DB", key="autoload_chat_db", help="Se abilitato carica automaticamente la cronologia delle chat dal disco (se presenti)", label_visibility="visible"):
                    provider.carica_chat_da_db()
            
        # Sezione Modalità Agentica
        with st.expander("🤖 Modalità Agentica", expanded=bool(st.session_state[provider_scelto][agentic_key])):
            # Callback per il toggle della modalità agentica
            def on_toggle_agentic():
                # Sincronizza il valore del toggle
                sincronizza_sessione(agentic_key)
                # Ricarica i tools attivi solo nel provider corrente
                risultato = _carica_tools_nei_provider(provider_name=provider_scelto)
                
                # Salva gli errori in session_state per mostrarli all'utente
                if risultato['errors']:
                    st.session_state["tools_loading_errors"] = risultato['errors']
                else:
                    # Rimuovi eventuali errori precedenti
                    if "tools_loading_errors" in st.session_state:
                        del st.session_state["tools_loading_errors"]
            
            # Toggle Modalità agentica
            modalita_agentica = st.toggle("Abilita Modalità Agentica", value=st.session_state[provider_scelto][agentic_key],
                       key=agentic_key, on_change=on_toggle_agentic)
            
            # Pulsante per configurare i tools
            if st.button("⚙️ Configura Tools", key="btn_config_tools", use_container_width=True):
                st.session_state["tools_dialog_open"] = True
                st.session_state["provider_corrente_dialog"] = provider_scelto
            
            # Mostra info sui tools attivi
            tools_attivi = ConfigurazioneDB.carica_tools_attivi()
            if tools_attivi:
                with st.expander("📋 Dettagli tools attivi", expanded=False):
                    for tool in tools_attivi:
                        st.write(f"• **{tool['nome_tool']}**")
            else:
                st.info("ℹ️ Nessun tool attivo. Configura e attiva i tools dalla finestra di configurazione.")
            
            # Mostra eventuali errori di caricamento dei tools
            if "tools_loading_errors" in st.session_state:
                with st.expander("⚠️ Errori di caricamento tools", expanded=True):
                    for error in st.session_state["tools_loading_errors"]:
                        st.error(error, icon="❌")
            
        # Sezione RAG
        with st.expander("🔎 RAG", expanded=bool(st.session_state[provider_scelto][rag_enabled_key])):
            # Toggle RAG
            rag_abilitato = st.toggle("Abilita RAG", key=rag_enabled_key,
                value=st.session_state[provider_scelto][rag_enabled_key],
                on_change=sincronizza_sessione, args=(rag_enabled_key,)
            )

            # Top-K
            topk = st.number_input("🔝 Top K", min_value=1, step=1, key=rag_topk_key,
                value=st.session_state[provider_scelto][rag_topk_key],
                on_change=sincronizza_sessione, args=(rag_topk_key,)
            )

            # Modalità di ricerca            
            modalita_ricerca = st.selectbox("🔦 Modalità di ricerca", modalities, key=rag_modalita_ricerca_key,
                index=modalities.index(st.session_state[provider_scelto][rag_modalita_ricerca_key]) if st.session_state[provider_scelto][rag_modalita_ricerca_key] in modalities else 0,
                on_change=sincronizza_sessione, args=(rag_modalita_ricerca_key,)
            )

            # Modello RAG
            if modelli_rag:
                modello_rag = st.selectbox("🕵️ Modello per il RAG", modelli_rag, key=rag_model_key,
                    index=modelli_rag.index(st.session_state[provider_scelto][rag_model_key]) if st.session_state[provider_scelto][rag_model_key] in modelli_rag else 0,
                    on_change=sincronizza_sessione, args=(rag_model_key,)
                )
            else:
                st.warning("Nessun modello RAG disponibile.", icon="⚠️")
                modello_rag=""
                st.session_state[provider_scelto][rag_model_key]=""
            # ---- Pulsante globale per aprire la finestra MODALE con TUTTI i vector store ----
            if st.button("Cache...", key="btn_vs_global", help="Gestisci tutti i vector store di tutti i provider", icon="🗄️"):
                st.session_state["vs_dialog_global_open"] = True
        
        # ──────────────────────────────────────────────────────────────────────────────
        # Sezione Chat
        # ──────────────────────────────────────────────────────────────────────────────
        with st.expander("💬 Gestione chat", expanded=False):                
            colonna1, colonna2, colonna3 = st.columns(3, border=True)
            with colonna1:# PULSANTI DI SALVATAGGIO CHAT
                with st.popover("💾 Salva..."):
                    col1, col2 = st.columns(2, border=True)
                    # Pulsante: Salva chat corrente
                    with col1:
                        st.subheader("Salva chat corrente")
                        try:
                            salva=st.button("💾 Salva chat corrente", use_container_width=True)
                            st.caption("ℹ️ Salva su disco il contenuto della chat attualmente visualizzata")
                            if salva:
                                cronologia = provider.get_cronologia_messaggi(modello=modello_scelto)
                                ConfigurazioneDB.salva_chat(provider_scelto, modello_scelto, cronologia)
                                st.success("Chat salvata nel DB", icon="✅")
                        except Exception as e:
                            st.exception(e)
                    with col2:
                        st.subheader("Salva tutte le chat")
                        # Pulsante: Salva tutte le chat
                        salva=st.button("🗃️ Salva tutte le chat")
                        st.caption("ℹ️ Salva su disco tutte le chat in memoria")
                        if salva:
                            try:
                                with st.empty():
                                    with st.status(label="Salvataggio in corso...", expanded=True):
                                        for nome_p, prov in providers.items():
                                            modelli = prov.get_lista_modelli_con_chat()
                                            for modello in modelli:
                                                st.write(f"Provider: {nome_p}, modello: {modello}...")
                                                ConfigurazioneDB.salva_chat(nome_p, modello, prov.get_cronologia_messaggi(modello=modello))
                                    st.success("Tutte le chat salvate", icon="✅")
                            except Exception as e:
                                st.exception(e)
            with colonna2: # PULSANTI DI IMPORT/EXPORT DB
                with st.popover("🔁 Importa/esporta...", use_container_width=True):    
                    col1, col2 = st.columns(2, border=True)
                    with col1:
                        st.subheader("Esporta")
                        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # genera la stringa di data/ora
                        filename = f"storico_{ts}.json"
                        try:
                            json_data = ConfigurazioneDB.esporta_chat_json()
                            st.download_button(
                                label="⬇️ Esporta tutte le chat",
                                data=json_data,
                                file_name=filename,
                                mime="application/json"
                            )
                            st.caption("ℹ️ Scarica solo le chat in formato JSON")
                        except Exception as e:
                            st.exception(e)
                    with col2:
                        st.subheader("Importa")
                        # Importa DB JSON
                        try:
                            json_file = st.file_uploader("📥 Seleziona JSON da importare", type=["json"])
                            if json_file and st.button("📥 Importa chat"):
                                text = json_file.read().decode("utf-8")
                                ConfigurazioneDB.importa_chat_json(text)
                                st.success("Chat importate", icon="✅")
                                st.rerun()
                        except Exception as e:
                            st.exception(e)
            with colonna3:# PULSANTI DI ELIMINAZIONE CHAT
                with st.popover("🗑️ Elimina...", use_container_width=True):
                    col1, col2, col3, col4 = st.columns(4, border=True)
                    with col1: # cancella la cronologia corrente in ram
                        st.subheader("Ripulisci chat")
                        ripulisci=st.button("🧹 Ripulisci chat")
                        st.caption("ℹ️ Svuota il cotenuto della chat visualizzata. I dati non salvati andranno persi.")
                        if ripulisci:
                            try:
                                provider.ripulisci_chat(modello_scelto)
                                st.success("Chat ripulita", icon="✅")
                            except Exception as e:
                                st.exception(e)
                    with col2: # cancella tutte le chat in ram
                        st.subheader("Ripulisci tutte le chat")
                        svuota=st.button("🚮 Ripulisci tutte le chat")
                        st.caption("ℹ️ Svuota tutte le chat visualizzate. I dati non salvati andranno persi.")
                        if svuota:
                            try:
                                with st.empty():
                                    with st.status(label="Svuotamento in corso...", expanded=True):
                                        for nome_p, prov in providers.items():
                                            modello = prov.get_modello_scelto()
                                            if modello:
                                                st.write(f"Provider: {nome_p}, modello: {modello}...")
                                                prov.ripulisci_chat(modello)
                                    st.success("Svuotate tutte le chat", icon="✅")
                            except Exception as e:
                                st.exception(e)
                    with col3:# Cancella chat dal disco
                        st.subheader("Cancella chat dal disco")
                        cancella=st.button("🔥 Cancella chat")
                        st.caption("ℹ️ La chat visualizzata viene cancellata dal disco. È possibile continuare a lavorare con quella visualizzata.")
                        if cancella:
                            try:
                                ConfigurazioneDB.cancella_chat(provider_scelto, modello_scelto)
                                st.success("Chat cancellata dal disco", icon="✅")
                            except Exception as e:
                                st.exception(e)
                    with col4: # Cancella tutto il DB
                        st.subheader("Elimina tutto il DB")
                        elimina=st.button("💥 Elimina tutte le chat")
                        st.caption("ℹ️ Tutte le chat salvate vengono eliminate definitivamente. I dati non esportati andranno persi. La configurazione dei provider e dei tools viene preservata.")
                        if elimina:
                            try:
                                ConfigurazioneDB.elimina_tutte_chat()
                                st.success("Tutte le chat eliminate", icon="✅")
                            except Exception as e:
                                st.error(f"Errore durante l'eliminazione delle chat: {e}")
        # Salva configurazione e gestione DB (in fondo alla sidebar)
        col_salva, col_db = st.columns(2)
        with col_salva:
            st.button("Salva configurazione", key="salva", on_click=salva_configurazione, args=[providers], use_container_width=True)
        with col_db:
            # Link per gestione avanzata DB config.db
            # sqlite-web viene avviato automaticamente all'avvio dell'applicazione
            url = "http://127.0.0.1:8080"
            st.markdown(
                f'<a href="{url}" target="_blank">'
                '<button style="width:100%; padding:8px; font-size:1rem; border:1px solid #ccc; border-radius:4px; cursor:pointer; background-color:white;">'
                '🔍 Gestione avanzata DB'
                '</button></a>',
                unsafe_allow_html=True
            )
        # Aggiorna provider runtime (usa i valori restituiti dai widget)
        try:
            provider.set_client(modello_scelto, api_key)
            provider.set_modalita_agentica(modalita_agentica)
            provider.set_rag(attivo=rag_abilitato, topk=topk, modello=modello_rag, modalita_ricerca=modalita_ricerca)
        except Exception as e:
            st.toast(f"Errore nell'impostazione dei parametri: {e}", icon="⛔")
    #st.sidebar.json(st.session_state)
    
    # ---- Render della finestra modale vector stores ----
    if st.session_state.get("vs_dialog_global_open", False):
        mostra_dialog_vectorestores_globale()
    
    # ---- Render della finestra modale configurazione tools ----
    if st.session_state.get("tools_dialog_open", False):
        mostra_dialog_tools_agent()

    return provider_scelto, messaggio_di_sistema

# ──────────────────────────────────────────────────────────────────────────────
# Invio messaggi & render cronologia
# ──────────────────────────────────────────────────────────────────────────────
def generate_response(prompt_utente, messaggio_di_sistema, provider_scelto: Provider):
    """
    Genera la risposta del modello o dell'agent.
    Se la modalità agentica è attiva, mostra un feedback visivo delle operazioni.
    """
    # Chiudi il dialog dei tools se è aperto (evita che si riapra dopo l'invio del messaggio)
    if st.session_state.get("tools_dialog_open", False):
        st.session_state["tools_dialog_open"] = False
    
    # Prepara la lista dei messaggi da inviare
    messaggi_da_inviare = []
    # Messaggio di sistema (opzionale)
    if messaggio_di_sistema:
        messaggi_da_inviare.append(Messaggio(testo=messaggio_di_sistema, ruolo="system"))
    # Messaggio utente
    messaggio_utente = Messaggio(ruolo="user")
    if prompt_utente.text:
        messaggio_utente.set_testo(prompt_utente.text)
    if prompt_utente["files"]:
        messaggio_utente.set_allegati(prompt_utente["files"])
    messaggi_da_inviare.append(messaggio_utente)
    
    # Invia i messaggi con feedback visivo se modalità agentica è attiva
    if provider_scelto.get_modalita_agentica():
        # Crea un container per il feedback con st.status()
        with st.status("🤖 Agent in azione...", expanded=True) as status:
            # Passa il container di status al metodo invia_messaggi
            provider_scelto.invia_messaggi(messaggi_da_inviare, status_container=status)
            # Aggiorna lo stato finale
            status.update(label="✅ Operazione completata!", state="complete")
    else:
        # Modalità normale senza feedback visivo
        provider_scelto.invia_messaggi(messaggi_da_inviare)
    
def mostra_cronologia_chat(cronologia: list[Messaggio]):    
    for msg in cronologia:
        ruolo = msg.get_ruolo()
        testo = msg.get_testo()
        allegati = msg.get_allegati()
        if ruolo == "system":
            st.info(testo)
        else:
            with st.chat_message(ruolo, avatar="src/img/testa.png" if ruolo != "user" else None):
                # Mostra prima il testo come Markdown
                if testo:
                    st.markdown(testo)
                # Poi gli allegati
                for allegato in allegati:
                    tipo = allegato.tipo
                    contenuto = allegato.contenuto
                    
                    # Per contenuti multimediali, decodifica base64 in bytes per Streamlit
                    if tipo in ("image", "audio", "video"):
                        try:
                            # Il contenuto è una stringa base64, decodificala
                            contenuto_bytes = base64.b64decode(contenuto)
                            if tipo == "image":
                                st.image(contenuto_bytes)
                            elif tipo == "audio":
                                st.audio(contenuto_bytes)
                            elif tipo == "video":
                                st.video(contenuto_bytes)
                        except Exception as e:
                            st.error(f"Errore nella visualizzazione di {tipo}: {e}")
                    elif tipo == "text":
                        st.write(contenuto)
                    elif tipo == "text-plain":
                        st.text(contenuto)
                    elif tipo == "url":
                        # Gestisci URL: mostra link cliccabile
                        filename = allegato.filename if hasattr(allegato, 'filename') else contenuto.split('/')[-1]
                        st.markdown(f"🔗 [Scarica: {filename}]({contenuto})")
                    elif tipo == "file":
                        st.write(f"📄 File ricevuto dal modello: {allegato.mime_type}")
                    else:
                        st.write("⚠️ Ricevuto un allegato sconosciuto ⚠️")