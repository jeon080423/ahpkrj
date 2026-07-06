import urllib.request
import json
import base64

def make_github_request(url, method="GET", data=None, token=None):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AHP-Master-Deployer"
    }
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            err_json = json.loads(body)
        except:
            err_json = body
        return e.code, err_json
    except Exception as e:
        return 0, str(e)

def main():
    token_file = "github_token.txt"
    with open(token_file, "r") as f:
        token = f.read().strip()
        
    username = "jeon080423"
    repo_name = f"{username}.github.io"
    
    # 1. Check if repository exists
    check_url = f"https://api.github.com/repos/{username}/{repo_name}"
    print(f"Checking if repo {repo_name} exists...")
    code, res = make_github_request(check_url, token=token)
    
    repo_exists = False
    if code == 200:
        print("Repository exists!")
        repo_exists = True
    elif code == 404:
        print("Repository does not exist. Creating it...")
        create_url = "https://api.github.com/user/repos"
        create_data = {
            "name": repo_name,
            "description": "Root GitHub Pages site for jeon080423",
            "auto_init": True,
            "private": False
        }
        create_code, create_res = make_github_request(create_url, method="POST", data=create_data, token=token)
        if create_code == 201:
            print("Successfully created repository!")
            repo_exists = True
        else:
            print(f"Failed to create repository: {create_code} - {create_res}")
            return
    else:
        print(f"Error checking repository: {code} - {res}")
        return
        
    if repo_exists:
        # Create naver verification file
        file_path = "naver4dbbe2785d1e5eedb0bf3bda5df4fb1c.html"
        file_content = "naver-site-verification: naver4dbbe2785d1e5eedb0bf3bda5df4fb1c.html"
        content_b64 = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")
        
        file_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
        
        # Check if file already exists to get its sha
        print(f"Checking if {file_path} exists in repo...")
        f_code, f_res = make_github_request(file_url, token=token)
        sha = None
        if f_code == 200:
            sha = f_res.get("sha")
            print("File already exists. Updating it...")
        
        upload_data = {
            "message": "Add Naver Verification HTML file",
            "content": content_b64
        }
        if sha:
            upload_data["sha"] = sha
            
        up_code, up_res = make_github_request(file_url, method="PUT", data=upload_data, token=token)
        if up_code in [200, 201]:
            print(f"Successfully uploaded {file_path}!")
        else:
            print(f"Failed to upload {file_path}: {up_code} - {up_res}")
            
        # Create or update index.html to redirect to /AHPkr/ and include meta tag
        index_path = "index.html"
        index_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="naver-site-verification" content="9a238d4eb7b2f9a0ac63b4fe805376fbe4e7ab01" />
    <script>
        window.location.href = "/AHPkr/";
    </script>
</head>
<body>
    Redirecting to AHP Master...
</body>
</html>"""
        index_b64 = base64.b64encode(index_content.encode("utf-8")).decode("utf-8")
        index_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{index_path}"
        
        # Check if index.html exists
        print("Checking if index.html exists in repo...")
        idx_code, idx_res = make_github_request(index_url, token=token)
        idx_sha = None
        if idx_code == 200:
            idx_sha = idx_res.get("sha")
            print("index.html exists. Checking if it already redirects...")
            # We will overwrite it to make sure it has the verification and redirect
        
        upload_idx_data = {
            "message": "Configure root index.html with redirect and naver verification",
            "content": index_b64
        }
        if idx_sha:
            upload_idx_data["sha"] = idx_sha
            
        up_idx_code, up_idx_res = make_github_request(index_url, method="PUT", data=upload_idx_data, token=token)
        if up_idx_code in [200, 201]:
            print("Successfully updated root index.html!")
        else:
            print(f"Failed to update root index.html: {up_idx_code} - {up_idx_res}")

if __name__ == "__main__":
    main()
