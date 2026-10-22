import os
import json
import base64
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import qrcode
from PIL import Image
import io
from database import APP_DIR, EXPORTS_DIR

class MobileSignatureHandler(BaseHTTPRequestHandler):
    employee_name = "Colaborador"
    signature_saved_callback = None
    server_instance = None

    def log_message(self, format, *args):
        # Suprime logs no console
        pass

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/sign"):
            html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Assinatura Digital - EPI Master Pro</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html, body {{
            height: 100%;
            height: 100dvh;
            overflow: hidden;
            background: #F1F5F9;
            color: #0F172A;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }}
        body {{
            display: flex;
            flex-direction: column;
            padding: 10px 14px;
            max-width: 540px;
            margin: 0 auto;
        }}
        .header {{
            flex-shrink: 0;
            text-align: center;
            padding-bottom: 6px;
        }}
        .header h1 {{
            font-size: 16px;
            color: #1E3A8A;
            font-weight: 700;
        }}
        .header p {{
            font-size: 13px;
            color: #64748B;
            margin-top: 2px;
        }}
        .canvas-container {{
            flex: 1 1 auto;
            min-height: 180px;
            max-height: calc(100dvh - 165px);
            background: #FFFFFF;
            border: 2px dashed #94A3B8;
            border-radius: 12px;
            position: relative;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
            overflow: hidden;
            touch-action: none;
        }}
        canvas {{
            width: 100%;
            height: 100%;
            display: block;
            touch-action: none;
        }}
        .hint {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #94A3B8;
            font-size: 15px;
            font-weight: 500;
            pointer-events: none;
            user-select: none;
            text-align: center;
        }}
        .buttons {{
            flex-shrink: 0;
            display: flex;
            gap: 12px;
            margin-top: 10px;
            padding-bottom: env(safe-area-inset-bottom, 8px);
        }}
        button {{
            flex: 1;
            padding: 14px 10px;
            font-size: 16px;
            font-weight: 700;
            border-radius: 10px;
            border: none;
            cursor: pointer;
            touch-action: manipulation;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .btn-clear {{
            background: #E2E8F0;
            color: #334155;
        }}
        .btn-save {{
            background: #16A34A;
            color: #FFFFFF;
        }}
        .success-overlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: #FFFFFF;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 24px;
            z-index: 999;
        }}
        .success-overlay h2 {{
            color: #10B981;
            font-size: 24px;
            margin-bottom: 8px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Termo de Cautela e Entrega de EPI</h1>
        <p>Colaborador: <b>{self.employee_name}</b></p>
    </div>

    <div class="canvas-container" id="container">
        <canvas id="sigCanvas"></canvas>
        <div class="hint" id="hint">✍️ Assine aqui com o dedo</div>
    </div>

    <div class="buttons">
        <button class="btn-clear" onclick="clearCanvas()">🗑️ Limpar</button>
        <button class="btn-save" onclick="saveSignature()">✔️ Confirmar</button>
    </div>

    <div class="success-overlay" id="success">
        <h2>✅ Assinatura Enviada!</h2>
        <p style="color: #64748B; font-size: 15px; margin-top: 6px;">
            Sua assinatura digital foi gravada com sucesso no sistema.<br/>Você já pode fechar esta aba.
        </p>
    </div>

    <script>
        const canvas = document.getElementById('sigCanvas');
        const container = document.getElementById('container');
        const hint = document.getElementById('hint');
        const ctx = canvas.getContext('2d');
        let drawing = false;
        let hasDrawn = false;

        function resize() {{
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
            ctx.lineWidth = 3;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.strokeStyle = '#0F172A';
        }}
        window.addEventListener('resize', resize);
        resize();

        function getPos(e) {{
            const rect = canvas.getBoundingClientRect();
            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const clientY = e.touches ? e.touches[0].clientY : e.clientY;
            return {{
                x: clientX - rect.left,
                y: clientY - rect.top
            }};
        }}

        function startDraw(e) {{
            e.preventDefault();
            drawing = true;
            hasDrawn = true;
            hint.style.display = 'none';
            const pos = getPos(e);
            ctx.beginPath();
            ctx.moveTo(pos.x, pos.y);
        }}

        function draw(e) {{
            if (!drawing) return;
            e.preventDefault();
            const pos = getPos(e);
            ctx.lineTo(pos.x, pos.y);
            ctx.stroke();
        }}

        function stopDraw(e) {{
            drawing = false;
        }}

        canvas.addEventListener('touchstart', startDraw, {{ passive: false }});
        canvas.addEventListener('touchmove', draw, {{ passive: false }});
        canvas.addEventListener('touchend', stopDraw);

        canvas.addEventListener('mousedown', startDraw);
        canvas.addEventListener('mousemove', draw);
        canvas.addEventListener('mouseup', stopDraw);

        function clearCanvas() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            hasDrawn = false;
            hint.style.display = 'block';
        }}

        function saveSignature() {{
            if (!hasDrawn) {{
                alert('Por favor, assine na tela antes de confirmar.');
                return;
            }}
            const dataUrl = canvas.toDataURL('image/png');
            fetch('/submit-signature', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ image: dataUrl }})
            }}).then(res => res.json())
              .then(data => {{
                  document.getElementById('success').style.display = 'flex';
              }}).catch(err => {{
                  alert('Erro ao enviar assinatura: ' + err);
              }});
        }}
    </script>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/submit-signature":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            img_b64 = data.get("image", "")

            if "," in img_b64:
                img_b64 = img_b64.split(",")[1]

            img_bytes = base64.b64decode(img_b64)
            sig_dir = os.path.join(EXPORTS_DIR, "signatures")
            os.makedirs(sig_dir, exist_ok=True)

            from datetime import datetime
            filename = f"mobile_sig_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            file_path = os.path.join(sig_dir, filename)

            # Salva como PNG com transparência
            image = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
            image.save(file_path, "PNG")

            if MobileSignatureHandler.signature_saved_callback:
                MobileSignatureHandler.signature_saved_callback(file_path)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "path": file_path}).encode("utf-8"))
        else:
            self.send_error(404)


class MobileSignatureService:
    _server = None
    _thread = None
    _port = 8765

    @staticmethod
    def get_local_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    @classmethod
    def start_session(cls, employee_name, on_signature_saved):
        """
        Inicia o servidor web local e gera o QR Code apontando para o link de assinatura móvel.
        Retorna (url, qrcode_image_path).
        """
        cls.stop_session()

        MobileSignatureHandler.employee_name = employee_name
        MobileSignatureHandler.signature_saved_callback = on_signature_saved

        local_ip = cls.get_local_ip()

        # Encontra porta disponível
        for port in range(8765, 8785):
            try:
                cls._server = HTTPServer(("0.0.0.0", port), MobileSignatureHandler)
                cls._port = port
                break
            except OSError:
                continue

        cls._thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        cls._thread.start()

        url = f"http://{local_ip}:{cls._port}/sign"

        # Gera QR Code em disco para exibir no app desktop
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        qr_path = os.path.join(EXPORTS_DIR, "mobile_qr.png")
        qr_img = qrcode.make(url)
        qr_img.save(qr_path)

        return url, qr_path

    @classmethod
    def stop_session(cls):
        """Finaliza o servidor local."""
        if cls._server:
            try:
                cls._server.shutdown()
                cls._server.server_close()
            except Exception:
                pass
            cls._server = None
            cls._thread = None
