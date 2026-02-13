"""
Modello per la configurazione dei provider
"""

from peewee import CharField
from .base import BaseModel


class ProviderModel(BaseModel):
    """
    Rappresenta un provider di modelli LLM (es. OpenRouter, HuggingFace)
    """
    nome = CharField(primary_key=True, max_length=100)
    base_url = CharField(max_length=500)
    api_key = CharField(max_length=500)
    modello_corrente = CharField(max_length=200, null=True)
    
    class Meta:
        table_name = 'provider'
    
    def to_dict(self):
        """Converte il modello in dizionario"""
        return {
            'nome': self.nome,
            'base_url': self.base_url,
            'api_key': self.api_key,
            'modello': self.modello_corrente,
        }

# Made with Bob
