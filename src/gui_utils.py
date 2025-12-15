import streamlit as st
from streamlit_cookies_controller import CookieController
from Rag import Rag
import extra_streamlit_components as stx
from Messaggio import Messaggio
from HuggingfaceProvider import HuggingfaceProvider
from OpenRouterProvider import OpenRouterProvider

def inizializza():
    cookie_controller = CookieController()
    # tutti i provider supportati
    if "providers" not in st.session_state.keys():
        st.session_state.providers={"Huggingface": HuggingfaceProvider(), 
                                    "Openrouter": OpenRouterProvider()} 
        
    providers = st.session_state.providers # shortcut per il nome della variabile
    providers_disponibili = {} # tutti i provider raggiungibili via rete
    cronologia_chat = { # dizionario che associa ad ogni modello la propria cronologia di messaggi
        # "Huggingface-MiniMaxAI/MiniMax-M2": ["ciao", "Ciao, come posso aiutarti", ....]
        # "Openrouter-gpt-oss-20b:free" : ["ciao", "Ciao, come posso aiutarti", ....]
    } 
    return providers, providers_disponibili, cronologia_chat, cookie_controller

def crea_sidebar(providers, providers_disponibili, cookie_controller):
    schede=[]
    st.logo(image="src/img/testa.png", size="large")
    with st.sidebar:
        for nome_provider in providers:
            schede.append(stx.TabBarItemData(id=nome_provider, title=nome_provider, description=""))
        provider_scelto = stx.tab_bar(data=schede, default=list(providers)[0]) # popola le tab nella sidebar
        apikey_provider = f"api_key_{provider_scelto}"
        if cookie_controller.get(apikey_provider):
            st.session_state[apikey_provider]=cookie_controller.get(apikey_provider)
        api_key=st.text_input("🗝️ API Key", type="password", key=apikey_provider)
        for nome_provider, provider in providers.items():
            if nome_provider == provider_scelto:
                # verifica se per ogni provider esiste almeno un modello disponibile
                if len(provider.lista_modelli(api_key=api_key)): 
                    select_modello_provider=f"select_{nome_provider}"
                    valore_cookie = cookie_controller.get(select_modello_provider)
                    if valore_cookie is not None and select_modello_provider not in st.session_state:
                        st.session_state[select_modello_provider] = valore_cookie
                    modello_scelto=st.selectbox("👾 Modello", options=provider.lista_modelli(api_key=api_key), key=select_modello_provider)
                    cookie_controller.set(select_modello_provider, modello_scelto)
                    providers_disponibili[nome_provider] = provider
                else: # altrimenti non è riuscito a scaricare il nome di alcun modello e mostra un errore
                    if nome_provider in providers_disponibili:
                        providers_disponibili.remove(nome_provider)
                    st.error("🤯 Errore di connessione, ricarica la pagina per riprovare")
                    st.button("Ricarica")               
        with st.expander("Avanzate"):
            messaggio_di_sistema = st.text_area("Messaggio di sistema", placeholder="Il messaggio con cui viene istruito il modello prima di rispondere", width="stretch")
            rag_abilitato=st.checkbox("Abilita RAG", key="rag_abilitato")
    return provider_scelto, modello_scelto, api_key, messaggio_di_sistema, rag_abilitato, providers_disponibili, apikey_provider, select_modello_provider

def generate_response(prompt_utente, messaggio_di_sistema, providers_disponibili, provider_scelto, rag_abilitato):
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
        # Se è stato abilitato il RAG, sostituisco gli allegati con quelli tornati dal vector DB.
        # Viene fatto dentro la if prompt_utente["files"] perchè ci devono essere dei files, altrimenti non ha senso.
        if rag_abilitato: 
            rag=Rag(prompt=messaggio_utente, modello=providers_disponibili[provider_scelto])
            allegati_rag=rag()
            messaggio_utente.set_allegati([])  
            preambolo="\r\nRispondi dando priorità al contesto fornito di seguito:\r\n"
            contenuti_rag="\r\n-----\r\n".join(allegato.contenuto for allegato in allegati_rag)
            messaggio_utente.set_testo(messaggio_utente.get_testo()+ preambolo + contenuti_rag)
    messaggi_da_inviare.append(messaggio_utente)    
    # Invia i messaggi
    providers_disponibili[provider_scelto].invia_messaggi(messaggi_da_inviare)  
    
def mostra_cronologia_chat(cronologia: list[Messaggio]):
    for msg in cronologia:                    
        ruolo = msg.get_ruolo()  # 'user', 'assistant', 'ai' o 'system'
        testo = msg.get_testo()
        allegati=msg.get_allegati()
        if ruolo == "system":  # Evidenzia i messaggi di sistema
            st.info(testo) 
        else:
            with st.chat_message(ruolo, avatar="src/img/testa.png" if ruolo != "user" else None):
                for allegato in allegati:
                    match allegato.tipo:
                        case "text":
                            st.write(allegato.contenuto)
                        case "text-plain":
                            st.text(allegato.contenuto)
                        case "image":
                            st.image(allegato.contenuto)
                        case "audio":
                            st.audio(allegato.contenuto)
                        case "video":
                            st.video(allegato.contenuto)
                        case "file":
                            st.write(f"📄 File ricevuto dal modello: {allegato['mime_type']}")
                        case _: 
                            st.write("⚠️Ricevuto un allegato sconosciuto⚠️")