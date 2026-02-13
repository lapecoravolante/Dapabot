"""
Modello per la configurazione dei tools per la modalità agentica
"""

from peewee import CharField, TextField, BooleanField
from .base import BaseModel
import json


class ToolModel(BaseModel):
    """
    Rappresenta la configurazione di un tool per la modalità agentica
    """
    nome_tool = CharField(primary_key=True, max_length=100)
    configurazione = TextField()  # JSON serializzato
    attivo = BooleanField(default=True)
    
    class Meta:
        table_name = 'tool'
    
    def get_configurazione(self):
        """Deserializza la configurazione JSON"""
        return json.loads(self.configurazione) if self.configurazione else {}
    
    def set_configurazione(self, config_dict):
        """Serializza la configurazione in JSON"""
        self.configurazione = json.dumps(config_dict, ensure_ascii=False)
    
    def to_dict(self):
        """Converte il modello in dizionario"""
        return {
            'nome_tool': self.nome_tool,
            'configurazione': self.get_configurazione(),
            'attivo': self.attivo,
        }

# Made with Bob
