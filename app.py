import streamlit as st
import sqlite3
import os
import re
from fpdf import FPDF

# Configuração da página
st.set_page_config(page_title="Plano de Classificação Online", page_icon="📁", layout="wide")

# Estilização CSS Minimalista
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    h1, h2, h3 { color: #2C3E50; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    .stButton>button { background-color: #2C3E50; color: white; border-radius: 4px; }
    .stButton>button:hover { background-color: #34495E; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS PERSISTENTE SEGURO ---
if not os.path.exists("/data"):
    try:
        os.makedirs("/data")
        DB_PATH = "/data/pcd_data_permanente.db"
    except Exception:
        DB_PATH = "pcd_data_permanente.db"
else:
    DB_PATH = "/data/pcd_data_permanente.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            matricula TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            orgao TEXT NOT NULL
        )    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estrutura (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT,
            tipo TEXT NOT NULL,
            codigo TEXT NOT NULL,
            texto TEXT NOT NULL,
            FOREIGN KEY (matricula) REFERENCES alunos(matricula)
        )    ''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- FUNÇÕES DE VALIDAÇÃO E BUSCA HIERÁRQUICA ---
def validar_codigo(codigo, tipo):
    codigo = codigo.strip()
    if tipo == "Função":
        return bool(re.match(r"^\d{2}$", codigo)), "Formato ideal: XX (ex: 01)"
    elif tipo == "Subfunção":
        return bool(re.match(r"^\d{2}\.\d{2}\.?$", codigo)), "Formato ideal: XX.XX. (ex: 01.01.)"
    elif tipo == "Atividade":
        return bool(re.match(r"^\d{2}\.\d{2}\.\d{2}\.?$", codigo)), "Formato ideal: XX.XX.XX. (ex: 01.01.01.)"
    elif tipo == "Tipo documental":
        return bool(re.match(r"^\d{2}\.\d{2}\.\d{2}\.\d{2}\.?$", codigo)), "Formato ideal: XX.XX.XX.XX. (ex: 01.01.01.01.)"
    return False, ""

def buscar_nome_elemento(matricula, codigo_prefixo):
    if not matricula:
        return "Usuário não identificado"
    cursor.execute("SELECT texto FROM estrutura WHERE matricula = ? AND (codigo = ? OR codigo = ?)", 
                   (matricula, codigo_prefixo, f"{codigo_prefixo}."))
    resultado = cursor.fetchone()
    return resultado[0] if resultado else "Elemento Pai Não Encontrado no Banco"

# --- GERADOR DE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Plano de Classificacao de Documentos', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def gerar_pdf(orgao, itens):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Orgao: {orgao}", 0, 1, 'L')
    pdf.ln(5)
    pdf.set_font("Arial", '', 11)
    
    itens_ordenados = sorted(itens, key=lambda x: x[1])
    
    for _, cod, tipo, txt in itens_ordenados:
        indent = ""
        if tipo == "Subfunção":
            indent = "    "
        elif tipo == "Atividade":
            indent = "        "
        elif tipo == "Tipo documental":
            indent = "            "
            
        texto_linha = f"{indent}[{tipo}] {cod} - {txt}"
        pdf.multi_cell(190, 8, texto_linha.encode('latin-1', 'replace').decode('latin-1'))
    return bytes(pdf.output())

# --- INTERFACE ---
st.title("Plano de Classificação Online")
st.caption("Disciplina de Tópicos Especiais 1 - Salvamento de Progresso Ativo")

menu = st.sidebar.radio("Navegação", ["Área do Aluno", "Área do Professor (Admin)"])

if menu == "Área do Aluno":
    st.header("📝 Identificação do Aluno")
    
    if 'aluno_logado' not in st.session_state:
        opcao_acesso = st.radio(
            "Selecione uma opção:",
            ["Primeiro Acesso (Criar Novo Perfil)", "Já Estou Cadastrado (Recuperar Progresso)"],
            horizontal=True,
            key="opcao_acesso_abas"
        )
        
        with st.form("cadastro_aluno"):
            matricula = st.text_input("Matrícula:").strip()
            nome = st.text_input("Nome Completo:").strip()
            
            if opcao_acesso == "Primeiro Acesso (Criar Novo Perfil)":
                orgao = st.text_input("Órgão do Plano de Classificação:").strip()
            else:
                orgao = ""
                
            enviar = st.form_submit_button("Entrar no Sistema")
            
            if enviar:
                if not matricula or not nome:
                    st.error("Por favor, preencha a Matrícula e o Nome Completo.")
                else:
                    cursor.execute("SELECT nome, orgao FROM alunos WHERE matricula = ?", (matricula,))
                    aluno_existente = cursor.fetchone()
                    
                    if opcao_acesso == "Já Estou Cadastrado (Recuperar Progresso)":
                        if aluno_existente:
                            nome_salvo = " ".join(aluno_existente[0].strip().split()).lower()
                            nome_digitado = " ".join(nome.strip().split()).lower()
                            
                            if nome_salvo != nome_digitado:
                                st.error("Nome incorreto para a matrícula informada.")
                            else:
                                st.session_state['aluno_matricula'] = matricula
                                st.session_state['aluno_nome'] = aluno_existente[0]
                                st.session_state['aluno_orgao'] = aluno_existente[1]
                                st.session_state['aluno_logado'] = True
                                st.success("Bem-vindo de volta! Seu progresso foi restaurado.")
                                st.rerun()
                        else:
                            st.error(f"A matrícula '{matricula}' não foi encontrada.")
                    
                    else: 
                        if not orgao:
                            st.error("Por favor, preencha o campo 'Órgão do Plano de Classificação'.")
                        elif aluno_existente:
                            st.error(f"A matrícula '{matricula}' já está cadastrada no
