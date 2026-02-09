from src.tools.Tool import Tool
from langchain_community.agent_toolkits.github.toolkit import GitHubToolkit
from langchain_community.utilities.github import GitHubAPIWrapper

class Github(Tool):

    def __init__(self) -> None:
        super().__init__(nome="Github", 
                        pacchetti_pytthon_necessari=["langchain-community", "pygithub"],
                        variabili_necessarie={
                            "LANGSMITH_API_KEY": "", 
                            "LANGSMITH_TRACING":"", 
                            "GITHUB_APP_ID":"", 
                            "GITHUB_APP_PRIVATE_KEY":"",
                            "GITHUB_BRANCH":"",
                            "GITHUB_BASE_BRANCH":""
                            }
                        )
        # Di seguito i parametri configurabili del tool
        self.include_release_tools = False

    def get_tool(self):
        return GitHubToolkit.from_github_api_wrapper(
                github_api_wrapper=GitHubAPIWrapper(), 
                include_release_tools=self.include_release_tools
                ).get_tools()