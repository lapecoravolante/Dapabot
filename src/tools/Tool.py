from abc import ABC, abstractmethod
import subprocess, os
import importlib.util

class Tool(ABC):

    def __init__(self, nome="", variabili_necessarie=None, pacchetti_python_necessari=None, configurazione=None, parametri_iniziali=None) -> None:
        self._nome = nome
        self._variabili_necessarie = variabili_necessarie if variabili_necessarie is not None else {}
        self._pacchetti_python_necessari = pacchetti_python_necessari if pacchetti_python_necessari is not None else {}
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
        pacchetti_python_necessari può essere una lista o un dizionario {pacchetto: modulo}.
        """
        for pacchetto, module_name in self._pacchetti_python_necessari.items():
            # Verifica se il pacchetto è già installato provando a importarlo
            try:
                importlib.import_module(module_name)
                # Pacchetto già installato, salta l'installazione
            except ImportError:
                # Pacchetto non installato, procedi con l'installazione
                print(f"📦 Installazione pacchetto: {pacchetto}")
                subprocess.run(["uv", "pip", "install", pacchetto])
            
    def set_nome(self, nome: str) -> None:
        self._nome = nome

    def get_nome(self) -> str:
        return self._nome

    def set_variabili_necessarie(self, variabili_necessarie: dict[str, str]) -> None:
        self._variabili_necessarie = variabili_necessarie
        # Imposta le variabili d'ambiente in os.environ solo se hanno un valore
        for variabile, valore in self._variabili_necessarie.items():
            os.environ[variabile] = valore

    def get_variabili_necessarie(self) -> dict[str, str]:
        return self._variabili_necessarie

    def set_configurazione(self, configurazione: dict) -> None:
        self._configurazione = configurazione

    def set_pacchetti_python_necessari(self, pacchetti_python_necessari: dict) -> None:
        """Imposta i pacchetti necessari come dizionario {pacchetto: modulo}."""
        self._pacchetti_python_necessari = pacchetti_python_necessari
        
    def get_pacchetti_python_necessari(self) -> dict:
        """Ritorna il dizionario dei pacchetti necessari {pacchetto: modulo}."""
        return self._pacchetti_python_necessari

    # ritorna la configurazione per la GUI e per il DB
    def get_configurazione(self) -> dict:
        return self.__dict__

    # Nel caso di un toolkit, questo meotdo ritorna una lista con le istanze dei tools pronti all'uso e configurati con i parametri impostati dall' utente
    # Nel caso di un tool singolo, la lista contiene un solo elemento
    @abstractmethod
    def get_tool(self) -> list:
        pass