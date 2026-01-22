import os
from dotenv import load_dotenv
from jira import JIRA
from jira.exceptions import JIRAError

load_dotenv()

server_url = os.getenv("SERVER")
token = os.getenv("TOKEN")

try:
    jira = JIRA(server=server_url, token_auth=token, )
    print(jira)
except JIRAError as err:
    print(f"Error connecting: {err}")
except Exception as err:
    print(f"Unknown error: {err}")
