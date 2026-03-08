"""Tool per interagire con database SQL tramite LangChain."""

from typing import Any, Dict, List, Optional
from src.tools.Tool import Tool


class SqlDatabase(Tool):
    """
    Tool per interagire con database SQL standard.
    Utilizza SQLDatabase di LangChain per connettersi al database
    e SQLDatabaseToolkit per ottenere i tool di interazione.
    """
    
    def __init__(self) -> None:
        super().__init__(
            nome="SqlDatabase",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "sqlalchemy": "sqlalchemy",
                # Driver per SQLite (incluso in Python)
                # Driver per PostgreSQL (versione binaria precompilata)
                "psycopg2-binary": "psycopg2",
                # Driver per MySQL/MariaDB
                "pymysql": "pymysql",
                # Driver per Microsoft SQL Server
                "pyodbc": "pyodbc",
                # Driver per Oracle (nuovo nome di cx_Oracle)
                "oracledb": "oracledb"
            },
            parametri_iniziali={
                "database_uri": "sqlite:///example.db",
                "sample_rows_in_table_info": 3,
                "include_tables": [],
                "ignore_tables": [],
                "view_support": False,
                "max_string_length": 300,
                "indexes_in_table_info": False
            }
        )
        
        # Descrizioni per i parametri nella GUI
        self._param_descriptions = {
            "database_uri": "URI di connessione al database (es: sqlite:///example.db, postgresql://user:pass@localhost/dbname, mysql+pymysql://user:pass@localhost/dbname)",
            "sample_rows_in_table_info": "Numero di righe di esempio da mostrare nelle informazioni della tabella",
            "include_tables": "Lista di tabelle da includere (lasciare vuoto per includere tutte)",
            "ignore_tables": "Lista di tabelle da ignorare (lasciare vuoto per non ignorare nessuna)",
            "view_support": "Se True, include anche le viste del database",
            "max_string_length": "Lunghezza massima delle stringhe nei risultati",
            "indexes_in_table_info": "Se True, include le informazioni sugli indici nelle descrizioni delle tabelle"
        }
        
        # Memorizza l'istanza del database
        self._db_instance = None

    def get_tool(self) -> List[Any]:
        """
        Crea e ritorna i tool per interagire col database SQL.
        
        Returns:
            Lista di tool per interagire col database (sql_db_query, sql_db_schema, sql_db_list_tables)
        """
        from langchain_community.utilities import SQLDatabase
        from sqlalchemy import create_engine
        
        # Crea l'engine e il database usando SQLAlchemy direttamente
        # per avere più controllo sul tipo di database
        try:
            # Prova prima a creare l'engine
            engine = create_engine(self.database_uri)
            
            # Crea l'istanza SQLDatabase
            self._db_instance = SQLDatabase(
                engine=engine,
                sample_rows_in_table_info=self.sample_rows_in_table_info,
                include_tables=self.include_tables if self.include_tables else None,
                ignore_tables=self.ignore_tables if self.ignore_tables else None,
                view_support=self.view_support,
                max_string_length=self.max_string_length,
                indexes_in_table_info=self.indexes_in_table_info
            )
        except Exception as e:
            # Se fallisce, prova con il metodo from_uri
            self._db_instance = SQLDatabase.from_uri(
                self.database_uri,
                sample_rows_in_table_info=self.sample_rows_in_table_info,
                include_tables=self.include_tables if self.include_tables else None,
                ignore_tables=self.ignore_tables if self.ignore_tables else None,
                view_support=self.view_support,
                max_string_length=self.max_string_length,
                indexes_in_table_info=self.indexes_in_table_info
            )
        
        # Crea i tool manualmente (funziona con o senza LLM)
        return self._create_tools_without_llm()
    
    def _create_tools_without_llm(self) -> List[Any]:
        """
        Crea i tool per interagire col database senza LLM.
        
        Returns:
            Lista di tool (sql_db_list_tables, sql_db_schema, sql_db_query)
        """
        from langchain_core.tools import Tool
        
        tools = []
        
        # Tool: list_tables
        def list_tables(input_str: str = "") -> str:
            """Elenca tutte le tabelle disponibili nel database."""
            return ", ".join(self._db_instance.get_usable_table_names())
        
        tools.append(
            Tool(
                name="sql_db_list_tables",
                description="Input is an empty string, output is a comma-separated list of tables in the database.",
                func=list_tables
            )
        )
        
        # Tool: schema
        def get_schema(input_str: str = "") -> str:
            """Restituisce lo schema e le righe di esempio per le tabelle specificate."""
            tables = [t.strip() for t in input_str.split(",") if t.strip()]
            return self._db_instance.get_table_info(tables)
        
        tools.append(
            Tool(
                name="sql_db_schema",
                description="Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables. Be sure that the tables actually exist by calling sql_db_list_tables first! Example Input: table1, table2, table3",
                func=get_schema
            )
        )
        
        # Tool: query
        def run_query(input_str: str = "") -> str:
            """Esegue una query SQL e restituisce i risultati."""
            return self._db_instance.run(input_str)
        
        tools.append(
            Tool(
                name="sql_db_query",
                description="Input to this tool is a detailed and correct SQL query, output is a result from the database. If the query is not correct, an error message will be returned. If an error is returned, rewrite the query, check the query, and try again. If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields.",
                func=run_query
            )
        )
        
        return tools
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Ottiene informazioni sul database connesso.
        
        Returns:
            Dizionario con informazioni sul database
        """
        if self._db_instance is None:
            # Crea l'istanza se non esiste
            self.get_tool()
        
        return self._db_instance.get_context()
    
    def execute_query(self, query: str) -> str:
        """
        Esegue una query SQL direttamente.
        
        Args:
            query: Query SQL da eseguire
            
        Returns:
            Risultati della query come stringa
        """
        if self._db_instance is None:
            self.get_tool()
        
        return self._db_instance.run(query)
