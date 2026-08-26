import os
import subprocess
import json

def get_git_info():
    # 1. Commits
    cmd_commits = ['git', 'log', '-n', '50', '--pretty=format:%h|%an|%ad|%s', '--date=short']
    out_commits = subprocess.check_output(cmd_commits, encoding='utf-8', errors='ignore')
    commits = []
    for line in out_commits.strip().split('\n'):
        if line:
            parts = line.split('|', 3)
            if len(parts) == 4:
                msg = parts[3]
                tag = "other"
                if msg.startswith("fix"): tag = "fix"
                elif msg.startswith("feat"): tag = "feat"
                elif msg.startswith("refactor"): tag = "refactor"
                elif msg.startswith("style"): tag = "style"
                elif msg.startswith("arch"): tag = "arch"
                
                commits.append({
                    'hash': parts[0],
                    'author': parts[1],
                    'date': parts[2],
                    'msg': msg,
                    'tag': tag
                })
    
    # 2. Branch atual
    cmd_branch = ['git', 'branch', '--show-current']
    current_branch = subprocess.check_output(cmd_branch, encoding='utf-8').strip() or "master"

    # 3. Stats gerais
    cmd_stats = ['git', 'shortlog', '-sn', '--all']
    authors_summary = subprocess.check_output(cmd_stats, encoding='utf-8', errors='ignore').strip()

    return current_branch, commits, authors_summary

def generate_dashboard_html():
    branch, commits, authors = get_git_info()
    commits_json = json.dumps(commits, ensure_ascii=False)
    template_path = os.path.join(os.path.dirname(__file__), "dashboard_template.html")

    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
    else:
        template = "<html><body><h1>Lumenia Dashboard</h1></body></html>"

    html_content = (
        template
        .replace("{{branch}}", branch)
        .replace("{{commit_count}}", str(len(commits)))
        .replace("{{commits_json}}", commits_json)
    )

    output_path = "github_project_dashboard.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Dashboard interativo gerado com sucesso em: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    generate_dashboard_html()
