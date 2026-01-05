import streamlit as st
from streamlit_cookies_controller import CookieController

class SessionManager:
    
    _istanza = None
    _inizializzata = False
    cookie_controller = None
    
    def __new__(cls, *args, **kwargs):
        if cls._istanza is None:
            cls._istanza = super().__new__(cls)
        return cls._istanza
     
    def __init__(self, cookie_controller=None):
        # Evita di rieseguire l'inizializzazione
        if self.__class__._inizializzata:
            return
        self.cookie_controller=cookie_controller
        if not cookie_controller:
            self.cookie_controller=CookieController()
        self.__class__._inizializzata = True
        
    def salva_cookie(self, chiave, valore):
        self.cookie_controller.set(chiave, valore)

    # Inizializza una chiave dentro session_state se non esiste
    def bootstrap_key(self, key, default=None):
        if key not in st.session_state:
            st.session_state[key] = default

    # Sincronizza i cookie prendendo i valori dalla sessione
    def sync_cookie(self, key):
        if self.cookie_controller:
            # Verifica se il cookie esiste e usa set invece di sync
            value = st.session_state.get(key, None)
            if value is not None:
                self.cookie_controller.set(key, value)

    # metodo per il popolamento di una selectbox con i valori da sessione
    def selectbox(self, key, label, options, default=None):
        if isinstance(options, set):
            options = list(options)  # converte set in lista

        # Se la chiave non esiste, inizializzala con un valore di default 
        if key not in st.session_state:
            st.session_state[key] = default if default in options else (options[0] if options else None)

        # Mostra la selectbox
        value = st.selectbox(label, options, key=key)
        return value

    # metodo per il setting di un toggle con valore preso da sessione
    def toggle(self, key, label, default=False):
        # Se la chiave non esiste, inizializzala
        if key not in st.session_state:
            st.session_state[key] = default
        return st.toggle(label, key=key)

    # Number input sicuro
    def number_input(self, key, label, min_value=None, max_value=None, step=1, default=0):
        if key not in st.session_state:
            st.session_state[key] = default
        value = st.number_input(label, min_value=min_value, max_value=max_value, step=step, key=key)
        return value
