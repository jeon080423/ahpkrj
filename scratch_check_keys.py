import toml
import os

def main():
    secrets_path = ".streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        print("secrets.toml not found")
        return
    secrets = toml.load(secrets_path)
    print("Keys in secrets.toml:", list(secrets.keys()))
    if "gcp_service_account" in secrets:
        print("Keys in gcp_service_account:", list(secrets["gcp_service_account"].keys()))

if __name__ == "__main__":
    main()
