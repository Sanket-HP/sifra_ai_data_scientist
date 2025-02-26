import os
import firebase_admin
from firebase_admin import credentials, auth
from flask import Flask, request, jsonify, render_template
from github import Github
import google.generativeai as genai
import time

# ✅ Secure API key handling (Load from environment)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "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your_github_token")  # Replace with your actual token
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDp1Q0i2ibPNUTWpj-PkBJFQ5DQivVvmwk")  # Replace with your actual key

if not GITHUB_TOKEN or not GEMINI_API_KEY:
    raise ValueError("GitHub or Gemini API Key is missing! Set it in the environment variables.")

# ✅ Initialize Flask app
app = Flask(__name__)

# ✅ Firebase Admin SDK initialization
cred = credentials.Certificate("sifraai-firebase-adminsdk-fbsvc-1415d35063.json")  # Path to Firebase credentials
firebase_admin.initialize_app(cred)

# ✅ GitHub authentication
g = Github(GITHUB_TOKEN)

# ✅ Initialize Google Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# 🏠 Home route
@app.route('/')
def index():
    return render_template('home.html')


# 🔹 Firebase Signup
@app.route('/signup', methods=['POST'])
def signup():
    try:
        email = request.form['email']
        password = request.form['password']
        user = auth.create_user(email=email, password=password)
        return jsonify({"status": "success", "user_id": user.uid}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# 🔹 Firebase Login
@app.route('/login', methods=['POST'])
def login():
    try:
        email = request.form['email']
        password = request.form['password']
        user = auth.get_user_by_email(email)
        return jsonify({"status": "success", "user_id": user.uid}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# 🔹 Save dataset & prompt to GitHub
@app.route('/save-to-github', methods=['POST'])
def save_to_github():
    try:
        github_username = request.form['github']
        dataset = request.files['dataset']
        programming_language = request.form['language']
        prompt = request.form['prompt']

        # ✅ Create a unique repo name
        timestamp = int(time.time())  # Unique timestamp to avoid duplicates
        repo_name = f"{github_username}-sifra-{timestamp}"

        # ✅ Create public repository
        user = g.get_user()
        repo = user.create_repo(repo_name, private=False)

        # ✅ Upload dataset file
        dataset_content = dataset.read().decode('utf-8')
        repo.create_file("dataset.csv", "Added dataset", dataset_content)

        # ✅ Save user prompt & programming language
        repo.create_file("prompt.txt", "Added prompt", prompt)
        repo.create_file("language.txt", "Added language", programming_language)

        return jsonify({"status": "success", "repo_name": repo_name, "message": "Repo created and data saved to GitHub."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# 🔹 Fetch dataset, prompt & generate code cell-wise
@app.route('/generate-code', methods=['GET'])
def generate_code_from_github():
    try:
        github_username = request.args.get('github')
        repo_name = request.args.get('repo')  # User should provide the created repo name

        repo = g.get_user().get_repo(repo_name)

        # ✅ Fetch dataset, prompt & language
        dataset_file = repo.get_contents("dataset.csv").decoded_content.decode('utf-8')
        prompt = repo.get_contents("prompt.txt").decoded_content.decode('utf-8')
        language = repo.get_contents("language.txt").decoded_content.decode('utf-8')

        # ✅ Generate code cell-wise with Gemini AI
        generated_code = generate_code(prompt, dataset_file, language)

        # ✅ Save generated code to GitHub
        repo.create_file("generated_code.py", "Generated AI Code", generated_code)

        return jsonify({"status": "success", "generated_code": generated_code}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# 🔹 Generate Code using Gemini API (Cell-wise)
def generate_code(prompt, dataset, language):
    try:
        complete_prompt = f"""
        You are an AI that generates {language} code for data analysis. 
        The user has uploaded this dataset:
        {dataset}

        Their request:
        {prompt}

        Please generate code **cell by cell**, ensuring real-time execution.
        """

        response = genai.generate_text(complete_prompt)

        # ✅ Simulating cell-wise generation (modify according to Gemini response structure)
        generated_code = "\n\n# 🚀 Generated Code (Cell-wise)\n"
        code_cells = response.result.split("\n\n")  # Assuming Gemini provides separate code blocks
        for idx, cell in enumerate(code_cells, 1):
            generated_code += f"# 📌 Cell {idx}\n{cell}\n\n"

        return generated_code
    except Exception as e:
        return str(e)


# 🔹 Save modified code back to GitHub
@app.route('/save-modified-code', methods=['POST'])
def save_modified_code():
    try:
        github_username = request.form['github']
        repo_name = request.form['repo']
        modified_code = request.form['modified_code']

        repo = g.get_user().get_repo(repo_name)

        # ✅ Save modified code
        try:
            repo.create_file("modified_generated_code.py", "Added modified code", modified_code)
        except:
            file = repo.get_contents("modified_generated_code.py")
            repo.update_file(file.path, "Updated modified code", modified_code, file.sha)

        return jsonify({"status": "success", "message": "Code updated successfully."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# 🏃 Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
