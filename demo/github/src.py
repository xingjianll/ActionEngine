from github import Github, Auth

auth = Auth.Token("access_token")
g = Github(auth=auth)


rs = g.search_repositories("")
for r in rs:
