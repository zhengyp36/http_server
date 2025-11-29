#!/usr/bin/env python3
import os
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote
import re

class UploadHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>UpLoading Files to {self.path}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
        h1 {{ color: #333; }}
        .upload-area {{ border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }}
        .progress {{ width: 100%; height: 30px; background: #f0f0f0; margin: 10px 0; display: none; }}
        .progress-bar {{ height: 100%; background: #4CAF50; width: 0%; text-align: center; line-height: 30px; color: white; }}
        .file-list {{ margin: 20px 0; }}
        .file-item {{ padding: 10px; margin: 5px 0; background: #f9f9f9; }}
        .status {{ margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>UpLoading Files to {self.path}</h1>
    <div class="upload-area">
        <input type="file" id="fileInput" multiple>
        <button onclick="uploadFiles()">Upload</button>
    </div>
    <div class="progress" id="progressContainer">
        <div class="progress-bar" id="progressBar">0%</div>
    </div>
    <div class="status" id="status"></div>
    <div class="file-list" id="fileList"></div>

    <script>
        async function uploadFiles() {{
            const files = document.getElementById('fileInput').files;
            if (files.length === 0) {{
                alert('Please select files first');
                return;
            }}

            const progressContainer = document.getElementById('progressContainer');
            const progressBar = document.getElementById('progressBar');
            const status = document.getElementById('status');
            const fileList = document.getElementById('fileList');
            
            fileList.innerHTML = '';
            progressContainer.style.display = 'block';

            for (let i = 0; i < files.length; i++) {{
                const file = files[i];
                const formData = new FormData();
                formData.append('file', file);

                status.innerHTML = `Uploading ${{i + 1}}/${{files.length}}: ${{file.name}}`;
                
                try {{
                    const xhr = new XMLHttpRequest();
                    
                    xhr.upload.addEventListener('progress', (e) => {{
                        if (e.lengthComputable) {{
                            const percent = Math.round((e.loaded / e.total) * 100);
                            progressBar.style.width = percent + '%';
                            progressBar.textContent = percent + '%';
                        }}
                    }});

                    await new Promise((resolve, reject) => {{
                        xhr.onload = () => {{
                            if (xhr.status === 200) {{
                                fileList.innerHTML += `<div class="file-item">✓ ${{file.name}} uploaded successfully</div>`;
                                resolve();
                            }} else {{
                                fileList.innerHTML += `<div class="file-item">✗ ${{file.name}} failed: ${{xhr.responseText}}</div>`;
                                reject();
                            }}
                        }};
                        xhr.onerror = () => reject();
                        xhr.open('POST', '/upload');
                        xhr.send(formData);
                    }});

                    progressBar.style.width = '0%';
                    progressBar.textContent = '0%';
                }} catch (error) {{
                    fileList.innerHTML += `<div class="file-item">✗ ${{file.name}} failed</div>`;
                }}
            }}

            progressContainer.style.display = 'none';
            status.innerHTML = `Completed: ${{files.length}} file(s) processed`;
            document.getElementById('fileInput').value = '';
        }}
    </script>
</body>
</html>
            '''
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/upload':
            try:
                content_length = int(self.headers['Content-Length'])
                content_type = self.headers['Content-Type']
                
                if not content_type or 'boundary' not in content_type:
                    self.send_error(400, 'Invalid content type')
                    return
                
                boundary = content_type.split('boundary=')[1].encode()
                
                remaining = content_length
                line = self.rfile.readline()
                remaining -= len(line)
                
                if boundary not in line:
                    self.send_error(400, 'Invalid boundary')
                    return
                
                filename = None
                line = self.rfile.readline()
                remaining -= len(line)
                
                match = re.search(rb'filename="(.+?)"', line)
                if match:
                    filename = match.group(1).decode('utf-8')
                
                if not filename:
                    self.send_error(400, 'No filename found')
                    return
                
                line = self.rfile.readline()
                remaining -= len(line)
                line = self.rfile.readline()
                remaining -= len(line)
                
                filepath = os.path.join(self.server.directory, os.path.basename(filename))
                
                with open(filepath, 'wb') as f:
                    preline = self.rfile.readline()
                    remaining -= len(preline)
                    
                    while remaining > 0:
                        line = self.rfile.readline()
                        remaining -= len(line)
                        
                        if boundary in line:
                            preline = preline[:-2]
                            if preline:
                                f.write(preline)
                            break
                        
                        f.write(preline)
                        preline = line
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Upload successful')
                
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404)

def run(directory, port):
    directory = os.path.abspath(directory)
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, UploadHTTPRequestHandler)
    httpd.directory = directory
    
    print(f'Server running on http://0.0.0.0:{port}')
    print(f'Upload directory: {directory}')
    httpd.serve_forever()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', default='.', help='Directory to save uploaded files')
    parser.add_argument('port', type=int, nargs='?', default=8000, help='Port number')
    args = parser.parse_args()
    
    run(args.directory, args.port)

