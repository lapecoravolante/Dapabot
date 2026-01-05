import streamlit as st
from datetime import datetime
from src.gui_utils import inizializza, crea_sidebar, generate_response, mostra_cronologia_chat
from src.SessionManager import SessionManager
from src.providers.base import Provider

sm = SessionManager()

st.title("🤖 DapaBot 🤖")    
providers, cronologia_chat = inizializza()
provider_scelto, modello_scelto, api_key, messaggio_di_sistema, apikey_provider, select_modello_provider= crea_sidebar(st.session_state.providers)

provider : Provider = providers[provider_scelto]                         
if provider.disponibile():
    prompt = st.chat_input("Scrivi il tuo messaggio...", accept_file="multiple")
    if apikey_provider in st.session_state and not api_key.startswith(provider.prefisso_token()):
        st.warning("Inserisci il token per l'API!", icon="⚠️")
    provider.set_client(modello_scelto, api_key)
    if not prompt: # se non è stato inviato alcun messaggio dall'utente allora si limita a caricare la cronologia dei messaggi già esistente
        mostra_cronologia_chat(provider.get_cronologia_messaggi())
    else: # altrimenti invia il messaggio al modello e carica la cronologia comprensiva di risposta
        sm.salva_cookie(apikey_provider, api_key) # persisto l'api_key inserita nei cookie  
        sm.salva_cookie(select_modello_provider, modello_scelto)
        if apikey_provider in st.session_state and api_key.startswith(provider.prefisso_token()):
            # Genera la risposta
            try:
                generate_response(prompt, messaggio_di_sistema, provider)
            except Exception as e:
                # Mostra l'errore come messaggio della chat
                # Usa il timestamp del messaggio utente se disponibile
                timestamp = datetime.now().strftime("%H:%M:%S")
                with st.chat_message("assistant"):
                    st.markdown(
                        f"<div style='color: red;'><strong>⚠️ Errore ({timestamp}):</strong> {str(e)}</div>",
                        unsafe_allow_html=True
                    )
            # Recupera tutta la cronologia aggiornata
            try:
                # Mostra la cronologia
                mostra_cronologia_chat(provider.get_cronologia_messaggi())
            except Exception as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                with st.chat_message("assistant"):
                    st.markdown(
                        f"<div style='color: red;'><strong>⚠️ Errore cronologia ({timestamp}):</strong> {str(e)}</div>",
                        unsafe_allow_html=True
                    )
