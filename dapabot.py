import sys
import streamlit as st
from datetime import datetime
sys.path.append('src/')
from src.gui_utils import inizializza, crea_sidebar, generate_response, mostra_cronologia_chat

st.title("🤖 DapaBot 🤖")    
providers, providers_disponibili, cronologia_chat, cookie_controller = inizializza()
provider_scelto, modello_scelto, api_key, messaggio_di_sistema, rag_abilitato, providers_disponibili, apikey_provider, select_modello_provider = crea_sidebar(st.session_state.providers, providers_disponibili, cookie_controller)
                            
if provider_scelto in providers_disponibili:
    prompt = st.chat_input("Scrivi il tuo messaggio...", accept_file="multiple")
    provider = providers[provider_scelto]

    if apikey_provider in st.session_state and not api_key.startswith(provider.prefisso_token()):
        st.warning("Inserisci il token per l'API!", icon="⚠️")
    provider.set_client(modello_scelto, api_key)
    cronologia = provider.get_cronologia_messaggi()
    if not prompt: # se non è stato inviato alcun messaggio dall'utente allora si limita a caricare la cronologia dei messaggi già esistente
        mostra_cronologia_chat(cronologia)
    else: # altrimenti invia il messaggio al modello e carica la cronologia comprensiva di risposta
        cookie_controller.set(apikey_provider, api_key) # persisto l'api_key inserita nei cookie  
        cookie_controller.set(select_modello_provider, modello_scelto)
        if apikey_provider in st.session_state and api_key.startswith(provider.prefisso_token()):
            # Genera la risposta
            try:
                generate_response(prompt, messaggio_di_sistema, providers_disponibili, provider_scelto, rag_abilitato)
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
                cronologia = provider.get_cronologia_messaggi()
                # Mostra la cronologia
                mostra_cronologia_chat(cronologia)
            except Exception as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                with st.chat_message("assistant"):
                    st.markdown(
                        f"<div style='color: red;'><strong>⚠️ Errore cronologia ({timestamp}):</strong> {str(e)}</div>",
                        unsafe_allow_html=True
                    )
