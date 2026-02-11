from src.tools.Tool import Tool
from langchain_community.agent_toolkits.github.toolkit import GitHubToolkit
from langchain_community.utilities.github import GitHubAPIWrapper

class Github(Tool):

    def __init__(self) -> None:
        # I parametri iniziali vengono impostati dalla classe base come attributi dell'oggetto
        super().__init__(
            nome="Github",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "pygithub": "github"
            },
            variabili_necessarie={
                "LANGSMITH_API_KEY": "",
                "LANGSMITH_TRACING":"",
                "GITHUB_APP_ID":"",
                "GITHUB_APP_PRIVATE_KEY":"",
                "GITHUB_BRANCH":"",
                "GITHUB_BASE_BRANCH":""
            },
            parametri_iniziali= {"include_release_tools": False}
        )

    def get_tool(self):
        return GitHubToolkit.from_github_api_wrapper(
                github_api_wrapper=GitHubAPIWrapper(), 
                include_release_tools=self.include_release_tools
                ).get_tools()