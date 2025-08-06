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
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import cv2
import html
from streamlit_option_menu import option_menu
import pywhatkit
from twilio.rest import Client
from googlesearch import search


# --- CONSTANTS ---
TERMINAL_WELCOME_MESSAGE = "Welcome to the Live Operations Terminal.\nSelect a task from the menu to begin.\nCommand output will appear here."

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="DevOps & AI Operations Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS INJECTION ---
def local_css(file_name):
    """Loads a local CSS file."""
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"Style file '{file_name}' not found. Please ensure it's in the same directory as the app.")

local_css("style.css")

# --- SESSION STATE INITIALIZATION ---
if 'terminal_output' not in st.session_state:
    st.session_state.terminal_output = TERMINAL_WELCOME_MESSAGE
if 'captured_image' not in st.session_state:
    st.session_state.captured_image = None
if 'listening' not in st.session_state:
    st.session_state.listening = False

# --- HELPER FUNCTIONS ---
def run_command(command, success_message="Command executed successfully."):
    """Executes a shell command with a spinner and updates the terminal output."""
    st.session_state.terminal_output += f"\n$ {command}\n"
    with st.spinner(f"Executing: {command}"):
        try:
            # Using Popen for better real-time feedback might be an advanced improvement
            result = subprocess.run(
                command, shell=True, check=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, timeout=300
            )
            st.session_state.terminal_output += result.stdout
            if result.stderr:
                st.session_state.terminal_output += f"stderr: {result.stderr}\n"
            st.toast(success_message, icon="✅")
        except subprocess.CalledProcessError as e:
            error_message = f"ERROR: Command failed with exit code {e.returncode}\n{e.stderr}"
            st.session_state.terminal_output += error_message
            st.error(error_message)
        except subprocess.TimeoutExpired:
            error_message = "ERROR: Command timed out after 5 minutes."
            st.session_state.terminal_output += error_message
            st.error(error_message)
        except Exception as e:
            error_message = f"An unexpected error occurred: {str(e)}"
            st.session_state.terminal_output += error_message
            st.error(error_message)
    # Trigger a rerun to update the terminal display immediately
    st.rerun()

def send_email_with_attachment(recipient_email, subject, body, image_bytes=None):
    """Sends an email, optionally with an image attachment, using credentials from secrets."""
    try:
        sender_email = st.secrets["SENDER_EMAIL"]
        sender_password = st.secrets["SENDER_PASSWORD"]

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if image_bytes:
            image = MIMEImage(image_bytes, name="captured_photo.jpg")
            msg.attach(image)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True, "Email sent successfully!"
    except Exception as e:
        return False, f"Failed to send email: {e}. Check your `secrets.toml` credentials and ensure 'less secure app access' is set up if not using an App Password."

# --- WEBRTC IMAGE CAPTURE CLASS ---
class VideoTransformer(VideoTransformerBase):
    def __init__(self):
        self.captured_frame = None

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        self.captured_frame = img
        return img

# --- UI LAYOUT ---
st.title("DevOps & AI Operations Platform")
st.caption("A professional showcase of modern IT automation and cloud engineering skills")

col1, col2 = st.columns([0.6, 0.4])

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("Operations Menu")
    menu_choice = option_menu(
        menu_title=None,
        options=[
            "Python Automation", "JS & Docker Tasks", "AWS Cloud", "Docker CLI",
            "Kubernetes", "Terraform", "Ansible", "Jenkins",
            "Generative AI", "MongoDB"
        ],
        icons=[
            "lightning-charge-fill", "box-seam-fill", "cloud-upload-fill", "hdd-stack-fill", "heptagon-fill",
            "stack", "robot", "gear-wide-connected", "chat-dots-fill", "database-fill-check"
        ],
        menu_icon="cast",
        default_index=0,
    )

# --- MAIN CONTROLS AREA (LEFT COLUMN) ---
with col1:
    st.header(menu_choice, divider='rainbow')

    if menu_choice == "Python Automation":
        with st.container(border=True):
            st.subheader("1. Send WhatsApp Message")
            st.info("Requires being logged into WhatsApp Web. A new browser tab will open.")
            whatsapp_num = st.text_input("Recipient Phone Number (+CountryCode)", "+91")
            whatsapp_msg = st.text_area("WhatsApp Message Content")
            if st.button("Send WhatsApp Message"):
                if whatsapp_num and whatsapp_msg:
                    try:
                        pywhatkit.sendwhatmsg_instantly(whatsapp_num, whatsapp_msg, 15, True, 5)
                        st.success("WhatsApp message request sent! Check your browser.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Please provide both phone number and message.")

        with st.container(border=True):
            st.subheader("2. Send Email")
            recipient_email = st.text_input("Recipient Email Address", key="email_recipient")
            email_subject = st.text_input("Subject", key="email_subject")
            email_body = st.text_area("Body", key="email_body")
            if st.button("Send Email"):
                with st.spinner("Sending email..."):
                    success, message = send_email_with_attachment(recipient_email, email_subject, email_body)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

        with st.container(border=True):
            st.subheader("3. Send SMS (via Twilio)")
            sms_num = st.text_input("Recipient Phone Number (+CountryCode)", key="sms_recipient")
            sms_msg = st.text_area("SMS Content")
            if st.button("Send SMS"):
                with st.spinner("Sending SMS..."):
                    try:
                        client = Client(st.secrets["TWILIO_ACCOUNT_SID"], st.secrets["TWILIO_AUTH_TOKEN"])
                        message = client.messages.create(body=sms_msg, from_=st.secrets["TWILIO_PHONE_NUMBER"], to=sms_num)
                        st.success(f"SMS sent successfully! SID: {message.sid}")
                    except Exception as e:
                        st.error(f"Error sending SMS: {e}. Check your Twilio credentials in secrets.toml.")
        
        with st.container(border=True):
            st.subheader("4. Google Search")
            search_query = st.text_input("Enter your search query")
            if st.button("Search Google"):
                st.write(f"Top 5 search results for '{search_query}':")
                try:
                    with st.spinner("Searching..."):
                        for j in search(search_query, num_results=5, lang="en"):
                            st.write(j)
                except Exception as e:
                    st.error(f"An error occurred during search: {e}")

                # --- FIX: Removed the tld="co.in" argument ---
                
                    

        with st.container(border=True):
            st.subheader("5. Generate Digital Scenery")
            if st.button("Generate Image"):
                with st.spinner("Creating scenery..."):
                    img = Image.new('RGB', (800, 600), color='skyblue')
                    d = ImageDraw.Draw(img)
                    d.rectangle([0, 450, 800, 600], fill='forestgreen') # Ground
                    d.ellipse([600, 50, 750, 200], fill='yellow') # Sun
                    for _ in range(random.randint(2, 4)):
                        x1, y1 = random.randint(0, 700), 450
                        x2, y2 = x1 + random.randint(100, 200), random.randint(150, 400)
                        x3, y3 = x2 + random.randint(100, 200), 450
                        d.polygon([(x1, y1), (x2, y2), (x3, y3)], fill='dimgray', outline='black')
                    st.image(img, caption="Generated Digital Scenery")


    elif menu_choice == "JS & Docker Tasks":
        with st.container(border=True):
            st.subheader("1. Webcam Photo Capture")
            webrtc_ctx = webrtc_streamer(key="webcam", video_transformer_factory=VideoTransformer,
                                         rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
            if webrtc_ctx.video_transformer:
                if st.button("Capture Photo"):
                    st.session_state.captured_image = webrtc_ctx.video_transformer.captured_frame
                    st.toast("Photo captured!", icon="📸")
            
            if st.session_state.captured_image is not None:
                st.image(st.session_state.captured_image, channels="BGR", caption="Captured Photo")
        
                st.subheader("2. Send Captured Photo via Email")
                email_photo_recipient = st.text_input("Recipient Email for Photo")
                if st.button("Send Photo"):
                    if not email_photo_recipient:
                        st.warning("Please enter a recipient email address.")
                    else:
                        with st.spinner("Encoding and sending image..."):
                            is_success, buffer = cv2.imencode(".jpg", st.session_state.captured_image)
                            if is_success:
                                success, message = send_email_with_attachment(
                                    email_photo_recipient, "Photo from DevOps Platform",
                                    "Attached is a photo captured from the platform.", buffer.tobytes())
                                if success: st.success(message)
                                else: st.error(message)
                            else:
                                st.error("Failed to encode image.")
        
        with st.container(border=True):
            st.subheader("3. Deploy Containerized Web Applications")
            app_type = st.radio("Select Application Type", ["Python Flask", "Apache Server"], horizontal=True)

            if app_type == "Python Flask":
                flask_port = st.number_input("Expose on Port", min_value=1024, value=5001)
                if st.button("Deploy Flask App"):
                    app_code = "from flask import Flask\napp = Flask(__name__)\n@app.route('/')\ndef hello(): return '<h1>Flask App running in Docker!</h1>'\nif __name__ == '__main__': app.run(host='0.0.0.0', port=5000)"
                    dockerfile = "FROM python:3.9-slim\nWORKDIR /app\nRUN pip install Flask\nCOPY app.py .\nCMD [\"python3\", \"app.py\"]"
                    with open("app.py", "w") as f: f.write(app_code)
                    with open("Dockerfile", "w") as f: f.write(dockerfile)
                    run_command("docker build -t flask-app-image .", "Flask image built.")
                    run_command(f"docker run -d --rm -p {flask_port}:5000 --name flask-app-container flask-app-image",
                                f"Flask app deployed! Access at http://localhost:{flask_port}")

            if app_type == "Apache Server":
                apache_port = st.number_input("Expose on Port", min_value=1024, value=8080)
                if st.button("Deploy Apache Server"):
                    html_code = "<h1>Apache Server in Docker</h1><p>Served by the DevOps Platform.</p>"
                    dockerfile = "FROM httpd:2.4\nCOPY ./index.html /usr/local/apache2/htdocs/"
                    with open("index.html", "w") as f: f.write(html_code)
                    with open("Dockerfile.apache", "w") as f: f.write(dockerfile) # Use separate dockerfile name
                    run_command("docker build -f Dockerfile.apache -t apache-server-image .", "Apache image built.")
                    run_command(f"docker run -d --rm -p {apache_port}:80 --name apache-container apache-server-image",
                                f"Apache server deployed! Access at http://localhost:{apache_port}")


    elif menu_choice == "AWS Cloud":
        try:
            # Check for secrets before creating session
            if not all(k in st.secrets for k in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"]):
                st.error("AWS credentials are not configured in `secrets.toml`. Please set them up.")
            else:
                boto3_session = boto3.Session(
                    aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
                    aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
                    region_name=st.secrets["AWS_DEFAULT_REGION"]
                )
                ec2 = boto3_session.resource('ec2')
                st.success(f"Successfully connected to AWS region: {boto3_session.region_name}")

                with st.container(border=True):
                    st.subheader("EC2 Instance Management")
                    if st.button("Refresh Instance List"):
                        st.rerun()

                    with st.spinner("Fetching EC2 instances..."):
                        try:
                            instances = list(ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'value': ['pending', 'running']}]))
                            if not instances:
                                st.write("No running instances found.")
                            else:
                                st.write("**Running Instances:**")
                                for instance in instances:
                                    st.write(f"- **ID:** {instance.id} | **Type:** {instance.instance_type} | **State:** {instance.state['Name']}")
                        except ClientError as e:
                            st.error(f"Error fetching instances: {e}. Check IAM permissions.")
                            instances = []
                    
                    with st.expander("Launch a new t2.micro EC2 Instance"):
                        if st.button("Launch Instance"):
                            try:
                                launched_instances = ec2.create_instances(
                                    ImageId='ami-0c55b159cbfafe1f0',  # Note: This is for us-east-1
                                    MinCount=1, MaxCount=1, InstanceType='t2.micro'
                                )
                                st.success(f"Instance {launched_instances[0].id} launch initiated.")
                                time.sleep(3)
                                st.rerun()
                            except ClientError as e:
                                st.error(f"AWS Error: {e}")

                    with st.expander("Terminate an EC2 Instance"):
                        if instances:
                            instance_to_terminate = st.selectbox("Select instance to terminate", [i.id for i in instances])
                            if st.button("Terminate Selected Instance", type="primary"):
                                try:
                                    ec2.instances.filter(InstanceIds=[instance_to_terminate]).terminate()
                                    st.warning(f"Termination request sent for {instance_to_terminate}.")
                                    time.sleep(3)
                                    st.rerun()
                                except ClientError as e:
                                    st.error(f"AWS Error: {e}")
                        else:
                            st.info("No running instances to terminate.")
        except (NoCredentialsError, PartialCredentialsError):
            st.error("AWS credentials not found. Please ensure they are set up correctly.")
        except Exception as e:
            st.error(f"An unexpected error occurred with AWS: {e}")

    # Simplified sections for CLI tools
    elif menu_choice in ["Docker CLI", "Kubernetes", "Terraform", "Ansible", "Jenkins"]:
        if menu_choice == "Docker CLI":
            c1, c2 = st.columns(2)
            img_name = c1.text_input("Image Name (e.g., 'nginx:latest')", "hello-world")
            c1.button("Pull Image", on_click=run_command, args=(f"docker pull {img_name}",))
            c2.button("List Images", on_click=run_command, args=("docker images",))
            c2.button("List All Containers", on_click=run_command, args=("docker ps -a",))

            st.markdown("---")
            container_id = st.text_input("Enter Container ID or Name for Stop/Remove")
            c3, c4 = st.columns(2)
            c3.button("Stop Container", on_click=run_command, args=(f"docker stop {container_id}",))
            c4.button("Remove Container", type="primary", on_click=run_command, args=(f"docker rm {container_id}",))

        elif menu_choice == "Kubernetes":
            st.info("Ensure `kubectl` is configured to connect to a cluster (e.g., Minikube).")
            pod_name = st.text_input("Pod Name", "my-nginx-pod")
            if st.button("Launch Nginx Pod"):
                run_command(f"kubectl run {pod_name} --image=nginx", "Pod launch command sent.")
            if st.button("Get All Pods"):
                run_command("kubectl get pods --all-namespaces")

        elif menu_choice == "Terraform":
            st.info("Ensure `.tf` files are present in the app's directory.")
            if st.button("Initialize Terraform"): run_command("terraform init")
            if st.button("Apply Configuration"): run_command("terraform apply --auto-approve")
            if st.button("Destroy Resources", type="primary"): run_command("terraform destroy --auto-approve")
            
        elif menu_choice == "Ansible":
             st.info("Requires an inventory file and playbook in the app's directory.")
             inventory = st.text_input("Inventory File Path", "inventory.ini")
             playbook = st.text_input("Playbook File Path", "playbook.yml")
             if st.button("List Inventory Hosts"): run_command(f"ansible-inventory -i {inventory} --list")
             if st.button("Run Ansible Playbook"): run_command(f"ansible-playbook -i {inventory} {playbook}")

        elif menu_choice == "Jenkins":
            st.info("This will launch a new Jenkins controller in Docker.")
            jenkins_port = st.number_input("Expose Jenkins UI on Port", value=8080)
            if st.button("Launch Jenkins"):
                run_command(f"docker run -d --rm -p {jenkins_port}:8080 -p 50000:50000 --name jenkins-instance jenkins/jenkins:lts",
                "Jenkins deployed! See terminal for steps to get the admin password.")
                st.session_state.terminal_output += "\nINFO: To get admin password, run this in your main terminal:\n"
                st.session_state.terminal_output += "docker exec jenkins-instance cat /var/jenkins_home/secrets/initialAdminPassword\n"

    elif menu_choice == "Generative AI":
        st.info("This feature uses your Google Gemini API key from `secrets.toml`.")
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            st.subheader("Live Microphone to Terminal Command")
            st.write("Speak a command from the predefined map (e.g., 'list all files').")
            if st.button("Start Listening"):
                st.session_state.listening = True
            
            if st.session_state.listening:
                r = sr.Recognizer()
                with sr.Microphone() as source, st.spinner("Listening..."):
                    try:
                        r.adjust_for_ambient_noise(source)
                        audio = r.listen(source, timeout=5, phrase_time_limit=4)
                        text = r.recognize_google(audio).lower()
                        st.write(f"Recognized command: **{text}**")
                        command_map = {"list all files": "ls -la", "date": "date", "who am i": "whoami", "docker containers": "docker ps -a"}
                        matched_command = next((cmd for phrase, cmd in command_map.items() if phrase in text), None)

                        if matched_command:
                            run_command(matched_command, f"Executed recognized command: {matched_command}")
                        else:
                            st.error("Command not recognized in predefined map.")
                        st.session_state.listening = False
                        st.rerun()

                    except sr.UnknownValueError: st.error("Could not understand audio.")
                    except sr.RequestError as e: st.error(f"Speech service error; {e}")
                    except Exception as e: st.error(f"Error during speech recognition: {e}")
                    finally: st.session_state.listening = False


        except Exception as e:
            st.error(f"Error with Generative AI setup: {e}. Check your Gemini API Key.")

    elif menu_choice == "MongoDB":
        try:
            client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
            client.admin.command('ismaster') # Check connection
            db = client["devops_platform_db"]
            collection = db["user_submissions"]
            st.success("Successfully connected to MongoDB.")

            with st.form("mongodb_form", clear_on_submit=True):
                st.subheader("Data Submission Form")
                name = st.text_input("Name")
                email = st.text_input("Email")
                notes = st.text_area("Notes")
                submitted = st.form_submit_button("Submit to Database")
                if submitted and all([name, email, notes]):
                    doc = {"name": name, "email": email, "notes": notes, "submission_time": time.ctime()}
                    collection.insert_one(doc)
                    st.success("Data successfully stored in MongoDB.")
                elif submitted:
                    st.warning("Please fill all fields before submitting.")
            
            st.subheader("Stored Database Records")
            if st.button("Refresh Data"): st.rerun()
            all_data = list(collection.find({}, {'_id': 0}))
            st.dataframe(all_data, use_container_width=True)

        except pymongo.errors.ConnectionFailure as e:
            st.error(f"MongoDB Connection Error: {e}. Is the MongoDB service running?")
        except Exception as e:
            st.error(f"An unexpected error occurred with MongoDB: {e}")


# --- TERMINAL OUTPUT (RIGHT COLUMN) ---
with col2:
    st.header("Live Operations Terminal", divider='gray')
    if st.button("Clear Terminal", use_container_width=True):
        st.session_state.terminal_output = TERMINAL_WELCOME_MESSAGE
        st.rerun()

    # Use a <pre> tag within a div to maintain formatting and enable scrolling
    terminal_content_html = html.escape(st.session_state.terminal_output)
    st.markdown(f'<div class="terminal"><pre style="white-space: pre-wrap; word-wrap: break-word;">{terminal_content_html}</pre></div>', unsafe_allow_html=True)