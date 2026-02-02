import csv
from collections import OrderedDict
import os
import re
import sys
from dotenv import load_dotenv
from jira import JIRA


def get_app_dir() -> str:
    # If running as PyInstaller exe
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # If running as normal .py script
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()

load_dotenv(os.path.join(APP_DIR, ".env"))


TICKET_REGEX = re.compile(r"\b([A-Z]+-\d+)\b")


def extract_ticket_id(testcase_value: str) -> str | None:
    if not testcase_value:
        return None

    match = TICKET_REGEX.search(testcase_value)
    return match.group(1) if match else None


def extract_results_from_csv(csv_path: str) -> list[tuple[str, str]]:
    # Order preserved as in file
    results: OrderedDict[str, str] = OrderedDict()

    severity = {
        "failed": 2,
        "passed": 1,
        "": 0,
    }

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if "TestCase" not in reader.fieldnames or "TestCase Status" not in reader.fieldnames:
            raise ValueError(
                "CSV must contain columns: 'TestCase' and 'TestCase Status'\n"
                f"Found columns: {reader.fieldnames}"
            )

        for row in reader:
            ticket_id = extract_ticket_id(row.get("TestCase", ""))
            status = row.get("TestCase Status", "").strip().lower()

            if not ticket_id:
                continue

            # Keep the worst status if repeated
            if ticket_id not in results:
                results[ticket_id] = status
            else:
                old_status = results[ticket_id]
                if severity.get(status, 0) > severity.get(old_status, 0):
                    results[ticket_id] = status

    return list(results.items())


def find_first_csv_in_script_folder() -> str:
    csv_files = [f for f in os.listdir(APP_DIR) if f.lower().endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError(f"No .csv file found in: {APP_DIR}")

    return os.path.join(APP_DIR, csv_files[0])


def testmanagement_ticket_extractor():
    csv_file = find_first_csv_in_script_folder()
    tuples_list = extract_results_from_csv(csv_file)
    return tuples_list


def create_test_execution_issue(jira_client: JIRA, project_key: str, summary: str, testcases: list[str]) -> str:
    issue_dict = {
        "project": {"key": project_key},
        "summary": summary,
        "customfield_10415": testcases,
        "issuetype": {"name": "Test Execution"},
    }
    issue = jira_client.create_issue(fields=issue_dict)
    return issue.key


def main():
    server_url = os.getenv("SERVER")
    token = os.getenv("TOKEN")
    jira_project_key = os.getenv("PROJECT")
    jira = JIRA(server=server_url, token_auth=token, )
    test_results = testmanagement_ticket_extractor()
    test_keys = [t[0] for t in test_results]
    # Create Test Execution issue
    test_exec_key = create_test_execution_issue(
        jira,
        jira_project_key,
        "Automated Test Execution Creation",
        test_keys
    )
    print(f"Created Test Execution: {test_exec_key} with {len(test_keys)} tests. Tests added: {test_keys}")


if __name__ == "__main__":
    main()
