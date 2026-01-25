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

# ──────────────────────────────────────────────────────────────────────────────
# Bootstrap iniziale
# ──────────────────────────────────────────────────────────────────────────────
def inizializza():
    if "providers" not in st.session_state:  # carica i providers una sola volta
        st.session_state.providers = Loader.discover_providers()
    providers = st.session_state.providers  # shortcut
    for nome, provider in providers.items():
        conf = provider.to_dict()
        rag_conf = conf.get(Configurazione.RAG_KEY, {})

        apikey_key               = f"api_key_{nome}"
        modello_key              = f"modello_{nome}"
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
                sysmsg_key: st.session_state.get(sysmsg_key, ""),
                rag_enabled_key: st.session_state.get(rag_enabled_key) or provider.get_rag().get_attivo() or rag_conf.get("attivo", False),
                rag_topk_key: st.session_state.get(rag_topk_key) or provider.get_rag().get_topk() or rag_conf.get("top_k", Rag.DEFAULT_TOPK),
                rag_model_key: st.session_state.get(rag_model_key) or provider.get_rag().get_modello() or rag_conf.get("modello", Rag.DEFAULT_EMBEDDING_MODEL),
                rag_modalita_ricerca_key: st.session_state.get(rag_modalita_ricerca_key) or provider.get_rag().get_modalita_ricerca() or rag_conf.get("modalita_ricerca", Rag.AVAILABLE_SEARCH_MODALITIES[0])
            }
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
        rag_enabled_key          = f"rag_enabled_{nome}"
        rag_topk_key             = f"rag_topk_{nome}"
        rag_model_key            = f"rag_model_{nome}"
        rag_modalita_ricerca_key = f"rag_modalita_ricerca_{nome}"
        
        # Prendo i valori da salvare
        base_url=provider.get_baseurl()
        api_key=st.session_state.get(apikey_key) or provider.get_apikey() or conf.get("api_key", provider.get_prefisso_token())
        modello=st.session_state.get(modello_key) or provider.get_modello_scelto() or conf.get("modello", "")
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
                Configurazione.RAG_KEY: {
                    "attivo": attivo,
                    "modello": modello_rag,
                    "top_k": top_k,
                    "directory_allegati": directory_allegati,
                    "modalita_ricerca": modalita_ricerca
                }
            })
        try: # rifletto immediatamente la configurazione sul provider
            provider.set_modello_scelto(configurazioni[nome]["modello"])
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

    # imposto il default per la tab_bar sottostante
    if "provider_scelto" not in st.session_state:
        st.session_state["provider_scelto"] = next(iter(providers))

    with st.sidebar:
        # Costruzione tab bar
        schede = [stx.TabBarItemData(id=nome, title=nome, description="") for nome in providers]
        provider_scelto = stx.tab_bar(data=schede, key="provider_scelto")
        provider: Provider = providers[provider_scelto]

        # Chiavi per il provider corrente
        apikey_key                  = f"api_key_{provider_scelto}"
        modello_key                 = f"modello_{provider_scelto}"
        rag_enabled_key             = f"rag_enabled_{provider_scelto}"
        rag_topk_key                = f"rag_topk_{provider_scelto}"
        rag_model_key               = f"rag_model_{provider_scelto}"
        rag_modalita_ricerca_key    = f"rag_modalita_ricerca_{provider_scelto}"
        sysmsg_key                  = f"system_msg_{provider_scelto}"

        # Opzioni correnti
        modelli     = list(provider.lista_modelli(api_key=st.session_state[provider_scelto][apikey_key]))
        modelli_rag = list(provider.lista_modelli_rag())
        modalities  = list(Rag.AVAILABLE_SEARCH_MODALITIES)

        # --- Widget: inizializzazione robusta ---
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
            modello_scelto = st.selectbox("👾 Modello", modelli, key=modello_key,
                index=modelli.index(st.session_state[provider_scelto][modello_key]) if st.session_state[provider_scelto][modello_key] in modelli else 0,
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

            # Aggiorna provider runtime (usa i valori restituiti dai widget)
            try:
                provider.set_client(modello_scelto, api_key)
                provider.set_rag(attivo=rag_abilitato, topk=topk, modello=modello_rag, modalita_ricerca=modalita_ricerca)
            except Exception as e:
                st.toast(f"Errore nell'impostazione dei parametri: {e}", icon="⛔")
            # ---- Pulsante globale per aprire la finestra MODALE con TUTTI i vector store ----
            if st.button("Cache...", key="btn_vs_global", help="Gestisci tutti i vector store di tutti i provider", icon="🗄️"):
                st.session_state["vs_dialog_global_open"] = True
        # ──────────────────────────────────────────────────────────────────────────────
        # Sezione Croologie
        # ──────────────────────────────────────────────────────────────────────────────
        with st.expander("💬 Gestione cronologie chat", expanded=False):
            with st.popover("💾 Salva cronologia..."):    
                # Pulsante: Salva cronologia corrente
                if st.button("💾 Salva cronologia corrente"):
                    cronologia = provider.get_cronologia_messaggi()
                    StoricoChat.salva_chat(provider_scelto, st.session_state[modello_key], cronologia)
                    st.toast("Cronologia salvata nel DB", icon="💾")
                # Pulsante: Salva tutte le cronologie
                if st.button("🗃️ Salva tutte le cronologie"):
                    for nome_p, prov in providers.items():
                        mod_corr = prov.get_modello_scelto()
                        if mod_corr:
                            StoricoChat.salva_chat(nome_p, mod_corr, prov.get_cronologia_messaggi())
                    st.toast("Tutte le cronologie salvate", icon="🗃️")
            with st.popover("🔁 Importa/esporta..."):    
                # Esporta DB JSON                
                # genera la stringa di data/ora
                ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"storico_{ts}.json"
                json_data = StoricoChat.esporta_json()
                st.download_button(
                    label="⬇️ Export DB in Json",
                    data=json_data,
                    file_name=filename,
                    mime="application/json"
                )
                # Importa DB JSON
                json_file = st.file_uploader("📥 Seleziona JSON da importare", type=["json"])
                if json_file and st.button("📥 Importa cronologie"):
                    text = json_file.read().decode("utf-8")
                    StoricoChat.importa_json(text)
                    st.toast("Importazione completata!", icon="✔️")
            
            with st.popover("🚮 Elimina cronologia..."):    
                # Cancella cronologia corrente
                if st.button("🗑️ Cancella cronologia corrente"):
                    StoricoChat.cancella_cronologia(provider_scelto, st.session_state[modello_key])
                    st.toast("Cronologia cancellata", icon="🗑️")      
                # Cancella tutto il DB
                if st.button("🧹 Cancella tutto il DB"):
                    StoricoChat.cancella_tutto()
                    st.toast("DB cancellato", icon="🧹")

            # Gestisci cronologie (placeholder)
            if st.button("🔍 Gestisci cronologie"):
                st.toast("Funzione da implementare", icon="ℹ️")


        # Salva configurazione (tutti i provider)
        st.button("Salva configurazione", key="salva", on_click=salva_configurazione, args=[providers])
    #st.sidebar.json(st.session_state)
    
    # ---- Render della finestra modale ----
    if st.session_state.get("vs_dialog_global_open", False):
        mostra_dialog_vectorestores_globale()

    return provider_scelto, messaggio_di_sistema

# ──────────────────────────────────────────────────────────────────────────────
# Invio messaggi & render cronologia
# ──────────────────────────────────────────────────────────────────────────────
def generate_response(prompt_utente, messaggio_di_sistema, provider_scelto: Provider):
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
    # Invia i messaggi
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