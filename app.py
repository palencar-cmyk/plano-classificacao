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
    .stButton>button { background-color: #2C3E50; color: white; border-radius: 4px; width: 100%; height: 40px; font-weight: bold; }
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

# --- FUNÇÕES DE VALIDAÇÃO E BUSCA ---
def validar_codigo(codigo, tipo):
    codigo = code = codigo.strip()
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
        return "Elemento Pai"
    cursor.execute("SELECT texto FROM estrutura WHERE matricula = ? AND (codigo = ? OR codigo = ?)", 
                   (matricula, codigo_prefixo, f"{codigo_prefixo}."))
    resultado = cursor.fetchone()
    return resultado[0] if resultado else "Elemento Pai não localizado"

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
        if tipo == "Subfunção": indent = "    "
        elif tipo == "Atividade": indent = "        "
        elif tipo == "Tipo documental": indent = "            "
        texto_linha = f"{indent}[{tipo}] {cod} - {txt}"
        pdf.multi_cell(190, 8, texto_linha.encode('latin-1', 'replace').decode('latin-1'))
    return bytes(pdf.output())

# --- INTERFACE PRINCIPAL ---
menu = st.sidebar.radio("Navegação", ["Área do Aluno", "Área do Professor (Admin)"])

if menu == "Área do Aluno":
    st.header("📝 Acesso do Estudante")
    
    if 'aluno_logado' not in st.session_state:
        opcao_acesso = st.radio(
            "Selecione o modo de entrada:",
            ["Já Estou Cadastrado (Recuperar Progresso)", "Primeiro Acesso (Criar Novo Perfil)"],
            horizontal=True
        )
        
        st.write("---")
        matricula_input = st.text_input("Digite sua Matrícula:", key="input_mat").strip()
        nome_input = st.text_input("Digite seu Nome Completo:", key="input_nome").strip()
        
        orgao_input = ""
        if opcao_acesso == "Primeiro Acesso (Criar Novo Perfil)":
            orgao_input = st.text_input("Nome da Instituição / Órgão do seu plano:", key="input_orgao").strip()
        
        st.write("##")
        if st.button("🚀 Entrar / Confirmar Cadastro no Sistema"):
            if not matricula_input or not nome_input:
                st.error("Por favor, preencha obrigatoriamente a Matrícula e o Nome Completo.")
            else:
                cursor.execute("SELECT nome, orgao FROM alunos WHERE matricula = ?", (matricula_input,))
                aluno_existente = cursor.fetchone()
                
                if opcao_acesso == "Já Estou Cadastrado (Recuperar Progresso)":
                    if aluno_existente:
                        nome_salvo = " ".join(aluno_existente[0].strip().split()).lower()
                        nome_digitado = " ".join(nome_input.strip().split()).lower()
                        
                        if nome_salvo != nome_digitado:
                            st.error("O nome digitado não confere com a matrícula salva no banco.")
                        else:
                            st.session_state['aluno_matricula'] = matricula_input
                            st.session_state['aluno_nome'] = aluno_existente[0]
                            st.session_state['aluno_orgao'] = aluno_existente[1]
                            st.session_state['aluno_logado'] = True
                            st.success("Sucesso! Carregando dados...")
                            st.rerun()
                    else:
                        st.error("Esta matrícula não foi encontrada. Se for seu primeiro acesso, mude a opção acima para 'Primeiro Acesso'.")
                
                else: # Primeiro Acesso
                    if not orgao_input:
                        st.error("Para novos cadastros, preencha o nome do Órgão.")
                    elif aluno_existente:
                        st.warning("Esta matrícula já existe. Use a opção 'Já Estou Cadastrado'.")
                    else:
                        cursor.execute("INSERT INTO alunos (matricula, nome, orgao) VALUES (?, ?, ?)", 
                                       (matricula_input, nome_input, orgao_input))
                        conn.commit()
                        st.session_state['aluno_matricula'] = matricula_input
                        st.session_state['aluno_nome'] = nome_input
                        st.session_state['aluno_orgao'] = orgao_input
                        st.session_state['aluno_logado'] = True
                        st.success("Perfil gerado com sucesso!")
                        st.rerun()
                        
    else:
        st.info(f"Estudante: **{st.session_state['aluno_nome']}** | Matrícula: **{st.session_state['aluno_matricula']}** | Órgão: **{st.session_state['aluno_orgao']}**")
        if st.sidebar.button("🚪 Sair / Mudar de Conta"):
            del st.session_state['aluno_logado']
            st.rerun()
            
        st.write("---")
        st.header("📁 Gerenciamento do seu Plano de Classificação")
        
        # DEFINIÇÃO DAS 3 ABAS SEPARADAS EXPLICITAMENTE
        tab1, tab2, tab3 = st.tabs([
            "➕ Inserir Novos Elementos", 
            "🔍 Visualizar & Editar Estrutura", 
            "📄 Exportar em PDF"
        ])
        
        # ABA 1: INSERÇÃO
        with tab1:
            st.subheader("Cadastrar Novo Item na Árvore Hierárquica")
            tipo_item = st.selectbox("Nível Hierárquico:", ["Função", "Subfunção", "Atividade", "Tipo documental"])
            codigo_item = st.text_input("Código Numérico:", help="Ex: 01, 01.01., 01.01.01.").strip()
            texto_item = st.text_area("Descrição/Texto (Máx 250 caracteres):", max_chars=250)
            
            if codigo_item and texto_item:
                valido, formato_correto = validar_codigo(codigo_item, tipo_item)
                if not valido:
                    st.error(f"Código inválido para '{tipo_item}'. {formato_correto}")
                else:
                    cod_limpo = codigo_item[:-1] if codigo_item.endswith('.') else codigo_item
                    partes = cod_limpo.split('.')
                    mat_atual = st.session_state['aluno_matricula']
                    
                    aviso_popup = ""
                    if tipo_item == "Subfunção" and len(partes) >= 2:
                        f_nome = buscar_nome_elemento(mat_atual, partes[0])
                        aviso_popup = f"O código {codigo_item} vincula este elemento à Função {partes[0]} ({f_nome})."
                    elif tipo_item == "Atividade" and len(partes) >= 3:
                        f_nome = buscar_nome_elemento(mat_atual, partes[0])
                        sf_cod = f"{partes[0]}.{partes[1]}"
                        sf_nome = buscar_nome_elemento(mat_atual, sf_cod)
                        aviso_popup = f"O código {codigo_item} vincula este elemento à Função {partes[0]} e Subfunção {sf_cod}."
                    elif tipo_item == "Tipo documental" and len(partes) >= 4:
                        at_cod = f"{partes[0]}.{partes[1]}.{partes[2]}"
                        aviso_popup = f"O código {codigo_item} vincula este elemento à subestrutura {at_cod}."

                    if tipo_item == "Função":
                        if st.button("💾 Salvar Função"):
                            cursor.execute("INSERT INTO estrutura (matricula, tipo, codigo, texto) VALUES (?, ?, ?, ?)",
                                           (mat_atual, tipo_item, codigo_item, texto_item.strip()))
                            conn.commit()
                            st.success("Função cadastrada com sucesso!")
                            st.rerun()
                    else:
                        with st.popover("Clique aqui para Validar & Salvar"):
                            st.write(aviso_popup)
                            if st.button("Confirmar e Gravar Elemento"):
                                cursor.execute("INSERT INTO estrutura (matricula, tipo, codigo, texto) VALUES (?, ?, ?, ?)",
                                               (mat_atual, tipo_item, codigo_item, texto_item.strip()))
                                conn.commit()
                                st.success("Elemento gravado!")
                                st.rerun()
            else:
                st.info("Preencha o código numérico e a descrição para liberar o salvamento.")

        # ABA 2: VISUALIZAÇÃO E EDIÇÃO
        with tab2:
            st.subheader(f"Estrutura de Classificação Atual: {st.session_state['aluno_orgao']}")
            cursor.execute("SELECT id, codigo, tipo, texto FROM estrutura WHERE matricula = ?", (st.session_state['aluno_matricula'],))
            dados = cursor.fetchall()
            
            if dados:
                dados_ordenados = sorted(dados, key=lambda x: x[1])
                
                # Exibição limpa da Árvore Arquivística
                for item_id, cod, tipo, txt in dados_ordenados:
                    if tipo == "Função": st.markdown(f"**{cod} {txt}**")
                    elif tipo == "Subfunção": st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📄 {cod} {txt}")
                    elif tipo == "Atividade": st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔹 {cod} {txt}")
                    elif tipo == "Tipo documental": st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔸 *{cod} {txt}*")
                
                st.write("---")
                st.subheader("🛠️ Painel de Modificações Rápidas")
                
                for item_id, cod, tipo, txt in dados_ordenados:
                    col_info, col_edit, col_del = st.columns([6, 2, 1])
                    with col_info:
                        st.write(f"`{cod}` **[{tipo}]** — {txt}")
                    with col_edit:
                        with st.expander("✏️ Editar"):
                            novo_texto = st.text_input("Alterar texto:", value=txt, key=f"txt_{item_id}")
                            if st.button("Confirmar", key=f"btn_edit_{item_id}"):
                                if novo_texto.strip():
                                    cursor.execute("UPDATE estrutura SET texto = ? WHERE id = ?", (novo_texto.strip(), item_id))
                                    conn.commit()
                                    st.success("Atualizado!")
                                    st.rerun()
                    with col_del:
                        if st.button("🗑️", key=f"btn_del_{item_id}", help="Excluir item"):
                            cursor.execute("DELETE FROM estrutura WHERE id = ?", (item_id,))
                            conn.commit()
                            st.warning("Removido!")
                            st.rerun()
            else:
                st.warning("Nenhum item adicionado à sua árvore hierárquica ainda.")

        # ABA 3: EXPORTAR EM PDF (COMPLETAMENTE ISOLADA)
        with tab3:
            st.subheader("📥 Exportação Oficial do Plano de Classificação")
            st.write("Gere a versão final consolidada do documento em formato PDF estruturado.")
            
            cursor.execute("SELECT id, codigo, tipo, texto FROM estrutura WHERE matricula = ?", (st.session_state['aluno_matricula'],))
            dados_pdf = cursor.fetchall()
            
            if dados_pdf:
                try:
                    pdf_data = gerar_pdf(st.session_state['aluno_orgao'], dados_pdf)
                    st.write("###")
                    st.download_button(
                        label="📄 Baixar Relatório Completo em PDF", 
                        data=pdf_data, 
                        file_name=f"Plano_de_Classificacao_{st.session_state['aluno_matricula']}.pdf", 
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error("Erro técnico ao compilar o PDF. Certifique-se de que não há caracteres invisíveis inválidos na descrição.")
            else:
                st.warning("Não há dados cadastrados para gerar o documento PDF.")

elif menu == "Área do Professor (Admin)":
    st.header("🔒 Painel Administrativo")
    usuario = st.text_input("Usuário Admin:")
    senha = st.text_input("Senha Admin:", type="password")
    if st.button("Acessar Painel"):
        if usuario == "Admin123" and senha == "123Admin":
            st.session_state['admin_logado'] = True
            st.success("Acesso autorizado!")
        else:
            st.error("Credenciais inválidas.")
