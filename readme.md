# 🛡️ Label Scanner: AI Ingredient Safety Analyzer

**Label Scanner** is an intelligent transparency tool that helps consumers understand what is inside their products. By simply uploading a photo of an ingredient label, the app uses **Google Gemini AI** to extract, analyze, and cross-reference chemicals against global safety standards (FDA, ECHA, and WHO).

## 🚀 Key Features

* **Multimodal OCR:** Uses Gemini Vision to read ingredients from curved or blurry product packaging.
* **Toxicological Analysis:** Leverages AI reasoning to identify irritants, allergens, and hazardous chemicals.
* **Dockerized Architecture:** Guaranteed "it works on my machine" experience using containerization.
* **Instant Reporting:** Provides a structured safety score and detailed breakdown for every ingredient found.

## 🛠️ Tech Stack

* **Backend:** Django (Python 3.10+)
* **AI Engine:** Google Gemini Pro / Vision
* **Environment:** Docker & Docker Compose
* **Deployment:** Render

## 🐳 Getting Started (Docker)

To run this project locally without worrying about dependencies, follow these steps:

### 1. Prerequisites

* [Docker](https://www.docker.com/get-started) installed on your machine.
* A Google Gemini API Key (Available via [Google AI Studio](https://aistudio.google.com/)).

### 2. Installation

Clone the repository:

```bash
git clone https://github.com/KushalGhosh9899/labecanner.git
cd labecanner

```

### 3. Environment Setup

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_api_key_here
SECRET_KEY=your_django_secret_key
DEBUG=True

```

### 4. Launch

Build and start the containers:

```bash
docker-compose up --build

```

Once the build is finished, the application will be live at `http://localhost:8000`.

## 🏗️ How it Works

1. **The Capture:** The user provides an image (via camera or upload).
2. **The Extraction:** Django sends the image to Gemini's Vision model.
3. **The Logic:** The backend parses the AI response and calculates a **Risk Score** based on known chemical hazards.
4. **The UI:** Results are displayed in a clean, categorized list highlighting "Safe" vs "Warning" ingredients.

## 🧠 Technical Challenges & Resilience

* **Prompt Engineering:** I spent significant time fine-tuning the system prompt to ensure Gemini returns valid JSON, preventing backend parsing errors.
* **Containerization:** Implementing Docker ensured that the Python environment and its specific AI libraries remained stable regardless of the hosting provider.
* **API Optimization:** Handled asynchronous requests to ensure the UI doesn't freeze while the AI is analyzing large ingredient lists.

## 🤝 Contributing

I am always looking to improve the safety database and UI. Feel free to fork this repo and submit a PR!
