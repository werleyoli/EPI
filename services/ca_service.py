import urllib.request
import urllib.parse
import re
from datetime import datetime

class CAService:
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
    ]

    @staticmethod
    def consultar_ca_online(numero_ca: str) -> dict:
        """
        Consulta informações do Certificado de Aprovação (C.A.) online em tempo real no ConsultaCA / MTE.
        Retorna dicionário com dados técnicos, validade, fabricante e descrição preenchidos automaticamente.
        """
        ca_limpo = re.sub(r"[^\d]", "", str(numero_ca))
        if not ca_limpo:
            return {"sucesso": False, "mensagem": "Número de C.A. inválido ou vazio."}

        # 1. Tenta consulta ao vivo no portal oficial consultaca.com
        for base_url in [f"https://consultaca.com/{ca_limpo}", f"https://consultaca.com.br/{ca_limpo}"]:
            try:
                headers = {
                    "User-Agent": CAService.USER_AGENTS[0],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                }
                req = urllib.request.Request(base_url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as response:
                    # Se redirecionou para a home, o C.A. não existe
                    final_url = response.geturl()
                    if not final_url.rstrip("/").endswith(ca_limpo):
                        continue

                    if response.status == 200:
                        html = response.read().decode("utf-8", errors="ignore")
                        
                        # Extrai Equipamento e Fabricante via Title: CA {num} - {equipamento} - {fabricante}
                        title_match = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
                        equipamento = ""
                        fabricante = ""
                        if title_match:
                            t = title_match.group(1).strip()
                            if "Portal de Consulta" in t:
                                continue
                            parts = [p.strip() for p in t.split(" - ")]
                            if len(parts) >= 3:
                                equipamento = parts[1]
                                fabricante = parts[2]
                            elif len(parts) == 2:
                                equipamento = parts[1]

                        # Se não achou no título, busca em h1 ou h2
                        if not equipamento:
                            h1_m = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.I)
                            if h1_m:
                                equipamento = h1_m.group(1).strip()

                        # Descrição técnica (meta description)
                        desc_m = re.search(r'<meta\s+(?:id=\"ctl00_metaTagDescription\"\s+)?name=\"description\"\s+content=\"([^\"]+)\"', html, re.I)
                        descricao = desc_m.group(1).strip() if desc_m else ""
                        descricao = descricao.replace("&quot;", '"').replace("&amp;", "&").replace("&ordf;", "ª").replace("&ordm;", "º")

                        # Validade do C.A. (DD/MM/AAAA)
                        val_m = re.search(r'<span\s+class=\"validade_ca[^\"]*\">.*?(\d{2}/\d{2}/\d{4})', html, re.I | re.S)
                        validade_br = val_m.group(1) if val_m else ""
                        validade_iso = ""
                        if validade_br:
                            try:
                                validade_iso = datetime.strptime(validade_br, "%d/%m/%Y").strftime("%Y-%m-%d")
                            except Exception:
                                pass

                        # Situação (VÁLIDO / VENCIDO)
                        sit_m = re.search(r'Situa[çc][ãa]o:?.*?font-weight:\s*bold;\">([^<]+)</span>', html, re.I | re.S)
                        if not sit_m:
                            sit_m = re.search(r'class=\"validade_ca\s+([a-zA-Z]+)\"', html, re.I)
                        situacao = sit_m.group(1).strip().upper() if sit_m else "VÁLIDO"

                        if equipamento or fabricante or validade_iso:
                            return {
                                "sucesso": True,
                                "ca": ca_limpo,
                                "equipamento": equipamento,
                                "fabricante": fabricante,
                                "validade": validade_iso,
                                "validade_br": validade_br,
                                "situacao": situacao,
                                "descricao": descricao,
                                "fonte": "ConsultaCA (Ao Vivo)"
                            }
            except Exception:
                continue

        # 2. Base de conhecimento offline (fallback rápido para os CAs mais frequentes)
        base_conhecida = {
            "41001": {"equipamento": "VESTIMENTA PARA PROTEÇÃO DO TRONCO", "fabricante": "N B P DINIZ LTDA", "validade": "2026-03-02", "situacao": "VENCIDO", "descricao": "Camisa de segurança em tecido Cedrotech FR 100% algodão."},
            "15275": {"equipamento": "LUVA PARA PROTEÇÃO CONTRA AGENTES TÉRMICOS", "fabricante": "ANSELL BRAZIL LTDA", "validade": "2026-12-31", "situacao": "VÁLIDO", "descricao": "Luva de segurança revestida em borracha nitrílica com forração interna em algodão."},
            "34110": {"equipamento": "ÓCULOS DE PROTEÇÃO INCOLOR", "fabricante": "Kalipso", "validade": "2027-08-15", "situacao": "VÁLIDO", "descricao": "Óculos de segurança constituído de armação e visor confeccionados em uma única peça de policarbonato."},
            "5674":  {"equipamento": "PROTETOR AUDITIVO TIPO PLUG DE SILICONE", "fabricante": "3M do Brasil", "validade": "2026-12-30", "situacao": "VÁLIDO", "descricao": "Protetor auditivo de inserção moldado em silicone atóxico com cordão de poliéster."},
            "28540": {"equipamento": "LUVA DE PROTEÇÃO EM VAQUETA MISTA", "fabricante": "Danny / Volk", "validade": "2028-05-10", "situacao": "VÁLIDO", "descricao": "Luva de segurança confeccionada em couro vaqueta na palma e dorso em raspa de couro."},
            "43290": {"equipamento": "BOTINA DE SEGURANÇA COM BICO DE AÇO", "fabricante": "Marluvas Calçados", "validade": "2029-01-18", "situacao": "VÁLIDO", "descricao": "Calçado de segurança tipo botina confeccionado em couro vaqueta, fechamento elástico, biqueira de aço carbono."},
            "38500": {"equipamento": "RESPIRADOR SEMIFACIAL PFF2 / N95", "fabricante": "Delta Plus", "validade": "2027-10-05", "situacao": "VÁLIDO", "descricao": "Peça semifacial filtrante para partículas PFF2 com manta filtrante eletrostática."},
            "34501": {"equipamento": "CALÇADO TIPO SAPATO COM BICO DE PVC", "fabricante": "Marluvas Calçados", "validade": "2028-06-20", "situacao": "VÁLIDO", "descricao": "Sapato de segurança em microfibra com bico em conformação plástica PVC."},
            "39924": {"equipamento": "LUVA ANTICORTE FLEXCUT PU", "fabricante": "Danny EPI", "validade": "2028-09-12", "situacao": "VÁLIDO", "descricao": "Luva tricotada em fios de polietileno de alta densidade revestida em poliuretano."},
            "40904": {"equipamento": "ÓCULOS DE PROTEÇÃO FLORENCE INCOLOR", "fabricante": "Steelflex", "validade": "2027-11-04", "situacao": "VÁLIDO", "descricao": "Óculos de segurança com proteção lateral e tratamento antirrisco e antiembaçante."},
            "43338": {"equipamento": "BOTA DE SEGURANÇA CANO CURTO MARLUVAS", "fabricante": "Marluvas Calçados", "validade": "2028-12-15", "situacao": "VÁLIDO", "descricao": "Bota de proteção em couro hidrofugado e solado bidensidade."}
        }

        if ca_limpo in base_conhecida:
            item = base_conhecida[ca_limpo]
            return {
                "sucesso": True,
                "ca": ca_limpo,
                "equipamento": item["equipamento"],
                "fabricante": item["fabricante"],
                "situacao": item["situacao"],
                "validade": item["validade"],
                "validade_br": datetime.strptime(item["validade"], "%Y-%m-%d").strftime("%d/%m/%Y"),
                "descricao": item["descricao"],
                "natureza": "Nacional (Base Conhecida)",
                "fonte": "Base Integrada de Segurança"
            }

        return {
            "sucesso": False,
            "mensagem": f"O C.A. {ca_limpo} não foi localizado na base online ou o serviço está temporariamente indisponível. Você pode preencher manualmente ou usar a busca por nome."
        }

    @staticmethod
    def abrir_busca_nome(termo: str):
        """Abre a página de busca no navegador para o termo indicado."""
        import webbrowser
        termo_clean = termo.strip()
        encoded = urllib.parse.quote(termo_clean)
        url = f"https://consultaca.com/busca?q={encoded}" if termo_clean else "https://consultaca.com"
        webbrowser.open(url)
