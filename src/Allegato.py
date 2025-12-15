# Classe usata solo per tornare gli allegati alla GUI
class Allegato():
    
    def __init__(self, tipo="", contenuto="", mime_type=""):
        self.tipo=tipo
        self.contenuto=contenuto
        self.mime_type=mime_type