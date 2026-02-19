import importlib, pkgutil, src.tools
from src.tools.Tool import Tool

class Loader():
    _caricamento_effettuato=False
    _moduli={}
    
    @staticmethod
    def discover_tools():
        # importa tutti i moduli del package tools
        if not Loader._caricamento_effettuato:
            for _, module_name, _ in pkgutil.iter_modules(src.tools.__path__):
                # Escludi Tool (classe base), gui_tools (modulo GUI) e loader (questo modulo)
                if module_name in ("Tool", "gui_tools", "loader"):
                    continue
                importlib.import_module(f"{src.tools.__name__}.{module_name}")
            Loader._caricamento_effettuato=True
            # istanzia tutte le sottoclassi concrete
            for cls in Tool.__subclasses__():
                instance = cls()
                if not instance.get_nome() in Loader._moduli:
                    Loader._moduli[instance.get_nome()] = instance
                    instance.installa_pacchetti() # installa i pacchetti necessari per il tool
        return Loader._moduli
