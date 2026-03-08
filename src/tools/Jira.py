"""Tool per interagire con Jira tramite LangChain."""

import os
from typing import Any
from src.tools.Tool import Tool

class Jira(Tool):
    """
    Tool per interagire con Atlassian Jira.
    Utilizza JiraToolkit di LangChain per le operazioni su Jira.
    """
    
    def __init__(self) -> None:
        super().__init__(
            nome="Jira",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "atlassian-python-api": "atlassian"
            },
            variabili_necessarie={
                "JIRA_API_TOKEN": "",
                "JIRA_USERNAME": "",
                "JIRA_INSTANCE_URL": ""
            },
            parametri_iniziali={
                "jira_cloud": True
            }
        )
        
        # Descrizioni per i parametri nella GUI
        self._param_descriptions = {
            "JIRA_API_TOKEN": "Token API di Jira (generato in Atlassian Account Settings)",
            "JIRA_USERNAME": "Username/email dell'account Jira",
            "JIRA_INSTANCE_URL": "URL dell'istanza Jira (es: https://tuodominio.atlassian.net)",
            "jira_cloud": "Usa Jira Cloud (attivo) o Jira Server/Data Center (disattivo)"
        }

    def get_tool(self) -> list[Any]:
        """
        Crea e ritorna i tool per interagire con Jira.
        Usa JiraToolkit di LangChain con patch per bug priority=None.
        
        Returns:
            Lista di tool Jira
        """
        from langchain_community.agent_toolkits.jira.toolkit import JiraToolkit
        from langchain_community.utilities.jira import JiraAPIWrapper
        
        # Leggi le credenziali dalle variabili d'ambiente
        api_token = os.environ.get('JIRA_API_TOKEN', '')
        username = os.environ.get('JIRA_USERNAME', '')
        instance_url = os.environ.get('JIRA_INSTANCE_URL', '')
        
        if not api_token or not username or not instance_url:
            raise ValueError("Credenziali Jira non configurate. Assicurati di aver impostato JIRA_API_TOKEN, JIRA_USERNAME e JIRA_INSTANCE_URL.")
        
        # Usa il parametro jira_cloud dall'istanza (configurabile via GUI come checkbox)
        is_cloud = getattr(self, 'jira_cloud', True)
        
        # Patch per il bug di LangChain: priority può essere None anche se la chiave esiste
        original_parse_issues = JiraAPIWrapper.parse_issues
        # Il codice originale di LangChain controlla solo se la chiave "priority" esiste
        # nel dizionario, ma non verifica se il valore è None. Quando tenta di accedere
        # a None["name"], causa l'errore "'NoneType' object is not subscriptable".
        # Per risolvere questo problema sostituiamo il tool originale con questa versione modificata
        def patched_parse_issues(self_wrapper, issues):
            """Versione patchata che gestisce priority=None correttamente."""
            parsed = []
            for issue in issues["issues"]:
                key = issue["key"]
                summary = issue["fields"]["summary"]
                created = issue["fields"]["created"][0:10]
                
                # FIX: Controlla che priority non sia None prima di accedere a ["name"]
                if "priority" in issue["fields"] and issue["fields"]["priority"] is not None:
                    priority = issue["fields"]["priority"]["name"]
                else:
                    priority = None
                
                status = issue["fields"]["status"]["name"]
                
                try:
                    assignee = issue["fields"]["assignee"]["displayName"]
                except Exception:
                    assignee = "None"
                
                rel_issues = {}
                for related_issue in issue["fields"].get("issuelinks", []):
                    if "inwardIssue" in related_issue.keys():
                        rel_type = related_issue["type"]["inward"]
                        rel_key = related_issue["inwardIssue"]["key"]
                        rel_summary = related_issue["inwardIssue"]["fields"]["summary"]
                    if "outwardIssue" in related_issue.keys():
                        rel_type = related_issue["type"]["outward"]
                        rel_key = related_issue["outwardIssue"]["key"]
                        rel_summary = related_issue["outwardIssue"]["fields"]["summary"]
                    rel_issues = {"type": rel_type, "key": rel_key, "summary": rel_summary}
                
                parsed.append(
                    {
                        "key": key,
                        "summary": summary,
                        "created": created,
                        "assignee": assignee,
                        "priority": priority,
                        "status": status,
                        "related_issues": rel_issues,
                    }
                )
            return parsed
        
        # Applica la patch
        JiraAPIWrapper.parse_issues = patched_parse_issues
        
        # Crea il wrapper e il toolkit
        jira_wrapper = JiraAPIWrapper(
            jira_username=username,
            jira_api_token=api_token,
            jira_instance_url=instance_url,
            jira_cloud=is_cloud
        )
        
        toolkit = JiraToolkit.from_jira_api_wrapper(jira_wrapper)
        
        # Ottieni i tool originali e aggiorna descrizioni
        tools = []
        for tool in toolkit.get_tools():
            if tool.name == "jql_query":
                tool.name = "jira_jql_query"
                tool.description = """Search Jira issues using JQL (Jira Query Language).

WARNING: You must provide a VALID JQL query, not a natural language phrase!

CORRECT QUERY EXAMPLES (copy these patterns exactly):
✓ project = KAN
✓ project = KAN AND status = "To Do"
✓ project = KAN ORDER BY created DESC
✓ assignee = currentUser()
✓ status IN ("To Do", "In Progress")

WRONG QUERY EXAMPLES (NEVER use these patterns):
✗ project all issues (WRONG - "all" is not a JQL operator)
✗ project = KAN LIMIT 10 (WRONG - LIMIT is not supported in JQL)
✗ show all issues (WRONG - not a JQL query)
✗ project KAN (WRONG - missing = operator)
✗ get all issues from KAN (WRONG - not JQL syntax)

MANDATORY RULES:
1. Use ONLY these operators: =, !=, <, >, <=, >=, ~, !~, IN, NOT IN, IS, IS NOT
2. NEVER use natural language words like "all", "show", "list", "get", "tutte", "mostra"
3. Project key must follow the = operator (e.g., project = KAN)
4. Strings with spaces need quotes: status = "To Do"
5. To sort: ORDER BY field ASC/DESC
6. To filter: use AND, OR, NOT

IMPORTANT: If you don't know the project key, call jira_get_projects first.
To get all issues from a project, simply use: project = KEY"""
            elif tool.name == "get_projects":
                tool.name = "jira_get_projects"
                tool.description = "Restituisce tutti i progetti Jira a cui l'utente ha accesso."
            elif tool.name == "create_issue":
                tool.name = "jira_create_issue"
                tool.description = "Crea una nuova issue Jira. Esempio: project=KAN, summary=Titolo, description=Descrizione."
            elif tool.name == "catch_all_jira_api":
                tool.name = "jira_other"
                tool.description = "Operazioni avanzate. Input deve essere JSON: {function: nome, args: [], kwargs: {}}. Non inventare nomi di funzioni."
            elif tool.name == "create_confluence_page":
                tool.name = "jira_create_confluence_page"
                tool.description = "Crea una pagina Confluence. Esempio: title=Titolo, space=SPACE, body=Contenuto."
            
            tools.append(tool)
        
        return tools
