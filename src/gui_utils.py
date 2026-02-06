import streamlit as st
import extra_streamlit_components as stx
from typing import Dict
from datetime import datetime
from src.Messaggio import Messaggio
from src.Configurazione import Configurazione
from src.providers.loader import Loader
from src.providers.base import Provider
from src.providers.rag import Rag
from src.StoricoChat import StoricoChat
from src.DBAgent import DBAgent

# ──────────────────────────────────────────────────────────────────────────────
# Bootstrap iniziale
# ──────────────────────────────────────────────────────────────────────────────
def inizializza():
    # Avvia i server sqlite-web per i database
    StoricoChat.start_sqlite_web_server()  # porta 8080 per storico_chat.db
    DBAgent.start_sqlite_web_server()      # porta 8081 per agent.db
    
    if "providers" not in st.session_state:  # carica i providers una sola volta
        st.session_state.providers = Loader.discover_providers()
    providers = st.session_state.providers  # shortcut
    
    # Se non c'è ancora un provider selezionato nella sessione, seleziona il primo provider come predefinito
    if "tabbar_key" not in st.session_state:
        st.session_state["tabbar_key"] = f"tab_{datetime.now().timestamp()}"
            
    # verifico se bisogna ripristinare sulla gui una chat recente    
    provider_da_ripristinare = modello_da_ripristinare = ""
    if "ripristina_chat" in st.session_state and st.session_state["ripristina_chat"]:
        provider_da_ripristinare, modello_da_ripristinare = st.session_state.get("ripristina_chat", ("", "")).split(" | ")
        st.session_state["provider_da_ripristinare"]=provider_da_ripristinare
        st.session_state["ripristina_chat"]=""
    
    for nome, provider in providers.items():
        conf = provider.to_dict()
        rag_conf = conf.get(Configurazione.RAG_KEY, {})

        apikey_key               = f"api_key_{nome}"
        modello_key              = f"modello_{nome}"
        agentic_key              = f"modalita_agentica_{nome}"
        sysmsg_key               = f"system_msg_{nome}"
        rag_enabled_key          = f"rag_enabled_{nome}"
        rag_topk_key             = f"rag_topk_{nome}"
        rag_model_key            = f"rag_model_{nome}"
        rag_modalita_ricerca_key = f"rag_modalita_ricerca_{nome}"

        # crea la variabile di sessione con le configurazioni del provider considerando nell'ordine:
        # valore in sessione -> valore memorizzato nel provider -> valore nella configurazione -> valore di default
        if nome not in st.session_state:
            st.session_state[nome]={
                apikey_key: st.session_state.get(apikey_key) or provider.get_apikey() or conf.get("api_key", provider.get_prefisso_token()),
                modello_key: st.session_state.get(modello_key) or provider.get_modello_scelto() or conf.get("modello", ""),
                agentic_key: st.session_state.get(agentic_key) or provider.get_modalita_agentica() or conf.get("agentic_mode", False),
                sysmsg_key: st.session_state.get(sysmsg_key, ""),
                rag_enabled_key: st.session_state.get(rag_enabled_key) or provider.get_rag().get_attivo() or rag_conf.get("attivo", False),
                rag_topk_key: st.session_state.get(rag_topk_key) or provider.get_rag().get_topk() or rag_conf.get("top_k", Rag.DEFAULT_TOPK),
                rag_model_key: st.session_state.get(rag_model_key) or provider.get_rag().get_modello() or rag_conf.get("modello", Rag.DEFAULT_EMBEDDING_MODEL),
                rag_modalita_ricerca_key: st.session_state.get(rag_modalita_ricerca_key) or provider.get_rag().get_modalita_ricerca() or rag_conf.get("modalita_ricerca", Rag.AVAILABLE_SEARCH_MODALITIES[0])
            }
        if provider_da_ripristinare == nome:
            st.session_state[nome][modello_key]=modello_da_ripristinare
    return providers

# ──────────────────────────────────────────────────────────────────────────────
# Salvataggio configurazione (per TUTTI i provider) + aggiornamento runtime
# ──────────────────────────────────────────────────────────────────────────────
def salva_configurazione(providers: Dict[str, Provider]):
    """
    Salva la configurazione di TUTTI i provider leggendo nell'ordine:
    valore in sessione -> valore memorizzato nel provider -> valore nella configurazione -> valore di default
    """
    configurazioni = []
    for nome, provider in providers.items():
        conf   = provider.to_dict()
        rag_conf = conf.get(Configurazione.RAG_KEY, {})
        # costruisco le chiavi da salvare
        apikey_key               = f"api_key_{nome}"
        modello_key              = f"modello_{nome}"
        agentic_key              = f"agentic_mode_{nome}"
        rag_enabled_key          = f"rag_enabled_{nome}"
        rag_topk_key             = f"rag_topk_{nome}"
        rag_model_key            = f"rag_model_{nome}"
        rag_modalita_ricerca_key = f"rag_modalita_ricerca_{nome}"
        
        # Prendo i valori da salvare
        base_url=provider.get_baseurl()
        api_key=st.session_state.get(apikey_key) or provider.get_apikey() or conf.get("api_key", provider.get_prefisso_token())
        modello=st.session_state.get(modello_key) or provider.get_modello_scelto() or conf.get("modello", "")
        modalita_agentica=st.session_state.get(agentic_key) or provider.get_modalita_agentica() or conf.get("modalita_agentica", False)
        attivo=st.session_state.get(rag_enabled_key) or provider.get_rag().get_attivo() or rag_conf.get("attivo", False)
        top_k=st.session_state.get(rag_topk_key) or provider.get_rag().get_topk() or rag_conf.get("top_k", Rag.DEFAULT_TOPK)
        directory_allegati=provider.get_rag().get_upload_dir() or rag_conf.get("directory_allegati", Rag.DEFAULT_UPLOAD_DIR)
        modalita_ricerca=st.session_state.get(rag_modalita_ricerca_key) or provider.get_rag().get_modalita_ricerca() or rag_conf.get("modalita_ricerca", Rag.AVAILABLE_SEARCH_MODALITIES[0])
        modello_rag=st.session_state.get(rag_model_key) or provider.get_rag().get_modello() or rag_conf.get("modello", Rag.DEFAULT_EMBEDDING_MODEL)
        
        # aggiungo la configurazione alla lista di quelle da salvare
        configurazioni.append({
                "nome": nome,
                "base_url": base_url,
                "api_key": api_key,
                "modello": modello,
                "modalita_agentica": modalita_agentica,
                Configurazione.RAG_KEY: {
                    "attivo": attivo,
                    "modello": modello_rag,
                    "top_k": top_k,
                    "directory_allegati": directory_allegati,
                    "modalita_ricerca": modalita_ricerca
                }
            })
        try: # rifletto immediatamente la configurazione sul provider
            provider.set_modello_scelto(configurazioni[nome]["modello"], st.session_state["autoload_chat_db"])
            provider.set_apikey(api_key)
            provider.set_rag(attivo=attivo, topk=top_k, modello=modello_rag, modalita_ricerca=modalita_ricerca)
        except Exception:
            pass # Non bloccare il salvataggio su errori runtime
    # salvo su file
    try:
        Configurazione.set(Configurazione.PROVIDERS_KEY, configurazioni)
        st.toast("Configurazione salvata ✅", icon="💾")
    except Exception as e:
        st.toast(f"Errore nel salvataggio: {e}", icon="💩")

# ──────────────────────────────────────────────────────────────────────────────
# Dialog configurazione tools per agent
# ──────────────────────────────────────────────────────────────────────────────
@st.dialog(
    "⚙️ Configurazione Tools per Agent",
    width="large",
    dismissible=True,
)
def mostra_dialog_tools_agent():
    """
    Dialog per configurare i tools disponibili per l'agent.
    I tools sono condivisi tra tutti i provider.
    Layout split: lista tools a sinistra, form configurazione a destra.
    """
    st.caption("Configura i tools disponibili per tutti i provider")
    
    # Inizializza la lista dei tools se non è già stata fatto
    if not DBAgent.TOOLS_LIST:
        with st.spinner("Caricamento tools disponibili..."):
            DBAgent.inizializza_tools_list()
    
    # Carica i tools già configurati dal DB
    tools_salvati = DBAgent.carica_tools()
    tools_salvati_dict = {t["nome_tool"]: t["configurazione"] for t in tools_salvati}
    
    # Inizializza lo stato della sessione per il tool selezionato
    if "selected_tool_for_config" not in st.session_state:
        st.session_state["selected_tool_for_config"] = None
    if "tool_config_temp" not in st.session_state:
        st.session_state["tool_config_temp"] = {}
    
    # Layout a due colonne
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("📋 Tools Disponibili")
        
        if not DBAgent.TOOLS_LIST:
            st.warning("Nessun tool disponibile. Verifica l'installazione di langchain-community.")
        else:
            # Mostra la lista dei tools con checkbox
            st.caption(f"Totale: {len(DBAgent.TOOLS_LIST)} tools")
            
            # Filtro di ricerca
            search_filter = st.text_input("🔍 Cerca tool", placeholder="Filtra per nome...")
            
            # Filtra i tools in base alla ricerca
            filtered_tools = [t for t in DBAgent.TOOLS_LIST if search_filter.lower() in t.lower()] if search_filter else DBAgent.TOOLS_LIST
            
            # Container scrollabile per la lista
            with st.container(height=400):
                for tool_name in sorted(filtered_tools):
                    is_configured = tool_name in tools_salvati_dict
                    
                    # Crea una riga per ogni tool
                    col_check, col_btn = st.columns([3, 1])
                    
                    with col_check:
                        # Checkbox per indicare se il tool è configurato
                        checked = st.checkbox(
                            tool_name,
                            value=is_configured,
                            key=f"tool_check_{tool_name}",
                            disabled=True,  # Solo visualizzazione
                            label_visibility="visible"
                        )
                    
                    with col_btn:
                        # Pulsante per configurare/modificare
                        if st.button("⚙️", key=f"config_btn_{tool_name}", help="Configura"):
                            st.session_state["selected_tool_for_config"] = tool_name
                            # Carica la configurazione esistente se presente
                            if tool_name in tools_salvati_dict:
                                st.session_state["tool_config_temp"] = tools_salvati_dict[tool_name].copy()
                            else:
                                st.session_state["tool_config_temp"] = {}
    
    with col_right:
        st.subheader("🔧 Configurazione Tool")
        
        selected_tool = st.session_state.get("selected_tool_for_config")
        
        if not selected_tool:
            st.info("👈 Seleziona un tool dalla lista per configurarlo")
        else:
            st.markdown(f"**Tool selezionato:** `{selected_tool}`")
            
            # Ottieni i parametri del tool
            tool_params = DBAgent.get_tool_params(selected_tool)
            
            if not tool_params or (len(tool_params) == 1 and "_description" in tool_params):
                st.info("Questo tool non ha parametri configurabili o non è stato possibile caricarli.")
                st.caption("Puoi comunque salvarlo per renderlo disponibile all'agent.")
            else:
                # Mostra la descrizione se disponibile
                if "_description" in tool_params:
                    with st.expander("📖 Descrizione", expanded=False):
                        st.text(tool_params["_description"])
                
                st.divider()
                st.caption("Configura i parametri del tool:")
                
                # Form dinamico basato sui parametri
                config_temp = st.session_state["tool_config_temp"]
                
                for param_name, param_info in tool_params.items():
                    if param_name == "_description":
                        continue
                    
                    param_type = param_info.get("type", "str")
                    param_default = param_info.get("default")
                    param_desc = param_info.get("description", "")
                    
                    # Valore corrente (da config temp o default)
                    current_value = config_temp.get(param_name, param_default)
                    
                    # Crea il widget appropriato in base al tipo
                    if "int" in param_type.lower():
                        value = st.number_input(
                            param_name,
                            value=int(current_value) if current_value is not None else 0,
                            help=param_desc,
                            key=f"param_{selected_tool}_{param_name}"
                        )
                        config_temp[param_name] = value
                    
                    elif "float" in param_type.lower():
                        value = st.number_input(
                            param_name,
                            value=float(current_value) if current_value is not None else 0.0,
                            help=param_desc,
                            key=f"param_{selected_tool}_{param_name}",
                            format="%.2f"
                        )
                        config_temp[param_name] = value
                    
                    elif "bool" in param_type.lower():
                        value = st.checkbox(
                            param_name,
                            value=bool(current_value) if current_value is not None else False,
                            help=param_desc,
                            key=f"param_{selected_tool}_{param_name}"
                        )
                        config_temp[param_name] = value
                    
                    elif "list" in param_type.lower() or "List" in param_type:
                        # Per liste, usa text_area con valori separati da virgola
                        list_value = ", ".join(str(v) for v in current_value) if isinstance(current_value, list) else str(current_value or "")
                        value = st.text_area(
                            param_name,
                            value=list_value,
                            help=f"{param_desc}\n(Valori separati da virgola)",
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
                            help=param_desc,
                            key=f"param_{selected_tool}_{param_name}"
                        )
                        config_temp[param_name] = value
                
                st.session_state["tool_config_temp"] = config_temp
            
            st.divider()
            
            # Pulsanti di azione
            col_save, col_remove, col_cancel = st.columns(3)
            
            with col_save:
                if st.button("💾 Salva Tool", type="primary", use_container_width=True):
                    try:
                        DBAgent.salva_tool({
                            "nome_tool": selected_tool,
                            "configurazione": st.session_state["tool_config_temp"]
                        })
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
                            DBAgent.cancella_tool({"nome_tool": selected_tool})
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
    
    st.divider()
    
    # Sezione gestione database
    st.subheader("🗄️ Gestione Database")
    col_import, col_export, col_delete = st.columns(3)
    
    with col_import:
        uploaded_file = st.file_uploader("📥 Importa configurazione", type=["json"], key="import_agent_db")
        if uploaded_file and st.button("Importa", key="btn_import_agent_db"):
            try:
                json_data = uploaded_file.read().decode("utf-8")
                DBAgent.importa_db(json_data)
                st.success("✅ Configurazione importata!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore nell'importazione: {e}")
    
    with col_export:
        if st.button("📤 Esporta configurazione", key="btn_export_agent_db", use_container_width=True):
            try:
                json_data = DBAgent.esporta_db()
                filename = f"agentdb-{datetime.now().strftime('%Y%m%d')}.json"
                st.download_button(
                    label="⬇️ Scarica",
                    data=json_data,
                    file_name=filename,
                    mime="application/json",
                    key="download_agent_db"
                )
            except Exception as e:
                st.error(f"Errore nell'esportazione: {e}")
    
    with col_delete:
        if st.button("🗑️ Elimina database", key="btn_delete_agent_db", use_container_width=True):
            if st.session_state.get("confirm_delete_agent_db", False):
                try:
                    DBAgent.elimina_db()
                    st.success("✅ Database eliminato!")
                    st.session_state["confirm_delete_agent_db"] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore nell'eliminazione: {e}")
            else:
                st.session_state["confirm_delete_agent_db"] = True
                st.warning("⚠️ Clicca di nuovo per confermare l'eliminazione")
    
    st.divider()
    
    # Pulsante chiudi
    if st.button("✅ Salva e Chiudi", type="primary", use_container_width=True):
        st.session_state["tools_dialog_open"] = False
        st.session_state["selected_tool_for_config"] = None
        st.session_state["tool_config_temp"] = {}
        st.rerun()

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
def crea_sidebar(providers: Dict[str, Provider]):
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
                    # Aggiorna la selezione del modello per quel provider                    "
                    st.session_state[f"modello_{prov}"] = mod
            
            chat_recenti = ["",]
            for nome_prov, prov in providers.items():
                modelli = prov.get_lista_modelli_con_chat()
                chat_recenti.extend([f"{nome_prov} | {modello}" for modello in modelli])
            if "chat_db_key" in st.session_state and st.session_state["chat_db_key"]:
                chat_su_disco=set([f"{prov} | {mod}" for prov, mod in StoricoChat.ritorna_chat_recenti()])
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
            # Toggle Modalità agentica
            modalita_agentica = st.toggle("Abilita Modalità Agentica", value=st.session_state[provider_scelto][agentic_key],
                       key=agentic_key, on_change=sincronizza_sessione, args=(agentic_key,))
            
            if modalita_agentica:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Pulsante per configurare i tools
                    if st.button("⚙️ Configura Tools", key="btn_config_tools", use_container_width=True):
                        st.session_state["tools_dialog_open"] = True
                
                with col2:
                    # Link per gestione avanzata DB agent.db (server avviato automaticamente all'inizializzazione)
                    if DBAgent.is_sqlite_web_active():
                        url = DBAgent.get_sqlite_web_url()
                        st.markdown(
                            f'<a href="{url}" target="_blank">'
                            '<button style="width:100%; padding:8px; font-size:1rem;">'
                            '🔍 Gestione avanzata DB'
                            '</button></a>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            '<button style="width:100%; padding:8px; font-size:1rem; opacity:0.5;" disabled>'
                            '🔍 Server DB non disponibile'
                            '</button>',
                            unsafe_allow_html=True
                        )
                
                # Mostra info sui tools configurati
                tools_config = DBAgent.carica_tools()
                if tools_config:
                    st.caption(f"✅ {len(tools_config)} tool(s) configurato/i")
                    with st.expander("📋 Tools configurati", expanded=False):
                        for tool in tools_config:
                            st.write(f"• **{tool['nome_tool']}**")
                else:
                    st.info("ℹ️ Nessun tool configurato. Clicca su 'Configura Tools' per iniziare.")
            
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
                                StoricoChat.salva_chat(provider_scelto, modello_scelto, cronologia)
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
                                                StoricoChat.salva_chat(nome_p, modello, prov.get_cronologia_messaggi(modello=modello))
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
                            json_data = StoricoChat.esporta_json()
                            st.download_button(
                                label="⬇️ Esporta tutte le chat",
                                data=json_data,
                                file_name=filename,
                                mime="application/json"
                            )
                            st.caption("ℹ️ Scarica il contenuto del DB delle chat in formato JSON")
                        except Exception as e:
                            st.exception(e)
                    with col2:
                        st.subheader("Importa")
                        # Importa DB JSON
                        try:
                            json_file = st.file_uploader("📥 Seleziona JSON da importare", type=["json"])
                            if json_file and st.button("📥 Importa chat"):
                                text = json_file.read().decode("utf-8")
                                StoricoChat.importa_json(text)
                                st.success("Chat importate", icon="✅")
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
                                StoricoChat.cancella_chat(provider_scelto, modello_scelto)
                                st.success("Chat cancellata dal disco", icon="✅")      
                            except Exception as e:
                                st.exception(e)
                    with col4: # Cancella tutto il DB
                        st.subheader("Elimina tutto il DB")
                        elimina=st.button("💥 Elimina tutto il DB")
                        st.caption("ℹ️ Il database con tutte le chat salvate viene eliminato definitivamente dal disco. Tutti i dati non esportati andranno persi.")
                        if elimina:
                            try:
                                StoricoChat.cancella_tutto()
                                st.success("DB eliminato", icon="✅")
                            except Exception as e:
                                st.exception
            # Gestisci cronologie (placeholder)
            if StoricoChat.is_sqlite_web_active():
                url = StoricoChat.get_sqlite_web_url()
                st.markdown(
                    f'<a href="{url}" target="_blank">'
                    '<button style="width:100%; padding:8px; font-size:1rem;">'
                    '🔍 Gestione avanzata DB'
                    '</button></a>',
                    unsafe_allow_html=True
                )
            else:
                if st.button("🔍 Avvia e apri la gestione avanzata del DB"):
                    started = StoricoChat.start_sqlite_web_server()
                    if started:
                        st.toast("Server DB avviato", icon="🌐")
                    else:
                        st.error("Avvio sqlite‑web fallito")

        # Salva configurazione (tutti i provider)
        st.button("Salva configurazione", key="salva", on_click=salva_configurazione, args=[providers])
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
    render_map = {
        "text": st.write,
        "text-plain": st.text,
        "image": st.image,
        "audio": st.audio,
        "video": st.video,
    }
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
                    render = render_map.get(allegato.tipo)
                    if render:
                        render(allegato.contenuto)
                    elif allegato.tipo == "file":
                        st.write(f"📄 File ricevuto dal modello: {allegato.mime_type}")
                    else:
                        st.write("⚠️ Ricevuto un allegato sconosciuto ⚠️")