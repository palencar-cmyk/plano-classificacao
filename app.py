import streamlit as st
import sqlite3
import os
import re
from datetime import datetime
from fpdf import FPDF

# Configuração da página
st.set_page_config(page_title="PCD Online - UFF", page_icon="📁", layout="wide")

# Estilização CSS para um visual acadêmico e profissional
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #1a3a5a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stButton>button { background-color: #1a3a5a; color: white; border-radius: 5px; font-weight: bold; height: 40px; width: 100%; }
    .stButton>button:hover { background-color: #2c527a; border: 1px solid #1a3a5a; }
    .report-box { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid #1a3a5a; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS PERSISTENTE ---
DB_PATH = "/data/pcd_data_permanente.db" if os.path.exists("/data") else "pcd_data_permanente.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS alunos (matricula TEXT PRIMARY KEY, nome TEXT NOT NULL, orgao TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS membros_grupo (id INTEGER PRIMARY KEY AUTOINCREMENT, matricula_lider TEXT, nome_membro TEXT, matricula_membro TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS estrutura (id INTEGER PRIMARY KEY AUTOINCREMENT, matricula TEXT, tipo TEXT NOT NULL, codigo TEXT NOT NULL, texto TEXT NOT NULL, FOREIGN KEY (matricula) REFERENCES alunos(matricula))''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- FUNÇÕES DE VALIDAÇÃO E BUSCA ---
def validar_codigo(codigo, tipo):
    codigo = codigo.strip()
    if tipo == "Função":
        return bool(re.match(r"^\d{2}\.?$", codigo)), "Formato ideal: XX (ex: 01)"
    elif tipo == "Subfunção":
        return bool(re.match(r"^\d{2}\.\d{2}\.?$", codigo)), "Formato ideal: XX.XX. (ex: 01.01.)"
    elif tipo == "Atividade":
        return bool(re.match(r"^\d{2}\.\d{2}\.\d{2}\.?$", codigo)), "Formato ideal: XX.XX.XX. (ex: 01.01.01.)"
    elif tipo == "Tipo documental":
        return bool(re.match(r"^\d{2}\.\d{2}\.\d{2}\.\d{2}\.?$", codigo)), "Formato ideal: XX.XX.XX.XX. (ex: 01.01.01.01.)"
    return False, ""

def buscar_nome_elemento(matricula, codigo_prefixo):
    if not matricula:
        return "Elemento Pai"
    cod_limpo = codigo_prefixo.strip()
    if cod_limpo.endswith('.'):
        cod_limpo = cod_limpo[:-1]
        
    cursor.execute("SELECT texto FROM estrutura WHERE matricula = ? AND (codigo = ? OR codigo = ?)", (matricula, cod_limpo, f"{cod_limpo}."))
    resultado = cursor.fetchone()
    return resultado[0] if resultado else "Não localizado na árvore atual"

# --- GERADOR DE PDF PROFISSIONAL CORRIGIDO ---
class ProfessionalPDF(FPDF):
    def __init__(self, orgao, emitente, membros):
        super().__init__()
        self.orgao = orgao
        self.emitente = emitente
        self.membros = membros
        self.data_emissao = datetime.now().strftime("%d/%m/%Y %H:%M")

    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, 'UNIVERSIDADE FEDERAL FLUMINENSE', 0, 1, 'C')
        self.cell(0, 5, 'INSTITUTO DE ARTE E COMUNICAÇÃO SOCIAL', 0, 1, 'C')
        self.cell(0, 5, 'DEPARTAMENTO DE CIÊNCIA DA INFORMAÇÃO', 0, 1, 'C')
        self.cell(0, 5, 'CURSO DE GRADUAÇÃO EM ARQUIVOLOGIA', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'DISCIPLINA DE TÓPICOS ESPECIAIS 1', 0, 1, 'C')
        self.cell(0, 5, 'PROFESSORES: CLARISSA SCHMIDT E PAULO ALENCAR', 0, 1, 'C')
        self.ln(10)
        self.line(10, 42, 200, 42)

    def footer(self):
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        self.line(10, 275, 200, 275)
        self.cell(0, 10, self.encode_txt(f'Emitido por: {self.emitente} | Data: {self.data_emissao}'), 0, 0, 'L')
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'R')

    def encode_txt(self, texto):
        if not texto:
            return ""
        texto_limpo = str(texto).replace('–', '-').replace('—', '-')
        return texto_limpo.encode('latin-1', 'ignore').decode('latin-1')

def gerar_relatorio_final(orgao, emitente, matricula, membros, dados):
    pdf = ProfessionalPDF(orgao, emitente, membros)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 15, pdf.encode_txt("PLANO DE CLASSIFICAÇÃO DE DOCUMENTOS"), 0, 1, 'C')
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, pdf.encode_txt(f"ÓRGÃO PRODUTOR: {orgao.upper()}"), 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, " COMPONENTES DO GRUPO", 0, 1, 'L', fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, pdf.encode_txt(f"Líder / Responsável: {emitente} ({matricula})"), 0, 1, 'L')
    for m_nome, m_mat in membros:
        pdf.cell(0, 6, pdf.encode_txt(f"Integrante: {m_nome} ({m_mat})"), 0, 1, 'L')
    pdf.ln(8)

    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, " ESTRUTURA ARQUIVÍSTICA DO PLANO", 0, 1, 'L', fill=True)
    pdf.ln(4)
    
    # Ordenação estrita garantindo que subitens sigam seus pais
    dados_ordenados = sorted(dados, key=lambda x: [int(p) for p in re.findall(r'\d+', x[1])])
    
    for _, cod, tipo, txt in dados_ordenados:
        indent = ""
        if tipo == "Subfunção": indent =
