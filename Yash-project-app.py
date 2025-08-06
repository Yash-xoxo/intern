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
import cv2  # OpenCV for image processing

# --- PAGE CONFIGURATION AND STYLING ---
st.set_page_config(
    page_title="DevOps & AI Control Center",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css("assets/style.css")

# --- SESSION STATE INITIALIZATION ---
if 'terminal_output' not in st.session_state:
    st.session_state.terminal_output = "Welcome to the Live Terminal!\nCommand output will appear here.\n"
if 'captured_image' not in st.session_state:
    st.session_state.captured_image = None

# --- HELPER & CORE FUNCTIONS ---
def run_command(command, cwd="."):
    """Executes a shell command and updates the terminal output in session state."""
    st.session_state.terminal_output += f"\n\n$ cd {cwd} && {command}\n"
    try:
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
    except Exception as general_error:
        st.session_state.terminal_output += f"An unexpected error occurred: {general_error}"
    st.rerun()

def send_email(recipient, subject, body, attachment_bytes=None):
    try:
        sender_email = st.secrets["SENDER_EMAIL"]
        sender_password = st.secrets["SENDER_PASSWORD"]

        msg = MIMEMultipart()
        msg['From'] = sender_email
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
st.title("DevOps & AI Control Center With Cloud Integration")
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
    st.header(f"{choice}")

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
                # FIXED: The `googlesearch-python` library now only accepts the query argument.
                # We will manually iterate and limit the results to 5.
                from googlesearch import search
                st.write(f"Top 5 results for '{query}':")
                try:
                    results = []
                    # Manually get the first 5 results from the generator
                    for j in search(query):
                        results.append(j)
                        if len(results) >= 5:
                            break
                    
                    if results:
                        for result in results:
                            st.markdown(f"- [{result}]({result})")
                    else:
                        st.warning("No results found.")

                except Exception as e:
                    # Catch potential HTTP errors if Google blocks the request
                    st.error(f"Search failed. This can happen if Google temporarily blocks requests. Please wait a bit. Error: {e}")
        
        with st.expander("5. Download Website Data"):
            url = st.text_input("Enter Website URL:", "http://info.cern.ch")
            if st.button("Download Website HTML"):
                try:
                    r = requests.get(url)
                    r.raise_for_status()
                    os.makedirs("website_data", exist_ok=True)
                    with open("website_data/index.html", "w", encoding='utf-8') as f:
                        f.write(r.text)
                    st.success("Website HTML saved to `website_data/index.html`.")
                    run_command("ls -l website_data")
                except requests.exceptions.RequestException as e:
                    st.error(f"Could not download website: {e}")
        
        with st.expander("7. Create Digital Scenery"):
            if st.button("Generate Image"):
                img = Image.new('RGB', (800, 600), color='#87CEEB')
                draw = ImageDraw.Draw(img)
                draw.rectangle((0, 500, 800, 600), fill='green')
                draw.ellipse((600, 50, 750, 200), fill='yellow', outline='orange')
                for _ in range(random.randint(2, 5)):
                    x1 = random.randint(-100, 700)
                    x2 = x1 + random.randint(200, 400)
                    y2 = random.randint(200, 400)
                    draw.polygon([(x1, 500), (x2, 500), ((x1+x2)//2, y2)], fill='grey')
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
    
    elif choice == "JavaScript + Docker":
        with st.expander("1. Capture Photo from Webcam", expanded=True):
            webrtc_ctx = webrtc_streamer(
                key="webcam-capture", mode=WebRtcMode.SENDRECV,
                video_transformer_factory=VideoTransformer
            )
            if webrtc_ctx.video_transformer and st.button("Snap Photo"):
                captured_frame = webrtc_ctx.video_transformer.frame
                if captured_frame is not None:
                    is_success, buffer = cv2.imencode(".jpg", captured_frame)
                    st.session_state.captured_image = buffer.tobytes()
                    st.success("Photo captured!")
            if st.session_state.captured_image:
                st.image(st.session_state.captured_image, caption="Your Captured Photo")

        with st.expander("2. Send Captured Photo via Email"):
            photo_email_to = st.text_input("Recipient Email for Photo:")
            if st.button("Send Captured Photo"):
                if st.session_state.captured_image and photo_email_to:
                    success, msg = send_email(photo_email_to, "Photo from DevOps Control Center", "Here is the photo you captured.", st.session_state.captured_image)
                    if success: st.success(msg)
                    else: st.error(msg)
                else:
                    st.warning("Please capture a photo and enter a recipient email first.")

        with st.expander("5. Launch Flask App in Docker"):
            flask_port = st.number_input("Expose on Port:", min_value=1024, value=5001, key="flask_port")
            if st.button("Launch Flask Container"):
                os.makedirs("flask_app", exist_ok=True)
                with open("flask_app/app.py", "w") as f:
                    f.write("from flask import Flask\napp = Flask(__name__)\n@app.route('/')\ndef hello(): return '<h1>Hello from Flask in Docker!</h1>'\nif __name__ == '__main__': app.run(host='0.0.0.0', port=5000)")
                with open("flask_app/Dockerfile", "w") as f:
                    f.write("FROM python:3.9-slim\nWORKDIR /app\nRUN pip install Flask\nCOPY app.py .\nCMD [\"python3\", \"-u\", \"app.py\"]")
                run_command("docker build -t my-flask-app .", cwd="flask_app")
                run_command(f"docker run -d --rm -p {flask_port}:5000 --name flask_container my-flask-app")
                st.success(f"Flask app container launched! Access at: http://localhost:{flask_port}")

        with st.expander("6. Launch Apache Server in Docker"):
            apache_port = st.number_input("Expose on Port:", min_value=1024, value=8081, key="apache_port")
            if st.button("Launch Apache Container"):
                os.makedirs("apache_server", exist_ok=True)
                with open("apache_server/index.html", "w") as f: f.write("<h1>Apache server in Docker is LIVE!</h1>")
                with open("apache_server/Dockerfile", "w") as f: f.write("FROM httpd:2.4\nCOPY ./index.html /usr/local/apache2/htdocs/")
                run_command("docker build -t my-apache-server .", cwd="apache_server")
                run_command(f"docker run -d --rm -p {apache_port}:80 --name apache_container my-apache-server")
                st.success(f"Apache container launched! Access at: http://localhost:{apache_port}")
                
    elif choice == "AWS Cloud Tasks":
         with st.expander("Manage EC2 Instances", expanded=True):
            st.info("Requires AWS credentials configured in your `secrets.toml` file.", icon="🔑")
            try:
                ec2 = boto3.client('ec2',
                    aws_access_key_id=st.secrets['AWS_ACCESS_KEY_ID'],
                    aws_secret_access_key=st.secrets['AWS_SECRET_ACCESS_KEY'],
                    region_name=st.secrets['AWS_DEFAULT_REGION']
                )
                if st.button("List EC2 Instances"):
                    run_command(f"aws ec2 describe-instances --region {st.secrets['AWS_DEFAULT_REGION']} --output table")

                if st.button("Launch a new t2.micro EC2 Instance"):
                    st.info("Sending launch request for a t2.micro with Amazon Linux 2 AMI...")
                    run_command(f"aws ec2 run-instances --image-id ami-0c55b159cbfafe1f0 --instance-type t2.micro --region {st.secrets['AWS_DEFAULT_REGION']}")
                
                instance_to_terminate = st.text_input("Enter Instance ID to Terminate:")
                if st.button("Terminate Instance", type="primary"):
                    if instance_to_terminate:
                        st.warning(f"Sending termination request for {instance_to_terminate}...")
                        run_command(f"aws ec2 terminate-instances --instance-ids {instance_to_terminate} --region {st.secrets['AWS_DEFAULT_REGION']}")
                    else:
                        st.error("Please provide an instance ID.")
            except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
                st.error(f"AWS Error: {e}. Check your secrets.toml and IAM permissions.")

    elif choice == "Docker CLI":
        st.subheader("Manage Docker Resources")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("List All Containers"): run_command("docker ps -a")
        with c2:
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
                run_command('terraform init')
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
                 st.info("The container is named 'jenkins-server'. Use the button below to get the password once it has started.")
        
        with st.expander("Get Jenkins Admin Password"):
            st.info("Click this ONLY after the Jenkins container is fully running.", icon="ℹ️")
            if st.button("Get Initial Password"):
                command = "docker exec jenkins-server cat /var/jenkins_home/secrets/initialAdminPassword"
                st.session_state.terminal_output += f"\n\n$ {command}\nAttempting to retrieve Jenkins admin password...\n"
                try:
                    result = subprocess.run(
                        command, shell=True, check=True, capture_output=True, text=True
                    )
                    st.success("Password retrieved! See terminal for details.")
                    st.code(result.stdout, language='text')
                    st.session_state.terminal_output += f"\n--- Jenkins Initial Admin Password ---\n{result.stdout}\n"
                except subprocess.CalledProcessError as e:
                    st.error("Failed to get password. Is the 'jenkins-server' container running and fully initialized?")
                    st.session_state.terminal_output += f"Error retrieving password: {e.stderr}\n"

    elif choice == "Generative AI":
        st.info("Requires Google Gemini API Key configured in secrets.toml", icon="🔑")
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        except Exception as e:
            st.error(f"Failed to configure Gemini AI. Check your secrets.toml file. Error: {e}")

        with st.expander("1. Voice Command to Terminal", expanded=True):
            st.write("Click 'Start Listening', speak a command like *'list all docker containers'* or *'what is today's date'*, and the AI will translate it to a shell command.")
            if st.button("Start Listening"):
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    st.warning("Listening... Speak clearly.")
                    try:
                        r.adjust_for_ambient_noise(source)
                        audio = r.listen(source, timeout=5, phrase_time_limit=10)
                        st.info("Audio captured. Translating with AI...")
                        recognized_text = r.recognize_google(audio).lower()
                        st.write(f"**You said:** *'{recognized_text}'*")
                        model = genai.GenerativeModel('gemini-1.5-flash-latest')
                        prompt = f"You are an expert AI that translates human language into a single, executable Linux shell command. Your response MUST be ONLY the shell command itself, with no explanation or formatting. If you cannot determine a clear and safe command, respond with the exact string 'ERROR:UNCLEAR'.\nUser's request: '{recognized_text}'\nYour command:"
                        response = model.generate_content(prompt)
                        command_from_ai = response.text.strip()
                        st.write(f"**AI translated command:** `{command_from_ai}`")
                        if "ERROR:UNCLEAR" in command_from_ai:
                            st.error("AI could not determine a safe or clear command from your speech.")
                        else:
                            run_command(command_from_ai)
                            st.success("AI-generated command executed.")
                    except sr.WaitTimeoutError: st.error("Listening timed out.")
                    except sr.UnknownValueError: st.error("Could not understand the audio.")
                    except Exception as e: st.error(f"An unexpected error occurred: {e}")

    elif choice == "MongoDB Database":
         with st.expander("Manage Database Records", expanded=True):
            try:
                client = pymongo.MongoClient("mongodb://localhost:27017/")
                db = client.devops_project_db
                collection = db.user_records
                with st.form("data_form", clear_on_submit=True):
                    name = st.text_input("User Name")
                    email = st.text_input("User Email")
                    if st.form_submit_button("Add Record"):
                        collection.insert_one({"name": name, "email": email, "timestamp": time.time()})
                        st.success("Record added to MongoDB!")
                st.subheader("Stored Records")
                records = list(collection.find({}, {"_id": 0}))
                st.dataframe(records, use_container_width=True)
            except pymongo.errors.ConnectionFailure as e:
                st.error(f"MongoDB connection failed. Is it running? Error: {e}")

# ==============================================================================
# TERMINAL OUTPUT AREA (COLUMN 2)
# ==============================================================================
with col2:
    c1, c2 = st.columns([3, 1])
    with c1:
        st.header("⚡ Live Terminal")
    with c2:
        if st.button("Clear 🗑️"):
            st.session_state.terminal_output = "Terminal cleared.\n"
            st.rerun()

    st.code(st.session_state.terminal_output, language='bash', line_numbers=False)
