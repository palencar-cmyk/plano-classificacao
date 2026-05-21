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

# --- BANCO DE DADOS PERSISTENTE LOCAL ---
# Salvando em um diretório que o Streamlit Cloud não apaga ao reiniciar o app
DB_PATH = os.path.join(os.getcwd(), "pcd_data_permanente.db")

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

# --- FUNÇÕES DE VALIDAÇÃO ---
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
    
    itens_ordenados = sorted(itens, key=lambda x: x[0])
    
    for cod, tipo, txt in itens_ordenados:
        texto_linha = f"[{tipo}] {cod} - {txt}"
        pdf.multi_cell(0, 8, texto_linha.encode('latin-1', 'replace').decode('latin-1'))
    return bytes(pdf.output())

# --- INTERFACE ---
st.title("Plano de Classificação Online")
st.caption("Disciplina de Tópicos Especiais 1 - Salvamento de Progresso Ativo")

menu = st.sidebar.radio("Navegação", ["Área do Aluno", "Área do Professor (Admin)"])

if menu == "Área do Aluno":
    st.header("📝 Identificação / Recuperação de Progresso")
    
    if 'aluno_logado' not in st.session_state:
        with st.form("cadastro_aluno"):
            nome = st.text_input("Nome Completo:").strip()
            matricula = st.text_input("Matrícula:").strip()
            orgao = st.text_input("Órgão do Plano de Classificação:").strip()
            enviar = st.form_submit_button("Entrar / Continuar de Onde Parei")
            
            if enviar:
                if nome and matricula and orgao:
                    # Busca se a matrícula já existe
                    cursor.execute("SELECT nome, orgao FROM alunos WHERE matricula = ?", (matricula,))
                    aluno_existente = cursor.fetchone()
                    
                    if aluno_existente:
                        # Se já existe, checa se o nome bate para evitar duplicados com dados errados
                        if aluno_existente[0].lower() != nome.lower():
                            st.error(f"A matrícula '{matricula}' já está registrada para outro estudante.")
                        else:
                            # Se bater nome e matrícula, recupera a sessão do aluno antigo
                            st.session_state['aluno_matricula'] = matricula
                            st.session_state['aluno_nome'] = aluno_existente[0]
                            st.session_state['aluno_orgao'] = aluno_existente[1]
                            st.session_state['aluno_logado'] = True
                            st.success("Seu progresso foi localizado e recuperado com sucesso!")
                            st.rerun()
                    else:
                        # Se for inédito, cadastra um novo
                        cursor.execute("INSERT INTO alunos (matricula, nome, orgao) VALUES (?, ?, ?)", (matricula, nome, orgao))
                        conn.commit()
                        st.session_state['aluno_matricula'] = matricula
                        st.session_state['aluno_nome'] = nome
                        st.session_state['aluno_orgao'] = orgao
                        st.session_state['aluno_logado'] = True
                        st.success("Novo perfil criado com sucesso!")
                        st.rerun()
                else:
                    st.error("Por favor, preencha todos os campos para acessar.")
    else:
        st.info(f"Estudante: **{st.session_state['aluno_nome']}** | Matrícula: **{st.session_state['aluno_matricula']}** | Órgão: **{st.session_state['aluno_orgao']}**")
        if st.button("Sair do Sistema (Salva automaticamente)"):
            del st.session_state['aluno_logado']
            st.rerun()
            
        st.write("---")
        st.header("📁 Elementos do seu Plano de Classificação")
        
        tab1, tab2 = st.tabs(["Inserir Níveis / Elementos", "Visualizar Estrutura & Exportar PDF"])
        
        with tab1:
            tipo_item = st.selectbox("Nível Hierárquico:", ["Função", "Subfunção", "Atividade", "Tipo documental"])
            codigo_item = st.text_input("Código Numérico:", help="Ex: 01, 01.01., 01.01.01.")
            texto_item = st.text_area("Descrição/Texto (Máx 250 caracteres):", max_chars=250)
            
            if st.button("Salvar Elemento"):
                if not codigo_item.strip() or not texto_item.strip():
                    st.error("Preencha todos os campos antes de salvar.")
                else:
                    valido, formato_correto = validar_codigo(codigo_item, tipo_item)
                    if not valido:
                        st.error(f"Código inválido para '{tipo_item}'. {formato_correto}")
                    else:
                        cursor.execute("INSERT INTO estrutura (matricula, tipo, codigo, texto) VALUES (?, ?, ?, ?)",
                                       (st.session_state['aluno_matricula'], tipo_item, codigo_item.strip(), texto_item.strip()))
                        conn.commit()
                        st.success(f"{tipo_item} adicionada com sucesso e salva na sua conta!")
                        st.rerun()
                        
        with tab2:
            st.subheader(f"Estrutura Atual: {st.session_state['aluno_orgao']}")
            
            cursor.execute("SELECT codigo, tipo, texto FROM estrutura WHERE matricula = ?", (st.session_state['aluno_matricula'],))
            dados = cursor.fetchall()
            
            if dados:
                dados_ordenados = sorted(dados, key=lambda x: x[0])
                
                for cod, tipo, txt in dados_ordenados:
                    if tipo == "Função":
                        st.markdown(f"**{cod} {txt}**")
                    elif tipo == "Subfunção":
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📄 {cod} {txt}")
                    elif tipo == "Atividade":
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔹 {cod} {txt}")
                    elif tipo == "Tipo documental":
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔸 *{cod} {txt}*")
                
                st.write("---")
                pdf_data = gerar_pdf(st.session_state['aluno_orgao'], dados)
                st.download_button(
                    label="📄 Exportar Relatório em PDF",
                    data=pdf_data,
                    file_name=f"Relatorio_PCD_{st.session_state['aluno_matricula']}.pdf",
                    mime="application/pdf"
                )
            else:
                st.warning("Nenhum item cadastrado por você ainda.")

elif menu == "Área do Professor (Admin)":
    st.header("🔒 Painel do Administrador")
    
    if 'admin_logado' not in st.session_state:
        usuario = st.text_input("Usuário Admin:")
        senha = st.text_input("Senha Admin:", type="password")
        if st.button("Acessar Painel"):
            if usuario == "Admin123" and senha == "123Admin":
                st.session_state['admin_logado'] = True
                st.rerun()
            else:
                st.error("Credenciais incorretas.")
    else:
        if st.button("Sair do Painel Admin"):
            del st.session_state['admin_logado']
            st.rerun()
            
        st.subheader("Planos de Classificação Cadastrados")
        
        cursor.execute("SELECT matricula, nome, orgao FROM alunos")
        lista_alunos = cursor.fetchall()
        
        if lista_alunos:
            for al_mat, al_nome, al_org in lista_alunos:
                with st.expander(f"Aluno: {al_nome} (Matrícula: {al_mat}) - Órgão: {al_org}"):
                    cursor.execute("SELECT codigo, tipo, texto FROM estrutura WHERE matricula = ?", (al_mat,))
                    itens_aluno = cursor.fetchall()
                    if itens_aluno:
                        itens_aluno = sorted(itens_aluno, key=lambda x: x[0])
                        for cod, tipo, txt in itens_aluno:
                            st.write(f"**{cod}** [{tipo}] - {txt}")
                    else:
                        st.write("Nenhum item cadastrado por este aluno.")
        else:
            st.info("Nenhum aluno realizou cadastros no sistema até o momento.")
