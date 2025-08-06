# --- Update package list ---
sudo apt update

# --- Install Core Tools (Git, Python, Pip, Docker, Ansible) ---
sudo apt install -y git python3 python3-pip docker.io ansible curl software-properties-common gnupg

# --- Configure Docker to run without sudo ---
# This is a critical step for the app to control Docker
sudo usermod -aG docker $USER
# IMPORTANT: You MUST log out and log back in for this change to take effect.

# --- Install Terraform ---
wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update
sudo apt install -y terraform

# --- Install Kubernetes CLI (kubectl) ---
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# --- Install Minikube for local Kubernetes testing ---
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
rm minikube-linux-amd64

# --- Install MongoDB ---
sudo apt install -y mongodb
sudo systemctl start mongodb
sudo systemctl enable mongodb

# --- Install Dependencies for Speech Recognition ---
sudo apt install -y portaudio19-dev python3-pyaudio

pip install -r requirements.txt
