from flask import Flask, render_template, request, send_from_directory, url_for, jsonify, redirect, session, send_file
import os
import subprocess
import re
from threading import Thread
import time
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key
app.config['DOWNLOAD_FOLDER'] = 'downloads'
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Global progress tracking
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
    """Sanitize filename to remove invalid characters"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def download_video(url, quality):
    global progress
    
    progress.update({
        'status': 'downloading',
        'percentage': 0,
        'filename': '',
        'speed': '',
        'eta': '',
        'title': '',
        'thumbnail': '',
        'error': '',
        'final_path': ''
    })
    
    try:
        os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
        output_template = os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s')
        
        cmd = [
            'yt-dlp',
            '--newline',
            '--output', output_template,
            '--print', 'after_move:filepath:%(filepath)s',
            '--print', 'title:%(title)s',
            '--print', 'thumbnail:%(thumbnail)s',
            '--no-warnings',
            '--ignore-errors',
            '--progress',
            '--force-overwrites',
            '--no-continue',
        ]
        
        if quality == 'audio':
            cmd.extend(['-x', '--audio-format', 'mp3'])
        elif quality == 'highest':
            cmd.extend(['-f', 'best'])
        else:
            cmd.extend(['-f', f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]'])
        
        cmd.append(url)
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            bufsize=1,
            universal_newlines=True
        )
        
        final_filename = None
        
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                if line.startswith('after_move:filepath:'):
                    filepath = line.split('after_move:filepath:')[1].strip()
                    final_filename = os.path.basename(filepath)
                    progress['filename'] = final_filename
                    progress['final_path'] = filepath
                elif line.startswith('title:'):
                    progress['title'] = line.split('title:')[1].strip()
                elif line.startswith('thumbnail:'):
                    progress['thumbnail'] = line.split('thumbnail:')[1].strip()
                elif '[download]' in line:
                    parse_progress_line(line)
        
        return_code = process.wait()
        
        if return_code == 0:
            if not final_filename:
                for file in os.listdir(app.config['DOWNLOAD_FOLDER']):
                    if file.endswith(('.mp4', '.mkv', '.webm', '.mp3', '.m4a')):
                        final_filename = file
                        progress['filename'] = final_filename
                        progress['final_path'] = os.path.join(app.config['DOWNLOAD_FOLDER'], final_filename)
                        break
            
            if final_filename and os.path.exists(os.path.join(app.config['DOWNLOAD_FOLDER'], final_filename)):
                progress.update({
                    'status': 'completed',
                    'percentage': 100,
                })
                return True, None
            else:
                error_msg = "Download completed but file not found"
                progress.update({'status': 'failed', 'error': error_msg})
                return False, error_msg
        else:
            error_msg = f"yt-dlp process failed with return code {return_code}"
            progress.update({'status': 'failed', 'error': error_msg})
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Download error: {str(e)}"
        progress.update({'status': 'failed', 'error': error_msg})
        return False, error_msg

def parse_progress_line(line):
    try:
        if '%' in line:
            percentage_match = re.search(r'(\d+(?:\.\d+)?)%', line)
            if percentage_match:
                progress['percentage'] = float(percentage_match.group(1))
        
        speed_match = re.search(r'(\d+(?:\.\d+)?(?:K|M|G)?iB/s)', line)
        if speed_match:
            progress['speed'] = speed_match.group(1)
        
        eta_match = re.search(r'ETA (\d+:\d+)', line)
        if eta_match:
            progress['eta'] = eta_match.group(1)
            
    except Exception as e:
        print(f"Error parsing progress line: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def start_download():
    url = request.form.get('video_url')
    quality = request.form.get('quality')
    
    if not url:
        return render_template('index.html', error="Please enter a video URL")
    
    session['download_url'] = url
    session['download_quality'] = quality
    
    thread = Thread(target=download_video, args=(url, quality))
    thread.daemon = True
    thread.start()
    
    return render_template('progress.html')

@app.route('/progress')
def get_progress():
    return jsonify(progress)

@app.route('/download_file/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        return f"Error downloading file: {str(e)}", 404

@app.route('/open_file/<filename>')
def open_file(filename):
    try:
        return send_from_directory(
            app.config['DOWNLOAD_FOLDER'],
            filename
        )
    except Exception as e:
        return f"Error opening file: {str(e)}", 404

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
