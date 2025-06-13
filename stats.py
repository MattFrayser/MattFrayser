import os
import requests
import time
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
        print(f"Processing repo: {repo['name']}")
        branch = repo['default_branch']
        commits_url = f"https://api.github.com/repos/{USER_NAME}/{repo['name']}/commits"
        
        # Start with page 1
        page = 1
        repo_commits = 0
        
        while True:
            params = {'author': USER_NAME, 'sha': branch, 'per_page': 100, 'page': page}
            r = requests.get(commits_url, headers=HEADERS, params=params)
            
            if r.status_code != 200:
                print(f"Failed to get commits for {repo['name']} (page {page}): {r.status_code}")
                break
                
            commits = r.json()
            if not commits:  # No more commits
                break
                
            repo_commits += len(commits)
            
            # less than 100 commits = last page
            if len(commits) < 100:
                break
                
            page += 1
        
        print(f"Found {repo_commits} commits in {repo['name']}")
        total_commits += repo_commits
    
    print(f"Total commits across all repos: {total_commits}")
    return total_commits    

def get_total_loc(repos):
    loc_add = 0
    loc_del = 0
    for repo in repos:
        url = f"https://api.github.com/repos/{USER_NAME}/{repo['name']}/stats/code_frequency"
        max_retries = 3
        for attempt in range(max_retries):
            r = requests.get(url, headers=HEADERS)
            
            if r.status_code == 200:
                stats = r.json()
                if stats:  # Make sure stats is not None or empty
                    repo_add = 0
                    repo_del = 0
                    for week in stats:
                        repo_add += week[1]
                        repo_del += abs(week[2])
                    
                    print(f"  {repo['name']}: +{repo_add:,} -{repo_del:,}")
                    loc_add += repo_add
                    loc_del += repo_del
                break
                
            elif r.status_code == 202:
                print(f"  {repo['name']}: Stats generating, waiting... (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait 2 seconds before retry
                else:
                    print(f"  {repo['name']}: Skipped after {max_retries} attempts")
            else:
                print(f"  {repo['name']}: Error {r.status_code}")
                break
        
        # Small delay between repos
        time.sleep(0.2)
    
    net_loc = loc_add - loc_del
    print(f"Total LOC: +{loc_add:,} -{loc_del:,} = {net_loc:,}")
    return [loc_add, loc_del, net_loc]

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
