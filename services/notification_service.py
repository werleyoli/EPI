import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import get_connection
from services.epi_service import EPIService
from services.movement_service import MovementService
from services.audit_service import AuditService
from datetime import datetime

class NotificationService:
    @staticmethod
    def get_smtp_config():
        """Recupera as configurações de SMTP do banco de dados."""
        with get_connection() as conn:
            cursor = conn.cursor()
            keys = [
                "smtp_servidor", "smtp_porta", "smtp_usuario", "smtp_senha",
                "smtp_remetente", "alerta_destinatarios"
            ]
            cfg = {}
            for k in keys:
                cursor.execute("SELECT valor FROM configuracoes WHERE chave = ?;", (k,))
                row = cursor.fetchone()
                cfg[k] = row[0] if row else ""
            return cfg

    @staticmethod
    def save_smtp_config(cfg: dict):
        """Salva as configurações de SMTP no banco."""
        with get_connection() as conn:
            cursor = conn.cursor()
            for k, v in cfg.items():
                cursor.execute("""
                    INSERT INTO configuracoes (chave, valor) VALUES (?, ?)
                    ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor;
                """, (k, str(v)))
            conn.commit()

        AuditService.log(
            acao="CONFIG_EMAIL",
            modulo="CONFIGURACOES",
            detalhes=f"Configurações de alerta por e-mail atualizadas (Servidor: {cfg.get('smtp_servidor')})"
        )

    @staticmethod
    def send_alert_email(assunto_custom=None, destinatarios_custom=None) -> dict:
        """
        Gera e dispara o relatório de alerta de estoque crítico e CAs vencendo.
        Retorna dicionário com status e mensagem.
        """
        cfg = NotificationService.get_smtp_config()
        servidor = cfg.get("smtp_servidor")
        porta = int(cfg.get("smtp_porta") or 587)
        usuario = cfg.get("smtp_usuario")
        senha = cfg.get("smtp_senha")
        remetente = cfg.get("smtp_remetente") or usuario
        destinatarios_str = destinatarios_custom or cfg.get("alerta_destinatarios", "")

        if not destinatarios_str:
            return {"sucesso": False, "mensagem": "Nenhum e-mail de destinatário configurado."}

        destinatarios = [d.strip() for d in destinatarios_str.split(",") if d.strip()]
        if not destinatarios:
            return {"sucesso": False, "mensagem": "Lista de destinatários vazia."}

        # Coleta dados para o alerta
        epis_criticos = EPIService.list_epis(filter_status="low") + EPIService.list_epis(filter_status="out")
        epis_ca = EPIService.list_epis(filter_status="ca_expiring")
        trocas_pendentes = MovementService.list_pending_replacements()

        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        assunto = assunto_custom or f"🚨 [ALERTA SST] Resumo de Estoque Crítico & Vencimento de EPIs - {now_str}"

        # Monta HTML profissional
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #1E293B; background-color: #F8FAFC; padding: 20px;">
            <div style="max-width: 650px; margin: 0 auto; background: #FFFFFF; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden;">
                <div style="background-color: #1E3A8A; color: #FFFFFF; padding: 20px; text-align: center;">
                    <h2 style="margin: 0; font-size: 20px;">EPI MASTER PRO - ALERTA OPERACIONAL</h2>
                    <p style="margin: 5px 0 0 0; font-size: 13px; opacity: 0.85;">Relatório Automatizado de Segurança do Trabalho e Compras</p>
                </div>
                
                <div style="padding: 20px;">
                    <p style="font-size: 14px;">Olá, este é um alerta emitido em <strong>{now_str}</strong> sobre itens que exigem atenção imediata no Almoxarifado:</p>
                    
                    <h3 style="color: #DC2626; border-bottom: 2px solid #FCA5A5; padding-bottom: 5px; margin-top: 25px;">
                        ⚠️ 1. EPIs com Estoque Crítico ou Zerado ({len(epis_criticos)} itens)
                    </h3>
        """

        if epis_criticos:
            html += """<table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px;">
            <thead>
                <tr style="background-color: #F1F5F9; text-align: left;">
                    <th style="padding: 8px; border: 1px solid #CBD5E1;">Código</th>
                    <th style="padding: 8px; border: 1px solid #CBD5E1;">EPI</th>
                    <th style="padding: 8px; border: 1px solid #CBD5E1;">Saldo</th>
                    <th style="padding: 8px; border: 1px solid #CBD5E1;">Mínimo</th>
                </tr>
            </thead>
            <tbody>"""
            for e in epis_criticos:
                status_color = "#DC2626" if e["quantidade"] == 0 else "#D97706"
                html += f"""<tr>
                    <td style="padding: 8px; border: 1px solid #E2E8F0; font-weight: bold;">{e['codigo']}</td>
                    <td style="padding: 8px; border: 1px solid #E2E8F0;">{e['nome']}</td>
                    <td style="padding: 8px; border: 1px solid #E2E8F0; color: {status_color}; font-weight: bold;">{e['quantidade']} {e['unidade']}</td>
                    <td style="padding: 8px; border: 1px solid #E2E8F0;">{e['estoque_minimo']} {e['unidade']}</td>
                </tr>"""
            html += "</tbody></table>"
        else:
            html += "<p style='color: #059669; font-size: 13px;'>✅ Nenhum item abaixo do estoque mínimo no momento.</p>"

        # Seção CA
        html += f"""
                    <h3 style="color: #D97706; border-bottom: 2px solid #FDE68A; padding-bottom: 5px; margin-top: 25px;">
                        ⏰ 2. C.A.s Vencidos ou a Vencer em 60 Dias ({len(epis_ca)} itens)
                    </h3>
        """
        if epis_ca:
            html += """<table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px;">
            <thead>
                <tr style="background-color: #F1F5F9; text-align: left;">
                    <th style="padding: 8px; border: 1px solid #CBD5E1;">EPI</th>
                    <th style="padding: 8px; border: 1px solid #CBD5E1;">C.A.</th>
                    <th style="padding: 8px; border: 1px solid #CBD5E1;">Validade</th>
                </tr>
            </thead>
            <tbody>"""
            for c in epis_ca:
                html += f"""<tr>
                    <td style="padding: 8px; border: 1px solid #E2E8F0;">{c['nome']}</td>
                    <td style="padding: 8px; border: 1px solid #E2E8F0; font-weight: bold;">{c['ca']}</td>
                    <td style="padding: 8px; border: 1px solid #E2E8F0; color: #DC2626;">{c.get('validade_ca') or 'N/D'}</td>
                </tr>"""
            html += "</tbody></table>"
        else:
            html += "<p style='color: #059669; font-size: 13px;'>✅ Todos os C.A.s estão regulares e dentro da validade.</p>"

        # Rodapé
        html += """
                    <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #E2E8F0; font-size: 12px; color: #64748B; text-align: center;">
                        Mensagem gerada automaticamente pelo <strong>EPI Master Pro</strong> em conformidade com a Norma NR-6.
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        # Envia e-mail via smtplib se usuário/senha estiverem configurados
        if not usuario or not senha:
            # Modo Simulação / Demonstração com registro de auditoria
            AuditService.log(
                acao="DISPARO_ALERTA_EMAIL",
                modulo="CONFIGURACOES",
                detalhes=f"Alerta gerado com sucesso para {len(destinatarios)} destinatários (Modo Demonstração: Credenciais SMTP não preenchidas)."
            )
            return {
                "sucesso": True,
                "mensagem": f"Relatório de alerta gerado com sucesso! (Modo Simulação: para envio real à internet, informe Usuário e Senha SMTP nas Configurações)."
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = assunto
            msg["From"] = remetente
            msg["To"] = ", ".join(destinatarios)
            msg.attach(MIMEText(html, "html"))

            server = smtplib.SMTP(servidor, porta, timeout=10)
            server.ehlo()
            if porta == 587:
                server.starttls()
            server.login(usuario, senha)
            server.sendmail(remetente, destinatarios, msg.as_string())
            server.quit()

            AuditService.log(
                acao="DISPARO_ALERTA_EMAIL",
                modulo="CONFIGURACOES",
                detalhes=f"E-mail de alerta enviado para {len(destinatarios)} destinatários via {servidor}"
            )
            return {"sucesso": True, "mensagem": f"E-mail de alerta enviado com sucesso para {len(destinatarios)} destinatários!"}
        except Exception as e:
            return {"sucesso": False, "mensagem": f"Falha no envio SMTP: {str(e)}"}
