import streamlit as st
import extra_streamlit_components as stx
from src.Messaggio import Messaggio
from src.Configurazione import Configurazione
from src.providers.loader import Loader
from src.SessionManager import SessionManager
from src.providers.base import Provider
from src.providers.rag import Rag
from typing import Dict, List, Tuple

configurazione = Configurazione()
sm = SessionManager()

def inizializza():
    if "providers" not in st.session_state:# carica i providers 
        st.session_state.providers = Loader.discover_providers()
    providers = st.session_state.providers # shortcut per il nome della variabile         
    cronologia_chat = {} # dizionario che associa ad ogni modello la propria cronologia di messaggi
    return providers, cronologia_chat

# Salva la configurazione leggendo i valori direttamente dalla GUI (st.session_state).

def salva_configurazione(providers):
    configurazioni = []

    for nome, provider in providers.items():
        # Dizionario corrente del provider (fonte di verità quando la GUI non ha chiavi)
        p_dict = provider.to_dict()
        rag_conf = p_dict.get(Configurazione.RAG_KEY, {})

        # Chiavi dei widget in GUI
        apikey_key                  = f"api_key_{nome}"
        modello_key                 = f"modello_{nome}"
        rag_enabled_key             = f"rag_enabled_{nome}"
        rag_topk_key                = f"rag_topk_{nome}"
        rag_model_key               = f"rag_model_{nome}"
        rag_modalita_ricerca_key    = f"rag_modalita_ricerca_{nome}"

        # ✅ Leggo dalla GUI, ma se la chiave NON esiste (tab non renderizzata),
        #    faccio fallback ai valori correnti del provider (p_dict/rag_conf)
        api_key_val                 = st.session_state.get(apikey_key,      p_dict.get("api_key", ""))
        modello_val                 = st.session_state.get(modello_key,     p_dict.get("modello", ""))
        rag_enabled_val             = st.session_state.get(rag_enabled_key, rag_conf.get("attivo", False))
        rag_topk_val                = st.session_state.get(rag_topk_key,    rag_conf.get("top_k", 3))
        rag_model_val               = st.session_state.get(rag_model_key,   rag_conf.get("modello", ""))
        rag_modalita_ricerca_val    = st.session_state.get(rag_modalita_ricerca_key, rag_conf.get("modalita_ricerca", ""))

        # directory_allegati: usiamo lo stato runtime del Rag, con fallback a config
        directory_allegati_val = provider.get_rag().get_upload_dir() or rag_conf.get("directory_allegati", "uploads/")

        configurazioni.append({
            "nome": nome,
            "base_url": provider.get_baseurl(),
            "api_key": api_key_val,
            "modello": modello_val,
            Configurazione.RAG_KEY: {
                "attivo": rag_enabled_val,
                "modello": rag_model_val,
                "top_k": rag_topk_val,
                "directory_allegati": directory_allegati_val,
                "modalita_ricerca": rag_modalita_ricerca_val,
            }
        })

    configurazione.set(Configurazione.PROVIDERS_KEY, configurazioni)

@st.dialog("🖴 Cache dei vector stores",           
            width="medium",          # small | medium | large
            dismissible=False,      # 👈 impedisce chiusura clic fuori, X, ESC
            on_dismiss="ignore"     # (facoltativo) non fare nulla su dismiss
          )
def mostra_dialog_vectorestores_globale(righe: List[Tuple[str, object, str, str, str, str]]):
    """
    Renderizza la modale globale con tabella:
    File | Modello | Elimina
    - Nessuna colonna Provider
    - Raggruppa per (label, model_name) aggregando tutte le occorrenze tra i provider
    - L'eliminazione agisce su tutte le occorrenze del gruppo
    """
    st.caption("Elenco dei vectorstore in cache disponibili per la cancellazione")

    # --- Raggruppa per (label, model_name) ---
    # righe: (provider_name, rag, id_str, collection_name, label, model_name)
    gruppi: Dict[Tuple[str, str], List[Tuple[str, object, str, str]]] = {}
    for provider_name, rag, id_str, coll_name, label, model_name in (righe or []):
        key = (label, model_name)
        gruppi.setdefault(key, []).append((provider_name, rag, id_str, coll_name))

    # Intestazioni tabella: 3 colonne
    header_cols = st.columns([0.50, 0.30, 0.20])
    with header_cols[0]:
        st.markdown("**File**")
    with header_cols[1]:
        st.markdown("**Modello**")
    with header_cols[2]:
        st.markdown("**Elimina**")

    if not gruppi:
        st.info("Nessun vector store disponibile.")
    else:
        # Render righe aggregate
        for idx, ((label, model_name), entries) in enumerate(gruppi.items()):
            row_cols = st.columns([0.50, 0.30, 0.20])
            with row_cols[0]:
                st.write(f"_{label}_")
            with row_cols[1]:
                st.code(model_name)
            with row_cols[2]:
                # ❌ Elimina tutte le occorrenze di questo (File, Modello) in tutti i provider
                if st.button("❌", key=f"del_vs_group_{idx}", help="Elimina questo vector store da tutti i provider"):
                    errori: List[str] = []
                    for provider_name, rag, id_str, _coll_name in entries:
                        ok = rag.delete_vectorstore(id_str)
                        if not ok:
                            errori.append(provider_name)
                    if errori:
                        st.warning(f"Impossibile eliminare da: {', '.join(errori)}")
                    else:
                        st.success(f"Eliminato: {label} • {model_name} (tutti i provider)")
                    st.rerun()

    st.divider()

    # Elimina tutto (su tutti i gruppi / provider)
    if st.button("Elimina tutto", type="primary", key="del_all_vs_global"):
        # Flatten di tutte le entry
        flat_entries: List[Tuple[str, object, str, str]] = [
            (provider_name, rag, id_str, coll_name)
            for (_label, _model), entries in gruppi.items()
            for (provider_name, rag, id_str, coll_name) in entries
        ]
        errori: List[str] = []
        for provider_name, rag, id_str, _coll_name in flat_entries:
            ok = rag.delete_vectorstore(id_str)
            if not ok:
                errori.append(provider_name)
        if errori:
            st.warning("Impossibile eliminare da: " + ", ".join(sorted(set(errori))))
        else:
            st.success("Tutti i vector store sono stati eliminati.")
        st.rerun()

    # Chiudi modale
    if st.button("Chiudi", key="close_vs_dialog_global"):
        st.session_state["vs_dialog_global_open"] = False
        st.rerun()
   
def crea_sidebar(providers):
    st.logo(image="src/img/testa.png", size="large")

    if "provider_scelto" not in st.session_state:
        st.session_state["provider_scelto"] = list(providers)[0]

    with st.sidebar:
        # ---------- Provider ----------
        schede = [stx.TabBarItemData(id=nome, title=nome, description="") for nome in providers]
        provider_scelto = stx.tab_bar(data=schede, key="provider_scelto")
        sm.sync_cookie("provider_scelto")

        provider : Provider = providers[provider_scelto]
        provider.set_disponibile(True)

        # ---------- API Key ----------
        apikey_key = f"api_key_{provider_scelto}"
        sm.bootstrap_key(apikey_key, default=provider.get_apikey())
        api_key = st.text_input("🗝️ API Key", type="password", key=apikey_key)
        sm.sync_cookie(apikey_key)

        # ---------- Modello principale ----------
        modelli = list(provider.lista_modelli(api_key=api_key))  # forza lista
        select_modello_key = f"modello_{provider_scelto}"
        modello_default = provider.get_modello_scelto() if provider.get_modello_scelto() else (modelli[0] if modelli else None)
        modello_scelto = sm.selectbox(select_modello_key, "👾 Modello", modelli, default=modello_default)

        # ---------- Messaggio di sistema ----------
        system_msg_key = f"system_msg_{provider_scelto}"
        sm.bootstrap_key(system_msg_key, default="")
        messaggio_di_sistema = st.text_area(
            "📝Messaggio di sistema",
            placeholder="Il messaggio con cui viene istruito il modello prima di rispondere",
            key=system_msg_key
        )
        sm.sync_cookie(system_msg_key)

        # ---------- RAG ----------
        conf = provider.to_dict().get("rag", {})
        rag_expander_key = f"rag_expanded_{provider_scelto}"
        rag_key = f"rag_enabled_{provider_scelto}"
        topk_key = f"rag_topk_{provider_scelto}"
        modello_rag_key = f"rag_model_{provider_scelto}"
        modalita_ricerca_rag_key=f"rag_modalita_ricerca_{provider_scelto}"
        sm.bootstrap_key(modalita_ricerca_rag_key, default=conf.get("modalita_ricerca", provider.get_rag().get_modalita_ricerca())
)


        # Inizializza topk, modello RAG e modalità di ricerca (solo se non presenti)
        sm.bootstrap_key(topk_key, default=conf.get("top_k", 3))
        modelli_rag = list(provider.lista_modelli_rag())
        default_modello_rag = conf.get("modello", modelli_rag[0] if modelli_rag else None)
        sm.bootstrap_key(modello_rag_key, default=default_modello_rag)

        # Inizializza il toggle solo se non esiste
        sm.bootstrap_key(rag_key, default=conf.get("attivo", False))

        # Expander per il RAG
        if rag_expander_key not in st.session_state:
            st.session_state[rag_expander_key] = st.session_state[rag_key]

        with st.expander("🔎 RAG", expanded=st.session_state[rag_expander_key]):
            # Toggle senza passare default
            rag_abilitato = sm.toggle(rag_key, label="Abilita RAG")
            st.session_state[rag_expander_key] = rag_abilitato
            # Numero di documenti top K
            topk = sm.number_input(topk_key, label="🔝 Top K", min_value=1, step=1)
            # tipo di ricerca per il Rag
            modalita_ricerca=sm.selectbox(modalita_ricerca_rag_key, "🔦 Modalità di ricerca", Rag.AVAILABLE_SEARCH_MODALITIES, default=Rag.AVAILABLE_SEARCH_MODALITIES[0])
            # Modello RAG
            modello_rag = sm.selectbox(modello_rag_key, "🕵️ Modello per il RAG", modelli_rag)

            # ---- Pulsante globale per aprire la finestra MODALE con TUTTI i vector store ----
            if st.button("Cache...", key="btn_vs_global", help="Gestisci tutti i vector store di tutti i provider", icon="🗄️"):
                st.session_state["vs_dialog_global_open"] = True

            # Aggiorna provider con RAG attivo
            provider.set_rag(attivo=rag_abilitato, topk=topk, modello=modello_rag, modalita_ricerca=modalita_ricerca)

        st.button("Salva configurazione", key="salva", on_click=salva_configurazione, args=[providers])
    
    # ---- Render della finestra modale ----
    if st.session_state.get("vs_dialog_global_open", False):
        righe = Rag.costruisci_righe(providers)
        mostra_dialog_vectorestores_globale(righe)

    return provider_scelto, modello_scelto, api_key, messaggio_di_sistema, apikey_key, select_modello_key

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
