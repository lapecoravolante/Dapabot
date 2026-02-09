import importlib, pkgutil, src.tools
from threading import Lock
from src.tools.Tool import Tool

class Loader():
    _caricamento_effettuato=False
    _moduli={}
    _mutex = Lock()
    
    @staticmethod
    def discover_tools():
        with Loader._mutex:
            # importa tutti i moduli del package providers
            if not Loader._caricamento_effettuato:
                for _, module_name, _ in pkgutil.iter_modules(src.tools.__path__):
                    if module_name in ("Tool"):
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
