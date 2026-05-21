import streamlit as st
import sqlite3
import re
from fpdf import FPDF

# Configuração da página (Design minimalista)
st.set_page_config(page_title="Plano de Classificação Online", page_icon="📁", layout="wide")

# Estilização CSS para um visual clean
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    h1, h2, h3 { color: #2C3E50; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    .stButton>button { background-color: #2C3E50; color: white; border-radius: 4px; }
    .stButton>button:hover { background-color: #34495E; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('pcd_escola.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            matricula TEXT NOT NULL,
            orgao TEXT NOT NULL
        )    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estrutura (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            tipo TEXT NOT NULL,
            codigo TEXT NOT NULL,
            texto TEXT NOT NULL,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id)
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
        self.cell(0, 10, 'Plano de Classificação de Documentos', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def gerar_pdf(orgao, itens):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Órgão: {orgao}", 0, 1, 'L')
    pdf.ln(5)
    pdf.set_font("Arial", '', 11)
    
    # Ordenar elementos pelo código numericamente para garantir a hierarquia visual no PDF
    itens_ordenados = sorted(itens, key=lambda x: x[0])
    
    for cod, tipo, txt in itens_ordenados:
        indent = ""
        if tipo == "Subfunção": indent = "   "
        elif tipo == "Atividade": indent = "      "
        elif tipo == "Tipo documental": indent = "         "
        
        texto_linha = f"{indent}{cod} {txt}"
        pdf.multi_cell(0, 8, texto_linha.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S')

# --- INTERFACE INICIAL ---
st.title("Plano de Classificação Online")
st.caption("Disciplina de Tópicos Especiais 1")

menu = st.sidebar.radio("Navegação", ["Área do Aluno", "Área do Professor (Admin)"])

# --- FLUXO ALUNO ---
if menu == "Área do Aluno":
    st.header("📝 Identificação do Aluno")
    
    if 'aluno_logado' not in st.session_state:
        with st.form("cadastro_aluno"):
            nome = st.text_input("Nome Completo:")
            matricula = st.text_input("Matrícula:")
            orgao = st.text_input("Órgão do Plano de Classificação:")
            enviar = st.form_submit_button("Iniciar Elaboração do Plano")
            
            if enviar:
                if nome and matricula and orgao:
                    cursor.execute("INSERT INTO alunos (nome, matricula, orgao) VALUES (?, ?, ?)", (nome, matricula, orgao))
                    conn.commit()
                    st.session_state['aluno_id'] = cursor.lastrowid
                    st.session_state['aluno_nome'] = nome
                    st.session_state['aluno_orgao'] = orgao
                    st.session_state['aluno_logado'] = True
                    st.rerun()
                else:
                    st.error("Por favor, preencha todos os campos de identificação.")
    else:
        st.info(f"Aluno: **{st.session_state['aluno_nome']}** | Órgão: **{st.session_state['aluno_orgao']}**")
        if st.button("Sair / Novo Cadastro"):
            del st.session_state['aluno_logado']
            st.rerun()
            
        st.write("---")
        st.header("📁 Cadastro de Elementos do Plano")
        
        tab1, tab2 = st.tabs(["Inserir Itens", "Visualizar Estrutura & Exportar"])
        
        with tab1:
            tipo_item = st.selectbox("Nível Hierárquico:", ["Função", "Subfunção", "Atividade", "Tipo documental"])
            codigo_item = st.text_input("Código Numérico:", help="Ex: 01, 01.01., 01.01.01., etc.")
            texto_item = st.text_area("Descrição/Texto (Máx 250 caracteres):", max_chars=250)
            
            if st.button("Salvar Item"):
                if not codigo_item.strip() or not texto_item.strip():
                    st.error("Proibido o cadastro de campos vazios. Preencha o código e o texto.")
                else:
                    valido, formato_correto = validar_codigo(codigo_item, tipo_item)
                    if not valido:
                        st.error(f"Código inválido para o nível '{tipo_item}'. {formato_correto}")
                    else:
                        cursor.execute("INSERT INTO estrutura (aluno_id, tipo, codigo, texto) VALUES (?, ?, ?, ?)",
                                       (st.session_state['aluno_id'], tipo_item, codigo_item.strip(), texto_item.strip()))
                        conn.commit()
                        st.success(f"{tipo_item} adicionada com sucesso!")
        
        with tab2:
            st.subheader(f"Estrutura Final: {st.session_state['aluno_orgao']}")
            
            cursor.execute("SELECT codigo, tipo, texto FROM estrutura WHERE aluno_id = ?", (st.session_state['aluno_id'],))
            dados = cursor.fetchall()
            
            if dados:
                # Ordenação lógica baseada nos códigos
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
                    file_name=f"Relatorio_Plano_Classificacao_{st.session_state['aluno_orgao']}.pdf",
                    mime="application/pdf"
                )
            else:
                st.warning("Nenhum item cadastrado ainda.")

# --- FLUXO PROFESSOR (ADMIN) ---
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
            
        st.subheader("Planos de Classificação Cadastrados por Aluno")
        
        cursor.execute("SELECT id, nome, matricula, orgao FROM alunos")
        lista_alunos = cursor.fetchall()
        
        if lista_alunos:
            for al_id, al_nome, al_mat, al_org in lista_alunos:
                with st.expander(f"Aluno: {al_nome} (Matrícula: {al_mat}) - Órgão: {al_org}"):
                    cursor.execute("SELECT codigo, tipo, texto FROM estrutura WHERE aluno_id = ?", (al_id,))
                    itens_aluno = cursor.fetchall()
                    if itens_aluno:
                        itens_aluno = sorted(itens_aluno, key=lambda x: x[0])
                        for cod, tipo, txt in itens_aluno:
                            st.write(f"**{cod}** [{tipo}] - {txt}")
                    else:
                        st.write("Nenhum item cadastrado por este aluno.")
        else:
            st.info("Nenhum aluno cadastrado no sistema até o momento.")
