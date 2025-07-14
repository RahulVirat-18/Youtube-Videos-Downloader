from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for, session
import os
import subprocess
import re
from threading import Thread
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

progress = {
    'status': 'idle',
    'percentage': 0,
    'filename': '',
    'speed': '',
    'eta': '',
    'title': '',
    'thumbnail': '',
    'error': '',
    'final_path': ''
}

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def download_video(url, quality):
    global progress
    progress.update({k: '' if isinstance(v, str) else 0 for k, v in progress.items()})
    progress['status'] = 'downloading'

    try:
        output_template = os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s')
        cmd = ['yt-dlp', '--newline', '--output', output_template, '--no-warnings', '--ignore-errors']

        if quality == 'audio':
            cmd += ['-x', '--audio-format', 'mp3']
        elif quality == 'highest':
            cmd += ['-f', 'best']
        else:
            cmd += ['-f', f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]']

        cmd.append(url)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if '[download]' in line:
                parse_progress_line(line)

        process.wait()

        for file in sorted(os.listdir(app.config['DOWNLOAD_FOLDER']), key=lambda x: os.path.getctime(os.path.join(app.config['DOWNLOAD_FOLDER'], x)), reverse=True):
            if file.endswith((".mp4", ".mp3", ".webm", ".mkv", ".m4a")):
                progress.update({
                    'status': 'completed',
                    'filename': file,
                    'final_path': os.path.join(app.config['DOWNLOAD_FOLDER'], file),
                    'percentage': 100
                })
                return True, None

        raise Exception("Downloaded file not found")

    except Exception as e:
        progress.update({'status': 'failed', 'error': str(e)})
        return False, str(e)

def parse_progress_line(line):
    match = re.search(r'(\d{1,3}\.\d+)%', line)
    if match:
        progress['percentage'] = float(match.group(1))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def start_download():
    url = request.form.get('video_url')
    quality = request.form.get('quality')

    if not url:
        return render_template('index.html', error="Please enter a video URL")

    success, error = download_video(url, quality)

    if success:
        return redirect(url_for('download_file', filename=progress['filename']))
    else:
        return render_template('progress.html', error=progress['error'])

@app.route('/download_file/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return f"Download failed: {e}", 500

@app.route('/progress')
def get_progress():
    return jsonify(progress)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Auto-detect port for hosting platforms
    app.run(debug=False, host='0.0.0.0', port=port)
