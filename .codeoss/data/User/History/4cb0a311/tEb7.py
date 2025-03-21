from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, flash
from werkzeug.utils import secure_filename
import os
from google.cloud import speech, texttospeech_v1

# Initialize Flask app
app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
TTS_FOLDER = 'tts'
ALLOWED_EXTENSIONS = {'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TTS_FOLDER'] = TTS_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TTS_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_files(folder):
    files = []
    for filename in os.listdir(folder):
        if allowed_file(filename):
            files.append(filename)
    files.sort(reverse=True)
    return files

def transcribe_audio(file_path):
    client = speech.SpeechClient()

    with open(file_path, 'rb') as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        language_code="en-US",
        enable_word_confidence=True,
        enable_word_time_offsets=True
    )

    response = client.recognize(config=config, audio=audio)

    transcript = ''
    for result in response.results:
        transcript += result.alternatives[0].transcript + '\n'

    return transcript

def synthesize_text_to_speech(text, output_file):
    client = texttospeech_v1.TextToSpeechClient()

    input = texttospeech_v1.SynthesisInput(text=text)

    voice = texttospeech_v1.VoiceSelectionParams(
        language_code="en-UK"
    )

    audio_config = texttospeech_v1.AudioConfig(
        audio_encoding=texttospeech_v1.AudioEncoding.LINEAR16
    )

    request = texttospeech_v1.SynthesizeSpeechRequest(
        input=input,
        voice=voice,
        audio_config=audio_config
    )

    response = client.synthesize_speech(request=request)

    with open(output_file, 'wb') as audio_file:
        audio_file.write(response.audio_content)

@app.route('/')
def index():
    audio_files = get_files(UPLOAD_FOLDER)
    tts_files = get_files(TTS_FOLDER)
    return render_template('index.html', audio_files=audio_files, tts_files=tts_files)

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio_data' not in request.files:
        flash('No audio data')
        return redirect(request.url)

    file = request.files['audio_data']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Transcribe audio and save transcript
        transcript = transcribe_audio(file_path)
        transcript_path = file_path + '.txt'
        with open(transcript_path, 'w') as transcript_file:
            transcript_file.write(transcript)

    return redirect('/')

@app.route('/upload_text', methods=['POST'])
def upload_text():
    text = request.form['text']
    if text.strip():
        filename = datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
        output_path = os.path.join(app.config['TTS_FOLDER'], filename)

        # Generate audio from text
        synthesize_text_to_speech(text, output_path)

    return redirect('/')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/tts/<filename>')
def tts_file(filename):
    return send_from_directory(app.config['TTS_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, port=5001)

