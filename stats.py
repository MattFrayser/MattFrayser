import os
import requests
from lxml import etree

if not os.environ.get('ACCESS_TOKEN'):
    raise Exception('ACCESS_TOKEN environment variable is not set. Did you forget to add your GitHub token to repository secrets?')

HEADERS = {'Authorization': 'token ' + os.environ['ACCESS_TOKEN']}
USER_NAME = 'mattfrayser'

def get_repos():
    repos = []
    url = f'https://api.github.com/users/{USER_NAME}/repos?per_page=100&type=owner'
    while url:
        r = requests.get(url, headers=HEADERS)
        data = r.json()
        repos.extend(data)
        url = r.links.get('next', {}).get('url')
    return repos

def get_total_commits(repos):
    total_commits = 0
    for repo in repos:
        branch = repo['default_branch']
        commits_url = f"https://api.github.com/repos/{USER_NAME}/{repo['name']}/commits"
        params = {'author': USER_NAME, 'sha': branch}  # Remove per_page=1
        r = requests.get(commits_url, headers=HEADERS, params=params)
        
        if 'Link' in r.headers and 'last' in r.links:
            last_url = r.links['last']['url']
            last_page = int(last_url.split('page=')[1].split('&')[0])
            total_commits += last_page
        elif r.status_code == 200:
            total_commits += len(r.json())  # Now this will count all commits on the page
    return total_commits    
    
def get_total_loc(repos):
    loc_add = 0
    loc_del = 0
    for repo in repos:
        url = f"https://api.github.com/repos/{USER_NAME}/{repo['name']}/stats/code_frequency"
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 202:
            # GitHub is generating stats, skip for now
            continue
        if r.status_code == 200:
            stats = r.json()
            for week in stats:
                loc_add += week[1]
                loc_del += abs(week[2])
    return [loc_add, loc_del, loc_add - loc_del]

def update_svg(filename, commit_count, repo_count, loc_data):
    tree = etree.parse(filename)
    root = tree.getroot()
    def set_text(element_id, value):
        el = root.find(f".//*[@id='{element_id}']")
        if el is not None:
            el.text = f"{value:,}"
    set_text('commit_data', commit_count)
    set_text('repo_data', repo_count)
    set_text('loc_data', loc_data[2])
    set_text('loc_add', loc_data[0])
    set_text('loc_del', loc_data[1])
    tree.write(filename, encoding='utf-8', xml_declaration=True)

if __name__ == '__main__':
    repos = get_repos()
    repo_count = len(repos)
    commit_count = get_total_commits(repos)
    loc_data = get_total_loc(repos)
    update_svg('darkmode.svg', commit_count, repo_count, loc_data)
