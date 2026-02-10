from abc import ABC, abstractmethod
import subprocess, os
import importlib.util

class Tool(ABC):

    def __init__(self, nome="", variabili_necessarie=None, pacchetti_pytthon_necessari=None, configurazione=None, parametri_iniziali=None) -> None:
        self._nome = nome
        self._variabili_necessarie = variabili_necessarie if variabili_necessarie is not None else {}
        self._pacchetti_pytthon_necessari = pacchetti_pytthon_necessari if pacchetti_pytthon_necessari is not None else []
        self._configurazione = configurazione if configurazione is not None else {}
        
        # Inizializza i parametri configurabili passati dalla sottoclasse
        # Questo permette di impostare i valori di default prima che get_configurazione() venga chiamato
        if parametri_iniziali:
            for nome_param, valore_default in parametri_iniziali.items():
                setattr(self, nome_param, valore_default)
        
        self.installa_pacchetti()

    def installa_pacchetti(self) -> None:
        """
        Installa i pacchetti python necessari per il corretto funzionamento del tool.
        Verifica prima se il pacchetto è già installato per evitare chiamate inutili a uv.
        """
        for pacchetto in self._pacchetti_pytthon_necessari:
            # Estrae il nome del modulo dal nome del pacchetto
            # Es: "langchain-community" -> "langchain_community"
            module_name = pacchetto.replace("-", "_")
            
            # Verifica se il pacchetto è già installato
            if importlib.util.find_spec(module_name) is None:
                # Pacchetto non installato, procedi con l'installazione
                print(f"📦 Installazione pacchetto: {pacchetto}")
                subprocess.run(["uv", "add", pacchetto])
            else:
                # Pacchetto già installato, salta l'installazione
                print(f"✅ Pacchetto già installato: {pacchetto}")
            
    def set_nome(self, nome: str) -> None:
        self._nome = nome

    def get_nome(self) -> str:
        return self._nome

    def set_variabili_necessarie(self, variabili_necessarie: dict[str, str]) -> None:
        self._variabili_necessarie = variabili_necessarie
        # Imposta le variabili d'ambiente in os.environ solo se hanno un valore
        for variabile, valore in self._variabili_necessarie.items():
            if valore:  # Solo se il valore non è vuoto
                os.environ[variabile] = valore

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