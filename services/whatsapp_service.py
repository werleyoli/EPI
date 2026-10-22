import urllib.parse
import webbrowser
import re

class WhatsAppService:
    @staticmethod
    def clean_phone(phone_str):
        if not phone_str:
            return ""
        # Remove caracteres não numéricos
        nums = re.sub(r"\D", "", phone_str)
        # Se não tiver DDI 55, adiciona
        if len(nums) in (10, 11):
            nums = "55" + nums
        return nums

    @staticmethod
    def build_delivery_url(employee, epi_name, ca_num, qtd, responsavel, dt_entrega=None):
        phone = WhatsAppService.clean_phone(employee.get("telefone", ""))

        dt_str = dt_entrega or "Hoje"

        msg = (
            f"🛡️ *COMPROVANTE DE ENTREGA DE EPI (NR-6)*\n\n"
            f"Olá, *{employee['nome']}*!\n\n"
            f"Confirmamos a entrega do seu equipamento de proteção individual:\n"
            f"📦 *EPI:* {epi_name}\n"
            f"🔖 *C.A. (MTE):* {ca_num}\n"
            f"🔢 *Quantidade:* {qtd}\n"
            f"📅 *Data da Entrega:* {dt_str}\n"
            f"👤 *Responsável:* {responsavel}\n\n"
            f"⚠️ _Lembramos que o uso do EPI é obrigatório e indispensável para a sua segurança, conforme a NR-6 do Ministério do Trabalho e Emprego._\n\n"
            f"Bom trabalho e conte com o setor de SST!"
        )

        encoded_msg = urllib.parse.quote(msg)

        if phone:
            url = f"https://wa.me/{phone}?text={encoded_msg}"
        else:
            # Abre WhatsApp Web para o usuário escolher o contato
            url = f"https://web.whatsapp.com/send?text={encoded_msg}"

        return url

    @staticmethod
    def build_exchange_alert_url(employee, epi_name, ca_num, dias_restantes):
        phone = WhatsAppService.clean_phone(employee.get("telefone", ""))

        prazo_str = f"vence em {dias_restantes} dias" if dias_restantes >= 0 else f"está VENCIDO há {abs(dias_restantes)} dias"

        msg = (
            f"⏰ *AVISO DE TROCA PREVENTIVA DE EPI (NR-6)*\n\n"
            f"Olá, *{employee['nome']}*!\n\n"
            f"Identificamos que o seu equipamento está no período de substituição preventiva:\n"
            f"📦 *EPI:* {epi_name} (C.A. {ca_num})\n"
            f"⏳ *Situação:* Seu equipamento {prazo_str}.\n\n"
            f"Por favor, compareça ao almoxarifado munido do equipamento usado para devolução e recebimento do item novo.\n\n"
            f"Setor de Segurança do Trabalho (SST)"
        )

        encoded_msg = urllib.parse.quote(msg)
        if phone:
            return f"https://wa.me/{phone}?text={encoded_msg}"
        else:
            return f"https://web.whatsapp.com/send?text={encoded_msg}"

    @staticmethod
    def send_via_whatsapp(url):
        webbrowser.open(url)
