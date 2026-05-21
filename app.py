import streamlit as st
from streamlit_sheets_connection import SheetsConnection
import pandas as pd
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

# --- CONEXÃO COM BANCO DE DADOS (GOOGLE SHEETS) ---
# Tenta conectar ao Sheets. Se não configurado, usa cache local seguro temporário
try:
    conn = st.connection("gsheets", type=SheetsConnection)
    uso_nuvem = True
except Exception:
    uso_nuvem = False

@st.cache_data(ttl=5)
def carregar_dados_banco(aba_nome):
    if uso_nuvem:
        try:
            return conn.read(worksheet=aba_nome, ttl="5s")
        except Exception:
            pass
    if f"local_db_{aba_nome}" not in st.session_state:
        if aba_nome == "alunos":
            st.session_state[f"local_db_{aba_nome}"] = pd.DataFrame(columns=["nome", "matricula", "orgao"])
        else:
            st.session_state[f"local_db_{aba_nome}"] = pd.DataFrame(columns=["matricula", "tipo", "codigo", "texto"])
    return st.session_state[f"local_db_{aba_nome}"]

def salvar_dados_banco(df, aba_nome):
    if uso_nuvem:
        try:
            conn.update(worksheet=aba_nome, data=df)
            return
        except Exception:
            pass
    st.session_state[f"local_db_{aba_nome}"] = df

# --- VALIDAÇÕES ---
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

def gerar_pdf(orgao, df_itens):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Orgao: {orgao}", 0, 1, 'L')
    pdf.ln(5)
    pdf.set_font("Arial", '', 11)
    
    df_ordenado = df_itens.sort_values(by="codigo")
    
    for _, row in df_ordenado.iterrows():
        texto_linha = f"[{row['tipo']}] {row['codigo']} - {row['texto']}"
        pdf.multi_cell(0, 8, texto_linha.encode('latin-1', 'replace').decode('latin-1'))
    return bytes(pdf.output())

# --- INTERFACE ---
st.title("Plano de Classificação Online")
st.caption("Disciplina de Tópicos Especiais 1 - Sistema de Salvamento Permanente")

menu = st.sidebar.radio("Navegação", ["Área do Aluno", "Área do Professor (Admin)"])

if menu == "Área do Aluno":
    st.header("📝 Acesso / Identificação do Aluno")
    
    if 'aluno_logado' not in st.session_state:
        with st.form("cadastro_aluno"):
            nome = st.text_input("Nome Completo:").strip()
            matricula = st.text_input("Matrícula:").strip()
            orgao = st.text_input("Órgão do Plano de Classificação:").strip()
            enviar = st.form_submit_button("Acessar / Criar Meu Plano")
            
            if enviar:
                if nome and matricula and orgao:
                    df_alunos = carregar_dados_banco("alunos")
                    
                    # REGRA: Verifica se a matrícula já existe no banco de dados permanente
                    registro_existente = df_alunos[df_alunos['matricula'] == matricula]
                    
                    if not registro_existente.empty:
                        # Se já existe, valida se o nome coincide para evitar fraude ou duplicados
                        dados_aluno = registro_existente.iloc[0]
                        if dados_aluno['nome'].lower() != nome.lower():
                            st.error(f"Erro: A matrícula '{matricula}' já está cadastrada para outro estudante.")
                        else:
                            # Carrega a sessão existente (Recupera o progresso salvo anteriormente!)
                            st.session_state['aluno_matricula'] = matricula
                            st.session_state['aluno_nome'] = dados_aluno['nome']
                            st.session_state['aluno_orgao'] = dados_aluno['orgao']
                            st.session_state['aluno_logado'] = True
                            st.success("Progresso anterior recuperado com sucesso!")
                            st.rerun()
                    else:
                        # Se for um usuário totalmente novo, cadastra no banco permanente
                        novo_aluno = pd.DataFrame([{"nome": nome, "matricula": matricula, "orgao": orgao}])
                        df_alunos = pd.concat([df_alunos, novo_aluno], ignore_index=True)
                        salvar_dados_banco(df_alunos, "alunos")
                        
                        st.session_state['aluno_matricula'] = matricula
                        st.session_state['aluno_nome'] = nome
                        st.session_state['aluno_orgao'] = orgao
                        st.session_state['aluno_logado'] = True
                        st.success("Novo perfil criado! Comece a cadastrar sua estrutura.")
                        st.rerun()
                else:
                    st.error("Por favor, preencha todos os campos.")
    else:
        st.info(f"Estudante: **{st.session_state['aluno_nome']}** | Matrícula: **{st.session_state['aluno_matricula']}** | Órgão: **{st.session_state['aluno_orgao']}**")
        
        col_botoes = st.columns([1, 4])
        with col_botoes[0]:
            if st.button("Sair do Sistema"):
                del st.session_state['aluno_logado']
                st.rerun()
                
        st.write("---")
        st.header("📁 Estrutura do Seu Plano de Classificação")
        
        tab1, tab2 = st.tabs(["Inserir Níveis / Elementos", "Visualizar Estrutura Salva & Exportar"])
        
        # Carrega os itens deste aluno específico
        df_estrutura_geral = carregar_dados_banco("estrutura")
        df_itens_aluno = df_estrutura_geral[df_estrutura_geral['matricula'] == st.session_state['aluno_matricula']]
        
        with tab1:
            tipo_item = st.selectbox("Nível Hierárquico:", ["Função", "Subfunção", "Atividade", "Tipo documental"])
            codigo_item = st.text_input("Código Numérico:", help="Ex: 01, 01.01., 01.01.01.")
            texto_item = st.text_area("Descrição / Texto do Nível (Máx 250 caracteres):", max_chars=250)
            
            if st.button("Salvar Elemento permanentemente"):
                if not codigo_item.strip() or not texto_item.strip():
                    st.error("Não é permitido cadastrar campos em branco.")
                else:
                    valido, formato_correto = validar_codigo(codigo_item, tipo_item)
                    if not valido:
                        st.error(f"Código inválido para o nível '{tipo_item}'. {formato_correto}")
                    else:
                        # Adiciona o novo item vinculando-o diretamente à matrícula do aluno
                        novo_item = pd.DataFrame([{
                            "matricula": st.session_state['aluno_matricula'],
                            "tipo": tipo_item,
                            "codigo": codigo_item.strip(),
                            "texto": texto_item.strip()
                        }])
                        df_estrutura_geral = pd.concat([df_estrutura_geral, novo_item], ignore_index=True)
                        salvar_dados_banco(df_estrutura_geral, "estrutura")
                        st.success(f"{tipo_item} adicionada e salva na nuvem com sucesso! Seu progresso está seguro.")
                        st.rerun()
                        
        with tab2:
            st.subheader(f"Árvore Hierárquica Atendida: {st.session_state['aluno_orgao']}")
            
            if not df_itens_aluno.empty:
                df_ordenado = df_itens_aluno.sort_values(by="codigo")
                
                for _, row in df_ordenado.iterrows():
                    cod, tipo, txt = row['codigo'], row['tipo'], row['texto']
                    if tipo == "Função":
                        st.markdown(f"**{cod} {txt}**")
                    elif tipo == "Subfunção":
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📄 {cod} {txt}")
                    elif tipo == "Atividade":
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔹 {cod} {txt}")
                    elif tipo == "Tipo documental":
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔸 *{cod} {txt}*")
                
                st.write("---")
                pdf_data = gerar_pdf(st.session_state['aluno_orgao'], df_itens_aluno)
                st.download_button(
                    label="📄 Exportar Relatório Oficial em PDF",
                    data=pdf_data,
                    file_name=f"Relatorio_PCD_{st.session_state['aluno_matricula']}.pdf",
                    mime="application/pdf"
                )
            else:
                st.warning("Você ainda não possui nenhum nível estrutural salvo neste plano.")

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
            
        st.subheader("Planos Permanentes Cadastrados por Aluno")
        
        df_alunos = carregar_dados_banco("alunos")
        df_estrutura = carregar_dados_banco("estrutura")
        
        if not df_alunos.empty:
            for _, al_row in df_alunos.iterrows():
                with st.expander(f"Aluno: {al_row['nome']} (Matrícula: {al_row['matricula']}) - Órgão: {al_row['orgao']}"):
                    itens_aluno = df_estrutura[df_estrutura['matricula'] == al_row['matricula']]
                    if not itens_aluno.empty:
                        itens_aluno = itens_aluno.sort_values(by="codigo")
                        for _, it_row in itens_aluno.iterrows():
                            st.write(f"**{it_row['codigo']}** [{it_row['tipo']}] - {it_row['texto']}")
                    else:
                        st.write("Nenhum item cadastrado por este aluno até o momento.")
        else:
            st.info("Nenhum aluno cadastrado no sistema permanente ainda.")
