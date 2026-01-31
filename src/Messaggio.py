from datetime import datetime

class Messaggio():
    def __init__(self, testo="", ruolo="", allegati=[], timestamp="", id=None):
        self._mappa_ruoli = {
            "assistant": "assistant",
            "tool": "assistant",
            "user": "user",
            "system": "system",
            "developer": "user",
            "ai": "ai"
        }    
        self._ruolo=""
        self._id=id
        self._allegati=allegati # i file allegati al messaggio
        self.set_testo(testo)
        self.set_ruolo(ruolo)
        self.set_timestamp(timestamp)
        
    def get_id(self):
        return self._id
    
    def set_id(self, id=None):
        self._id=id
        
    def get_testo(self):
        return self._testo
    
    def get_allegati(self):
        return self._allegati
    
    def set_allegati(self, allegati):
        self._allegati = allegati
        
    def add_allegato(self, allegato):
        self._allegati.append(allegato)
    
    def get_allegato_at(self, indice):
        return self._allegati[indice]
    
    def timestamp(self):
        return self._timestamp
    
    def set_timestamp(self, timestamp=""):
        self._timestamp=timestamp or datetime.now()
    
    def set_testo(self, testo=""):
        self._testo=testo
    
    def set_ruolo(self, ruolo):
        """
        Imposta il ruolo del messaggio.
        Se il ruolo non è presente nella mappa, assume 'user' di default.
        """
        if ruolo in self._mappa_ruoli.keys():
            self._ruolo=self._mappa_ruoli[ruolo]
        else:
            self._ruolo = "user"  # default se ruolo sconosciuto
    
    def get_ruolo(self):
        """
        Ritorna il ruolo convertito secondo la mappa (_mappa_ruoli).
        Serve per passare il ruolo direttamente a Streamlit.
        """
        return self._mappa_ruoli[self._ruolo]
    
    
    
    
    
        
    