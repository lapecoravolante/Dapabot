import importlib
import pkgutil
import src.providers
from src.providers.base import Provider
from threading import Lock

class Loader():
    _caricamento_effettuato=False
    _moduli={}
    _mutex = Lock()
    
    def discover_providers():
        with Loader._mutex:
            # importa tutti i moduli del package providers
            if not Loader._caricamento_effettuato:
                for _, module_name, _ in pkgutil.iter_modules(src.providers.__path__):
                    if module_name in ("base", "loader", "rag"):
                        continue
                    importlib.import_module(f"{src.providers.__name__}.{module_name}")
                Loader._caricamento_effettuato=True
                # istanzia tutte le sottoclassi concrete
                for cls in Provider.__subclasses__():
                    instance = cls()
                    if not instance.nome() in Loader._moduli:
                        Loader._moduli[instance.nome()] = instance
        return Loader._moduli
