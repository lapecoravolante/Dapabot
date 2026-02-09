from abc import ABC, abstractmethod
import subprocess, os

class Tool(ABC):

    def __init__(self, nome="", variabili_necessarie=[], pacchetti_pytthon_necessari=[], configurazione={}) -> None:
        self._nome=""
        self._variabili_necessarie={} # dizionario delle variabili d'ambiente (e relativo valore) necessarie per il corretto funzionamentod del tool
        self._pacchetti_pytthon_necessari=[] # lista dei pacchetti python necessari per il corretto funzionamentod del tool
        self._configurazione = {} # la configurazione del tool in formato JSON
        self.installa_pacchetti()

    def installa_pacchetti(self) -> None:
        # installa i pacchetti python necessari per il corretto funzionamento del tool
        for pacchetto in self._pacchetti_pytthon_necessari:
            subprocess.run(["uv", "add", pacchetto])
            
    def set_nome(self, nome: str) -> None:
        self._nome = nome

    def get_nome(self) -> str:
        return self._nome

    def set_variabili_necessarie(self, variabili_necessarie: dict[str, str]) -> None:
        self._variabili_necessarie = variabili_necessarie
        for variabile, valore in self._variabili_necessarie:
            os.environ[variabile]=valore

    def get_variabili_necessarie(self) -> dict[str, str]:
        return self._variabili_necessarie

    def set_configurazione(self, configurazione: dict) -> None:
        self._configurazione = configurazione

    def set_pacchetti_pytthon_necessari(self, pacchetti_pytthon_necessari: list) -> None:
        self._pacchetti_pytthon_necessari = pacchetti_pytthon_necessari
        
    def get_pacchetti_pytthon_necessari(self) -> list:
        return self._pacchetti_pytthon_necessari

    # ritorna la configurazione per la GUI e per il DB
    def get_configurazione(self) -> dict:
        return self.__dict__

    # Nel caso di un toolkit, questo meotdo ritorna una lista con le istanze dei tools pronti all'uso e configurati con i parametri impostati dall' utente
    # Nel caso di un tool singolo, la lista contiene un solo elemento
    @abstractmethod
    def get_tool(self) -> list:
        pass