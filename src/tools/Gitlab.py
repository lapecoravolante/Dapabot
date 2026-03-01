"""Tool per interagire con GitLab tramite LangChain Community."""

from typing import Any, Dict, List, Optional
from src.tools.Tool import Tool


class Gitlab(Tool):
    def __init__(self) -> None:
        super().__init__(
            nome="Gitlab",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "python-gitlab": "gitlab"
            },
            variabili_necessarie={
                "GITLAB_URL": "https://gitlab.com",
                "GITLAB_REPOSITORY": "",
                "GITLAB_PERSONAL_ACCESS_TOKEN": "",
                "GITLAB_BRANCH": "main",
                "GITLAB_BASE_BRANCH": "main"
            },
            parametri_iniziali={
                "selected_tools": [
                    "get_issues",
                    "get_issue",
                    "comment_on_issue",
                    "create_pull_request",
                    "create_file",
                    "read_file",
                    "update_file",
                    "delete_file"
                ]
            }
        )
        
        # Descrizioni per i parametri nella GUI
        self._param_descriptions = {
            "selected_tools": "Lista dei tool da abilitare (lasciare vuoto per usare i tool di default: get_issues, get_issue, comment_on_issue, create_pull_request, create_file, read_file, update_file, delete_file)"
        }
        
        # Opzioni disponibili per selected_tools
        self._param_options = {
            "selected_tools": [
                "get_issues",
                "get_issue",
                "comment_on_issue",
                "create_pull_request",
                "create_file",
                "read_file",
                "update_file",
                "delete_file",
                "create_branch",
                "list_branches_in_repo",
                "set_active_branch",
                "list_files_in_main_branch",
                "list_files_in_bot_branch",
                "list_files_from_directory"
            ]
        }

    def get_tool(self) -> List[Any]:
        """
        Ottiene i tool GitLab configurati.
        
        Returns:
            Lista di tool GitLab configurati
        """
        from langchain_community.agent_toolkits.gitlab.toolkit import GitLabToolkit
        from langchain_community.utilities.gitlab import GitLabAPIWrapper
        
        # Crea il wrapper GitLab (usa le variabili d'ambiente impostate in Tool)
        gitlab_wrapper = GitLabAPIWrapper()
        
        # Ottieni i tool selezionati dall'attributo dell'istanza
        selected_tools = self.selected_tools
        
        # Se selected_tools è None o vuoto, usa i tool di default
        if not selected_tools:
            selected_tools = [
                "get_issues",
                "get_issue",
                "comment_on_issue",
                "create_pull_request",
                "create_file",
                "read_file",
                "update_file",
                "delete_file"
            ]
        
        # Crea il toolkit con i tool selezionati
        toolkit = GitLabToolkit.from_gitlab_api_wrapper(
            gitlab_wrapper,
            included_tools=selected_tools
        )
        
        return toolkit.get_tools()