"""
Classe unificata per gestire tutta la configurazione dell'applicazione
tramite il database SQLite config.db con modelli Peewee.

Sostituisce le vecchie classi:
- Configurazione (config.json)
- StoricoChat (storico_chat.db)
- DBAgent (agent.db)
"""

import json
import base64
from datetime import datetime
from src.Messaggio import Messaggio
from src.Allegato import Allegato
from src.models import (
    db, BaseModel, ProviderModel, ConfigurazioneRagModel,
    ModelloModel, ChatModel, MessaggioModel, AllegatoModel,
    MessaggioInChatModel, ToolModel, MCPServerModel
)


class ConfigurazioneDB:
    """
    Classe unificata per gestire la configurazione dell'applicazione.
    Gestisce provider, RAG, cronologia chat, allegati e tools.
    """
    
    @classmethod
    def inizializza_db(cls):
        """Inizializza il database creando tutte le tabelle"""
        db.connect(reuse_if_open=True)
        BaseModel.create_tables()
    
    @classmethod
    def chiudi_db(cls):
        """Chiude la connessione al database"""
        if not db.is_closed():
            db.close()
    
    # ==================== GESTIONE PROVIDER ====================
    
    @classmethod
    def salva_provider(cls, nome: str, base_url: str, api_key: str,
                       modello: str | None = None,
                       rag_config: dict | None = None) -> ProviderModel:
        """
        Salva o aggiorna la configurazione di un provider.
        
        Args:
            nome: Nome del provider
            base_url: URL base del provider
            api_key: API key del provider
            modello: Modello corrente selezionato
            rag_config: Configurazione RAG (dict con chiavi: attivo, modello, top_k, directory_allegati, modalita_ricerca)
        
        Returns:
            Istanza di ProviderModel salvata
        """
        cls.inizializza_db()
        
        provider, created = ProviderModel.get_or_create(
            nome=nome,
            defaults={
                'base_url': base_url,
                'api_key': api_key,
                'modello_corrente': modello
            }
        )
        
        if not created:
            provider.base_url = base_url
            provider.api_key = api_key
            provider.modello_corrente = modello
            provider.save()
        
        # Salva configurazione RAG se fornita
        if rag_config:
            cls.salva_configurazione_rag(nome, rag_config)
        
        return provider
    
    @classmethod
    def carica_provider(cls, nome: str) -> dict | None:
        """
        Carica la configurazione di un provider.
        
        Returns:
            Dizionario con la configurazione o None se non esiste
        """
        cls.inizializza_db()
        
        try:
            provider = ProviderModel.get(ProviderModel.nome == nome)
            config = provider.to_dict()
            
            # Aggiungi configurazione RAG
            rag = cls.carica_configurazione_rag(nome)
            config['rag'] = rag if rag else {
                'attivo': False,
                'modello': None,
                'top_k': 5,
                'directory_allegati': 'uploads',
                'modalita_ricerca': 'similarity'
            }
            
            return config
        except ProviderModel.DoesNotExist:
            return None
    
    @classmethod
    def carica_tutti_provider(cls) -> list[dict]:
        """
        Carica tutti i provider configurati.
        
        Returns:
            Lista di dizionari con le configurazioni
        """
        cls.inizializza_db()
        
        providers = []
        for provider in ProviderModel.select():
            config = provider.to_dict()
            rag = cls.carica_configurazione_rag(provider.nome)
            config['rag'] = rag if rag else {
                'attivo': False,
                'modello': None,
                'top_k': 5,
                'directory_allegati': 'uploads',
                'modalita_ricerca': 'similarity'
            }
            providers.append(config)
        
        return providers
    
    @classmethod
    def elimina_provider(cls, nome: str):
        """Elimina un provider e tutte le sue configurazioni associate"""
        cls.inizializza_db()
        
        try:
            provider = ProviderModel.get(ProviderModel.nome == nome)
            provider.delete_instance(recursive=True)
        except ProviderModel.DoesNotExist:
            pass
    
    # ==================== GESTIONE RAG ====================
    
    @classmethod
    def salva_configurazione_rag(cls, provider_nome: str, config: dict):
        """
        Salva la configurazione RAG per un provider.
        
        Args:
            provider_nome: Nome del provider
            config: Dizionario con la configurazione RAG
        """
        cls.inizializza_db()
        
        # Elimina configurazione esistente
        ConfigurazioneRagModel.delete().where(
            ConfigurazioneRagModel.provider == provider_nome
        ).execute()
        
        # Crea nuova configurazione
        ConfigurazioneRagModel.create(
            provider=provider_nome,
            attivo=config.get('attivo', False),
            modello=config.get('modello'),
            top_k=config.get('top_k', 5),
            directory_allegati=config.get('directory_allegati', 'uploads'),
            modalita_ricerca=config.get('modalita_ricerca', 'similarity')
        )
    
    @classmethod
    def carica_configurazione_rag(cls, provider_nome: str) -> dict | None:
        """Carica la configurazione RAG di un provider"""
        cls.inizializza_db()
        
        try:
            rag = ConfigurazioneRagModel.get(
                ConfigurazioneRagModel.provider == provider_nome
            )
            return rag.to_dict()
        except ConfigurazioneRagModel.DoesNotExist:
            return None
    
    # ==================== GESTIONE MODELLI ====================
    
    @classmethod
    def salva_modello(cls, modello_id: str, provider_nome: str):
        """Salva un modello disponibile per un provider"""
        cls.inizializza_db()
        
        ModelloModel.get_or_create(
            id=modello_id,
            defaults={'provider': provider_nome}
        )
    
    @classmethod
    def carica_modelli(cls, provider_nome: str) -> list[str]:
        """Carica tutti i modelli disponibili per un provider"""
        cls.inizializza_db()
        
        modelli = ModelloModel.select().where(
            ModelloModel.provider == provider_nome
        )
        return [m.id for m in modelli]
    
    # ==================== GESTIONE CRONOLOGIA CHAT ====================
    
    @classmethod
    def salva_chat(cls, provider: str, modello: str, cronologia: list[Messaggio]):
        """
        Salva la cronologia di una chat.
        
        Args:
            provider: Nome del provider
            modello: ID del modello
            cronologia: Lista di oggetti Messaggio
        """
        cls.inizializza_db()
        
        # Assicurati che provider e modello esistano
        ProviderModel.get_or_create(nome=provider, defaults={
            'base_url': '',
            'api_key': ''
        })
        ModelloModel.get_or_create(id=modello, defaults={'provider': provider})
        
        # Ottieni o crea la chat
        chat, _ = ChatModel.get_or_create(
            provider=provider,
            modello=modello
        )
        
        # Elimina i messaggi esistenti per questa chat
        MessaggioInChatModel.delete().where(
            MessaggioInChatModel.chat == chat
        ).execute()
        
        # Salva i nuovi messaggi
        for mess in cronologia:
            msg_id = mess.get_id()
            ruolo = mess.get_ruolo()
            testo = mess.get_testo()
            timestamp = mess.timestamp()
            
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            # Salva il messaggio
            MessaggioModel.insert(
                id=msg_id,
                timestamp=timestamp,
                ruolo=ruolo,
                contenuto=testo
            ).on_conflict_ignore().execute()
            
            # Collega il messaggio alla chat
            MessaggioInChatModel.create(
                chat=chat,
                messaggio_id=msg_id,
                messaggio_timestamp=timestamp
            )
            
            # Elimina gli allegati esistenti per questo messaggio
            AllegatoModel.delete().where(
                (AllegatoModel.messaggio_id == msg_id) &
                (AllegatoModel.messaggio_timestamp == timestamp)
            ).execute()
            
            # Salva i nuovi allegati
            for idx, allegato in enumerate(mess.get_allegati()):
                contenuto = allegato.contenuto
                tipo = allegato.tipo
                
                # Il contenuto è già nel formato corretto:
                # - base64 string per file binari (image, video, audio, file)
                # - testo plain per file di testo
                # Non serve ricodificare
                
                AllegatoModel.create(
                    id=f"{msg_id}-{idx}",  # Usa indice invece di timestamp
                    messaggio_id=msg_id,
                    messaggio_timestamp=timestamp,
                    tipo=tipo,
                    mime_type=allegato.mime_type,
                    contenuto=contenuto,
                    filename=allegato.filename
                )
    
    @classmethod
    def carica_cronologia(cls, provider: str, modello: str) -> list[Messaggio]:
        """
        Carica la cronologia di una chat.
        
        Returns:
            Lista di oggetti Messaggio
        """
        cls.inizializza_db()
        
        try:
            chat = ChatModel.get(
                (ChatModel.provider == provider) &
                (ChatModel.modello == modello)
            )
        except ChatModel.DoesNotExist:
            return []
        
        # Carica i messaggi ordinati per timestamp
        messaggi_in_chat = (MessaggioInChatModel
                           .select()
                           .where(MessaggioInChatModel.chat == chat)
                           .order_by(MessaggioInChatModel.messaggio_timestamp))
        
        messaggi = []
        for mic in messaggi_in_chat:
            # Carica il messaggio
            msg = MessaggioModel.get(
                (MessaggioModel.id == mic.messaggio_id) &
                (MessaggioModel.timestamp == mic.messaggio_timestamp)
            )
            
            # Carica gli allegati
            allegati_db = AllegatoModel.select().where(
                (AllegatoModel.messaggio_id == msg.id) &
                (AllegatoModel.messaggio_timestamp == msg.timestamp)
            )
            
            allegati = []
            for a in allegati_db:
                contenuto = a.contenuto
                tipo = a.tipo
                
                # Il contenuto è già in formato corretto dal DB:
                # - base64 string per file binari (image, video, audio, file)
                # - testo plain per file di testo
                # Non decodificare, mantieni il formato originale
                
                allegati.append(Allegato(
                    tipo=tipo,
                    contenuto=contenuto,
                    mime_type=a.mime_type,
                    filename=a.filename
                ))
            
            messaggi.append(Messaggio(
                testo=msg.contenuto,
                ruolo=msg.ruolo,
                allegati=allegati,
                timestamp=msg.timestamp,  # Passa datetime direttamente, non la stringa ISO
                id=msg.id
            ))
        
        return messaggi
    
    @classmethod
    def cancella_chat(cls, provider: str, modello: str):
        """Cancella la cronologia di una chat"""
        cls.inizializza_db()
        
        try:
            chat = ChatModel.get(
                (ChatModel.provider == provider) &
                (ChatModel.modello == modello)
            )
            chat.delete_instance(recursive=True)
        except ChatModel.DoesNotExist:
            pass
    
    @classmethod
    def ritorna_chat_recenti(cls) -> list[tuple]:
        """
        Ritorna la lista delle chat recenti.
        
        Returns:
            Lista di tuple (provider, modello)
        """
        cls.inizializza_db()
        
        chats = ChatModel.select().order_by(ChatModel.provider, ChatModel.modello)
        return [(chat.provider.nome, chat.modello.id) for chat in chats]
    
    # ==================== GESTIONE TOOLS ====================
    
    @classmethod
    def salva_tool(cls, nome_tool: str, configurazione: dict, attivo: bool = True):
        """
        Salva o aggiorna la configurazione di un tool.
        
        Args:
            nome_tool: Nome del tool
            configurazione: Dizionario con la configurazione
            attivo: Se il tool è attivo o meno
        """
        cls.inizializza_db()
        
        tool, created = ToolModel.get_or_create(
            nome_tool=nome_tool,
            defaults={
                'configurazione': json.dumps(configurazione, ensure_ascii=False),
                'attivo': attivo
            }
        )
        
        if not created:
            tool.set_configurazione(configurazione)
            tool.attivo = attivo
            tool.save()
    
    @classmethod
    def carica_tools(cls) -> list[dict]:
        """Carica tutti i tools configurati"""
        cls.inizializza_db()
        
        return [tool.to_dict() for tool in ToolModel.select()]
    
    @classmethod
    def carica_tools_attivi(cls) -> list[dict]:
        """Carica solo i tools attivi"""
        cls.inizializza_db()
        
        tools = ToolModel.select().where(ToolModel.attivo == True)
        return [{'nome_tool': t.nome_tool, 'configurazione': t.get_configurazione()} 
                for t in tools]
    
    @classmethod
    def aggiorna_stato_tool(cls, nome_tool: str, attivo: bool):
        """Aggiorna lo stato attivo/inattivo di un tool"""
        cls.inizializza_db()
        
        try:
            tool = ToolModel.get(ToolModel.nome_tool == nome_tool)
            tool.attivo = attivo
            tool.save()
        except ToolModel.DoesNotExist:
            pass
    
    @classmethod
    def aggiorna_stati_tools(cls, tools_attivi: list[str]):
        """
        Aggiorna lo stato di tutti i tools.
        I tools nella lista vengono attivati, gli altri disattivati.
        """
        cls.inizializza_db()
        
        # Disattiva tutti
        ToolModel.update(attivo=False).execute()
        
        # Attiva quelli nella lista
        if tools_attivi:
            for tool_name in tools_attivi:
                tool, created = ToolModel.get_or_create(
                    nome_tool=tool_name,
                    defaults={
                        'configurazione': json.dumps({}),
                        'attivo': True
                    }
                )
                if not created:
                    tool.attivo = True
                    tool.save()
    
    @classmethod
    def cancella_tool(cls, nome_tool: str):
        """Cancella un tool"""
        cls.inizializza_db()
        
        try:
            tool = ToolModel.get(ToolModel.nome_tool == nome_tool)
            tool.delete_instance()
        except ToolModel.DoesNotExist:
            pass
    
    @classmethod
    def elimina_tutti_tools(cls):
        """Elimina tutti i tools dalla tabella tool"""
        cls.inizializza_db()
        ToolModel.delete().execute()
    
    # ==================== GESTIONE SERVER MCP ====================
    
    @classmethod
    def salva_mcp_server(cls, nome: str, tipo: str, descrizione: str = "",
                         configurazione: dict = None, attivo: bool = True):
        """
        Salva o aggiorna la configurazione di un server MCP.
        
        Args:
            nome: Nome identificativo del server
            tipo: Tipo di server ('local' o 'remote')
            descrizione: Descrizione del server
            configurazione: Dizionario con la configurazione specifica
            attivo: Se il server è attivo o meno
        """
        cls.inizializza_db()
        
        server, created = MCPServerModel.get_or_create(
            nome=nome,
            defaults={
                'tipo': tipo,
                'descrizione': descrizione,
                'configurazione': json.dumps(configurazione or {}, ensure_ascii=False),
                'attivo': attivo
            }
        )
        
        if not created:
            server.tipo = tipo
            server.descrizione = descrizione
            server.set_configurazione(configurazione or {})
            server.attivo = attivo
            server.save()
    
    @classmethod
    def carica_mcp_servers(cls) -> list[dict]:
        """Carica tutti i server MCP configurati"""
        cls.inizializza_db()
        
        return [server.to_dict() for server in MCPServerModel.select()]
    
    @classmethod
    def carica_mcp_servers_attivi(cls) -> list[dict]:
        """Carica solo i server MCP attivi"""
        cls.inizializza_db()
        
        servers = MCPServerModel.select().where(MCPServerModel.attivo == True)
        return [server.to_dict() for server in servers]
    
    @classmethod
    def carica_mcp_server(cls, nome: str) -> dict | None:
        """
        Carica la configurazione di un server MCP specifico.
        
        Returns:
            Dizionario con la configurazione o None se non esiste
        """
        cls.inizializza_db()
        
        try:
            server = MCPServerModel.get(MCPServerModel.nome == nome)
            return server.to_dict()
        except MCPServerModel.DoesNotExist:
            return None
    
    @classmethod
    def aggiorna_stato_mcp_server(cls, nome: str, attivo: bool):
        """Aggiorna lo stato attivo/inattivo di un server MCP"""
        cls.inizializza_db()
        
        try:
            server = MCPServerModel.get(MCPServerModel.nome == nome)
            server.attivo = attivo
            server.save()
        except MCPServerModel.DoesNotExist:
            pass
    
    @classmethod
    def cancella_mcp_server(cls, nome: str):
        """Cancella un server MCP"""
        cls.inizializza_db()
        
        try:
            server = MCPServerModel.get(MCPServerModel.nome == nome)
            server.delete_instance()
        except MCPServerModel.DoesNotExist:
            pass
    
    @classmethod
    def aggiorna_stati_mcp_servers(cls, servers_attivi: list[str]):
        """
        Aggiorna lo stato di tutti i server MCP.
        I server nella lista vengono attivati, gli altri disattivati.
        """
        cls.inizializza_db()
        
        # Disattiva tutti
        MCPServerModel.update(attivo=False).execute()
        
        # Attiva quelli nella lista
        if servers_attivi:
            for server_name in servers_attivi:
                try:
                    server = MCPServerModel.get(MCPServerModel.nome == server_name)
                    server.attivo = True
                    server.save()
                except MCPServerModel.DoesNotExist:
                    pass
    
    @classmethod
    def elimina_tutti_mcp_servers(cls):
        """Elimina tutti i server MCP dalla tabella"""
        cls.inizializza_db()
        MCPServerModel.delete().execute()
    
    @classmethod
    def elimina_tutte_chat(cls):
        """
        Elimina tutte le chat e i relativi messaggi e allegati.
        Preserva la configurazione dei provider e dei tools.
        """
        cls.inizializza_db()
        
        # Elimina in ordine per rispettare le foreign keys
        # 1. Elimina allegati
        AllegatoModel.delete().execute()
        
        # 2. Elimina relazioni messaggio-chat
        MessaggioInChatModel.delete().execute()
        
        # 3. Elimina messaggi
        MessaggioModel.delete().execute()
        
        # 4. Elimina chat
        ChatModel.delete().execute()
        
        # 5. Elimina modelli (opzionale, ma mantiene coerenza)
        ModelloModel.delete().execute()
    
    # ==================== UTILITY ====================
    
    @classmethod
    def esporta_chat_json(cls) -> str:
        """Esporta solo le chat (cronologia messaggi) in formato JSON"""
        cls.inizializza_db()
        
        data = {
            'export_date': datetime.now().isoformat(),
            'export_type': 'chat_only',
            'chats': []
        }
        
        # Esporta tutte le chat
        for provider, modello in cls.ritorna_chat_recenti():
            cronologia = cls.carica_cronologia(provider, modello)
            data['chats'].append({
                'provider': provider,
                'modello': modello,
                'messaggi': [
                    {
                        'id': m.get_id(),
                        'ruolo': m.get_ruolo(),
                        'testo': m.get_testo(),
                        'timestamp': m.timestamp().isoformat() if isinstance(m.timestamp(), datetime) else m.timestamp(),
                        'allegati': [
                            {
                                'tipo': a.tipo,
                                'mime_type': a.mime_type,
                                'filename': a.filename,
                                # Codifica bytes in Base64 per JSON
                                'contenuto': base64.b64encode(a.contenuto).decode('utf-8') if isinstance(a.contenuto, bytes) else a.contenuto
                            }
                            for a in m.get_allegati()
                        ]
                    }
                    for m in cronologia
                ]
            })
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    @classmethod
    def importa_chat_json(cls, json_data: str):
        """
        Importa le chat da un file JSON esportato.
        
        Args:
            json_data: Stringa JSON con i dati delle chat da importare
        """
        cls.inizializza_db()
        data = json.loads(json_data)
        
        for chat in data.get('chats', []):
            provider = chat['provider']
            modello = chat['modello']
            messaggi = []
            
            for msg_data in chat.get('messaggi', []):
                allegati = []
                for all_data in msg_data.get('allegati', []):
                    contenuto = all_data['contenuto']
                    tipo = all_data['tipo']
                    
                    # Il contenuto è già nel formato corretto dal JSON:
                    # - base64 string per file binari
                    # - testo plain per file di testo
                    # Non decodificare, mantieni il formato originale
                    
                    allegati.append(Allegato(
                        tipo=tipo,
                        contenuto=contenuto,
                        mime_type=all_data.get('mime_type'),
                        filename=all_data.get('filename')
                    ))
                
                messaggi.append(Messaggio(
                    testo=msg_data['testo'],
                    ruolo=msg_data['ruolo'],
                    allegati=allegati,
                    timestamp=msg_data['timestamp'],
                    id=msg_data['id']
                ))
            
            if messaggi:
                cls.salva_chat(provider, modello, messaggi)
    
    @classmethod
    def esporta_json(cls) -> str:
        """Esporta l'intero database in formato JSON"""
        cls.inizializza_db()
        
        data = {
            'export_date': datetime.now().isoformat(),
            'export_type': 'full_database',
            'providers': cls.carica_tutti_provider(),
            'tools': cls.carica_tools(),
            'chats': []
        }
        
        # Esporta tutte le chat
        for provider, modello in cls.ritorna_chat_recenti():
            cronologia = cls.carica_cronologia(provider, modello)
            data['chats'].append({
                'provider': provider,
                'modello': modello,
                'messaggi': [
                    {
                        'id': m.get_id(),
                        'ruolo': m.get_ruolo(),
                        'testo': m.get_testo(),
                        'timestamp': m.timestamp().isoformat() if isinstance(m.timestamp(), datetime) else m.timestamp(),
                        'allegati': [a.to_dict() for a in m.get_allegati()]
                    }
                    for m in cronologia
                ]
            })
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    @classmethod
    def elimina_db(cls):
        """Elimina tutte le tabelle dal database"""
        cls.inizializza_db()
        BaseModel.drop_tables()


# Made with Bob