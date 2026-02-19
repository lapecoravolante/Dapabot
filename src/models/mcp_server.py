"""
Modello per la configurazione dei server MCP
"""

from peewee import CharField, TextField, BooleanField
from .base import BaseModel
import json


class MCPServerModel(BaseModel):
    """
    Rappresenta la configurazione di un server MCP (locale o remoto)
    """
    nome = CharField(primary_key=True, max_length=100)
    tipo = CharField(max_length=20)  # 'local' o 'remote'
    descrizione = TextField(default='')
    configurazione = TextField()  # JSON serializzato con la configurazione specifica
    attivo = BooleanField(default=True)
    
    class Meta:
        table_name = 'mcp_server'
    
    def get_configurazione(self):
        """Deserializza la configurazione JSON"""
        return json.loads(self.configurazione) if self.configurazione else {}
    
    def set_configurazione(self, config_dict):
        """Serializza la configurazione in JSON"""
        self.configurazione = json.dumps(config_dict, ensure_ascii=False)
    
    def to_dict(self):
        """Converte il modello in dizionario"""
        return {
            'nome': self.nome,
            'tipo': self.tipo,
            'descrizione': self.descrizione,
            'configurazione': self.get_configurazione(),
            'attivo': self.attivo,
        }


# Made with Bob