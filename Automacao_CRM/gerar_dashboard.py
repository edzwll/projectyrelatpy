import json
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from html2image import Html2Image
from google import genai

# -------------------------------------------------------------------
# CONFIGURAÇÃO DE PASTAS E AMBIENTE
# -------------------------------------------------------------------
PASTA_ENTRADA = "Automacao_CRM/PDFs_Entrada"
os.makedirs(PASTA_ENTRADA, exist_ok=True)

data_hoje = datetime.now().strftime("%d-%m-%Y")
PASTA_SAIDA = f"Automacao_CRM/Relatorios_{data_hoje}"
os.makedirs(PASTA_SAIDA, exist_ok=True)

NOME_DO_TEMPLATE_HTML = "relatorio_template.html"

# Inicializa as ferramentas
client = genai.Client(api_key="AQ.Ab8RN6Kic6dUckARom3yVrgluKAfAh9NAgmdYbg2M2d0Q9BzLQ")
env = Environment(loader=FileSystemLoader('Automacao_CRM'))
template = env.get_template(NOME_DO_TEMPLATE_HTML)

hti = Html2Image(
    browser_executable=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    output_path=PASTA_SAIDA 
)

# -------------------------------------------------------------------
# LISTAR TODOS OS PDFs NA PASTA DE ENTRADA
# -------------------------------------------------------------------
arquivos_pdf = [f for f in os.listdir(PASTA_ENTRADA) if f.lower().endswith('.pdf')]

if not arquivos_pdf:
    print("---------------------------------------------------------")
    print(f"❌ Nenhum arquivo PDF encontrado.")
    print(f"👉 Jogue seus relatórios PDF dentro da pasta: {PASTA_ENTRADA}")
    print("---------------------------------------------------------")
    exit()

print(f"🚀 Encontrados {len(arquivos_pdf)} arquivo(s) PDF para processar!")
print("-" * 50)

# -------------------------------------------------------------------
# LOOP: PROCESSAR CADA PDF ENCONTRADO
# -------------------------------------------------------------------
for nome_arquivo in arquivos_pdf:
    caminho_pdf = os.path.join(PASTA_ENTRADA, nome_arquivo)
    
    print(f"🔄 Processando: {nome_arquivo}...")
    
    try:
        # PASSO 1: IA EXTRAI DADOS DO PDF
        pdf_file = client.files.upload(file=caminho_pdf)
        
        prompt = """
        Você é um extrator de dados de CRM. Analise o documento PDF anexado e retorne 
        EXATAMENTE um objeto JSON contendo as informações extraídas.

        Mantenha a estrutura e as chaves exatamente como neste exemplo:
        {
          "empresa": "Nome da Empresa",
          "usuario": "Nome do Usuário",
          "origem": "Origem dos leads",
          "status_funil": "Status do funil",
          "periodo": "Período analisado",
          "praca": "Nome da praça",
          "pdv": "Nome do PDV",
          "total_leads": 131,
          "info_consolidacao": "Texto referente ao total consolidado",
          "ranking": [
            {"nome": "VEICULO 1", "qtd": 30},
            {"nome": "VEICULO 2", "qtd": 20}
          ],
          "vendedores": ["Nome Vendedor 1", "Nome Vendedor 2"],
          "gestores": ["Nome Gestor 1"],
          "data_geracao": "DD/MM/AAAA HH:MM"
        }

        Se algum dado não for encontrado, coloque uma string amigável ao invés de null.
        """

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[pdf_file, prompt],
            config={"response_mime_type": "application/json"}
        )
        dados = json.loads(response.text.strip())

        # -------------------------------------------------------------------
        # GERAR NOME DINÂMICO DOS ARQUIVOS (PRAÇA + PDV)
        # -------------------------------------------------------------------
        praca_str = str(dados.get('praca') or 'N/A').upper()
        pdv_str = str(dados.get('pdv') or 'N/A').upper()
        total_leads = dados.get('total_leads', 0)
        
        # Pega a praça e o PDV, junta tudo e troca espaços por underline
        nome_inteligente = f"{praca_str}_{pdv_str}".replace(" ", "_").replace("/", "-")
        
        nome_imagem_final = f"Dashboard_{nome_inteligente}.png"
        nome_texto_final = f"Resumo_{nome_inteligente}.txt"

        # PASSO 2: INJETAR NO HTML
        html_preenchido = template.render(dados)

        # PASSO 3: GERAR IMAGEM COM O NOME NOVO
        hti.screenshot(
            html_str=html_preenchido, 
            save_as=nome_imagem_final, 
            size=(1160, 750)
        )

        # PASSO 4: MONTAR O TEXTO DO WHATSAPP
        print(f"   -> Montando o resumo: {nome_texto_final}")
        
        ranking = dados.get("ranking", [])
        
        # Monta as linhas de medalha de forma inteligente
        top1 = f"🥇 {str(ranking[0].get('nome', '')).upper()} ({ranking[0].get('qtd', 0)} leads)" if len(ranking) > 0 else ""
        top2 = f"🥈 {str(ranking[1].get('nome', '')).upper()} ({ranking[1].get('qtd', 0)} leads)" if len(ranking) > 1 else ""
        top3 = f"🥉 {str(ranking[2].get('nome', '')).upper()} ({ranking[2].get('qtd', 0)} leads)" if len(ranking) > 2 else ""
        
        texto_ranking = "\n".join(filter(None, [top1, top2, top3]))

        texto_gerado = f"""📊 RELATÓRIO GERAL DE LEADS
📅 Período consolidado dos registros: {data_hoje}
📍 Praça: {praca_str}
🏢 PDV: {pdv_str}

📥 Total de leads
{total_leads} leads registrados no período.

🏆 TOP 3 — MAIOR INTERESSE DOS LEADS

{texto_ranking}"""
        
        caminho_arquivo_texto = os.path.join(PASTA_SAIDA, nome_texto_final)
        with open(caminho_arquivo_texto, "w", encoding="utf-8") as arquivo:
            arquivo.write(texto_gerado)
            
        print(f"   ✅ Relatório '{nome_inteligente}' gerado com sucesso!")

    except Exception as e:
        print(f"   ❌ Erro ao processar o arquivo '{nome_arquivo}': {e}")
        
    print("-" * 50)

print(f"🎉 Todos os processos concluídos! Acesse a pasta: {PASTA_SAIDA}")