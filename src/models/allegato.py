"""
Modello per gli allegati ai messaggi
"""

from peewee import CharField, TextField, DateTimeField, CompositeKey
from .base import BaseModel


class AllegatoModel(BaseModel):
    """
    Rappresenta un allegato (file, immagine, ecc.) associato a un messaggio
    """
    id = CharField(primary_key=True, max_length=100)
    messaggio_id = CharField(max_length=100)
    messaggio_timestamp = DateTimeField()
    tipo = CharField(max_length=50)  # image, video, audio, text, file
    mime_type = CharField(max_length=100, null=True)
    contenuto = TextField()  # Base64 per binari, testo per text/plain
    filename = CharField(max_length=500, null=True)
    
    class Meta:
        table_name = 'allegato'
        indexes = (
            (('messaggio_id', 'messaggio_timestamp'), False),  # Indice per foreign key
        )

# Made with Bob
