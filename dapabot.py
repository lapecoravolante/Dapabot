import streamlit as st
from datetime import datetime
from src.gui_utils import inizializza, crea_sidebar, generate_response, mostra_cronologia_chat
from src.providers.base import Provider

st.title("🤖 DapaBot 🤖")    
providers = inizializza()
provider_scelto, messaggio_di_sistema = crea_sidebar(st.session_state.providers)

provider : Provider = providers[provider_scelto]                         
if provider.disponibile():
    prompt = st.chat_input("Scrivi il tuo messaggio...", accept_file="multiple")
    mostra_cronologia_chat(provider.get_cronologia_messaggi())
    if prompt: # invia il messaggio al modello e carica la cronologia comprensiva di risposta
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
        else:
            # Recupera tutta la cronologia aggiornata
            try:
                # Aggiunge alla cronologia a schermo anche l'ultimo messaggio inviato dall'utente e la relativa risposta del modello
                messaggi_da_mostrare=-2 if messaggio_di_sistema.strip()=="" else -3
                mostra_cronologia_chat(provider.get_cronologia_messaggi()[messaggi_da_mostrare:])
            except Exception as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                with st.chat_message("assistant"):
                    st.markdown(
                        f"<div style='color: red;'><strong>⚠️ Errore cronologia ({timestamp}):</strong> {str(e)}</div>",
                        unsafe_allow_html=True
                    )
else: # Provider non disponibile
    st.error(f"⚠️ Provider {provider_scelto} temporaneamente indisponibile. Verifica la connessione di rete o l'API_KEY inserita")
    if st.button("Riprova"):
        try:
            provider.lista_modelli()
            if provider.disponibile():
                st.toast("Provider disponibile", icon="✅")
            else:
                st.toast("Provider ancora non disponibile. Controlla API key o rete.", icon="⚠️")
        except Exception as e:
            st.error(f"Errore: {e}")