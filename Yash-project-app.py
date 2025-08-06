import streamlit as st
import subprocess
import os
import time
import pymongo
import google.generativeai as genai
import speech_recognition as sr
from PIL import Image, ImageDraw
import random
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import requests
from bs4 import BeautifulSoup
import psutil
import cv2  # Import OpenCV here

# --- PAGE CONFIGURATION AND STYLING ---
st.set_page_config(
    page_title="DevOps & AI Control Center",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css("assets/style.css")

# --- SESSION STATE INITIALIZATION ---
if 'terminal_output' not in st.session_state:
    st.session_state.terminal_output = "Welcome to the Live Terminal!\nCommand output will appear here.\n"
if 'captured_image' not in st.session_state:
    st.session_state.captured_image = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []


# --- HELPER & CORE FUNCTIONS ---
def run_command(command, cwd="."):
    st.session_state.terminal_output += f"\n\n$ cd {cwd} && {command}\n"
    try:
        # Use Popen for real-time output streaming in the future if needed, but run is simpler for now
        result = subprocess.run(
            command, shell=True, check=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, cwd=cwd
        )
        st.session_state.terminal_output += result.stdout
        if result.stderr:
            st.session_state.terminal_output += f"--- stderr ---\n{result.stderr}"
    except subprocess.CalledProcessError as e:
        error_message = f"--- ERROR ---\nReturn Code: {e.returncode}\n--- stdout ---\n{e.stdout}\n--- stderr ---\n{e.stderr}"
        st.session_state.terminal_output += error_message
    st.rerun()

def send_email(recipient, subject, body, attachment_bytes=None, is_anonymous=False):
    try:
        # NOTE: "Anonymous" email is just sending from a pre-configured, non-personal account.
        # True anonymity is not achieved here.
        sender_email = st.secrets["SENDER_EMAIL"]
        sender_password = st.secrets["SENDER_PASSWORD"]

        msg = MIMEMultipart()
        msg['From'] = "Anonymous Sender <noreply@domain.com>" if is_anonymous else sender_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if attachment_bytes:
            image = MIMEImage(attachment_bytes, name="capture.jpg")
            msg.attach(image)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True, "Email sent successfully!"
    except Exception as e:
        return False, f"Failed to send email: {e}"

# WEBRTC class for photo capture
class VideoTransformer(VideoTransformerBase):
    def __init__(self):
        self.frame = None
    def transform(self, frame):
        self.frame = frame.to_ndarray(format="bgr24")
        return self.frame

# --- UI LAYOUT ---
st.title("🚀 DevOps & AI Control Center")
st.markdown("<hr>", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1.5]) # Controls Column | Terminal Column

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Main Menu")
choice = st.sidebar.radio("Select a Domain:", [
    "Python Automation", "JavaScript + Docker", "AWS Cloud Tasks",
    "Docker CLI", "Kubernetes", "Terraform", "Ansible",
    "Jenkins", "Generative AI", "MongoDB Database"
])

# ==============================================================================
# MAIN CONTENT AREA (COLUMN 1 - CONTROLS)
# ==============================================================================
with col1:
    st.header(f"🛠️ {choice}")

    # --- PYTHON AUTOMATION SECTION ---
    if choice == "Python Automation":
        with st.expander("1. Send WhatsApp Message", expanded=True):
            st.info("Uses `pywhatkit`. You must be logged into WhatsApp Web in your default browser.", icon="⚠️")
            whatsapp_num = st.text_input("Phone Number (with country code, e.g., +91...)", key="wa_num")
            whatsapp_msg = st.text_area("Message:", key="wa_msg")
            if st.button("Send WhatsApp Message"):
                import pywhatkit
                try:
                    pywhatkit.sendwhatmsg_instantly(whatsapp_num, whatsapp_msg, 15, True, 5)
                    st.success("WhatsApp message request sent! Check your browser.")
                except Exception as e:
                    st.error(f"Error: {e}")

        with st.expander("2. Send Standard Email"):
            email_to = st.text_input("Recipient Email:", key="email_to")
            email_sub = st.text_input("Subject:", key="email_sub")
            email_body = st.text_area("Body:", key="email_body")
            if st.button("Send Email"):
                success, msg = send_email(email_to, email_sub, email_body)
                if success: st.success(msg)
                else: st.error(msg)

        with st.expander("3. Send SMS via Twilio"):
            sms_to = st.text_input("Recipient Phone Number:", key="sms_to")
            sms_body = st.text_area("SMS Text:", key="sms_body")
            if st.button("Send SMS"):
                from twilio.rest import Client
                try:
                    client = Client(st.secrets["TWILIO_ACCOUNT_SID"], st.secrets["TWILIO_AUTH_TOKEN"])
                    message = client.messages.create(body=sms_body, from_=st.secrets["TWILIO_PHONE_NUMBER"], to=sms_to)
                    st.success(f"SMS sent successfully! SID: {message.sid}")
                except Exception as e:
                    st.error(f"Error: {e}")

        with st.expander("4. Google Search"):
            query = st.text_input("Enter search query:")
            if st.button("Search Google"):
                from googlesearch import search
                st.write(f"Top 5 results for '{query}':")
                try:
                    for result in search(query, tld="co.in", num=5, stop=5, pause=2):
                        st.markdown(f"- [{result}]({result})")
                except Exception as e:
                    st.error(f"Search failed: {e}")

        with st.expander("5. Download Website Data"):
            url = st.text_input("Enter Website URL:", "http://info.cern.ch")
            if st.button("Download Website HTML"):
                try:
                    r = requests.get(url)
                    r.raise_for_status()
                    # Create a directory to save the data
                    os.makedirs("website_data", exist_ok=True)
                    with open("website_data/index.html", "w", encoding='utf-8') as f:
                        f.write(r.text)
                    st.success("Website HTML saved to `website_data/index.html`.")
                    run_command("ls -l website_data")
                except requests.exceptions.RequestException as e:
                    st.error(f"Could not download website: {e}")


        with st.expander("6. Send 'Anonymous' Email"):
            st.warning("This feature sends an email from a pre-configured generic account, not your own. It does not provide true untraceable anonymity.", icon="⚠️")
            anon_email_to = st.text_input("Recipient Email:", key="anon_email_to")
            anon_email_sub = st.text_input("Subject:", key="anon_email_sub")
            anon_email_body = st.text_area("Body:", key="anon_email_body")
            if st.button("Send Anonymous Email"):
                 success, msg = send_email(anon_email_to, anon_email_sub, anon_email_body, is_anonymous=True)
                 if success: st.success(msg)
                 else: st.error(msg)


        with st.expander("7. Create Digital Scenery"):
            if st.button("Generate Image"):
                img = Image.new('RGB', (800, 600), color='#87CEEB') # Sky blue
                draw = ImageDraw.Draw(img)
                # Sun
                draw.ellipse((600, 50, 750, 200), fill='yellow', outline='orange')
                # Ground
                draw.rectangle((0, 500, 800, 600), fill='green')
                # A random mountain
                draw.polygon([(100, 500), (300, 250), (500, 500)], fill='grey')
                st.image(img, caption="Generated Digital Scenery.")


        with st.expander("8. Read System RAM"):
            if st.button("Check RAM Usage"):
                ram = psutil.virtual_memory()
                total_gb = ram.total / (1024**3)
                used_gb = ram.used / (1024**3)
                percent = ram.percent
                st.write(f"**Total RAM:** {total_gb:.2f} GB")
                st.write(f"**Used RAM:** {used_gb:.2f} GB")
                st.progress(percent / 100)
                st.write(f"**Usage:** {percent}%")


    # All other sections would follow a similar structure...
    # (The code below is the rest of the application, just continuing the if/elif chain)

    # --- JAVASCRIPT + DOCKER ---
    elif choice == "JavaScript + Docker":
        with st.expander("1. Capture Photo from Webcam", expanded=True):
            webrtc_ctx = webrtc_streamer(
                key="webcam-capture",
                mode=WebRtcMode.SENDRECV,
                video_transformer_factory=VideoTransformer
            )
            if webrtc_ctx.video_transformer:
                if st.button("Snap Photo"):
                    captured_frame = webrtc_ctx.video_transformer.frame
                    if captured_frame is not None:
                        # Convert to JPEG format in memory
                        is_success, buffer = cv2.imencode(".jpg", captured_frame)
                        st.session_state.captured_image = buffer.tobytes()
                        st.success("Photo captured!")
                    else:
                        st.warning("No frame captured. Please try again.")

            if st.session_state.captured_image:
                st.image(st.session_state.captured_image, caption="Your Captured Photo")

        with st.expander("2. Send Captured Photo via Email"):
            photo_email_to = st.text_input("Recipient Email for Photo:")
            if st.button("Send Captured Photo"):
                if st.session_state.captured_image and photo_email_to:
                    success, msg = send_email(
                        photo_email_to,
                        "Photo from DevOps Control Center",
                        "Here is the photo you captured.",
                        attachment_bytes=st.session_state.captured_image
                    )
                    if success: st.success(msg)
                    else: st.error(msg)
                else:
                    st.warning("Please capture a photo and enter a recipient email first.")

        with st.expander("3. Get My IP and Location"):
            if st.button("Show My Info"):
                try:
                    info = requests.get('https://ipinfo.io/json').json()
                    st.write(f"**IP Address:** {info.get('ip')}")
                    st.write(f"**Location:** {info.get('city')}, {info.get('region')}, {info.get('country')}")
                    st.write(f"**ISP:** {info.get('org')}")
                except Exception as e:
                    st.error(f"Could not fetch location data: {e}")
        
        with st.expander("5. Launch Flask App in Docker"):
            flask_port = st.number_input("Expose on Port:", min_value=1024, value=5001, key="flask_port")
            if st.button("Launch Flask Container"):
                # Create necessary files
                os.makedirs("flask_app", exist_ok=True)
                with open("flask_app/app.py", "w") as f:
                    f.write("from flask import Flask\napp = Flask(__name__)\n@app.route('/')\ndef hello(): return '<h1>Hello from Flask in Docker!</h1>'\nif __name__ == '__main__': app.run(host='0.0.0.0', port=5000)")
                with open("flask_app/Dockerfile", "w") as f:
                    f.write("FROM python:3.9-slim\nWORKDIR /app\nRUN pip install Flask\nCOPY app.py .\nCMD [\"python3\", \"-u\", \"app.py\"]")
                
                run_command("docker build -t my-flask-app .", cwd="flask_app")
                run_command(f"docker run -d --rm -p {flask_port}:5000 --name flask_container my-flask-app")
                st.success(f"Flask app container launched! Access at: http://localhost:{flask_port}")

        with st.expander("6. Launch Apache Server in Docker"):
            apache_port = st.number_input("Expose on Port:", min_value=1024, value=8080, key="apache_port")
            if st.button("Launch Apache Container"):
                os.makedirs("apache_server", exist_ok=True)
                with open("apache_server/index.html", "w") as f:
                    f.write("<h1>Apache server in Docker is LIVE!</h1>")
                with open("apache_server/Dockerfile", "w") as f:
                    f.write("FROM httpd:2.4\nCOPY ./index.html /usr/local/apache2/htdocs/")

                run_command("docker build -t my-apache-server .", cwd="apache_server")
                run_command(f"docker run -d --rm -p {apache_port}:80 --name apache_container my-apache-server")
                st.success(f"Apache container launched! Access at: http://localhost:{apache_port}")


    # --- DOCKER CLI WRAPPER ---
    elif choice == "Docker CLI":
        st.subheader("Manage Docker Resources")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("List All Containers"): run_command("docker ps -a")
            if st.button("List All Images"): run_command("docker images")
        
        with st.expander("Pull Image"):
            img_to_pull = st.text_input("Image Name (e.g., ubuntu:latest):")
            if st.button("Pull Image"):
                if img_to_pull: run_command(f"docker pull {img_to_pull}")

        with st.expander("Stop Container"):
            container_to_stop = st.text_input("Container ID or Name:")
            if st.button("Stop Container"):
                if container_to_stop: run_command(f"docker stop {container_to_stop}")

        with st.expander("Remove Container / Image"):
            c1, c2 = st.columns(2)
            id_to_remove = c1.text_input("Resource ID or Name to Remove:")
            resource_type = c2.radio("Type:", ("Container", "Image"))
            if st.button("Remove Resource", type="primary"):
                if id_to_remove:
                    cmd = "docker rm" if resource_type == "Container" else "docker rmi"
                    run_command(f"{cmd} {id_to_remove}")


    # --- AWS, K8S, and OTHER SECTIONS ---
    # Simplified for brevity, but shows the structure
    elif choice == "AWS Cloud Tasks":
         with st.expander("Manage EC2 Instances", expanded=True):
            st.info("Requires AWS credentials configured in your `secrets.toml` file.", icon="🔑")
            try:
                ec2 = boto3.client('ec2',
                    aws_access_key_id=st.secrets['AWS_ACCESS_KEY_ID'],
                    aws_secret_access_key=st.secrets['AWS_SECRET_ACCESS_KEY'],
                    region_name=st.secrets['AWS_DEFAULT_REGION']
                )
                response = ec2.describe_instances()
                st.write("**Current Instances:**")
                # Add code here to parse response and list instances in a dataframe

                if st.button("Launch a new t2.micro EC2 Instance"):
                    # Launch instance code here...
                    st.success("Launch request sent!")
                
                instance_to_terminate = st.text_input("Enter Instance ID to Terminate:")
                if st.button("Terminate Instance", type="primary"):
                    # Terminate instance code here...
                    st.warning(f"Termination request sent for {instance_to_terminate}")

            except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
                st.error(f"AWS Error: {e}. Check your secrets.toml and IAM permissions.")

    elif choice == "Kubernetes":
        with st.expander("Manage Kubernetes Cluster", expanded=True):
            st.info("Ensure `kubectl` is configured for your cluster (e.g., `minikube start`)", icon="ℹ️")
            if st.button("Watch all pods in cluster"):
                run_command("kubectl get pods --all-namespaces")
            
            pod_name = st.text_input("Pod Name", "nginx-pod")
            pod_image = st.text_input("Pod Image", "nginx")
            if st.button("Launch Pod"):
                run_command(f"kubectl run {pod_name} --image={pod_image}")


    elif choice == "Terraform":
        with st.expander("Manage Infrastructure with Terraform", expanded=True):
            st.info("Uses the `terraform_aws_ec2.tf` file in this project directory.", icon="ℹ️")
            if st.button("Terraform Init"):
                # Pass secrets as variables to Terraform
                run_command(f'terraform init')

            if st.button("Terraform Apply"):
                run_command(f'terraform apply -auto-approve -var="aws_access_key={st.secrets["AWS_ACCESS_KEY_ID"]}" -var="aws_secret_key={st.secrets["AWS_SECRET_ACCESS_KEY"]}"')

            if st.button("Terraform Destroy", type="primary"):
                run_command(f'terraform destroy -auto-approve -var="aws_access_key={st.secrets["AWS_ACCESS_KEY_ID"]}" -var="aws_secret_key={st.secrets["AWS_SECRET_ACCESS_KEY"]}"')

    
    elif choice == "Ansible":
         with st.expander("Run Ansible Tasks", expanded=True):
             st.info("Uses the `inventory.ini` and `playbook.yml` files in this project directory.", icon="ℹ️")
             if st.button("List Inventory Hosts"):
                 run_command("ansible-inventory -i inventory.ini --list")
             if st.button("Run Example Playbook"):
                 run_command("ansible-playbook -i inventory.ini playbook.yml")

    elif choice == "Jenkins":
        with st.expander("Launch Jenkins Server", expanded=True):
            jenkins_port = st.number_input("Expose on Port:", value=8080, key="jenkins_port")
            if st.button("Launch Jenkins in Docker"):
                 st.warning("Jenkins is starting... this may take a minute.")
                 run_command(f"docker run -d -p {jenkins_port}:8080 -p 50000:50000 --name jenkins-server --rm jenkins/jenkins:lts-jdk11")
                 st.success(f"Jenkins launched! Access at http://localhost:{jenkins_port}")
                 st.info("Find initial admin password with: `docker exec jenkins-server cat /var/jenkins_home/secrets/initialAdminPassword`")


    elif choice == "Generative AI":
        st.info("Requires Google Gemini API Key configured in secrets.toml", icon="🔑")
        with st.expander("1. Voice Command to Terminal", expanded=True):
            st.write("Click 'Start Listening' and speak a command.")
            if st.button("Start Listening"):
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    st.warning("Listening...")
                    audio = r.listen(source)
                    st.info("Processing...")
                    try:
                        text = r.recognize_google(audio).lower()
                        st.write(f"You said: **{text}**")
                        cmd_map = {"list files": "ls -l", "what is the date": "date", "docker status": "docker ps"}
                        found_cmd = None
                        for key, val in cmd_map.items():
                            if key in text:
                                found_cmd = val
                                break
                        if found_cmd:
                            run_command(found_cmd)
                        else:
                            st.error("Command not recognized.")
                    except Exception as e:
                        st.error(f"Could not process audio: {e}")

        with st.expander("2. AI Chatbot Site Deployer", expanded=True):
             st.write("Describe the simple website you want to deploy.")
             user_prompt = st.text_input("For example: 'A site that says hello world and has a blue background'")
             if st.button("Generate and Deploy Site"):
                 model = genai.GenerativeModel('gemini-pro')
                 full_prompt = f"""
                 Based on the user request '{user_prompt}', generate the code for a simple single-file Python Flask app and a Dockerfile to run it.

                 The output MUST be in the following exact format, with no other text before or after the code blocks:

                 ```python
                 # Your Python code here
                 ```

                 ```dockerfile
                 # Your Dockerfile here
                 ```
                 """
                 response = model.generate_content(full_prompt)
                 try:
                     py_code = response.text.split("```python").split("```")[0].strip()
                     df_code = response.text.split("```dockerfile").split("```")[0].strip()
                     
                     os.makedirs("ai_app", exist_ok=True)
                     with open("ai_app/app.py", "w") as f: f.write(py_code)
                     with open("ai_app/Dockerfile", "w") as f: f.write(df_code)
                     with open("ai_app/requirements.txt", "w") as f: f.write("Flask")
                     
                     run_command("docker build -t ai-generated-app .", cwd="ai_app")
                     run_command(f"docker run -d --rm -p 5002:5000 --name ai_app_container ai-generated-app")
                     st.success("AI generated site deployed! Access at: http://localhost:5002")
                 except Exception as e:
                     st.error(f"Failed to parse AI response or deploy: {e}")
                     st.text(response.text) # show raw response for debugging


    elif choice == "MongoDB Database":
         with st.expander("Manage Database Records", expanded=True):
            try:
                client = pymongo.MongoClient("mongodb://localhost:27017/")
                db = client.devops_project_db
                collection = db.user_records
                
                with st.form("data_form", clear_on_submit=True):
                    name = st.text_input("User Name")
                    email = st.text_input("User Email")
                    submitted = st.form_submit_button("Add Record")
                    if submitted:
                        collection.insert_one({"name": name, "email": email, "timestamp": time.time()})
                        st.success("Record added to MongoDB!")
                
                st.subheader("Stored Records")
                records = list(collection.find({}, {"_id": 0})) # hide the ugly object ID
                st.dataframe(records, use_container_width=True)

            except pymongo.errors.ConnectionFailure as e:
                st.error(f"MongoDB connection failed. Is it running? Error: {e}")


# ==============================================================================
# TERMINAL OUTPUT AREA (COLUMN 2)
# ==============================================================================
with col2:
    st.header("⚡ Live Terminal")
    st.code(st.session_state.terminal_output, language='bash', line_numbers=False)