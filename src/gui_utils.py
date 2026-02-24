import streamlit as st
import extra_streamlit_components as stx
import base64
import asyncio
from datetime import datetime
from src.Messaggio import Messaggio
from src.ConfigurazioneDB import ConfigurazioneDB
from src.providers.loader import Loader
from src.providers.base import Provider
from src.providers.rag import Rag
from src.tools.loader import Loader as tools_loader
from src.tools.gui_tools import mostra_dialog_tools_agent, _on_close_tools_dialog
from src.mcp.gui_mcp import mostra_dialog_mcp
from src.mcp.client import get_mcp_client_manager
from src.mcp.gui_mcp_discovery import mostra_dialog_mcp_discovery

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
# Funzione helper per caricare tools nei provider
# ──────────────────────────────────────────────────────────────────────────────
def _carica_tools_nei_provider(provider_name: str | None = None):
    """
    Carica i tools configurati nei provider e crea l'agent.
    Include anche i tools dai server MCP se il toggle MCP è attivo.
    
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
    
    # Carica tools, risorse e prompt MCP se il toggle è attivo
    if st.session_state.get("mcp_enabled", False):
        try:
            manager = get_mcp_client_manager()
            manager.carica_configurazioni_da_db()
            # Usa il nuovo metodo unificato che ritorna (tools, errors)
            mcp_all_tools, mcp_errors = asyncio.run(manager.get_all_as_langchain_tools())
            
            # Aggiungi gli errori MCP alla lista degli errori
            if mcp_errors:
                for error in mcp_errors:
                    error_msg = f"Errore MCP: {error}"
                    risultato['errors'].append(error_msg)
                    st.toast(f"⚠️ {error_msg}", icon="⚠️")
            
            # Aggiungi i tools caricati (anche se ci sono errori parziali)
            if mcp_all_tools:
                tools_to_use.extend(mcp_all_tools)
        except Exception as e:
            error_msg = f"Errore caricamento MCP (tools/risorse/prompt): {str(e)}"
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

        # ──────────────────────────────────────────────────────────────────────────────
        # Sezione Chat
        # ──────────────────────────────────────────────────────────────────────────────
        with st.expander("💬 Gestione chat", expanded=False):                
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
                                
        # Sezione Modalità Agentica
        with st.expander("🕵️ Modalità Agentica", expanded=bool(st.session_state[provider_scelto][agentic_key])):
            # Callback per il toggle della modalità agentica
            def on_toggle_agentic():
                # Sincronizza il valore del toggle
                sincronizza_sessione(agentic_key)
                
                # Se disabilito modalità agentica, disabilito anche MCP e chiudi discovery
                if not st.session_state[agentic_key]:
                    st.session_state["mcp_enabled"] = False
                    st.session_state["mcp_discovery_open"] = False
                
                # Ricarica i tools attivi solo nel provider corrente
                risultato = _carica_tools_nei_provider(provider_name=provider_scelto)
            
            # Toggle Modalità agentica
            modalita_agentica = st.toggle("Abilita Modalità Agentica", value=st.session_state[provider_scelto][agentic_key],
                       key=agentic_key, on_change=on_toggle_agentic)
            
            # Toggle MCP (accanto al toggle modalità agentica)
            def on_toggle_mcp():
                # Se abilito MCP, abilito automaticamente anche modalità agentica
                if st.session_state.get("mcp_enabled", False):
                    if not st.session_state[provider_scelto][agentic_key]:
                        st.session_state[agentic_key] = True
                        st.session_state[provider_scelto][agentic_key] = True
                else:
                    # Se disabilito MCP, chiudi la dialog discovery
                    st.session_state["mcp_discovery_open"] = False
                
                # Ricarica i tools quando MCP viene attivato/disattivato
                risultato = _carica_tools_nei_provider(provider_name=provider_scelto)
            
            # MCP richiede modalità agentica, quindi disabilita il toggle se agentica è off
            mcp_disabled = not modalita_agentica
            mcp_enabled = st.toggle("Abilita MCP",
                       value=st.session_state.get("mcp_enabled", False) and modalita_agentica,
                       key="mcp_enabled",
                       on_change=on_toggle_mcp,
                       disabled=mcp_disabled,
                       help="Abilita i tools dai server MCP attivi (richiede modalità agentica)")
            
            # Pulsanti per configurare tools e MCP
            col_tools, col_mcp, col_discovery = st.columns(3)
            
            with col_tools:
                if st.button("⚙️ Configura Tools", key="btn_config_tools", use_container_width=True):
                    st.session_state["tools_dialog_open"] = True
                    st.session_state["provider_corrente_dialog"] = provider_scelto
            
            with col_mcp:
                if st.button("🔌 Configura MCP", key="btn_config_mcp", use_container_width=True):
                    st.session_state["mcp_dialog_open"] = True
            
            with col_discovery:
                # Pulsante MCP Discovery - sempre disponibile per esplorare i server
                if st.button("🔍 MCP Discovery", key="btn_mcp_discovery",
                           use_container_width=True,
                           help="Esplora tools, risorse e prompt dai server MCP configurati"):
                    st.session_state["mcp_discovery_open"] = True
            
            # Mostra info sui tools attivi
            tools_attivi = ConfigurazioneDB.carica_tools_attivi()
            if tools_attivi:
                with st.expander("📋 Dettagli tools attivi", expanded=False):
                    for tool in tools_attivi:
                        st.write(f"• **{tool['nome_tool']}**")
            else:
                st.info("ℹ️ Nessun tool attivo. Configura e attiva i tools dalla finestra di configurazione.")
            
            # Mostra info sui server MCP attivi
            if st.session_state.get("mcp_enabled", False):
                servers_mcp_attivi = ConfigurazioneDB.carica_mcp_servers_attivi()
                if servers_mcp_attivi:
                    with st.expander("🔌 Server MCP attivi", expanded=False):
                        for server in servers_mcp_attivi:
                            tipo_icon = "💻" if server['tipo'] == 'local' else "🌐"
                            st.write(f"{tipo_icon} **{server['nome']}** ({server['tipo']})")
                else:
                    st.info("ℹ️ Nessun server MCP attivo. Configura e attiva i server dalla finestra MCP.")
            
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
                modello_rag = st.selectbox("🧩 Modello per il RAG", modelli_rag, key=rag_model_key,
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

        # Salva configurazione e gestione DB (in fondo alla sidebar)
        col_salva, col_db = st.columns(2)
        with col_salva:
            st.button("Salva configurazione", key="salva", on_click=salva_configurazione, args=[providers], use_container_width=True)
        with col_db:
            # Link per gestione avanzata DB config.db
            # sqlite-web viene avviato automaticamente all'avvio dell'applicazione
            url = "http://127.0.0.1:6969"
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
    
    # ---- Render della finestra modale configurazione MCP ----
    if st.session_state.get("mcp_dialog_open", False):
        mostra_dialog_mcp()
    
    # ---- Render della finestra modale MCP Discovery ----
    if st.session_state.get("mcp_discovery_open", False):
        mostra_dialog_mcp_discovery()

    return provider_scelto, messaggio_di_sistema

# ──────────────────────────────────────────────────────────────────────────────
# Invio messaggi & render cronologia
# ──────────────────────────────────────────────────────────────────────────────
def generate_response(prompt_utente, messaggio_di_sistema, provider_scelto: Provider):
    """
    Genera la risposta del modello o dell'agent.
    Se la modalità agentica è attiva, mostra un feedback visivo delle operazioni.
    """
    
    # Prepara la lista dei messaggi da inviare
    messaggi_da_inviare = []
    
    # Messaggio di sistema
    if messaggio_di_sistema:
        messaggi_da_inviare.append(Messaggio(testo=messaggio_di_sistema, ruolo="system"))
    
    # Messaggio utente
    messaggio_utente = Messaggio(ruolo="user")
    
    # Testo del messaggio utente
    user_text = prompt_utente.text if prompt_utente.text else ""
    
    if user_text:
        messaggio_utente.set_testo(user_text)
    
    # Allegati dal file uploader
    if prompt_utente["files"]:
        messaggio_utente.set_allegati(prompt_utente["files"])
    
    messaggi_da_inviare.append(messaggio_utente)
    
    # Invia i messaggi con feedback visivo se modalità agentica è attiva
    if provider_scelto.get_modalita_agentica():
        # Crea un container per il feedback con st.status()
        with st.status("🤖 Agent in azione...", expanded=True) as status:
            # Passa il container di status al metodo invia_messaggi (ora asincrono)
            asyncio.run(provider_scelto.invia_messaggi(messaggi_da_inviare, status_container=status))
            # Aggiorna lo stato finale
            status.update(label="✅ Operazione completata!", state="complete")
    else:
        # Modalità normale senza feedback visivo (anche questa è asincrona ora)
        asyncio.run(provider_scelto.invia_messaggi(messaggi_da_inviare))
    
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