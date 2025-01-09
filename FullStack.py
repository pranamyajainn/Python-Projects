import os 
import json
import pandas as pd
import fitz
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from llama_index.llms.groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
import matplotlib
matplotlib.use('Agg')  # Use the Agg backend for matplotlib
import matplotlib.pyplot as plt
from llama_index.core import set_global_tokenizer
import tiktoken

set_global_tokenizer(tiktoken.encoding_for_model("gpt-4o").encode)


# Load environment variables from .env file
load_dotenv()

# Initialize the Flask app
app = Flask(__name__)
CORS(app)

# Groq API configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-70b-8192"  # Specify the model to use

# Initialize Groq client
groq_client = Groq(model=GROQ_MODEL, api_key=GROQ_API_KEY)

# Configure upload folder and allowed file extensions
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'csv', 'xlsx', 'json'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Ensure required directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Utility function: Check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function: Query Groq API
def use_groq_chat_api(prompt):
    try:
        response = groq_client.complete(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error occurred while processing the data with Groq API: {e}"


# Function: Generate PDF with file content and Groq API response
def generate_pdf(prompt, file_content, groq_response, df):
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'report.pdf')
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()

    # Custom styles for better formatting
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle

    custom_body_style = ParagraphStyle(
        'CustomBodyStyle',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,  # Line spacing
        alignment=TA_LEFT,  # Left-align text
        spaceAfter=10  # Space after each paragraph
    )

    custom_heading_style = ParagraphStyle(
        'CustomHeadingStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        alignment=TA_LEFT,
        spaceAfter=12,
    )

    elements = []

    # Add a bold heading
    elements.append(Paragraph("<b>FULL STACK REPORT GENERATING AGENT</b>", custom_heading_style))
    elements.append(Spacer(1, 12))

    # Add Groq API response
    formatted_response = groq_response.replace("\n", "<br />")  # Replace newlines with HTML line breaks
    elements.append(Paragraph(formatted_response, custom_body_style))
    elements.append(Spacer(1, 12))

    # Add comparison plot if there are exactly two columns
    if df.shape[1] == 2:
        try:
            plt.figure()
            df.plot(x=df.columns[0], y=df.columns[1], kind='bar', figsize=(8, 6))
            plt.title('Comparison Plot')
            comparison_plot_path = os.path.join(app.config['UPLOAD_FOLDER'], 'comparison_plot.png')
            plt.savefig(comparison_plot_path)
            plt.close()

            elements.append(Paragraph("Comparison Plot from Data:", custom_heading_style))
            elements.append(Image(comparison_plot_path, width=400, height=300))
            elements.append(Spacer(1, 12))
        except Exception as e:
            print(f"Error creating comparison plot: {e}")

    # Add numeric data visualizations
    if not df.empty:
        numeric_df = df.select_dtypes(include=['number'])  # Select numeric columns

        if not numeric_df.empty:
            # Bar plot
            try:
                plot_path_bar = os.path.join(app.config['UPLOAD_FOLDER'], 'plot_bar.png')
                numeric_df.plot(kind='bar', figsize=(8, 6))
                plt.title("Bar Plot of Numeric Data")
                plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels
                plt.tight_layout()
                plt.savefig(plot_path_bar)
                plt.close()

                elements.append(Paragraph("Bar Plot of Numeric Data:", custom_heading_style))
                elements.append(Image(plot_path_bar, width=400, height=300))
                elements.append(Spacer(1, 12))
            except Exception as e:
                print(f"Error creating bar plot: {e}")

            # Pie chart for the first numeric column
            try:
                plot_path_pie = os.path.join(app.config['UPLOAD_FOLDER'], 'plot_pie.png')
                numeric_df.iloc[:, 0].plot(kind='pie', figsize=(8, 6), autopct='%1.1f%%')
                plt.title("Pie Chart of First Numeric Column")
                plt.ylabel("")  # Remove y-axis label
                plt.tight_layout()
                plt.savefig(plot_path_pie)
                plt.close()

                elements.append(Paragraph("Pie Chart of First Numeric Column:", custom_heading_style))
                elements.append(Image(plot_path_pie, width=400, height=300))
                elements.append(Spacer(1, 12))
            except Exception as e:
                print(f"Error creating pie chart: {e}")

            # Histogram
            try:
                plot_path_hist = os.path.join(app.config['UPLOAD_FOLDER'], 'plot_hist.png')
                numeric_df.plot(kind='hist', figsize=(8, 6), alpha=0.7, bins=10)
                plt.title("Histogram of Numeric Data")
                plt.xlabel("Value")
                plt.ylabel("Frequency")
                plt.tight_layout()
                plt.savefig(plot_path_hist)
                plt.close()

                elements.append(Paragraph("Histogram of Numeric Data:", custom_heading_style))
                elements.append(Image(plot_path_hist, width=400, height=300))
                elements.append(Spacer(1, 12))
            except Exception as e:
                print(f"Error creating histogram: {e}")

    # Build and save the PDF
    doc.build(elements)
    return pdf_path


# Route: File upload and processing
@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400
    files = request.files.getlist('files[]')

    if not files or all(file.filename == '' for file in files):
        return jsonify({"error": "No files selected"}), 400

    prompt = request.form.get('prompt', '')  # Get user prompt

    # Initialize variables for processing
    combined_content = ""
    all_dfs = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            file_extension = filename.rsplit(".", 1)[1].lower()
            try:
                if file_extension == "csv":
                    df = pd.read_csv(file_path)
                elif file_extension == "xlsx":
                    df = pd.read_excel(file_path)
                elif file_extension == "json":
                    df = pd.read_json(file_path)
                elif file_extension == "pdf":
                    doc = fitz.open(file_path)
                    text = "".join(page.get_text() for page in doc)
                    df = pd.DataFrame([text], columns=["Content"])
                elif file_extension == "txt":
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    df = pd.DataFrame({"Content": [content]})
                else:
                    return jsonify({"error": f"Unsupported file type: {filename}"}), 400
            except Exception as e:
                return jsonify({"error": f"Error reading file {filename}: {str(e)}"}), 400

            # Combine data for processing
            all_dfs.append(df)
            combined_content += f"\n\nFile: {filename}\n{df.to_string(index=False)}"

    # Concatenate all DataFrames for visualization
    final_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

    # Combine prompt with file content
    combined_prompt = f"{prompt}\n\n{combined_content}"
    print("User Prompt:\n", prompt)
    print("Combined Content Sent to Groq API:\n", combined_prompt)

    # Call Groq API
    try:
        groq_response = use_groq_chat_api(combined_prompt)
    except Exception as e:
        return jsonify({"error": f"Groq API error: {str(e)}"}), 500

    # Generate PDF
    pdf_path = generate_pdf(prompt, combined_content, groq_response, final_df)
    return send_file(pdf_path, as_attachment=True, download_name='report.pdf')


@app.route("/")
def index():
    return render_template("upload.html")

# Main entry point
if __name__ == "__main__":
    app.run(debug=True)

#backend:
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Report Generation</title>
    <link rel="icon" href="https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Essay.svg/20px-Essay.svg.png"
        type="image/png">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            color: #fff;
            overflow: hidden;
            /* Prevents scrolling */
        }

        /* Moving gradient background */
        body::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, #4caf50, #81c784, #ffcc80, #ff7043, #4caf50);
            background-size: 300% 300%;
            animation: gradientMove 12s infinite linear;
            z-index: -1;
        }

        @keyframes gradientMove {
            0% {
                background-position: 0% 50%;
            }

            50% {
                background-position: 100% 50%;
            }

            100% {
                background-position: 0% 50%;
            }
        }

        header {
            text-align: center;
            margin-top: 50px;
        }

        header h1 {
            font-size: 2.5rem;
            font-weight: bold;
            text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.4);
        }

        header p {
            font-size: 1.2rem;
            margin-top: 10px;
            text-shadow: 1px 1px 4px rgba(0, 0, 0, 0.4);
        }

        .time {
            position: absolute;
            top: 15px;
            right: 20px;
            font-size: 1rem;
            font-weight: bold;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.6);
        }

        .form-container {
            margin-top: 100px;
            padding: 20px;
            width: 60%;
            max-width: 600px;
            margin: 100px auto;
        }

        form {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        textarea,
        input[type="file"],
        button {
            padding: 15px;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        textarea {
            resize: none;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.3);
        }

        input[type="file"] {
            background: rgba(255, 255, 255, 0.2);
            color: #fff;
            cursor: pointer;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.3);
        }

        button {
            background: #ff7043;
            color: #fff;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.4);
            text-transform: uppercase;
        }

        button:hover {
            background: #ff5722;
            transform: translateY(-2px);
            box-shadow: 0px 6px 12px rgba(0, 0, 0, 0.6);
        }

        .branding {
            text-align: center;
            margin-top: 40px;
        }

        .branding img {
            height: 40px;
            margin: 0 15px;
        }

        .branding a {
            color: #fff;
            font-size: 1rem;
            text-decoration: none;
        }

        .branding a:hover {
            text-decoration: underline;
        }
    </style>
    <script>
        function updateTime() {
            const now = new Date();
            const timeString = now.toLocaleTimeString();
            document.getElementById('time').innerText = timeString;
        }

        setInterval(updateTime, 1000);
    </script>
</head>

<body>
    <div class="time" id="time"></div>
    <header>
        <h1>AI Report Generation</h1>
        <p>Create insightful reports powered by Llama Index and Groq API.</p>
    </header>

    <div class="form-container">
        <form action="/upload" method="post" enctype="multipart/form-data">
            <textarea name="prompt" rows="4" placeholder="Enter your prompt here..." required></textarea>
            <input type="file" name="files[]" multiple>
            <button type="submit">Generate Report</button>
        </form>
    </div>

    <div class="branding">
        <a href="https://llamaindex.ai" target="_blank">
            <img src="https://cdn.brandfetch.io/id6a4s3gXI/w/400/h/400/theme/dark/icon.jpeg?c=1bfwsmEH20zzEfSNTed"
                alt="Llama Index">
        </a>
        <a href="https://groq.com" target="_blank">
            <img src="https://groq.com/favicon.ico" alt="Groq">
        </a>
    </div>
</body>

</html>
